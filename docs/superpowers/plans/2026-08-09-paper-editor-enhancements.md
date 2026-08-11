# 論文編輯器增強 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 論文編輯器新增「插入變數表格」功能、修正刪除線圖示與底線功能、補齊表格編輯的基本操作（合併/拆分儲存格、儲存格底色、列/欄插在前面、刪除表格）。

**Architecture:** 後端加一支單一專案查詢 API；前端把欄位對應結果的持久化格式從「變數名→欄位名」擴充成「變數名→{欄位名,型別}」；`PaperEditor.vue` 的工具列依序補上插入變數表格按鈕、修正兩個既有圖示問題、以及一組表格編輯按鈕（其中儲存格底色需要擴充 Tiptap 的 TableCell/TableHeader）。

**Tech Stack:** Flask + SQLAlchemy（後端）、Vue 3 + TypeScript + Tiptap v3（前端富文字編輯器）。

## Global Constraints

- 所有使用者可見文字、程式註解一律用繁體中文
- 只新增一個 npm 套件：`@tiptap/extension-underline`；其餘表格功能全部用專案已裝的 `@tiptap/extension-table`／`table-cell`／`table-header`／`table-row` 既有指令，不裝新套件
- `project.column_mapping` 是 JSONB，後端對其內容完全不做結構驗證（純轉存），前後端型別要靠前端自己維持一致
- 工具列按鈕一律沿用既有樣式：`.toolbar-btn-wrap` 包一個 `data-tooltip` 屬性 + `v-btn size="small"`（比照 `frontend/src/components/paper/PaperEditor.vue` 現有寫法）
- 前端沒有自動化測試框架，驗證方式是 `npm run type-check` / `npm run build` + 手動瀏覽器測試
- 後端 `backend/routes/project.py` 目前完全沒有 pytest 覆蓋（會實際查詢/寫入 DB 的路由，這個專案的慣例是不寫 mock DB 的 pytest，而是手動對開發用資料庫驗證），這次新增的端點延續這個慣例，不新增 pytest
- 後端指令一律透過 `docker exec datamind-backend uv run <command>` 執行（host 端 `backend/.venv` 在這台 Windows 機器上是壞的），前端指令直接在 host 執行（`frontend/node_modules` 在 host 上是好的）

---

## Task 1: 後端：新增單一專案查詢 API

**Files:**
- Modify: `backend/routes/project.py`（新增 `GET /<int:project_id>` 路由）
- Modify: `backend/models/project.py:33`（更新過時的欄位註解）

**Interfaces:**
- Produces: `GET /api/projects/<id>` — 成功回傳 `{"success": true, "result": {...與現有 _serialize_project 相同欄位..., "columnMapping": {...}}}`；查無此專案或不屬於目前使用者回 404 `{"success": false, "error": "找不到專案"}`

- [ ] **Step 1: 在 `backend/routes/project.py` 新增路由**

在 `update_project` 函式（檔案最後）**之前**插入：

```python
@project_bp.route("/<int:project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    return jsonify({"success": True, "result": _serialize_project(project)})
```

- [ ] **Step 2: 更新 `backend/models/project.py` 過時的欄位註解**

把：

```python
    # { 論文變數名: 使用者欄位名 }，由欄位對齊頁寫入
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

改成：

```python
    # { 論文變數名: { column: 使用者欄位名, type: 變數型別 } }，由欄位對齊頁寫入
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 3: 手動驗證（對開發用資料庫）**

Run（在 `backend/` 目錄下）:

```bash
docker exec datamind-backend uv run python - <<'EOF'
from apps import create_app
from extensions import db
from models.project import Project
from models.user import User

app = create_app()
with app.app_context():
    admin = User.query.filter_by(email="admin@datamind.local").first()
    other_project = Project.query.filter(Project.user_id != admin.id).first()
    print("admin_id", admin.id)
    print("has_project_owned_by_other_user", other_project is not None)
    print("other_project_id", other_project.id if other_project else None)
EOF
```

記下輸出的 `admin_id`（用來登入）跟一個屬於 admin 的專案 id（沒有的話用下面指令建一個）：

```bash
curl -s -c /tmp/verify_cookies.txt -X POST http://localhost:5001/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@datamind.local","password":"changeme-locally"}'
curl -s -b /tmp/verify_cookies.txt http://localhost:5001/api/projects
```

從上面 `GET /api/projects` 的回傳結果拿一個屬於 admin 的專案 `id`（例如 `3`），驗證新端點：

