# 專案／框架庫遷移至資料庫 設計文件

## 背景與範圍

這是「把現有功能資料流程移進資料庫」大工程的第二個子專案，接續在[[前端登入串接](2026-08-01-frontend-auth-integration-design.md)]之後。資料庫 schema（`projects`、`frameworks` 表）在更早的 [使用者登入與資料庫設計](2026-08-01-user-auth-database-design.md) 子專案中就已經建好，但至今沒有任何路由或前端程式碼真的去讀寫它們——`frontend/src/store/projectStore.ts`、`frontend/src/store/frameworkStore.ts` 目前仍是純 Pinia + `localStorage`（key 分別是 `datamind_projects`、`datamind_frameworks`），並各自寫死 3 筆示範資料做初始值。

這次的範圍：新增後端 CRUD API（依登入使用者做資料隔離）、前端兩個 store 改成呼叫 API 而不是讀寫 localStorage。**不**包含資料集檔案（`datasets` 表）、工作流程狀態持久化（`workflow_states` 表）——這些留給後續子專案。**不**搬移現有 localStorage 裡的示範資料——新註冊帳號一律從空的開始（已與使用者確認）。

## 架構總覽

```
frontend/src/api/project.ts ──┐
frontend/src/api/framework.ts ┘── credentials:'include' ──▶ backend routes ──▶ projects / frameworks 表
        │                                                    (@login_required,
        ▼                                                     依 current_user.id 過濾)
frontend/src/store/projectStore.ts
frontend/src/store/frameworkStore.ts
        │
        ▼
Dashboard / ProjectsView / FrameworkLibraryView / CreateProjectView / ProjectDetailView / WorkflowWorkspace ...
```

## 後端 API

### `backend/routes/project.py`（新增 blueprint `project_bp`，url_prefix `/api/projects`）

全部 `@login_required`。所有回傳的 JSON 欄位用 camelCase（對應前端介面），資料庫欄位是 snake_case，路由層負責轉換——沿用 `routes/auth.py` 既有的 `{"success": bool, "result": ...}` / `{"success": false, "error": str}` 回傳格式。

| Method | Path | Body | 行為 |
|---|---|---|---|
| GET | `/api/projects` | 無 | 回傳 `current_user` 的所有專案，`ORDER BY created_at DESC` |
| POST | `/api/projects` | `{name, description, frameworkId, datasetName, variables}` | 建立新專案，`user_id = current_user.id`，`status` 預設 `draft`、`progress` 預設 `0`；回傳建立好的完整專案（含資料庫 `id`） |
| PATCH | `/api/projects/<id>` | 任意子集：`{status?, progress?, datasetName?, accuracy?, keyFinding?}` | 先查 `Project.query.get(id)`，若不存在或 `project.user_id != current_user.id` 回 404（不透露資源存在與否）；否則只更新 body 裡出現的欄位並回傳更新後的完整專案 |

`status` 欄位驗證：body 若帶 `status`，值必須是 `draft`/`running`/`completed` 三者之一（對應 `ProjectStatus` enum），否則回 400。

### `backend/routes/framework.py`（新增 blueprint `framework_bp`，url_prefix `/api/frameworks`）

全部 `@login_required`。

| Method | Path | Body | 行為 |
|---|---|---|---|
| GET | `/api/frameworks` | 無 | 回傳 `current_user` 的所有框架，`ORDER BY created_at DESC` |
| POST | `/api/frameworks` | `{title, subtitle, tag, variables, paperTitle, description, independentVars, dependentVars, hypotheses, workflowJson}` | 建立新框架，`user_id = current_user.id`；回傳建立好的完整框架（含資料庫 `id`） |

沒有 `PATCH`/`DELETE`——目前前端完全沒有編輯或刪除框架的介面（`frameworkStore.ts` 只有 `addFramework` 一個 mutator），不做超出現況需求的端點（YAGNI）。同理，`projects` 也沒有 `DELETE`——現況沒有刪除專案的 UI。

### 註冊 blueprint

在 `backend/apps/__init__.py` 依現有 pattern（`auth_bp`、`report_bp` 那幾行）加上：
```python
from routes.project import project_bp
from routes.framework import framework_bp
...
app.register_blueprint(project_bp, url_prefix="/api/projects")
app.register_blueprint(framework_bp, url_prefix="/api/frameworks")
```

## 前端 API 包裝

### `frontend/src/api/project.ts`（新增）

```
listProjects(): Promise<ProjectDTO[]>
createProject(payload: {name, description, frameworkId, datasetName, variables}): Promise<ProjectDTO>
updateProject(id: number, patch: Partial<{status, progress, datasetName, accuracy, keyFinding}>): Promise<ProjectDTO>
```
所有請求帶 `credentials: 'include'`（比照 `api/auth.ts`，因為這些路由現在都要求登入）。失敗時 `throw new Error(...)`，沿用 `report.ts`/`auth.ts` 既有的錯誤處理慣例。

### `frontend/src/api/framework.ts`（新增）

```
listFrameworks(): Promise<FrameworkDTO[]>
createFramework(payload: {title, subtitle, tag, variables, paperTitle, description, independentVars, dependentVars, hypotheses, workflowJson}): Promise<FrameworkDTO>
```

## 前端 Store 改寫

### `projectStore.ts`

- 移除 `loadFromStorage`/`INITIAL_PROJECTS`/`STORAGE_KEY`/`watch(...localStorage.setItem...)` 全部拿掉
- `Project` 介面：
  - `id` 型別從 `string` 改成 `number`（對齊資料庫主鍵，`id: number`）
  - 移除 `frameworkName` 欄位（資料庫沒有這個冗餘欄位）
  - 其餘欄位不變
