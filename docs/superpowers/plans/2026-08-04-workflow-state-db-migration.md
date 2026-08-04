# Workflow 畫布／分析狀態遷移至資料庫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把目前存在 `localStorage` 的 workflow 畫布狀態與分析結果（nodes/edges、執行狀態、AI 洞察、結構化分析、對話紀錄）改成讀寫 PostgreSQL 的 `workflow_states` 表。

**Architecture:** 新增一組後端 workflow-state API（掛在既有 `project_bp` 上，`@login_required` 依 `current_user.id` 過濾），新增前端 API 包裝與一個 Pinia store（記憶體快取 + debounce 自動存檔），並修正六個原本直接呼叫 `useWorkflowStorage.ts` 狀態函式的呼叫端。

**Tech Stack:** Flask + SQLAlchemy（後端，沿用既有 `WorkflowState` model）、Vue 3 + Pinia + 原生 `fetch`（前端）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-04-workflow-state-db-migration-design.md`
- `WorkflowState` model 已存在且**這次不修改**：`backend/models/workflow_state.py`（欄位 `id`/`project_id`（UNIQUE，FK 到 `projects.id`）/`state`（JSONB）/`updated_at`）
- 後端新路由要 `@login_required`，透過 `Project.query.get(project_id)` 找到專案後檢查 `project.user_id == current_user.id`，不符合（含專案不存在）一律回 404，訊息「找不到專案」——不區分「不存在」與「不是你的」
- JSON 回傳格式沿用既有慣例：成功 `{"success": true, "result": ...}`，失敗 `{"success": false, "error": "..."}`（繁體中文錯誤訊息）
- GET 找不到 `WorkflowState` 資料時回 `{"success": true, "result": null}`——**不是** 404 或 error，這是新專案還沒存過狀態的正常情況
- PUT body 為 `{"state": {...}}`，`state` 內容後端不解析結構，原封不動存進 JSONB 欄位
- 前端所有打 `/api/projects/...` 的 fetch 都要帶 `credentials: 'include'`
- 前端沒有自動化測試框架，前端任務驗證用 `cd frontend && npm run type-check` + `npm run lint`；後端任務驗證用 curl 直接打 `http://localhost:5001`（`datamind-backend` 容器已把 5001 對外開放，`FLASK_DEBUG=true` 會自動 reload，不用手動重啟容器）
- 測試登入帳號：`backend/.env` 目前設定 `ADMIN_EMAIL=admin@datamind.local`、`ADMIN_PASSWORD=changeme123`
- 前端自動存檔的 debounce 時間為 600ms（`frontend/src/store/workflowStateStore.ts` 內的常數 `SAVE_DEBOUNCE_MS`）
- 本次不搬移 CSV 資料檔（維持 IndexedDB）與使用者上傳的 workflow JSON 匯入檔（維持 localStorage）；不做舊 localStorage 資料的一次性遷移，新建立的專案直接改用新來源
- `frontend/src/composables/workflow/useWorkflowStorage.ts` 裡跟「狀態」相關的 6 個函式（`saveWorkflowStateToStorage`、`loadWorkflowStateFromStorage`、`save/loadResultInsightFromStorage`、`clearResultInsightFromStorage`、`save/loadStructuredAnalysisFromStorage`、`save/loadChatHistoryFromStorage`、`clearActiveJobIdFromStorage`）最終要整批刪除，但要等所有呼叫端都遷移完（Task 9）才能刪，中途仍保留

---

### Task 1: 後端 — Workflow State GET/PUT API

**Files:**
- Modify: `backend/routes/project.py`

**Interfaces:**
- Consumes: `backend.models.workflow_state.WorkflowState`（既有，不改）、`backend.models.project.Project`（既有）、`backend.extensions.db`
- Produces：
  - `GET /api/projects/<int:project_id>/workflow-state` → `{"success": true, "result": {"state": {...}, "updatedAt": "..."} | null}`
  - `PUT /api/projects/<int:project_id>/workflow-state`，body `{"state": {...}}` → `{"success": true, "result": {"state": {...}, "updatedAt": "..."}}`

- [ ] **Step 1: 在 `backend/routes/project.py` 新增 import 與兩個路由**

找到檔案開頭：
```python
"""專案 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.project import Project, ProjectStatus

project_bp = Blueprint("project", __name__)
```

改成：
```python
"""專案 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.project import Project, ProjectStatus
from models.workflow_state import WorkflowState

project_bp = Blueprint("project", __name__)
```

在檔案最後（`update_project` function 之後）新增：
```python


@project_bp.route("/<int:project_id>/workflow-state", methods=["GET"])
@login_required
def get_workflow_state(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    workflow_state = WorkflowState.query.filter_by(project_id=project_id).first()
    if not workflow_state:
        return jsonify({"success": True, "result": None})

    return jsonify(
        {
            "success": True,
            "result": {
                "state": workflow_state.state,
                "updatedAt": workflow_state.updated_at.isoformat(),
            },
        }
    )


@project_bp.route("/<int:project_id>/workflow-state", methods=["PUT"])
@login_required
def put_workflow_state(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    data = request.get_json()
    if not data or "state" not in data:
        return jsonify({"success": False, "error": "需要 JSON body 並包含 state 欄位"}), 400

    workflow_state = WorkflowState.query.filter_by(project_id=project_id).first()
    if workflow_state:
        workflow_state.state = data["state"]
    else:
        workflow_state = WorkflowState(project_id=project_id, state=data["state"])
        db.session.add(workflow_state)

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "result": {
                "state": workflow_state.state,
                "updatedAt": workflow_state.updated_at.isoformat(),
            },
        }
    )
```