```bash
curl -s -b /tmp/verify_cookies.txt http://localhost:5001/api/projects/3
```

Expected: `{"success": true, "result": {"id": 3, ... "columnMapping": ...}}`

再驗證查不存在的 id 會回 404：

```bash
curl -s -w "\nHTTP_STATUS:%{http_code}\n" -b /tmp/verify_cookies.txt http://localhost:5001/api/projects/999999
```

Expected: `HTTP_STATUS:404`，body 是 `{"success": false, "error": "找不到專案"}`

- [ ] **Step 4: Commit**

```bash
git add backend/routes/project.py backend/models/project.py
git commit -m "feat: add GET /api/projects/<id> endpoint"
```

---

## Task 2: 前端：欄位對應資料改存變數型別

**Files:**
- Modify: `frontend/src/api/project.ts`
- Modify: `frontend/src/store/projectStore.ts`
- Modify: `frontend/src/views/hub/FieldMappingView.vue:667-676`（`confirmAndRun` 裡組 mapping 的地方）+ `frontend/src/views/hub/FieldMappingView.vue:681-685`（`renameByColumn` 反查的地方）

**Interfaces:**
- Consumes: Task 1 的 `GET /api/projects/<id>`
- Produces: `VariableMapping { column: string, type: string }`（`frontend/src/api/project.ts` 匯出）；`getProject(id: number): Promise<ProjectDTO>`；`ProjectDTO.columnMapping` / `Project.columnMapping` 型別變成 `Record<string, VariableMapping> | null` — Task 3 會讀取這個型別

- [ ] **Step 1: 修改 `frontend/src/api/project.ts`**

把檔案開頭的：

```typescript
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
  columnMapping?: Record<string, string> | null
  date: string
}
```

改成：

```typescript
export interface VariableMapping {
  column: string
  type: string
}

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
  columnMapping?: Record<string, VariableMapping> | null
  date: string
}
```

把：

```typescript
export interface UpdateProjectPatch {
  status?: string
  progress?: number
  datasetName?: string
  accuracy?: string
  keyFinding?: string
  columnMapping?: Record<string, string>
  variables?: number
}
```

改成：

```typescript
export interface UpdateProjectPatch {
  status?: string
  progress?: number
  datasetName?: string
  accuracy?: string
  keyFinding?: string
  columnMapping?: Record<string, VariableMapping>
  variables?: number
}
```

在檔案最後（`updateProject` 函式之後）新增：

```typescript

export async function getProject (id: number): Promise<ProjectDTO> {
  const response = await fetch(`/api/projects/${id}`, { credentials: 'include' })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}
```

- [ ] **Step 2: 修改 `frontend/src/store/projectStore.ts`**

把：

```typescript
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
  /** 對映關係：{ 論文變數名: 使用者欄位名 }。供資料表面板顯示對照來源用。 */
  columnMapping?: Record<string, string> | null
}
```

改成：

```typescript
export interface VariableMapping {
  column: string
  type: string
}

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
  /** 對映關係：{ 論文變數名: { column: 使用者欄位名, type: 變數型別 } }。 */
  columnMapping?: Record<string, VariableMapping> | null
}
```

把：

```typescript
  async function saveColumnMapping (
    projectId: number,
    mapping: Record<string, string>,
  ): Promise<void> {
```

改成：

```typescript
  async function saveColumnMapping (
    projectId: number,
    mapping: Record<string, VariableMapping>,
  ): Promise<void> {
```

- [ ] **Step 3: 修改 `frontend/src/views/hub/FieldMappingView.vue` 的 `confirmAndRun`**

把：

```typescript
    const mapping: Record<string, string> = {}
    for (const item of items.value) {
      if (item.matched_user_column && item.status !== 'SKIPPED') {
        mapping[item.paper_variable] = item.matched_user_column
      }
    }
```

改成：

```typescript
    const mapping: Record<string, { column: string, type: string }> = {}
    for (const item of items.value) {
      if (item.matched_user_column && item.status !== 'SKIPPED') {
        mapping[item.paper_variable] = { column: item.matched_user_column, type: item.required_type }
      }
    }
```

把：

```typescript
      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, column] of Object.entries(mapping)) {
        renameByColumn.set(column, variable)
      }
```

改成：

```typescript
      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, info] of Object.entries(mapping)) {
        renameByColumn.set(info.column, variable)
      }
```

- [ ] **Step 4: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 5: 手動驗證**

