# 分頁 AI 解讀 Design Spec

## 背景

`ConfusionMatrixPanel.vue`（畫布上「Classification Evaluation」節點的面板）現在有五個分頁：混淆矩陣／ROC 曲線／PR 曲線／校準曲線／各類別指標。使用者希望每個分頁旁邊都能有一段 AI 針對該分頁內容生成的文字解讀，幫助非統計背景的使用者理解圖表/表格代表的意義。

專案裡已經有一個類似的既有功能——`ResultsPage.vue` 的「AI 生成洞察」卡片，打 `POST /api/rag/insight`，把整份 `workflowResult` 丟給後端、後端摘要成文字後叫 Gemini 生成一段 2-3 句的洞察，用 `localStorage`（key 是 `resultInsight_<projectId>`）快取，只在使用者重新套用 dataTable 欄位設定或按下「繼續」時才清快取。

這次的分頁解讀不能照搬「自動生成」的模式：一份結果有 N 個模型 × N 個 fold × 5 個分頁，全部自動生成會產生大量非必要的 Gemini 呼叫。

## 範圍

- 後端：`backend/services/rag/paper_rag.py` 新增 `generate_tab_insight()`，`backend/routes/rag.py` 新增 `POST /api/rag/tab-insight` 路由
- 前端：`ConfusionMatrixPanel.vue` 每個分頁內容區改成左右兩欄（左：既有圖表/表格，右：AI 解讀按鈕/文字），`frontend/src/api/insight.ts` 新增對應 API 函式，`useWorkflowStorage.ts` 新增分頁解讀的快取函式，`projectId` 需要從 `WorkflowWorkspace.vue` 一路往下傳到 `WorkflowOptionsPanel.vue`（目前沒有傳）再到 `ConfusionMatrixPanel.vue`
- **不**自動生成，一律使用者按「AI 解讀」按鈕才觸發
- **不**把整份原始曲線座標陣列丟給 Gemini——比照既有 `_format_datamind_output()` 的節制做法，只送精簡摘要文字

## 後端設計

`PaperRagService` 新增 `generate_tab_insight(mining_results, tab, model_name, split_name) -> str`：

1. 從 `mining_results["results"]` 裡找出 `model_name`/`split_name` 都吻合、且沒有 `error` 欄位的那一筆
2. 根據 `tab`（`'matrix'`/`'roc'`/`'pr'`/`'calibration'`/`'perClass'`）呼叫對應的私有格式化函式，只挑該分頁需要的欄位轉成文字：
   - `matrix`：`confusion_matrix` 的 labels/matrix 轉成「實際 X：預測 A=n、預測 B=n」這種文字列表
   - `roc`/`pr`：`roc_pr_curve` 只取 `pos_label` + 對應的 `auc`/`auprc` 數值（從同一筆結果的 `metrics` 陣列讀）+ 均勻取樣 5 個座標點（不送整條曲線的完整陣列）
   - `calibration`：`calibration_curve` 的 `prob_true`/`prob_pred`（bin 數量本來就 ≤10，直接送）
   - `perClass`：`per_class_metrics` 的 labels/precision/recall/f1/support 逐類別列出
3. 組 prompt：固定開頭（你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果）+ 該分頁的資料文字 + 每個分頁各自的解讀重點提示（例如混淆矩陣要點出容易誤判的類別、ROC 要說明判別力、PR 要提到類別不平衡下的意義、校準曲線要說明機率可不可信、各類別指標要點出表現最差的類別）+ 要求繁體中文 2-4 句話、只輸出解讀本身
4. 呼叫既有的 `self._call_gemini(prompt, usage_total)`，回傳 `.strip()` 後的文字——沿用既有的「失敗不拋例外、回傳『（生成失敗：...）』字串」慣例

路由 `POST /api/rag/tab-insight`：接 `{mining_results, tab, model_name, split_name}`，四個都必填，找不到對應結果或分頁沒有可用資料時回傳一段說明文字（不是錯誤），呼叫失敗才回 500，比照既有 `/insight` 路由的錯誤處理寫法。

## 前端設計

**API**：`frontend/src/api/insight.ts` 新增 `fetchTabInsight(miningResults, tab, modelName, splitName): Promise<string>`，寫法比照既有的 `fetchResultInsight()`。

