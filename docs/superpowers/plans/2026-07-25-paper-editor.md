# 論文可編輯化（Word 式編輯）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `/paper` 頁面從唯讀渲染變成可編輯（Word 式工具列：粗體/斜體/底線/標題/清單/對齊/表格），並把編輯結果存到後端，下次回訪同一個專案能讀回，同時不遺失引用文獻的歸屬資訊。

**Architecture:** 用 Tiptap（`@tiptap/vue-3`）做單一編輯器元件 `PaperEditor.vue`，`editable` prop 切換檢視/編輯模式；引用歸屬用自訂的 `Citation` mark 附著在文字上（不是烘進純文字），檢視與編輯共用同一份 Tiptap JSON 文件內容。後端沿用 `VectorStore` 的 JSON 檔案持久化模式，新增 `ReportStore`，以 `project_id` 為 key 存/讀。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript + Tiptap 2（`@tiptap/vue-3`, `@tiptap/starter-kit`, extension 系列）、Vuetify；後端 Flask Blueprint + 純 JSON 檔案持久化（無資料庫）。

## Global Constraints

- 前端沒有 vitest/jest；每個前端 task 用 `npm run type-check`（`frontend/` 目錄下，`vue-tsc --build --force`）當自動化把關，其餘用手動瀏覽器驗證。前端 dev server 埠號是 **3000**（見 `frontend/vite.config.mts`），不是 5173；`/api` 已經有 proxy 轉到 `http://127.0.0.1:5001`。
- 後端沒有 pytest/mypy/ruff；每個後端 task 用 `uv run python -c "..."` 直接跑 sanity check（import + 呼叫 + assert），路由類的 task 額外用 `curl` 手動打 API 驗證。後端跑在 5001 埠（`FLASK_PORT` 預設值）。
- 程式碼風格照被修改檔案原本的風格：前端 `.vue`/`.ts`（`views`、`components`、`store`、`utils`、`api`）一律單引號、無分號、2 空白縮排、函式簽名 `functionName (args)` 中間留空格；後端 `.py` 照 `services/rag/`、`routes/rag.py` 現有風格（type hints、`logger.exception(...)`、lazy import service 於 route handler 內部）。
- Out of scope（見 `docs/superpowers/specs/2026-07-25-paper-editor-design.md`）：多人協作/版本歷史、匯出 `.docx`/PDF、參考文獻清單本身的新增/刪除/編輯、自動存檔（debounce）、帳號權限驗證。
- 引用編號 `[n]` 不寫進文字內容，由 `Citation` mark 依 `citations` 陣列順序算出、透過 CSS `attr()` 動態顯示（沿用現有 `mockPaperReport` 註解裡講的既有慣例）。
- `Citation` mark 只承載**第一個** citation id（沿用現有 `PaperSection.vue` 的 `firstCitationId` 行為——多重引用 `[1][2]` 目前點擊本來就只導向第一篇）。

---

## Task 1: 後端 — ReportStore 持久化服務

**Files:**
- Create: `backend/services/report/__init__.py`
- Create: `backend/services/report/report_store.py`

**Interfaces:**
- Produces: `ReportStore(index_dir: str | Path)` with `.save(project_id: str, title: str, content: dict, citations: list) -> dict` and `.load(project_id: str) -> dict | None`；模組層級 `get_report_store() -> ReportStore`。Task 2 的 route handler 是唯一消費者。

- [ ] **Step 1: 建立 package `__init__.py`**

```python
```

（空檔案，比照 `backend/services/rag/__init__.py` 的做法，讓 `services.report` 成為可 import 的 package。）

- [ ] **Step 2: 建立 `backend/services/report/report_store.py`**

```python
"""論文編輯內容持久化服務

以 project_id 為 key，把論文的 Tiptap 文件內容 + 參考文獻清單存成 JSON 檔案。
沒有資料庫，比照 services/rag/vector_store.py 的 JSON 檔案持久化模式。
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ReportStore:
    def __init__(self, index_dir: str | Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, project_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", project_id)
        return self.index_dir / f"{safe_id}.json"

    def save(self, project_id: str, title: str, content: dict, citations: list) -> dict:
        record = {
            "title": title,
            "content": content,
            "citations": citations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path_for(project_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record

    def load(self, project_id: str) -> Optional[dict]:
        path = self._path_for(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[ReportStore] = None


def get_report_store() -> ReportStore:
    global _instance
    if _instance is None:
        index_dir = (
            Path(__file__).parent.parent.parent
            / os.getenv("REPORT_STORE_DIR", "artifacts/paper_reports")
        )
        _instance = ReportStore(index_dir=index_dir)
    return _instance
```

- [ ] **Step 3: Sanity check（無 pytest，直接跑一段驗證腳本）**