啟動前端（如果還沒啟動）：容器 `datamind-frontend` 已在跑 `npm run dev`，改完檔案會自動 reload。

瀏覽器測試：
1. 開一個還沒做過欄位對應的專案，走一次「欄位對應」流程，確認到最後一步能正常送出、導到 `/workflow`
2. 打開瀏覽器開發者工具的 Network 分頁，找到那次 `PATCH /api/projects/<id>` 的 request payload，確認 `columnMapping` 的每個值是 `{ column: "...", type: "..." }` 物件，不是純字串

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/project.ts frontend/src/store/projectStore.ts frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: persist variable type alongside column mapping"
```

---

## Task 3: PaperEditor：插入變數表格按鈕

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: `getProject(id: number)`、`VariableMapping`（Task 2，`frontend/src/api/project.ts`）
- Produces: 無（純 UI 功能，末端任務）

- [ ] **Step 1: 修改 `frontend/src/components/paper/PaperEditor.vue` 的 `<script setup>` imports**

把：

```typescript
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { CharacterCount } from '@tiptap/extension-character-count'
  import { Link } from '@tiptap/extension-link'
  import { Subscript } from '@tiptap/extension-subscript'
  import { Superscript } from '@tiptap/extension-superscript'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { ref, watch } from 'vue'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
```

改成：

```typescript
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { CharacterCount } from '@tiptap/extension-character-count'
  import { Link } from '@tiptap/extension-link'
  import { Subscript } from '@tiptap/extension-subscript'
  import { Superscript } from '@tiptap/extension-superscript'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
```

- [ ] **Step 2: 在 `props` 定義之後新增變數表格相關的 state 與函式**

把：

```typescript
  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)
  const linkUrlDraft = ref('')
```

改成：

```typescript
  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)
  const linkUrlDraft = ref('')
  const projectColumnMapping = ref<Record<string, VariableMapping> | null>(null)

  onMounted(async () => {
    if (!props.projectId) return
    try {
      const project = await getProject(Number(props.projectId))
      projectColumnMapping.value = project.columnMapping ?? null
    } catch {
      projectColumnMapping.value = null
    }
  })

  const hasVariableMapping = computed(
    () => !!projectColumnMapping.value && Object.keys(projectColumnMapping.value).length > 0,
  )

  function escapeHtml (value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
  }

  function insertVariableTable () {
    if (!projectColumnMapping.value) return
    const rows = Object.entries(projectColumnMapping.value)
      .map(([name, info]) => `<tr><td>${escapeHtml(name)}</td><td></td><td>${escapeHtml(info.type)}</td></tr>`)
      .join('')
    const html = `<table><tbody><tr><th>變數名稱</th><th>定義</th><th>型別</th></tr>${rows}</tbody></table>`
    editor.value?.chain().focus().insertContent(html).run()
  }
```

- [ ] **Step 3: 在工具列的「插入表格」按鈕之後、`v-if="editor?.isActive('table')"` 區塊之前新增按鈕**

把：

```html
        <div class="toolbar-btn-wrap" data-tooltip="插入表格">
          <v-btn
            icon="mdi-table-plus"
            size="small"
            variant="text"
            @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
          />
        </div>
        <template v-if="editor?.isActive('table')">
```

改成：

```html
        <div class="toolbar-btn-wrap" data-tooltip="插入表格">
          <v-btn
            icon="mdi-table-plus"
            size="small"
            variant="text"
            @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="插入變數表格">
          <v-btn
            :disabled="!hasVariableMapping"
            icon="mdi-table-account"
            size="small"
            variant="text"
            @click="insertVariableTable"
          />
        </div>
        <template v-if="editor?.isActive('table')">
```

- [ ] **Step 4: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 5: 手動驗證**

1. 打開一個**還沒**做過欄位對應的專案的論文編輯頁（`/paper?project=<id>`），進入編輯模式，確認「插入變數表格」按鈕是灰的（disabled）
2. 打開一個**已經**完成欄位對應的專案（可以先用 Task 2 驗證步驟裡走過流程的那個專案），進入論文編輯頁的編輯模式，點「插入變數表格」，確認游標位置插入一個三欄表格，欄位是「變數名稱／定義／型別」，變數名稱與型別欄有正確值，定義欄是空的
3. 儲存論文、重新整理頁面，確認剛插入的表格內容還在

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add insert-variable-table button to paper editor"
```

---

## Task 4: PaperEditor：修正刪除線圖示與底線功能