- [ ] **Step 2: 手動驗證（curl，帶 cookie jar 保持登入）**

```bash
COOKIE_JAR=/tmp/workflow-state-api-verify-cookies.txt
rm -f "$COOKIE_JAR"

curl -s -c "$COOKIE_JAR" -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@datamind.local","password":"changeme123"}'
```
Expected: 回傳 JSON 含 `"success":true`

```bash
# 先建立一個測試專案，記下回傳的 id（下面用 <ID> 代替）
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST http://localhost:5001/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"workflow-state驗證用專案","description":"","frameworkId":null,"datasetName":"","variables":0}'
```
Expected: 回傳 `result.id` 是整數

```bash
# 新專案還沒存過狀態，GET 應該回 result: null
curl -s -b "$COOKIE_JAR" http://localhost:5001/api/projects/<ID>/workflow-state
```
Expected: `{"success":true,"result":null}`

```bash
# PUT 存一份狀態
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X PUT http://localhost:5001/api/projects/<ID>/workflow-state \
  -H "Content-Type: application/json" \
  -d '{"state":{"nodes":[{"id":"file"}],"edges":[],"activeJobId":"job-123"}}'
```
Expected: 回傳 `result.state.activeJobId` 是 `"job-123"`

```bash
# 再次 GET，應該拿回剛剛存的內容
curl -s -b "$COOKIE_JAR" http://localhost:5001/api/projects/<ID>/workflow-state
```
Expected: `result.state.nodes` 是 `[{"id":"file"}]`

```bash
# PUT 再存一次（覆蓋），確認是 upsert 不是新增第二筆
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X PUT http://localhost:5001/api/projects/<ID>/workflow-state \
  -H "Content-Type: application/json" \
  -d '{"state":{"nodes":[],"edges":[],"activeJobId":null}}'
docker exec datamind-postgres psql -U datamind -d datamind -c "SELECT count(*) FROM workflow_states WHERE project_id = <ID>;"
```
Expected: count 是 `1`

```bash
# 用別人的專案 id 測 404（用一個不存在的 id）
curl -s -o /dev/null -w "%{http_code}\n" -b "$COOKIE_JAR" http://localhost:5001/api/projects/999999/workflow-state
```
Expected: `404`

- [ ] **Step 3: 清理測試資料**

```bash
docker exec datamind-postgres psql -U datamind -d datamind -c "DELETE FROM projects WHERE name = 'workflow-state驗證用專案';"
rm -f /tmp/workflow-state-api-verify-cookies.txt
```
Expected: `DELETE 1`（連帶的 `workflow_states` 列會因 FK 但沒有設 CASCADE，若報錯需先手動 `DELETE FROM workflow_states WHERE project_id = <ID>;` 再刪 project）

- [ ] **Step 4: Commit**

```bash
git add backend/routes/project.py
git commit -m "feat: add workflow state GET/PUT API"
```

---

### Task 2: 前端 — `frontend/src/api/workflowState.ts`

**Files:**
- Create: `frontend/src/api/workflowState.ts`

**Interfaces:**
- Consumes: Task 1 的 `GET/PUT /api/projects/<id>/workflow-state`；`@/types/workflow` 的 `FlowNode`/`EdgeBase`；`@/api/resultAnalysis` 的 `ChatMessage`/`StructuredAnalysis`
- Produces（給 Task 3 用）:
  - `export interface WorkflowStateData { nodes: FlowNode[]; edges: EdgeBase[]; nodeStatuses?: Record<string, 'running' | 'finished'>; pausedAtNodeId?: string | null; dataTableApplied?: boolean; selectedNodeId?: string | null; isDemoFinished?: boolean; workflowResult?: Record<string, unknown> | null; activeJobId?: string | null; resultInsight?: string | null; structuredAnalysis?: StructuredAnalysis | null; chatHistory?: ChatMessage[] }`
  - `export async function fetchWorkflowState(projectId: number): Promise<WorkflowStateData | null>`
  - `export async function saveWorkflowState(projectId: number, state: WorkflowStateData): Promise<WorkflowStateData>`

- [ ] **Step 1: 建立檔案**

