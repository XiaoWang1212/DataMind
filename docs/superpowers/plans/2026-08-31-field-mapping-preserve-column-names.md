# 欄位對齊後保留原始欄位名稱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 欄位對齊完成後，資料集欄位維持使用者原始命名（不再被改寫成論文變數名稱），同時讓工作區的「套用建議」自動偵測目標欄位功能繼續正常運作。

**Architecture:** 欄位對齊頁停止呼叫 `rewriteDataset` 的改名功能（只保留刪除未使用欄位）；工作區原本靠「欄位名稱 === 論文變數名稱」的字串比對來自動抓目標欄位，改成明確透過專案已存的 `columnMapping`（論文變數 → 使用者原始欄名）查找，找不到才 fallback 回原始變數名稱（等同現在的降級行為）。純前端改動，後端與資料流程不受影響。

**Tech Stack:** Vue 3 + `<script setup>` + TypeScript, Pinia (`projectStore`)

**Spec:** `docs/superpowers/specs/2026-08-31-field-mapping-preserve-column-names-design.md`

## Global Constraints

- 後端不得修改：後端只認識執行當下傳入的實際欄位字串，不依賴欄位名稱與論文變數名稱一致。
- 未被任何變數認領的欄位維持現狀直接從資料集移除（`dropColumns` 邏輯不變）。
- 這個專案的前端目前沒有任何自動化測試框架（`frontend/package.json` 沒有 `vitest`/`jest`/`@vue/test-utils`，也沒有既有 `*.test.ts`/`*.spec.ts` 檔案）。不要為了這個小改動另外引入測試框架；改用 `npm run type-check` 做靜態驗證，並在最後一個任務用瀏覽器手動走一次完整流程驗證行為（照 CLAUDE.md 對前端改動的要求）。

---

## Task 1: 欄位對齊頁停止改寫欄位名稱

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue:470-484`（`confirmAndRun` 函式開頭）

**Interfaces:**
- Consumes: 既有的 `rewriteDataset(file, renameByColumn, dropColumns)`（`frontend/src/utils/dataset.ts:217`）、既有的 `unusedColumns` computed、既有的 `mapping`（`Record<string, { column: string, type: string }>`，本任務不變動它的建構或存檔邏輯）。
- Produces: 之後任務都不依賴這個任務新增的介面，純粹是行為變更。

- [ ] **Step 1: 修改 `confirmAndRun`，`rewriteDataset` 不再傳入改名對照表**

把現在的：

```ts
    try {
      saveError.value = ''

      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, info] of Object.entries(mapping)) {
        renameByColumn.set(info.column, variable)
      }

      // 沒被任何變數（含自訂變數）認領的原始欄位，之後在 workflow 就不會再出現
      const dropColumns = new Set(unusedColumns.value.map(c => c.name))

      // 先改寫檔案再寫資料庫，避免寫檔失敗但對映已存檔，下次用到未改寫的資料集
      const renamed = await rewriteDataset(datasetFile.value, renameByColumn, dropColumns)
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))
```

改成：

```ts
    try {
      saveError.value = ''

      // 沒被任何變數（含自訂變數）認領的原始欄位，之後在 workflow 就不會再出現
      const dropColumns = new Set(unusedColumns.value.map(c => c.name))

      // 只刪未使用欄位，不改寫欄位名稱：資料集維持使用者原始命名。
      // 論文變數 ↔ 欄位的對應關係已經存進 columnMapping（下面 saveColumnMapping），
      // 工作區會用那份資料查找目標欄位，不再靠欄位名稱跟變數名稱字串相符
      const renamed = await rewriteDataset(datasetFile.value, new Map(), dropColumns)
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))
```

（`mapping` 變數的建構、`renamed` 之後的用法、`saveColumnMapping(projectId.value, mapping)` 呼叫都維持原樣，不要動。）

- [ ] **Step 2: 靜態型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 沒有新增的型別錯誤（`renameByColumn` 已經整段移除，確認沒有其他地方還在引用它）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "fix: keep original column names when confirming field mapping"
```

---

## Task 2: 工作區目標欄位提示改用 columnMapping 查找

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue:287-291`（`testScoreTargetColHint` computed）

**Interfaces:**
- Consumes: 既有的 `projectStore`（`frontend/src/store/projectStore.ts`，已經在這個檔案第 167 行以 `const projectStore = useProjectStore()` 取得）、既有的 `projectId`（`computed(() => route.query.project as string | undefined)`，這個檔案第 165 行）、`Project.columnMapping?: Record<string, { column: string, type: string }> | null`（`frontend/src/store/projectStore.ts:9-27`）。
- Produces: `testScoreTargetColHint`（`ComputedRef<string>`）的回傳值語意改變——現在回傳的是**使用者的原始欄名**（查得到時），不是論文變數名稱；這個值會繼續原封不動傳給 `WorkflowOptionsPanel` 的 `target-col-hint` prop（第 91 行 `:target-col-hint="testScoreTargetColHint"`），介面型別（`string`）不變，Task 3 依賴這個語意變更去更新註解。

- [ ] **Step 1: 修改 `testScoreTargetColHint` computed**

把現在的：

```ts
  const testScoreTargetColHint = computed<string>(() => {
    const node = nodes.value.find(n => n.id === 'testScore')
    const val = node?.data.config.targetCol
    return typeof val === 'string' ? val : ''
  })
