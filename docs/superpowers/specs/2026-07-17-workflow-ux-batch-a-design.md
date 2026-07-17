# Workflow UX 批次 A 設計

> 三個互不相干的 Workflow UI 小修正，同一批處理。
> 共同前提：不碰 workflow 狀態機（`continueWorkflow` / `nodeStatuses` / `pausedAtNodeId`），那屬於後續的跨節點「上一步＋重置」工作。

## Settings「繼續」按鈕依步驟改文案與行為

**現況**：`SettingsPanel.vue` 的按鈕永遠顯示「繼續」，且不論在哪一步都 `emit('continue')`（觸發父層 `continueWorkflow` 啟動 workflow）。四個步驟分頁（前處理／特徵工程／模型／信賴區間）本來就能自由點擊切換。

**改法（全部在 `SettingsPanel.vue` 內，父層不動）**：
- 主按鈕文案：`currentStep < 3 ? '下一步' : '執行'`。
- 主按鈕點擊行為：`currentStep < 3` → `currentStep++`（只切分頁，不呼叫後端）；`currentStep === 3` → `emit('continue')`（維持既有啟動路徑）。
- disabled：「下一步」永遠可按；「執行」在 `props.models.length === 0` 時 disabled。等同 `:disabled="currentStep === 3 && props.models.length === 0"`，disabled 樣式的 class 同步收窄到這個條件。
- 「上一步」按鈕：**僅限 Settings 分頁內導覽**。`currentStep > 0` 時顯示（第 1 步前處理 `currentStep === 0` 直接 `v-if` 隱藏，不是 disabled），點擊 `currentStep--`。footer 版面為「上一步（左）／下一步 or 執行（右）」。此按鈕**只做 `currentStep--`**，不觸發任何執行狀態重置——跨節點的上一步＋下游重置屬於後續批次，不在此。

**不變**：`WorkflowWorkspace` 仍只在最後一步收到 `continue`，`continueWorkflow` 完全不受影響。模型分頁的「必填」badge 維持。

## Settings 模型列 icon 與文字垂直對齊

**現況**：模型列（`SettingsPanel.vue` Step 2 的 `item-row`）用 `item-head--top`（`align-items: flex-start` + 圓點 `.item-idx` `margin-top: 2px`），這是當初為「名稱換行時圓點/✕維持在首行」加的。單行名稱時圓點視覺偏低。

**改法（純 CSS）**：模型列改用基礎 `.item-head`（`align-items: center`，與前處理／特徵工程列一致），移除 `item-head--top` 這個 modifier 的使用，並刪掉只服務它的兩條 CSS 規則（`.item-head--top` 與 `.item-head--top .item-idx`）。名稱換行的少數情況圓點會垂直置中，可接受。

## 模型節點不可選取

**現況**：畫布層已設 `elements-selectable="false"`，但點模型節點仍會 `emit('select-node')` → `handleSelectNode()` → 開啟該節點的面板。游標沿用 vue-flow 預設，看起來可互動。

**改法**：
- 不開面板：`WorkflowWorkspace.handleSelectNode()` 開頭加守門 `if (nodeId.startsWith('model-')) return`（單一守門點；`onNodeClick` 內既有的 `userHasPanned = true` 維持，不影響平移意圖）。
- 看起來不可點：`useWorkflowNodes.ts` 的 `canvasNodes` computed 給 `model-*` 節點的 `data` 注入 `nonInteractive: true`；`IconNode.vue` 讀這個旗標，把 `.icon-node-wrap` 的 `cursor` 設為 `default`（畫布 pane 為 `grab`，模型節點不再暗示可互動）。

## 測試

無自動測試。`npm run dev` 手動驗：
1. Settings 四步：前三步顯示「下一步」且只切分頁、第 4 步顯示「執行」且啟動 workflow；「執行」在無模型時 disabled，「下一步」永遠可按；第 1 步無「上一步」，第 2–4 步有「上一步」且只往回切分頁。
2. 模型列圓點與名稱垂直對齊。
3. 點模型節點不開面板；游標非手指。

收尾：`npm run build`（vue-tsc 型別檢查）＋ `npm run lint`。