```ts
import type { ChatMessage, StructuredAnalysis } from '@/api/resultAnalysis'
import type { EdgeBase, FlowNode } from '@/types/workflow'

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

async function parseWorkflowStateResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

export async function fetchWorkflowState (projectId: number): Promise<WorkflowStateData | null> {
  const response = await fetch(`/api/projects/${projectId}/workflow-state`, { credentials: 'include' })
  const result = await parseWorkflowStateResponse(response)
  const payload = result.result as { state: WorkflowStateData, updatedAt: string } | null
  return payload ? payload.state : null
}

export async function saveWorkflowState (projectId: number, state: WorkflowStateData): Promise<WorkflowStateData> {
  const response = await fetch(`/api/projects/${projectId}/workflow-state`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ state }),
  })
  const result = await parseWorkflowStateResponse(response)
  const payload = result.result as { state: WorkflowStateData, updatedAt: string }
  return payload.state
}
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/api/workflowState.ts`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/workflowState.ts
git commit -m "feat: add frontend workflow state API wrapper"
```

---

### Task 3: 前端 — `frontend/src/store/workflowStateStore.ts`

**Files:**
- Create: `frontend/src/store/workflowStateStore.ts`

**Interfaces:**
- Consumes: Task 2 的 `fetchWorkflowState`、`saveWorkflowState`、`WorkflowStateData`
- Produces（給 Task 4-8 用）:
  - `useWorkflowStateStore()` 回傳：`loadWorkflowState(projectId: number): Promise<WorkflowStateData | null>`、`getState(projectId: number): WorkflowStateData | undefined`、`updateWorkflowState(projectId: number, patch: Partial<WorkflowStateData>): void`、`flushWorkflowState(projectId: number): void`

- [ ] **Step 1: 建立檔案**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchWorkflowState, saveWorkflowState, type WorkflowStateData } from '@/api/workflowState'

const SAVE_DEBOUNCE_MS = 600

export const useWorkflowStateStore = defineStore('workflowState', () => {
  const cache = ref<Map<number, WorkflowStateData>>(new Map())
  const saveTimers = new Map<number, number>()

  async function loadWorkflowState (projectId: number): Promise<WorkflowStateData | null> {
    const cached = cache.value.get(projectId)
    if (cached) return cached

    let fetched: WorkflowStateData | null = null
    try {
      fetched = await fetchWorkflowState(projectId)
    } catch (error) {
      console.error('載入 workflow 狀態失敗', error)
      return null
    }

    if (fetched) {
      const next = new Map(cache.value)
      next.set(projectId, fetched)
      cache.value = next
    }
    return fetched
  }

  function getState (projectId: number): WorkflowStateData | undefined {
    return cache.value.get(projectId)
  }

  function persist (projectId: number): void {
    const state = cache.value.get(projectId)
    if (!state) return
    saveWorkflowState(projectId, state).catch(error => {
      console.error('儲存 workflow 狀態失敗', error)
    })
  }

  // 每個 projectId 各自維護一個 debounce 計時器：連續操作只在停止 600ms 後打一次 PUT，
  // 避免像調整欄位設定這種連續動作每次都各打一次 API
  function updateWorkflowState (projectId: number, patch: Partial<WorkflowStateData>): void {
    const current = cache.value.get(projectId) ?? { nodes: [], edges: [] }
    const merged = { ...current, ...patch }
    const next = new Map(cache.value)
    next.set(projectId, merged)
    cache.value = next

    const existingTimer = saveTimers.get(projectId)
    if (existingTimer) window.clearTimeout(existingTimer)
    const timerId = window.setTimeout(() => {
      saveTimers.delete(projectId)
      persist(projectId)
    }, SAVE_DEBOUNCE_MS)
    saveTimers.set(projectId, timerId)
  }

  // 離開頁面（pagehide/onBeforeUnmount）時呼叫：立刻送出目前快取的狀態，不等 debounce。
  // fire-and-forget——頁面隨時可能卸載，不保證這次 PUT 一定送達
  function flushWorkflowState (projectId: number): void {
    const existingTimer = saveTimers.get(projectId)
    if (existingTimer) {
      window.clearTimeout(existingTimer)
      saveTimers.delete(projectId)
    }
    persist(projectId)
  }

  return { loadWorkflowState, getState, updateWorkflowState, flushWorkflowState }
})
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/store/workflowStateStore.ts`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/workflowStateStore.ts
git commit -m "feat: add workflowStateStore with debounced autosave"
```

---

### Task 4: 前端 — `WorkflowWorkspace.vue` 遷移

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: Task 3 的 `useWorkflowStateStore()`（`loadWorkflowState`、`updateWorkflowState`、`flushWorkflowState`）

- [ ] **Step 1: 調整 import**

找到：
```ts
  import {
    clearResultInsightFromStorage,
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    loadWorkflowStateFromStorage,
    saveWorkflowDataFileToStorage,
    saveWorkflowStateToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
  import { INITIAL_EDGES, INITIAL_NODES } from '@/constants/workflowData'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
```

改成：
```ts
  import {
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    saveWorkflowDataFileToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
  import { INITIAL_EDGES, INITIAL_NODES } from '@/constants/workflowData'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { useWorkflowStateStore } from '@/store/workflowStateStore'
```

- [ ] **Step 2: 新增 store 實例**

找到：
```ts
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()
```

改成：
```ts
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()
  const workflowStateStore = useWorkflowStateStore()
```

- [ ] **Step 3: 改寫 `saveState()`**

找到：
```ts
  function saveState (): void {
    saveWorkflowStateToStorage(toRaw(nodes.value), toRaw(edges.value), projectId.value, {
      nodeStatuses: Object.fromEntries(nodeStatuses.value),
      pausedAtNodeId: pausedAtNodeId.value,
      dataTableApplied: dataTableApplied.value,
      selectedNodeId: selectedNodeId.value,
      isDemoFinished: isDemoFinished.value,
      workflowResult: workflowResult.value,
      activeJobId: activeJobId.value,
    })
  }
```

改成：
```ts
  function saveState (): void {
    const id = projectId.value ? Number(projectId.value) : NaN
    if (!Number.isFinite(id)) return
    workflowStateStore.updateWorkflowState(id, {
      nodes: toRaw(nodes.value),
      edges: toRaw(edges.value),
      nodeStatuses: Object.fromEntries(nodeStatuses.value),
      pausedAtNodeId: pausedAtNodeId.value,
      dataTableApplied: dataTableApplied.value,
      selectedNodeId: selectedNodeId.value,
      isDemoFinished: isDemoFinished.value,
      workflowResult: workflowResult.value,
      activeJobId: activeJobId.value,
    })
  }
```

- [ ] **Step 4: 改寫 `handleApplyColumnConfig`/`handleContinueSettings` 的 `clearResultInsightFromStorage` 呼叫**

找到：
```ts
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    if (projectId.value) clearResultInsightFromStorage(projectId.value)
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleContinueSettings (): void {
    if (projectId.value) clearResultInsightFromStorage(projectId.value)
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

改成：
```ts
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    if (projectId.value) workflowStateStore.updateWorkflowState(Number(projectId.value), { resultInsight: null })
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleContinueSettings (): void {
    if (projectId.value) workflowStateStore.updateWorkflowState(Number(projectId.value), { resultInsight: null })
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

- [ ] **Step 5: 改寫 `onMounted` 內還原狀態的邏輯**

找到：
```ts
      } else {
        const restoredState = loadWorkflowStateFromStorage(projectId.value)
        if (restoredState && restoredState.nodes?.length > 0) {
```

改成：
```ts
      } else {
        const numericProjectId = projectId.value ? Number(projectId.value) : null
        const restoredState = numericProjectId !== null
          ? await workflowStateStore.loadWorkflowState(numericProjectId)
          : null
        if (restoredState && restoredState.nodes?.length > 0) {
```

（這個 `if` block 內剩下的內容，包含 `restoredState.nodeStatuses`、`restoredState.pausedAtNodeId` 等欄位還原邏輯，以及後面的 `else` 分支 `loadWorkflowJsonFileFromStorage` 呼叫，都維持原樣不動——只有取得 `restoredState` 的來源換掉。）

- [ ] **Step 6: 改寫 `pagehide`/`onBeforeUnmount`**

找到：
```ts
  // 瀏覽器刷新／關閉頁籤時 Vue 的 onBeforeUnmount 不會被觸發，
  // 必須額外監聽 pagehide 才能確保最新狀態在頁面卸載前被寫入 localStorage
  function handlePageHide (): void {
    saveState()
  }

  window.addEventListener('pagehide', handlePageHide)

  // 離開頁面時不能再呼叫 resetDemo() 清空 nodeStatuses：onBeforeUnmount 執行的當下，
  // 元件的 watch 還沒被 Vue 停掉，清空動作可能被該 watch 偵測到並把「清空後」的狀態存進
  // localStorage，導致下次打開專案時整個 workflow 看起來被清掉
  onBeforeUnmount(() => {
    window.removeEventListener('pagehide', handlePageHide)
    saveState()
  })
```

改成：
```ts
  // 瀏覽器刷新／關閉頁籤時 Vue 的 onBeforeUnmount 不會被觸發，
  // 必須額外監聽 pagehide 才能確保最新狀態在頁面卸載前送出存檔請求
  // （debounce 期間的變動也一併 flush，不用等 600ms；fetch 不保證在頁面關閉前送達，是已知的可接受風險）
  function handlePageHide (): void {
    if (!projectId.value) return
    saveState()
    workflowStateStore.flushWorkflowState(Number(projectId.value))
  }

  window.addEventListener('pagehide', handlePageHide)

  // 離開頁面時不能再呼叫 resetDemo() 清空 nodeStatuses：onBeforeUnmount 執行的當下，
  // 元件的 watch 還沒被 Vue 停掉，清空動作可能被該 watch 偵測到並把「清空後」的狀態存進
  // 資料庫，導致下次打開專案時整個 workflow 看起來被清掉
  onBeforeUnmount(() => {
    window.removeEventListener('pagehide', handlePageHide)
    if (!projectId.value) return
    saveState()
    workflowStateStore.flushWorkflowState(Number(projectId.value))
  })
```

- [ ] **Step 7: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/components/workflow/WorkflowWorkspace.vue`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: migrate WorkflowWorkspace state persistence to database"
```

---

### Task 5: 前端 — `ResultView.vue` 遷移

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue`

**Interfaces:**
- Consumes: Task 3 的 `useWorkflowStateStore()`

- [ ] **Step 1: 調整 import**

找到：
```ts
  import {
    loadChatHistoryFromStorage,
    loadStructuredAnalysisFromStorage,
    loadWorkflowStateFromStorage,
    saveChatHistoryToStorage,
    saveStructuredAnalysisToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
```

改成：
```ts
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { useWorkflowStateStore } from '@/store/workflowStateStore'
```

- [ ] **Step 2: 新增 store 實例與數字型 projectId**

找到：
```ts
  const route = useRoute()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // 注意：projectId 維持字串型別——這個變數後面還會拿去當 localStorage 的 key
  // （loadWorkflowStateFromStorage 等函式都吃字串），只有跟 store.projects 比對時才轉數字
  const projectId = computed(() => route.params.id as string)
```

改成：
```ts
  const route = useRoute()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()
  const workflowStateStore = useWorkflowStateStore()

  const projectId = computed(() => route.params.id as string)
  const numericProjectId = computed(() => Number(projectId.value))
```

- [ ] **Step 3: 改寫 `summary` computed**

找到：
```ts
  const summary = computed<ModelMetricSummary[]>(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    return summarizeWorkflowResult(state?.workflowResult ?? null)
  })
```

改成：
```ts
  const summary = computed<ModelMetricSummary[]>(() => {
    const state = workflowStateStore.getState(numericProjectId.value)
    return summarizeWorkflowResult(state?.workflowResult ?? null)
  })
```

- [ ] **Step 4: 改寫 `loadAnalysis`**

找到：
```ts
  async function loadAnalysis (): Promise<void> {
    const cached = loadStructuredAnalysisFromStorage(projectId.value)
    if (cached) {
      analysis.value = cached
      return
    }

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return

    analysisLoading.value = true
    analysisError.value = null
    try {
      analysis.value = await fetchStructuredAnalysis(miningResult)
      const isAllEmpty = Object.values(analysis.value).every(v => v === '')
      if (isAllEmpty) {
        analysis.value = null
        throw new Error('AI 分析生成失敗，請稍後重試')
      }
      saveStructuredAnalysisToStorage(projectId.value, analysis.value)
    } catch (error) {
      analysisError.value = error instanceof Error ? error.message : String(error)
    } finally {
      analysisLoading.value = false
    }
  }
```

改成：
```ts
  async function loadAnalysis (): Promise<void> {
    const cached = workflowStateStore.getState(numericProjectId.value)?.structuredAnalysis
    if (cached) {
      analysis.value = cached
      return
    }

    const miningResult = workflowStateStore.getState(numericProjectId.value)?.workflowResult
    if (!miningResult) return

    analysisLoading.value = true
    analysisError.value = null
    try {
      analysis.value = await fetchStructuredAnalysis(miningResult)
      const isAllEmpty = Object.values(analysis.value).every(v => v === '')
      if (isAllEmpty) {
        analysis.value = null
        throw new Error('AI 分析生成失敗，請稍後重試')
      }
      workflowStateStore.updateWorkflowState(numericProjectId.value, { structuredAnalysis: analysis.value })
    } catch (error) {
      analysisError.value = error instanceof Error ? error.message : String(error)
    } finally {
      analysisLoading.value = false
    }
  }
```

- [ ] **Step 5: 改寫 `sendMessage`**

找到：
```ts
    try {
      const historyForApi: ChatMessage[] = chatMessages.value
        .slice(0, -1)
        .filter(m => !m.failed)
        .map(m => ({ role: m.role, text: m.text }))
      const { reply, papers } = await sendChatMessage(miningResult, historyForApi, text)
      chatMessages.value.push({ role: 'model', text: reply, papers: papers.length > 0 ? papers : undefined })
      saveChatHistoryToStorage(projectId.value, chatMessages.value)
    } catch (error) {
```

改成：
```ts
    try {
      const historyForApi: ChatMessage[] = chatMessages.value
        .slice(0, -1)
        .filter(m => !m.failed)
        .map(m => ({ role: m.role, text: m.text }))
      const { reply, papers } = await sendChatMessage(miningResult, historyForApi, text)
      chatMessages.value.push({ role: 'model', text: reply, papers: papers.length > 0 ? papers : undefined })
      workflowStateStore.updateWorkflowState(numericProjectId.value, { chatHistory: chatMessages.value })
    } catch (error) {
```

同一個函式稍上方找到：
```ts
  async function sendMessage (): Promise<void> {
    const text = chatInput.value.trim()
    if (!text || chatLoading.value) return

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return
```

改成：
```ts
  async function sendMessage (): Promise<void> {
    const text = chatInput.value.trim()
    if (!text || chatLoading.value) return

    const miningResult = workflowStateStore.getState(numericProjectId.value)?.workflowResult
    if (!miningResult) return
```

- [ ] **Step 6: 改寫 `onMounted`**

找到：
```ts
  onMounted(() => {
    if (summary.value.length === 0) return
    loadAnalysis()
    chatMessages.value = loadChatHistoryFromStorage(projectId.value) as DisplayChatMessage[]
  })
```

改成：
```ts
  onMounted(async () => {
    await workflowStateStore.loadWorkflowState(numericProjectId.value)
    if (summary.value.length === 0) return
    loadAnalysis()
    chatMessages.value = (workflowStateStore.getState(numericProjectId.value)?.chatHistory ?? []) as DisplayChatMessage[]
  })
```

- [ ] **Step 7: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/views/hub/ResultView.vue`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "feat: migrate ResultView state persistence to database"
```

---

### Task 6: 前端 — `ResultsPage.vue` 遷移

**Files:**
- Modify: `frontend/src/views/ResultsPage.vue`

**Interfaces:**
- Consumes: Task 3 的 `useWorkflowStateStore()`

- [ ] **Step 1: 調整 import**

找到：
```ts
  import { fetchResultInsight } from '@/api/insight'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import {
    loadResultInsightFromStorage,
    loadWorkflowStateFromStorage,
    saveResultInsightToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
```

改成：
```ts
  import { fetchResultInsight } from '@/api/insight'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import { useWorkflowStateStore } from '@/store/workflowStateStore'
```

- [ ] **Step 2: 新增 store 實例與數字型 projectId**

找到：
```ts
  const route = useRoute()
  const router = useRouter()

  const projectId = computed(() => route.query.project as string | undefined)
```

改成：
```ts
  const route = useRoute()
  const router = useRouter()
  const workflowStateStore = useWorkflowStateStore()

  const projectId = computed(() => route.query.project as string | undefined)
  const numericProjectId = computed(() => (projectId.value ? Number(projectId.value) : null))
```

- [ ] **Step 3: 改寫 `loadInsight`**

找到：
```ts
  async function loadInsight (): Promise<void> {
    if (!projectId.value || !workflowResult.value) return
    const cached = loadResultInsightFromStorage(projectId.value)
    if (cached) {
      insightText.value = cached
      return
    }
    insightLoading.value = true
    insightError.value = null
    try {
      const insight = await fetchResultInsight(workflowResult.value)
      insightText.value = insight
      saveResultInsightToStorage(projectId.value, insight)
    } catch (error) {
      insightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      insightLoading.value = false
    }
  }
```

改成：
```ts
  async function loadInsight (): Promise<void> {
    const id = numericProjectId.value
    if (id === null || !workflowResult.value) return
    const cached = workflowStateStore.getState(id)?.resultInsight
    if (cached) {
      insightText.value = cached
      return
    }
    insightLoading.value = true
    insightError.value = null
    try {
      const insight = await fetchResultInsight(workflowResult.value)
      insightText.value = insight
      workflowStateStore.updateWorkflowState(id, { resultInsight: insight })
    } catch (error) {
      insightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      insightLoading.value = false
    }
  }
```

- [ ] **Step 4: 改寫載入狀態的 `onMounted`**

找到：
```ts
  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    workflowResult.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (workflowResult.value) {
      loadInsight()
    }
  })
```

改成：
```ts
  onMounted(async () => {
    const id = numericProjectId.value
    const state = id !== null ? await workflowStateStore.loadWorkflowState(id) : null
    workflowResult.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (workflowResult.value) {
      loadInsight()
    }
  })
```

（檔案裡另有一個 `onMounted(() => { document.title = 'DataMind' })`，維持不動；Vue 允許同一個元件多次呼叫 `onMounted`。）

- [ ] **Step 5: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/views/ResultsPage.vue`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/ResultsPage.vue
git commit -m "feat: migrate ResultsPage state persistence to database"
```

---

### Task 7: 前端 — `PaperSourcesView.vue` + `InsertChartDialog.vue` 遷移（唯讀）

**Files:**
- Modify: `frontend/src/views/PaperSourcesView.vue`
- Modify: `frontend/src/components/paper/InsertChartDialog.vue`

**Interfaces:**
- Consumes: Task 3 的 `useWorkflowStateStore()`

- [ ] **Step 1: `PaperSourcesView.vue` 調整 import**

找到：
```ts
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { usePaperStore } from '@/store/paperStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'
```

改成：
```ts
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import { usePaperStore } from '@/store/paperStore'
  import { useWorkflowStateStore } from '@/store/workflowStateStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'
```

- [ ] **Step 2: `PaperSourcesView.vue` 新增 store 實例並改寫 `onMounted`**

找到：
```ts
  const route = useRoute()
  const router = useRouter()
  const paperStore = usePaperStore()

  const projectId = computed(() => route.query.project as string | undefined)
```

改成：
```ts
  const route = useRoute()
  const router = useRouter()
  const paperStore = usePaperStore()
  const workflowStateStore = useWorkflowStateStore()

  const projectId = computed(() => route.query.project as string | undefined)
```

找到：
```ts
  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (miningResults.value) {
      loadCandidates()
    }
  })
```

改成：
```ts
  onMounted(async () => {
    const id = projectId.value ? Number(projectId.value) : null
    const state = id !== null ? await workflowStateStore.loadWorkflowState(id) : null
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (miningResults.value) {
      loadCandidates()
    }
  })
```

- [ ] **Step 3: `InsertChartDialog.vue` 調整 import 與 watch**

找到：
```ts
  import { computed, ref, watch } from 'vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```

改成：
```ts
  import { computed, ref, watch } from 'vue'
  import { useWorkflowStateStore } from '@/store/workflowStateStore'
  import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
```

找到：
```ts
  const chartType = ref<'bar' | 'radar'>('bar')
  const summaries = ref<ModelMetricSummary[]>([])
  const selectedModels = ref<string[]>([])
  const selectedMetrics = ref<string[]>([])
  const previewRef = ref<HTMLElement | null>(null)

  watch(() => props.modelValue, open => {
    if (!open) return
    const state = loadWorkflowStateFromStorage(props.projectId)
    summaries.value = summarizeWorkflowResult(state?.workflowResult ?? null)
    selectedModels.value = summaries.value.map(s => s.model_name)
    selectedMetrics.value = [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))]
  })
```

改成：
```ts
  const chartType = ref<'bar' | 'radar'>('bar')
  const summaries = ref<ModelMetricSummary[]>([])
  const selectedModels = ref<string[]>([])
  const selectedMetrics = ref<string[]>([])
  const previewRef = ref<HTMLElement | null>(null)
  const workflowStateStore = useWorkflowStateStore()

  watch(() => props.modelValue, async open => {
    if (!open) return
    const id = props.projectId ? Number(props.projectId) : null
    const state = id !== null ? await workflowStateStore.loadWorkflowState(id) : null
    summaries.value = summarizeWorkflowResult(state?.workflowResult ?? null)
    selectedModels.value = summaries.value.map(s => s.model_name)
    selectedMetrics.value = [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))]
  })
```

- [ ] **Step 4: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向這兩個檔案

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperSourcesView.vue frontend/src/components/paper/InsertChartDialog.vue
git commit -m "feat: migrate PaperSourcesView and InsertChartDialog to read workflow state from database"
```

---

### Task 8: 前端 — `projectStore.ts` 遷移

**Files:**
- Modify: `frontend/src/store/projectStore.ts`

**Interfaces:**
- Consumes: Task 3 的 `useWorkflowStateStore()`

- [ ] **Step 1: 調整 import**

找到：
```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createProject, type CreateProjectPayload, listProjects, updateProject } from '@/api/project'
import { fetchWorkflowJob, WorkflowJobNotFoundError } from '@/api/workflow'
import { clearActiveJobIdFromStorage, loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
```

改成：
```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createProject, type CreateProjectPayload, listProjects, updateProject } from '@/api/project'
import { fetchWorkflowJob, WorkflowJobNotFoundError } from '@/api/workflow'
import { useWorkflowStateStore } from './workflowStateStore'
```

- [ ] **Step 2: 新增 store 實例並改寫 `loadProjects()`**

找到：
```ts
export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeContext = ref<ActiveProjectContext | null>(null)

  async function loadProjects (): Promise<void> {
    try {
      projects.value = await listProjects()
    } catch (error) {
      console.error('載入專案列表失敗', error)
      return
    }

    // App 重新載入時，把上次還在跑的 job 接續輪詢起來
    for (const p of projects.value) {
      const state = loadWorkflowStateFromStorage(String(p.id))
      if (state?.activeJobId) {
        pollProjectJob(p.id, state.activeJobId)
      }
    }
  }
```

改成：
```ts
export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeContext = ref<ActiveProjectContext | null>(null)
  const workflowStateStore = useWorkflowStateStore()

  async function loadProjects (): Promise<void> {
    try {
      projects.value = await listProjects()
    } catch (error) {
      console.error('載入專案列表失敗', error)
      return
    }

    // App 重新載入時，把上次還在跑的 job 接續輪詢起來；只有「進行中」的專案才可能有未完成的
    // job，其餘狀態（draft/completed）不需要多打一次 workflow-state 的 GET
    for (const p of projects.value.filter(project => project.status === 'running')) {
      const state = await workflowStateStore.loadWorkflowState(p.id)
      if (state?.activeJobId) {
        pollProjectJob(p.id, state.activeJobId)
      }
    }
  }
```

- [ ] **Step 3: 改寫 `pollProjectJob` 內的 `clearActiveJobIdFromStorage` 呼叫**

找到：
```ts
        } catch (error) {
          if (error instanceof WorkflowJobNotFoundError) {
            // job 在後端已經永久消失（重啟／超過 TTL），不是暫時性錯誤，停止輪詢並清掉過期紀錄
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            clearActiveJobIdFromStorage(String(projectId))
            return
          }
          // 輪詢暫時失敗（網路抖動等），下一輪再試
        }
```

改成：
```ts
        } catch (error) {
          if (error instanceof WorkflowJobNotFoundError) {
            // job 在後端已經永久消失（重啟／超過 TTL），不是暫時性錯誤，停止輪詢並清掉過期紀錄
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            workflowStateStore.updateWorkflowState(projectId, { activeJobId: null })
            return
          }
          // 輪詢暫時失敗（網路抖動等），下一輪再試
        }
```

- [ ] **Step 4: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/store/projectStore.ts`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/projectStore.ts
git commit -m "feat: migrate projectStore active job resume to workflowStateStore"
```

---

### Task 9: 前端 — `useWorkflowStorage.ts` 清理

**Files:**
- Modify: `frontend/src/composables/workflow/useWorkflowStorage.ts`

**Interfaces:**
- Consumes: 無（純刪除，Task 4-8 已經沒有任何呼叫端使用被刪除的函式）

- [ ] **Step 1: 確認沒有殘留呼叫端**

Run: `cd frontend && grep -rn "saveWorkflowStateToStorage\|loadWorkflowStateFromStorage\|saveResultInsightToStorage\|loadResultInsightFromStorage\|clearResultInsightFromStorage\|saveStructuredAnalysisToStorage\|loadStructuredAnalysisFromStorage\|saveChatHistoryToStorage\|loadChatHistoryFromStorage\|clearActiveJobIdFromStorage" src`
Expected: 只有 `src/composables/workflow/useWorkflowStorage.ts` 自己這一個檔案出現（Task 4-8 都已經改掉呼叫端）

- [ ] **Step 2: 整檔換成**

```ts
const WORKFLOW_DATA_FILE_KEY = 'workflowDataFile'
const WORKFLOW_JSON_FILE_KEY = 'workflowJsonFile'

const DB_NAME = 'datamindWorkflowFiles'
const DB_STORE = 'files'

function k (base: string, projectId?: string): string {
  return projectId ? `${base}_${projectId}` : base
}

// 一次性清掉舊版（base64 存 localStorage）留下的資料檔案，
// 這些殘留可能就是當初把 localStorage 配額塞滿、導致存檔靜默失敗的原因
function purgeLegacyDataFileEntries (): void {
  const staleKeys: string[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (key && (key === WORKFLOW_DATA_FILE_KEY || key.startsWith(`${WORKFLOW_DATA_FILE_KEY}_`))) {
      staleKeys.push(key)
    }
  }
  for (const key of staleKeys) {
    localStorage.removeItem(key)
  }
}

purgeLegacyDataFileEntries()

// CSV 資料檔案改用 IndexedDB 儲存：localStorage 容量通常只有 5~10MB，
// 累積多個專案的資料檔很容易超過上限導致 setItem 靜默失敗，造成刷新後資料消失
function openFileDb (): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(DB_STORE)) {
        request.result.createObjectStore(DB_STORE)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.addEventListener('error', () => reject(request.error))
  })
}

