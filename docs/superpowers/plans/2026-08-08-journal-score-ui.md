# 期刊評分系統 UI 重新設計 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「期刊評分」功能（觸發按鈕、佔位卡、評分摘要卡、評分結果彈窗）的視覺設計改成使用者提供的 Figma Make 設計稿樣式，且只動評分系統本身，不改動 PaperPage 其餘部分（論文內文、引用面板行為、頁首其他元素）。

**Architecture:** 純視覺重構，資料流與既有 API 合約不變（僅新增 1 個欄位 `overall_comment`／`overallComment`）。新增 2 個共用的小型 TS 工具（分數門檻顏色、期刊識別色）與 2 個新 Vue 元件（`ScoreRing.vue` 圓形量表、`JournalScorePanel.vue` 側欄卡片），並整個重寫 `JournalScoreDialog.vue` 的樣板與樣式；`PaperPage.vue` 只改按鈕（圖示/文字/loading 視覺）與側欄版面（在 `CitationPanel` 上方插入新卡片）。

**Tech Stack:** Vue 3 `<script setup lang="ts">` + Vuetify 4（`v-progress-circular`、`v-icon`、`v-btn`）+ scoped CSS（沿用專案既有「每元件自訂 CSS variable」風格，不使用 Tailwind utility class，因為 `PaperPage.vue`/`JournalScoreDialog.vue` 現況本來就不用）；後端 Flask + Gemini（`backend/services/rag/paper_rag.py`）。

## Global Constraints

- **範圍鎖定**：只能修改下列檔案，其他一律不動：
  `frontend/src/views/PaperPage.vue`、`frontend/src/components/paper/JournalScoreDialog.vue`、`frontend/src/api/arxiv.ts`、`backend/services/rag/paper_rag.py`、`backend/routes/rag.py`、`backend/scripts/test_score_paper.py`，以及本計畫新增的檔案。
- **不新增套件**：不得在 `frontend/package.json` / `backend/requirements.txt` 新增任何相依套件（圖示已有 `@mdi/font`，圓形量表用 Vuetify 既有的 `v-progress-circular`，襯線字體用系統字體 fallback stack，不額外載入字型）。
- **色票（依螢幕截圖與既有程式碼色票校準，允許實作時用瀏覽器 DevTools 微調 ±10% 亮度以貼近截圖，但色相與門檻邏輯不可變）**：
  - 期刊識別色（tab 底線／`期刊評分報告` 眉標／`逐項評分準則`・`修改建議` 標題色）：JAMIA = `#1058d6`（沿用 `PaperPage.vue` 既有 `--brand`）、npj Digital Medicine = `#8a6d1a`（沿用 `CitationPanel.vue` 既有金色）、BMC Medical Informatics and Decision Making = `#0d5d73`（沿用 `frontend/src/styles/tailwind.css` 既有 `--color-secondary-800`）。
  - 分數門檻色（圓形量表、進度條，與期刊識別色**互相獨立**）：分數 `>= 80` 用 teal `#0d5d73`，分數 `< 80` 用金色 `#8a6d1a`。
  - 按鈕主色（不隨分數/期刊變動的固定品牌金色）：實心 `#6f5613`、tonal/loading 態底色 `#fffbe8` 邊框 `#c9ad2a` 文字 `#8a6d1a`（沿用 `CitationPanel.vue` 金色家族）。
- **佔位卡／評分摘要卡的放置位置**：使用者已確認放在 `paper-citations` 欄位（`CitationPanel` 正上方），不得放進論文內文區或頁首。
- **「再次評分」文案規則**：按鈕文字狀態機為 `期刊評分`（`journalScores.length === 0` 且非 loading）→ `評分中...`（`scoring === true`）→ `再次評分`（`journalScores.length > 0` 且非 loading）。
- **設計參考截圖**：已存放於 `docs/superpowers/plans/assets/2026-08-08-journal-score-ui/`（`01-idle.png` ~ `09-summary-after-close.png`），每個 Task 會指名對應截圖，實作時務必用 Read 工具開啟比對。
- **驗證方式**：此專案前端無單元測試框架（無 vitest/jest），後端此功能的既有驗證方式是手動腳本 `backend/scripts/test_score_paper.py`（需要 `backend/.env` 內的 `GEMINI_API_KEY`，已確認存在）。因此本計畫的「測試」步驟採：(a) 純函式邏輯用 `python -c` 隔離驗證（不需要 API key）、(b) 型別檢查 `npm run type-check`／`npm run lint`、(c) 最終以 `docker compose up -d backend frontend` 啟動後，瀏覽器開 `http://localhost:5173/paper`（未帶 `paperStore.generatedReport` 時會自動顯示 `mockPaperReport`，不需跑完整 arXiv 流程）人工比對截圖。

---

## Task 1: 分數門檻顏色與期刊識別色工具函式

**Files:**
- Create: `frontend/src/utils/scoreColor.ts`
- Create: `frontend/src/utils/journalTheme.ts`

**Interfaces:**
- Consumes: 無（純函式，無外部依賴）
- Produces:
  - `scoreColor.ts` 匯出 `SCORE_THRESHOLD: number`、`SCORE_COLOR_HIGH: string`、`SCORE_COLOR_LOW: string`、`getScoreColor(score: number): string`
  - `journalTheme.ts` 匯出 `interface JournalAccent { main: string; soft: string; text: string }`、`getJournalAccent(journal: string): JournalAccent`
  - 供 Task 2（`ScoreRing.vue`）、Task 3（`JournalScorePanel.vue`）、Task 4（`JournalScoreDialog.vue`）使用

- [ ] **Step 1: 建立 `scoreColor.ts`**

```ts
// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80
export const SCORE_COLOR_HIGH = '#0d5d73'
export const SCORE_COLOR_LOW = '#8a6d1a'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? SCORE_COLOR_HIGH : SCORE_COLOR_LOW
}
```

- [ ] **Step 2: 建立 `journalTheme.ts`**