Run（在 `backend/` 目錄下）：

```bash
cd backend
uv run python -c "
import tempfile, shutil
from services.report.report_store import ReportStore

tmp = tempfile.mkdtemp()
store = ReportStore(tmp)

assert store.load('proj-1') is None, 'expected None for missing project'

saved = store.save('proj-1', 'Test Title', {'type': 'doc', 'content': []}, [{'id': 'cite-1'}])
assert saved['title'] == 'Test Title'
assert saved['content'] == {'type': 'doc', 'content': []}
assert 'updated_at' in saved

loaded = store.load('proj-1')
assert loaded == saved, 'load() should return exactly what save() wrote'

shutil.rmtree(tmp)
print('OK')
"
```

Expected: 印出 `OK`，沒有 `AssertionError` 或例外。

- [ ] **Step 4: Commit**

```bash
git add backend/services/report/__init__.py backend/services/report/report_store.py
git commit -m "feat: add ReportStore for persisting edited paper reports"
```

---

## Task 2: 後端 — report_bp 路由與註冊

**Files:**
- Create: `backend/routes/report.py`
- Modify: `backend/apps/__init__.py:26-38`

**Interfaces:**
- Consumes: `get_report_store()`、`ReportStore.save`/`.load`（Task 1，`backend.services.report.report_store`）。
- Produces: `POST /api/report/<project_id>`、`GET /api/report/<project_id>`。Task 5（`frontend/src/api/report.ts`）是消費者。

- [ ] **Step 1: 建立 `backend/routes/report.py`**

```python
"""論文編輯內容儲存 API"""

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__)


@report_bp.route("/<project_id>", methods=["POST"])
def save_report(project_id: str):
    """儲存論文編輯內容

    JSON body:
        - title    : 論文標題（必填）
        - content  : Tiptap JSON 文件內容（必填）
        - citations: 參考文獻清單（選填，預設空陣列）
    """
    from services.report.report_store import get_report_store

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    title = data.get("title")
    content = data.get("content")
    citations = data.get("citations", [])

    if not title or content is None:
        return jsonify({"success": False, "error": "title 和 content 為必填欄位"}), 400

    store = get_report_store()

    try:
        result = store.save(project_id, title, content, citations)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("儲存論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route("/<project_id>", methods=["GET"])
def get_report(project_id: str):
    """讀取論文編輯內容，查無資料回 404"""
    from services.report.report_store import get_report_store

    store = get_report_store()

    try:
        result = store.load(project_id)
        if result is None:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("讀取論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: 註冊 blueprint**

Modify `backend/apps/__init__.py`:

Old:
```python
    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

New:
```python
    from routes.health import health_bp
    from routes.rag import rag_bp
    from routes.report import report_bp
    from routes.stt import stt_bp
    from routes.gemini import gemini_bp
    from routes.mineru import mineru_bp
    from routes.model import model_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(rag_bp, url_prefix="/api/rag")
    app.register_blueprint(report_bp, url_prefix="/api/report")
    app.register_blueprint(stt_bp, url_prefix="/api/stt")
    app.register_blueprint(gemini_bp, url_prefix="/api/gemini")
    app.register_blueprint(mineru_bp, url_prefix="/api/mineru")
    app.register_blueprint(model_bp, url_prefix="/api/models")
```

- [ ] **Step 3: 啟動後端、用 curl 驗證兩個端點**

Run（背景啟動 server）：

```bash
cd backend
uv run python app.py &
sleep 2
```

驗證「查無資料回 404」：

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5001/api/report/plan-test-project
```
Expected: `404`

驗證「儲存」：

```bash
curl -s -X POST http://127.0.0.1:5001/api/report/plan-test-project \
  -H "Content-Type: application/json" \
  -d '{"title":"測試論文","content":{"type":"doc","content":[]},"citations":[]}'
```
Expected: JSON 內含 `"success":true` 與 `"result":{"title":"測試論文",...,"updated_at":"..."}`

驗證「讀取」：

```bash
curl -s http://127.0.0.1:5001/api/report/plan-test-project
```
Expected: `"success":true`，`result.title` 為 `"測試論文"`

清理測試檔案並關閉 server：

```bash
rm -f backend/artifacts/paper_reports/plan-test-project.json
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/report.py backend/apps/__init__.py
git commit -m "feat: add report_bp for saving/loading edited paper reports"
```

---

## Task 3: 前端 — 安裝 Tiptap 依賴

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: `@tiptap/core`、`@tiptap/vue-3`、`@tiptap/pm`、`@tiptap/starter-kit`、`@tiptap/extension-underline`、`@tiptap/extension-text-align`、`@tiptap/extension-table`、`@tiptap/extension-table-row`、`@tiptap/extension-table-header`、`@tiptap/extension-table-cell` 套件可供 import。Task 4、6 直接依賴這些套件。

- [ ] **Step 1: 安裝套件**

```bash
cd frontend
npm install @tiptap/core @tiptap/vue-3 @tiptap/pm @tiptap/starter-kit @tiptap/extension-underline @tiptap/extension-text-align @tiptap/extension-table @tiptap/extension-table-row @tiptap/extension-table-header @tiptap/extension-table-cell
```

Expected: `package.json` 的 `dependencies` 多出上述套件，`npm install` 無錯誤退出。

- [ ] **Step 2: 型別檢查（確認既有程式碼沒有因為新依賴而壞掉）**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出（跟安裝前的 baseline 一致，因為目前還沒有任何檔案 import 這些套件）。

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add Tiptap dependencies for paper editor"
```