export async function saveWorkflowDataFileToStorage (file: File | null, projectId?: string): Promise<void> {
  const key = k(WORKFLOW_DATA_FILE_KEY, projectId)
  try {
    const db = await openFileDb()
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(DB_STORE, 'readwrite')
      if (file) {
        tx.objectStore(DB_STORE).put({ name: file.name, type: file.type || 'text/csv', blob: file }, key)
      } else {
        tx.objectStore(DB_STORE).delete(key)
      }
      tx.oncomplete = () => resolve()
      tx.addEventListener('error', () => reject(tx.error))
    })
    db.close()
  } catch (error) {
    console.error('[WF-SAVE] 無法將資料檔案存入 IndexedDB:', error)
  }
}

export async function loadWorkflowDataFileFromStorage (projectId?: string): Promise<File | null> {
  const key = k(WORKFLOW_DATA_FILE_KEY, projectId)
  try {
    const db = await openFileDb()
    const record = await new Promise<{ name: string, type: string, blob: Blob } | undefined>((resolve, reject) => {
      const tx = db.transaction(DB_STORE, 'readonly')
      const req = tx.objectStore(DB_STORE).get(key)
      req.onsuccess = () => resolve(req.result)
      req.addEventListener('error', () => reject(req.error))
    })
    db.close()
    if (!record) {
      return null
    }
    return new File([record.blob], record.name, { type: record.type })
  } catch (error) {
    console.error('[WF-LOAD] 無法從 IndexedDB 還原資料檔案:', error)
    return null
  }
}

