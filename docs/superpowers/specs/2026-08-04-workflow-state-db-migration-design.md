# Workflow 畫布／分析狀態遷移至資料庫 Design

**Goal：** 把目前存在 `localStorage` 的 workflow 畫布狀態與分析結果（nodes/edges、執行狀態、AI 洞察、結構化分析、對話紀錄），改成讀寫 PostgreSQL 的 `workflow_states` 表，讓資料不再受限於單一瀏覽器/裝置。

**Non-goals（本次不做）：**
- CSV 資料檔（目前存 IndexedDB）與使用者上傳的 workflow JSON 匯入檔（目前存 localStorage）——維持原樣，不搬移。這兩者是「檔案內容」而非「狀態」，未來若要做檔案永久化屬於另一個獨立子專案（對應既有的 `datasets` 表）。
- 舊 localStorage 資料的一次性遷移——直接改用新來源，舊資料不搬。使用者若有進行中的 workflow，畫布狀態會顯示為空白（需重新執行 workflow）。
- 語言偏好（`plugins/i18n.ts` 用的 `locale` key）——單純 UI 偏好，不涉及業務資料，不搬。

## 架構總覽

```
useWorkflowStorage.ts  ──保留──▶  CSV 檔案(IndexedDB) / JSON 匯入檔(localStorage)  [不動]
                        ──移除──▶  workflowState / resultInsight / structuredAnalysis / chatHistory 六個函式

新增 frontend/src/store/workflowStateStore.ts (Pinia)
  ├─ cache: Ref<Map<number, WorkflowStateData>>  （記憶體快取，同一 session 每個專案只 fetch 一次）
  ├─ loadWorkflowState(projectId): Promise<WorkflowStateData | null>
  ├─ getState(projectId): WorkflowStateData | null       （同步讀快取，給 computed 用）
  ├─ updateWorkflowState(projectId, patch): void          （merge 進快取 + debounce 600ms 後存檔）
  └─ flushWorkflowState(projectId): void                  （立刻存檔，fire-and-forget，unmount/pagehide 用）
        │
        ▼
新增 frontend/src/api/workflowState.ts
  ├─ fetchWorkflowState(projectId): Promise<WorkflowStateData | null>
  └─ saveWorkflowState(projectId, state): Promise<WorkflowStateData>
        │
        ▼
新增後端路由 backend/routes/workflow_state.py（掛在既有的 project_bp 之後，url_prefix 沿用 /api/projects）
  ├─ GET /api/projects/<int:project_id>/workflow-state  → {"success": true, "result": {...} | null}
  └─ PUT /api/projects/<int:project_id>/workflow-state  → upsert，body {"state": {...}}
        │
        ▼
既有的 backend/models/workflow_state.py（已存在，不改）→ workflow_states 表（已建立，migration 已跑過）
```

## 後端 API 設計

**Files:**
- Create: `backend/routes/workflow_state.py`
- Modify: `backend/apps/__init__.py`（註冊 blueprint）

**規則（沿用 `backend/routes/project.py`、`backend/routes/framework.py` 既有慣例）：**
- `@login_required`，透過 `Project.query.get(project_id)` 找到專案後檢查 `project.user_id == current_user.id`，不符合（含專案不存在）一律回 404，訊息「找不到專案」——不區分「不存在」與「不是你的」，避免洩漏其他使用者專案是否存在
- GET 找不到 `WorkflowState` 資料時回 `{"success": true, "result": null}`（**不是** 404／error——新專案還沒存過狀態是正常情況，前端據此判斷要不要顯示初始畫布）
- PUT body 為 `{"state": {...}}`，`state` 是前端傳來的完整 JSON blob，後端**不解析內容結構**，原封不動存進 JSONB 欄位（`WorkflowState.state`）
- PUT 用 `WorkflowState.query.filter_by(project_id=project_id).first()` 查找：有就更新 `state` 欄位（`updated_at` 由 model 的 `onupdate` 自動更新），沒有就新建一筆並 `db.session.add`；`project_id` 有 UNIQUE constraint 保證不會重複建立
- 回傳格式：`{"success": true, "result": {"state": {...}, "updatedAt": "2026-08-04T12:00:00"}}`

