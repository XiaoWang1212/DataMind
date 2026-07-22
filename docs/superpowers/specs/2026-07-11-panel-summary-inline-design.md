# Data Table／Distribution 欄位統計文字搬到跟檔名同一行 設計

日期：2026-07-11
範圍：`frontend/src/components/workflow/nodePanel/DataTablePanel.vue`、`frontend/src/components/workflow/nodePanel/DistributionPanel.vue`

要處理的問題：Data Table／Distribution 面板的欄位統計文字獨佔一行，想搬到跟檔名同一行。

## 背景

兩個節點面板都各自把「N 個欄位 / M 筆資料」這行統計文字，獨立顯示在 header（「已選檔案：X.csv」那行）下方，另起一行：

- `DataTablePanel.vue`：`.data-table-header`（3-19 行）顯示 `.data-table-guide`（暫停等待選 target 的藍色/綠色提示卡，`props.loading && columnsReady` 時顯示）+ `.data-table-file`（檔名，靠右對齊）；`.data-table-summary`（統計文字）則在下面 `.data-table-body`（34 行起）最上方獨立一行。
- `DistributionPanel.vue`：`.distribution-header`（2-10 行）只有 `.distribution-file`；`.distribution-summary`（統計文字）在下面另起一行（23-26 行）。

目標：統計文字搬到跟檔名同一行顯示，省掉獨立一行的空間。

> **實作階段的修正（2026-07-11）**：原設計原本打算把 `.data-table-body` 內獨立一行的統計文字整個移除（暫停等待選 target 時，統計文字完全不顯示，只有按下「繼續」後才在 header 出現）。使用者在驗證時指出這樣暫停期間會看不到統計文字，體驗上等於暫時消失；修正為「統計文字永遠可見，只是位置會換」：暫停等待選 target 時，統計文字留在 `.data-table-body` 原本的位置（`.data-table-summary`，維持原本 `margin-bottom:12px` 的區塊樣式）；按下「繼續」、guide 消失後，才改在 header 顯示（改用新的 `.data-table-summary-inline` class，`flex:1 1 auto; min-width:0`，接手 guide 原本的插槽）。這兩個 class 分開是因為同一個元素不可能同時滿足「body 區塊要有下方留白」跟「header flex row 裡要撐滿橫向剩餘空間」兩種互斥的排版需求。下方「改動 1」已更新為修正後的版本。Distribution 沒有暫停狀態，不受影響，維持原設計。

> **`/code-review` 後的追加修正（2026-07-11）**：8 個角度的自動 review 抓到 1 個真的 bug、5 項 Minor 建議，使用者要求一併處理：
> 1. **Bug（已修）**：`DistributionPanel.vue` 的 `.distribution-header` 用 `justify-content:space-between` 定位，但檔案讀取中（`loading` 為 true）那個短暫時間窗口 header 只剩「已選檔案」一個子元素，單一子元素在 `space-between` 下會貼左，等統計文字出現後檔名會從左跳到右。修法：比照 `DataTablePanel.vue` 的 `.data-table-file`，幫 `.distribution-file` 補上 `flex-shrink:0; margin-left:auto`，讓它不管旁邊有沒有統計文字都固定貼右，不再依賴 `space-between` 的雙子元素假設。
> 2. **狀態判斷整併（已修）**：`DataTablePanel.vue` 原本在 header（2 處）跟 body（1 處）各自獨立檢查 `props.loading`/`columnsReady`，3 個地方各自重複判斷同一件事（現在該顯示 guide、統計文字、還是都不顯示）。新增一個 `headerState` computed（`'guide' | 'summary' | 'none'`）作為唯一判斷來源，header 兩處分支跟 body 的顯示條件都改成讀這個 computed，不再各自重複判斷邏輯。
> 3. **CSS 重複（已修）**：`.data-table-summary`（body 版本）與 `.data-table-summary-inline`（header 版本）原本各自完整寫一份 `display:flex; gap:14px; color:#475569; font-size:13px`，只有少數屬性不同。改成用共用選擇器（`.data-table-summary, .data-table-summary-inline { ... 共同屬性 ... }`）宣告共同部分，各自只保留差異屬性（`margin-bottom` vs. `flex/min-width`）。
> 4. **順便補上防護（已修）**：`.data-table-summary-inline` 原本沒有跟 `.data-table-guide` 一樣的換行保護，窄螢幕+長檔名時兩個統計文字可能被擠到換行、撐高 header。補上 `white-space:nowrap`，避免這個情況。
> 5. **文字/markup 重複（暫不處理）**：header 跟 body 的兩個 `<span>` 統計文字內容目前逐字重複兩份（各自屬於互斥狀態，一次只會顯示一份）。要完全消除重複需要另外拆一個小元件（例如 `DataTableSummaryStats.vue`）承載這兩行文字，對兩行靜態文字來說有點小題大作，這次先不做。
> 6. **Distribution 的條件小重複（暫不處理）**：`DistributionPanel.vue` header 的 `v-if="file && !loading"` 跟下面 `v-if="!file"`/`v-else`/`v-if="loading"`/`v-else` 這條鏈在概念上有一點重疊，但兩處目前都正確、只是分開兩個地方各自表達同一件事；風險低、修起來效益也低，這次先不動。

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
      <div v-else-if="columnsReady" class="data-table-summary-inline">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