export async function saveWorkflowJsonFileToStorage (file: File | null, projectId?: string): Promise<void> {
  const key = k(WORKFLOW_JSON_FILE_KEY, projectId)
  if (!file) {
    localStorage.removeItem(key)
    return
  }
  try {
    const text = await file.text()
    const payload = { name: file.name, type: file.type || 'application/json', text }
    localStorage.setItem(key, JSON.stringify(payload))
  } catch (error) {
    console.warn('Unable to persist workflow JSON to localStorage', error)
  }
}

export async function loadWorkflowJsonFileFromStorage (projectId?: string): Promise<File | null> {
  const key = k(WORKFLOW_JSON_FILE_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as { name: string, type: string, text: string }
    return new File([parsed.text], parsed.name, { type: parsed.type })
  } catch (error) {
    console.warn('Unable to restore workflow JSON from localStorage', error)
    localStorage.removeItem(key)
    return null
  }
}
```

- [ ] **Step 3: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤（全專案，因為這是最後一個刪除舊函式的步驟，若有殘留呼叫端會在這裡曝光）

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/composables/workflow/useWorkflowStorage.ts
git commit -m "refactor: remove localStorage-based workflow state functions"
```

---

### Task 10: 整批驗證

**Files:** 無新增/修改檔案，純驗證

