# Distribution Panel 圖表排版（只在 full 段位改 grid）設計

日期：2026-07-11
範圍：`frontend/src/composables/useDrawerDrag.ts`、`frontend/src/components/workflow/WorkflowWorkspace.vue`、`frontend/src/components/workflow/WorkflowOptionsPanel.vue`、`frontend/src/components/workflow/nodePanel/DistributionPanel.vue`

對應 `.claude/ux-issues.md` 問題 #2：「Distribution 圖太多，排版不佳」。

## 背景

`DistributionPanel.vue` 的 `.distribution-chart-grid` 目前用 `display:flex; overflow-x:auto` 做橫向捲動卡片列，卡片固定寬 `flex:0 0 320px`。欄位一多，使用者要一直橫向捲動找圖表，體驗不佳。

抽屜（drawer）在 2026-07-10 已從三段擴充成四段（`peeked` 100px / `collapsed` 280px / `expanded` 54vh / `full` 90vh，見 `useDrawerDrag.ts`），`full` 段位提供了接近整頁的可視高度，但 `DistributionPanel` 目前完全沒有使用這個空間——面板高度只跟著內容自然撐開，不管抽屜實際段位是什麼。

## 決策：只在 full 段位切換成 grid，其餘三段維持現況

跟 Data Table 的「無條件撐滿抽屜高度」不同，這次的需求是**只有使用者把抽屜拖到 full（90vh）時，圖表才改成可換行的 grid 排列並撐滿高度**；`peeked` / `collapsed` / `expanded` 三段完全不變，維持現在的橫向捲動卡片。

原因：橫向捲動卡片在較矮的段位（collapsed 280px / expanded 54vh）本身沒有問題，是可用的瀏覽方式；只有在使用者刻意展開到全高、想要「看到很多圖表」時，橫向捲動才顯得笨拙，改成 grid 換行才有意義。

## 改動 1：暴露 drawer stage

`useDrawerDrag.ts` 目前的 `stage`（型別 `Stage = "peeked" | "collapsed" | "expanded" | "full"`）只在組合式函式內部使用，回傳值只有 `{ style, startDrag, reset, expand }`。

改動：回傳值新增唯讀的 `stage`（`readonly(stage)` 或直接回傳 `computed(() => stage.value)`），供外部讀取目前段位。

## 改動 2：往下傳遞 stage

- `WorkflowWorkspace.vue`：已呼叫 `useDrawerDrag()`（見 `drawerStyle`/`startDrag`/`resetDrawer`/`expandDrawer` 的解構），改成同時解構出 `stage`，命名為 `drawerStage`；透過新增的 prop 傳給 `WorkflowOptionsPanel`（例如 `:drawer-stage="drawerStage"`）。
- `useDrawerDrag.ts`：`export type Stage = ...`（原本是模組內部型別，改成 export，供其他檔案 import）。
- `WorkflowOptionsPanel.vue`：`import type { Stage } from '@/composables/useDrawerDrag'`；`defineProps` 新增 `drawerStage: Stage`；在 `<DistributionPanel>` 使用處新增 `:drawer-stage="props.drawerStage"`。
- `DistributionPanel.vue`：`import type { Stage } from '@/composables/useDrawerDrag'`；`defineProps` 新增 `drawerStage?: Stage`。

## 改動 3：DistributionPanel 依 stage 切換樣式

新增一個 computed：

```ts
const isFullStage = computed(() => props.drawerStage === 'full')
```

模板上 `.distribution-chart-grid` 綁定 modifier class：

```html
<div class="distribution-chart-grid" :class="{ 'distribution-chart-grid--full': isFullStage }">
```

`.distribution-panel` 同樣綁定：

```html
<section class="distribution-panel" :class="{ 'distribution-panel--full': isFullStage }">
```

### CSS：非 full（預設，不變）

`.distribution-panel`、`.distribution-chart-grid`、`.distribution-chart-card` 維持現有樣式（横向 flex 捲動、卡片固定寬 320px、webkit 捲軸樣式等）完全不動。

### CSS：full 段位 modifier

```css
.distribution-panel--full {
  flex: 1;
  min-height: 0;
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

跟 Data Table 的 `.data-table-column-settings` 同一手法：`380px` 高度地板避免抽屜在較矮螢幕上被壓扁；超過地板高度時 `flex:1` 讓 grid 撐滿可用空間，內部自己垂直捲動（`overflow-y:auto`），不依賴外層 `.options-drawer__scroll`。

`.distribution-chart-grid--full .distribution-chart-card` 這條規則是為了蓋掉卡片原本的 `flex: 0 0 320px; min-width: 320px;`——grid 容器下 `flex` 屬性本身無效，但 `min-width:320px` 仍會生效並可能跟 `minmax(280px, 1fr)` 的欄寬衝突（欄寬 280px 卻要求卡片至少 320px 寬），所以需要顯式覆蓋成 `min-width:0`。

### 不受影響

卡片內部排版（標題換行/展開按鈕、副標題、meta、SVG 直方圖/長條圖）完全不動；`.distribution-summary`、`.distribution-header`、空狀態、loading 狀態不動；`chartData`/`computeNumericBins`/CSV 解析等 `<script>` 邏輯不動。

## 不涉及的部分

- `.claude/ux-issues.md` #16（統計文字搬到跟檔名同一行）不在本次範圍。
- 其他節點面板（settings/preprocessor/…）不受影響——`drawerStage` 是新增的可選 prop，只有 `DistributionPanel` 使用。

## 驗證方式

手動在瀏覽器開啟 workflow 畫面、上傳一個欄位數較多（例如 10+ 欄）的 CSV，切到 Distribution 節點：

- 抽屜停在 `collapsed`（預設）：圖表維持橫向捲動卡片，行為與現在完全一致。
- 拖曳到 `expanded`（54vh）：同樣維持橫向捲動，不應該變成 grid。
- 拖曳到 `full`（90vh）：圖表改成可換行的 grid，欄數隨抽屜寬度自適應；卡片之間無寬度衝突（不會有卡片被擠出容器或出現水平捲軸）；圖表數量超過一屏時，grid 區塊自己垂直捲動。
- 從 `full` 縮回 `expanded`／`collapsed`：grid 應該正確切回橫向捲動卡片，不殘留 grid 樣式或錯誤高度。
- 用欄位很少（1-2 欄）的 CSV 在 `full` 段位測試：確認 `min-height:380px` 地板生效，區塊不會被壓得比卡片內容還矮。