**Files:**
- Create: `frontend/src/components/paper/StrikethroughIcon.vue`
- Modify: `frontend/package.json`（新增 `@tiptap/extension-underline`）
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Produces: `<StrikethroughIcon />` 元件（無 props，純顯示用）

- [ ] **Step 1: 建立 `frontend/src/components/paper/StrikethroughIcon.vue`**

```vue
<template>
  <span class="strikethrough-icon" aria-hidden="true">S</span>
</template>

<style scoped>
.strikethrough-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
  font-size: 19px;
  font-weight: 700;
  line-height: 1;
  text-decoration: line-through;
  text-decoration-thickness: 2px;
}
</style>
```

- [ ] **Step 2: 安裝 `@tiptap/extension-underline`**

Run（在 `frontend/` 目錄下）: `npm install @tiptap/extension-underline@^3.29.2 --legacy-peer-deps`

（這個專案的 `package.json` 對 Tiptap v3 系列全部釘在 `^3.29.x`，`--legacy-peer-deps` 是既有慣例，見 `docker-compose.yml` 的 frontend service 啟動指令註解。）

Expected: `frontend/package.json` 的 `dependencies` 多一行 `"@tiptap/extension-underline": "^3.29.2"`（或 npm 實際解析到的版本）

- [ ] **Step 3: 修改 `frontend/src/components/paper/PaperEditor.vue` 的 imports**

把（Task 3 已經改過一次，這是 Task 3 之後的狀態）：

```typescript
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
```

改成：

```typescript
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { Underline } from '@tiptap/extension-underline'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'
```

- [ ] **Step 4: 把 `Underline` 加進 `useEditor` 的 extensions 陣列**

把：

```typescript
      StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
```

改成：

```typescript
      StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
```

- [ ] **Step 5: 把刪除線按鈕的 icon 換成 `StrikethroughIcon` 元件**

把：

```html
        <div class="toolbar-btn-wrap" data-tooltip="刪除線">
          <v-btn
            icon="mdi-format-strikethrough"
            size="small"
            :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
            @click="editor?.chain().focus().toggleStrike().run()"
          />
        </div>
```

改成：

```html
        <div class="toolbar-btn-wrap" data-tooltip="刪除線">
          <v-btn
            size="small"
            :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
            @click="editor?.chain().focus().toggleStrike().run()"
          >
            <StrikethroughIcon />
          </v-btn>
        </div>
```

- [ ] **Step 6: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 7: 手動驗證**

1. 論文編輯頁編輯模式下，確認刪除線按鈕變成「S 中間一條線」的樣子，跟粗體/斜體/底線同一種風格
2. 選一段文字點刪除線按鈕，確認文字真的加上刪除線
3. 選一段文字點底線按鈕，確認文字真的加上底線（這是修正前就壞掉的功能，之前點了沒反應）
4. 儲存、重新整理，確認刪除線與底線格式都有正確存回來

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/paper/StrikethroughIcon.vue frontend/src/components/paper/PaperEditor.vue
git commit -m "fix: correct strikethrough icon styling and add missing Underline extension"
```

---

## Task 5: PaperEditor：表格列/欄/儲存格結構操作

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- 無新介面，純工具列按鈕 + Tiptap 既有指令

- [ ] **Step 1: 修改表格工具列區塊，補上合併/拆分儲存格、插在前面、刪除表格**

把（Task 3 已經在這段前面加過「插入變數表格」按鈕，這是接續的狀態）：

```html
        <template v-if="editor?.isActive('table')">
          <div class="toolbar-btn-wrap" data-tooltip="新增列">
            <v-btn
              icon="mdi-table-row-plus-after"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addRowAfter().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="刪除列">
            <v-btn
              icon="mdi-table-row-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteRow().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="新增欄">
            <v-btn
              icon="mdi-table-column-plus-after"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addColumnAfter().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="刪除欄">
            <v-btn
              icon="mdi-table-column-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteColumn().run()"
            />
          </div>
        </template>