```

改成：

```ts
  const testScoreTargetColHint = computed<string>(() => {
    const node = nodes.value.find(n => n.id === 'testScore')
    const val = node?.data.config.targetCol
    if (typeof val !== 'string' || !val) return ''

    // val 是論文變數名稱（例如 "readmission_30d"）。欄位對齊已經不改寫欄位名稱了，
    // 資料集裡不會直接有這個名字的欄位，所以要透過 columnMapping 查回使用者的原始欄名；
    // 查不到（沒使用框架、專案還沒存過 mapping、或這個變數沒被對應到任何欄位）就
    // fallback 用原始變數名稱，效果等同「比對失敗、不顯示套用建議按鈕」
    const mapping = projectId.value
      ? projectStore.projects.find(p => p.id === Number(projectId.value))?.columnMapping
      : undefined
    return mapping?.[val]?.column ?? val
  })
```

- [ ] **Step 2: 靜態型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 沒有新增的型別錯誤。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "fix: resolve target-column hint through columnMapping instead of raw variable name"
```

---

## Task 3: 更新 DataTablePanel 裡過時的註解

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue:327-328`

**Interfaces:**
- Consumes: Task 2 產生的 `testScoreTargetColHint`（透過 `WorkflowOptionsPanel` 轉傳的 `targetColumnHint` prop，型別、比對邏輯都不變，本任務不改程式碼，只改註解）。
- Produces: 無（純文件性修改）。

- [ ] **Step 1: 更新註解文字**

把現在的：

```ts
  // 框架建議的目標欄位名稱通常是對齊頁改名後的結果，會跟欄位名完全相符；
  // 找不到就不顯示「套用建議」按鈕，避免使用者點了卻沒反應
  const targetHintColumnIndex = computed(() => {
```

改成：

```ts
  // 這個 hint 是上層（WorkflowWorkspace.vue）用專案的 columnMapping 把論文變數名稱
  // 查回使用者原始欄名後才傳下來的；查不到對應關係時會 fallback 成原始變數名稱，
  // 這裡就會比對失敗、不顯示「套用建議」按鈕，避免使用者點了卻沒反應
  const targetHintColumnIndex = computed(() => {
```

- [ ] **Step 2: 靜態型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 沒有錯誤（純註解修改，這步只是保險）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "docs: clarify how the target-column hint is resolved"
```

---

## Task 4: 瀏覽器手動驗證完整流程

**Files:** 無程式碼異動，純驗證。

**Interfaces:**
- Consumes: Task 1-3 的全部改動。
- Produces: 無。

這個專案前端沒有自動化測試，這個任務用來取代「跑測試套件」——照 CLAUDE.md 的要求，前端改動要在瀏覽器裡實際走過一次再回報完成。

- [ ] **Step 1: 啟動前端開發伺服器**

Run: `cd frontend && npm run dev`
Expected: Vite 印出本機網址（通常是 `http://localhost:5173`），伺服器正常啟動不噴錯。

- [ ] **Step 2: 建立測試專案並選擇一個有 `target_col` 的框架**

在瀏覽器打開開發伺服器網址，走「建立專案」流程：選一個框架庫裡已存在的框架（不要選「不使用框架」），上傳任一份有欄位表頭的 CSV/Excel 測試檔（欄位名稱故意跟框架的論文變數名稱不同，例如用 `col_a`, `col_b` 這種通用命名，才驗證得出「沒被改名」）。

Expected: 建立成功後自動導向欄位對齊頁。

- [ ] **Step 3: 在欄位對齊頁完成對映並確認送出**

把至少一個使用者欄位對應到框架的目標變數（`target_col` 對應的那個論文變數），其餘欄位可以對應或跳過都行，按「確認」送出。

Expected: 沒有跳出「儲存失敗」錯誤訊息，頁面導向工作區（`/workflow?project=...`）。

- [ ] **Step 4: 確認資料集欄位名稱沒有被改寫**

在工作區的資料表（DataTable）步驟，檢視目前顯示的欄位名稱列表。

Expected: 欄位名稱是你上傳檔案裡的原始名稱（例如 `col_a`），不是框架的論文變數名稱；沒被任何變數對應到的欄位已經消失（維持現有的刪除行為）。

- [ ] **Step 5: 確認「套用建議」自動偵測目標欄位仍正常運作**

檢查資料表步驟裡，你在 Step 3 對應到 `target_col` 的那個欄位，是否出現「套用建議」按鈕（或已經自動被標成 Target）。點擊套用建議（如果沒有自動套用）。

Expected: 該欄位的 Role 被設成 `Target`，且是你在對齊頁選的那個欄位（用原始名稱對到），不是別的欄位。

- [ ] **Step 6: 確認「不使用框架」流程不受影響**

回到專案列表，重新走一次建立專案流程，這次選「不使用框架」。

Expected: 直接跳過欄位對齊頁進工作區，資料表步驟正常顯示原始欄位，沒有「套用建議」按鈕（因為沒有 `target_col` 可比對），跟修改前的行為一致。

- [ ] **Step 7: 記錄結果**

如果 Step 4-6 都符合預期，這個 plan 執行完畢，可以進入 finishing-a-development-branch 流程；如果有任何一步不符合預期，回頭檢查對應的 Task（Step 4 異常查 Task 1，Step 5 異常查 Task 2）。
