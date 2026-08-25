# UI 回饋批次（checkbox／AI 骨架屏／品牌識別／文案／專案詳情）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一次處理五項互相獨立的前端調整：自刻 checkbox、result 頁 AI 分析載入骨架屏、品牌 logo／favicon 落地、產出物文案由「論文」改為「技術報告」、專案詳情頁改顯示最佳模型與流程摘要。

**Architecture:** 全部是既有頁面內的前端改動，不動後端、不動路由、不動資料庫。兩處需要抽共用程式碼：最佳模型計算從 `ResultView.vue` 抽到 `utils/workflow/`（兩頁共用），前處理／特徵工程的中文標籤表從 `SettingsPanel.vue` 抽到 `constants/`（兩處共用）。新增一個 `AppCheckbox` 進既有的 `components/ui/` 元件組。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript、Vuetify 4、Tailwind 4、Vite。樣式一律 scoped CSS + 設計 token（`--color-*`／`--radius-*`），不用 Vuetify 的 `v-checkbox`。

**Spec:** 無獨立 spec 檔。本批屬 bounded 範圍，需求與設計取捨來自 2026-08-25 與使用者的討論，逐項寫在下列任務的「背景」段。

## Global Constraints

- 使用者可見文案、註解、文件一律繁體中文；程式碼識別字（變數、函式、CSS class、檔名）用英文。
- 註解風格：一律 `//`（CSS 內用 `/* */`）、平實直述、精簡，不重述程式碼在做什麼，只寫「為什麼」。不用口語。
- 顏色一律走設計 token，禁止寫死色碼。可用的品牌 token：`--color-ink`、`--color-ink-strong`、`--color-ink-vivid`、`--color-ink-soft`、`--color-surface`、`--color-surface-alt`、`--color-border`、`--color-border-strong`、`--color-text`、`--text-secondary`。圓角用 `--radius-sm`（8px）／`--radius-md`（12px）／`--radius-lg`（16px）。
- 本專案沒有自動化測試。每個任務的驗收是：`npm run build`（含 `vue-tsc` 型別檢查）與 `npm run lint` 都要通過，再加上人工看畫面。
- **不要 `git commit` 或 `git push`。** 每個任務做完就停下來回報，等使用者看過畫面確認。commit 訊息屆時由使用者點頭後再下，格式為單行、不加 `Co-Authored-By` trailer。
- 前端指令一律在 `frontend/` 目錄下執行。

---

### Task 1: 自刻 checkbox 元件並套用到參考文獻選擇

**背景：** 參考文獻挑選清單目前用的是瀏覽器原生 `<input type="checkbox">`，外觀是作業系統預設樣式，跟整站的藏青設計語彙完全脫節。

**Files:**
- Create: `frontend/src/components/ui/AppCheckbox.vue`
- Modify: `frontend/src/views/PaperSourcesView.vue`（template 第 60-75 行附近、script import 區、style 區）

**Interfaces:**
- Consumes: 無（本任務不依賴其他任務）
- Produces: `AppCheckbox` 元件，`v-model` 綁 `boolean`。Props：`modelValue: boolean`、`disabled?: boolean`（預設 `false`）、`ariaLabel?: string`。Emit：`update:modelValue` 帶 `boolean`。後續任務不依賴它。

**注意：** `PaperSourcesView.vue` 目前的 `selectedIds` 是字串陣列，原生 checkbox 用 `v-model` + `:value` 做陣列收集。`AppCheckbox` 只吃 `boolean`，所以套用時要改成「算出這一筆有沒有被選 → 由事件自己增刪陣列」。這是本任務唯一有邏輯風險的地方，Step 3 有完整程式碼。

- [ ] **Step 1: 建立 `AppCheckbox.vue`**

建立 `frontend/src/components/ui/AppCheckbox.vue`，內容如下：

