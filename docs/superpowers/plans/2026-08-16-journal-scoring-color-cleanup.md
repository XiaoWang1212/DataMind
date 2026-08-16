# Journal Scoring 顏色收斂 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收斂期刊評分報告（`JournalScoreDialog.vue` / `JournalScorePanel.vue` / `ScoreRing.vue`）目前疊在一起的兩套顏色系統——分數高低二元色（綠/金黃）跟期刊各自的識別色——改成統一的品牌藍，同時拿掉彈窗的玻璃背景、警告黃底、修改建議的邊框。

**Architecture:** 純前端樣式收斂，不動任何資料流或後端。`utils/scoreColor.ts` 改成回傳固定色；`utils/journalTheme.ts` 整個刪除；`JournalScoreDialog.vue`／`JournalScorePanel.vue` 的 template 拿掉讀取這兩個 util 的 inline style，改成 scoped CSS 固定值。

**Tech Stack:** Vue 3 `<script setup>`，既有 `styles/tailwind.css` 的 `--color-*` design token。

## Global Constraints

- 不動分數/評分邏輯本身（後端算分方式），只動顏色呈現（見 spec「範圍外」）。
- `chartColors.ts` 與論文結構化圖表顏色不在這次範圍內，不要動。
- 沒有自動化測試（`CLAUDE.md`：no automated test suite），每個 task 用 `npm run build`（含 vue-tsc 型別檢查）驗證，外加人工在瀏覽器核對視覺結果。
- Commit 訊息一行、英文。

---

### Task 1: `scoreColor.ts` 改成固定回傳品牌藍

**Files:**
- Modify: `frontend/src/utils/scoreColor.ts`

**Interfaces:**
- Consumes: 無（獨立 util，不依賴其他 task）
- Produces: `getScoreColor(score: number): string` — 簽名不變，回傳值固定是 `'var(--color-accent)'`。後續 task（`ScoreRing.vue`、`JournalScorePanel.vue`、`JournalScoreDialog.vue`）都已經在呼叫這個函式，不用改呼叫端。

現在的內容（全檔案）：

```ts
// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80
export const SCORE_COLOR_HIGH = 'var(--color-success)'
export const SCORE_COLOR_LOW = 'var(--color-warning)'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? SCORE_COLOR_HIGH : SCORE_COLOR_LOW
}
```

- [ ] **Step 1: 確認沒有其他地方直接用到 `SCORE_THRESHOLD`/`SCORE_COLOR_HIGH`/`SCORE_COLOR_LOW`**

Run: `grep -rn "SCORE_THRESHOLD\|SCORE_COLOR_HIGH\|SCORE_COLOR_LOW" frontend/src`
Expected: 只有 `frontend/src/utils/scoreColor.ts` 自己的定義與使用，沒有其他檔案 import 這三個 named export（只有 `getScoreColor` 被外部使用）。如果掃出其他檔案有用到，先記下來，Step 2 的改法要連那個呼叫端一起處理（目前程式庫狀態下不會發生）。

- [ ] **Step 2: 改寫成固定色**

```ts
// frontend/src/utils/scoreColor.ts
// 分數不分高低，統一用品牌藍——曾經是「≥80 綠色/其餘金黃色」的二元判斷，
// 但多數分數落在 80 以下，金黃色佔滿畫面，跟評分失敗的警告色也撞在一起。
const SCORE_COLOR = 'var(--color-accent)'

export function getScoreColor (_score: number): string {
  return SCORE_COLOR
}
```

參數名加底線前綴（`_score`）是因為函式內部不再用它，只是保留簽名相容既有呼叫端；ESLint 的 `no-unused-vars` 對底線開頭的參數通常會放行（沿用本專案既有慣例，跟 `id, projectId` 這類未用參數的處理方式一致）。

- [ ] **Step 3: 執行 build 驗證型別與語法**

Run: `cd frontend && npm run build`
Expected: 成功，無 TypeScript 錯誤（`getScoreColor` 呼叫端全部是 `getScoreColor(someNumber)`，簽名沒變，不會出現型別錯誤）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/scoreColor.ts
git commit -m "style(paper): make score color a fixed brand blue"
```

---

### Task 2: 刪除 `journalTheme.ts`，`JournalScoreDialog.vue` 期刊識別色改統一品牌藍

**Files:**
- Delete: `frontend/src/utils/journalTheme.ts`
- Modify: `frontend/src/components/paper/JournalScoreDialog.vue`

**Interfaces:**
- Consumes: 無
- Produces: 無新介面。`JournalScoreDialog.vue` 之後不再 import `journalTheme.ts`，任何後續 task 都不能再假設這個 util 存在。

**現況（`JournalScoreDialog.vue` 相關片段）：**

Template（第 7-37 行、第 67 行、第 96 行、第 100-102 行）：

```vue
    <div class="journal-score-card glass-panel">
      <header class="journal-score-header">
        <div class="journal-score-header__text">
          <p class="journal-score-eyebrow" :style="{ color: activeAccent.text }">期刊評分報告</p>
          <h3 class="journal-score-title">Journal Peer Review Simulation</h3>
        </div>
        ...
      </header>

      ...

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
```

```vue
        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">逐項評分準則</p>
