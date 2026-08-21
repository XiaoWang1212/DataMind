# Workflow 驗證方式設定 UI Design Spec

## 背景

後端 `WorkflowService`（`backend/services/workflow/workflow_service.py`）已完整支援 5 種驗證方式（`k_fold`、`group_k_fold`、`random_sampling`、`leave_one_out`、`test_on_test`/`test_on_train`）及其對應參數（`n_splits`、`n_repeats`、`train_size`、`stratified`、`group_column` 等，見 `_normalize_validation_config`，`workflow_service.py:92-123`），但前端完全沒有 UI 讓使用者設定這些參數——`testScore` 節點的 `TestScorePanel.vue` 只是唯讀的結果表格，`SettingsPanel.vue` 也沒有驗證方式分頁。`validation` 設定目前只能透過論文萃取（Gemini）或匯入 JSON 檔案間接帶入，使用者無法在畫布上手動調整或選擇。

參考 Orange Data Mining 的 Test & Score widget（6 種驗證方式：Cross validation、Cross validation by feature、Random sampling、Leave one out、Test on train data、Test on test data），在 `SettingsPanel.vue` 新增一個「驗證方式」分頁，讓使用者能直接設定。

## 範圍

- 新增：`SettingsPanel.vue` 第 5 個分頁「驗證方式」，UI 互動模式參考 Orange（radio 選一種方式，選中才展開對應子參數），視覺風格沿用 DataMind 現有面板樣式（不是深色重現 Orange）
- 新增：extraction prompt 的範例 schema 補上 `n_repeats`、`group_column` 兩個欄位，讓論文萃取也能填出 `random_sampling`/`group_k_fold` 需要的參數
- **不**動後端 `workflow_service.py` 的驗證邏輯（已經完整支援，不需要改）
- **不**動 `TestScorePanel.vue`（維持唯讀結果表格）

## 資料流與節點歸屬

`validation` 設定實際存在 `testScore` 節點的 `config.validation`（執行時 `useWorkflowExecution.ts:80` 從這裡讀），不是 `settings` 節點自己的 config。新分頁放在 `SettingsPanel.vue`（`settings` 節點的面板）裡，但讀寫的目標是 `testScore` 節點：

- **讀取初始值**：`WorkflowWorkspace.vue` 計算 `testScoreValidationConfig = nodes.value.find(n => n.id === 'testScore')?.data.config.validation`，往下傳給 `WorkflowOptionsPanel` → `SettingsPanel`
- **寫回**：沿用既有的 `update-config` 事件機制（`WorkflowOptionsPanel.vue` 的 `emit('update-config', {nodeId, config})`，`WorkflowWorkspace.vue` 的 `handleUpdateConfig` 已經支援依 `nodeId` 更新任意節點），新增的 handler 固定傳 `nodeId: 'testScore'`，不是 `props.selectedNode.id`
- **論文萃取初始化**：已經有在運作，不需要額外接線——`useWorkflowImport.ts:94` 匯入框架時，`workflow_json.validation`（Gemini 萃取填的）已經直接寫進 `testScoreNode.data.config.validation`，正好是新分頁讀寫的同一個位置

**Group column 下拉選單的欄位清單**：從 `dataTable` 節點的 `config.columnConfig`（`{name, type, role}[]`）取，同樣需要 `WorkflowWorkspace.vue` 多算一個 prop 往下傳（`nodes.value.find(n => n.id === 'dataTable')?.data.config.columnConfig`）

## UI 設計

**`SettingsPanel.vue`**：`STEPS` 陣列從 `['前處理', '特徵工程', '模型', '信賴區間']` 改成 `['前處理', '特徵工程', '模型', '驗證方式', '信賴區間']`（驗證方式插在模型之後、信賴區間之前），新增對應的 `step-body`。

6 個 radio 選項對應後端方法（`test_on_test` 對應到的視覺上拆成兩個 radio，因為 Orange 也是分開顯示，選哪個只是 `method` 值不同）：

