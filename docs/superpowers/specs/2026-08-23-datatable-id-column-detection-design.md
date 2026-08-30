# DataTable 疑似 ID 欄位偵測 Design Spec

## 背景

`DataTablePanel.vue`（workflow 畫布上 dataTable 節點的欄位設定面板）目前的初始化邏輯很陽春：`buildColumnSettings()` 裡每個欄位一律 `selectedRole = existing?.role ?? 'feature'`，沒有任何自動判斷。使用者每次上傳新資料集都要自己找出哪一欄該設成 `target`，也完全沒有防呆——如果不小心把病歷編號、案例 ID 這類欄位設成 `target`，會產生「每一筆都是不同類別」的退化模型，而且不會有任何提示，使用者要等到後面 workflow 執行完看到離譜的結果才會發現問題。

## 範圍

- 前端：`frontend/src/components/workflow/nodePanel/DataTablePanel.vue` 新增一個「疑似 ID 欄位」偵測函式，並用在兩個地方：初始化時的預設 `role`、選了 `target` 時的警告提示
- **不**動 `type`（型別）的偵測邏輯（`getColumnTypeCandidates`），只動 `role` 的預設值
- **不**阻擋使用者手動選擇——偵測到疑似 ID 只是改變預設值 + 顯示警告，使用者仍然可以照自己的判斷把任何欄位設成任何 role
- **不**動後端，這純粹是前端初始化體驗跟防呆提示的改善

## 偵測邏輯

新增 `isLikelyIdColumn(header: string, values: string[]): boolean`，符合以下任一條件即回傳 `true`：

1. **欄名比對**：把 `header` 依底線、連字號、空白、camelCase 邊界拆成單字（例如 `patient_id` → `['patient', 'id']`，`caseID` → `['case', 'ID']`，`ID` → `['ID']`），任一單字（不分大小寫）等於 `"id"` 即命中。這裡刻意不用簡單的 `header.endsWith('id')` 字串比對，因為那樣 `valid`、`android` 這類欄名會被誤判（`"valid".endsWith('id')` 為 `true`）。
2. **唯一值比例**：`values` 陣列（沿用既有 `getColumnRawValues` 那樣先過濾空字串）裡，唯一值數 ÷ 總筆數 > 0.95，且總筆數 ≥ 10（樣本太少時比例本身不可靠，例如只有 3 筆全部不同，不代表這是 ID 欄位）。

兩個條件用「或」——欄名符合就直接判定，不用再看數值分布；欄名沒特徵但數值幾乎全不重複，也判定為疑似 ID。

## 初始化行為

`buildColumnSettings()` 目前：
```typescript
const selectedRole = existing?.role ?? 'feature'
```
改成：在沒有既有設定（`existing` 為 `undefined`，也就是使用者第一次看到這份資料、還沒手動調整過）時，如果 `isLikelyIdColumn(header, columnValues)` 為真，預設 `role` 是 `'skip'`；否則維持現有的 `'feature'` 預設。已經有 `existing` 設定的欄位（使用者調整過，或是從已存的 `columnConfig` 還原）完全不受影響，一律沿用 `existing.role`——這個偵測只影響「全新資料集第一次載入」那一刻的預設值，不會覆蓋使用者已經做過的選擇。

## 警告提示

`ColumnSetting` 型別（或是渲染層的 computed）新增一個 `isLikelyId: boolean` 欄位，沿用同一個 `isLikelyIdColumn()` 判斷（跟初始化預設用同一份邏輯，只是這裡不影響 `role` 的值，純粹拿來決定要不要顯示提示）。

在 Role 欄位（`.role-select-wrap` 那個 `<td>`）裡，當 `column.role === 'target' && column.isLikelyId` 時，顯示一行小字警告：「這個欄位的值幾乎都不重複，可能不適合當分類目標」。純提示、不影響「繼續」按鈕的 `disabled` 狀態（`hasTarget` 邏輯不變），使用者看到警告後仍然可以選擇忽略、直接繼續。

## 錯誤處理 / 邊界情況

- 空欄位（全部是空字串）：唯一值比例分母（總筆數）用「非空值筆數」計算，避免全空欄位被唯一值比例誤判（0/0 情況要處理成不視為 ID，直接讓欄名比對決定）
- 只有欄名符合、資料量太小（<10 筆）：欄名比對不受樣本數限制，只要單字比對命中就算，樣本數門檻只套用在唯一值比例那個條件
- 使用者手動把某個欄位從 `skip` 改回 `feature` 或 `target`：這是正常操作，不受這次改動影響，`onRoleChange`（既有的「只能有一個 target」邏輯）維持不變

## 測試

- 前端無 vitest，用 `npm run type-check` 做語法/型別檢查
- 人工瀏覽器驗證：
  1. 上傳一份含 `patient_id`（或類似欄名）欄位的 CSV，確認該欄位初始化時 role 是 `Skip`，其餘一般欄位仍是 `Feature`
  2. 上傳一份沒有明顯 ID 欄名、但某欄位數值幾乎每筆都不同（例如流水號）的 CSV，確認該欄位一樣被預設成 `Skip`
  3. 把一個疑似 ID 欄位的 role 手動改成 `Target`，確認出現警告文字，且「繼續」按鈕不受影響（選了 target 就能按）
  4. 確認欄名像 `valid`、`android_version` 這類「結尾是 id 但不是獨立單字」的欄位不會被誤判成疑似 ID
  5. 重新整理頁面或切換節點再切回來，確認使用者手動調整過的 role 不會被這個偵測邏輯覆蓋回去
