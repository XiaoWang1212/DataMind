# Workflow UX 批次 B 設計：執行前回退 + 狀態機修正

> 核心是 workflow「上一步 + 下游重置」，順帶修同一塊狀態機的相關 bug，以及 DataTable 重選 target 的行為。
> 範圍限**執行前**（尚未按「執行」啟動 job 的設定階段）；執行一旦開始不在回退範圍，要重來＝整個重跑。

## 整體模型

把設定階段當成一條線性 stepper：`DataTable →（Settings：前處理→特徵工程→模型→信賴區間）→ 執行`。

- 前進：Settings footer 的「下一步」（tab 1–3）/「執行」（tab 4），沿用批次 A。
- 分頁回退：Settings footer 的「上一步」（tab 2–4），沿用批次 A（tab 1 不顯示）。
- **跨節點回退**：獨立控件（見下），從 Settings 回到 DataTable。

狀態集中在 `useWorkflowExecution`：`pausedAtNodeId`（`'dataTable' | 'settings' | null`）、`dataTableApplied`、`nodeStatuses`、`workflowResult`、`activeJobId`。

## 1. 跨節點「回 DataTable」控件

**現況**：Settings 沒有回上一個節點的入口；要回去只能點 DataTable 節點（且會踩到下述「繼續」按鈕缺暫停感知的問題）。

**改法**：
- `SettingsPanel.vue` 在步驟籤（`.wizard-tabs`）上方加一個 link 式按鈕「← 回 Data Table」，四個 tab 都顯示，樣式明顯有別於 footer 的實心按鈕（文字 + 左箭頭、無底色）。點擊 `emit('back-node')`。這是獨立於 batch A 分頁導覽的控件，不改動 footer 的上一步/下一步/執行。
- `WorkflowOptionsPanel.vue` 把 `back-node` 往上轉傳；`WorkflowWorkspace.vue` 接 `@back-node="handleBackToDataTable"`。
- `handleBackToDataTable()`：`pausedAtNodeId.value = 'dataTable'`；`selectedNodeId.value = 'dataTable'`；更新 `nodeStatuses`——`dataTable` 設為 `'running'`（等待中）、把 `settings` 的狀態移除（回到未完成）；`expandDrawer()`。**保留** Settings 既有設定（models / preprocessing / featureEngineering / compute_ci 全部不動）。

## 2. 「只有真的改了才重置」（只清流程/進度狀態）

**目標**：回 DataTable 後若真的改了 target/欄位設定，往前走時要「重置下游流程狀態」；沒改就直接前進、Settings 設定原封不動。範圍只清**流程/進度狀態**（`dataTableApplied` 等旗標與 `nodeStatuses` 的完成標記），**不清** Settings 設定。

**機制**：以 `dataTableApplied` 承載「是否需要重新確認」。
- `WorkflowWorkspace.handleUpdateConfig()` 收到 dataTable 的 `columnConfig` 時，把**新值與節點目前已存的 columnConfig 做深比對**（逐欄比 `name`/`type`/`role`）。只有在**確實不同**且原本 `dataTableApplied === true` 時，才 `dataTableApplied.value = false`。相同則不動（避免面板重掛時 emit 相同設定被誤判成改動）。
- 這取代目前那條窄的「沒有 target 才 reset」（`WorkflowWorkspace.vue:393-400`）——新邏輯涵蓋改名/改型別/改/移除 target 全部情況（「沒有 target」是其中一種）。
- 效果：回 DataTable 沒改 → `dataTableApplied` 維持 `true` → 直接按「繼續」前進、Settings 不動；有改 → `dataTableApplied` 變 `false` → 必須重按「繼續」（`dataTableCanContinue` 才會通過）＝重新確認。

## 3. 暫停視覺一致（settings 不再被標成 finished）

**現況**：`continueWorkflow` 在暫停到 settings 時把 `settings` 設成 `'finished'`（`useWorkflowExecution.ts:238-246`），於是節點變黃、`settings → 下一節點` 的線也變黃（`done = status === 'finished'`），看起來像已完成、可往下走；而 dataTable 暫停時是 `'running'`（spinner）。兩者不一致。

**改法**（`useWorkflowExecution.ts`）：
- dataTable→settings 分支：暫停到 settings 時，`settings` 設為 `'running'`（與 dataTable 暫停一致的 spinner），**不要**設 `'finished'`。
- settings→執行 分支開頭：使用者按「執行」後，先把 `settings` 設為 `'finished'`，再播放後續 pipeline 動畫。
- 結果：兩個暫停點視覺一致；暫停期間 `settings → 下一節點` 的線保持灰色（未完成），不再提早變黃。