```ts
// frontend/src/utils/journalTheme.ts
export interface JournalAccent {
  main: string
  soft: string
  text: string
}

const JOURNAL_ACCENTS: Record<string, JournalAccent> = {
  JAMIA: { main: '#1058d6', soft: '#eaf1fd', text: '#1058d6' },
  'npj Digital Medicine': { main: '#8a6d1a', soft: '#fffbe8', text: '#8a6d1a' },
  'BMC Medical Informatics and Decision Making': { main: '#0d5d73', soft: '#e6f3f6', text: '#0d5d73' },
}

const DEFAULT_ACCENT: JournalAccent = { main: '#4a4f5c', soft: '#eef0f4', text: '#4a4f5c' }

export function getJournalAccent (journal: string): JournalAccent {
  return JOURNAL_ACCENTS[journal] ?? DEFAULT_ACCENT
}
```

> 用期刊「名稱字串」查表而非陣列索引，是因為 `failed_journals` 可能讓 `journalScores` 少掉其中一個期刊（例如 JAMIA 評分失敗時，陣列只剩 npj + BMC MIDM 兩筆），若用索引 0/1/2 對應顏色會把顏色分配錯期刊。

- [ ] **Step 3: 型別檢查**

Run（於 `frontend/` 目錄下）：`npm run type-check`
Expected: 無錯誤（兩個新檔案目前未被任何地方 import，但仍需通過型別檢查本身）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/scoreColor.ts frontend/src/utils/journalTheme.ts
git commit -m "feat: add score threshold color and journal accent color utils"
```

---

## Task 2: `ScoreRing.vue` 圓形分數量表元件

**Files:**
- Create: `frontend/src/components/paper/ScoreRing.vue`

**Interfaces:**
- Consumes: `getScoreColor` from `@/utils/scoreColor`（Task 1）
- Produces: `ScoreRing` 元件，props `{ score: number; size?: number; strokeWidth?: number; fontSize?: number }`（`size` 預設 96、`strokeWidth` 預設 8、`fontSize` 預設 `Math.round(size / 3.4)`），供 Task 3、Task 4 以大／小兩種尺寸重用（對照截圖 `03-modal-jamia-top.png` 左側大圓環，以及大圓環右側 78/82/80 三個小圓環）

- [ ] **Step 1: 建立元件**

```vue
<!-- frontend/src/components/paper/ScoreRing.vue -->
<template>
  <v-progress-circular
    bg-color="#e8ebf1"
    class="score-ring"
    :color="ringColor"
    :model-value="score"
    :size="size"
    :width="strokeWidth"
  >
    <span class="score-ring__value" :style="{ fontSize: `${fontSize}px` }">{{ score }}</span>
  </v-progress-circular>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = withDefaults(defineProps<{
    score: number
    size?: number
    strokeWidth?: number
    fontSize?: number
  }>(), {
    size: 96,
    strokeWidth: 8,
  })

  const ringColor = computed(() => getScoreColor(props.score))
  const fontSize = computed(() => props.fontSize ?? Math.round(props.size / 3.4))
</script>

<style scoped>
  .score-ring__value {
    font-weight: 700;
    color: #1c2130;
  }
</style>
```

> 使用 Vuetify 既有的 `v-progress-circular`（此專案已經在用 `v-btn`/`v-icon` 等 Vuetify 元件）取代手刻 SVG，`model-value` 直接吃 0–100 的分數當百分比，`bg-color` 是底層灰色軌道（沿用 `JournalScoreDialog.vue` 現有的 `#e8ebf1` 分隔線色，維持一致）。

- [ ] **Step 2: 型別檢查**

Run（於 `frontend/` 目錄下）：`npm run type-check`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/ScoreRing.vue
git commit -m "feat: add ScoreRing circular score gauge component"
```

---

## Task 3: `JournalScorePanel.vue` 側欄卡片（佔位卡 + 評分摘要卡）

**Files:**
- Create: `frontend/src/components/paper/JournalScorePanel.vue`
- Test: 人工瀏覽器比對（無自動化測試框架，見 Global Constraints）

**Interfaces:**
- Consumes:
  - `ScoreRing` from `@/components/paper/ScoreRing.vue`（Task 2）
  - `getScoreColor` from `@/utils/scoreColor`（Task 1）
  - `type JournalScore` from `@/api/arxiv`（既有型別，見下方「目前介面」）
- Produces: `JournalScorePanel` 元件
  - Props: `{ journalScores: JournalScore[]; scoring: boolean }`
  - Emits: `openReport: []`（使用者點擊「查看完整評分報告 →」時觸發，由 Task 5 的 `PaperPage.vue` 接住並設 `scoreDialogVisible.value = true`）

目前 `JournalScore`（`frontend/src/api/arxiv.ts` 既有介面，Task 6 會加一個欄位）：
```ts
export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  criteria: CriterionScore[]
  suggestions: string[]
}
```

- [ ] **Step 1: 建立元件（先建對照截圖 `01-idle.png` 的佔位卡狀態，與 `09-summary-after-close.png` 的評分摘要卡狀態）**

```vue
<!-- frontend/src/components/paper/JournalScorePanel.vue -->
<template>
  <div class="score-panel">
    <div v-if="journalScores.length === 0" class="score-panel-empty">
      <div class="score-panel-empty__icon">
        <v-icon color="#8a6d1a" icon="mdi-star" size="22" />
      </div>
      <p class="score-panel-empty__text">
        點擊「期刊評分」按鈕，以 <strong>JAMIA</strong>、<strong>npj Digital Medicine</strong>、<strong>BMC MIDM</strong> 的審稿標準評估本文
      </p>
      <p class="score-panel-empty__meta">3 個期刊 · 6 項準則 · AI 評分</p>
    </div>

    <div v-else class="score-panel-summary">
      <div class="score-panel-summary__head">
        <ScoreRing :font-size="15" :score="averageScore" :size="40" :stroke-width="4" />
        <span class="score-panel-summary__avg-label">avg</span>
      </div>

      <p class="score-panel-summary__title">評分摘要</p>

      <ul class="score-panel-summary__list">
        <li v-for="js in journalScores" :key="js.journal" class="score-panel-summary__row">
          <div class="score-panel-summary__row-head">
            <span class="score-panel-summary__row-name">{{ js.journal }}</span>
            <span class="score-panel-summary__row-score" :style="{ color: getScoreColor(js.overallScore) }">
              {{ js.overallScore }}
            </span>
          </div>
          <div class="score-panel-summary__bar">
            <div
              class="score-panel-summary__bar-fill"
              :style="{ width: `${js.overallScore}%`, background: getScoreColor(js.overallScore) }"
            />
          </div>
        </li>
      </ul>

      <button class="score-panel-summary__cta" type="button" @click="emit('openReport')">
        查看完整評分報告
        <v-icon icon="mdi-arrow-right" size="14" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = defineProps<{
    journalScores: JournalScore[]
    scoring: boolean
  }>()

  const emit = defineEmits<{
    openReport: []
  }>()

  const averageScore = computed(() => {
    if (props.journalScores.length === 0) return 0
    const sum = props.journalScores.reduce((acc, js) => acc + js.overallScore, 0)
    return Math.round(sum / props.journalScores.length)
  })
