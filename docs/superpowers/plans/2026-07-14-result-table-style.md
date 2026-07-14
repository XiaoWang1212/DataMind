# Test & Score 與 Feature Importance 表格樣式統一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Test & Score 與 Feature Importance 兩個結果表格改成同一套「資料表風」樣式（白底細框、灰 header、列分隔線、hover 高亮、數字右對齊）。

**Architecture:** 純樣式改動，兩個 panel **各自維持自己的 `<style scoped>`**，不抽共用 CSS、不抽共用元件——使用者預期這兩個表格之後會分開演化，提早抽共用層會讓分歧變成「要不要破壞共用元件」的兩難。代價是兩份樣式各寫各的、日後改配色要改兩處，這是明確接受的取捨。`<script>` 一行不動，資料計算、文案、i18n 全不碰。

**Tech Stack:** Vue 3 `<script setup lang="ts">` SFC、scoped CSS。無新增套件、無新增檔案。

## Global Constraints

- 本專案前端未設置任何自動化測試框架（無 vitest/jest，`package.json` 沒有 `test` script）。改動以「啟動 `npm run dev`、在瀏覽器手動操作驗證」取代自動化測試步驟；**若執行者無法完成手動驗證，必須明確說明「無法測試 UI」，不能逕自宣稱驗證通過**。
- **`npm run lint` 在本專案 baseline 就是紅的，不能拿它當閘門**。閘門是 `npm run build`（`vue-tsc` type-check + `vite build`）。
- **Commit 前必須先取得使用者明確同意**：完成實作、跑完 `npm run build`、並列出手動驗證步驟後，必須停下來明確詢問使用者，取得明確答覆後才能執行 `git add` / `git commit`。即使透過 `superpowers:subagent-driven-development` 執行，也要覆蓋掉 implementer 預設會自動 commit 的行為。
- Commit 訊息**一行就好**，不加 `Co-Authored-By` trailer。
- **只動這兩個檔案**。不要動 `ComputeCiPanel.vue`、`DataTablePanel.vue`、`PreprocessorPanel.vue`、`SettingsPanel.vue`、`FeatureEngineeringPanel.vue`，也不要新增任何全域 CSS 檔。
- ~~**不要動 `<script setup>`**：兩個 panel 的 props、computed、格式化函式（`formatImportance`）全部原樣保留。改動限於 `<template>` 的 class 與 `<style scoped>`。~~ **（2026-07-14 作廢）** Task 3 的轉置改了 `TestScorePanel.vue` 的 computed；Feature Importance 的 fold 聚合也會需要新的 computed。
- 精確色碼與數值（**逐字照抄，不要自行微調**）：
  - 表格外框：`1px solid rgba(148, 163, 184, 0.22)`
  - 列分隔線：`1px solid rgba(148, 163, 184, 0.16)`
  - Header 底色：`#f8fafc`；Header 文字：`#475569`、`12px`、`font-weight: 600`
  - 列 hover 底色：`rgba(0, 93, 255, 0.035)`
  - 左欄（Metric / Feature）文字：`#1e293b`、`font-weight: 600`
  - 儲存格 padding：`11px 14px`；字級 `13px`
  - 圓角：`12px`（表格與卡片一致）
  - 數字欄一律 `text-align: right` + `font-variant-numeric: tabular-nums`
- **不要用斑馬紋**。有了列分隔線之後，斑馬紋是重複的視覺噪音；列的區辨改靠 hover。
- Spec 來源：`docs/superpowers/specs/2026-07-14-result-table-style-design.md`

---

## File Structure

| 檔案 | 職責 | 本次改動 |
|---|---|---|
| `frontend/src/components/workflow/nodePanel/TestScorePanel.vue` | Test & Score 節點的唯讀面板：把執行結果攤成 metric（列）× model（欄）矩陣 | template 的數值格加 `table-cell--num`；`<style scoped>` 整段改寫成資料表風 |
| `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue` | Feature Importance 節點的唯讀面板：模型卡片 → split → 兩欄表（Feature / Importance） | template 不動；`<style scoped>` 整段改寫成資料表風，並補上三個目前完全沒有 CSS 規則的 class |

兩個檔案都已存在，不新增檔案。兩個 Task 彼此**沒有依賴**，可獨立驗證、獨立 commit。

---