**快取**：`useWorkflowStorage.ts` 新增 `saveTabInsightToStorage`/`loadTabInsightFromStorage`，key 用 `tabInsight_<tab>_<modelName>_<splitName>_<projectId>` 這種組合（比照既有 `k()` helper 的 `<base>_<projectId>` 格式，只是 base 本身多帶三個維度）。另外新增 `clearAllTabInsightsFromStorage(projectId)`——因為組合鍵無法像單一 key 那樣直接刪，要掃描 `localStorage` 所有 key、篩出符合 `tabInsight_` 開頭且屬於這個 `projectId` 的，全部移除。這個函式要跟既有的 `clearResultInsightFromStorage(projectId)` 一樣，加進 `WorkflowWorkspace.vue` 的 `handleApplyColumnConfig()`/`handleContinueSettings()` 這兩個既有的清快取時機點。

**`projectId` 往下傳**：`WorkflowWorkspace.vue` 呼叫 `<WorkflowOptionsPanel>` 時新增 `:project-id="projectId"`；`WorkflowOptionsPanel.vue` 新增 `projectId?: string` prop，呼叫 `<ConfusionMatrixPanel>` 時新增 `:project-id="props.projectId"`；`ConfusionMatrixPanel.vue` 新增對應的 `projectId?: string` prop。

**`ConfusionMatrixPanel.vue` 版面**：五個既有的分頁內容區塊（`v-if="activeTab === '...' && ..."`／`v-else-if="... && groupedResults.length > 0"`）目前是彼此獨立的 sibling `<div>`。這次把它們整體包進一個新的 flex row 容器（`.cm-tab-row`），讓現有的圖表/表格區塊維持在左邊、旁邊新增一個共用的 AI 解讀面板（`.cm-insight-panel`）在右邊——因為 AI 解讀面板的內容（按鈕/loading/文字）不因分頁不同而有結構差異，只有依據 `activeTab`/`selectedModel`/`selectedFold` 這三個既有狀態變化，所以不需要在五個分頁各寫一份，用同一個區塊、同一個 `v-if="groupedResults.length > 0"` 條件即可涵蓋全部五個分頁。

AI 解讀面板狀態機（沿用既有 `insightLoading`/`insightError`/`insightText` 那套三態模式，但這次是依 `activeTab`+`selectedModel`+`selectedFold` 組合鍵快取，不是整頁只有一份）：
- 尚未生成過這個組合：顯示「AI 解讀」按鈕
- 生成中：loading 文字
- 失敗：錯誤文字 + 重試按鈕
- 已生成（含從 localStorage 讀到快取）：顯示文字 + 一個「重新生成」的小按鈕（比照 `ResultsPage.vue` 既有的重試按鈕寫法）

切換分頁或切換模型/fold 下拉時，如果那個組合先前已經生成過（不管是這次 session 生成的還是 localStorage 裡的快取），要立刻顯示，不用重新打 API；沒有的話顯示「AI 解讀」按鈕等使用者按。

## 錯誤處理 / 相容性

- 找不到對應的 `model_name`/`split_name` 結果，或該分頁沒有資料（例如多分類跑 ROC 分頁）：後端回傳一段說明文字（例如「此分頁沒有可供解讀的資料。」），不是錯誤，前端當作正常的解讀文字顯示即可
- Gemini 呼叫本身失敗：沿用 `_call_gemini()` 既有的「回傳『（生成失敗：...）』字串」慣例，不拋例外；前端仍走既有的 `try/catch`（呼叫本身若因為網路問題等原因整個失敗才會進 catch，顯示錯誤文字 + 重試）
- 舊的 workflow 結果（這次改動之前存的）沒有 `confusion_matrix`/`roc_pr_curve`/`calibration_curve`/`per_class_metrics` 欄位：後端格式化函式回傳 `None`，`generate_tab_insight()` 這種情況下回傳「此分頁沒有可供解讀的資料。」

## 測試

- 後端無 pytest，前端無 vitest。用 `docker exec datamind-backend .venv/bin/python -m py_compile` 做語法檢查，前端用 `npm run type-check`
- 人工瀏覽器驗證：執行一次 workflow，點「Classification Evaluation」節點，每個分頁都按一次「AI 解讀」，確認：
  - 五個分頁都能正常生成文字，內容跟該分頁的資料相關（不是空泛的通用文字）
  - 切換模型/fold 下拉後同一分頁要重新按才生成（不同組合各自獨立），切回先前按過的組合要立刻顯示、不用重新打 API
  - 重新整理頁面後，先前生成過的組合仍然能從快取顯示
  - 重新套用 dataTable 欄位設定或按「繼續」後，先前所有分頁解讀的快取都要被清空
