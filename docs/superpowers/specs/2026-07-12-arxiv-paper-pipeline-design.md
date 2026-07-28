# arXiv 文獻檢索與論文生成 Pipeline 設計

日期:2026-07-12
狀態:已與使用者確認方向,待寫實作計畫

## 背景

`backend/services/rag/paper_rag.py` 的 `PaperRAGService.generate_paper()` 已經能用 DataMind 資料探勘結果 + 向量庫裡的參考論文,逐章節透過 Gemini 生成學術論文,並輸出 `citation_map`(逐段引用地圖)。但目前向量庫裡的參考論文只能靠 `add_paper()` 手動上傳(見 `backend/scripts/test_paper_gen.py` 裡手打的 `MOCK_PAPERS`),沒有自動化的文獻來源。

前端 `/paper` 頁面([[2026-07-08-results-paper-transition-design]] 的成果)目前也只是讀取寫死的 `frontend/src/constants/reportData.ts` 假資料,尚未接上 `generate_paper()` 的真實回傳。

本設計要補上「資料探勘結果 → 自動分類產生查詢字 → 查 arXiv → 使用者勾選候選論文 → 下載全文入庫 → 生成論文 → 顯示在 /paper」這一整條路徑。

## 決策摘要

- **向量庫維持單一、全域,每次生成前清空。** 不做多專案分庫,`ingest_arxiv_selection()` 一律先 `clear()` 再入庫,避免跨主題引用污染。
- **分類與查詢用 Gemini,不用規則比對。** 沿用 `PaperRAGService` 既有的 Gemini client,讀 `_format_datamind_output()` 摘要,一次呼叫同時產生研究主題(topic)與 arXiv 查詢字串,不需要使用者手動輸入主題。
- **候選論文用摘要,選中的才下載全文。** arXiv API 本身就回傳摘要,查詢/勾選階段不下載 PDF;使用者確認勾選後才對選中的論文下載 PDF、用既有的 `pymupdf` 解析全文入庫。
- **兩支 API,不是一次全包。** `search` 只回傳候選清單給前端顯示;`generate` 才做「入庫 + 呼叫既有 generate_paper()」,兩者可獨立測試。
- **選完直接跑完整論文生成,完成後導向 `/paper`。** 使用者體驗上是一次性的:進入選擇頁 → 勾選 → 按確認 → 等待 → 看到 `/paper` 的真實結果。
- **本次也把「生成結果 → `/paper` 顯示」的轉換一併做掉**,雖然這原本屬於「打通真實資料流」子專案的範圍,但因為這裡的使用者流程需要看到 `/paper` 的真實結果,所以只做「這一次生成結果的顯示」,`/workflow → /results` 真實資料串接、`/results` 儀表板真實圖表仍然留到之後的子專案。
- **`mining_results` 暫時用假資料。** `/results` 目前仍是假資料(見上一點的範圍收斂),「生成論文」按鈕送出跟 `test_paper_gen.py` 裡 `MOCK_DATAMIND_OUTPUT` 同形狀的假 JSON。
- **`PaperSegment` 型別擴充為支援多重引用。** 後端生成文字可能出現 `[1][2]` 這種同句多引用,把 `citationId?: string` 改成 `citationIds?: string[]`,`PaperSection.vue` 對應調整。

## 1. 後端

### 1.1 新模組:`backend/services/rag/arxiv_source.py`

不依賴 Gemini,純粹的 arXiv API 與 PDF 處理函式:

```python
def search_arxiv(query: str, max_results: int = 8) -> list[dict]:
    """呼叫 arXiv Export API(export.arxiv.org/api/query),用 stdlib
    urllib + xml.etree 解析 Atom XML(不需要新增 pip 套件)。
    回傳每筆:{arxiv_id, title, authors, year, abstract, pdf_url}
    """

def fetch_pdf_text(pdf_url: str) -> str:
    """下載 PDF 到暫存檔,用既有的 pymupdf(routes/rag.py 已在用)解析全文,
    結束後清除暫存檔,回傳純文字。下載或解析失敗時拋出例外,由呼叫端決定
    是否跳過該篇。
    """
```

### 1.2 `PaperRAGService` 新增方法(`paper_rag.py`)

```python
def classify_topic(self, mining_results: dict) -> dict:
    """用既有 self._model(Gemini),讀 _format_datamind_output() 摘要,
    回傳 {"topic": str, "arxiv_query": str}。
    一次 Gemini 呼叫同時產生「給人看的研究主題」與「給 arXiv 查詢的英文關鍵字字串」。
    """

def search_arxiv_candidates(self, mining_results: dict) -> dict:
    """呼叫 classify_topic() 取得 topic/arxiv_query,
    呼叫 arxiv_source.search_arxiv(arxiv_query) 取得候選清單。
    回傳 {"topic": str, "arxiv_query": str, "candidates": [...]}
    此步驟不寫入向量庫。
    """

def ingest_arxiv_selection(self, candidates: list[dict]) -> dict:
    """candidates: 使用者勾選的候選論文清單(含 title/pdf_url/authors/year/arxiv_id)。
    先 self.clear() 清空向量庫,再逐篇呼叫 arxiv_source.fetch_pdf_text() +
    self.add_paper()。單篇下載/解析失敗時跳過並記錄,不中斷整體流程;
    若全部失敗則回傳 {"success": False, "error": ...}。
    回傳 {"success": True, "ingested": [...標題清單], "failed": [...標題清單]}
    """
```