**Interfaces:**
- Consumes: Task 1-9 全部產出

- [ ] **Step 1: 確認容器正在跑且 type-check 全專案乾淨**

Run: `docker ps --format "{{.Names}}"`
Expected: 包含 `datamind-frontend`、`datamind-backend`、`datamind-postgres`

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 2: 瀏覽器驗證 — 執行 workflow 後重新整理狀態還原**

登入 → 建立專案 → 在 `/workflow?project=<id>` 走完一次 workflow → 重新整理頁面
Expected: 畫布節點、執行結果正確還原（不是回到初始空白畫布）

- [ ] **Step 3: 瀏覽器驗證 — AI 分析與對話持久化**

到 `/hub/projects/<id>/result` → 等 AI 結構化分析生成 → 在對話框問一個問題 → 重新整理頁面
Expected: 結構化分析與對話紀錄都還在，不用重新生成/重新輸入

- [ ] **Step 4: 瀏覽器驗證 — 獨立頁面各自讀取正常**

- `/results?project=<id>`（`ResultsPage.vue`）：AI 洞察正確顯示且重新整理後仍在
- `/paper/sources?project=<id>`：能讀到 workflow 結果並查到 arXiv 候選文獻

- [ ] **Step 5: Network 分頁驗證 — debounce 生效**

在 `/workflow?project=<id>` 開瀏覽器 Network 分頁，篩選 `workflow-state`，連續快速調整多個欄位設定（例如勾選多個前處理選項）
Expected: 只在停止操作後約 600ms 觸發一次 `PUT /api/projects/<id>/workflow-state`，不是每次勾選都各打一次

- [ ] **Step 6: 資料隔離驗證**

登出，用另一個帳號註冊並登入，開啟自己名下一個有 workflow 結果的專案的結果頁
Expected: 看不到第一個帳號的分析/對話紀錄（新帳號的專案本來就是空的，屬於正常情況，不會噴錯或顯示別人的資料）

無需 commit（這個任務不產生程式碼變更）。