---

## Task 4: 前端 — Citation Tiptap mark extension

**Files:**
- Create: `frontend/src/components/paper/citationMark.ts`

**Interfaces:**
- Produces: `CitationMark`（Tiptap `Mark` extension，`export const CitationMark`），`configure({ citationIndex: Record<string, number> })`，屬性 `citationId: string`，渲染出的 DOM 帶 `data-citation-id` 與 `data-citation-number`。Task 6（`PaperEditor.vue`）與 Task 7（`paperTransform.ts` 產生的 Tiptap JSON 節點用 `marks: [{ type: 'citation', attrs: { citationId } }]`）都依賴這個 mark 的 `name: 'citation'` 與 `citationId` attribute 名稱。

- [ ] **Step 1: 建立 `frontend/src/components/paper/citationMark.ts`**

```ts
import { Mark, mergeAttributes } from '@tiptap/core'

export interface CitationMarkOptions {
  citationIndex: Record<string, number>
}

export const CitationMark = Mark.create<CitationMarkOptions>({
  name: 'citation',

  addOptions () {
    return {
      citationIndex: {},
    }
  },

  addAttributes () {
    return {
      citationId: {
        default: null,
        parseHTML: element => element.getAttribute('data-citation-id'),
        renderHTML: attributes => {
          if (!attributes.citationId) return {}
          return { 'data-citation-id': attributes.citationId }
        },
      },
    }
  },

  parseHTML () {
    return [{ tag: 'span[data-citation-id]' }]
  },

  renderHTML ({ HTMLAttributes }) {
    const citationId = HTMLAttributes['data-citation-id'] as string | undefined
    const number = citationId ? this.options.citationIndex[citationId] : undefined

    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        class: 'citation-mark',
        'data-citation-number': number ?? '',
      }),
      0,
    ]
  },
})
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。這個檔案目前還沒有任何地方 import，所以只是確認它本身型別正確。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/citationMark.ts
git commit -m "feat: add Citation Tiptap mark for tracking citation attribution through edits"
```

---

## Task 5: 前端 — `api/report.ts`

**Files:**
- Create: `frontend/src/api/report.ts`

**Interfaces:**
- Consumes: `Citation` type（`@/constants/reportData`，目前欄位不變：`id/title/authors/journal/year/snippet`）。
- Produces: `saveReport(projectId: string, payload: { title: string, content: JSONContent, citations: Citation[] }): Promise<SavedReport>`、`getReport(projectId: string): Promise<SavedReport | null>`、`export interface SavedReport { title: string, content: JSONContent, citations: Citation[], updated_at: string }`。Task 7（`PaperPage.vue`）是消費者。

- [ ] **Step 1: 建立 `frontend/src/api/report.ts`**