## Task 1: `TestScorePanel.vue` 改成資料表風

> **已完成（2026-07-14，`cfe259c`）**。步驟全部照計畫走，另依實機回饋加了兩處本計畫沒寫的間距調整：`.workflow-summary` 改成 `gap: 10px; padding: 0;`（原 `gap: 14px; padding: 10px 0;`），並新增 `.table-row--header .table-cell { padding: 8px 14px; }` 讓標題列比資料列矮。
>
> **接著又做了 Task 3 的轉置**（模型當列、metric 當欄），所以本任務下方保留的「metric×model 矩陣」描述、`grid-template-columns: 160px …`、以及 `.table-cell--metric` 都**已經是舊的**。要看目前的結構請直接讀 `TestScorePanel.vue` 或 spec 的「改動 3」。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue:18-27`（template 的資料列）
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue:80-166`（整段 `<style scoped>`）

**Interfaces:**
- Consumes: 無。`props.summary`、`modelNames` / `modelSplits` / `metricKeys` / `matrixRows` 這些 computed 全部**原樣不動**。
- Produces: 無新的函式/型別/props/emits。新增一個 CSS class `table-cell--num`（數字欄），僅在本檔案內使用。

- [ ] **Step 1: template 的數值格加上 `table-cell--num`**

把（`TestScorePanel.vue:18-27`）：

```html
      <div v-for="row in matrixRows" :key="row.metric" class="table-row">
        <div class="table-cell table-cell--metric">{{ row.metric }}</div>
        <div
          v-for="(value, index) in row.values"
          :key="`${row.metric}-${modelNames[index]}`"
          class="table-cell"
        >
          {{ value }}
        </div>
      </div>
```

改成（只有 `class` 那一行變了）：

```html
      <div v-for="row in matrixRows" :key="row.metric" class="table-row">
        <div class="table-cell table-cell--metric">{{ row.metric }}</div>
        <div
          v-for="(value, index) in row.values"
          :key="`${row.metric}-${modelNames[index]}`"
          class="table-cell table-cell--num"
        >
          {{ value }}
        </div>
      </div>
```

Header 那一列（`TestScorePanel.vue:6-16`）**完全不動**——`table-cell--model` 的兩行堆疊只改 CSS，不改 class。

- [ ] **Step 2: 整段替換 `<style scoped>`**

把 `TestScorePanel.vue:80-166` 的 `<style scoped>` **整段**換成下面這份（`.workflow-summary`、`h4`、`.summary-empty` 三條原樣保留，其餘全部改寫）：