### 1.3 新增路由(`routes/rag.py`)

```
POST /api/rag/arxiv/search
  body: { mining_results: dict }
  → service.search_arxiv_candidates(mining_results)
  回傳: { success, topic, arxiv_query, candidates }

POST /api/rag/arxiv/generate
  body: { topic: str, mining_results: dict, selected_candidates: list[dict] }
  → service.ingest_arxiv_selection(selected_candidates)
  → service.generate_paper(topic=topic, mining_results=mining_results)
  回傳: 與現有 /api/rag/generate-paper 相同形狀
        { success, result: { paper_markdown, citation_map, references,
                              citation_report, sections_generated, usage } }
  若 ingest 全部失敗 → 提早回傳錯誤,不呼叫 generate_paper()
```

## 2. 前端

### 2.1 假 mining_results

新增 `frontend/src/constants/mockMiningResults.ts`,內容形狀對齊後端 `test_paper_gen.py` 的 `MOCK_DATAMIND_OUTPUT`(class_distribution / preprocess_variants / results 陣列)。

### 2.2 新頁面:`frontend/src/views/PaperSourcesView.vue`

路由 `/paper/sources`(不加入 sidebar 導覽項目,沿用 `<HubSidebar />` 維持外觀一致)。

行為:
1. mount 時呼叫 `POST /api/rag/arxiv/search`(帶 mock mining_results),顯示 loading。
2. 顯示候選論文卡片清單(標題/作者/年份/摘要),每張卡片一個 checkbox。查無結果或呼叫失敗時顯示對應錯誤/空狀態,「確認」按鈕停用。
3. 使用者勾選後按「確認並生成論文」→ 呼叫 `POST /api/rag/arxiv/generate`,顯示生成中狀態。
4. 成功 → 把後端回傳轉換成 `PaperReport`(見 2.4)存進 `paperStore`,`router.push('/paper')`。
5. 失敗 → 顯示錯誤訊息,停在本頁,可重新勾選/重試。

### 2.3 觸發入口

`ResultsPage.vue` 新增「生成論文」按鈕 → 帶著 `mockMiningResults` 導向 `/paper/sources`(mining_results 透過同一個 `paperStore` 或 route state 傳遞,實作計畫階段決定細節)。

### 2.4 後端回傳 → `PaperReport` 轉換

新增轉換函式(建議放在 `frontend/src/utils/paperTransform.ts`),輸入後端 `/api/rag/arxiv/generate` 回傳的 `result`,輸出符合 `frontend/src/constants/reportData.ts` 的 `PaperReport` 型別:

- 解析 `paper_markdown`:依 `\n\n---\n\n` 分段落取出每個 `## 章節標題` 區塊(略過最後的「參考文獻」區塊,因為 `references` 陣列已有結構化資料)。
- 每個區塊內文依空行切段落,每段落依正規表達式抓出 `[n]`(可能連續多個,如 `[1][2]`)切成 `PaperSegment[]`。
- `references` 陣列轉成 `Citation[]`(欄位對應:`ref_id → id`、`title/author/year` 對應、`relevant_chunk`(來自 `citation_map` 對應項)作為 `snippet`)。

### 2.5 型別擴充(`reportData.ts`)

```ts
export interface PaperSegment {
  text: string
  citationIds?: string[]   // 原本是 citationId?: string，改為陣列支援同句多重引用
}
```

`PaperSection.vue` 對應調整:一個 `<mark>` 對應到 `citationIds` 全部,`data-citation-id` 存成以逗號分隔的清單,`activeCitationId` 比對邏輯改為 `segment.citationIds?.includes(activeCitationId)`。

### 2.6 `/paper` 頁面調整

新增 `frontend/src/store/paperStore.ts`(Pinia,沿用 `projectStore.ts` 的 `activeContext` 一次性交接模式):`PaperSourcesView` 生成成功後把轉換好的 `PaperReport` 存進去;`PaperPage.vue` mount 時讀取並清空,若沒有資料則 fallback 顯示既有的 `mockPaperReport`(維持直接開 `/paper` 也能看到示範內容)。

## 3. 錯誤處理

- arXiv 查詢失敗/查無結果:前端顯示錯誤或空狀態,停用「確認」。
- 選中候選論文的 PDF 下載/解析失敗:單篇跳過、記錄,不中斷整體;全部失敗則整體回傳錯誤。
- Gemini 呼叫失敗(分類或章節生成):回傳錯誤訊息,前端顯示並允許重試。

## 4. 不在本次範圍

- `/workflow → /results` 真實資料串接、`/results` 儀表板真實圖表(留給後續子專案)。
- 已入庫論文的管理 UI(刪除/編輯;後端刪除 API 已存在但不做介面)。
- 多組論文庫並存(維持單一庫、每次生成前清空)。
- 論文匯出(PDF/Word)。