> 註：更講究的「非 spinner 的等待態」（獨立 `'waiting'` 狀態）留作日後 polish，不在這批——這批只做到「不誤標 finished、兩點一致」。

**相容性（別踩壞還原邏輯）**：`WorkflowWorkspace.vue` 還原時 `pausedAtNodeId` 是直接從 localStorage 還原（`:486`），settings 暫停靠這個還原、不靠 `nodeStatuses`；而 `:496-516` 那段「job 遺失才退回 checkpoint」的啟發式只在 `pausedAtNodeId === null`（＝已按執行）時跑，用 `nodeStatuses.get('settings') === 'finished'` 判斷。因為本節在「按執行時」才把 settings 設 `'finished'`，該啟發式仍成立；settings **暫停期間**是 `'running'`，但那時 `pausedAtNodeId==='settings'`、啟發式不會跑。實作時不要為了這批去改那段 checkpoint 啟發式。

## 4. 拿掉硬編碼 target fallback

**現況**：`buildWorkflowPayload()` 的 `target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '是否跌倒'`（`useWorkflowExecution.ts:87`）在沒有 target 時掉回硬編碼「是否跌倒」。

**改法**：把 `?? '是否跌倒'` 改為 `?? ''`。執行路徑已被 `dataTableCanContinue` 閘門保證有 target，不該再猜一個欄位名；真的空字串代表上游閘門有漏，屬 bug 而非默默送假欄位。

## 5. DataTable「繼續」加暫停感知

**現況**：DataTable 的「繼續」只用 `!hasTarget` 決定 disable（`DataTablePanel.vue:135-143`），不看 `pausedAtNodeId`。流程推進到 settings 後回點 dataTable，「繼續」仍可按，按下去落進 `continueWorkflow` 的 settings 分支、跳出文不對題的「請至少新增一個模型」。

**改法**：
- `DataTablePanel.vue`：「繼續」按鈕 disable 條件改為 `!hasTarget || !props.loading`（`loading` 即 `pausedNodeId === 'dataTable'`，代表目前正停在 dataTable 這步）。
- `WorkflowWorkspace.handleApplyColumnConfig()`：開頭加防呆 `if (pausedAtNodeId.value !== 'dataTable') return`，即使按鈕被繞過也不會誤觸發 settings 分支。
- 回退情境相容：`handleBackToDataTable` 會把 `pausedAtNodeId` 設回 `'dataTable'`，屆時 `loading` 為 true、「繼續」恢復可按。

## 6. 重選 target 自動把舊 target 改回 feature

**現況**：`DataTablePanel.vue` 的 Role 下拉中，`target` 選項在「已有其他 target」時被 `:disabled`（`:94-98`），使用者選不了第二個 target，要換 target 得先手動把舊的改回別的角色。

**改法**（`DataTablePanel.vue`）：
- 移除 target 選項的 `:disabled`（連同不再使用的 `hasOtherTarget`），讓任一欄都能被選為 target。
- Role 下拉加 `@change="onRoleChange(index)"`：若該欄被設為 `target`，就把其他 `role === 'target'` 的欄位改回 `'feature'`（永遠只保留一個 target）。
- 既有的 `columnSettings` 深 watcher 會把新設定 emit 出去（`update-column-config`），因此改 target 也會經過第 2 節的變更偵測、`dataTableApplied` 轉 false，與回退重置一致。

## 測試

無自動測試。`npm run dev` 手動走這些情境：
1. 完整順跑：DataTable 選 target → 繼續 → Settings 四步 → 執行 → 有結果。
2. 暫停視覺：停在 Settings 時，settings 節點不是黃色、`settings → 下一節點` 的線是灰的（非黃、非 animated）。
3. 回退不改：Settings「← 回 Data Table」→ 不改任何東西 → 繼續 → 直接回到 Settings，模型/前處理等設定都還在。
4. 回退有改：回 DataTable → 改 target 或欄位 → 必須重按「繼續」才能前進（沒重按前進不了）。
5. 繼續按鈕暫停感知：流程推進到 Settings 後回點 dataTable 節點 →「繼續」不可按；不會跳「請至少新增一個模型」。
6. 重選 target：已有一個 target，去別欄選 target → 原 target 自動變回 feature，永遠只有一個 target。
7. 無 target 防呆：無 target 時無法送出（不會拿「是否跌倒」去打後端）。

收尾：`npm run build`（vue-tsc）。`npm run lint` 為既有壞基線，本批照現有檔案風格撰寫、不引入新種類問題。
