# /workflow → /results 真實資料串接設計

日期:2026-07-13
狀態:已與使用者確認方向,待寫實作計畫

## 背景

`/workflow` 執行完成後,結果(`workflowResult`,形狀同 `backend/scripts/test_paper_gen.py` 的 `MOCK_DATAMIND_OUTPUT`:`{success, class_distribution, preprocess_variants, results: [...]}`)已經存在 `useWorkflowExecution.ts` 的 `workflowResult` ref 裡,並透過既有的 `saveWorkflowStateToStorage()`/`loadWorkflowStateFromStorage()`(`frontend/src/composables/workflow/useWorkflowStorage.ts`)以 `workflowState_<projectId>` 為 key 存進 localStorage。但目前完全沒有路徑把這份真實結果導向 `/results`——`/workflow` 從不導頁,`ResultsPage.vue` 也是 100% 寫死的假資料(指標卡片、模型比較表格、AI 洞察文字全是硬編碼)。

本設計把這條路徑打通:workflow 跑完後使用者可以手動前往 `/results` 看到這次真正的結果,且之後隨時重新造訪同一個專案的 `/results` 都能看到同一份結果(不是一次性顯示)。

## 決策摘要

- **手動觸發,不自動導頁。** `WorkflowWorkspace.vue` 既有的浮動工具列新增「查看結果」按鈕,只在 `workflowResult` 有值時顯示,點擊後 `router.push('/results?project=' + projectId)`。不影響 workflow 頁面本身既有的完成動畫/互動。
- **結果可重複造訪。** `/results` 讀 `route.query.project`,透過既有的 `loadWorkflowStateFromStorage(projectId)` 取得該專案存好的 `workflowResult`,而不是用一次性的暫存 store(不同於論文生成那條走 `paperStore` 的一次性交接模式)。
- **「真實圖表」= 把現有卡片/表格換成真資料,不是新增圖表元件。** 確認過 `ResultsPage.vue` 目前沒有任何圖表函式庫(無 Chart.js/ECharts),只有指標卡片 + 模型比較表格 + 洞察文字三塊,本次範圍就是把這三塊接上真實資料。
- **表格欄位改成動態。** 後端每個模型的 `metrics` 是使用者在 workflow 裡自己選的,不固定;表格欄位 = 這次所有模型實際回傳的 metric 名稱聯集。**移除「訓練時間」欄位**(後端 `WorkflowService` 沒有記錄任何逐模型訓練時間)。
- **AI 洞察文字真的呼叫 Gemini,生成一次後快取。** 新增後端 endpoint,`/results` 第一次造訪某專案時呼叫並存進 localStorage,之後重新造訪直接讀快取,不重複呼叫。

## 1. 觸發:WorkflowWorkspace 新增「查看結果」按鈕

**檔案:** `frontend/src/components/workflow/WorkflowWorkspace.vue`

- 在既有的浮動按鈕群(`demo-btn`/`execute-workflow-btn`/`json-upload-btn` 等,`position: absolute; top: 14px`)新增一顆「查看結果」按鈕。
- 顯示條件:`workflowResult.value` 不为 `null`(來自 `useWorkflowExecution` 既有回傳值)。
- 點擊行為:`router.push(`/results?project=${projectId.value}`)`,`projectId` 沿用元件內既有的 `computed(() => route.query.project as string | undefined)`。

## 2. `/results` 讀取真實資料

**檔案:** `frontend/src/views/ResultsPage.vue`

- mount 時讀 `route.query.project`,呼叫 `loadWorkflowStateFromStorage(projectId)`,取出 `workflowResult`。
- **空狀態處理:**
  - 沒有 `project` 查詢參數,或該專案從未存過 workflow 狀態 → 顯示「尚無結果」空狀態,附一顆返回 `/workflow` 的按鈕。
  - 有存過狀態但 `workflowResult` 是 `null`(job 出錯或尚未完成)→ 同樣顯示空狀態,提示「請先在 workflow 頁面完成執行」。
- 有資料時才渲染指標卡片、比較表格、AI 洞察區塊。

## 3. 指標卡片與模型比較表格(動態欄位)

**指標卡片(4 張,對齊現有版面):**

- 排名依據:依序嘗試 `balanced_accuracy` → `accuracy` → `auc` → 該次結果中第一個出現的 metric 名稱,取第一個「所有模型都至少有這個 metric」的當排名依據。
- 「最佳模型」= 在排名 metric 上數值最高的模型。
- 其餘卡片:同一個最佳模型在其他有出現的 metric 上的數值,依常見順序(`accuracy`/`balanced_accuracy` → `f1` → `auc` → 其他)最多再取 3 個填滿卡片,不足則卡片數量隨之減少(不用假數字填充)。

**模型比較表格:**

- 欄位 = 這次所有模型結果的 `metrics[].metric` 名稱聯集(依上述常見順序排序,其餘依原順序附加在後)。
- **移除「訓練時間」欄位。**
- 「最佳分數」标粗欄位改為前述排名 metric 對應的那一欄。
- 若某模型缺少某個欄位對應的 metric → 顯示 `N/A`。

## 4. AI 生成洞察(真實 Gemini 呼叫 + 快取)

**後端:** `backend/services/rag/paper_rag.py` 的 `PaperRAGService` 新增

```python
def generate_insight(self, mining_results: dict) -> str:
    """讀 mining_results 摘要，用 Gemini 生成一段繁體中文洞察文字，供 /results 儀表板顯示。"""
```

重用既有的 `self._model`/`self._call_gemini()`/`self._format_datamind_output()`。新增路由 `POST /api/rag/insight`(`backend/routes/rag.py`,掛在既有 `rag_bp`),body `{mining_results: dict}`,回傳 `{success, insight: str}`。

**前端快取:** `frontend/src/composables/workflow/useWorkflowStorage.ts` 新增一對獨立函式(用專屬 localStorage key,不動既有的 workflow state blob):

```ts
export function saveResultInsightToStorage(projectId: string, insight: string): void
export function loadResultInsightFromStorage(projectId: string): string | null
```

**`ResultsPage.vue` 行為:** mount 時先查快取,有就直接顯示;沒有則顯示 loading、呼叫 `/api/rag/insight`,成功後存快取並顯示;失敗顯示簡短錯誤訊息 + 重試按鈕,不影響卡片/表格的顯示(兩者是獨立的非同步流程)。

## 5. 不在本次範圍

- 「報告/程式碼」分頁的實際切換內容(維持 [[2026-07-08-results-paper-transition-design]] 裡的延後決定)。
- `/workflow` 完成後自動導頁(已決定用手動按鈕)。
- 多使用者/併發情境下的資料一致性。
- 新增圖表函式庫或全新視覺化類型。
