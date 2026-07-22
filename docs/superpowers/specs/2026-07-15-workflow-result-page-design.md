# Workflow 結果頁設計（接上 /hub/projects/:id/result）

## 背景

Workflow job 跑完後，實際結果（`workflowResult`）只會顯示在 `WorkflowWorkspace.vue` 的 canvas 抽屜裡，離開頁面就看不到彙整過的結果。現有的 `/results`（`ResultsPage.vue`）是一份完全用假資料寫死的頁面，且不掛在 `HubLayout` 底下（有自己另一套 sidebar/品牌列），也沒有被 app 裡任何地方連結到——是一個死頁面。

本次目標：讓已完成的專案有一個可以隨時回來查看真實結果的頁面，並清掉重複／死掉的舊頁面。

## 範圍

**做：**
- 新增 `/hub/projects/:id/result` 頁面，顯示指標卡 + 模型比較表（真實資料）
- 從 `ProjectDetailView.vue` 加入「查看完整結果」入口
- 抽出共用的結果彙總邏輯，供 canvas 抽屜與新結果頁共用
- 移除死掉的 `/results` 路由與 `ResultsPage.vue`

**不做（out of scope）：**
- 訓練時間欄位（後端目前無此資料，需要另外設計計時機制）
- AI 生成洞察文字（需要另外呼叫 LLM，是獨立功能）
- `Project.accuracy` / `Project.keyFinding` 欄位回填（目前完全沒有任何地方寫入這兩個欄位；本次結果頁不依賴它們，改成直接從 `workflowResult` 現算，這個既有缺口不在本次範圍內修）
- Workflow job 完成後自動導頁（本次維持手動點擊「查看完整結果」）

## 資料來源與資料流

後端 job（`backend/services/workflow/job_manager.py`）是純記憶體狀態，完成後 1 小時（`_JOB_TTL_SECONDS`）就會被清掉，重啟後端也會全部遺失，不能當作結果頁的資料來源。

真正可靠、且已經在用的持久化位置是前端 `localStorage`：`WorkflowWorkspace.vue` 在 `workflowResult` 改變時，會透過 `saveWorkflowStateToStorage(nodes, edges, projectId, { ...，workflowResult })`（見 `useWorkflowStorage.ts`）把完整結果寫入 `workflowState_<projectId>` key，且頁面重新整理／重進時也會從同一個 key 還原（`loadWorkflowStateFromStorage`）。

結果頁的資料流：

```
ResultView.vue (mounted)
  → route.params.id 取得 projectId
  → projectStore.projects 找出 project（找不到 → 404 態）
  → loadWorkflowStateFromStorage(projectId) 讀 workflowState_<projectId>
  → 取出 .workflowResult
      → 不存在 → 空狀態（引導「在 Workflow 中開啟」重新執行）
      → 存在 → summarizeWorkflowResult(workflowResult) → 渲染指標卡 + 比較表
```

不呼叫任何後端 API，純讀 localStorage，跟 canvas 是否還掛載無關。

## 共用彙總邏輯抽取

`useWorkflowExecution.ts` 目前有一個內聯的 `workflowSummary` computed（依 `model_name` 分組，把每個 metric 的多次數值取平均），這段邏輯搬到新檔案：

`frontend/src/utils/workflow/summarizeWorkflowResult.ts`

```ts
export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult(
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[]
```

邏輯原封不動搬過去（不改行為），`useWorkflowExecution.ts` 的 `workflowSummary` computed 改成呼叫這個函式；`ResultView.vue` 也呼叫同一個函式。

## 頁面設計：ResultView.vue

路徑：`frontend/src/views/hub/ResultView.vue`
路由：在 `router/index.ts` 的 `/hub` children 裡新增

```ts
{
  path: 'projects/:id/result',
  name: 'hub-project-result',
  component: () => import('@/views/hub/ResultView.vue'),
},
```

版面延續 `ProjectDetailView.vue` 的既有風格（`back-link` 返回專案、`page-title`），內容區塊參考現有 `ResultsPage.vue` 的 `metric-grid` / `comparison-card` CSS 樣式做裁切，但改吃真實資料：

1. **返回連結**：回到 `/hub/projects/:id`
2. **指標卡（動態）**：
   - 從 `summarizeWorkflowResult()` 結果中蒐集所有出現過的 metric 名稱
   - 「最佳模型」卡：以第一個出現的 metric 排序，取數值最高的 model_name
   - 其餘每個 metric 各一張卡，顯示最佳模型在該 metric 上的數值
   - 最多顯示 4 張卡（與現有 grid 版面一致），超過的 metric 不上卡片、但仍會出現在下方比較表
3. **模型比較表**：
   - 欄位 = 這次結果裡實際出現過的所有 metric（動態，不寫死 accuracy/precision/recall/f1）
   - 列 = 每個 model，數值取 `summarizeWorkflowResult()` 算好的 `valueFormatted`
   - 若某模型某 metric 有 error（`errors` 欄位），該格顯示錯誤提示而非數值
   - 不含訓練時間欄
4. **空狀態**：`workflowResult` 不存在時，顯示「尚未有可用結果」＋按鈕連回 `/workflow?project=:id`（沿用 `ProjectDetailView.openInWorkflow` 的同一種導頁方式）
5. **找不到專案**：`project` 為 `undefined` 時顯示「找不到該專案」（沿用 `ProjectDetailView.vue` 現有寫法）

## ProjectDetailView.vue 變更

在 `status === 'completed'` 區塊，`result-divider` 下方新增一個連結按鈕：

```html
<RouterLink class="view-result-btn" :to="`/hub/projects/${project.id}/result`">
  查看完整結果
  <v-icon icon="mdi-arrow-right" size="14" />
</RouterLink>
```

樣式比照現有 `open-workflow-btn`（次要按鈕風格，避免喧賓奪主）。原本的「在 Workflow 中開啟」按鈕保留在原位置不動。

## 移除項目

- `frontend/src/router/index.ts`：刪除 `/results` 這個 route 物件
- `frontend/src/views/ResultsPage.vue`：整個檔案刪除

（已確認整個 frontend 沒有其他地方引用 `ResultsPage` 或 `"/results"`，可以安全移除。）

## 錯誤處理

- `projectId` 對應不到任何 project → 沿用 `ProjectDetailView.vue` 現有的「找不到該專案」樣式
- `localStorage` 讀取失敗（例如格式壞掉）→ `loadWorkflowStateFromStorage` 本身已有 try/catch，回傳 `null`，視同「沒有結果」走空狀態
- `workflowResult.results` 不是陣列或為空 → `summarizeWorkflowResult` 回傳空陣列，頁面顯示空狀態（不當成例外處理）

## 測試

- 手動驗證：
  1. 走完一次 workflow（跑完至少 2 個模型）→ 從 `ProjectDetailView` 點「查看完整結果」→ 確認指標卡與比較表數值跟 canvas 抽屜裡看到的一致
  2. 重新整理結果頁 → 資料仍在（證明是讀 localStorage 而非依賴 canvas 記憶體狀態）
  3. 對一個 `status: 'draft'`／從未執行過的專案，直接改網址列進入 `/hub/projects/:id/result` → 確認顯示空狀態而非報錯
  4. 確認 `/results` 網址已經 404（路由移除後的預期行為）