</script>

<style scoped>
  .score-panel {
    margin-bottom: 12px;
  }

  .score-panel-empty {
    background: #ffffff;
    border: 1px solid #e8ebf1;
    border-radius: 12px;
    padding: 24px 18px;
    text-align: center;
  }

  .score-panel-empty__icon {
    width: 44px;
    height: 44px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fffbe8;
    border-radius: 10px;
  }

  .score-panel-empty__text {
    margin: 0 0 8px;
    font-size: 12.5px;
    line-height: 1.7;
    color: #4a4f5c;
  }

  .score-panel-empty__text strong {
    color: #1c2130;
  }

  .score-panel-empty__meta {
    margin: 0;
    font-size: 11.5px;
    color: #1058d6;
  }

  .score-panel-summary {
    background: #ffffff;
    border: 1px solid #e8ebf1;
    border-radius: 12px;
    padding: 16px 16px 14px;
  }

  .score-panel-summary__head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .score-panel-summary__avg-label {
    font-size: 11px;
    color: #6f7480;
  }

  .score-panel-summary__title {
    margin: 0 0 10px;
    font-size: 12.5px;
    font-weight: 700;
    color: #8a6d1a;
  }

  .score-panel-summary__list {
    list-style: none;
    margin: 0 0 12px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .score-panel-summary__row-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }

  .score-panel-summary__row-name {
    font-size: 12px;
    font-weight: 600;
    color: #1c2130;
  }

  .score-panel-summary__row-score {
    font-size: 12.5px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .score-panel-summary__bar {
    height: 5px;
    border-radius: 3px;
    background: #e8ebf1;
    overflow: hidden;
  }

  .score-panel-summary__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .score-panel-summary__cta {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 10px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: none;
    font-size: 12px;
    font-weight: 600;
    color: #4a4f5c;
    cursor: pointer;
  }

  .score-panel-summary__cta:hover {
    border-color: #1058d6;
    color: #1058d6;
  }
</style>
```

> `scoring` prop 目前只保留給未來擴充用（截圖 `02-loading.png` 顯示 loading 中卡片內容跟 idle 一樣不變，所以本元件內部不需要依 `scoring` 切換樣式，但仍宣告該 prop 讓 `PaperPage.vue` 呼叫端型別完整、之後若要加 loading 骨架也不用改 props 介面）。

- [ ] **Step 2: 型別檢查**

Run（於 `frontend/` 目錄下）：`npm run type-check`
Expected: 無錯誤（此元件尚未被使用，Task 5 才會接上）

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/JournalScorePanel.vue
git commit -m "feat: add JournalScorePanel sidebar card (empty state + score summary)"
```

---

## Task 4: 後端 — `score_paper()` 新增每期刊「一句話總評」欄位

設計稿的大圓環旁邊有一句總評文字（例如 JAMIA 頁籤：「本文具備發表潛力，但需在引用廣度與臨床轉化論述上強化。」，見 `03-modal-jamia-top.png`），現有 API 回傳的 `JournalScore`（`journal`/`journal_full_name`/`overall_score`/`criteria`/`suggestions`）沒有這個欄位，需要後端新增 `overall_comment`。

**Files:**
- Modify: `backend/services/rag/paper_rag.py:622-641`（`_validate_score_shape`）
- Modify: `backend/services/rag/paper_rag.py:421-434`（`score_paper()` 組裝回傳 dict）
- Modify: `backend/services/rag/paper_rag.py:692-711`（`_build_score_prompt`）
- Modify: `backend/routes/rag.py:462-465`（docstring）
- Modify: `backend/scripts/test_score_paper.py:65-72`

**Interfaces:**
- Consumes: 無新依賴
- Produces: `POST /api/rag/score-paper` 回應的 `journal_scores[].overall_comment: string`（非空字串），供 Task 5（`arxiv.ts` 型別/映射）與 Task 6（`JournalScoreDialog.vue` 顯示）使用

- [ ] **Step 1: 在 `_build_score_prompt` 的 JSON schema 指示中加入 `overall_comment`**

`backend/services/rag/paper_rag.py:692-711` 現況：

```python
    @staticmethod
    def _build_score_prompt(paper_text: str, rubric: Dict[str, str]) -> str:
        criteria_list = "\n".join(f"- {c}" for c in _SCORE_CRITERIA)
        return (
            f"你是《{rubric['full_name']}》（{rubric['name']}）的資深審稿人。"
            f"該期刊特別重視：{rubric['emphasis']}。\n\n"
            "請依照以下 6 項準則評估這篇論文，每項給 0 到 100 分並附上簡短的中文理由，"
            "最後再給一個 0 到 100 的總分，以及 2 到 5 條具體的修改建議。\n\n"
            f"【評分準則】\n{criteria_list}\n\n"
            f"【論文全文】\n{paper_text}\n\n"
            "請「只」輸出以下形狀的 JSON，不要有其他文字或 Markdown 圍欄：\n"
            "{\n"
            '  "overall_score": <0-100 整數>,\n'
            '  "criteria": [\n'
            '    {"name": "<準則名稱，須完全比照上面清單>", "score": <0-100 整數>, "comment": "<中文理由>"},\n'
            "    ...\n"
            "  ],\n"
            '  "suggestions": ["<修改建議1>", "<修改建議2>", ...]\n'
            "}"
        )
```

改為：

```python
    @staticmethod
    def _build_score_prompt(paper_text: str, rubric: Dict[str, str]) -> str:
        criteria_list = "\n".join(f"- {c}" for c in _SCORE_CRITERIA)
        return (
            f"你是《{rubric['full_name']}》（{rubric['name']}）的資深審稿人。"
            f"該期刊特別重視：{rubric['emphasis']}。\n\n"
            "請依照以下 6 項準則評估這篇論文，每項給 0 到 100 分並附上簡短的中文理由，"
            "最後再給一個 0 到 100 的總分、一句總評，以及 2 到 5 條具體的修改建議。\n\n"
            f"【評分準則】\n{criteria_list}\n\n"
            f"【論文全文】\n{paper_text}\n\n"
            "請「只」輸出以下形狀的 JSON，不要有其他文字或 Markdown 圍欄：\n"
            "{\n"
            '  "overall_score": <0-100 整數>,\n'
            '  "overall_comment": "<一句話總評，20 到 40 字繁體中文，'
            "須具體點出本文相對於本期刊發表門檻的主要優勢與待加強之處，不可只是空泛的鼓勵語句>,\n"
            '  "criteria": [\n'
            '    {"name": "<準則名稱，須完全比照上面清單>", "score": <0-100 整數>, "comment": "<中文理由>"},\n'
            "    ...\n"
            "  ],\n"
            '  "suggestions": ["<修改建議1>", "<修改建議2>", ...]\n'
            "}"
        )
```

- [ ] **Step 2: 在 `_validate_score_shape` 加入 `overall_comment` 驗證**

`backend/services/rag/paper_rag.py:622-628` 現況：

```python
    @staticmethod
    def _validate_score_shape(parsed: dict) -> None:
        """檢查 score_paper() 解析出的 JSON 是否符合預期結構，不符合則拋出 ValueError，
        交由呼叫端的重試/失敗邏輯處理，避免不完整的 Gemini 回傳被當成成功結果。"""
        if not isinstance(parsed.get("overall_score"), (int, float)):
            raise ValueError(f"overall_score 缺漏或非數字：{parsed.get('overall_score')!r}")

        criteria = parsed.get("criteria")
```

改為（在 `overall_score` 檢查後、`criteria = parsed.get("criteria")` 前插入新檢查）：

```python
    @staticmethod
    def _validate_score_shape(parsed: dict) -> None:
        """檢查 score_paper() 解析出的 JSON 是否符合預期結構，不符合則拋出 ValueError，
        交由呼叫端的重試/失敗邏輯處理，避免不完整的 Gemini 回傳被當成成功結果。"""
        if not isinstance(parsed.get("overall_score"), (int, float)):
            raise ValueError(f"overall_score 缺漏或非數字：{parsed.get('overall_score')!r}")

        if not isinstance(parsed.get("overall_comment"), str) or not parsed["overall_comment"].strip():
            raise ValueError(f"overall_comment 缺漏或非文字：{parsed.get('overall_comment')!r}")

        criteria = parsed.get("criteria")
```

- [ ] **Step 3: 用純 Python 驗證 `_validate_score_shape` 的新檢查（不需要 GEMINI_API_KEY，不打網路）**

Run（於 `backend/` 目錄下）：

```bash
python -c "
from services.rag.paper_rag import PaperRAGService

base = {
    'overall_score': 80,
    'overall_comment': '本文方法嚴謹但文獻回顧稍嫌不足。',
    'criteria': [
        {'name': n, 'score': 80, 'comment': 'ok'}
        for n in ['研究貢獻與新穎性', '方法嚴謹性', '結果呈現與統計報告完整度',
                  '文獻回顧與引用品質', '臨床/實務意義與限制討論', '寫作結構與期刊格式規範']
    ],
    'suggestions': ['補充近兩年文獻'],
}
PaperRAGService._validate_score_shape(base)
print('PASS: 完整結構通過驗證')

missing = dict(base)
del missing['overall_comment']
try:
    PaperRAGService._validate_score_shape(missing)
    raise SystemExit('FAIL: 缺少 overall_comment 應該要丟 ValueError')
except ValueError as e:
    print(f'PASS: 缺少 overall_comment 正確被擋下（{e}）')
"
```

Expected: 兩行都印出 `PASS:` 開頭訊息，若印出 `FAIL:` 或拋出未預期例外則代表驗證邏輯有誤，需修正 Step 2 的程式碼。

> 這個 `python -c` 只 import `PaperRAGService` 這個 class 定義並直接呼叫 `@staticmethod`，不會觸發 `__init__`（不會嘗試連線 Gemini 或載入向量庫），所以不需要 `GEMINI_API_KEY` 也能跑。

- [ ] **Step 4: 在 `score_paper()` 組裝回傳 dict 時帶入 `overall_comment`**

`backend/services/rag/paper_rag.py:421-434` 現況：

```python
                journal_scores.append({
                    "journal": rubric["name"],
                    "journal_full_name": rubric["full_name"],
                    "overall_score": int(parsed["overall_score"]),
                    "criteria": [
                        {
                            "name": str(c["name"]),
                            "score": int(c["score"]),
                            "comment": str(c["comment"]),
                        }
                        for c in parsed["criteria"]
                    ],
                    "suggestions": [str(s) for s in parsed.get("suggestions", [])],
                })
```

改為：

```python
                journal_scores.append({
                    "journal": rubric["name"],
                    "journal_full_name": rubric["full_name"],
                    "overall_score": int(parsed["overall_score"]),
                    "overall_comment": str(parsed["overall_comment"]),
                    "criteria": [
                        {
                            "name": str(c["name"]),
                            "score": int(c["score"]),
                            "comment": str(c["comment"]),
                        }
                        for c in parsed["criteria"]
                    ],
                    "suggestions": [str(s) for s in parsed.get("suggestions", [])],
                })
```

- [ ] **Step 5: 更新 `backend/routes/rag.py` 的路由 docstring（純文件字串，反映新欄位）**

`backend/routes/rag.py:462-465` 現況：

```python
    回傳：
        - journal_scores  : 各期刊評分結果（journal/journal_full_name/overall_score/criteria/suggestions）
        - failed_journals : 評分失敗的期刊名稱清單
        - usage           : Gemini token 用量
```

改為：

```python
    回傳：
        - journal_scores  : 各期刊評分結果（journal/journal_full_name/overall_score/overall_comment/criteria/suggestions）
        - failed_journals : 評分失敗的期刊名稱清單
        - usage           : Gemini token 用量
```

- [ ] **Step 6: 更新既有的手動驗證腳本，斷言新欄位存在（需要真實 `GEMINI_API_KEY`，會打網路呼叫 Gemini）**

`backend/scripts/test_score_paper.py:65-72` 現況：

```python
    for js in result["journal_scores"]:
        print(f"\n▶ {js['journal']}（總分 {js['overall_score']}）")
        assert 0 <= js["overall_score"] <= 100
        assert len(js["criteria"]) == 6, f"應有 6 項準則：{js['criteria']}"
        for c in js["criteria"]:
            assert 0 <= c["score"] <= 100
            print(f"    - {c['name']}: {c['score']} — {c['comment'][:40]}...")
        assert len(js["suggestions"]) >= 1, "至少要有一條修改建議"
```

改為：

```python
    for js in result["journal_scores"]:
        print(f"\n▶ {js['journal']}（總分 {js['overall_score']}）")
        assert 0 <= js["overall_score"] <= 100
        assert js["overall_comment"].strip(), "overall_comment 不可為空字串"
        print(f"    總評：{js['overall_comment']}")
        assert len(js["criteria"]) == 6, f"應有 6 項準則：{js['criteria']}"
        for c in js["criteria"]:
            assert 0 <= c["score"] <= 100
            print(f"    - {c['name']}: {c['score']} — {c['comment'][:40]}...")
        assert len(js["suggestions"]) >= 1, "至少要有一條修改建議"
```

Run（於 `backend/` 目錄下，`backend/.env` 內需有有效的 `GEMINI_API_KEY`，已於環境中確認存在）：`python scripts/test_score_paper.py`
Expected: 印出 `測試完成！`，且每個期刊底下都印出「總評：...」那一行，沒有 `AssertionError`。若這步驟因為額度/網路問題無法執行，先跳過，最終 Task 7 的瀏覽器人工驗證仍會實際打這支 API。

- [ ] **Step 7: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/routes/rag.py backend/scripts/test_score_paper.py
git commit -m "feat: add overall_comment field to score_paper() journal results"
```

---

## Task 5: 前端 — `arxiv.ts` 新增 `overallComment` 型別與映射

**Files:**
- Modify: `frontend/src/api/arxiv.ts:94-147`

**Interfaces:**
- Consumes: 無新依賴（純型別/映射修改）
- Produces: `JournalScore.overallComment: string`，供 Task 6（`JournalScoreDialog.vue`）使用

- [ ] **Step 1: 在 `JournalScore` 介面加入欄位**

`frontend/src/api/arxiv.ts` 現況（節錄）：

```ts
export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  criteria: CriterionScore[]
  suggestions: string[]
}
```

改為：

```ts
export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  overallComment: string
  criteria: CriterionScore[]
  suggestions: string[]
}
```

- [ ] **Step 2: 在 `scorePaper()` 的映射中補上該欄位**

現況：

```ts
    journalScores: rawScores.map(js => ({
      journal: String(js.journal ?? ''),
      journalFullName: String(js.journal_full_name ?? ''),
      overallScore: Number(js.overall_score ?? 0),
      criteria: Array.isArray(js.criteria)
```

改為：

```ts
    journalScores: rawScores.map(js => ({
      journal: String(js.journal ?? ''),
      journalFullName: String(js.journal_full_name ?? ''),
      overallScore: Number(js.overall_score ?? 0),
      overallComment: String(js.overall_comment ?? ''),
      criteria: Array.isArray(js.criteria)
```

- [ ] **Step 3: 型別檢查**

Run（於 `frontend/` 目錄下）：`npm run type-check`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/arxiv.ts
git commit -m "feat: map overall_comment field in scorePaper() response"
```

---

## Task 6: 重寫 `JournalScoreDialog.vue`（評分結果彈窗）

對照截圖：`03-modal-jamia-top.png`、`04-modal-jamia-bottom.png`（JAMIA／藍色識別色）、`05-modal-npj-top.png`、`06-modal-npj-bottom.png`（npj／金色識別色）、`07-modal-bmc-top.png`、`08-modal-bmc-bottom.png`（BMC MIDM／teal 識別色）。整個檔案改寫，Props/Emits 介面維持不變（`visible`/`journalScores`/`failedJournals`/`emit('close')`），呼叫端 `PaperPage.vue` 不用改這部分的呼叫方式。

**Files:**
- Modify: `frontend/src/components/paper/JournalScoreDialog.vue`（全檔改寫）

**Interfaces:**
- Consumes:
  - `ScoreRing` from `@/components/paper/ScoreRing.vue`（Task 2）
  - `getScoreColor` from `@/utils/scoreColor`（Task 1）
  - `getJournalAccent` from `@/utils/journalTheme`（Task 1）
  - `type JournalScore` from `@/api/arxiv`，現在含 `overallComment`（Task 5）
- Produces: 同既有介面 `props: { visible: boolean; journalScores: JournalScore[]; failedJournals: string[] }`、`emits: { close: [] }`，供 Task 7 的 `PaperPage.vue` 使用（呼叫端程式碼不需要變動）

- [ ] **Step 1: 整檔改寫 `frontend/src/components/paper/JournalScoreDialog.vue`**

```vue
<template>
  <div
    v-if="visible"
    class="journal-score-backdrop"
    @click.self="emit('close')"
  >
    <div class="journal-score-card">
      <header class="journal-score-header">
        <div class="journal-score-header__text">
          <p class="journal-score-eyebrow" :style="{ color: activeAccent.text }">期刊評分報告</p>
          <h3 class="journal-score-title">Journal Peer Review Simulation</h3>
        </div>
        <button class="journal-score-esc" type="button" @click="emit('close')">ESC</button>
      </header>

      <p v-if="failedJournals.length > 0" class="journal-score-warning">
        <v-icon icon="mdi-alert-outline" size="14" />
        {{ failedJournals.join('、') }} 評分失敗，僅顯示其餘期刊結果
      </p>

      <nav class="journal-score-tabs">
        <button
          v-for="(js, index) in journalScores"
          :key="js.journal"
          class="journal-score-tab"
          :class="{ 'journal-score-tab--active': index === activeIndex }"
          :style="index === activeIndex
            ? { color: getJournalAccent(js.journal).text, borderBottomColor: getJournalAccent(js.journal).main }
            : undefined"
          type="button"
          @click="activeIndex = index"
        >
          {{ js.journal }}
        </button>
      </nav>

      <div v-if="activeJournal" class="journal-score-body">
        <div class="journal-score-overview">
          <ScoreRing :font-size="30" :score="activeJournal.overallScore" :size="104" :stroke-width="9" />

          <div class="journal-score-overview__text">
            <p class="journal-score-overview__name">{{ activeJournal.journalFullName }}</p>
            <p class="journal-score-overview__comment">{{ activeJournal.overallComment }}</p>

            <div class="journal-score-overview__minis">
              <ScoreRing
                v-for="c in activeJournal.criteria.slice(0, 3)"
                :key="c.name"
                :font-size="12"
                :score="c.score"
                :size="40"
                :stroke-width="4"
              />
              <span v-if="activeJournal.criteria.length > 3" class="journal-score-overview__more">
                +{{ activeJournal.criteria.length - 3 }} more
              </span>
            </div>
          </div>
        </div>

        <hr class="journal-score-divider">

        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">逐項評分準則</p>

        <ol class="journal-score-criteria">
          <li
            v-for="(criterion, index) in activeJournal.criteria"
            :key="criterion.name"
            class="journal-score-criterion"
          >
            <div class="journal-score-criterion__head">
              <span class="journal-score-criterion__index">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="journal-score-criterion__name">{{ criterion.name }}</span>
            </div>
            <div class="journal-score-criterion__bar-row">
              <div class="journal-score-criterion__bar">
                <div
                  class="journal-score-criterion__bar-fill"
                  :style="{ width: `${criterion.score}%`, background: getScoreColor(criterion.score) }"
                />
              </div>
              <span class="journal-score-criterion__score" :style="{ color: getScoreColor(criterion.score) }">
                {{ criterion.score }}
              </span>
            </div>
            <p class="journal-score-criterion__comment">{{ criterion.comment }}</p>
          </li>
        </ol>

        <hr class="journal-score-divider">

        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">修改建議</p>

        <ol class="journal-score-suggestions">
          <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index" class="journal-score-suggestion">
            <span class="journal-score-suggestion__index" :style="{ color: activeAccent.text }">
              {{ String(index + 1).padStart(2, '0') }}.
            </span>
            <span class="journal-score-suggestion__text">{{ suggestion }}</span>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import { getJournalAccent } from '@/utils/journalTheme'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = defineProps<{
    visible: boolean
    journalScores: JournalScore[]
    failedJournals: string[]
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const activeIndex = ref(0)

  const activeJournal = computed(() => props.journalScores[activeIndex.value] ?? null)
  const activeAccent = computed(() => getJournalAccent(activeJournal.value?.journal ?? ''))

  function onKeydown (event: KeyboardEvent) {
    if (event.key === 'Escape') emit('close')
  }

  watch(() => props.visible, visible => {
    if (visible) {
      activeIndex.value = 0
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  }, { immediate: true })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown)
  })
</script>

<style scoped>
  .journal-score-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(20, 22, 30, 0.45);
    z-index: 1000;
  }

  .journal-score-card {
    width: 680px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
    overflow: hidden;
  }

  .journal-score-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 20px 24px 0;
    flex-shrink: 0;
  }

  .journal-score-eyebrow {
    margin: 0 0 4px;
    font-size: 11.5px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  .journal-score-title {
    margin: 0;
    font-family: 'Noto Serif TC', Georgia, 'Times New Roman', serif;
    font-size: 22px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-esc {
    flex-shrink: 0;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: none;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #8a8f9c;
    cursor: pointer;
  }

  .journal-score-esc:hover {
    border-color: #b7bcc7;
    color: #4a4f5c;
  }

  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 14px 24px 0;
    padding: 8px 12px;
    border-radius: 8px;
    background: #fff4e5;
    color: #9a5b00;
    font-size: 12px;
    flex-shrink: 0;
  }

  .journal-score-tabs {
    display: flex;
    gap: 20px;
    padding: 18px 24px 0;
    border-bottom: 1px solid #e8ebf1;
    flex-shrink: 0;
  }

  .journal-score-tab {
    border: none;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    color: #8a8f9c;
    cursor: pointer;
  }

  .journal-score-tab--active {
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-body {
    padding: 22px 24px 24px;
    overflow-y: auto;
  }

  .journal-score-overview {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .journal-score-overview__text {
    flex: 1;
    min-width: 0;
  }

  .journal-score-overview__name {
    margin: 0 0 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #8a8f9c;
  }

  .journal-score-overview__comment {
    margin: 0 0 12px;
    font-size: 14.5px;
    line-height: 1.6;
    font-weight: 600;
    color: #1c2130;
  }

  .journal-score-overview__minis {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .journal-score-overview__more {
    font-size: 12px;
    color: #8a8f9c;
  }

  .journal-score-divider {
    margin: 20px 0;
    border: none;
    border-top: 1px solid #e8ebf1;
  }

  .journal-score-section-title {
    margin: 0 0 14px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .journal-score-criteria {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .journal-score-criterion__head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 6px;
  }

  .journal-score-criterion__index {
    font-size: 11px;
    font-weight: 700;
    color: #b7bcc7;
  }

  .journal-score-criterion__name {
    font-size: 13.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-criterion__bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .journal-score-criterion__bar {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: #e8ebf1;
    overflow: hidden;
  }

  .journal-score-criterion__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .journal-score-criterion__score {
    flex-shrink: 0;
    font-size: 13px;
    font-weight: 700;
    min-width: 24px;
    text-align: right;
  }

  .journal-score-criterion__comment {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.65;
    color: #4a4f5c;
  }

  .journal-score-suggestions {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .journal-score-suggestion {
    display: flex;
    gap: 10px;
    border: 1px solid #e8ebf1;
    border-radius: 10px;
    padding: 12px 14px;
  }

  .journal-score-suggestion__index {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 700;
  }

  .journal-score-suggestion__text {
    font-size: 12.5px;
    line-height: 1.65;
    color: #3a3f4a;
  }
</style>
```

> ESC 鍵：除了原本就有的 `@click.self="emit('close')"`（點背景關閉）之外，新增 `window.addEventListener('keydown', ...)` 監聽 `Escape` 鍵並在元件卸載/隱藏時移除，對應截圖右上角的 `ESC` 提示按鈕（`03-modal-jamia-top.png` 右上角）。監聽器只在 `visible === true` 時掛上，避免彈窗關閉後仍佔用全域鍵盤事件。
>
> 期刊識別色 vs. 分數門檻色：`activeAccent`（來自 `getJournalAccent`）只用在「眉標／分頁底線／逐項評分準則標題／修改建議標題／建議編號」這幾個「期刊品牌」相關的地方；圓環與長條的顏色一律用 `getScoreColor`（分數門檻），兩者不要混用，這是對照截圖比對出的規則（見 Global Constraints）。

- [ ] **Step 2: 型別檢查與 lint**

Run（於 `frontend/` 目錄下）：`npm run type-check && npm run lint`
Expected: 兩者皆無錯誤。若 `npm run lint` 對於 `<style>` 內的屬性排序/命名有意見，依 eslint 訊息調整（不要用 `eslint-disable` 繞過）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/JournalScoreDialog.vue
git commit -m "redesign: rebuild JournalScoreDialog to match Figma Make reference"
```

---

## Task 7: `PaperPage.vue` 整合 — 按鈕狀態機、側欄版面、最終驗證

對照截圖：`01-idle.png`（初始按鈕＋佔位卡）、`02-loading.png`（評分中按鈕）、`09-summary-after-close.png`（關閉彈窗後的摘要卡，按鈕文字變 in-scope 的「再次評分」規則見下）。

**Files:**
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes:
  - `JournalScorePanel` from `@/components/paper/JournalScorePanel.vue`（Task 3），props `{ journalScores, scoring }`，emits `openReport`
  - 既有 `JournalScoreDialog`（Task 6 已重寫外觀，props/emits 不變）
  - 既有 `scorePaper`/`JournalScore` from `@/api/arxiv`（Task 5 已補 `overallComment`，呼叫端不需改）
- Produces: 無新對外介面（此為整合層，是 `/paper` 路由的最終畫面）

- [ ] **Step 1: 改造頁首按鈕（圖示、動態文字、手動控制 loading 視覺）**

`frontend/src/views/PaperPage.vue:15-24` 現況：

```vue
        <v-btn
          class="score-btn"
          :loading="scoring"
          prepend-icon="mdi-school-outline"
          size="small"
          variant="tonal"
          @click="handleScorePaper"
        >
          期刊評分
        </v-btn>
```

改為：

```vue
        <v-btn
          class="score-btn"
          :disabled="scoring"
          size="small"
          variant="tonal"
          @click="handleScorePaper"
        >
          <template #prepend>
            <v-icon :class="{ 'mdi-spin': scoring }" :icon="scoring ? 'mdi-loading' : 'mdi-star'" />
          </template>
          {{ scoreButtonLabel }}
        </v-btn>
```

> 不用 `v-btn` 內建的 `:loading` 是因為 Vuetify 預設會把按鈕內容整個蓋掉、只顯示置中轉圈圈，文字會消失；但截圖 `02-loading.png` 是「轉圈圈圖示 + `評分中...` 文字」同時並存，所以改成手動控制圖示（`mdi-loading` 配 `.mdi-spin`，這是 `@mdi/font` 內建的旋轉動畫 class，不用額外寫 `@keyframes`）與 `:disabled` 防止重複點擊。

- [ ] **Step 2: 加入按鈕文字狀態機的 computed**

在 `frontend/src/views/PaperPage.vue` 的 `<script setup>` 區塊，`const failedJournals = ref<string[]>([])` 之後（第 90 行後）新增：

```ts
  const scoreButtonLabel = computed(() => {
    if (scoring.value) return '評分中...'
    return journalScores.value.length > 0 ? '再次評分' : '期刊評分'
  })
```

並在檔案頂部的 import 中把 `ref` 改成同時引入 `computed`：

現況（第 63 行）：
```ts
  import { onMounted, ref } from 'vue'
```

改為：
```ts
  import { computed, onMounted, ref } from 'vue'
```

- [ ] **Step 3: 在側欄插入 `JournalScorePanel`，並把 `paper-citations` 的版面容器從 `CitationPanel` 移到外層 wrapper**

`frontend/src/views/PaperPage.vue:44-49` 現況：

```vue
        <CitationPanel
          :active-citation-id="activeCitationId"
          :citations="report.citations"
          class="paper-citations"
          @select="onPanelSelect"
        />
```

改為：

```vue
        <div class="paper-citations">
          <JournalScorePanel
            :journal-scores="journalScores"
            :scoring="scoring"
            @open-report="scoreDialogVisible = true"
          />
          <CitationPanel
            :active-citation-id="activeCitationId"
            :citations="report.citations"
            @select="onPanelSelect"
          />
        </div>
```

加入 import（第 66-69 行區域，依現有字母排序風格插入）：

現況：
```ts
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
```

改為：
```ts
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import JournalScorePanel from '@/components/paper/JournalScorePanel.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
```

- [ ] **Step 4: 調整 CSS ── `.paper-citations` 改成 flex 直排容器（原本套用在 `CitationPanel` 上的 sticky/寬度樣式現在要套在外層 wrapper）**

`frontend/src/views/PaperPage.vue:212-220` 現況：

```css
  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
  }
```

改為（新增 `display: flex; flex-direction: column; gap: 16px;`，讓 `JournalScorePanel` 卡片和 `CitationPanel` 之間有間距）：

```css
  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
```

> `CitationPanel.vue` 內部的 `.citation-panel { display:flex; flex-direction:column; gap:12px }`（引用卡片之間的間距）不受影響，因為那是它自己 scoped 的內層樣式，這裡改的是外層新 wrapper 的排版。

- [ ] **Step 5: 型別檢查與 lint**

Run（於 `frontend/` 目錄下）：`npm run type-check && npm run lint`
Expected: 兩者皆無錯誤

- [ ] **Step 6: 啟動前後端，於瀏覽器人工比對全部 9 張截圖**

Run：

```bash
docker compose up -d backend frontend
```

（若本機已用其他方式跑著 dev server 則不需要 docker，直接沿用現有跑法即可；重點是 backend 需要載入 `backend/.env` 裡的 `GEMINI_API_KEY`。）

在瀏覽器開啟 `http://localhost:5173/paper`（沒有先跑過 arXiv 生成流程時，`PaperPage.vue` 會自動 fallback 顯示 `mockPaperReport`，可以直接測，不需要跑完整流程）。

比對檢查清單（逐項核對，對照 `docs/superpowers/plans/assets/2026-08-08-journal-score-ui/`）：
1. 對照 `01-idle.png`：頁首右上是金色 `★ 期刊評分` 按鈕；右側欄最上方是白色佔位卡（星形圖示、`JAMIA`/`npj Digital Medicine`/`BMC MIDM` 為粗體的說明文字、下方藍色小字 `3 個期刊 · 6 項準則 · AI 評分`）。
2. 點擊「期刊評分」，對照 `02-loading.png`：按鈕變成不可點擊、圖示轉圈圈、文字變 `評分中...`；右側佔位卡內容不變。
3. 評分完成後彈窗自動開啟，依序切換 3 個分頁，對照 `03`–`08`：
   - JAMIA 分頁底線與「期刊評分報告」字樣是藍色，npj 是金色，BMC MIDM 是 teal 色（`getJournalAccent` 是否正確依期刊名稱切換，尤其注意如果有期刊評分失敗、`journalScores` 少一筆時顏色不會跑掉）。
   - 大圓環與逐項準則的長條顏色只依分數門檻變色（`>=80` teal、`<80` 金色），不受目前分頁的期刊識別色影響。
   - 大圓環右側有 `overallComment` 一句總評文字（確認不是空字串，Task 4/5 有正確串接）。
   - 3 個小圓環 + `+3 more` 正確顯示（6 項準則時應顯示 `+3 more`）。
   - 按右上角 `ESC` 按鈕、按鍵盤 Escape 鍵、點背景，三種方式都能關閉彈窗。
4. 關閉彈窗後，對照 `09-summary-after-close.png`：右側欄佔位卡變成「評分摘要」卡（含 avg 小圓環、3 期刊各一行含分數與色條、底部「查看完整評分報告 →」按鈕），且頁首按鈕文字變成 `再次評分`。
5. 點擊「查看完整評分報告 →」，確認會重新打開同一份彈窗結果（不會重新呼叫 API）。
6. 再點一次頁首的「再次評分」按鈕，確認會重新呼叫 API、loading 態文字/圖示正確，成功後彈窗結果與摘要卡都用新的一輪分數更新。
7. 確認論文內文（`paper-sheet`）與引用面板（`CitationPanel` 卡片點擊高亮/捲動）行為與改動前完全一致，沒有被誤動到。

若步驟 6 因為 Gemini 額度或網路問題無法完整跑完，至少完成步驟 1–2（不需要打 API）與型別檢查，並在交付說明中明確註記「未完成真實 API 的端對端視覺驗證」。

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "redesign: wire journal score button states and sidebar panel into PaperPage"
```

---

## Self-Review Notes

- **Spec 覆蓋**：按鈕（idle/loading/re-score 三態）✅ Task 7、佔位卡 ✅ Task 3、評分摘要卡 ✅ Task 3、彈窗（眉標/標題/ESC/分頁/大圓環/一句總評/小圓環+more/逐項準則長條/修改建議編號卡）✅ Task 6、「再次評分」文案規則 ✅ Task 7 Step 2、範圍鎖定（不動論文內文與引用面板行為）✅ Task 7 Step 3-4 只調整外層 wrapper。
- **型別一致性**：`JournalScore.overallComment`（Task 5）與 `JournalScoreDialog.vue` 內 `activeJournal.overallComment`（Task 6）、`test_score_paper.py` 的 `js["overall_comment"]`（Task 4）三處欄位命名（camelCase vs snake_case）已核對一致。`ScoreRing` 的 props（`score`/`size`/`strokeWidth`/`fontSize`）在 Task 2 定義後，Task 3/Task 6 的所有呼叫處都用同樣的 prop 名稱（Vue 範本內用 kebab-case `stroke-width`/`font-size`，對應 script 端的 camelCase，屬 Vue 慣例非命名不一致）。
- **無佔位符**：所有程式碼區塊皆為可直接套用的完整內容，無 `TODO`/`實作細節略`。

