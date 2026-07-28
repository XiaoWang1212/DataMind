# 論文期刊評分代理人（Journal Scoring Agent）設計

日期:2026-07-28
狀態:已與使用者確認方向,待寫實作計畫

## 背景

[[2026-07-12-arxiv-paper-pipeline-design]] 已打通「資料探勘結果 → arXiv 候選 → 生成論文 → 顯示在 `/paper`」的流程,`backend/services/rag/paper_rag.py` 的 `PaperRAGService.generate_paper()` 會逐章節用 Gemini 生成論文,回傳 `paper_markdown`,前端 `paperTransform.ts` 把它轉成 `PaperReport`(拆成 `sections[].paragraphs[].segments`)存進 `paperStore`,`PaperPage.vue` 讀出來渲染,但轉換過程中不保留原始 `paper_markdown`。

本設計要在 `/paper` 頁面最後加一個「期刊評分」步驟:使用者看完生成的論文後,手動點擊按鈕,系統同時比對 3 個醫學資料科學相關期刊的審稿標準,對論文分別評分,並列出逐項理由與修改建議。

## 決策摘要

- **手動觸發,不接在 `generate_paper()` 後自動跑。** 使用者在 `/paper` 頁面看過論文後自行點擊「期刊評分」按鈕,評分過程不阻塞論文顯示。
- **同時比對 3 個固定期刊,各自獨立評分。** 不做期刊選擇 UI,固定比對 JAMIA、npj Digital Medicine、BMC Medical Informatics and Decision Making 三個醫學資料科學相關期刊,一次評分秀出全部 3 份結果。
- **評分準則寫死在後端常數,不做動態設定 UI。** 跟 `paper_rag.py` 既有的 `_SECTION_QUERIES` 同一種模組層級 dict 常數寫法,之後要調整期刊或準則直接改常數。
- **每個期刊各一次獨立的 Gemini 單次呼叫,JSON 回傳。** 沿用 `paper_rag.py` 既有的「一次 prompt 進、一次文字出」單次呼叫模式(如 `classify_topic()`、`generate_insight()`),但用 `response_mime_type="application/json"`(比照 `gemini_service.py` 的 `_generation_config()`)取得結構化分數,而非規則式文字再用正規表達式解析。3 個期刊之間互不共享 context,各自獨立呼叫、獨立失敗。
- **輸出格式:總分 + 逐項評分理由 + 修改建議。** 每個期刊回傳一個總分與 6 項準則(各自分數 + 文字理由),外加一組修改建議清單。
- **不持久化,只在前端當次使用。** 跟 `paperStore` 現有的一次性交接模式一致,評分結果只存在 dialog 開啟期間的 component state,離開頁面或重新評分就消失,後端不新增資料庫或檔案儲存。
- **從 `PaperReport` 還原論文文字,不改動現有的 store/transform 資料結構。** `PaperReport` 目前不保留原始 `paper_markdown`,新增一個純前端的還原函式,把 `report.sections` 組回一段文字送去評分,對「真實生成的論文」與「demo 用的 `mockPaperReport`」都同樣適用。
- **結果用彈出 Dialog + 期刊 Tab 呈現,不改動現有三欄版面。** 不在 `/paper` 頁面新增常駐面板,避免要重新分配論文本文欄與引用欄的寬度。

## 1. 評分準則

固定比對以下 3 個期刊,各自代表不同審稿側重點:

| 期刊 | 側重點 |
|---|---|
| JAMIA(Journal of the American Medical Informatics Association) | 方法嚴謹度、可重現性、資訊系統與臨床決策整合的實用性 |
| npj Digital Medicine | 臨床/實務影響力、創新性、跨領域整合、敘事簡潔清楚 |
| BMC Medical Informatics and Decision Making | 技術細節完整度、統計報告透明度(如信賴區間)、開放科學規範 |

每個期刊用同一組 6 項評分準則(維度相同,prompt 裡對每個期刊的側重描述不同):

1. 研究貢獻與新穎性
2. 方法嚴謹性(驗證策略、重採樣、超參數調校是否交代清楚)
3. 結果呈現與統計報告完整度
4. 文獻回顧與引用品質
5. 臨床/實務意義與限制討論
6. 寫作結構與期刊格式規範(IMRaD 完整度)

## 2. 後端

### 2.1 `paper_rag.py` 新增模組常數

```python
_JOURNAL_RUBRICS = [
    {
        "key": "jamia",
        "name": "JAMIA",
        "full_name": "Journal of the American Medical Informatics Association",
        "emphasis": "方法嚴謹度、可重現性、資訊系統與臨床決策整合的實用性",
    },
    {
        "key": "npj_digital_medicine",
        "name": "npj Digital Medicine",
        "full_name": "npj Digital Medicine",
        "emphasis": "臨床/實務影響力、創新性、跨領域整合、敘事簡潔清楚",
    },
    {
        "key": "bmc_midm",
        "name": "BMC Medical Informatics and Decision Making",
        "full_name": "BMC Medical Informatics and Decision Making",
        "emphasis": "技術細節完整度、統計報告透明度（如信賴區間）、開放科學規範",
    },
]

_SCORE_CRITERIA = [
    "研究貢獻與新穎性",
    "方法嚴謹性",
    "結果呈現與統計報告完整度",
    "文獻回顧與引用品質",
    "臨床/實務意義與限制討論",
    "寫作結構與期刊格式規範",
]
```

### 2.2 `PaperRAGService` 新增方法

