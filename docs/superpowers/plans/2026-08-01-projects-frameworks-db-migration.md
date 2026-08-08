# 專案／框架庫遷移至資料庫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「專案」「框架庫」兩個功能從純前端 Pinia + localStorage 改成真正讀寫 PostgreSQL 資料庫，並依登入使用者做資料隔離。

**Architecture:** 新增兩組後端 CRUD 路由（`@login_required`，依 `current_user.id` 過濾），新增對應的前端 API 包裝，重寫兩個 Pinia store 改成呼叫 API，並修正所有讀取舊欄位（`frameworkName`）或依賴舊 id 型別（`string`）的呼叫端。

**Tech Stack:** Flask + SQLAlchemy（後端，沿用既有 `Project`/`Framework` model）、Vue 3 + Pinia + 原生 `fetch`（前端）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-01-projects-frameworks-db-migration-design.md`
- 資料庫 model 已存在且**這次不修改**：`backend/models/project.py`（`Project`，欄位 `id/user_id/name/description/framework_id/dataset_name/status(enum draft|running|completed)/progress/accuracy/key_finding/variables/created_at/updated_at`）、`backend/models/framework.py`（`Framework`，欄位 `id/user_id/title/subtitle/tag/variables/paper_title/description/independent_vars(array)/dependent_vars(array)/hypotheses(array)/workflow_json(jsonb)/created_at`）
- 後端所有新路由都要 `@login_required`（`from flask_login import current_user, login_required`），且用 `current_user.id` 過濾——絕不能回傳別的使用者的資料
- JSON 回傳格式沿用 `backend/routes/auth.py` 既有慣例：成功 `{"success": true, "result": ...}`，失敗 `{"success": false, "error": "..."}`（繁體中文錯誤訊息）
- 回傳欄位一律 camelCase（`frameworkId`、`datasetName`、`keyFinding`、`paperTitle`、`independentVars`、`dependentVars`、`workflowJson`），資料庫是 snake_case，路由層負責轉換
- `date` 欄位（前端 `Project`/`Framework` 介面都有）不是資料庫欄位，由後端在序列化時用 `created_at.strftime("%Y-%m-%d")` 產生
- 前端所有打 `/api/projects`、`/api/frameworks` 的 fetch 都要帶 `credentials: 'include'`（沿用 `frontend/src/api/auth.ts` 慣例，因為這些路由現在都要求登入）
- `Project.id` 型別從 `string` 改成 `number`（對齊資料庫主鍵）；`Framework.id` 本來就是 `number`，不用改
- 移除 `Project.frameworkName` 欄位（資料庫沒有這個冗餘欄位），改用 `frameworkId` 查 `frameworkStore.frameworks` 取得名稱
- 專案執行工作流程時的進度輪詢（`pollProjectJob` 內的 `setInterval`）：每次 tick **只改本地 `ref`，不呼叫 API**；只有 job 完成/失敗那一刻才透過 `updateProjectStatus`/`updateProjectProgress` 寫回資料庫
- 前端沒有自動化測試框架，前端任務驗證用 `cd frontend && npm run type-check` + `npm run lint`；後端任務驗證用 curl 直接打 `http://localhost:5001`（backend 容器已把 5001 對外開放，不需要透過 Vite proxy），`datamind-backend` 容器跑在 `FLASK_DEBUG=true`，host 上編辑 `backend/` 底下的檔案會自動觸發 reload，不用手動重啟容器
- 測試登入帳號：`backend/.env` 的 `ADMIN_EMAIL=admin@datamind.local`、`ADMIN_PASSWORD=changeme-locally`（`scripts/seed_admin.py` 已建立過這個帳號）
- 這次不搬移既有 localStorage 資料、不做資料集檔案上傳（`datasets` 表）、不做工作流程狀態持久化（`workflow_states` 表）——都是後續獨立子專案的範圍

---

### Task 1: 後端 — 專案 CRUD API

**Files:**
- Create: `backend/routes/project.py`
- Modify: `backend/apps/__init__.py`

**Interfaces:**
- Consumes: `backend.models.project.Project`、`ProjectStatus`（既有，不改）、`backend.extensions.db`
- Produces: Flask blueprint `project_bp`，掛在 `/api/projects`：
  - `GET /api/projects` → `{"success": true, "result": Project[]}`
  - `POST /api/projects`，body `{name, description, frameworkId, datasetName, variables}` → `{"success": true, "result": Project}`
  - `PATCH /api/projects/<int:project_id>`，body 任意子集 `{status?, progress?, datasetName?, accuracy?, keyFinding?}` → `{"success": true, "result": Project}`
  - 序列化後的 `Project` JSON 形狀：`{id, name, description, frameworkId, datasetName, status, progress, accuracy, keyFinding, variables, date}`

- [ ] **Step 1: 建立 `backend/routes/project.py`**

