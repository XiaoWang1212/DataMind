# Distribution Panel 圖表排版（僅 full 段位改 grid）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distribution 節點面板的圖表卡片，只有在 drawer 拖到 `full`（90vh）段位時，才從橫向捲動列改成可換行、撐滿高度的 grid 排列；`peeked` / `collapsed` / `expanded` 三段完全維持現況不變。

**Architecture:** `useDrawerDrag.ts` 目前的 `stage`（四段：`peeked`/`collapsed`/`expanded`/`full`）只在組合式函式內部使用，這次要把它 export 出去、往下傳成 `drawerStage` prop，一路穿過 `WorkflowWorkspace.vue` → `WorkflowOptionsPanel.vue` → `DistributionPanel.vue`。`DistributionPanel.vue` 內用一個 `isFullStage` computed 判斷是否為 `full`，再用 `:class` 綁定一組 modifier class（`--full`），CSS 走 Data Table 表格區塊已驗證過的手法：`flex:1 1 380px; min-height:380px; overflow-y:auto` 撐滿高度＋捲動地板。非 full 時完全不套用 modifier class，原本的橫向捲動樣式原封不動。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC，scoped CSS，無額外套件。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。依照 `CLAUDE.md` 的慣例，本計畫不新增測試框架，改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟；若執行者（例如沒有瀏覽器操作能力的 subagent）無法完成手動驗證，必須明確說明「無法測試 UI」，不能逕自宣稱驗證通過。
- **Commit 前必須先取得使用者明確同意**：完成實作、跑完自動化檢查（`npm run build`）、並列出手動驗證步驟後，必須停下來、明確詢問使用者「瀏覽器手動測試沒問題了嗎？」，取得使用者的明確答覆後才能執行 `git add` / `git commit`。就算是透過 `superpowers:subagent-driven-development` 執行、implementer subagent 原本的預設流程會自動 commit，這裡也要覆蓋掉那個預設行為——不要在拿到使用者確認之前自動 commit。Task-reviewer 對 diff 的核可不能取代使用者自己在瀏覽器裡的驗證。
- **只有 `full`（90vh）段位改變外觀**：`peeked` / `collapsed` / `expanded` 三段的 `DistributionPanel` 樣式與行為必須維持現況、逐 pixel 不變。
- `.distribution-chart-grid--full` 的高度地板固定為 `380px`，欄寬用 `repeat(auto-fill, minmax(280px, 1fr))` 自適應欄數（使用者已於 2026-07-11 確認這兩個決策）。
- 所有使用者可見文字維持繁體中文；本次改動不新增任何使用者可見文字。
- Spec 來源：`docs/superpowers/specs/2026-07-11-distribution-panel-grid-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/composables/useDrawerDrag.ts` | Drawer 拖曳/段位（stage）狀態管理 | `Stage` 型別改成 `export`；回傳值新增唯讀 `stage` |
| `frontend/src/components/workflow/WorkflowWorkspace.vue` | Drawer 外殼，呼叫 `useDrawerDrag()`，渲染 `WorkflowOptionsPanel` | 解構出 `stage`（命名 `drawerStage`），透過新 prop 往下傳 |
| `frontend/src/components/workflow/WorkflowOptionsPanel.vue` | Drawer 內容路由，依 `selectedNode.id` 渲染各節點面板 | 新增 `drawerStage` prop，轉傳給 `DistributionPanel` |
| `frontend/src/components/workflow/nodePanel/DistributionPanel.vue` | Distribution 節點面板：CSV 預覽＋圖表卡片 | 新增 `drawerStage` prop、`isFullStage` computed、`--full` modifier class 樣式 |

這四個檔案都是既有的父子鏈節點，本次不新增任何檔案。

---

## Task 1: 暴露 drawer stage、往下傳遞、DistributionPanel 依段位切換 grid 排版

**Files:**
- Modify: `frontend/src/composables/useDrawerDrag.ts:24`（`type Stage` 定義）
- Modify: `frontend/src/composables/useDrawerDrag.ts:222`（`useDrawerDrag()` 回傳值）
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue:166`（`useDrawerDrag()` 解構）
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue:73-91`（`<WorkflowOptionsPanel>` 使用處）
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue:226-263`（import + `defineProps`）
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue:25-27`（`<DistributionPanel>` 使用處）
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:2`（`.distribution-panel` 根節點 class 綁定）
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:25`（`.distribution-chart-grid` class 綁定）
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:108-116`（import + `defineProps` + `isFullStage` computed）
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:343-395`（style：新增 `--full` modifier 規則）

