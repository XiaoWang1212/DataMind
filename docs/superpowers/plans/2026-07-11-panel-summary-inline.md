# Data Table／Distribution 欄位統計文字搬到跟檔名同一行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DataTablePanel.vue` 與 `DistributionPanel.vue` 的「N 個欄位 / M 筆資料」統計文字，改成跟「已選檔案：X.csv」同一行顯示，不再獨立佔一整行。

**Architecture:** 純 template 結構搬移 + 少量 CSS 屬性調整，兩個檔案的 `<script setup>` 邏輯完全不動。Data Table 因為有暫停等待使用者選 target 的狀態機，header 左側要做成「guide 提示卡／統計文字」互斥的同一個插槽（`v-if`/`v-else-if` 兩個分支共用同一個位置）；Distribution 沒有暫停狀態，統計文字單純搬進 header，用既有的 `justify-content: space-between` 自然分居兩側，不需要狀態切換。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC，scoped CSS，無額外套件。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。依照 `CLAUDE.md` 的慣例，改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟；若執行者無法完成手動驗證，必須明確說明「無法測試 UI」，不能逕自宣稱驗證通過。
- **Commit 前必須先取得使用者明確同意**：完成實作、跑完 `npm run build`、並列出手動驗證步驟後，必須停下來明確詢問使用者「瀏覽器手動測試沒問題了嗎？」，取得使用者明確答覆後才能執行 `git add` / `git commit`。即使透過 `superpowers:subagent-driven-development` 執行，也要覆蓋掉 implementer 預設會自動 commit 的行為。
- Data Table 的統計文字（`.data-table-summary`）在 header 只會在 `columnsReady === true` 且 guide 提示卡沒顯示時出現（`v-else-if`，跟 guide 互斥，不會同時顯示兩者，也不會兩者都不顯示）；`.data-table-body` 內原本獨立一行的統計文字要整個移除，不能兩處都保留造成重複。
- Distribution 的統計文字（`.distribution-summary`）搬進 header 後，顯示條件必須跟原本所在位置一致：`file && !loading`（不新增、不改變條件邏輯）。
- 兩個檔案本次都不改 `<script setup>` 區塊，只動 template 與 `<style>`。
- Spec 來源：`docs/superpowers/specs/2026-07-11-panel-summary-inline-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/components/workflow/nodePanel/DataTablePanel.vue` | Data Table 節點面板：欄位設定表格 + 暫停等待選 target 的提示卡 | header 內 guide/統計文字改成互斥插槽；body 內原本獨立一行的統計文字移除；`.data-table-summary` CSS 從獨立區塊改成 header 插槽樣式 |
| `frontend/src/components/workflow/nodePanel/DistributionPanel.vue` | Distribution 節點面板：CSV 預覽 + 圖表卡片 | 統計文字搬進 header，原本獨立一行移除 |

兩個檔案本身已存在，不新增檔案；兩者互相獨立，可分開驗證。

---

## Task 1: DataTablePanel.vue — header 插槽 + 移除 body 內獨立統計行

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:3-19`（template，`.data-table-header`）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:34-38`（template，`.data-table-body` 開頭）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:516-522`（style，`.data-table-summary`）

**Interfaces:**
- Consumes: 既有 computed/prop——`columnsReady`（既有 computed，模板已在別處使用如 `v-else-if="!columnsReady"`）、`props.loading`、`hasTarget`、`targetColumnName`、`previewColumns`、`previewDataRows`。全部既有，不新增。
- Produces: 無新的函式/型別/props/emits。`.data-table-summary` 這個 class 現在只出現在 header（不再出現在 body），後續若有人要調整這行文字的樣式，要記得只有一個生效位置。

- [ ] **Step 1: Header 內新增「統計文字」分支，跟 guide 互斥**

把（`DataTablePanel.vue:3-19`）：

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

改成（新增 `v-else-if="columnsReady"` 分支）：

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

- [ ] **Step 2: 移除 `.data-table-body` 內原本獨立一行的統計文字**

把（`DataTablePanel.vue:34-38`）：

```html
    <div v-else class="data-table-body">
      <div class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>

      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

改成：

```html
    <div v-else class="data-table-body">
      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
```

- [ ] **Step 3: `.data-table-summary` CSS 從獨立區塊改成 header 插槽樣式**

把（`DataTablePanel.vue:516-522`）：

```css
  .data-table-summary {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
    margin-bottom: 12px;
  }
```

改成（拿掉 `margin-bottom`，補上 `flex: 1 1 auto; min-width: 0;`，讓它跟 `.data-table-guide` 一樣撐滿 header 左側可用空間）：

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

- [ ] **Step 4: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（`vue-tsc` type-check + `vite build` 都不報錯）。這一步只能抓出 template/CSS/型別錯誤，不能證明排版視覺效果正確，下一步一定要接著手動驗證。