```python
"""專案 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.project import Project, ProjectStatus

project_bp = Blueprint("project", __name__)


def _serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "frameworkId": project.framework_id,
        "datasetName": project.dataset_name,
        "status": project.status.value,
        "progress": project.progress,
        "accuracy": project.accuracy,
        "keyFinding": project.key_finding,
        "variables": project.variables,
        "date": project.created_at.strftime("%Y-%m-%d"),
    }


@project_bp.route("", methods=["GET"])
@login_required
def list_projects():
    projects = (
        Project.query.filter_by(user_id=current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "result": [_serialize_project(p) for p in projects]})


@project_bp.route("", methods=["POST"])
@login_required
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"success": False, "error": "name 為必填欄位"}), 400

    project = Project(
        user_id=current_user.id,
        name=name,
        description=data.get("description"),
        framework_id=data.get("frameworkId"),
        dataset_name=data.get("datasetName"),
        variables=data.get("variables") or 0,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_project(project)})


@project_bp.route("/<int:project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    if "status" in data:
        try:
            project.status = ProjectStatus(data["status"])
        except ValueError:
            return (
                jsonify({"success": False, "error": "status 必須是 draft/running/completed 其中之一"}),
                400,
            )
    if "progress" in data:
        project.progress = data["progress"]
    if "datasetName" in data:
        project.dataset_name = data["datasetName"]
    if "accuracy" in data:
        project.accuracy = data["accuracy"]
    if "keyFinding" in data:
        project.key_finding = data["keyFinding"]

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_project(project)})
```

- [ ] **Step 2: 在 `backend/apps/__init__.py` 註冊 blueprint**

找到這一段（大約在檔案中段的 import 區）：
```python
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

改成（新增 `project_bp` 的 import 跟註冊，緊接在 `auth_bp` 後面）：
```python
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.project import project_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(project_bp, url_prefix="/api/projects")
    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

- [ ] **Step 3: 手動驗證（curl，帶 cookie jar 保持登入）**

```bash
COOKIE_JAR=/tmp/project-api-verify-cookies.txt
rm -f "$COOKIE_JAR"

# 登入
curl -s -c "$COOKIE_JAR" -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@datamind.local","password":"changeme-locally"}'
```
Expected: 回傳 JSON 含 `"success":true`

```bash
# 建立專案
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST http://localhost:5001/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"驗證用專案","description":"","frameworkId":null,"datasetName":"","variables":0}'
```
Expected: 回傳 JSON 含 `"success":true`，`result.status` 是 `"draft"`，`result.progress` 是 `0`，`result.id` 是一個整數——記下這個 `id`（下面用 `<ID>`代替）

```bash
# 列出專案，應該看得到剛建立的那筆
curl -s -b "$COOKIE_JAR" http://localhost:5001/api/projects
```
Expected: `result` 陣列包含剛剛的專案

```bash
# 局部更新
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X PATCH http://localhost:5001/api/projects/<ID> \
  -H "Content-Type: application/json" \
  -d '{"status":"running","progress":42}'
```
Expected: 回傳 `result.status` 是 `"running"`、`result.progress` 是 `42`

```bash
# 用另一個不存在的 id 測試 404
curl -s -o /dev/null -w "%{http_code}\n" -b "$COOKIE_JAR" -X PATCH http://localhost:5001/api/projects/999999 \
  -H "Content-Type: application/json" -d '{"status":"running"}'
```
Expected: `404`

- [ ] **Step 4: 清理測試資料**