```vue
<template>
  <span class="app-checkbox" :class="{ 'app-checkbox--disabled': disabled }">
    <input
      :aria-label="ariaLabel"
      :checked="modelValue"
      class="app-checkbox-input"
      :disabled="disabled"
      type="checkbox"
      @change="onChange"
    >
    <span aria-hidden="true" class="app-checkbox-box">
      <svg class="app-checkbox-tick" viewBox="0 0 16 16">
        <path
          d="M3.5 8.5 L6.5 11.5 L12.5 4.5"
          fill="none"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2.2"
        />
      </svg>
    </span>
  </span>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    modelValue: boolean
    disabled?: boolean
    ariaLabel?: string
  }>(), {
    disabled: false,
    ariaLabel: undefined,
  })

  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
  }>()

  function onChange (event: Event): void {
    emit('update:modelValue', (event.target as HTMLInputElement).checked)
  }
</script>

<style scoped>
  .app-checkbox {
    position: relative;
    display: inline-flex;
    flex: none;
    width: 18px;
    height: 18px;
  }

  /* 原生 input 疊在方框上並保持可聚焦，鍵盤操作與表單語意才不會斷掉 */
  .app-checkbox-input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    opacity: 0;
    cursor: pointer;
  }

  .app-checkbox-input:disabled {
    cursor: not-allowed;
  }

  .app-checkbox-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    border: 1.5px solid var(--color-border-strong);
    border-radius: 5px;
    background: var(--color-surface);
    transition: background-color 140ms ease, border-color 140ms ease;
  }

  .app-checkbox-tick {
    width: 14px;
    height: 14px;
    color: #fff;
    opacity: 0;
    transform: scale(0.7);
    transition: opacity 140ms ease, transform 140ms ease;
  }

  .app-checkbox-input:hover:not(:disabled) + .app-checkbox-box {
    border-color: var(--color-ink);
  }

  .app-checkbox-input:checked + .app-checkbox-box {
    border-color: var(--color-ink);
    background: var(--color-ink);
  }

  .app-checkbox-input:checked + .app-checkbox-box .app-checkbox-tick {
    opacity: 1;
    transform: scale(1);
  }

  .app-checkbox-input:focus-visible + .app-checkbox-box {
    outline: 2px solid var(--color-ink-vivid);
    outline-offset: 2px;
  }

  .app-checkbox--disabled .app-checkbox-box {
    opacity: 0.45;
  }
</style>
```

- [ ] **Step 2: 型別檢查通過**

Run: `cd frontend && npm run build`
Expected: 通過，無 `vue-tsc` 錯誤。

- [ ] **Step 3: 在 `PaperSourcesView.vue` 換掉原生 checkbox**

把 template 中 `<li class="candidate-card">` 內的 `<label class="candidate-select">` 區塊（原生 `<input v-model="selectedIds" type="checkbox" :value="candidate.arxiv_id">` 那段）換成：

```vue
<label class="candidate-select">
  <AppCheckbox
    :aria-label="`選擇 ${candidate.title}`"
    :model-value="selectedIds.includes(candidate.arxiv_id)"
    @update:model-value="toggleCandidate(candidate.arxiv_id, $event)"
  />
  <div class="candidate-body">
    <p class="candidate-title">{{ candidate.title }}</p>
    <p class="candidate-meta">
      {{ candidate.authors }}
      <span v-if="candidate.year">({{ candidate.year }})</span>
    </p>
    <p class="candidate-abstract">{{ candidate.abstract }}</p>
  </div>
</label>
```

在 `<script setup>` 的 import 區加上（依現有 import 的字母順序插入 `@/components/ui/` 那一群）：

```ts
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
```

在 script 中 `selectedIds` 宣告之後加上：

```ts
function toggleCandidate (arxivId: string, checked: boolean): void {
  selectedIds.value = checked
    ? [...selectedIds.value, arxivId]
    : selectedIds.value.filter(id => id !== arxivId)
}
```

在 `.candidate-select` 的樣式規則中，把 `align-items: flex-start` 保持不變，另外在該規則後面新增一條讓方框與標題首行對齊：

```css
/* checkbox 是固定 18px，標題行高比它高，往下推齊視覺基線 */
.candidate-select :deep(.app-checkbox) {
  margin-top: 2px;
}
```

- [ ] **Step 4: 驗收**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。

人工檢查（開 `npm run dev`，走到產出參考文獻挑選頁）：
1. 未選取時方框是白底細邊框，hover 邊框轉藏青。
2. 點擊後方框填滿藏青、出現白色勾號，有短促的縮放動畫。
3. 用 Tab 鍵可以聚焦到方框，出現外框光暈；按空白鍵可切換選取。
4. 底部按鈕的計數 `(N)` 隨勾選正確增減，取消勾選會減回去。

- [ ] **Step 5: 停下回報**

不要 commit。回報畫面截圖給使用者確認。

---

### Task 2: result 頁 AI 分析載入骨架屏