`columnsReady` 是既有的 computed（模板已在別處使用，如 `v-else-if="!columnsReady"`）；`.data-table-summary-inline` 是新增的 class（見下方 CSS 段落），跟 body 原本的 `.data-table-summary` 分開，因為兩者排版需求互斥（見下方說明）。

### Template（`DataTablePanel.vue:34-38`）— body 內的統計文字改成「只在暫停時顯示」

原本：

```html
    <div v-else class="data-table-body">
      <div class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>

      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

改為（`.data-table-summary` 保留在原位置，但加上 `v-if="props.loading"`——只有暫停等待選 target、header 顯示 guide 時才在這裡出現；按下「繼續」後這裡就不再顯示，改由 header 的 `.data-table-summary-inline` 接手）：

```html
    <div v-else class="data-table-body">
      <div v-if="props.loading" class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>

      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

（這裡不需要再檢查 `columnsReady`——能進到 `.data-table-body` 就代表 `columnsReady` 已經是 true。）

### CSS（`DataTablePanel.vue:520-527`）— 新增 `.data-table-summary-inline`，`.data-table-summary` 維持原樣不動

`.data-table-summary`（body 區塊版本）維持原本樣式不變（`margin-bottom:12px`，區塊間距用得到）。在它後面新增一條給 header 插槽用的 `.data-table-summary-inline`：

```css
  .data-table-summary {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
    margin-bottom: 12px;
  }

  .data-table-summary-inline {
    display: flex;
    flex: 1 1 auto;
    min-width: 0;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }
```

`.data-table-summary-inline` 拿掉 `margin-bottom`（不需要跟下面留白，因為它在 header 一整行裡），補上 `flex: 1 1 auto; min-width: 0;`，讓它跟 `.data-table-guide` 一樣能撐滿 header 左側可用空間，接手 guide 原本的位置。兩個 class 分開是因為同一個元素不可能同時滿足「body 區塊要有下方留白」跟「header flex row 裡要撐滿橫向剩餘空間」兩種互斥的排版需求。

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
- full 切換過場動畫、full 段位內部捲動的 flex chain bug，不在本次範圍。

## 驗證方式

手動在瀏覽器開啟 workflow 畫面：

- **Data Table**：上傳 CSV，切到 Data Table 節點。暫停等待選 target 時：確認 header 左側仍顯示藍色/綠色 guide 提示卡（跟改之前一樣），body 最上方**依然**顯示統計文字（「N 個欄位 / M 筆已讀取」，維持原本位置與間距）。按下「繼續」後：確認 header 左側變成統計文字，跟右側「已選檔案：X.csv」同一行；body 這時**不再**顯示獨立的統計文字行（已搬到 header）。
- **Distribution**：上傳 CSV，切到 Distribution 節點。確認統計文字（「N 個欄位 / M 筆資料」）跟「已選檔案：X.csv」同一行顯示（統計在左、檔名在右），原本圖表上方的獨立統計行消失。切換 drawer 段位（collapsed/expanded/full）確認 header 這行在各段位都正常顯示，不影響 #2 的 grid 排版功能。
- 兩邊都測：檔案很少欄位、很多欄位的情況，確認統計文字跟檔名不會擠壓換行跑版。