- [ ] **Step 5: 手動驗證（需要瀏覽器操作，無法操作瀏覽器時必須明確說明「無法測試 UI」而非宣稱驗證通過）**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開啟 `http://localhost:3000/workflow`，上傳一份 CSV，切到 Data Table 節點，確認：

- 暫停等待選 target 時（`繼續` 按鈕還沒按）：header 左側顯示藍色 guide 提示卡（跟改之前一樣，文字內容不變），`.data-table-body` 最上方**不再**顯示「N 個欄位 / M 筆已讀取」這行。
- 在 Role 欄選好 Target 之後（guide 變綠色「已選定目標變數...」）：header 左側依然是 guide（還沒按繼續），不是統計文字。
- 按下「繼續」之後：header 左側從 guide 變成統計文字（「N 個欄位 / M 筆已讀取」），跟右側「已選檔案：X.csv」同一行顯示；`.data-table-body` 依然沒有獨立的統計文字行、只剩欄位設定表格。
- 換一份欄位很少（2-3 欄）跟很多（10+ 欄）的 CSV 各測一次，確認統計文字跟檔名不會擠壓換行、版面正常。

- [ ] **Step 6: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「已經跑完 `npm run build` 並列出手動驗證步驟，麻煩實際在瀏覽器測過暫停中／已選 target／按下繼續三種狀態，確認沒問題後再讓我 commit。」等待使用者明確回覆「可以」或指出問題，才能進到下一步。

- [ ] **Step 7: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "fix: move data table column summary into header row"
```

---

## Task 2: DistributionPanel.vue — 統計文字搬進 header

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:6-10`（template，`.distribution-header`）
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue:22-26`（template，原本 `.distribution-summary` 所在位置）

**Interfaces:**
- Consumes: 既有 computed/prop/ref——`file`（prop）、`loading`（ref）、`fileName`（computed）、`previewColumns`（ref）、`allRows`（ref）。全部既有，不新增。
- Produces: 無新的函式/型別/props/emits。`.distribution-summary` 這個 class 現在只出現在 header（不再出現在圖表上方）。不影響 `isFullStage`／`.distribution-chart-grid--full`（full 段位 grid 排版功能），兩者是 header 內外不同區塊。

- [ ] **Step 1: Header 內新增統計文字**

把（`DistributionPanel.vue:6-10`）：

```html
    <div class="distribution-header">
      <div v-if="fileName" class="distribution-file">
        已選檔案：{{ fileName }}
      </div>
    </div>
```

改成（新增 `.distribution-summary`，放在 `.distribution-file` 前面；條件比照原本 `.distribution-summary` 所在分支：`file` 存在且不在 loading 中）：

```html
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

- [ ] **Step 2: 移除原本圖表上方獨立一行的統計文字**

把（`DistributionPanel.vue:22-26`）：

```html
      <div v-else>
        <div class="distribution-summary">
          <span>{{ previewColumns.length }} 個欄位</span>
          <span>{{ allRows.length }} 筆資料</span>
        </div>

        <div
          class="distribution-chart-grid"
```

改成：

```html
      <div v-else>
        <div
          class="distribution-chart-grid"
```

**注意**：`.distribution-header`（CSS 已是 `display:flex; justify-content:space-between; align-items:center; gap:12px`）、`.distribution-summary`（CSS 已是 `display:flex; gap:14px; color:#475569; font-size:13px`）、`.distribution-file` 三條 CSS 規則都不需要改，`justify-content:space-between` 會自動把兩個子元素分居兩側。

- [ ] **Step 3: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（`vue-tsc` type-check + `vite build` 都不報錯）。

- [ ] **Step 4: 手動驗證（需要瀏覽器操作，無法操作瀏覽器時必須明確說明「無法測試 UI」而非宣稱驗證通過）**

在瀏覽器開啟 `http://localhost:3000/workflow`（dev server 若未啟動，先 `cd frontend && npm run dev`），上傳一份 CSV，切到 Distribution 節點，確認：

- 統計文字（「N 個欄位 / M 筆資料」）跟「已選檔案：X.csv」同一行顯示，統計在左、檔名在右；原本圖表上方的獨立統計行消失。
- 拖曳 drawer 到 collapsed / expanded / full 三個段位，確認這行 header 在各段位都正常顯示，不影響 full 段位的 grid 排版（`.distribution-chart-grid--full`）。
- 換一份欄位很少（2-3 欄）跟很多（10+ 欄）的 CSV 各測一次，確認統計文字跟檔名不會擠壓換行、版面正常。

- [ ] **Step 5: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「已經跑完 `npm run build` 並列出手動驗證步驟，麻煩實際在瀏覽器測過 collapsed / expanded / full 三段的 Distribution header 顯示，確認沒問題後再讓我 commit。」等待使用者明確回覆「可以」或指出問題，才能進到下一步。

- [ ] **Step 6: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/components/workflow/nodePanel/DistributionPanel.vue
git commit -m "fix: move distribution panel summary into header row"
```