**背景：** result 頁的「AI 結構化分析」在生成期間只顯示一行「正在生成分析...」純文字，等待期間版面是空的，載入完成時四個區塊突然出現、版面高度會跳。

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue`（template 第 93 行的 `analysis-loading` 段、style 區的 `.analysis-loading` 規則）

**Interfaces:**
- Consumes: 全域 `.skeleton-line`（定義在 `frontend/src/styles/motion.css:27`，已有 4s 掃光動畫）
- Produces: 無（純樣式改動，不對外暴露）

**注意：** 全域 `.skeleton-line` 的掃光是白色亮帶配 `--color-ink` 10% 的底，已經是專案調校過的速度，不要另外定義新的 keyframes 或改 timing。

- [ ] **Step 1: 換掉載入文字**

在 `frontend/src/views/hub/ResultView.vue` 的 template 中，把這一行：

```vue
<p v-if="analysisLoading" class="analysis-loading">正在生成分析...</p>
```

換成：

```vue
<div v-if="analysisLoading" aria-label="正在生成分析" class="analysis-grid" role="status">
  <!-- 骨架用與真實內容相同的 grid 與區塊高度，載入完換上真值時版面不跳 -->
  <div v-for="n in 4" :key="n" class="analysis-block analysis-block--skeleton">
    <div class="skeleton-line skeleton-heading" />
    <div class="skeleton-line" style="width: 100%" />
    <div class="skeleton-line" style="width: 92%" />
    <div class="skeleton-line" style="width: 68%" />
  </div>
</div>
```

- [ ] **Step 2: 加上骨架區塊樣式**

在 `frontend/src/views/hub/ResultView.vue` 的 `<style>` 區塊中，把原本的 `.analysis-loading` 規則整條刪掉（它已無使用者），並在 `.analysis-block p` 規則之後新增：

```css
.analysis-block--skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 標題條比內文條短且深一階，骨架的層次要對應真實內容的標題／內文關係 */
.analysis-block--skeleton .skeleton-heading {
  width: 42%;
  height: 13px;
  margin-bottom: 2px;
}

.analysis-block--skeleton .skeleton-line:not(.skeleton-heading) {
  height: 11px;
}
```

- [ ] **Step 3: 驗收**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。lint 不應出現 `.analysis-loading` 未使用的殘留。

人工檢查（開一個已完成、且尚未快取過分析結果的專案的結果頁；必要時清掉 localStorage 中該專案的結構化分析快取以重現載入狀態）：
1. 載入期間出現 2×2 四個骨架區塊，每塊一條短標題條加三條內文條。
2. 掃光由右往左緩慢移動，速度與其他頁面的骨架屏一致。
3. 載入完成換上真實內容時，卡片高度不應有明顯跳動。

- [ ] **Step 4: 停下回報**

不要 commit。回報畫面給使用者確認，特別確認「載入完成瞬間版面有沒有跳」。

---

### Task 3: 品牌 logo 與 favicon 落地

**背景：** 瀏覽器分頁目前顯示 Vuetify 的預設 favicon 與「Welcome to Vuetify 4」標題；`src/assets/` 下的 logo 也還是 Vuetify 的 V 字。使用者已把新的品牌識別（深藏青六角形內含亮藍腦圖）放進 `frontend/public/`，需要就定位。側邊欄不加 logo。

**Files:**
- Move: `frontend/public/datamind.ico` → `frontend/public/favicon.ico`（覆蓋現有的 Vuetify 版本）
- Move: `frontend/public/logo.png` → `frontend/src/assets/logo.png`（覆蓋現有的 Vuetify 版本）
- Delete: `frontend/src/assets/logo.svg`
- Modify: `frontend/index.html`
- Modify: `frontend/src/views/LoginView.vue`（template 標題上方、style 區）
- Modify: `frontend/src/views/RegisterView.vue`（同上）

**Interfaces:**
- Consumes: 無
- Produces: `@/assets/logo.png` 成為全站唯一的品牌圖檔來源。

**注意：**
- `public/` 的檔案不經 Vite 處理（不壓縮、不加 content hash），只適合放 favicon 這種必須用固定路徑取得的檔案。元件裡要用的圖必須放 `src/assets/` 才會被打包最佳化。
- `src/assets/logo.png` 目前已被 `frontend/src/components/Introduction.vue:8` 以 `@/assets/logo.png` 引用，覆蓋檔案後該處自動生效，**不需要改它**。
- `src/assets/logo.svg` 全專案無人引用（已確認），可直接刪除。使用者沒有提供新的 SVG，不要自行重繪。

- [ ] **Step 1: 檔案就定位**

Run:
```bash
cd frontend
mv -f public/datamind.ico public/favicon.ico
mv -f public/logo.png src/assets/logo.png
rm src/assets/logo.svg
```

驗證：
```bash
cd frontend && file public/favicon.ico src/assets/logo.png && ls public/ src/assets/
```
Expected: `favicon.ico` 是 `MS Windows icon resource - 3 icons, 16x16 ... 32x32`；`logo.png` 是 `PNG image data, 1000 x 1000`。`public/` 只剩 `favicon.ico`，`src/assets/` 只剩 `logo.png`。

- [ ] **Step 2: 改 `index.html`**

把 `frontend/index.html` 整份換成：

```html
<!DOCTYPE html>
<html lang="zh-TW">
  <head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico" sizes="any">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataMind</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 3: 登入與註冊頁加上 logo**