```

改成：

```html
        <template v-if="editor?.isActive('table')">
          <div class="toolbar-btn-wrap" data-tooltip="新增列（前）">
            <v-btn
              icon="mdi-table-row-plus-before"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addRowBefore().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="新增列（後）">
            <v-btn
              icon="mdi-table-row-plus-after"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addRowAfter().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="刪除列">
            <v-btn
              icon="mdi-table-row-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteRow().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="新增欄（前）">
            <v-btn
              icon="mdi-table-column-plus-before"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addColumnBefore().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="新增欄（後）">
            <v-btn
              icon="mdi-table-column-plus-after"
              size="small"
              variant="text"
              @click="editor?.chain().focus().addColumnAfter().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="刪除欄">
            <v-btn
              icon="mdi-table-column-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteColumn().run()"
            />
          </div>
          <div v-if="editor?.can().mergeCells()" class="toolbar-btn-wrap" data-tooltip="合併儲存格">
            <v-btn
              icon="mdi-table-merge-cells"
              size="small"
              variant="text"
              @click="editor?.chain().focus().mergeCells().run()"
            />
          </div>
          <div v-if="editor?.can().splitCell()" class="toolbar-btn-wrap" data-tooltip="拆分儲存格">
            <v-btn
              icon="mdi-table-split-cell"
              size="small"
              variant="text"
              @click="editor?.chain().focus().splitCell().run()"
            />
          </div>
          <div class="toolbar-btn-wrap" data-tooltip="刪除表格">
            <v-btn
              icon="mdi-table-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteTable().run()"
            />
          </div>
        </template>
```

- [ ] **Step 2: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 3: 手動驗證**

1. 插入一個表格，游標移進去，確認工具列出現「新增列（前）」「新增列（後）」「刪除列」「新增欄（前）」「新增欄（後）」「刪除欄」「刪除表格」
2. 點「新增列（前）」「新增欄（前）」，確認真的插在游標所在列/欄的前面，不是後面
3. 選取多個相鄰儲存格（滑鼠拖曳選取），確認出現「合併儲存格」按鈕，點擊後確認合併成功
4. 游標移進剛合併的儲存格，確認出現「拆分儲存格」按鈕，點擊後確認拆回原本的格數
5. 點「刪除表格」，確認整個表格被移除
6. 儲存、重新整理，確認合併過的儲存格結構有正確存回來

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add merge/split cell, insert-before, and delete-table controls"
```

---

## Task 6: PaperEditor：儲存格底色

**Files:**
- Create: `frontend/src/components/paper/coloredTableCell.ts`
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Produces: `ColoredTableCell`、`ColoredTableHeader`（`frontend/src/components/paper/coloredTableCell.ts` 匯出，取代原本直接用的 `TableCell`／`TableHeader`）

- [ ] **Step 1: 建立 `frontend/src/components/paper/coloredTableCell.ts`**

比照專案既有的 `frontend/src/components/paper/alignableImage.ts` 寫法：

```typescript
import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'

function backgroundColorAttribute () {
  return {
    backgroundColor: {
      default: null,
      parseHTML: (element: HTMLElement) => element.style.backgroundColor || null,
      renderHTML: (attributes: { backgroundColor?: string | null }) =>
        attributes.backgroundColor ? { style: `background-color: ${attributes.backgroundColor}` } : {},
    },
  }
}

export const ColoredTableCell = TableCell.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      ...backgroundColorAttribute(),
    }
  },
})

export const ColoredTableHeader = TableHeader.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      ...backgroundColorAttribute(),
    }
  },
})
```

- [ ] **Step 2: 修改 `frontend/src/components/paper/PaperEditor.vue` 的 imports**

把（Task 4 已經改過，這是接續的狀態）：

```typescript
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { Underline } from '@tiptap/extension-underline'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'
```

改成：

```typescript
  import { Table } from '@tiptap/extension-table'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { Underline } from '@tiptap/extension-underline'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import { ColoredTableCell, ColoredTableHeader } from '@/components/paper/coloredTableCell'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'
```

（拿掉直接匯入的 `TableCell`／`TableHeader`，改用擴充過的版本。）

- [ ] **Step 3: 修改 `useEditor` 的 extensions 陣列**

把：

```typescript
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
```

改成：

```typescript
      Table.configure({ resizable: true }),
      TableRow,
      ColoredTableHeader,
      ColoredTableCell,
```

- [ ] **Step 4: 新增底色選單的 state 與色票常數**

在 `insertVariableTable` 函式之後新增：

```typescript
  const CELL_BACKGROUND_COLORS: { label: string, value: string | null }[] = [
    { label: '橘', value: '#fdecd2' },
    { label: '灰藍', value: '#e2e8f0' },
    { label: '淡黃', value: '#fdf6b2' },
    { label: '淡綠', value: '#dcf5e3' },
    { label: '無', value: null },
  ]

  function setCellBackgroundColor (color: string | null) {
    editor.value?.chain().focus().setCellAttribute('backgroundColor', color).run()
  }
```