```ts
import type { JSONContent } from '@tiptap/core'
import type { Citation } from '@/constants/reportData'

export interface SavedReport {
  title: string
  content: JSONContent
  citations: Citation[]
  updated_at: string
}

export async function saveReport (
  projectId: string,
  payload: { title: string, content: JSONContent, citations: Citation[] },
): Promise<SavedReport> {
  const response = await fetch(`/api/report/${encodeURIComponent(projectId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as SavedReport
}

export async function getReport (projectId: string): Promise<SavedReport | null> {
  const response = await fetch(`/api/report/${encodeURIComponent(projectId)}`)

  if (response.status === 404) return null

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as SavedReport
}
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 3: 手動驗證（打真的後端，需要 Task 2 已完成、後端在跑）**

```bash
cd backend && uv run python app.py &
sleep 2
cd frontend && node -e "
fetch('http://127.0.0.1:5001/api/report/api-ts-check', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title: 'node fetch check', content: { type: 'doc', content: [] }, citations: [] }),
})
  .then(r => r.json())
  .then(json => { console.log(json); process.exit(json.success ? 0 : 1) })
"
rm -f backend/artifacts/paper_reports/api-ts-check.json
kill %1
```

Expected: 印出 `{ success: true, result: { title: 'node fetch check', ... } }`，exit code 0。

（這一步只是確認 `saveReport`/`getReport` 打的 URL 路徑與後端 route 對得上；真正在瀏覽器裡透過 `PaperPage.vue` 呼叫的完整驗證留到 Task 7。）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/report.ts
git commit -m "feat: add saveReport/getReport API client for paper report persistence"
```

---

## Task 6: 前端 — `PaperEditor.vue` 元件

**Files:**
- Create: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: `CitationMark`（Task 4，`@/components/paper/citationMark`）、`Citation` type（`@/constants/reportData`，不變）。
- Produces: Props `{ modelValue: JSONContent, editable: boolean, citations: Citation[] }`；Emits `update:modelValue(content: JSONContent)`、`citation-click(citationId: string)`；`defineExpose({ getDom: () => HTMLElement | null })`。Task 7（`PaperPage.vue`）用 `v-model="report.content"`、`:editable`、`:citations`、`@citation-click`，並透過 `ref` 呼叫 `getDom()`。

此元件這一步先不接進任何頁面，所以本步驟先用型別檢查驗證，完整瀏覽器手動驗證留到 Task 7（那時候才會被 `PaperPage.vue` 掛載並實際渲染內容）。

- [ ] **Step 1: 建立 `frontend/src/components/paper/PaperEditor.vue`**

```vue
<template>
  <div class="paper-editor">
    <div v-if="editable" class="editor-toolbar">
      <v-btn
        icon="mdi-format-bold"
        size="small"
        :variant="editor?.isActive('bold') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleBold().run()"
      />
      <v-btn
        icon="mdi-format-italic"
        size="small"
        :variant="editor?.isActive('italic') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleItalic().run()"
      />
      <v-btn
        icon="mdi-format-underline"
        size="small"
        :variant="editor?.isActive('underline') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleUnderline().run()"
      />
      <v-btn
        icon="mdi-format-strikethrough"
        size="small"
        :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleStrike().run()"
      />
      <span class="toolbar-divider" />
      <v-btn
        icon="mdi-format-header-1"
        size="small"
        :variant="editor?.isActive('heading', { level: 1 }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
      />
      <v-btn
        icon="mdi-format-header-2"
        size="small"
        :variant="editor?.isActive('heading', { level: 2 }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
      />
      <v-btn
        icon="mdi-format-header-3"
        size="small"
        :variant="editor?.isActive('heading', { level: 3 }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
      />
      <span class="toolbar-divider" />
      <v-btn
        icon="mdi-format-list-bulleted"
        size="small"
        :variant="editor?.isActive('bulletList') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleBulletList().run()"
      />
      <v-btn
        icon="mdi-format-list-numbered"
        size="small"
        :variant="editor?.isActive('orderedList') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleOrderedList().run()"
      />
      <v-btn
        icon="mdi-format-quote-close"
        size="small"
        :variant="editor?.isActive('blockquote') ? 'tonal' : 'text'"
        @click="editor?.chain().focus().toggleBlockquote().run()"
      />
      <span class="toolbar-divider" />
      <v-btn
        icon="mdi-format-align-left"
        size="small"
        :variant="editor?.isActive({ textAlign: 'left' }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().setTextAlign('left').run()"
      />
      <v-btn
        icon="mdi-format-align-center"
        size="small"
        :variant="editor?.isActive({ textAlign: 'center' }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().setTextAlign('center').run()"
      />
      <v-btn
        icon="mdi-format-align-right"
        size="small"
        :variant="editor?.isActive({ textAlign: 'right' }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().setTextAlign('right').run()"
      />
      <v-btn
        icon="mdi-format-align-justify"
        size="small"
        :variant="editor?.isActive({ textAlign: 'justify' }) ? 'tonal' : 'text'"
        @click="editor?.chain().focus().setTextAlign('justify').run()"
      />
      <span class="toolbar-divider" />
      <v-btn
        icon="mdi-table-plus"
        size="small"
        variant="text"
        @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
      />
      <span class="toolbar-divider" />
      <v-btn icon="mdi-undo" size="small" variant="text" @click="editor?.chain().focus().undo().run()" />
      <v-btn icon="mdi-redo" size="small" variant="text" @click="editor?.chain().focus().redo().run()" />
    </div>

    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />
  </div>
</template>

<script setup lang="ts">
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { Underline } from '@tiptap/extension-underline'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { watch } from 'vue'
  import { CitationMark } from '@/components/paper/citationMark'

  const props = defineProps<{
    modelValue: JSONContent
    editable: boolean
    citations: Citation[]
  }>()

  const emit = defineEmits<{
    (e: 'update:modelValue', content: JSONContent): void
    (e: 'citation-click', citationId: string): void
  }>()

  const citationIndex: Record<string, number> = {}
  for (const [index, citation] of props.citations.entries()) {
    citationIndex[citation.id] = index + 1
  }

  const editor = useEditor({
    content: props.modelValue,
    editable: props.editable,
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      CitationMark.configure({ citationIndex }),
    ],
    editorProps: {
      handleClick: (_view, _pos, event) => {
        if (props.editable) return false
        const target = (event.target as HTMLElement).closest('[data-citation-id]')
        const citationId = target?.getAttribute('data-citation-id')
        if (citationId) {
          emit('citation-click', citationId)
          return true
        }
        return false
      },
    },
    onUpdate: ({ editor: instance }) => {
      emit('update:modelValue', instance.getJSON())
    },
  })

  watch(() => props.editable, value => {
    editor.value?.setEditable(value)
  })

  watch(() => props.modelValue, value => {
    if (!editor.value) return
    const current = JSON.stringify(editor.value.getJSON())
    if (current !== JSON.stringify(value)) {
      editor.value.commands.setContent(value, false)
    }
  })

  defineExpose({
    getDom: (): HTMLElement | null => editor.value?.view.dom ?? null,
  })