在 `frontend/src/views/LoginView.vue` 中，把 `<h1 class="auth-title">登入</h1>` 這一行之前插入：

```vue
<img alt="DataMind" class="auth-logo" src="@/assets/logo.png">
```

在該檔 `<style>` 區的 `.auth-title` 規則之前新增：

```css
.auth-logo {
  display: block;
  width: 52px;
  height: 52px;
  margin: 0 auto 12px;
  object-fit: contain;
}
```

在 `frontend/src/views/RegisterView.vue` 做完全相同的兩處改動（該檔的標題行是 `<h1 class="auth-title">註冊</h1>` 或相近文字，插在它之前）。

- [ ] **Step 4: 驗收**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。build 不應出現找不到 `@/assets/logo.svg` 的錯誤（確認沒有殘留引用）。

Run: `cd frontend && grep -rn "logo.svg" src/ index.html`
Expected: 無輸出。

人工檢查（`npm run dev`）：
1. 瀏覽器分頁顯示腦圖 icon，標題是「DataMind」。若看到舊 icon，強制重整（Cmd+Shift+R）—— favicon 快取很黏。
2. 登入頁與註冊頁標題上方置中出現 logo。
3. 教學頁（`/tutorial`）的 logo 已換成腦圖，不再是 Vuetify V 字。

- [ ] **Step 5: 停下回報**

不要 commit。回報三處畫面給使用者確認。側邊欄刻意不加 logo（使用者已明確表示不需要）。

---

### Task 4: 產出物文案改為「技術報告」

**背景：** 系統會依實驗結果產出一份文件，介面上一律稱之為「論文」，但它實際上是實驗結果報告，與使用者上傳的那篇研究論文是兩回事，同一個詞指兩件事造成混淆。

**Files:**
- Modify: `frontend/src/views/PaperSourcesView.vue`（第 28、86 行）
- Modify: `frontend/src/views/hub/ProjectDetailView.vue`（第 44、47、51 行，以及第 275 行的註解）
- Modify: `frontend/src/views/hub/ResultView.vue`（第 17、20、24 行，以及第 410 行的註解）
- Modify: `frontend/src/views/PaperPage.vue`（第 40 行）

**Interfaces:**
- Consumes: 無
- Produces: 無

**注意：這是本批最容易做錯的任務。** 全專案共有約 40 處「論文」字樣，其中**絕大多數指的是使用者上傳的研究論文，必須原封不動**。只改下列明確列出的 8 處使用者可見文案，外加 2 處連帶的註解。

**明確不要改**（這些講的是上傳的那篇研究論文）：
- `views/hub/ExtractFrameworkView.vue`（「上傳研究論文以自動提取方法論」「從論文提取框架」「上傳論文」）
- `views/hub/FrameworkLibraryView.vue`（「上傳論文」「論文標題」）
- `views/hub/DashboardView.vue`（「上傳研究論文以提取方法論和變數」）
- `components/hub/fieldMapping/MappingTable.vue`（「論文變數」）
- `components/workflow/nodePanel/ComputeCiPanel.vue`、`SettingsPanel.vue`（「適合學術論文」「適合論文報告」）
- `views/StyleGuideView.vue`、`composables/workflow/useWorkflowImport.ts`、`types/fieldMapping.ts`、`utils/dataset.ts`、`utils/paperTransform.ts`、`components/paper/` 下各檔的註解
- 路由路徑 `/paper`、`/paper/sources`，以及所有程式碼識別字（`usePaperExists`、`PaperPage`、`hasPaper`、`report` 等）一律不動。

- [ ] **Step 1: 改 `PaperSourcesView.vue`**

第 28 行：
```
論文標題（選填）
```
改為：
```
技術報告標題（選填）
```

第 86 行：
```
確認並生成論文 ({{ selectedIds.length }})
```
改為：
```
確認並生成技術報告 ({{ selectedIds.length }})
```

- [ ] **Step 2: 改 `ProjectDetailView.vue`**

第 44 行 `重新生成論文` → `重新生成技術報告`
第 47 行 `查看論文` → `查看技術報告`
第 51 行 `生成論文` → `生成技術報告`

第 275 行的註解：
```
/* 樣式比照 ResultView 的論文按鈕，同一個功能在兩處要長得一樣 */
```
改為：
```
/* 樣式比照 ResultView 的技術報告按鈕，同一個功能在兩處要長得一樣 */
```

- [ ] **Step 3: 改 `ResultView.vue`**

第 17 行 `重新生成論文` → `重新生成技術報告`
第 20 行 `查看論文` → `查看技術報告`
第 24 行 `生成論文` → `生成技術報告`