- [ ] **Step 5: 在表格工具列的「刪除表格」按鈕之後新增底色選單**

把（Task 5 加過的區塊，這是接續的狀態）：

```html
          <div class="toolbar-btn-wrap" data-tooltip="刪除表格">
            <v-btn
              icon="mdi-table-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteTable().run()"
            />
          </div>
        </template>
```

改成：

```html
          <div class="toolbar-btn-wrap" data-tooltip="刪除表格">
            <v-btn
              icon="mdi-table-remove"
              size="small"
              variant="text"
              @click="editor?.chain().focus().deleteTable().run()"
            />
          </div>
          <v-menu location="bottom">
            <template #activator="{ props: menuProps }">
              <div class="toolbar-btn-wrap" data-tooltip="儲存格底色">
                <v-btn icon="mdi-format-color-fill" size="small" variant="text" v-bind="menuProps" />
              </div>
            </template>
            <v-card class="cell-color-menu-card">
              <button
                v-for="swatch in CELL_BACKGROUND_COLORS"
                :key="swatch.label"
                class="cell-color-swatch"
                :style="{ backgroundColor: swatch.value ?? '#ffffff' }"
                :title="swatch.label"
                type="button"
                @click="setCellBackgroundColor(swatch.value)"
              />
            </v-card>
          </v-menu>
        </template>
```

- [ ] **Step 6: 新增底色選單的樣式**

在 `<style scoped>` 區塊裡的 `.link-menu-actions` 樣式之後新增：

```css
  .cell-color-menu-card {
    padding: 10px;
    display: flex;
    gap: 8px;
  }

  .cell-color-swatch {
    width: 22px;
    height: 22px;
    border-radius: 5px;
    border: 1.5px solid rgba(28, 33, 48, 0.15);
    cursor: pointer;
  }

  .cell-color-swatch:hover {
    border-color: rgba(28, 33, 48, 0.4);
  }
```

- [ ] **Step 7: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 8: 手動驗證**

1. 游標移進表格任一儲存格，工具列出現「儲存格底色」按鈕，點開看到 5 個色塊（橘/灰藍/淡黃/淡綠/無）
2. 選一個儲存格點「橘」，確認那格背景變橘色
3. 點「無」，確認底色被清除
4. 儲存、重新整理，確認底色有正確存回來
5. 確認 Task 3 的「插入變數表格」功能還能正常用（表頭跟一般儲存格外觀沒有跑掉——`ColoredTableHeader`／`ColoredTableCell` 只是加了一個可選屬性，不影響原本渲染）

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/paper/coloredTableCell.ts frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add cell background color picker to table toolbar"
```

---

## Self-Review

**Spec coverage：**
- 段落 A（資料流變更）→ Task 2
- 段落 B（新增單一專案查詢 API）→ Task 1
- 段落 C（插入變數表格）→ Task 3
- 段落 D（刪除線圖示）→ Task 4
- 段落 E（表格功能增強：合併/拆分、插在前面、刪除表格、儲存格底色）→ Task 5（結構操作）、Task 6（底色）
- 段落 F（修正 Underline 套件缺失）→ Task 4

**Placeholder scan：** 每個 Step 都有完整可執行的程式碼、明確的 Run/Expected，沒有 TBD/TODO。

**Type consistency：** `VariableMapping { column: string, type: string }` 在 Task 2 於 `frontend/src/api/project.ts` 定義，Task 3 從同一個檔案 import 使用，欄位名稱一致。`getProject(id: number): Promise<ProjectDTO>` 簽名在 Task 2 定義、Task 3 呼叫時的參數型別（`Number(props.projectId)`）與回傳值使用（`.columnMapping`）一致。`ColoredTableCell`／`ColoredTableHeader` 在 Task 6 定義並取代 Task 4 之前一路沿用的原生 `TableCell`／`TableHeader` import，兩者的 `addAttributes()` 都正確透過 `...this.parent?.()` 保留原有屬性（沿用 `alignableImage.ts` 已驗證過的既有模式）。`setCellAttribute('backgroundColor', color)` 呼叫的屬性名稱跟 `coloredTableCell.ts` 裡 `addAttributes()` 回傳的 `backgroundColor` 鍵一致。PaperEditor.vue 各 Task 之間的 import 區塊、extensions 陣列改動都是接續狀態（後一個 Task 的「把...改成...」是以前一個 Task 改完後的檔案內容為準），沒有互相矛盾。