**Blueprint 註冊：** 不需要新的 url_prefix，直接掛在 `project_bp` 上以子路由形式提供（`/api/projects/<int:project_id>/workflow-state`），或建立獨立 blueprint 用完整路徑定義路由——兩者皆可，實作時選較符合現有程式風格的一種（現有 `project_bp` 用 `url_prefix="/api/projects"` 掛載，新路由可以在同一個 blueprint 內新增 `@project_bp.route("/<int:project_id>/workflow-state", ...)`，不需要另建 blueprint）。

## 前端資料結構

**統一後的 `WorkflowStateData`**（合併原本 6 個獨立 localStorage key 的內容）：

```ts
export interface WorkflowStateData {
  nodes: FlowNode[]
  edges: EdgeBase[]
  nodeStatuses?: Record<string, 'running' | 'finished'>
  pausedAtNodeId?: string | null
  dataTableApplied?: boolean
  selectedNodeId?: string | null
  isDemoFinished?: boolean
  workflowResult?: Record<string, unknown> | null
  activeJobId?: string | null
  resultInsight?: string | null
  structuredAnalysis?: StructuredAnalysis | null
  chatHistory?: ChatMessage[]
}
```

## `frontend/src/api/workflowState.ts`

```ts
export interface WorkflowStateData { /* 同上 */ }

export async function fetchWorkflowState(projectId: number): Promise<WorkflowStateData | null>
export async function saveWorkflowState(projectId: number, state: WorkflowStateData): Promise<WorkflowStateData>
```
兩者都 `credentials: 'include'`，沿用 `api/project.ts`/`api/framework.ts` 既有的 response parse 慣例（`!response.ok || !result.success` 就 throw）。

## `frontend/src/store/workflowStateStore.ts`

- `cache: Ref<Map<number, WorkflowStateData>>`——響應式，`getState()` 讀它所以 Vue computed 能正確追蹤變化
- `loadWorkflowState(projectId)`：cache 已有該 projectId 就直接回傳（同一 session 每個專案只打一次 GET）；沒有就 fetch，寫入 cache 後回傳；fetch 失敗則 `console.error` 並回傳 `null`（視同全新專案）
- `getState(projectId)`：同步讀 cache，給 computed 用；未 load 過回傳 `undefined`
- `updateWorkflowState(projectId, patch)`：`Object.assign` merge 進 cache 中對應物件；每個 projectId 各自維護一個 `setTimeout` 計時器（用 `Map<number, number>` 存 timer id），600ms debounce 後呼叫 `saveWorkflowState` PUT；PUT 失敗只 `console.error`，不中斷使用者操作，下次 `updateWorkflowState` 觸發時用最新狀態重試
- `flushWorkflowState(projectId)`：清掉該 projectId 待執行的計時器，立刻呼叫 `saveWorkflowState`（不 await，fire-and-forget——因為呼叫時機是 `pagehide`/`onBeforeUnmount`，頁面可能隨時卸載）

## 呼叫端遷移