**Interfaces:**
- Consumes: 無新的外部依賴（純既有 Vue 3 `computed`/`defineProps`）。
- Produces: `useDrawerDrag()` 回傳值新增 `stage: ComputedRef<Stage>`；`Stage` 型別現在是具名 export，供其他檔案 `import type { Stage } from '@/composables/useDrawerDrag'`。`WorkflowOptionsPanel` 與 `DistributionPanel` 都新增 `drawerStage?: Stage` prop。`DistributionPanel` 新增 `isFullStage`（`ComputedRef<boolean>`，`drawerStage === 'full'` 時為 `true`）。後續若有其他面板（settings/preprocessor/…）要做類似「只在 full 段位變化」的效果，可以比照這條 prop 鏈直接接上，不需要再改 `useDrawerDrag.ts`。

- [ ] **Step 1: `useDrawerDrag.ts` — export `Stage` 型別**

把：

```ts
type Stage = "peeked" | "collapsed" | "expanded" | "full";
```

改成：

```ts
export type Stage = "peeked" | "collapsed" | "expanded" | "full";
```

- [ ] **Step 2: `useDrawerDrag.ts` — 回傳值新增唯讀 `stage`**

把（`useDrawerDrag()` 的最後一行）：

```ts
  return { style, startDrag, reset, expand };
}
```

改成：

```ts
  return { style, startDrag, reset, expand, stage: computed(() => stage.value) };
}
```

（`computed` 已經在檔案第一行 `import { computed, onBeforeUnmount, ref } from "vue";` 匯入，不需要新增 import。）

- [ ] **Step 3: `WorkflowWorkspace.vue` — 解構 `stage`，命名為 `drawerStage`**

把：

```ts
  const { style: drawerStyle, startDrag, reset: resetDrawer, expand: expandDrawer } = useDrawerDrag()
```

改成：

```ts
  const { style: drawerStyle, startDrag, reset: resetDrawer, expand: expandDrawer, stage: drawerStage } = useDrawerDrag()
```

- [ ] **Step 4: `WorkflowWorkspace.vue` — 把 `drawerStage` 傳給 `WorkflowOptionsPanel`**

把：

```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
```

改成（在 `available-models` 之後、`file` 之前，依現有的字母序插入 `drawer-stage`）：

```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :drawer-stage="drawerStage"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
```

- [ ] **Step 5: `WorkflowOptionsPanel.vue` — import `Stage` 型別、新增 `drawerStage` prop**

把 script 開頭的 import：

```ts
<script setup lang="ts">
  import type { ConfigValue, SimpleNode } from '@/types/workflow'
  import { computed, reactive, ref, watch } from 'vue'
```

改成：

```ts
<script setup lang="ts">
  import type { ConfigValue, SimpleNode } from '@/types/workflow'
  import type { Stage } from '@/composables/useDrawerDrag'
  import { computed, reactive, ref, watch } from 'vue'
```

把 `defineProps`：

```ts
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
  }>()
```

改成（新增 `drawerStage`）：

```ts
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
  }>()
```

- [ ] **Step 6: `WorkflowOptionsPanel.vue` — 把 `drawerStage` 傳給 `DistributionPanel`**

把：

```html
        <!-- Distribution 節點：顯示當前資料視覺化 -->
        <template v-if="selectedNode.id === 'distribution'">
          <DistributionPanel :file="props.file" :file-name="fileName" />
        </template>
```

改成：

```html
        <!-- Distribution 節點：顯示當前資料視覺化 -->
        <template v-if="selectedNode.id === 'distribution'">
          <DistributionPanel
            :drawer-stage="props.drawerStage"
            :file="props.file"
            :file-name="fileName"
          />
        </template>
```

- [ ] **Step 7: `DistributionPanel.vue` — import `Stage` 型別、新增 `drawerStage` prop、新增 `isFullStage` computed**

把：

```ts
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
  }>()

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')
```

改成：

```ts
<script setup lang="ts">
  import type { Stage } from '@/composables/useDrawerDrag'
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
    drawerStage?: Stage
  }>()

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')
  const isFullStage = computed(() => props.drawerStage === 'full')
```

- [ ] **Step 8: `DistributionPanel.vue` — template 綁定 modifier class**

把根節點：