</script>

<style scoped>
  .paper-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .editor-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: #f7f8fb;
  }

  .toolbar-divider {
    width: 1px;
    height: 20px;
    margin: 0 4px;
    background: #d8dbe3;
  }

  :deep(.editor-content) {
    font-size: 13.5px;
    line-height: 1.9;
    color: #2a2f3a;
  }

  :deep(.editor-content .ProseMirror) {
    outline: none;
  }

  :deep(.editor-content h1),
  :deep(.editor-content h2),
  :deep(.editor-content h3) {
    margin: 0 0 10px;
    font-weight: 700;
    color: #1c2130;
  }

  :deep(.editor-content p) {
    margin: 0 0 12px;
    text-align: justify;
    text-indent: 2em;
  }

  :deep(.editor-content table) {
    border-collapse: collapse;
    margin: 12px 0;
  }

  :deep(.editor-content th),
  :deep(.editor-content td) {
    border: 1px solid #d8dbe3;
    padding: 6px 10px;
  }

  :deep(.citation-mark) {
    background: #fdf0a8;
    padding: 1px 2px;
    border-radius: 3px;
  }

  :deep(.citation-mark::after) {
    content: '[' attr(data-citation-number) ']';
    font-size: 0.85em;
    margin-left: 1px;
  }

  .editor-content--readonly :deep(.citation-mark) {
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .editor-content--readonly :deep(.citation-mark:hover) {
    background: #fae57e;
  }
</style>
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。若有 Tiptap extension 的型別報錯（例如 `editorProps.handleClick` 參數型別），照錯誤訊息調整參數型別標註即可，邏輯不變。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add PaperEditor Tiptap component with view/edit toolbar"
```

---

## Task 7: 前端 — 整合：資料模型改版、`paperTransform.ts`、`PaperPage.vue`、`PaperSourcesView.vue`

這是把前面幾個 task 兜起來、讓功能真正端到端可用的整合任務。因為 `PaperReport` 型別是破壞性變更（`sections` → `content`），所有消費它的檔案必須在同一個 task 內一起改完，否則中間狀態會 type-check 失敗。

**Files:**
- Modify: `frontend/src/constants/reportData.ts`（整份重寫）
- Modify: `frontend/src/utils/paperTransform.ts`（整份重寫）
- Modify: `frontend/src/views/PaperPage.vue`（整份重寫）
- Modify: `frontend/src/views/PaperSourcesView.vue:124-143`
- Delete: `frontend/src/components/paper/PaperSection.vue`

**Interfaces:**
- Consumes: `PaperEditor.vue`（Task 6）、`saveReport`/`getReport`/`SavedReport`（Task 5）、`CitationMark`（Task 4，僅 `paperTransform.ts` 用到它的 mark 型別結構，不需要 import extension 本身）。
- Produces: 新的 `PaperReport { title: string, content: JSONContent, citations: Citation[] }`，供整個 app 使用（本 task 之後不會再有消費者用到舊的 `sections`/`PaperSection`/`PaperSegment`）。

- [ ] **Step 1: 重寫 `frontend/src/constants/reportData.ts`**

```ts
import type { JSONContent } from '@tiptap/core'

export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
}

export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
}

