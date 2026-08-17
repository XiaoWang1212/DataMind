# Workflow 編輯中斷與結果失效 Design Spec

## 背景

目前 `WorkflowWorkspace.vue` 只有在編輯 `dataTable`（欄位設定）節點時，才會清空既有的 `workflowResult` 並把下游流程拉回 `dataTable`（`handleUpdateConfig` 裡的 dataTable 分支 → `clearSettingsDownstream()` + `snapFlowToDataTable()`）。編輯 `settings` 節點（前處理/特徵工程/驗證方式/信賴區間）完全沒有對應的失效邏輯——使用者可以在有結果、甚至有 job 正在跑的情況下，直接改掉模型設定，畫面卻完全沒有反應，容易讓使用者誤以為看到的結果對應現在的設定。

而且既有的 dataTable 失效邏輯本身就有兩個問題：
1. **靜默執行，沒有任何確認**——使用者可能不小心點到、或沒意識到會把結果清掉。
2. **視覺殘留 bug**：`clearSettingsDownstream()` 只清掉「被砍掉的節點」（`model-*`/`computeCi`）的 `nodeStatuses`，但 `testScore`/`featureImportance`/`confusionMatrix` 這些一直留在畫布上的靜態節點，即使模型都被砍了、結果都被清空了，它們的 `nodeStatuses` 仍然是 `'finished'`（對應 `useWorkflowNodes.ts:67` 的 `colorClass: status === 'finished' ? 'node-yellow' : ...`），畫面上會繼續顯示黃色「已完成」，跟實際狀態不符。
3. **race condition**：如果編輯當下還有一個 `pollJob()` 的 `setInterval` 在跑（對應編輯前那次執行的 job），它之後 poll 到 `status: 'done'` 還是會把 `workflowResult.value = job.result`（`useWorkflowExecution.ts:160`），把剛清空的結果又蓋回去。

這次要做的：把「編輯 settings/dataTable 節點時中斷並清空結果」這件事做成一個統一、對稱、有確認、視覺正確的機制，同時修掉上面三個既有問題。

## 範圍

- 前端：`WorkflowWorkspace.vue`、`useWorkflowExecution.ts` 改動；新增一個確認 modal 元件
- **不**動後端。「中斷」只在前端層面生效——停止 polling、忽略該 job 的結果，但後端的模型訓練執行緒會繼續跑完，只是沒人理會其結果。這是明確的取捨（後端合作式取消機制成本高、Python thread 無法強制終止，只能靠迴圈內檢查點，範圍大很多），不在這次範圍內。
- **不**加畫布鏡頭平移（Vue Flow 的 `setCenter`）。導向節點沿用既有的 `selectedNodeId` + `expandDrawer()` 慣用法。
- 觸發範圍限定在「經過 `handleUpdateConfig` 的 `update-config` 事件」——也就是 `SettingsPanel.vue`（前處理/特徵工程/驗證方式/信賴區間分頁）跟 `DataTablePanel.vue`（欄位設定表格）觸發的編輯。加/移除模型（`handleAddModel`/`handleRemoveModel`，畫布上直接點的按鈕）維持既有的立即生效行為，不納入這次的確認流程。

## 核心流程

**觸發條件**：`handleUpdateConfig` 收到 `nodeId === 'settings'` 或 `nodeId === 'dataTable'` 的事件時，同時符合以下兩者才會進入中斷流程：
1. 目前有東西可能因為這次編輯而失效——`workflowResult.value !== null`（有結果）或 `activeJobId.value !== null`（job 正在跑）
2. 這次的新設定值跟目前節點上的設定值**真的不一樣**（用一個通用的深度比對函式，取代目前只用在 dataTable 的 `columnConfigEqual`，同時套用在 settings 的各個子欄位）

不符合以上任一條件（沒有結果可失效、或值根本沒變）時，維持現有行為：直接套用，不彈窗、不中斷。