```bash
docker exec datamind-postgres psql -U datamind -d datamind -c "DELETE FROM projects WHERE name = '驗證用專案';"
rm -f /tmp/project-api-verify-cookies.txt
```
Expected: `DELETE 1`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/project.py backend/apps/__init__.py
git commit -m "feat: add project CRUD API"
```

---

### Task 2: 後端 — 框架庫 CRUD API

**Files:**
- Create: `backend/routes/framework.py`
- Modify: `backend/apps/__init__.py`

**Interfaces:**
- Consumes: `backend.models.framework.Framework`（既有，不改）、`backend.extensions.db`
- Produces: Flask blueprint `framework_bp`，掛在 `/api/frameworks`：
  - `GET /api/frameworks` → `{"success": true, "result": Framework[]}`
  - `POST /api/frameworks`，body `{title, subtitle, tag, variables, paperTitle, description, independentVars, dependentVars, hypotheses, workflowJson}` → `{"success": true, "result": Framework}`
  - 序列化後的 `Framework` JSON 形狀：`{id, title, subtitle, tag, variables, paperTitle, description, independentVars, dependentVars, hypotheses, workflowJson, date}`
  - 沒有 `PATCH`/`DELETE`（現況前端沒有編輯/刪除框架的介面）

- [ ] **Step 1: 建立 `backend/routes/framework.py`**

```python
"""框架庫 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.framework import Framework

framework_bp = Blueprint("framework", __name__)


def _serialize_framework(framework: Framework) -> dict:
    return {
        "id": framework.id,
        "title": framework.title,
        "subtitle": framework.subtitle,
        "tag": framework.tag,
        "variables": framework.variables,
        "paperTitle": framework.paper_title,
        "description": framework.description,
        "independentVars": framework.independent_vars or [],
        "dependentVars": framework.dependent_vars or [],
        "hypotheses": framework.hypotheses or [],
        "workflowJson": framework.workflow_json,
        "date": framework.created_at.strftime("%Y-%m-%d"),
    }


@framework_bp.route("", methods=["GET"])
@login_required
def list_frameworks():
    frameworks = (
        Framework.query.filter_by(user_id=current_user.id)
        .order_by(Framework.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "result": [_serialize_framework(f) for f in frameworks]})


@framework_bp.route("", methods=["POST"])
@login_required
def create_framework():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"success": False, "error": "title 為必填欄位"}), 400

    framework = Framework(
        user_id=current_user.id,
        title=title,
        subtitle=data.get("subtitle"),
        tag=data.get("tag"),
        variables=data.get("variables"),
        paper_title=data.get("paperTitle"),
        description=data.get("description"),
        independent_vars=data.get("independentVars"),
        dependent_vars=data.get("dependentVars"),
        hypotheses=data.get("hypotheses"),
        workflow_json=data.get("workflowJson"),
    )
    db.session.add(framework)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
```

- [ ] **Step 2: 在 `backend/apps/__init__.py` 註冊 blueprint**

找到（Task 1 已經改過一次的版本）：
```python
    from routes.auth import auth_bp
    from routes.health import health_bp
    from routes.project import project_bp
    from routes.rag import rag_bp
```
改成：
```python
    from routes.auth import auth_bp
    from routes.framework import framework_bp
    from routes.health import health_bp
    from routes.project import project_bp
    from routes.rag import rag_bp
```

並找到：
```python
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(project_bp, url_prefix="/api/projects")
    app.register_blueprint(health_bp)
```
改成：
```python
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(project_bp, url_prefix="/api/projects")
    app.register_blueprint(framework_bp, url_prefix="/api/frameworks")
    app.register_blueprint(health_bp)
```

- [ ] **Step 3: 手動驗證（curl）**

```bash
COOKIE_JAR=/tmp/framework-api-verify-cookies.txt
rm -f "$COOKIE_JAR"

curl -s -c "$COOKIE_JAR" -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@datamind.local","password":"changeme-locally"}'
```
Expected: `"success":true`

```bash
curl -s -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST http://localhost:5001/api/frameworks \
  -H "Content-Type: application/json" \
  -d '{"title":"驗證用框架","subtitle":"","tag":"測試","variables":3,"paperTitle":"","description":"","independentVars":["x1"],"dependentVars":["y1"],"hypotheses":[]}'
```
Expected: 回傳 `result.id` 是整數、`result.independentVars` 是 `["x1"]`

```bash
curl -s -b "$COOKIE_JAR" http://localhost:5001/api/frameworks
```
Expected: `result` 陣列包含剛建立的框架

- [ ] **Step 4: 清理測試資料**

```bash
docker exec datamind-postgres psql -U datamind -d datamind -c "DELETE FROM frameworks WHERE title = '驗證用框架';"
rm -f /tmp/framework-api-verify-cookies.txt
```
Expected: `DELETE 1`

- [ ] **Step 5: Commit**

```bash
git add backend/routes/framework.py backend/apps/__init__.py
git commit -m "feat: add framework CRUD API"
```

---

### Task 3: 前端 — `frontend/src/api/project.ts`

**Files:**
- Create: `frontend/src/api/project.ts`

**Interfaces:**
- Consumes: Task 1 的 `GET/POST /api/projects`、`PATCH /api/projects/<id>`
- Produces:
  - `export interface ProjectDTO { id: number; name: string; description: string; frameworkId: number | null; datasetName: string; status: 'draft' | 'running' | 'completed'; progress: number; accuracy?: string; keyFinding?: string; variables: number; date: string }`
  - `export interface CreateProjectPayload { name: string; description: string; frameworkId: number | null; datasetName: string; variables: number }`
  - `export async function listProjects(): Promise<ProjectDTO[]>`
  - `export async function createProject(payload: CreateProjectPayload): Promise<ProjectDTO>`
  - `export async function updateProject(id: number, patch: Partial<{ status: string, progress: number, datasetName: string, accuracy: string, keyFinding: string }>): Promise<ProjectDTO>`

- [ ] **Step 1: 建立檔案**

```ts
export interface ProjectDTO {
  id: number
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  status: 'draft' | 'running' | 'completed'
  progress: number
  accuracy?: string
  keyFinding?: string
  variables: number
  date: string
}

export interface CreateProjectPayload {
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  variables: number
}

export interface UpdateProjectPatch {
  status?: string
  progress?: number
  datasetName?: string
  accuracy?: string
  keyFinding?: string
}

async function parseProjectResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

export async function listProjects (): Promise<ProjectDTO[]> {
  const response = await fetch('/api/projects', { credentials: 'include' })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO[]
}

export async function createProject (payload: CreateProjectPayload): Promise<ProjectDTO> {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}

export async function updateProject (id: number, patch: UpdateProjectPatch): Promise<ProjectDTO> {
  const response = await fetch(`/api/projects/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/api/project.ts` 相關錯誤

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/project.ts
git commit -m "feat: add frontend project API wrapper"
```

---

### Task 4: 前端 — `frontend/src/api/framework.ts`

**Files:**
- Create: `frontend/src/api/framework.ts`

**Interfaces:**
- Consumes: Task 2 的 `GET/POST /api/frameworks`
- Produces:
  - `export interface FrameworkDTO { id: number; title: string; subtitle: string; tag: string; variables: number; paperTitle: string; description: string; independentVars: string[]; dependentVars: string[]; hypotheses: string[]; workflowJson?: Record<string, unknown>; date: string }`
  - `export interface CreateFrameworkPayload { title: string; subtitle: string; tag: string; variables: number; paperTitle: string; description: string; independentVars: string[]; dependentVars: string[]; hypotheses: string[]; workflowJson?: Record<string, unknown> }`
  - `export async function listFrameworks(): Promise<FrameworkDTO[]>`
  - `export async function createFramework(payload: CreateFrameworkPayload): Promise<FrameworkDTO>`

- [ ] **Step 1: 建立檔案**

```ts
export interface FrameworkDTO {
  id: number
  title: string
  subtitle: string
  tag: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
  date: string
}

export interface CreateFrameworkPayload {
  title: string
  subtitle: string
  tag: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
}

async function parseFrameworkResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

export async function listFrameworks (): Promise<FrameworkDTO[]> {
  const response = await fetch('/api/frameworks', { credentials: 'include' })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO[]
}

export async function createFramework (payload: CreateFrameworkPayload): Promise<FrameworkDTO> {
  const response = await fetch('/api/frameworks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO
}
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/framework.ts
git commit -m "feat: add frontend framework API wrapper"
```

---

### Task 5: 前端 — `projectStore.ts` 改寫

**Files:**
- Modify: `frontend/src/store/projectStore.ts`（整檔換掉）

**Interfaces:**
- Consumes: Task 3 的 `listProjects`、`createProject`、`updateProject`、`CreateProjectPayload`
- Produces（給後面 Task 8/9/10 用）:
  - `export interface Project { id: number; name: string; description: string; frameworkId: number | null; datasetName: string; status: 'draft' | 'running' | 'completed'; date: string; progress: number; accuracy?: string; keyFinding?: string; variables: number }`（**不再有** `frameworkName`，`id` 是 `number`）
  - `export interface ActiveProjectContext { projectId: number; datasetFile: File | null; frameworkId: number | null }`
  - `useProjectStore()` 回傳：`projects`, `activeContext`, `loadProjects(): Promise<void>`, `addProject(p: CreateProjectPayload): Promise<Project>`, `updateProjectStatus(projectId: number, status): Promise<void>`, `updateProjectProgress(projectId: number, progress: number): Promise<void>`, `pollProjectJob(projectId: number, jobId: string): void`, `setActiveContext`, `clearActiveContext`

- [ ] **Step 1: 整檔換成**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { type CreateProjectPayload, createProject, listProjects, updateProject } from '@/api/project'
import { fetchWorkflowJob, WorkflowJobNotFoundError } from '@/api/workflow'
import { clearActiveJobIdFromStorage, loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'

const JOB_POLL_INTERVAL_MS = 2000

export interface Project {
  id: number
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  status: 'draft' | 'running' | 'completed'
  date: string
  progress: number
  accuracy?: string
  keyFinding?: string
  variables: number
}

export interface ActiveProjectContext {
  projectId: number
  datasetFile: File | null
  frameworkId: number | null
}

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

  async function addProject (p: CreateProjectPayload): Promise<Project> {
    const created = await createProject(p)
    projects.value = [created, ...projects.value]
    return created
  }

  async function updateProjectStatus (projectId: number, status: Project['status']): Promise<void> {
    const target = projects.value.find(p => p.id === projectId)
    if (target) target.status = status
    try {
      await updateProject(projectId, { status, progress: target?.progress })
    } catch (error) {
      console.error('更新專案狀態失敗', error)
    }
  }

  async function updateProjectProgress (projectId: number, progress: number): Promise<void> {
    const target = projects.value.find(p => p.id === projectId)
    if (target) target.progress = progress
    try {
      await updateProject(projectId, { progress })
    } catch (error) {
      console.error('更新專案進度失敗', error)
    }
  }

  // store 是整個 App 生命週期內的單一實例，輪詢掛在這裡才不會因為離開 WorkflowWorkspace
  // 畫面（例如切回專案列表）就被砍掉，導致列表上的進度卡住、即使後端早就跑完了
  const jobPollers = new Map<number, { intervalId: number, jobId: string }>()

  function pollProjectJob (projectId: number, jobId: string): void {
    const existing = jobPollers.get(projectId)
    if (existing) {
      if (existing.jobId === jobId) {
        return
      }
      window.clearInterval(existing.intervalId)
    }

    const intervalId = window.setInterval(() => {
      ;(async () => {
        try {
          const job = await fetchWorkflowJob(jobId)
          const target = projects.value.find(p => p.id === projectId)
          if (!target) {
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            return
          }

          if (job.totalModels > 0) {
            // 進行中的 tick 只改本地畫面，不寫回資料庫；完成時才持久化（見下方）
            target.progress = Math.round((job.completedModels.length / job.totalModels) * 100)
          }

          if (job.status === 'done' || job.status === 'error') {
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            if (job.status === 'done') {
              target.progress = 100
              await updateProjectStatus(projectId, 'completed')
            }
          }
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
      })()
    }, JOB_POLL_INTERVAL_MS)
    jobPollers.set(projectId, { intervalId, jobId })
  }

  function setActiveContext (ctx: ActiveProjectContext): void {
    activeContext.value = ctx
  }

  function clearActiveContext (): void {
    activeContext.value = null
  }

  return { projects, activeContext, loadProjects, addProject, updateProjectStatus, updateProjectProgress, pollProjectJob, setActiveContext, clearActiveContext }
})
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 會出現其他還沒改的檔案（`CreateProjectView.vue` 等）的型別錯誤，這是預期的——它們會在後面的 Task 修正。只要確認錯誤訊息都指向**其他檔案**、不是 `projectStore.ts` 本身的型別問題即可。

Run: `cd frontend && npm run lint`
Expected: `src/store/projectStore.ts` 本身無 lint 錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/projectStore.ts
git commit -m "feat: rewrite projectStore to use database API"
```

---

### Task 6: 前端 — `frameworkStore.ts` 改寫

**Files:**
- Modify: `frontend/src/store/frameworkStore.ts`（整檔換掉）

**Interfaces:**
- Consumes: Task 4 的 `listFrameworks`、`createFramework`、`CreateFrameworkPayload`
- Produces（給後面 Task 8/9 用）:
  - `export interface Framework { id: number; title: string; subtitle: string; tag: string; date: string; variables: number; paperTitle: string; description: string; independentVars: string[]; dependentVars: string[]; hypotheses: string[]; workflowJson?: Record<string, unknown> }`（型別不變，只是資料來源換掉）
  - `useFrameworkStore()` 回傳：`frameworks`, `loadFrameworks(): Promise<void>`, `addFramework(fw: CreateFrameworkPayload): Promise<Framework>`

- [ ] **Step 1: 整檔換成**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { type CreateFrameworkPayload, createFramework, listFrameworks } from '@/api/framework'

export interface Framework {
  id: number
  title: string
  subtitle: string
  tag: string
  date: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
}

export const useFrameworkStore = defineStore('framework', () => {
  const frameworks = ref<Framework[]>([])

  async function loadFrameworks (): Promise<void> {
    try {
      frameworks.value = await listFrameworks()
    } catch (error) {
      console.error('載入框架庫失敗', error)
    }
  }

  async function addFramework (fw: CreateFrameworkPayload): Promise<Framework> {
    const created = await createFramework(fw)
    frameworks.value = [created, ...frameworks.value]
    return created
  }

  return { frameworks, loadFrameworks, addFramework }
})
```

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 可能有其他還沒改的檔案（`ExtractFrameworkView.vue`）的型別錯誤，屬預期，後面 Task 會修

Run: `cd frontend && npm run lint`
Expected: `src/store/frameworkStore.ts` 本身無 lint 錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/frameworkStore.ts
git commit -m "feat: rewrite frameworkStore to use database API"
```

---

### Task 7: 前端 — `main.ts` 開機時載入專案/框架

**Files:**
- Modify: `frontend/src/main.ts`

**Interfaces:**
- Consumes: Task 5 的 `useProjectStore().loadProjects`、Task 6 的 `useFrameworkStore().loadFrameworks`
- Produces: 無（純啟動流程調整）

- [ ] **Step 1: 修改檔案**

把整個檔案內容換成：

```ts
/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Composables
import { createApp } from 'vue'

// Plugins
import { registerPlugins } from '@/plugins'

// Store
import { useAuthStore } from '@/store/authStore'
import { useFrameworkStore } from '@/store/frameworkStore'
import { useProjectStore } from '@/store/projectStore'

// Components
import App from './App.vue'

// Styles
import 'unfonts.css'
import './styles/tailwind.css'
import './styles/main.scss'

const app = createApp(App)

registerPlugins(app)

const authStore = useAuthStore()
const projectStore = useProjectStore()
const frameworkStore = useFrameworkStore()

authStore.checkSession().finally(() => {
  app.mount('#app')
})
projectStore.loadProjects()
frameworkStore.loadFrameworks()
```

未登入時 `loadProjects()`/`loadFrameworks()` 打 API 會收到 401，依 Task 5/6 的 `catch` 邏輯保持空陣列即可，不影響後續路由守衛導去 `/login`。

- [ ] **Step 2: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向 `src/main.ts`

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/main.ts
git commit -m "feat: load projects and frameworks on app boot"
```

---

### Task 8: 前端 — 建立流程呼叫端調整

**Files:**
- Modify: `frontend/src/views/hub/CreateProjectView.vue`
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue`

**Interfaces:**
- Consumes: Task 5 的 `projectStore.addProject(payload: CreateProjectPayload): Promise<Project>`、Task 6 的 `frameworkStore.addFramework(payload: CreateFrameworkPayload): Promise<Framework>`

- [ ] **Step 1: 修改 `CreateProjectView.vue` 的 `executeProject`**

找到（在 `<script setup>` 裡）：
```ts
  function executeProject (): void {
    const today = new Date().toISOString().slice(0, 10)
    const project = projectStore.addProject({
      name: form.value.name || '未命名專案',
      description: form.value.description,
      frameworkId: form.value.frameworkId,
      frameworkName: selectedFramework.value?.title ?? '',
      datasetName: form.value.datasetFile?.name ?? '',
      status: 'draft',
      date: today,
      progress: 0,
      variables: selectedFramework.value?.variables ?? 0,
    })

    projectStore.setActiveContext({
      projectId: project.id,
      datasetFile: form.value.datasetFile,
      frameworkId: form.value.frameworkId,
    })

    router.push(`/workflow?project=${project.id}`)
  }
```

改成：
```ts
  async function executeProject (): Promise<void> {
    const project = await projectStore.addProject({
      name: form.value.name || '未命名專案',
      description: form.value.description,
      frameworkId: form.value.frameworkId,
      datasetName: form.value.datasetFile?.name ?? '',
      variables: selectedFramework.value?.variables ?? 0,
    })

    projectStore.setActiveContext({
      projectId: project.id,
      datasetFile: form.value.datasetFile,
      frameworkId: form.value.frameworkId,
    })

    router.push(`/workflow?project=${project.id}`)
  }
```

（`status`/`date`/`progress`/`frameworkName` 都改成由後端決定，不再由前端傳入；`today` 常數整個移除）

- [ ] **Step 2: 修改 `ExtractFrameworkView.vue` 的 `saveFramework`**

找到：
```ts
  function saveFramework (): void {
    if (!extractedData.value) return
    const d = extractedData.value
    const today = new Date().toISOString().slice(0, 10)
    store.addFramework({
      title: d.name,
      subtitle: d.models.join('、') || '未命名方法',
      tag: d.models[0] ?? 'AI 提取',
      date: today,
      variables: d.preprocessing.length + d.featureEngineering.length,
      paperTitle: d.name,
      description: `目標欄位：${d.targetCol || '未知'}。評估指標：${d.metrics.join(', ') || '未知'}。`,
      independentVars: [...d.preprocessing, ...d.featureEngineering],
      dependentVars: d.targetCol ? [d.targetCol] : [],
      hypotheses: [],
      workflowJson: rawWorkflowJson.value ?? undefined,
    })
    extractedData.value = null
    rawWorkflowJson.value = null
    selectedFile.value = null
    router.push('/hub/library')
  }
```

改成：
```ts
  async function saveFramework (): Promise<void> {
    if (!extractedData.value) return
    const d = extractedData.value
    await store.addFramework({
      title: d.name,
      subtitle: d.models.join('、') || '未命名方法',
      tag: d.models[0] ?? 'AI 提取',
      variables: d.preprocessing.length + d.featureEngineering.length,
      paperTitle: d.name,
      description: `目標欄位：${d.targetCol || '未知'}。評估指標：${d.metrics.join(', ') || '未知'}。`,
      independentVars: [...d.preprocessing, ...d.featureEngineering],
      dependentVars: d.targetCol ? [d.targetCol] : [],
      hypotheses: [],
      workflowJson: rawWorkflowJson.value ?? undefined,
    })
    extractedData.value = null
    rawWorkflowJson.value = null
    selectedFile.value = null
    router.push('/hub/library')
  }
```

（`date`/`today` 整個移除，改由後端決定）

- [ ] **Step 3: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向這兩個檔案（`frameworkName` 相關的型別錯誤應該消失了）

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/CreateProjectView.vue frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "feat: update project/framework creation flows for database-backed stores"
```

---

### Task 9: 前端 — 顯示層 `frameworkName` 查表 + id 型別修正

**Files:**
- Modify: `frontend/src/views/hub/ProjectsView.vue`
- Modify: `frontend/src/views/hub/ProjectDetailView.vue`
- Modify: `frontend/src/views/hub/ResultView.vue`

**Interfaces:**
- Consumes: Task 5 的 `Project`（`id: number`，無 `frameworkName`）、Task 6 的 `Framework`（`id: number`, `title: string`）

- [ ] **Step 1: `ProjectsView.vue`**

在 `<script setup>` 裡，把：
```ts
  import type { Project } from '@/store/projectStore'
  import { RouterLink } from 'vue-router'
  import { useProjectStore } from '@/store/projectStore'

  const store = useProjectStore()
```
改成：
```ts
  import type { Project } from '@/store/projectStore'
  import { RouterLink } from 'vue-router'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'

  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()
```

並在 `statusLabel` 之後、`projectLink` 之前加一個新函式：
```ts
  function frameworkTitle (project: Project): string {
    return frameworkStore.frameworks.find(fw => fw.id === project.frameworkId)?.title ?? '（未選擇）'
  }
```

template 裡把：
```html
          <div class="project-meta">框架：{{ project.frameworkName }}</div>
```
改成：
```html
          <div class="project-meta">框架：{{ frameworkTitle(project) }}</div>
```

- [ ] **Step 2: `ProjectDetailView.vue`**

把：
```ts
  import { computed } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { useProjectStore } from '@/store/projectStore'

  const route = useRoute()
  const router = useRouter()
  const store = useProjectStore()
```
改成：
```ts
  import { computed } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'

  const route = useRoute()
  const router = useRouter()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()
```

把：
```ts
  const project = computed(() =>
    store.projects.find(p => p.id === route.params.id),
  )
```
改成：
```ts
  const project = computed(() =>
    store.projects.find(p => p.id === Number(route.params.id)),
  )

  const frameworkTitle = computed(() =>
    frameworkStore.frameworks.find(fw => fw.id === project.value?.frameworkId)?.title ?? '（未選擇）',
  )
```

template 裡把：
```html
      <div class="framework-link">框架：{{ project.frameworkName }}</div>
```
改成：
```html
      <div class="framework-link">框架：{{ frameworkTitle }}</div>
```

- [ ] **Step 3: `ResultView.vue`**

把：
```ts
  import { useProjectStore } from '@/store/projectStore'
```
改成：
```ts
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
```

並把：
```ts
  const route = useRoute()
  const store = useProjectStore()

  const projectId = computed(() => route.params.id as string)

  const project = computed(() =>
    store.projects.find(p => p.id === projectId.value),
  )
```
改成：
```ts
  const route = useRoute()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // 注意：projectId 維持字串型別——這個變數後面還會拿去當 localStorage 的 key
  // （loadWorkflowStateFromStorage 等函式都吃字串），只有跟 store.projects 比對時才轉數字
  const projectId = computed(() => route.params.id as string)

  const project = computed(() =>
    store.projects.find(p => p.id === Number(projectId.value)),
  )

  const frameworkTitle = computed(() =>
    frameworkStore.frameworks.find(fw => fw.id === project.value?.frameworkId)?.title ?? '（未選擇）',
  )
```

template 裡把：
```html
          <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
```
改成：
```html
          <p class="page-sub">結果總覽 · 框架：{{ frameworkTitle }}</p>
```

- [ ] **Step 4: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤指向這三個檔案

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/ProjectsView.vue frontend/src/views/hub/ProjectDetailView.vue frontend/src/views/hub/ResultView.vue
git commit -m "fix: look up framework title by id instead of denormalized field"
```

---

### Task 10: 前端 — `WorkflowWorkspace.vue` id 型別修正

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: Task 5 的 `Project`（`id: number`）、`projectStore.updateProjectProgress(projectId: number, ...)`、`pollProjectJob(projectId: number, ...)`、`updateProjectStatus(projectId: number, ...)`

這個檔案裡的 `projectId` computed（`const projectId = computed(() => route.query.project as string | undefined)`）**不要改**——它同時也拿去當 localStorage 相關 composable（`saveWorkflowStateToStorage`、`loadWorkflowStateFromStorage` 等）的 key，那些都吃字串，是這次計畫範圍外的東西。只在跟 `projectStore` 互動的地方，個別把 `projectId.value` 包一層 `Number(...)`。

- [ ] **Step 1: 修正 `onProgress`/`onJobActive` callback**

找到：
```ts
    onProgress: pct => {
      if (projectId.value) projectStore.updateProjectProgress(projectId.value, pct)
    },
    onJobActive: jobId => {
      if (projectId.value) projectStore.pollProjectJob(projectId.value, jobId)
    },
```
改成：
```ts
    onProgress: pct => {
      if (projectId.value) projectStore.updateProjectProgress(Number(projectId.value), pct)
    },
    onJobActive: jobId => {
      if (projectId.value) projectStore.pollProjectJob(Number(projectId.value), jobId)
    },
```

- [ ] **Step 2: 修正 `markProjectRunning`**

找到：
```ts
  // 專案狀態：草稿建立後從未變動過，這裡讓它跟著 workflow 實際進度走
  function markProjectRunning (): void {
    if (!projectId.value) return
    const target = projectStore.projects.find(p => p.id === projectId.value)
    if (target && target.status !== 'running') {
      projectStore.updateProjectStatus(projectId.value, 'running')
    }
  }
```
改成：
```ts
  // 專案狀態：草稿建立後從未變動過，這裡讓它跟著 workflow 實際進度走
  function markProjectRunning (): void {
    if (!projectId.value) return
    const target = projectStore.projects.find(p => p.id === Number(projectId.value))
    if (target && target.status !== 'running') {
      projectStore.updateProjectStatus(Number(projectId.value), 'running')
    }
  }
```

- [ ] **Step 3: 修正 `watch(workflowResult, ...)`**

找到：
```ts
  // workflow 真正跑出結果才算「已完成」；調整設定後重新執行會在 markProjectRunning() 退回「進行中」
  watch(workflowResult, val => {
    if (val && projectId.value) {
      projectStore.updateProjectStatus(projectId.value, 'completed')
    }
  })
```
改成：
```ts
  // workflow 真正跑出結果才算「已完成」；調整設定後重新執行會在 markProjectRunning() 退回「進行中」
  watch(workflowResult, val => {
    if (val && projectId.value) {
      projectStore.updateProjectStatus(Number(projectId.value), 'completed')
    }
  })
```

- [ ] **Step 4: 修正 `onMounted` 裡的專案狀態檢查**

找到：
```ts
      if (projectId.value) {
        const target = projectStore.projects.find(p => p.id === projectId.value)
        if (target && target.status !== 'completed') markProjectRunning()
      }
```
改成：
```ts
      if (projectId.value) {
        const target = projectStore.projects.find(p => p.id === Number(projectId.value))
        if (target && target.status !== 'completed') markProjectRunning()
      }
```

- [ ] **Step 5: 型別檢查與 lint**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤（改之前這個檔案應該會因為 `string`/`number` 不匹配而報型別錯誤，改完應該乾淨）

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "fix: convert project id to number when calling projectStore from workflow workspace"
```

---

### Task 11: 整批驗證

**Files:** 無新增/修改檔案，純驗證

**Interfaces:**
- Consumes: Task 1-10 全部產出

- [ ] **Step 1: 確認容器正在跑且 type-check 全專案乾淨**

Run: `docker ps --format "{{.Names}}"`
Expected: 包含 `datamind-frontend`、`datamind-backend`、`datamind-postgres`

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 2: 瀏覽器驗證 — 空清單**

登入（用管理員帳號或新註冊一個帳號），開啟 Hub Dashboard、`/hub/projects`、`/hub/library`
Expected: 專案跟框架都顯示空清單（沒有殘留的示範資料）

- [ ] **Step 3: 瀏覽器驗證 — 建立框架後重新整理仍在**

到 `/hub/library/extract`，走「擷取框架」流程建立一個框架 → 導回 `/hub/library` 應該看到剛建立的框架 → 重新整理頁面 → 框架仍然存在（代表真的寫進資料庫，不是只存在記憶體）

- [ ] **Step 4: 瀏覽器驗證 — 建立專案並正確顯示框架名稱**

到 `/hub/projects/new`，選擇剛建立的框架，走完流程建立專案 → 應該導到 `/workflow?project=<id>`（`<id>` 是資料庫真實整數 id）→ 回到 `/hub/projects`，專案列表要正確顯示框架名稱（不是空白或 `undefined`）

- [ ] **Step 5: 瀏覽器驗證 — 執行工作流程時狀態正確持久化**

在 `/workflow?project=<id>` 開始執行 → 重新整理頁面 → 專案狀態應該還是「進行中」（代表 `markProjectRunning` 有即時持久化）→ 等待執行完成 → 專案狀態變成「已完成」、`progress` 是 100 → 重新整理頁面確認最終值有持久化

- [ ] **Step 6: 瀏覽器開發者工具驗證 — 輪詢不寫資料庫**

執行工作流程期間，開瀏覽器 Network 分頁，篩選 `projects`
Expected: 過程中的 2 秒輪詢**不會**觸發 `PATCH /api/projects/:id`，只有開始跟結束各出現一次

- [ ] **Step 7: 資料隔離驗證**

登出，用另一個帳號註冊並登入
Expected: 看不到第一個帳號建立的專案或框架

無需 commit（這個任務不產生程式碼變更）。