第 410 行的註解：
```
/* 重新生成是次要動作，查看論文才是主要路徑，用 outline 拉開層級 */
```
改為：
```
/* 重新生成是次要動作，查看技術報告才是主要路徑，用 outline 拉開層級 */
```

- [ ] **Step 4: 改 `PaperPage.vue`**

第 40 行：
```
此論文尚未關聯專案,無法儲存
```
改為（順手把半形逗號改成全形，與全站中文標點一致）：
```
此技術報告尚未關聯專案，無法儲存
```

- [ ] **Step 5: 確認沒有誤傷**

Run:
```bash
cd frontend && grep -rn "生成論文\|查看論文\|論文標題（選填）\|此論文尚未" src/
```
Expected: 無輸出。

Run:
```bash
cd frontend && grep -rn "上傳論文\|從論文提取框架\|論文變數" src/
```
Expected: 仍有輸出（`ExtractFrameworkView.vue`、`FrameworkLibraryView.vue`、`MappingTable.vue`），代表上傳研究論文那條線沒有被誤改。

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。

- [ ] **Step 6: 停下回報**

不要 commit。回報改動清單給使用者確認用詞。

---

### Task 5: 抽出共用的最佳模型計算與流程標籤表

**背景：** 為 Task 6 做準備。最佳模型的計算目前寫死在 result 頁的元件內，前處理與特徵工程的中文標籤表也鎖在 workflow 設定面板的 `<script setup>` 裡，兩者都要在專案詳情頁重用。複製一份會造成兩份會各自漂移的邏輯。

**Files:**
- Create: `frontend/src/constants/workflowLabels.ts`
- Create: `frontend/src/utils/workflow/summarizeWorkflowPipeline.ts`
- Modify: `frontend/src/utils/workflow/summarizeWorkflowResult.ts`（新增 `findBestModel` 匯出）
- Modify: `frontend/src/views/hub/ResultView.vue`（移除本地的 `bestModelFor`，改用匯入）
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`（移除本地的 `PREPROCESS_LABELS`／`FEATURE_LABELS`／`VALIDATION_METHODS`，改用匯入）

**Interfaces:**
- Consumes: `ModelMetricSummary`（已定義於 `frontend/src/utils/workflow/summarizeWorkflowResult.ts`）、`FlowNode`（已定義於 `frontend/src/types/workflow.ts`）
- Produces:
  - `constants/workflowLabels.ts`：`PREPROCESS_LABELS: Record<string, string>`、`FEATURE_LABELS: Record<string, string>`、`VALIDATION_LABELS: Record<string, string>`
  - `summarizeWorkflowResult.ts` 新增：`findBestModel(summary: ModelMetricSummary[], metric: string): { modelName: string, valueFormatted: string } | null`
  - `summarizeWorkflowPipeline.ts`：`summarizeWorkflowPipeline(nodes: unknown): PipelineSummary`，其中 `PipelineSummary` 為 `{ preprocess: string[], featureEngineering: string[], resampling: string | null, validation: string | null, models: string[] }`

**注意：** `SettingsPanel.vue` 現有的 `VALIDATION_METHODS` 是 `Array<{ value, label }>`（給下拉選單用），而 Task 6 需要的是「由 method 字串查標籤」。新的 `VALIDATION_LABELS` 用 `Record` 形態，`SettingsPanel` 的下拉選單改由它推導出陣列，兩邊共用同一份真值。

- [ ] **Step 1: 建立 `constants/workflowLabels.ts`**

建立 `frontend/src/constants/workflowLabels.ts`：

```ts
// 前處理／特徵工程／驗證方法的中文標籤。workflow 設定面板與專案詳情頁共用，
// 兩處顯示的名稱必須一致
export const PREPROCESS_LABELS: Record<string, string> = {
  fill_na: '缺值填補',
  knn_impute: 'KNN 缺值填補',
  iterative_impute: 'MICE 多重插補',
  normalize: 'Min-Max 正規化',
  standardize: 'Z-score 標準化',
  one_hot: 'One-Hot 編碼',
  label_encode: 'Label 編碼',
  drop_columns: '移除欄位',
  remove_outliers_iqr: 'IQR 異常值處理',
  remove_outliers_zscore: 'Z-score 異常值處理',
}

export const FEATURE_LABELS: Record<string, string> = {
  select_relevant_features: '特徵選擇',
  pca: 'PCA 降維',
  discretize_continuous: '連續→離散',
  continuize_discrete: '離散→連續',
  normalize_features: '特徵正規化',
  remove_sparse_features: '移除稀疏特徵',
}