```html
<template>
  <section class="distribution-panel">
    <div class="distribution-header">
```

改成：

```html
<template>
  <section
    class="distribution-panel"
    :class="{ 'distribution-panel--full': isFullStage }"
  >
    <div class="distribution-header">
```

把圖表 grid 容器：

```html
        <div class="distribution-chart-grid">
          <div
            v-for="(chart, index) in chartData"
```

改成：

```html
        <div
          class="distribution-chart-grid"
          :class="{ 'distribution-chart-grid--full': isFullStage }"
        >
          <div
            v-for="(chart, index) in chartData"
```

- [ ] **Step 9: `DistributionPanel.vue` — 新增 `.distribution-panel--full` CSS 規則**

把：

```css
  .distribution-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .distribution-header {
```

改成：

```css
  .distribution-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .distribution-panel--full {
    flex: 1;
    min-height: 0;
  }

  .distribution-header {
```

- [ ] **Step 10: `DistributionPanel.vue` — 新增 `.distribution-chart-grid--full` 與卡片覆蓋規則**

把：

```css
  .distribution-chart-grid {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .distribution-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .distribution-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }
```

改成：

```css
  .distribution-chart-grid {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .distribution-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .distribution-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .distribution-chart-grid--full {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    align-content: start;
    flex: 1 1 380px;
    min-height: 380px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .distribution-chart-grid--full .distribution-chart-card {
    flex: none;
    min-width: 0;
  }
```

（`.distribution-chart-grid--full` 的 `display:grid`／`overflow-x:hidden` 會蓋掉上面 `.distribution-chart-grid` 的 `display:flex`／`overflow-x:auto`，因為兩條規則 specificity 相同、`--full` 在後面，一般 CSS cascade 就會讓後面的規則生效——不需要 `!important`。`.distribution-chart-card` 原本的 `flex: 0 0 320px; min-width: 320px;` 在 grid 容器裡 `flex` 屬性本身就無效，但 `min-width:320px` 仍會生效並跟 `minmax(280px, 1fr)` 的欄寬衝突，所以需要顯式覆蓋成 `min-width:0`。）

- [ ] **Step 11: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（`vue-tsc` type-check + `vite build` 都不報錯）。這一步只能抓出 template/CSS/型別錯誤，不能證明排版視覺效果正確，下一步一定要接著手動驗證。

- [ ] **Step 12: 手動驗證（需要瀏覽器操作，無法操作瀏覽器時必須明確說明「無法測試 UI」而非宣稱驗證通過）**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開啟 `http://localhost:3000/workflow`，上傳一份欄位數較多（例如 10+ 欄）的 CSV，點選畫布上的 Distribution 節點，確認：

- Drawer 停在 `collapsed`（預設）：圖表維持橫向捲動卡片，畫面跟改動前完全一致。
- 把 drawer 手把往上拖到 `expanded`（54vh）：同樣維持橫向捲動卡片，不應該變成 grid。
- 把 drawer 繼續往上拖到 `full`（90vh）：圖表改成可換行的 grid，欄數隨 drawer 寬度自適應；卡片之間沒有寬度衝突（不會有卡片被擠出容器，也不會出現水平捲軸）；圖表數量超過一屏時，grid 區塊自己垂直捲動（不是整個 drawer 捲動）。
- 從 `full` 縮回 `expanded` / `collapsed`：grid 要正確切回橫向捲動卡片，不殘留 grid 排版或錯誤高度。
- 換一份欄位很少（1-2 欄）的 CSV，在 `full` 段位測試：確認 `min-height:380px` 地板生效，圖表區塊不會被壓得比卡片內容還矮。
- 確認圖表卡片的「更多／收起」標題展開按鈕（`.distribution-title-toggle`）在 grid 模式下依然正常運作。

- [ ] **Step 13: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「已經跑完 `npm run build` 並列出手動驗證步驟，麻煩實際在瀏覽器測過 collapsed / expanded / full 三段的 Distribution 圖表排版，確認沒問題後再讓我 commit。」等待使用者明確回覆「可以」或指出問題，才能進到下一步。

- [ ] **Step 14: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/composables/useDrawerDrag.ts frontend/src/components/workflow/WorkflowWorkspace.vue frontend/src/components/workflow/WorkflowOptionsPanel.vue frontend/src/components/workflow/nodePanel/DistributionPanel.vue
git commit -m "feat: switch distribution panel charts to grid layout at full drawer stage"
```
