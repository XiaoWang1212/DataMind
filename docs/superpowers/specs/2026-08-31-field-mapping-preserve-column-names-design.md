# 欄位對齊後保留原始欄位名稱 — 設計

## 背景

欄位對齊頁（`FieldMappingView.vue`）目前在使用者確認對映後，會把資料集裡對到論文變數的欄位**實際改名**成該論文變數的名稱（例如把使用者的欄位改名成 `readmission_30d`），未對到任何變數的欄位則直接刪除。

框架的 workflowJson 會宣告一個 `target_col`（論文變數名稱，例如 `是否跌倒`）。工作區（`WorkflowWorkspace.vue` → `DataTablePanel.vue`）會拿這個名稱去跟目前資料表的欄位名稱做**完全字串比對**，比對成功才出現「套用建議」按鈕、自動把該欄位設成 Target 角色。這個比對之所以現在能成功，純粹是因為欄位已經被改名成論文變數名稱了——也就是說，「自動建議目標欄位」這個 UX 依賴於「欄位對齊會實際改寫欄位名稱」這個副作用。

現在要取消改名這個副作用，資料集欄位維持使用者原始命名，因此需要一個明確的查找機制取代原本隱性的字串比對。

## 目標

- 欄位對齊完成後，資料集裡的欄位名稱維持使用者上傳時的原始名稱，不再被覆寫成論文變數名稱。
- 未被任何變數（含自訂變數）認領的欄位，維持現狀直接從資料集移除。
- 工作區的「套用建議」自動偵測目標欄位功能維持正常運作，不因為停止改名而失效。
- 不改動後端；後端不需要知道也不依賴欄位名稱與論文變數名稱是否一致。

## 非目標

- 不處理 preprocessing / feature engineering 步驟裡可能出現的欄位名稱清單（`columns` 參數）。目前所有既有框架範本都沒有在這些步驟寫死論文變數名稱（都留白讓後端自動抓數值/類別欄位）；若未來 AI 產生的框架真的填了欄位清單，後端在找不到對應欄位時會自動略過（fallback 到全部/數值欄位），不會報錯，屬於已知且可接受的邊界情況，本次不處理。
- 不處理既有專案：已經完成過對齊、資料集已被改名過的舊專案不會被回溯還原成原始名稱。

## 設計

### 1. `FieldMappingView.vue` — 停止改寫欄位名稱

`confirmAndRun()` 目前呼叫：

```ts
const renamed = await rewriteDataset(datasetFile.value, renameByColumn, dropColumns)
```

改為呼叫時 `renameByColumn` 傳入空 Map，只保留 `dropColumns`：

```ts
const renamed = await rewriteDataset(datasetFile.value, new Map(), dropColumns)
```

`renameByColumn` 這個區域變數（原本用來反查「使用者欄位 → 論文變數」）不再需要建構，可以整段移除；`mapping`（存進 `project.columnMapping` 的那份，變數名 → `{ column: 使用者原始欄名, type }`）維持不變——這份資料本來記的就是使用者的原始欄名，不受影響。

### 2. `WorkflowWorkspace.vue` — 目標欄位提示改用對照表查找

`testScoreTargetColHint` 目前：

```ts
const testScoreTargetColHint = computed<string>(() => {
  const node = nodes.value.find(n => n.id === 'testScore')
  const val = node?.data.config.targetCol
  return typeof val === 'string' ? val : ''
})
```

改成先用目前專案的 `columnMapping` 把論文變數名稱反查成使用者的原始欄名：

```ts
const testScoreTargetColHint = computed<string>(() => {
  const node = nodes.value.find(n => n.id === 'testScore')
  const val = node?.data.config.targetCol
  if (typeof val !== 'string' || !val) return ''

  const mapping = projectId.value
    ? projectStore.projects.find(p => p.id === Number(projectId.value))?.columnMapping
    : undefined
  return mapping?.[val]?.column ?? val
})
```

查不到對應關係時（沒使用框架、專案還沒存過 mapping、或這個變數沒被使用者對應到任何欄位）就 fallback 回傳原始的 `val`，行為與現在相同（比對失敗、不顯示套用建議按鈕）。

`columnMapping` 的型別（`Record<string, { column: string, type: string }>`）已經存在於 project store，這裡只是多一層查找，不需要新增型別或 API。

### 3. `DataTablePanel.vue` — 只需更新註解

`targetHintColumnIndex` 的比對邏輯完全不用改，因為它收到的 `targetColumnHint` 已經是翻譯過的實際欄名。唯一要動的是這行過時的註解：

```ts
// 框架建議的目標欄位名稱通常是對齊頁改名後的結果，會跟欄位名完全相符；
// 找不到就不顯示「套用建議」按鈕，避免使用者點了卻沒反應
```

改為說明 hint 是由上層（`WorkflowWorkspace.vue`）透過專案的 `columnMapping` 查找後傳入的實際欄名，找不到對應時才會 fallback 成原始變數名稱、進而比對失敗。

## 測試

- 建立專案 → 選框架 → 上傳資料集 → 走到欄位對齊頁，對映若干欄位（含跳過部分欄位）並確認送出：
  - 驗證下載/檢視最終存進 IndexedDB 的資料集，欄位名稱與使用者原始上傳的檔案相同（未對映欄位仍被移除）。
  - 進入工作區的資料表步驟，確認「套用建議」按鈕會出現，點擊後正確把使用者原始欄名對應的那一欄設成 Target。
- 「不使用框架」流程（跳過欄位對齊）不受影響：`columnMapping` 不存在，`testScoreTargetColHint` 直接 fallback，行為與現況相同。
- 資料集裡沒有任何欄位對到 `target_col` 這個變數的情況（使用者跳過該變數的對映）：`columnMapping[val]` 不存在，fallback 回傳原始變數名稱，「套用建議」按鈕不出現，維持現況的降級行為（使用者手動在 Role 欄位選 Target）。