export const VALIDATION_LABELS: Record<string, string> = {
  k_fold: 'Cross validation',
  group_k_fold: 'Cross validation by feature',
  random_sampling: 'Random sampling',
  leave_one_out: 'Leave one out',
  test_on_train: 'Test on train data',
  test_on_test: 'Test on test data',
}
```

- [ ] **Step 2: 讓 `SettingsPanel.vue` 改用共用標籤表**

在 `frontend/src/components/workflow/nodePanel/SettingsPanel.vue` 的 `<script setup>` 中：

刪掉本地的 `const PREPROCESS_LABELS = { ... }`、`const FEATURE_LABELS = { ... }`、`const VALIDATION_METHODS = [ ... ]` 三段宣告（約在第 400-428 行）。

在 import 區加上：

```ts
import { FEATURE_LABELS, PREPROCESS_LABELS, VALIDATION_LABELS } from '@/constants/workflowLabels'
```

在原本 `VALIDATION_METHODS` 的位置改寫為由共用表推導：

```ts
const VALIDATION_METHODS = Object.entries(VALIDATION_LABELS)
  .map(([value, label]) => ({ value, label }))
```

`preprocessOptions` 與 `featureOptions` 兩個 computed 保持原樣不動（它們讀的名稱沒變）。

- [ ] **Step 3: 驗證 SettingsPanel 沒壞**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。

人工檢查：開 workflow 頁，點 Settings 節點，確認前處理與特徵工程的下拉選項、以及驗證方法下拉選項，內容與順序跟改動前一致。

- [ ] **Step 4: 在 `summarizeWorkflowResult.ts` 新增 `findBestModel`**

在 `frontend/src/utils/workflow/summarizeWorkflowResult.ts` 檔尾新增：

```ts
// 指定指標下分數最高的模型。指標值一律視為越大越好——目前介面暴露的
// 指標（accuracy、auc、f1 等）都符合這個方向
export function findBestModel (
  summary: ModelMetricSummary[],
  metric: string,
): { modelName: string, valueFormatted: string } | null {
  let best: { modelName: string, valueFormatted: string, value: number } | null = null
  for (const row of summary) {
    const entry = row.metrics.find(m => m.metric === metric)
    if (!entry) continue
    if (Number.isNaN(entry.valueRaw)) continue
    if (!best || entry.valueRaw > best.value) {
      best = { modelName: row.model_name, valueFormatted: entry.valueFormatted, value: entry.valueRaw }
    }
  }
  return best ? { modelName: best.modelName, valueFormatted: best.valueFormatted } : null
}
```

- [ ] **Step 5: 讓 `ResultView.vue` 改用 `findBestModel`**

在 `frontend/src/views/hub/ResultView.vue` 中：

把 import 那行：
```ts
import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```
改為：
```ts
import { findBestModel, type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```

刪掉本地的整個 `function bestModelFor (metric: string) { ... }`（約第 234-246 行）。

在 `metricCards` computed 中，把兩處呼叫改為傳入 `summary.value`，並把回傳欄位名 `model_name` 改為 `modelName`：

```ts
const metricCards = computed<MetricCard[]>(() => {
  if (metricNames.value.length === 0) return []
  const primaryMetric = metricNames.value[0]!
  const best = findBestModel(summary.value, primaryMetric)

  const cards: MetricCard[] = [
    {
      key: 'best-model',
      title: '最佳模型',
      value: best?.modelName ?? '—',
      hint: best ? `${primaryMetric}: ${best.valueFormatted}` : '',
      accent: true,
    },
  ]

  for (const metric of metricNames.value.slice(1, 4)) {
    const metricBest = findBestModel(summary.value, metric)
    cards.push({
      key: metric,
      title: metric,
      value: metricBest?.valueFormatted ?? '—',
      hint: metricBest?.modelName ?? '',
    })
  }

  return cards.slice(0, 4)
})
```

- [ ] **Step 6: 建立 `summarizeWorkflowPipeline.ts`**

建立 `frontend/src/utils/workflow/summarizeWorkflowPipeline.ts`：

```ts
import { FEATURE_LABELS, PREPROCESS_LABELS, VALIDATION_LABELS } from '@/constants/workflowLabels'

export interface PipelineSummary {
  preprocess: string[]
  featureEngineering: string[]
  resampling: string | null
  validation: string | null
  models: string[]
}

const EMPTY: PipelineSummary = {
  preprocess: [],
  featureEngineering: [],
  resampling: null,
  validation: null,
  models: [],
}

interface StoredNode {
  id?: unknown
  data?: { config?: Record<string, unknown>, label?: unknown }
}

function asRecord (value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

// pipeline 步驟的形狀是 { type, ...參數 }，只取 type 去查中文標籤；
// 查不到就原樣顯示，讓未知步驟至少看得見而不是憑空消失
function stepLabels (pipeline: unknown, labels: Record<string, string>): string[] {
  if (!Array.isArray(pipeline)) return []
  return pipeline
    .map(step => String(asRecord(step).type ?? ''))
    .filter(Boolean)
    .map(type => labels[type] ?? type)
}

export function summarizeWorkflowPipeline (nodes: unknown): PipelineSummary {
  if (!Array.isArray(nodes)) return EMPTY

  const list = nodes as StoredNode[]
  const byId = (id: string) => list.find(n => String(n.id ?? '') === id)

  const preprocessorConfig = asRecord(byId('preprocessor')?.data?.config)
  const featureConfig = asRecord(byId('featureEngineering')?.data?.config)
  const testScoreConfig = asRecord(byId('testScore')?.data?.config)

  const validationMethod = String(asRecord(testScoreConfig.validation).method ?? '')
  const resamplingMethod = String(testScoreConfig.resampling_method ?? 'none')

  return {
    preprocess: stepLabels(preprocessorConfig.pipeline, PREPROCESS_LABELS),
    featureEngineering: stepLabels(featureConfig.pipeline, FEATURE_LABELS),
    resampling: resamplingMethod && resamplingMethod !== 'none' ? resamplingMethod : null,
    validation: validationMethod ? (VALIDATION_LABELS[validationMethod] ?? validationMethod) : null,
    models: list
      .filter(n => String(n.id ?? '').startsWith('model-'))
      .map(n => String(asRecord(n.data?.config).modelName ?? n.data?.label ?? ''))
      .filter(Boolean),
  }
}
```

- [ ] **Step 7: 驗收**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。

人工檢查：開一個已完成專案的結果頁，確認上方四張指標卡（最佳模型 + 三個指標）顯示的內容與抽出共用邏輯前完全一致。

- [ ] **Step 8: 停下回報**

不要 commit。這個任務沒有視覺改動，回報「畫面應該零變化」並請使用者確認結果頁指標卡沒跑掉。

---

### Task 6: 專案詳情頁改顯示最佳模型與流程摘要

**背景：** 已完成專案的詳情頁目前顯示「模型準確率」與「關鍵發現」兩列。使用者認為這兩項資訊價值不高，想改成顯示最佳模型，以及這個專案實際跑了什麼流程（前處理、特徵工程、重採樣、驗證、模型）。

**Files:**
- Modify: `frontend/src/views/hub/ProjectDetailView.vue`（template 的 completed 區塊、script 區、style 區）

**Interfaces:**
- Consumes:
  - `summarizeWorkflowResult(workflowResult)` 與 `findBestModel(summary, metric)`（Task 5 產出）
  - `summarizeWorkflowPipeline(nodes)` 回傳 `PipelineSummary`（Task 5 產出）
  - `loadWorkflowStateFromStorage(projectId: string)`（已存在於 `frontend/src/composables/workflow/useWorkflowStorage.ts`），回傳物件同時含 `nodes` 與 `workflowResult`
- Produces: 無

**注意：**
- `loadWorkflowStateFromStorage` 吃的是**字串** projectId，而 `ProjectDetailView` 現有的 `route.params.id` 已經是字串，直接用即可。
- 專案跑完但 localStorage 被清掉（換瀏覽器、清快取）時抓不到資料，此時整段流程摘要要降級成一行提示，不要留一排空白列。
- `Project` 型別的 `accuracy` 與 `keyFinding` 欄位在其他頁面仍被使用（專案列表卡片），**不要刪除型別欄位**，本任務只是不在詳情頁顯示它們。

- [ ] **Step 1: 加入 script 邏輯**

在 `frontend/src/views/hub/ProjectDetailView.vue` 的 `<script setup>` import 區加上：

```ts
import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
import { summarizeWorkflowPipeline } from '@/utils/workflow/summarizeWorkflowPipeline'
import { findBestModel, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```

在 `frameworkTitle` computed 之後加上：

```ts
// nodes 與 workflowResult 存在同一份 localStorage 記錄裡，一次讀出來給兩個摘要用
const workflowState = computed(() => loadWorkflowStateFromStorage(String(route.params.id)))

const summary = computed(() => summarizeWorkflowResult(workflowState.value?.workflowResult ?? null))

const primaryMetric = computed(() => summary.value[0]?.metrics[0]?.metric ?? null)

const bestModel = computed(() =>
  primaryMetric.value ? findBestModel(summary.value, primaryMetric.value) : null,
)

const pipeline = computed(() => summarizeWorkflowPipeline(workflowState.value?.nodes))

// 每一列都有值才顯示，避免一排「（無）」洗版；全空代表沒有可用的執行紀錄
const pipelineRows = computed(() => {
  const p = pipeline.value
  const rows: Array<{ label: string, value: string }> = []
  if (p.preprocess.length > 0) rows.push({ label: '前處理', value: p.preprocess.join('、') })
  if (p.featureEngineering.length > 0) rows.push({ label: '特徵工程', value: p.featureEngineering.join('、') })
  if (p.resampling) rows.push({ label: '重採樣', value: p.resampling })
  if (p.validation) rows.push({ label: '驗證', value: p.validation })
  if (p.models.length > 0) rows.push({ label: '模型', value: `${p.models.length} 個：${p.models.join('、')}` })
  return rows
})
```

`loadWorkflowStateFromStorage` 的回傳型別是 `({ nodes: FlowNode[], edges: EdgeBase[] } & WorkflowExecutionState) | null`（見 `useWorkflowStorage.ts:143-145`），`nodes` 與 `workflowResult` 都是有型別的欄位，不需要額外斷言。

- [ ] **Step 2: 改 template 的 completed 區塊**

把 template 中 `<template v-if="project.status === 'completed'">` 內、`<div class="result-row">` 到第二個 `<div class="result-divider" />` 為止的那段（即「模型準確率」與「關鍵發現」兩列及其分隔線）整段換成：

```vue
<div class="result-row">
  <div class="result-label">最佳模型</div>
  <div class="result-value result-value--model">{{ bestModel?.modelName ?? '—' }}</div>
  <div v-if="bestModel && primaryMetric" class="result-metric-hint">
    {{ primaryMetric }}: {{ bestModel.valueFormatted }}
  </div>
</div>
<div class="result-divider" />

<template v-if="pipelineRows.length > 0">
  <div v-for="row in pipelineRows" :key="row.label" class="result-row result-row--compact">
    <div class="result-label">{{ row.label }}</div>
    <div class="result-value">{{ row.value }}</div>
  </div>
</template>
<div v-else class="result-empty">找不到此專案的執行紀錄</div>
<div class="result-divider" />
```

`.result-row` 是上下堆疊（label 在上、value 在下），不是左右兩欄 —— 指標小字直接接在 value 之後即可，不需要另外開一列。

底下原有的「查看完整結果」連結與論文按鈕區塊維持不動。

- [ ] **Step 3: 加上新的樣式**

該檔的 `<style>` 區內容縮排兩個空格，新增的規則要跟著對齊。

先把原本註明「準確率是這頁唯一的展示型數字」的 `.result-value.large` 規則整條刪掉（模型準確率已經移除，沒有使用者了），再於 `.result-value` 規則之後新增：

```css
  /* 最佳模型是這頁的視覺錨點，但模型名可能長到 20 幾個字元，
     字級要比原本放數字時小一階才不會撐出卡片 */
  .result-value--model {
    font-size: 22px;
    font-weight: 500;
    line-height: 1.2;
    color: var(--color-ink);
    word-break: break-word;
  }

  .result-metric-hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* 流程各列是清單而非展示數字，壓縮行距讓五列不會把卡片拉太長 */
  .result-row--compact {
    padding: 9px 0;
  }

  .result-row--compact .result-value {
    line-height: 1.5;
    word-break: break-word;
  }

  .result-empty {
    padding: 10px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }
```

- [ ] **Step 4: 驗收**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆通過。

Run: `cd frontend && grep -n "模型準確率\|關鍵發現" src/views/hub/ProjectDetailView.vue`
Expected: 無輸出。

人工檢查（`npm run dev`）：
1. 開一個已完成、且本機有執行紀錄的專案詳情頁：頂部顯示「最佳模型」標籤、模型名稱（22px 藏青），其下一行小字指標值，接著是前處理／特徵工程／重採樣／驗證／模型各列。
2. 沒有設定前處理的專案：該列整列不出現，不應看到「前處理　（無）」。
3. 在瀏覽器 DevTools 清掉該專案的 workflow localStorage 記錄後重整：最佳模型顯示「—」，流程區顯示「找不到此專案的執行紀錄」，版面不塌。
4. 進行中與草稿狀態的專案詳情頁維持原樣（骨架屏／「尚未執行此專案」）。
5. 模型清單很長時文字換行，不會撐破卡片或水平溢出。

- [ ] **Step 5: 停下回報**

不要 commit。回報三種狀態（有紀錄、無前處理、無紀錄）的畫面給使用者確認。

---

## 收尾

六個任務全部通過後，一次性驗收：

- [ ] Run: `cd frontend && npm run build && npm run lint` —— 全綠。
- [ ] 掃過完整 diff，把只是重述程式碼在做什麼的註解刪掉。
- [ ] 把改動整理成一份清單給使用者，等使用者明確點頭後才 `git commit`（單行訊息、不加 `Co-Authored-By` trailer）。
