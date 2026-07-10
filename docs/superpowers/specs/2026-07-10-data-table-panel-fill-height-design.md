# Data Table Panel 欄位設定表格 撐滿抽屜高度 設計

日期：2026-07-10
範圍：`frontend/src/components/workflow/WorkflowWorkspace.vue`、`frontend/src/components/workflow/WorkflowOptionsPanel.vue`、`frontend/src/components/workflow/nodePanel/DataTablePanel.vue`

## 背景

Data Table 節點面板的「欄位設定」表格（`.data-table-column-settings`）目前被寫死 `max-height: 380px`，跟抽屜（drawer）實際高度完全脫鉤。抽屜的高度是由 `useDrawerDrag.ts` 依段位動態控制（collapsed 280px / expanded 54vh / full 90vh，見 [[2026-07-09-data-table-panel-design]] 的改動 4），而抽屜內容容器鏈（`.drawer-content-wrapper` → `.setting-area` → `.panel` → `.panel-body` → `.data-table-panel`）也沒有把高度一路以 `flex:1` 往下傳，所以表格區塊只會停在自己「原本需要的高度」，抽屜被拉得越高（尤其是 full 90vh），底下留白就越明顯，浪費畫面空間。

目標：表格區塊的高度應該跟著抽屜當前段位動態撐滿，段位越高（54vh、90vh）表格就越高；但同時不能因為某些段位（例如較矮螢幕上的 54vh，或 collapsed 280px）反而讓表格比現在的 380px 還矮。

## 改動：flex 撐滿容器鏈 + 380px 高度地板

### 1. 撐滿容器鏈（由外到內，皆補上 `flex:1; min-height:0`）

- `WorkflowWorkspace.vue` — `.drawer-content-wrapper`：目前是沒有任何樣式的裸 div，補上 `display:flex; flex-direction:column; flex:1; min-height:0`。
- `WorkflowOptionsPanel.vue` — `.setting-area`：已有 `min-height:0`，補上 `flex:1`。
- `DataTablePanel.vue` — 包住 summary/欄位設定區塊的 `<div v-else>`：目前沒有 class、沒有樣式，補上 class `data-table-body` 並設定 `display:flex; flex-direction:column; flex:1; min-height:0`。
- `DataTablePanel.vue` — `.data-table-panel`：補上 `flex:1; min-height:0`（原本只有 `display:flex; flex-direction:column; gap:14px`）。

`.panel`、`.panel-body`（`WorkflowOptionsPanel.vue`）已經是 `flex:1; min-height:0`，不需要改。

### 2. 表格區塊本身：`flex:1` 撐滿 + `min-height:380px` 保底

`.data-table-column-settings`（`DataTablePanel.vue`）：

```css
/* 原本 */
max-height: 380px;
overflow: hidden;

/* 改為 */
flex: 1 1 380px;
min-height: 380px;
overflow: hidden;
```

- 空間足夠時（54vh、90vh）：`flex:1` 讓它長大填滿可用空間，撐滿抽屜當前段位給的高度。
- 空間不足 380px 時（例如較矮螢幕上的 54vh，或 collapsed 280px 段位）：`min-height:380px` 保底，表格高度不會比現在的固定 380px 還矮；超出的部分交給外層 `.options-drawer__scroll`（本身已有 `overflow-y:auto`）讓整個抽屜一起捲動，不會把表格內容硬壓扁。

內層 `.column-settings-body`（已經是 `flex:1; min-height:0; overflow-y:auto`）不需要改，欄位很多時仍由它負責表格內部捲動。

### 已知的視覺副作用（預期內）

欄位很少、表格內容本身很短時，`.data-table-column-settings` 仍會被撐到填滿當前可用高度，「Reset / 繼續」按鈕會被推到區塊最底部（貼底，類似對話框 footer 的效果），而不是緊接在最後一列表格下面。剩餘空白會出現在「區塊內部、最後一列跟按鈕之間」，而不是像現在這樣出現在「區塊外、整片抽屜的浪費空間」。

## 不涉及的部分

純 CSS layout 調整，三個檔案皆不涉及 `<script>` 區塊或任何資料/互動邏輯變更。

## 驗證方式

- 手動在瀏覽器開啟 workflow 畫面、上傳 CSV，選到 Data Table 節點：
  - 抽屜停在 collapsed（預設）時，表格區塊維持原本可用的高度，若欄位多於可視範圍，抽屜整體可捲動查看。
  - 拖曳/點擊把抽屜拉到 expanded（54vh）：表格區塊明顯長高、貼齊可用空間，底部不再有大片空白。
  - 拖曳把抽屜拉到 full（90vh）：表格區塊撐滿到接近整頁，「Reset / 繼續」按鈕貼在區塊底部。
  - 用欄位很少（例如 2-3 欄）的 CSV 測試：確認在 54vh / 90vh 時按鈕仍正確貼底，不會出現表格重疊或跑版。
  - 用欄位很多的 CSV 測試：確認表格內部（`.column-settings-body`）仍可正常捲動，thead 仍 sticky。