```

```vue
        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">修改建議</p>

        <ol class="journal-score-suggestions">
          <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index" class="journal-score-suggestion">
            <span class="journal-score-suggestion__index" :style="{ color: activeAccent.text }">
              {{ String(index + 1).padStart(2, '0') }}.
            </span>
```

Script（第 111-132 行）：

```ts
  import type { JournalScore } from '@/api/arxiv'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import AppButton from '@/components/ui/AppButton.vue'
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
```

- [ ] **Step 1: 刪除 `journalTheme.ts`**

```bash
rm frontend/src/utils/journalTheme.ts
```

- [ ] **Step 2: 拿掉 script 裡的 import 與 `activeAccent`**

```ts
  import type { JournalScore } from '@/api/arxiv'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import AppButton from '@/components/ui/AppButton.vue'
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
```

（`getJournalAccent` import 整行刪除；`activeAccent` computed 整段刪除。）

- [ ] **Step 3: Template — 分頁籤選中狀態改純 class，不用 inline style**

把：

```vue
          :style="index === activeIndex
            ? { color: getJournalAccent(js.journal).text, borderBottomColor: getJournalAccent(js.journal).main }
            : undefined"
```

整行刪除（`journal-score-tab` 這個 `<button>` 不再需要 `:style` 綁定，選中狀態完全交給 `.journal-score-tab--active` 這個 class 的 CSS 規則）。

- [ ] **Step 4: Template — 其餘 4 處 `:style="{ color: activeAccent.text }"` 全部刪除**

- 第 10 行 `.journal-score-eyebrow`：`<p class="journal-score-eyebrow">期刊評分報告</p>`（拿掉 `:style`）
- 第 67 行 `.journal-score-section-title`（逐項評分準則）：`<p class="journal-score-section-title">逐項評分準則</p>`
- 第 96 行 `.journal-score-section-title`（修改建議）：`<p class="journal-score-section-title">修改建議</p>`
- 第 100-102 行 `.journal-score-suggestion__index`：

```vue
            <span class="journal-score-suggestion__index">
              {{ String(index + 1).padStart(2, '0') }}.
            </span>
```

- [ ] **Step 5: CSS — 這 4 個 class 加上固定的 `color: var(--color-accent)`，並補上分頁籤選中狀態的顏色**

找到 `<style scoped>` 裡對應的規則，改成：

```css
  .journal-score-eyebrow {
    margin: 0 0 4px;
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.01em;
    color: var(--color-accent);
  }
```

```css
  .journal-score-tab--active {
    font-weight: 500;
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
  }
```

```css
  .journal-score-section-title {
    margin: 0 0 14px;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-accent);
  }
```

```css
  .journal-score-suggestion__index {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-accent);
  }
```

（`.journal-score-section-title` 只有一份 CSS 規則、被兩處 template 共用，改一次即可。）

- [ ] **Step 6: 全站搜尋確認沒有其他地方還在用 `journalTheme`**

Run: `grep -rn "journalTheme\|getJournalAccent" frontend/src`
Expected: 沒有任何結果（`journalTheme.ts` 已刪除，`JournalScoreDialog.vue` 已經拿掉所有引用）。

- [ ] **Step 7: 執行 build 驗證**

Run: `cd frontend && npm run build`
Expected: 成功。如果報 `activeAccent`/`getJournalAccent` 未定義的錯誤，回頭檢查 Step 2-4 是否有漏改的地方。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/utils/journalTheme.ts frontend/src/components/paper/JournalScoreDialog.vue
git commit -m "style(paper): drop per-journal accent colors, unify to brand blue"
```

---

### Task 3: `JournalScoreDialog.vue` — 實色白底彈窗、警告拿掉黃底、建議拿掉框框

**Files:**
- Modify: `frontend/src/components/paper/JournalScoreDialog.vue`

**Interfaces:**
- Consumes: Task 2 完成後的 `JournalScoreDialog.vue`（這個 task 只動 CSS，不再碰 script/import）
- Produces: 無新介面

這個 task 只改 `<style scoped>` 區塊跟一處 class 綁定，template 的其他部分不動。

**現況：**

```vue
      <p v-if="failedJournals.length > 0" class="journal-score-warning">
```

```css
  .journal-score-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(18, 30, 58, 0.45);
    z-index: 1000;
  }

  /* 底色、邊框、圓角、陰影由 .glass-panel 提供，在這裡重寫會蓋掉玻璃 */
  .journal-score-card {
    width: 680px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
```