export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citations: [
    {
      id: 'cite-1',
      title: 'Benchmarking Machine Learning Algorithms for Telecom Churn Prediction',
      authors: 'Chen, W., & Smith, J.',
      journal: 'International Journal of Data Science, 12(4)',
      year: 2023,
      snippet:
        '“...Our empirical comparison demonstrates that gradient boosting frameworks (specifically XGBoost) consistently outperform SVM. Their superiority is attributed to their robustness in handling mixed data types and modeling non-linear interactions...”',
    },
    {
      id: 'cite-2',
      title: 'Switching Costs and Customer Loyalty in Subscription-Based Markets',
      authors: 'Kumar, A., & Lee, D.',
      journal: 'Journal of Marketing Analytics, 8(2)',
      year: 2024,
      snippet:
        '“...Customers under long-term contracts exhibit significantly lower churn propensity, as contractual switching costs reinforce retention even when short-term satisfaction fluctuates...”',
    },
  ],
  content: {
    type: 'doc',
    content: [
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.1 模型效能評估 (Model Performance Evaluation)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '本研究採用分層十折交叉驗證 (Stratified 10-Fold Cross-Validation) 對三種異質模型進行了嚴謹的基準測試。實驗結果顯示,XGBoost 模型在各項關鍵指標上均優於隨機森林 (Random Forest) 與支持向量機 (SVM),其準確率 (Accuracy) 達到 94.2%,F1-Score 為 0.92。相較之下,SVM 在處理類別不平衡數據時表現較弱,Recall 僅為 0.76。這項結果與近期文獻一致,指出梯度提升決策樹 (GBDT) 演算法由於具備處理特徵間複雜非線性交互作用的能力,在結構化表格數據 (Tabular Data) 的分類任務中,通常能提供比傳統統計模型更穩健的預測能力',
            marks: [{ type: 'citation', attrs: { citationId: 'cite-1' } }],
          },
          { type: 'text', text: '。因此,本系統最終選擇 XGBoost 作為部署至生產環境的最佳模型。' },
        ],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.2 關鍵特徵影響因子分析 (Analysis of Key Determinants)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '進一步透過 SHAP (SHapley Additive exPlanations) 值解析模型的決策邏輯,我們發現「合約類型 (Contract Type)」是預測客戶流失的最顯著特徵。SHAP Summary Plot 顯示,合約期限越短,SHAP 值越高,代表流失風險越大。數據顯示,採「按月付費 (Month-to-month)」合約的客戶,其基礎流失機率比簽訂「兩年合約」的長期客戶高出 45%,這反映了合約轉換成本 (Switching Cost) 會顯著降低客戶的忠誠度',
            marks: [{ type: 'citation', attrs: { citationId: 'cite-2' } }],
          },
          { type: 'text', text: '。這表明,電信營運商應將行銷資源集中於引導月租客戶升級至年約方案,而非僅依賴價格補貼。' },
        ],
      },
      {
        type: 'heading',
        attrs: { level: 3 },
        content: [{ type: 'text', text: '4.3 服務類型與市場競爭 (Service Type and Market Competition)' }],
      },
      {
        type: 'paragraph',
        content: [
          {
            type: 'text',
            text: '除了合約結構,「光纖網路服務 (Fiber Optic)」的使用者群體也呈現出異常高的流失傾向。雖然光纖用戶通常貢獻較高的 ARPU (每用戶平均收入),但模型預測顯示其流失風險反而是 DSL 用戶的 1.5 倍。針對此現象,可能的解釋包括光纖市場競爭激烈、價格敏感度高,以及用戶對高價服務的品質期望更為嚴苛,值得後續研究進一步驗證。',
          },
        ],
      },
    ],
  },
}
```

（原本 `PaperSection`/`PaperSegment` 型別移除，不再需要——引用歸屬現在由 Tiptap 文件內的 `citation` mark 承載。）

- [ ] **Step 2: 重寫 `frontend/src/utils/paperTransform.ts`**

```ts
import type { JSONContent } from '@tiptap/core'
import type { ArxivGenerateResult } from '@/api/arxiv'
import type { Citation, PaperReport } from '@/constants/reportData'

function parseParagraphToContent (paragraphText: string): JSONContent[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const nodes: JSONContent[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const firstDigits = token.match(/\d+/)?.[0]
      if (!firstDigits) continue
      const citationId = `cite-${firstDigits}`
      const prev = nodes.at(-1)

      if (prev && prev.type === 'text' && !prev.marks) {
        // 引用標記依附在「前一句」文字上,不寫進文字內容本身
        prev.marks = [{ type: 'citation', attrs: { citationId } }]
      } else {
        // 沒有前一句可依附(例如段落一開頭就是引用標記):用零寬空白當文字節點,
        // 只是為了承載 citation mark,避免 ProseMirror 不允許空文字節點
        nodes.push({ type: 'text', text: '​', marks: [{ type: 'citation', attrs: { citationId } }] })
      }
    } else {
      nodes.push({ type: 'text', text: token })
    }
  }

  return nodes
}

