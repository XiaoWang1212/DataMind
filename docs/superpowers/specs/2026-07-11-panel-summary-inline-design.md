# Data Table／Distribution 欄位統計文字搬到跟檔名同一行 設計

日期：2026-07-11
範圍：`frontend/src/components/workflow/nodePanel/DataTablePanel.vue`、`frontend/src/components/workflow/nodePanel/DistributionPanel.vue`

對應 `.claude/ux-issues.md` 問題 #16。

## 背景

兩個節點面板都各自把「N 個欄位 / M 筆資料」這行統計文字，獨立顯示在 header（「已選檔案：X.csv」那行）下方，另起一行：

- `DataTablePanel.vue`：`.data-table-header`（3-19 行）顯示 `.data-table-guide`（暫停等待選 target 的藍色/綠色提示卡，`props.loading && columnsReady` 時顯示）+ `.data-table-file`（檔名，靠右對齊）；`.data-table-summary`（統計文字）則在下面 `.data-table-body`（34 行起）最上方獨立一行。
- `DistributionPanel.vue`：`.distribution-header`（2-10 行）只有 `.distribution-file`；`.distribution-summary`（統計文字）在下面另起一行（23-26 行）。

目標：統計文字搬到跟檔名同一行顯示，省掉獨立一行的空間。

## 改動 1：DataTablePanel.vue — header 內「guide / 統計文字」共用同一個插槽

Data Table 有暫停狀態，兩者互斥：

- 使用者還沒按「繼續」（`props.loading && columnsReady` 為 true）：header 顯示 `.data-table-guide`，跟現在一樣。
- 使用者按下「繼續」之後（`!props.loading`，此時 `columnsReady` 必為 true 才會走到這個分支）：guide 消失，改在**同一個位置**顯示統計文字，接手 guide 原本佔的空間。
- `.data-table-body` 裡原本獨立一行的統計文字整個移除，不再重複顯示——統計文字永遠只出現在 header。

### Template（`DataTablePanel.vue:3-19`）

原本：

```html
    <div class="data-table-header">
      <div
        v-if="props.loading && columnsReady"
        class="data-table-guide"
        :class="{ 'data-table-guide--ready': hasTarget }"
      >
        <span v-if="hasTarget">
          已選定目標變數「{{ targetColumnName }}」，按右下角「繼續」即可進入下一步。
        </span>
        <span v-else>
          請將要預測的欄位在下方「Role」欄選為 <strong>Target</strong>，再按右下角「繼續」。
        </span>
      </div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

改為（新增 `v-else-if` 分支，`columnsReady` 為 true 且 guide 沒顯示時，顯示統計文字）：

```html
    <div class="data-table-header">
      <div
        v-if="props.loading && columnsReady"
        class="data-table-guide"
        :class="{ 'data-table-guide--ready': hasTarget }"
      >
        <span v-if="hasTarget">
          已選定目標變數「{{ targetColumnName }}」，按右下角「繼續」即可進入下一步。
        </span>
        <span v-else>
          請將要預測的欄位在下方「Role」欄選為 <strong>Target</strong>，再按右下角「繼續」。
        </span>
      </div>
      <div v-else-if="columnsReady" class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

`columnsReady` 是既有的 computed（模板已在別處使用，如 `v-else-if="!columnsReady"`），不需要新增。

### Template（`DataTablePanel.vue:34-38`）— 移除 body 內獨立一行的統計文字

原本：

```html
    <div v-else class="data-table-body">
      <div class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>

      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

改為（整段 `.data-table-summary` 移除）：

```html
    <div v-else class="data-table-body">
      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

### CSS（`DataTablePanel.vue:516-522`）— `.data-table-summary` 從獨立區塊改成 header 插槽

原本：

```css
  .data-table-summary {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
    margin-bottom: 12px;
  }
```

改為（拿掉 `margin-bottom`，補上 `flex: 1 1 auto; min-width: 0;`，讓它跟 `.data-table-guide` 一樣能撐滿 header 左側可用空間，行為與視覺尺寸接手 guide 原本的位置）：