```css
  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 14px 24px 0;
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    background: var(--color-warning-bg);
    color: var(--color-warning-text);
    font-size: 12px;
    flex-shrink: 0;
  }
```

```css
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
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: 12px 14px;
  }
```

- [ ] **Step 1: Template — `.journal-score-card` 拿掉 `glass-panel` class**

```vue
    <div class="journal-score-card">
```

- [ ] **Step 2: CSS — `.journal-score-card` 自己補上實色底/圓角/陰影**

```css
  .journal-score-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(18, 30, 58, 0.45);
    z-index: 1000;
  }

  /* 實色白底，不套玻璃：backdrop-filter 疊在深色遮罩前面會把深色一起模糊進來，
     顏色會偏濁。跟 2026-08-15 workflow canvas 同一個判斷 */
  .journal-score-card {
    width: 680px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
  }
```

- [ ] **Step 3: CSS — `.journal-score-warning` 拿掉黃底色塊，改純文字＋icon**

```css
  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 14px 24px 0;
    color: var(--color-warning-text);
    font-size: 12px;
    font-weight: 500;
    flex-shrink: 0;
  }
```

（拿掉 `padding`、`border-radius`、`background`；`color` 保留 `--color-warning-text`——這是真的警告事件，語意保留，只是不再整塊上色。）

- [ ] **Step 4: CSS — `.journal-score-suggestion` 拿掉框框，用間距分隔**

```css
  .journal-score-suggestions {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .journal-score-suggestion {
    display: flex;
    gap: 10px;
  }
```

（`gap` 從 10px 加大到 16px，扛起原本靠邊框分隔的視覺責任；`border`/`border-radius`/`padding` 三行整個拿掉。）

- [ ] **Step 5: 執行 build 驗證**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/paper/JournalScoreDialog.vue
git commit -m "style(paper): solid dialog background, drop warning fill and suggestion borders"
```

---

### Task 4: `JournalScorePanel.vue` — 修正兩處誤用 warning 色的裝飾

**Files:**
- Modify: `frontend/src/components/paper/JournalScorePanel.vue`

**Interfaces:**
- Consumes: 無（獨立於前三個 task，可以任何順序做，但排在最後方便跟 Task 1-3 一起验收）
- Produces: 無新介面

**現況（第 4-11 行、第 130-135 行）：**

```vue
    <div v-if="journalScores.length === 0" class="score-panel-empty">
      <div class="score-panel-empty__icon">
        <v-icon color="var(--color-warning-text)" icon="mdi-star" size="22" />
      </div>
      <p class="score-panel-empty__text">
        點擊「期刊評分」按鈕，以 <strong>JAMIA</strong>、<strong>npj Digital Medicine</strong>、<strong>BMC MIDM</strong> 的審稿標準評估本文
      </p>
      <p class="score-panel-empty__meta">3 個期刊 · 6 項準則 · AI 評分</p>
    </div>
```

```css
  .score-panel-empty__icon {
    width: 44px;
    height: 44px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-warning-bg);
    border-radius: var(--radius-md);
  }
```

```css
  .score-panel-summary__title {
    margin: 0 0 10px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--color-warning-text);
  }
```

- [ ] **Step 1: Template — 空狀態星星 icon 顏色改中性灰**

```vue
        <v-icon color="var(--color-ink-soft)" icon="mdi-star" size="22" />
```

- [ ] **Step 2: CSS — 空狀態 icon 底色改中性淺灰**

```css
  .score-panel-empty__icon {
    width: 44px;
    height: 44px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-surface-alt);
    border-radius: var(--radius-md);
  }
```

- [ ] **Step 3: CSS — 「評分摘要」標題文字改中性色**

```css
  .score-panel-summary__title {
    margin: 0 0 10px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--color-text);
  }
```

- [ ] **Step 4: 執行 build 驗證**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/JournalScorePanel.vue
git commit -m "style(paper): stop reusing warning color for panel decoration"
```

---

## 整批驗收（所有 task 完成後）

- `npm run build`（含 vue-tsc）與 `npm run lint` 都要過。
- 瀏覽器實際打開一次期刊評分報告（`ResultView`/`PaperPage` 裡觸發 `JournalScoreDialog` 的入口），核對：
  - `ScoreRing`、進度條、分數數字統一是品牌藍，不再有綠/金黃區分
  - JAMIA / npj Digital Medicine / BMC MIDM 三個分頁籤外觀完全一致，只有文字不同
  - 彈窗底是不透明白色，背後看不到深色透出來的濁感
  - 「評分失敗」訊息沒有黃底色塊，只有文字+icon
  - 「修改建議」每條沒有邊框，靠間距分隔
  - `JournalScorePanel.vue` 空狀態跟「評分摘要」標題不再是黃色系
