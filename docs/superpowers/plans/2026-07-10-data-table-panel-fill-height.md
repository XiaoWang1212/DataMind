# Data Table Panel 欄位設定表格撐滿抽屜高度 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 Data Table 節點面板的「欄位設定」表格，跟著 drawer 目前的段位（collapsed 280px / expanded 54vh / full 90vh）動態撐滿高度，同時不比現在的固定 380px 還矮。

**Architecture:** 全部是既有元件 `<style scoped>` CSS 的調整，把 `flex:1; min-height:0` 沿著「drawer 內容容器 → panel → 表格區塊」這條既有的父子鏈一路往下傳，讓最內層的 `.data-table-column-settings` 改用 `flex:1 1 380px; min-height:380px` 取代目前寫死的 `max-height:380px`。不新增元件、不新增狀態、不動任何 `<script>` 邏輯。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC，scoped CSS，無額外套件。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。依照 `CLAUDE.md` 的慣例，本計畫不新增測試框架，全部改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟；若執行者（例如沒有瀏覽器操作能力的 subagent）無法完成手動驗證，必須明確說明「無法測試 UI」，不能逕自宣稱驗證通過。
- 純 CSS layout 調整，三個檔案皆不涉及 `<script>` 區塊或任何資料/互動邏輯變更。
- `.data-table-column-settings` 的高度地板固定為 `380px`（沿用目前既有的固定值，使用者已於 2026-07-10 確認）。
- 所有使用者可見文字維持繁體中文（本次改動不新增任何使用者可見文字，僅供後續改動參考）。
- Spec 來源：`docs/superpowers/specs/2026-07-10-data-table-panel-fill-height-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/components/workflow/WorkflowWorkspace.vue` | Drawer 外殼與內容捲動容器 | 幫 `.drawer-content-wrapper` 補上 flex 撐滿樣式 |
| `frontend/src/components/workflow/WorkflowOptionsPanel.vue` | Drawer 內容的節點面板路由（`.setting-area` 是它的元件根節點） | 幫 `.setting-area` 補上 `flex:1` |
| `frontend/src/components/workflow/nodePanel/DataTablePanel.vue` | Data Table 節點的欄位設定表格 | 幫 `<div v-else>` 補 class、幫 `.data-table-panel` 補 flex 撐滿樣式、把 `.data-table-column-settings` 從固定 `max-height` 改成「flex 撐滿 + 380px 地板」 |

這三個檔案原本就是「drawer → panel → 表格」這條父子鏈上既有的節點，本次不新增任何檔案。

---

## Task 1: Flex 撐滿容器鏈 + 380px 高度地板

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue:755-769`（`.options-drawer__scroll` CSS 區塊後方，新增 `.drawer-content-wrapper` 規則）
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue:394-404`（`.setting-area` CSS）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:34`（template，`<div v-else>` 補 class）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:459-463`（`.data-table-panel` CSS）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:483-485`（`.data-table-panel { position: relative; }` 區塊前方，新增 `.data-table-body` 規則）
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:534-543`（`.data-table-column-settings` CSS）

**Interfaces:**
- Consumes: 無（純 CSS 調整，不讀取任何 script 內的 ref/computed）
- Produces: 無新的函式/型別/props/emits。後續若有其他任務要動這幾個檔案的樣式，需知道：`DataTablePanel.vue` 的 `<div v-else>` 現在有 class `data-table-body`；`.data-table-column-settings` 不再有 `max-height`，改成 `flex: 1 1 380px; min-height: 380px`。

- [ ] **Step 1: `WorkflowWorkspace.vue` — 讓 drawer 內容包裹層撐滿捲動容器高度**

目前 `.options-drawer__scroll` 規則結尾是：

```css
  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    /* 永遠保留捲軸空間（兩側等寬），避免捲軸出現/消失時內容寬度跳動、且左右留白對稱 */
    scrollbar-gutter: stable both-edges;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar {
```

在 `.options-drawer__scroll` 規則和 `.options-drawer__scroll::-webkit-scrollbar` 之間，插入一條新規則（`.drawer-content-wrapper` 目前完全沒有樣式，對應 template 裡 `class="drawer-content-wrapper"` 的那個 div）：

```css
  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    /* 永遠保留捲軸空間（兩側等寬），避免捲軸出現/消失時內容寬度跳動、且左右留白對稱 */
    scrollbar-gutter: stable both-edges;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .drawer-content-wrapper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .options-drawer__scroll::-webkit-scrollbar {
```

- [ ] **Step 2: `WorkflowOptionsPanel.vue` — 讓面板根節點撐滿父層高度**

把：

```css
  .setting-area {
    border: none;
    border-radius: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
```

改成（加上 `flex: 1;`）：

```css
  .setting-area {
    flex: 1;
    border: none;
    border-radius: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
```

- [ ] **Step 3: `DataTablePanel.vue` — 幫欄位已解析完成的區塊補上 class**

把 template 裡：

```html
    <div v-else>
      <div class="data-table-summary">
```

改成：

```html
    <div v-else class="data-table-body">
      <div class="data-table-summary">
```

- [ ] **Step 4: `DataTablePanel.vue` — 讓 `.data-table-panel` 撐滿父層高度，並新增 `.data-table-body` 規則**

把：

```css
  .data-table-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
```

改成：

```css
  .data-table-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 14px;
  }
```

接著在下面的：

```css
  .data-table-panel {
    position: relative;
  }

  .data-table-header {
```

之間插入 `.data-table-body` 規則：

```css
  .data-table-panel {
    position: relative;
  }

  .data-table-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .data-table-header {
```

- [ ] **Step 5: `DataTablePanel.vue` — 表格區塊改成「flex 撐滿 + 380px 地板」**

把：

```css
  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    max-height: 380px;
    overflow: hidden;
  }
```

改成：

```css
  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }
```

- [ ] **Step 6: 型別/建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（type-check + vite build 都不報錯）。這一步只能抓出 template/CSS 語法或型別錯誤，不能證明排版視覺效果正確，下一步一定要接著手動驗證。

- [ ] **Step 7: 手動驗證（需要瀏覽器操作，無法操作瀏覽器時必須明確說明「無法測試 UI」而非宣稱驗證通過）**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開啟 `http://localhost:3000/workflow`，上傳一份欄位數中等（例如 8-15 欄）的 CSV，點選畫布上的 Data Table 節點，確認：

- Drawer 停在 collapsed（預設，280px）時：表格區塊維持原本可用高度，欄位若超出可視範圍，抽屜整體可以捲動查看，沒有版面跑掉或內容被夾死的情況。
- 把 drawer 手把往上拖到 expanded（54vh）：表格區塊明顯比 collapsed 時更高、貼齊可用空間，表格下方不再看到大片空白背景色。
- 把 drawer 繼續往上拖到 full（90vh）：表格區塊撐到接近整個 drawer 高度，「Reset / 繼續」兩個按鈕貼在區塊最底部。
- 換一份欄位很少（2-3 欄）的 CSV 重複以上三段測試：確認 expanded、full 時「Reset / 繼續」按鈕仍正確貼底，表格跟按鈕之間即使有空白也不會重疊、跑版。
- 換一份欄位很多（超過一屏可視範圍）的 CSV：確認表格內部（`.column-settings-body`）仍可正常捲動，欄位標題列（thead）仍然 sticky 在表格區塊頂端。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue frontend/src/components/workflow/WorkflowOptionsPanel.vue frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "fix: let data table column-settings fill drawer height at every stage"
```
