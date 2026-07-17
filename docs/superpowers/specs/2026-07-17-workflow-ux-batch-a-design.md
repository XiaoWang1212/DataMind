# Workflow UX 批次 A 設計

> 三個互不相干的 Workflow UI 小修正，同一批處理。
> 共同前提：不碰 workflow 狀態機（`continueWorkflow` / `nodeStatuses` / `pausedAtNodeId`），那屬於後續的跨節點「上一步＋重置」工作。

## Settings「繼續」按鈕依步驟改文案與行為

**現況**：`SettingsPanel.vue` 的按鈕永遠顯示「繼續」，且不論在哪一步都 `emit('continue')`（觸發父層 `continueWorkflow` 啟動 workflow）。四個步驟分頁（前處理／特徵工程／模型／信賴區間）本來就能自由點擊切換。

**改法（全部在 `SettingsPanel.vue` 內，父層不動）**：
- 主按鈕文案：`currentStep < 3 ? '下一步' : '執行'`。
- 主按鈕點擊行為：`currentStep < 3` → `currentStep++`（只切分頁，不呼叫後端）；`currentStep === 3` → `emit('continue')`（維持既有啟動路徑）。
- disabled：「下一步」永遠可按；「執行」在 `props.models.length === 0` 時 disabled。等同 `:disabled="currentStep === 3 && props.models.length === 0"`，disabled 樣式的 class 同步收窄到這個條件。
- 「上一步」按鈕：**僅限 Settings 分頁內導覽**。`currentStep > 0` 時顯示（第 1 步前處理 `currentStep === 0` 直接 `v-if` 隱藏，不是 disabled），點擊 `currentStep--`。此按鈕**只做 `currentStep--`**，不觸發任何執行狀態重置——跨節點的上一步＋下游重置屬於後續批次，不在此。
- footer 版面：兩顆按鈕並排靠右（「上一步」緊貼在主按鈕左邊），`.settings-footer` 用 `justify-content: flex-end` + `gap`。

**不變**：`WorkflowWorkspace` 仍只在最後一步收到 `continue`，`continueWorkflow` 完全不受影響。模型分頁的「必填」badge 維持。

## Settings footer 固定在面板底（sticky footer）

**現況**：`.settings-wizard` 未撐滿高度，footer 接在內容之後，各步內容高度不一時主按鈕的垂直位置會跳動。

**改法（純 CSS，沿用既有高度鏈路）**：`.setting-area` / `.panel` / `.panel-body` 已是 `flex:1; min-height:0` 的 flex column。讓 `.settings-wizard` 也 `flex:1; min-height:0`；`.wizard-tabs` 與 `.settings-footer` 設 `flex-shrink:0`（分別固定在頂／底）；`.step-body` 設 `flex:1; min-height:0; overflow-y:auto` 成為唯一可捲區。footer 加 `border-top` 與 `padding-top` 讓它讀起來像固定的動作列。效果：切步驟時主按鈕位置恆定；某步內容過長時只有中間區捲動、按鈕列不動。

## Settings 模型列 icon 與文字垂直對齊

**現況**：模型列（`SettingsPanel.vue` Step 2 的 `item-row`）用 `item-head--top`（`align-items: flex-start` + 圓點 `.item-idx` `margin-top: 2px`），這是當初為「名稱換行時圓點/✕維持在首行」加的。單行名稱時圓點視覺偏低。

**改法（純 CSS）**：模型列改用基礎 `.item-head`（`align-items: center`，與前處理／特徵工程列一致），移除 `item-head--top` 這個 modifier 的使用，並刪掉只服務它的兩條 CSS 規則（`.item-head--top` 與 `.item-head--top .item-idx`）。名稱換行的少數情況圓點會垂直置中，可接受。

## Settings 步驟參數標籤改英文

**現況**：Settings 各步卡片內的參數標籤中英混用：前處理 knn_impute 顯示「鄰居數」、remove_outliers 顯示「閾值」、特徵工程 pca 顯示「維度」，其餘（`strategy`、`k`）已是英文。

**改法**：把三個中文標籤改成與 step 物件實際欄位名一致的英文 key，對齊 Preprocessor 唯讀面板（該面板直接以 `{{ key }}` 顯示 raw key）：「鄰居數」→ `n_neighbors`、「閾值」→ `threshold`、「維度」→ `n_components`。

**暫不改**：`fill_na` 的 strategy 下拉選項文字維持中文（均值／中位數／眾數）——參數名 `strategy` 已是英文，選項是給人挑的值，保留中文較好懂。

## 模型節點不可選取

**現況**：畫布層已設 `elements-selectable="false"`，但點模型節點仍會 `emit('select-node')` → `handleSelectNode()` → 開啟該節點的面板。游標沿用 vue-flow 預設（節點上顯示 `grab` 手掌），看起來可互動。

**改法**：
- 不開面板：`WorkflowWorkspace.handleSelectNode()` 開頭加守門 `if (nodeId.startsWith('model-')) return`（單一守門點；`onNodeClick` 內既有的 `userHasPanned = true` 維持，不影響平移意圖）。
- 游標區分（畫布層 `:deep`，才壓得過 vue-flow 的 `.vue-flow__node`）：`useWorkflowNodes.ts` 的 `canvasNodes` 給 `model-*` 節點掛 `class: 'node-non-interactive'`；`WorkflowCanvas.vue` 加 `:deep(.vue-flow__node) { cursor: pointer }`（可點節點顯示手指）與 `:deep(.vue-flow__node.node-non-interactive) { cursor: default }`（模型節點顯示箭頭）。
  - 註：原本設想在 `IconNode.vue` 內設 `cursor` 會被 vue-flow 的 `.vue-flow__node` 蓋掉，故改用畫布層 `:deep`；順帶把所有可點節點從 `grab` 改為 `pointer`，讓「可點／不可點」對比更清楚。

## 測試

無自動測試。`npm run dev` 手動驗：
1. Settings 四步：前三步顯示「下一步」且只切分頁、第 4 步顯示「執行」且啟動 workflow；「執行」在無模型時 disabled，「下一步」永遠可按；第 1 步無「上一步」，第 2–4 步有「上一步」且只往回切分頁；「上一步」並排在主按鈕左邊。
2. footer 固定在面板底：切步驟時按鈕位置不跳；某步內容過長時只有中間區捲動、按鈕列不動。
3. 模型列圓點與名稱垂直對齊。
4. 參數標籤顯示 `n_neighbors` / `threshold` / `n_components`。
5. 模型節點：hover 顯示箭頭（非 grab、非手指）、點了不開面板；其他可點節點 hover 顯示手指。

收尾：`npm run build`（vue-tsc 型別檢查）通過。`npm run lint` 為既有壞基線（全 repo 不符 vuetify preset），本批改動照現有檔案風格撰寫、未引入新種類問題。