| 檔案 | 改動 |
|---|---|
| `WorkflowWorkspace.vue` | `saveState()` 內部呼叫改成 `workflowStateStore.updateWorkflowState(Number(projectId.value), {...})`；`onMounted` 開頭 `await workflowStateStore.loadWorkflowState(Number(projectId.value))` 取代同步讀 localStorage；`clearResultInsightFromStorage` 呼叫點改成 `updateWorkflowState(id, { resultInsight: null })`；`pagehide`/`onBeforeUnmount` 改呼叫 `flushWorkflowState` |
| `ResultView.vue` | `onMounted` 先 `await loadWorkflowState(Number(projectId.value))`；`summary` computed、`loadAnalysis`、`sendMessage` 內原本同步讀 localStorage 的地方改呼叫 `workflowStateStore.getState(Number(projectId.value))`；`saveStructuredAnalysisToStorage`/`saveChatHistoryToStorage` 改成 `updateWorkflowState(id, { structuredAnalysis })`/`updateWorkflowState(id, { chatHistory })` |
| `ResultsPage.vue` | 同上模式（`resultInsight` 相關的 load/save） |
| `PaperSourcesView.vue` | 唯讀用途，`onMounted` 補一次 `await loadWorkflowState` 再呼叫 `getState` |
| `InsertChartDialog.vue` | 唯讀用途，dialog 開啟（`onMounted` 或 watch `visible`）時 `await loadWorkflowState` 一次再讀 `getState` |
| `projectStore.ts` | `loadProjects()` 裡「接續輪詢 job」的邏輯，改成只對 `status === 'running'` 的專案呼叫 `workflowStateStore.loadWorkflowState(p.id)` 再檢查回傳值的 `activeJobId`（避免開機時對所有專案，包含 draft/completed，都打一次不必要的 GET） |

`useWorkflowStorage.ts` 瘦身：只留 `saveWorkflowDataFileToStorage`/`loadWorkflowDataFileFromStorage`（IndexedDB，CSV）、`saveWorkflowJsonFileToStorage`/`loadWorkflowJsonFileFromStorage`（localStorage，JSON 匯入檔）、`purgeLegacyDataFileEntries`。其餘 6 個「狀態」相關函式（`saveWorkflowStateToStorage`、`loadWorkflowStateFromStorage`、`save/loadResultInsightFromStorage`、`clearResultInsightFromStorage`、`save/loadStructuredAnalysisFromStorage`、`save/loadChatHistoryFromStorage`、`clearActiveJobIdFromStorage`）整批刪除。

`clearActiveJobIdFromStorage` 的用途（job 在後端永久查不到時清除過期的 `activeJobId`）改成 `workflowStateStore.updateWorkflowState(projectId, { activeJobId: null })`。

## 錯誤處理

- GET 失敗（網路錯誤/伺服器錯誤）：`loadWorkflowState` catch 後回傳 `null`，畫面等同「全新專案」從空白狀態開始，並 `console.error` 記錄（與現有 `loadProjects`/`loadFrameworks` 的錯誤處理風格一致）
- PUT（debounce 自動存檔）失敗：`console.error` 記錄，不跳 UI 錯誤 toast（避免暫時性網路抖動一直打斷使用者），下次任何欄位變動觸發新的 `updateWorkflowState` 時會帶著最新狀態重試
- `flushWorkflowState` 失敗（離開頁面時）：不處理，best-effort；已知風險是 debounce 600ms 內的最後一段編輯有極小機率遺失（使用者已在前面的問答中接受此風險，以換取比舊方案更短的 debounce）

## 測試與驗證

**後端（curl，比照 `project.py`/`framework.py` 既有驗證方式）：**
- 登入取得 cookie → GET 一個新專案的 workflow-state，預期 `result: null`
- PUT 一份 `{"state": {"nodes": [...], "edges": [...]}}`，預期 `success: true`
- 再次 GET，預期拿回剛剛存的內容
- 用另一個使用者的專案 id 呼叫，預期 404

**前端：**
- `cd frontend && npm run type-check` + `npm run lint`，確認全專案無錯誤
- 瀏覽器手動驗證：
  - 建立專案 → 走完 workflow → 重新整理頁面 → 畫布狀態、執行結果正確還原
  - `/hub/projects/:id/result` 產生 AI 洞察/結構化分析/對話後，重新整理仍在
  - `/results`（`ResultsPage.vue`）與 `/paper/sources` 兩個獨立頁面各自讀取同一專案狀態正常
  - Network 分頁確認：連續操作（例如快速調整多個欄位設定）只在停止操作後 600ms 觸發一次 PUT，不是每次操作都打
  - 登出後用另一帳號登入，確認看不到第一個帳號的 workflow 狀態（資料隔離）