- 初始狀態：`const projects = ref<Project[]>([])`
- 新增 `async function loadProjects(): Promise<void>`，呼叫 `listProjects()` 填入 `projects.value`
- `addProject` 改成 `async`：呼叫 `createProject(...)`，把回傳的（含真實資料庫 `id`）專案塞進 `projects.value` 開頭，回傳它
- `updateProjectStatus(projectId: number, status)`／`updateProjectProgress(projectId: number, progress)` 改成 `async`：先樂觀更新本地 `target`，再呼叫 `updateProject(projectId, {...})`；PATCH 失敗只記錄 console error，不 rollback UI（這兩個函式呼叫頻率低，且都是關鍵狀態轉換如「開始執行」「完成」，樂觀更新後失敗機率低，不做複雜的 rollback 機制）
- `pollProjectJob` 內部 `setInterval` 的每個 tick：
  - **不呼叫** `updateProjectProgress`（不寫回資料庫），只直接改 `target.progress = ...`（純本地）
  - job 狀態變成 `done`/`error` 的那一刻，才呼叫 `updateProjectStatus(projectId, 'completed')`（`done` 時）——這一次呼叫本身就會把當下的 `progress` 一併帶進 PATCH body，一次把 progress 跟 status 都寫回去
- `activeContext`／`setActiveContext`／`clearActiveContext` 不動（純記憶體狀態，不曾寫進 localStorage，這次也不用碰）

### `frameworkStore.ts`

- 同樣移除 localStorage 相關程式碼
- 初始狀態：`const frameworks = ref<Framework[]>([])`
- 新增 `async function loadFrameworks(): Promise<void>`
- `addFramework` 改成 `async`，呼叫 `createFramework(...)`

## 呼叫端調整

- 資料載入時機**不能**放在 `HubLayout.vue` 的 `onMounted`：`/workflow`、`/results`、`/paper` 這幾個路由是頂層路由，不在 `/hub` 底下（見 `router/index.ts`），使用者若直接重新整理 `/workflow` 頁面，`HubLayout` 根本不會掛載，store 會是空的，導致工作流程頁面找不到專案/框架資料。
- 改成在 `frontend/src/main.ts` 的開機流程觸發：跟 Task 6（登入串接）加入的 `authStore.checkSession()` 並列，各自獨立呼叫、不互相 `await`（載入專案/框架跟確認登入狀態是兩件獨立的事，不用互相等待）：
  ```ts
  authStore.checkSession().finally(() => { app.mount('#app') })
  projectStore.loadProjects()
  frameworkStore.loadFrameworks()
  ```
  未登入時這兩個請求會收到 401，`listProjects`/`listFrameworks` 依「錯誤處理」段落的規則保持空陣列即可（使用者接著會被路由守衛導去 `/login`，空陣列不會被看到）；登入後才需要靠使用者實際導航或重新整理來再次觸發载入——這次不做「登入成功後自動重新載入」這種進階同步機制（YAGNI），因為 `login()`/`register()` 成功後一律 `router.push('/hub/dashboard')`，而 `main.ts` 開機時已經呼叫過一次，登入頁本身也不需要顯示專案/框架資料。
- 所有讀取 `project.frameworkName` 的地方（`DashboardView.vue`、`ProjectsView.vue`、`ProjectDetailView.vue`、`ResultView.vue` 等）改成：`frameworkStore.frameworks.find(fw => fw.id === project.frameworkId)?.title ?? ''`
- `router/index.ts` 裡 `projects/:id`、`projects/:id/result` 兩個路由讀取 `route.params.id` 的地方（在對應的 View 元件內，不是路由設定本身）要用 `Number(route.params.id)` 轉型後再拿去跟 `project.id`（現在是 `number`）比對

## 錯誤處理

- `loadProjects`/`loadFrameworks` 失敗（後端未啟動、網路問題）：`projects`/`frameworks` 維持空陣列，console 記錄錯誤，不彈錯誤視窗（沿用整體專案目前沒有全域通知系統的現況，不在這次順便新建一個）
- `createProject`/`createFramework` 失敗：呼叫端（`CreateProjectView.vue`/`ExtractFrameworkView.vue`）維持在目前畫面，用 `console.error` 記錄，不新增 toast（YAGNI；有需要可作為後續子專案的獨立需求）

## 資料遷移

不搬移現有 localStorage 資料。新註冊帳號的 `projects`/`frameworks` 一律從空的開始。

## 驗證方式（手動）

1. 登入後開啟 Hub Dashboard／專案列表／框架庫，應顯示空清單（新帳號）
2. 框架庫「擷取框架」建立一個新框架 → 重新整理頁面 → 框架仍在（確認真的寫進資料庫，不是只存在記憶體）
3. 「新增專案」流程選擇剛建立的框架、建立專案 → 專案列表出現該專案，且框架名稱正確顯示（驗證 `frameworkId` 查表邏輯）
4. 執行一次工作流程 → 專案狀態變成 `running`（重新整理頁面應該還是 `running`，代表狀態轉換有立即持久化）→ 等待完成 → 專案狀態變成 `completed` 且 `progress` 是 100（重新整理頁面確認最終值有持久化，但過程中的中間進度不要求持久化）
5. 用瀏覽器開發者工具 Network 分頁確認：工作流程執行過程中，`PATCH /api/projects/:id` 只在開始跟結束各觸發一次，過程中的 2 秒輪詢不應該有 PATCH 請求
6. 登出後用另一個帳號登入，確認看不到第一個帳號建立的專案/框架（資料隔離）

無自動化測試框架（沿用專案既有慣例），以上步驟全部手動驗證。