function buildCitations (result: ArxivGenerateResult): Citation[] {
  return result.references
    .toSorted((a, b) => a.ref_id - b.ref_id)
    .map(ref => {
      const snippetEntry = result.citation_map
        .flatMap(entry => entry.sources)
        .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)

      return {
        id: `cite-${ref.ref_id}`,
        title: ref.title,
        authors: String(ref.author ?? ''),
        journal: String(ref.journal ?? 'arXiv'),
        year: Number(ref.year) || 0,
        snippet: snippetEntry?.relevant_chunk ?? '',
      }
    })
}

export function transformArxivResultToPaperReport (result: ArxivGenerateResult, topic: string): PaperReport {
  const blocks = result.paper_markdown.split('\n\n---\n\n')
  const docContent: JSONContent[] = []

  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ') || trimmed.startsWith('## 參考文獻')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    docContent.push({
      type: 'heading',
      attrs: { level: 3 },
      content: [{ type: 'text', text: heading }],
    })

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const paragraph of paragraphs) {
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph) })
    }
  }

  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
  }
}
```

- [ ] **Step 3: 重寫 `frontend/src/views/PaperPage.vue`**

```vue
<template>
  <section class="paper-page">
    <HubSidebar />

    <main class="paper-main">
      <header class="paper-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.back()"
        />
        <h2 class="paper-title">{{ report.title }}</h2>

        <div class="toolbar-actions">
          <v-btn
            v-if="mode === 'view'"
            :disabled="loading"
            prepend-icon="mdi-pencil"
            size="small"
            variant="text"
            @click="mode = 'edit'"
          >
            編輯
          </v-btn>
          <template v-else>
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              color="primary"
              :disabled="!projectId"
              :loading="saving"
              size="small"
              @click="save"
            >
              儲存
            </v-btn>
          </template>
        </div>
      </header>

      <p v-if="mode === 'edit' && !projectId" class="save-hint">
        此論文尚未關聯專案,無法儲存
      </p>
      <p v-if="saveError" class="save-error">{{ saveError }}</p>

      <div class="paper-body">
        <article class="paper-sheet">
          <PaperEditor
            ref="editorRef"
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            @citation-click="onCitationClick"
          />
        </article>

        <CitationPanel
          :active-citation-id="activeCitationId"
          :citations="report.citations"
          class="paper-citations"
          @select="onPanelSelect"
        />
      </div>
    </main>
  </section>
</template>