| Radio 標籤 | `method` 值 | 選中展開的子參數 |
|---|---|---|
| Cross validation | `k_fold` | Number of folds（數字輸入，對應 `n_splits`）、Stratified（checkbox） |
| Cross validation by feature | `group_k_fold` | Number of folds（`n_splits`）、Group column（下拉選單，對應 `group_column`） |
| Random sampling | `random_sampling` | Repeat train/test（數字，對應 `n_repeats`）、Training set size（百分比，對應 `train_size`）、Stratified |
| Leave one out | `leave_one_out` | 無 |
| Test on train data | `test_on_train` | Training set size（`train_size`）、Stratified |
| Test on test data | `test_on_test` | Training set size（`train_size`）、Stratified |

切換 radio 時，`method` 改變，但保留使用者已經輸入過的其他欄位值在 local state 裡（不因為切換方式又切回來就重填預設值，減少使用者重複輸入）。

**元件/props/emit 改動：**

- `SettingsPanel.vue`：新增 `validation: Record<string, unknown>` 和 `datasetColumns: Array<{name: string, type: string, role: string}>` 兩個 prop，新增 `update-validation` emit（payload 為完整 `validation` 物件）
- `WorkflowOptionsPanel.vue`：新增 `validationConfig`、`datasetColumns` 兩個 prop（從父層 `WorkflowWorkspace.vue` 傳入），傳給 `SettingsPanel`；新增 `handleSettingsValidationUpdate(value)` handler，內容是 `emit('update-config', { nodeId: 'testScore', config: { validation: value } })`
- `WorkflowWorkspace.vue`：計算 `testScoreValidationConfig`、`dataTableColumns` 兩個 computed，傳給 `WorkflowOptionsPanel`

## 論文萃取範例 schema 補欄位

`backend/services/gemini_service.py` 的 `_WORKFLOW_EXAMPLE`（第 49-54 行附近）目前的 `validation` 範例只有 `method`/`n_splits`/`stratified`/`train_size`。補上 `n_repeats`（給 `random_sampling` 用）和 `group_column`（給 `group_k_fold` 用），讓 Gemini 知道這兩個欄位的存在與命名，論文提到重複抽樣次數或分組驗證欄位時才有機會被萃取出來。不改「填寫原則」段落文字（那段已經是「依論文驗證方式，若未提及則用預設值」，邏輯上已經涵蓋這兩個新欄位，不需要額外強調）。

## 錯誤處理 / 相容性

- 舊專案/舊框架的 `testScore` 節點若沒有 `validation` 欄位（或欄位不完整），新分頁比照現有 `SettingsPanel` 其他分頁的寫法（例如 `step.strategy ?? 'mean'`），每個輸入都用 `??` 給合理預設值，不會因為缺欄位而報錯
- `group_column` 下拉選單若 `dataTableColumns` 是空陣列（使用者還沒設定資料表欄位），顯示為停用狀態或提示文字，不阻擋其他驗證方式的選擇

## 測試

- 前端無單元測試框架，用 `npm run type-check` + 人工瀏覽器驗證：
  - 開一個已有 workflow 的專案，進 `settings` 節點，確認新分頁「驗證方式」存在，且能看到目前的驗證設定（如果框架萃取時有帶，應該會直接顯示萃取結果）
  - 切換 6 種驗證方式，確認對應子參數正確展開/收合，輸入數值後，回到已執行過的 `testScore` 節點確認設定有正確反映（或至少確認 `nodes` 狀態、瀏覽器 Network 送出的 `validation_config` payload 正確）
  - 選 Cross validation by feature，確認 Group column 下拉選單有列出目前資料表的欄位
  - 執行一次 workflow，確認新設定的驗證方式真的被後端採用（例如選 leave_one_out 觀察執行時間/結果明顯不同於預設 k_fold）
- 後端 prompt 調整無法自動化測試，用已知有「重複抽樣」或「分組驗證」描述的論文樣本重新萃取，確認 `n_repeats`/`group_column` 有機會被填出來（若手邊沒有這種樣本 PDF，這步驟可以跳過，不阻擋本次功能上線）