```css
<style scoped>
  .workflow-summary {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 10px 0;
  }

  .workflow-summary h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }

  .summary-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
  }

  .table-row {
    display: grid;
    grid-template-columns: 160px repeat(auto-fit, minmax(120px, 1fr));
    gap: 0;
    align-items: center;
  }

  /* 分隔線掛在 row 上（不是 cell）：cell 的 border 會被 grid 的欄間切斷成一段一段 */
  .table-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .table-row:not(.table-row--header):hover {
    background: rgba(0, 93, 255, 0.035);
  }

  .table-row--header {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
  }

  .table-cell {
    padding: 11px 14px;
    color: #0f172a;
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: left;
  }

  .table-cell--metric {
    font-weight: 600;
    color: #1e293b;
  }

  /* tabular-nums：讓各模型的分數逐位對齊，比置中好比較 */
  .table-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* 表頭的模型名/split 名靠右，才會跟底下那一整欄的數字對齊 */
  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 3px;
    align-items: flex-end;
    background: transparent;
  }

  .model-name {
    font-weight: 700;
    color: #1f2937;
    font-size: 12px;
  }

  .model-split {
    font-size: 11px;
    font-weight: 400;
    color: #94a3b8;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

**這次刻意刪掉的三條規則**（不要留著）：

- `.table-row:not(.table-row--header) { background: #ffffff; }` 與 `.table-row:nth-child(even):not(.table-row--header) { background: #f8fafc; }`——斑馬紋。有列分隔線就不需要，而且 `nth-child(even)` 依賴 header 是第一個子元素，很脆弱。
- `.table-row:last-child .table-cell { border-bottom: none; }`——死規則。cell 本來就沒有 `border-bottom`，這條什麼都沒關掉。
- `.table-cell--metric` 原本的 `background: rgba(226, 232, 240, 0.25)`——左欄靠字重就夠跟數字區分，多一塊底色會把表格看起來切成兩半，而且它會蓋掉整列的 hover 高亮。

- [ ] **Step 3: 建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過（`vue-tsc` + `vite build` 都不報錯）。這一步只能抓語法錯誤，**不能證明視覺效果正確**，下一步一定要接著手動驗證。

- [ ] **Step 4: 手動驗證（需要瀏覽器操作；無法操作瀏覽器時必須明確說明「無法測試 UI」，不可宣稱驗證通過）**

執行（若尚未啟動）：

```bash
cd frontend && npm run dev
```

在瀏覽器開 `http://localhost:3000/workflow`。**這個 panel 要有 `workflowResult` 才會顯示表格**（沒有時顯示「尚未有測試評分結果…」）。`workflowResult` 存在 localStorage（`WorkflowWorkspace.vue:489` 還原），所以用一個**已經跑完 workflow 的既有專案**即可，不必重跑；若手上沒有，就上傳 CSV、在 Settings 加 2 個以上模型跑完一次。點 Test & Score 節點開啟面板，確認：

1. **Header 是灰底不是藍底**：標題列底色是淺灰 `#f8fafc`，不再是原本的藍 `#e7f0ff`。
2. **沒有斑馬紋**：所有資料列都是白底，不再一深一淺交錯。
3. **有列分隔線**：每一列之間有一條細灰線。
4. **數字靠右且逐位對齊**：任兩個分數（例如 `0.8421` 與 `0.9013`）的小數點在同一條垂直線上。
5. **hover 整列高亮**：滑鼠移到任一資料列，**整列**（含左邊的 metric 名稱那格）變成淡藍底——如果 metric 那格沒跟著變色，代表 `.table-cell--metric` 的背景色沒刪乾淨。
6. **表頭對齊**：模型名與 split 名（兩行堆疊）靠右，跟底下那一欄的數字對齊。
7. **模型多時不爆版**：跑 4 個以上模型 → 表頭的模型名不溢出格子；長模型名（如 `RandomForestClassifier`）會換行而不是把欄寬撐爆。
8. **空狀態沒壞**：開一個沒跑過的新專案 → 顯示「尚未有測試評分結果，請執行 Workflow 後在此查看。」，沒有殘留的空表格外框。

- [ ] **Step 5: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「Test & Score 表格已改成資料表風，`npm run build` 通過。麻煩實際在瀏覽器看一下（尤其是 hover 整列會不會亮、以及模型多的時候表頭會不會擠爆），確認沒問題後再讓我 commit。」等待使用者明確回覆「可以」或指出問題，才能進到下一步。

- [ ] **Step 6: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/components/workflow/nodePanel/TestScorePanel.vue
git commit -m "style: restyle test & score table as a data table"
```

---

## Task 2: `FeatureImportancePanel.vue` 改成資料表風

> **暫緩，且本任務的作法已作廢（2026-07-14）**。下面這套「純換 `<style scoped>`」的改法實機試過後還原了——它會造成框中框，而且沒解決真正的問題：10-fold 下每個模型的 feature importance 被重複列 10 遍。正確解法是先把 fold 聚合掉（詳見 spec 開頭的「實作階段的修正」）。**不要照下面的步驟做**；等使用者與組員確認是否聚合後，重寫這個任務。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue:149-229`（整段 `<style scoped>`）

**Interfaces:**
- Consumes: 無。`props.workflowResult`、`rawResults` / `importanceResults` / `groupedResults` 這些 computed 與 `formatImportance()` 全部**原樣不動**。
- Produces: 無新的函式/型別/props/emits。Template 也不動——現有的 class（`importance-list` / `importance-split-list` / `importance-split` / `importance-split__title` / `importance-cell--feature` / `importance-cell--value`）已經夠掛樣式，其中前四個目前在 CSS 裡**完全沒有對應規則**。

- [ ] **Step 1: 整段替換 `<style scoped>`**

Template **完全不動**。把 `FeatureImportancePanel.vue:149-229` 的 `<style scoped>` **整段**換成下面這份：

```css
<style scoped>
  .feature-importance-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 10px 0;
  }

  .feature-importance-panel h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }

  /* 這條目前不存在：沒有它，模型超過一個時卡片會直接黏在一起
     （.feature-importance-panel 的 gap 只作用在它的直接子元素上，管不到 .importance-list 內部） */
  .importance-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .importance-card {
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.16);
  }

  /* 補一條底線：卡片 header 與表格 header 都是 #f8fafc，
     沒有分界的話會看成兩條連在一起的灰帶 */
  .importance-card__header {
    padding: 14px 16px;
    background: #f8fafc;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    display: flex;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .importance-card__title {
    font-weight: 700;
    color: #0f172a;
    font-size: 14px;
  }

  .importance-card__subtitle {
    font-size: 12px;
    color: #475569;
  }

  /* 這條目前不存在：表格加了外框後，需要 padding 把它跟卡片邊緣隔開 */
  .importance-split-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 14px 16px;
  }

  /* 這條目前不存在 */
  .importance-split {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  /* 這條目前不存在：split 名稱現在是無樣式的預設文字，
     降成 12px 灰字，讀起來才像表格的標籤而不是另一個標題 */
  .importance-split__title {
    font-size: 12px;
    color: #94a3b8;
  }

  .importance-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
  }

  .importance-row {
    display: grid;
    grid-template-columns: 1fr 120px;
    gap: 0;
    align-items: center;
  }

  .importance-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .importance-row:not(.importance-row--header):hover {
    background: rgba(0, 93, 255, 0.035);
  }

  .importance-row--header {
    font-size: 12px;
    font-weight: 600;
    background: #f8fafc;
    color: #475569;
  }

  /* padding 從 row 移到 cell：留在 row 上的話，加了外框之後
     hover 底色會在 padding 之外露出一圈白邊、鋪不滿整列 */
  .importance-cell {
    padding: 11px 14px;
    color: #0f172a;
    font-size: 13px;
    word-break: break-word;
  }

  .importance-cell--feature {
    font-weight: 600;
    color: #1e293b;
  }

  .importance-cell--value {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
    padding: 14px 16px;
  }
</style>
```

**跟改動前的差異一覽**（用來自查有沒有漏改）：

- `.importance-card` 圓角 `18px` → `12px`（跟表格一致）
- `.importance-card__header` 補 `border-bottom`
- `.importance-table` 補外框 + `12px` 圓角 + `overflow: hidden`
- `.importance-row` 的 `padding: 12px 16px` 移到 `.importance-cell` 的 `padding: 11px 14px`
- `.importance-row` 新增 `:not(:last-child)` 分隔線與 `:hover` 高亮
- `.importance-row--header` 的 `#f1f5f9` → `#f8fafc`、`font-weight: 700` → `600`、補 `font-size: 12px`、`color: #0f172a` → `#475569`
- `.importance-cell--feature` 的 `color: #1f2937` → `#1e293b` 並加 `font-weight: 600`
- `.importance-cell--value` 補 `font-variant-numeric: tabular-nums`
- 新增 `.importance-list` / `.importance-split-list` / `.importance-split` / `.importance-split__title` 四條規則

- [ ] **Step 2: 建置檢查**

Run:

```bash
cd frontend && npm run build
```

Expected: 通過。同樣**不能證明視覺效果正確**，下一步一定要接著手動驗證。

- [ ] **Step 3: 手動驗證（需要瀏覽器操作；無法操作瀏覽器時必須明確說明「無法測試 UI」，不可宣稱驗證通過）**

在瀏覽器開 `http://localhost:3000/workflow`（dev server 若未啟動，先 `cd frontend && npm run dev`）。同 Task 1，這個 panel 也要有 `workflowResult` 才會顯示表格，而且**該結果裡要有 `feature_importance`**（樹模型如 Random Forest / XGBoost 才會回傳；SVM 之類沒有）。點 Feature Importance 節點開啟面板，確認：

1. **表格有自己的外框**：每張模型卡片內，表格有 1px 細框 + 12px 圓角，且跟卡片邊緣有間距（不會貼齊卡片內緣）。
2. **卡片與表格圓角一致**：卡片外框的圓角看起來跟表格的一樣（都是 12px），不再是卡片比較圓。
3. **有列分隔線 + hover**：每一列之間有細灰線；滑鼠移到任一資料列，**整列**（含 Feature 名稱那格）變成淡藍底，且底色**鋪滿整列、邊緣沒有露白**——如果邊緣有一圈白邊，代表 padding 沒從 `.importance-row` 移到 `.importance-cell`。
4. **Feature 比 Importance 粗**：Feature 名稱是深色粗體，數值是一般字重、靠右對齊。
5. **多個模型不黏在一起**：跑 2 個以上會回傳 feature importance 的模型 → 卡片之間有 14px 間距，不是黏成一整塊。
6. **split 標題是小灰字**：表格上方的 split 名稱（如 `train_test`）是 12px 灰字，不是跟卡片標題一樣大的黑字。
7. **空狀態沒壞**：開一個沒跑過的新專案 → 顯示「尚未有特徵重要性結果，請執行 Workflow 後再查看。」，沒有殘留的空表格外框。
8. **跟 Test & Score 看起來像同一套**：在這兩個節點之間來回切換 → 外框粗細、圓角、header 的灰、字級、列高都一致。（此項需 Task 1 已完成。）

- [ ] **Step 4: 停下來，等待使用者確認**

不要執行下一步的 `git add` / `git commit`。明確詢問使用者：「Feature Importance 表格已改成資料表風，`npm run build` 通過。麻煩在瀏覽器對照 Test & Score 看一下兩者是不是同一套樣式，確認沒問題後再讓我 commit。」等待使用者明確回覆。

- [ ] **Step 5: Commit（僅在使用者確認沒問題後執行）**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue
git commit -m "style: restyle feature importance table to match test & score"
```

---

## Task 3: `TestScorePanel.vue` 表格轉置（模型當列、metric 當欄）

> **已完成（2026-07-14）**，在 Task 1 之後追加。理由見 spec 的「改動 3」：模型數會成長、metric 相對固定，讓會成長的那一維走垂直方向，表格才不會橫向擠爆；而且「一個模型一列」是 ML 模型比較表的領域慣例（sklearn / PyCaret 的 `compare_models`、論文結果表）。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue`（`<template>` 的表格、`<script>` 的 computed、`<style>` 的欄寬與列首）

**Interfaces:**
- Consumes: `props.summary`（形狀不變：`Array<{ model_name, split_name, metrics: Array<{ metric, valueFormatted }> }>`）。
- Produces: `modelRows` computed 取代 `matrixRows` / `modelNames` / `modelSplits`。`metricKeys` 保留，改當欄的來源。

- [x] **Step 1: `<script>` 收斂 computed**

刪掉 `modelNames`、`modelSplits`、`matrixRows`，改成單一 `modelRows`：

```ts
  const metricKeys = computed(() => {
    const keys = new Set<string>()
    for (const item of props.summary) {
      for (const metric of item.metrics) keys.add(metric.metric)
    }
    return Array.from(keys)
  })

  // 一個模型一列、metric 當欄：模型數會隨使用者加減而成長，metric 相對固定，
  // 讓會成長的那一維走垂直方向，表格才不會橫向擠爆
  const modelRows = computed(() =>
    props.summary.map(item => ({
      model_name: item.model_name,
      split_name: item.split_name,
      values: metricKeys.value.map(metricName => {
        const metric = item.metrics.find(m => m.metric === metricName)
        return metric?.valueFormatted ?? '-'
      }),
    })),
  )
```

- [x] **Step 2: `<template>` 換成模型列**

```html
    <div v-if="summary.length > 0" class="summary-table">
      <div class="table-row table-row--header">
        <div class="table-cell">Model</div>
        <div
          v-for="metricName in metricKeys"
          :key="metricName"
          class="table-cell table-cell--num"
        >
          {{ metricName }}
        </div>
      </div>

      <div v-for="row in modelRows" :key="row.model_name" class="table-row">
        <div class="table-cell table-cell--model">
          <div class="model-name">{{ row.model_name }}</div>
          <div class="model-split">{{ row.split_name }}</div>
        </div>
        <div
          v-for="(value, index) in row.values"
          :key="`${row.model_name}-${metricKeys[index]}`"
          class="table-cell table-cell--num"
        >
          {{ value }}
        </div>
      </div>
    </div>
```

metric 表頭套 `table-cell--num`（靠右），才會跟底下那一整欄的數字切齊。

- [x] **Step 3: `<style>` 調欄寬與列首**

- `grid-template-columns`：`160px repeat(auto-fit, minmax(120px, 1fr))` → `180px repeat(auto-fit, minmax(80px, 1fr))`（最左欄放模型名所以加寬；數值欄只放一個小數所以縮窄）
- `.table-cell--model`：`align-items: flex-end` → `flex-start`、`gap: 3px` → `2px`；`.model-name` 改 `font-size: 13px; font-weight: 600; color: #1e293b`（它現在是列首，不是表頭）
- `.table-cell--metric`：**整條刪除**（轉置後沒有消費者）

- [x] **Step 4: 建置檢查**

Run: `cd frontend && npm run build` — 通過。

- [x] **Step 5: 手動驗證**

使用者已在瀏覽器確認。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/TestScorePanel.vue
git commit -m "refactor: transpose test & score table to one row per model"
```

---

## Task 4: `TestScorePanel.vue` 標出每個 metric 的最佳模型

> 理由與安全性論證見 spec 的「改動 4」。關鍵前提：後端十個 score metric 全部越高越好，沒有反向指標；若日後新增 log loss / Brier score 之類，這個假設會失效。

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue`（`<template>` 的數值格、`<script>` 新增 `bestByMetric`、`<style>` 新增 `.table-cell--best`）

**Interfaces:**
- Consumes: `props.summary`（形狀不變）。刻意**不**更動 `useWorkflowExecution.ts` 的 `workflowSummary`——`valueFormatted` 是 `toFixed(4)` 的字串，`Number()` 解得回來，不需要為了比大小多帶一個原始數值欄位。
- Produces: `bestByMetric` computed；`modelRows` 的 `values` 由 `string[]` 變成 `{ metric: string, text: string, isBest: boolean }[]`。

- [ ] **Step 1: `<script>` 新增 `bestByMetric`，並改寫 `modelRows` 的 `values`**

在 `metricKeys` 之後插入：

```ts
  // 每個 metric 的最佳值（後端的 10 個 metric——accuracy / balanced_accuracy / precision /
  // recall / specificity / f1 / mcc / kappa / auc / auprc——全部都是越高越好，沒有反向指標）
  const bestByMetric = computed(() => {
    const best: Record<string, number> = {}
    for (const item of props.summary) {
      for (const metric of item.metrics) {
        const value = Number(metric.valueFormatted)
        if (Number.isNaN(value)) continue
        const current = best[metric.metric]
        if (current === undefined || value > current) best[metric.metric] = value
      }
    }
    return best
  })
```

`modelRows` 的 `values` 改成回傳物件：

```ts
      values: metricKeys.value.map(metricName => {
        const text
          = item.metrics.find(m => m.metric === metricName)?.valueFormatted ?? '-'
        const value = Number(text)
        return {
          metric: metricName,
          text,
          isBest:
            !Number.isNaN(value) && bestByMetric.value[metricName] === value,
        }
      }),
```

- [ ] **Step 2: `<template>` 的數值格掛上 `table-cell--best`**

```html
        <div
          v-for="cell in row.values"
          :key="`${row.model_name}-${cell.metric}`"
          class="table-cell table-cell--num"
          :class="{ 'table-cell--best': cell.isBest }"
        >
          {{ cell.text }}
        </div>
```

- [ ] **Step 3: `<style>` 新增 `.table-cell--best`**

插在 `.table-cell--num` 之後：

```css
  /* 該 metric 表現最好的模型。這是 leaderboard 真正要回答的問題，
     不用逐格比對小數點就看得出誰贏 */
  .table-cell--best {
    font-weight: 700;
  }
```

**只用字重、不加顏色**：藍色粗體試過，使用者選擇拿掉。表格已有 hover 的淡藍底，數值再上藍色會跟它競爭。

- [ ] **Step 4: 建置檢查**

Run: `cd frontend && npm run build`
Expected: 通過。

- [ ] **Step 5: 手動驗證（需要瀏覽器操作）**

開 Test & Score 面板，確認每一個 metric 欄裡數值最大的那一格是粗體，其餘為一般字重；平手時該平手的格子同時加粗。

- [ ] **Step 6: 停下來，等待使用者確認，取得同意後才 commit**

```bash
git add frontend/src/components/workflow/nodePanel/TestScorePanel.vue
git commit -m "feat: bold the best model per metric in test & score"
```