<script setup lang="ts">
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { getReport, saveReport } from '@/api/report'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'

  const route = useRoute()
  const router = useRouter()
  const paperStore = usePaperStore()

  const projectId = computed(() => route.query.project as string | undefined)

  const report = ref<PaperReport>(mockPaperReport)
  const loading = ref(true)
  const mode = ref<'view' | 'edit'>('view')
  const saving = ref(false)
  const saveError = ref<string | null>(null)
  const activeCitationId = ref<string | null>(null)
  const editorRef = ref<InstanceType<typeof PaperEditor> | null>(null)

  let savedSnapshot: PaperReport = mockPaperReport

  onMounted(async () => {
    document.title = 'DataMind'

    if (paperStore.generatedReport) {
      report.value = paperStore.generatedReport
      paperStore.clearGeneratedReport()
    } else if (projectId.value) {
      try {
        const saved = await getReport(projectId.value)
        if (saved) {
          report.value = { title: saved.title, content: saved.content, citations: saved.citations }
        }
      } catch (error) {
        saveError.value = error instanceof Error ? error.message : String(error)
      }
    }

    savedSnapshot = structuredClone(report.value)
    loading.value = false
  })

  function onCitationClick (citationId: string) {
    activeCitationId.value = citationId
  }

  function onPanelSelect (citationId: string) {
    activeCitationId.value = citationId
    editorRef.value
      ?.getDom()
      ?.querySelector(`[data-citation-id="${CSS.escape(citationId)}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
  }

  async function save () {
    if (!projectId.value) return
    saving.value = true
    saveError.value = null
    try {
      const result = await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
      })
      report.value = { title: result.title, content: result.content, citations: result.citations }
      savedSnapshot = structuredClone(report.value)
      mode.value = 'view'
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    } finally {
      saving.value = false
    }
  }
</script>

<style scoped>
  .paper-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background:
      radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
      linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: hidden;
  }

  .paper-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .paper-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }

  .save-hint {
    margin: 8px 2px 0;
    font-size: 12px;
    color: #b45309;
  }

  .save-error {
    margin: 8px 2px 0;
    font-size: 12px;
    color: #dc2626;
  }

  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 16px;
    margin-top: 14px;
    overflow: auto;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    max-width: 760px;
    margin: 0 auto;
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 28px 34px;
    height: fit-content;
  }

  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
  }

  @media (max-width: 1100px) {
    .paper-body {
      flex-direction: column;
    }

    .paper-citations {
      width: 100%;
      position: static;
      max-height: none;
      overflow-y: visible;
    }
  }
</style>
```

- [ ] **Step 4: `PaperSourcesView.vue` 導頁時帶上 `project` query**

Modify `frontend/src/views/PaperSourcesView.vue`:

Old:
```ts
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push('/paper')
```

New:
```ts
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
```

- [ ] **Step 5: 刪除 `PaperSection.vue`**

```bash
rm frontend/src/components/paper/PaperSection.vue
```

- [ ] **Step 6: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。這一步會抓到任何殘留引用舊 `PaperSection`/`sections`/`PaperSegment` 的地方。

- [ ] **Step 7: 手動端到端驗證**

```bash
cd backend && uv run python app.py &
cd frontend && npm run dev &
```

瀏覽器開 `http://localhost:3000`：

1. 走 `/results` → 選文獻 → 生成論文 → 確認導到 `/paper?project=<id>`（網址列可見 `project` query），畫面是檢視模式，引用文字有黃色高亮，點擊能在右側面板高亮對應文獻並捲動聚焦
2. 點「編輯」→ 確認出現工具列；測試粗體、H1-H3、清單、引言、四種對齊、插入表格、復原/重做；確認引用文字仍看得到（含 `[n]` 編號），但點擊沒有反應（不會觸發右側面板）
3. 在引用文字「中間」打幾個字，確認新打的字視覺上跟引用文字一起被標記背景（表示 mark 有正確繼承）
4. 點「儲存」→ 確認：a) 按鈕顯示 loading 後恢復、b) 自動切回檢視模式、c) `backend/artifacts/paper_reports/<project_id>.json` 檔案存在且內容正確（用 `cat` 確認）
5. 重新整理頁面（保留 `?project=<id>`）→ 確認能讀回剛存的內容，且回到檢視模式時引用點擊互動又能正常運作(因為 mark 資訊有正確存回並讀回)
6. 進入編輯模式後點「取消」→ 確認變更被捨棄、回到編輯前的內容
7. 直接開 `http://localhost:3000/paper`（不帶 `project` query）→ 確認顯示 mock 論文、點「編輯」後「儲存」按鈕是灰色不可點、上方有提示文字

驗證完關閉背景 process：

```bash
kill %1 %2
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/constants/reportData.ts frontend/src/utils/paperTransform.ts frontend/src/views/PaperPage.vue frontend/src/views/PaperSourcesView.vue
git rm frontend/src/components/paper/PaperSection.vue
git commit -m "feat: make generated papers Word-like editable with backend persistence"
```

---

## Self-Review Notes

- **Spec coverage**：spec（`docs/superpowers/specs/2026-07-25-paper-editor-design.md`）的五個「做」項目——(1) 可編輯模式含完整工具列 → Task 6；(2) 檢視/編輯雙模式切換、檢視模式保留引用互動 → Task 7 Step 3；(3) 引用歸屬用 Tiptap mark 保存 → Task 4 + Task 7 Step 2；(4) 後端 JSON 持久化 → Task 1、2；(5) `PaperSourcesView.vue` 帶 `project` query → Task 7 Step 4。「不做」清單（多人協作、匯出檔案、引用清單編輯、自動存檔、帳號權限）都沒有出現在任何 task 裡。Mark 的 `inclusive` 行為（spec 補充的澄清）是 Tiptap 預設值，沒有額外程式碼要寫，Task 7 Step 7 的手動驗證第 3 點會實際確認這個行為。
- **型別一致性**：`PaperReport { title, content: JSONContent, citations: Citation[] }` 在 Task 7 Step 1 定義，Task 7 Step 2（`paperTransform.ts`）與 Step 3（`PaperPage.vue`）原樣使用；`Citation` 型別全程沒變。`CitationMark` 的 `name: 'citation'` 與 `citationId` attribute 名稱，在 Task 4 定義、Task 7 Step 2 手動組出的 `marks: [{ type: 'citation', attrs: { citationId } }]` 結構一致。`PaperEditor` 的 props（`modelValue`/`editable`/`citations`）、emits（`update:modelValue`/`citation-click`）、`defineExpose({ getDom })` 在 Task 6 定義，Task 7 Step 3 的 `v-model`/`:editable`/`:citations`/`@citation-click`/`editorRef.value?.getDom()` 用法一致。`saveReport`/`getReport`/`SavedReport` 在 Task 5 定義，Task 7 Step 3 原樣使用。
- **無佔位符**：所有 step 都是完整可執行的程式碼或指令，沒有「之後補」「視情況處理」這類字眼。