```python
def score_paper(self, paper_text: str) -> dict:
    """對 _JOURNAL_RUBRICS 中每個期刊各呼叫一次 Gemini（JSON 回傳），
    依該期刊的 emphasis 與 _SCORE_CRITERIA 產生總分、逐項評分理由、修改建議。

    單一期刊評分失敗（Gemini 呼叫例外或 JSON 解析失敗）時跳過並記錄，
    不中斷整體流程；若全部期刊皆失敗則回傳 {"success": False, "error": ...}。

    回傳：
      {
        "success": True,
        "journal_scores": [
          {
            "journal": "JAMIA",
            "journal_full_name": "Journal of the American Medical Informatics Association",
            "overall_score": 78,
            "criteria": [
              {"name": "研究貢獻與新穎性", "score": 80, "comment": "..."},
              ...
            ],
            "suggestions": ["...", "..."]
          },
          ...
        ],
        "failed_journals": [],  # 評分失敗的期刊 name 清單
        "usage": {...}
      }
    """
```

實作細節:
- 每個期刊呼叫用 `generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=4096, response_mime_type="application/json")`,比照 `gemini_service.py` 的 `_generation_config()`。
- Prompt 內容:研究主題不需要(直接評論文全文),帶入 `paper_text`、該期刊的 `emphasis`、`_SCORE_CRITERIA` 清單,要求輸出符合上述 JSON 形狀。
- JSON 解析沿用 `gemini_service.py` 的 `_safe_parse_json()` 邏輯(直接 parse → 剝 ```json 圍欄 → 正規表達式抓 `{...}`),搬到 `paper_rag.py` 或抽成共用函式皆可,實作計畫階段決定。
- 單一期刊解析失敗或 Gemini 例外:記錄 warning log,加入 `failed_journals`,繼續下一個期刊。
- 3 個期刊皆失敗:回傳 `{"success": False, "error": "所有期刊評分皆失敗"}`。
- `usage` 累加 3 次呼叫的 token 用量,格式同 `generate_paper()` 的 `usage_total`。

### 2.3 新增路由(`routes/rag.py`)

```
POST /api/rag/score-paper
  body: { paper_text: str }
  → service.score_paper(data["paper_text"])
  回傳：與 score_paper() 相同形狀
```

驗證邏輯比照 `generate-paper`:無 JSON body 或 `paper_text` 為空白字串回 400。

## 3. 前端

### 3.1 還原論文純文字(`paperTransform.ts` 新增函式)

```ts
export function buildPaperText (report: PaperReport, citationIndex: Record<string, number>): string
```

`PaperReport` 目前不保留原始 `paper_markdown`,只有 `sections[].paragraphs[].segments`。此函式把 `report.title` + 每個 section 的 heading + 每段落 segment 的文字(遇到 `citationIds` 依 `citationIndex` 換算回 `[n]` 標記)重新組回一段純文字字串。對「真實生成的論文」與「demo 用的 `mockPaperReport`」都同樣適用,不需要改動 `paperStore` 或既有 transform 邏輯。

### 3.2 新增 API 函式(`frontend/src/api/arxiv.ts`)

```ts
export interface CriterionScore {
  name: string
  score: number
  comment: string
}

export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  criteria: CriterionScore[]
  suggestions: string[]
}

export async function scorePaper (paperText: string): Promise<{
  journalScores: JournalScore[]
  failedJournals: string[]
}>
```

沿用 `generateFromArxiv()` 同樣的 fetch → 檢查 `success` → 拋錯 / 回傳 result 模式。

### 3.3 新元件:`frontend/src/components/paper/JournalScoreDialog.vue`

- `v-dialog`,由 `PaperPage.vue` 控制開關與傳入 `journalScores` / `failedJournals`。
- 內部用 `v-tabs` 依期刊切換(3 個 tab),每個 tab 顯示:
  - 期刊全名 + 總分(例如以圓形分數或數字大字呈現)
  - 6 項準則:名稱 + 分數 + 文字理由(逐項列出)
  - 修改建議清單(條列)
- 若 `failedJournals` 非空,dialog 頂部顯示一行提示,例如「BMC Medical Informatics and Decision Making 評分失敗,僅顯示其餘期刊結果」。

### 3.4 `PaperPage.vue` 改動

- toolbar(`paper-toolbar`)新增「期刊評分」按鈕(`v-btn`,icon 例如 `mdi-school-outline`),放在標題右側。
- 點擊時:
  1. 呼叫 `buildPaperText(report, citationIndex)` 組出純文字。
  2. 按鈕進入 loading 狀態,呼叫 `scorePaper()`。
  3. 成功 → 開啟 `JournalScoreDialog`,傳入結果。
  4. 失敗(全部期刊評分失敗 / API 層級錯誤,如 HTTP 5xx、網路錯誤)→ 顯示 snackbar 錯誤訊息,不開 dialog,按鈕恢復可再次點擊(可重試)。

## 4. 錯誤處理

- 單一期刊評分失敗(Gemini 例外、JSON 解析失敗):後端跳過該期刊、記錄 log,回傳結果中列入 `failed_journals`,前端 dialog 頂部提示,其餘期刊正常顯示。
- 全部期刊評分失敗:後端回傳 `{"success": False, "error": ...}`,前端顯示 snackbar 錯誤訊息,不開 dialog,可重新點擊按鈕重試。
- 網路 / API 層級錯誤(如 HTTP 5xx、連線失敗):前端 `scorePaper()` 拋出例外,`PaperPage.vue` 捕捉後顯示 snackbar,按鈕恢復可重試。

## 5. 不在本次範圍

- 期刊清單或評分準則的使用者自訂 UI(維持寫死在後端常數)。
- 評分結果持久化(資料庫、檔案儲存、歷史評分查詢)。
- 自動在 `generate_paper()` 完成後接著評分(維持手動觸發)。
- 依評分建議自動修改論文內容。