```css
  .data-table-summary {
    display: flex;
    flex: 1 1 auto;
    min-width: 0;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }
```

`.data-table-header`（496-500 行）、`.data-table-file`（502-507 行）不需要改，`.data-table-file` 原本就有 `margin-left: auto`，讓它固定貼右，不管左側是 guide 還是統計文字。

## 改動 2：DistributionPanel.vue — 統計文字搬進 header

Distribution 沒有暫停狀態，統計文字永遠跟檔名同一行，條件維持跟現在一樣（`file && !loading`，即目前 `.distribution-summary` 原本所在的 `v-else` 分支條件）。

### Template（`DistributionPanel.vue:2-10`，header）

原本：

```html
  <section
    class="distribution-panel"
    :class="{ 'distribution-panel--full': isFullStage }"
  >
    <div class="distribution-header">
      <div v-if="fileName" class="distribution-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

改為（新增 `.distribution-summary`，放在 `.distribution-file` 前面；條件比照原本 `.distribution-summary` 所在分支：`file` 存在且不在 loading 中）：

```html
  <section
    class="distribution-panel"
    :class="{ 'distribution-panel--full': isFullStage }"
  >
    <div class="distribution-header">
      <div v-if="file && !loading" class="distribution-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ allRows.length }} 筆資料</span>
      </div>
      <div v-if="fileName" class="distribution-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

### Template（`DistributionPanel.vue`，原本 `.distribution-summary` 所在位置）— 移除獨立一行

原本（`v-else` 分支內）：

```html
      <div v-else>
        <div class="distribution-summary">
          <span>{{ previewColumns.length }} 個欄位</span>
          <span>{{ allRows.length }} 筆資料</span>
        </div>

        <div
          class="distribution-chart-grid"
```

改為（整段 `.distribution-summary` 移除）：

```html
      <div v-else>
        <div
          class="distribution-chart-grid"
```

### CSS — `.distribution-header`／`.distribution-summary`／`.distribution-file` 都不需要改

`.distribution-header` 本來就是 `display:flex; justify-content:space-between; align-items:center; gap:12px`，兩個子元素（`.distribution-summary`、`.distribution-file`）不需要額外 flex 屬性，`space-between` 就會自動把統計文字推左、檔名推右。`.distribution-summary` 現有樣式（`display:flex; gap:14px; color:#475569; font-size:13px`）搬進 header 後外觀不變，不需要改。

## 不涉及的部分

- 兩個檔案的 `<script setup>` 邏輯（`chartData`、CSV 解析、`columnsReady`、`hasTarget` 等 computed/ref）完全不變，只動 template 結構位置與少數 CSS 屬性。
- Distribution 的 full 段位 grid 排版（`.distribution-chart-grid--full`、`isFullStage`）不受影響——本次改動的 `.distribution-summary` 完全在 grid 之外的 header 區塊。
- `.claude/ux-issues.md` #17（full 切換過場動畫）、#18（full 段位內部捲動 flex chain bug）不在本次範圍。

## 驗證方式

手動在瀏覽器開啟 workflow 畫面：

- **Data Table**：上傳 CSV，切到 Data Table 節點。暫停等待選 target 時：確認 header 左側仍顯示藍色/綠色 guide 提示卡（跟改之前一樣），body 最上方**不再**顯示統計文字（只剩欄位設定表格）。按下「繼續」後：確認 header 左側變成統計文字（「N 個欄位 / M 筆已讀取」），跟右側「已選檔案：X.csv」同一行；body 依然沒有獨立的統計文字行。
- **Distribution**：上傳 CSV，切到 Distribution 節點。確認統計文字（「N 個欄位 / M 筆資料」）跟「已選檔案：X.csv」同一行顯示（統計在左、檔名在右），原本圖表上方的獨立統計行消失。切換 drawer 段位（collapsed/expanded/full）確認 header 這行在各段位都正常顯示，不影響 #2 的 grid 排版功能。
- 兩邊都測：檔案很少欄位、很多欄位的情況，確認統計文字跟檔名不會擠壓換行跑版。