**符合條件時**：
1. 不立刻把新設定寫進 `nodes.value` 對應節點的 `data.config`，改為存進一個新的 `pendingConfigChange` ref，彈出確認 modal
2. 使用者按「確定中斷」：
   - 把 `pendingConfigChange` 的內容套用進節點設定（沿用各自既有的套用邏輯——dataTable 走 `clearSettingsDownstream()` + `snapFlowToDataTable()`，settings 走現有分支對應的設定寫入）
   - 執行「下游結果失效」：清空 `workflowResult`；把 `testScore`/`featureImportance`/`confusionMatrix` 這些靜態結果節點的 `nodeStatuses` 條目重置（不是只篩掉已從 `nodes.value` 移除的節點，而是明確地把這幾個一定會留在畫布上的節點狀態重置），讓它們的顏色正確地退回預設（非黃色）
   - 如果有 job 正在跑（`activeJobId.value !== null`）：呼叫新的 `abandonActiveJob()`（停掉 `pollJob()` 的 `setInterval`、清空 `activeJobId`），後端執行緒繼續跑但前端不再理會其結果——順帶修掉 race condition，因為 interval 真的被停掉了，不會有「舊 poll 蓋掉新清空結果」的情況
   - 導向被編輯的節點：`selectedNodeId.value = <editedNodeId>` + `expandDrawer()`（沿用既有慣用法）
3. 使用者按「取消」：
   - 丟棄 `pendingConfigChange`，不套用、不清空任何東西
   - 觸發面板重新掛載（透過一個可遞增的 `panelResetKey`，綁在 `WorkflowOptionsPanel` 或對應子面板的 `:key` 上），讓面板從（沒被改動過的）節點設定重新初始化本地狀態，畫面上的欄位值回到編輯前的樣子

## 確認 Modal

新增一個小型確認對話框元件，比照既有的 `InsertChartDialog.vue` 用 Vuetify 的 `v-dialog`/`v-card`/`v-card-title`/`v-card-text`/`v-card-actions` 寫法，維持風格一致。內容：標題「確定要中斷嗎？」，內文依情境略有不同措辭（有 job 在跑 vs 只是有既有結果），兩個按鈕「取消」/「確定中斷」。

## 錯誤處理 / 邊界情況

- 使用者在沒有結果、沒有 job 在跑時編輯設定：完全不受影響，維持現有的即時套用行為
- 使用者連續快速編輯（例如在 modal 還開著時又點了別的欄位）：modal 開啟期間，面板本身的互動不特別鎖定（YAGNI，這次不加輸入鎖），但 `pendingConfigChange` 只會保留「觸發 modal 的那一次」變更；如果需要更嚴謹的鎖定行為，之後再視實際使用體驗補上
- `abandonActiveJob()` 呼叫時 `activeJobId` 已經是 `null`（例如 job 剛好在同一時刻自然完成）：函式內做 `if (activeJobId.value === null) return` 這類防禦，不重複處理
- 頁面重新整理後：`activeJobId`/`workflowResult` 都會存進 `localStorage`（既有的 `saveState()`），如果中斷發生在重整之前，`activeJobId` 已經被清成 `null` 並存檔，重整後 `resumeJob()` 不會誤接回被放棄的 job

## 測試

- 前端無 vitest。用 `npm run type-check` 做語法/型別檢查
- 人工瀏覽器驗證：
  1. 執行一次 workflow 到完成，編輯 dataTable 欄位設定 → 應彈出確認 modal；按確定中斷 → 結果清空、`testScore`/`featureImportance`/`confusionMatrix` 節點顏色退回預設（不再黃）、畫面跳到 dataTable 節點設定面板
  2. 同上但改成編輯 settings（例如切換一個前處理選項）→ 一樣彈窗、一樣正確失效、跳到 settings 節點
  3. 執行中（job 正在跑，還沒完成）時編輯 settings → 彈窗；確定後停止輪詢、`activeJobId` 清空、畫面不再顯示訓練進度動畫（後端可能還在跑，但前端已經放棄）
  4. 彈窗時按取消 → 面板欄位值回到編輯前，`workflowResult`/`nodeStatuses` 都不變
  5. 沒有結果、沒有 job 在跑時編輯任何設定 → 完全不彈窗，維持現有行為
