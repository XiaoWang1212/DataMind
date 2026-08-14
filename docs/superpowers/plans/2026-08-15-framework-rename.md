# 編輯框架名稱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可以在框架庫（`FrameworkLibraryView.vue`）的詳情面板裡編輯框架名稱（`title` 欄位），目前建立後完全無法修改。

**Architecture:** 後端在 `backend/routes/framework.py` 新增 `GET /api/frameworks/<id>` 與 `PATCH /api/frameworks/<id>`，PATCH 採「選擇性欄位更新」設計（比照 `backend/routes/project.py` 的 `update_project`），目前只處理 `title`，owner 檢查與錯誤格式沿用既有慣例。前端新增 `updateFramework` API 函式與 `frameworkStore.renameFramework`（樂觀更新 + 失敗回滾，比照 `projectStore.saveColumnMapping`）。UI 只在詳情面板標題旁加一個編輯圖示，點擊後標題變成輸入框，Enter/失焦儲存、Esc 取消；儲存前先做前端空值檢查，失敗時（空值或 API 錯誤）顯示錯誤文字並保留編輯狀態。左側卡片列表不可編輯，但因為與詳情面板共用同一份 store 資料，儲存成功後會自動同步顯示新名稱。

**Tech Stack:** Flask + SQLAlchemy（後端）、Vue 3 `<script setup>` + TypeScript + Pinia（前端）、無 CSS framework。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-15-framework-rename-design.md`
- 不新增資料庫欄位或 migration：`Framework.title`（`backend/models/framework.py:15`）已存在，直接沿用
- 只在框架庫詳情面板（`.detail-panel`）加編輯功能，左側卡片列表（`.fw-title`）維持唯讀
- 後端 `PATCH /api/frameworks/<id>` 是選擇性欄位更新設計，目前只實作 `title`，但介面本身要能直接延伸支援未來新增欄位（比照 `update_project` 的寫法）
- 這個專案的路由層 pytest 測試一律不碰真實資料庫（`test_field_mapping_routes.py`、`test_auth_routes.py` 開頭註解都明講這件事）；會實際寫入/查詢 `frameworks`/`users` 表的行為，改用手動驗證腳本（`backend/scripts/test_*.py`）對開發用資料庫驗證，跟 `backend/scripts/test_auth_google_and_reset.py` 走一樣的模式
- 前端沒有 vitest，一律用 `npm run type-check` + 人工瀏覽器驗證
- 每個 task 完成後都要跑對應的型別檢查/驗證腳本，確認沒有問題才能進下一步

---

### Task 1: 後端 — 新增 GET/PATCH `/api/frameworks/<id>`

**Files:**
- Modify: `backend/routes/framework.py`（在檔案末尾新增兩個路由）
- Create: `backend/scripts/test_framework_rename.py`（手動驗證腳本，需要可連線的開發用資料庫）

**Interfaces:**
- Consumes: `models.framework.Framework`、`_serialize_framework()`（`backend/routes/framework.py:12-26`，既有函式，直接複用）
- Produces: `GET /api/frameworks/<int:framework_id>` → 200 `{"success": true, "result": FrameworkDTO}` 或 404；`PATCH /api/frameworks/<int:framework_id>`，body 可帶 `{"title": string}`，成功回 200 `{"success": true, "result": FrameworkDTO}`，`title` 為空/純空白回 400，找不到或非本人框架回 404。Task 2 的前端 `updateFramework()` 會呼叫這個 PATCH endpoint。

- [ ] **Step 1: 在 `backend/routes/framework.py` 檔案末尾新增兩個路由**

找到檔案結尾（第 66-67 行，`create_framework` 函式結束的地方）：

```python
    db.session.add(framework)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
```

在它後面新增：

```python


@framework_bp.route("/<int:framework_id>", methods=["GET"])
@login_required
def get_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404

    return jsonify({"success": True, "result": _serialize_framework(framework)})


@framework_bp.route("/<int:framework_id>", methods=["PATCH"])
@login_required
def update_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return jsonify({"success": False, "error": "title 不可為空"}), 400
        framework.title = title

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
```

- [ ] **Step 2: 建立手動驗證腳本**

`backend/scripts/test_framework_rename.py`：

```python
"""手動驗證腳本：GET/PATCH /api/frameworks/<id>（需要可連線的開發用資料庫）

用法（在 backend/ 目錄下執行）：
    uv run python scripts/test_framework_rename.py

涵蓋：
  1. 已登入使用者建立框架後，PATCH title 可以成功改名，GET 讀回同一個值
  2. PATCH title 為空字串/純空白 → 回 400，資料庫裡的 title 不變
  3. 用另一個使用者的 client 對別人的框架 GET/PATCH → 回 404
  4. PATCH 不存在的 framework id → 回 404

執行後會清除腳本建立的測試帳號與框架，不會在資料庫留下垃圾資料。
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from apps import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models.framework import Framework  # noqa: E402
from models.user import User  # noqa: E402

OWNER_EMAIL = "framework-rename-owner@example.com"
OTHER_EMAIL = "framework-rename-other@example.com"
PASSWORD = "TestPass123"


def cleanup(app):
    with app.app_context():
        users = User.query.filter(User.email.in_([OWNER_EMAIL, OTHER_EMAIL])).all()
        user_ids = [u.id for u in users]
        if user_ids:
            Framework.query.filter(Framework.user_id.in_(user_ids)).delete(synchronize_session=False)
        User.query.filter(User.email.in_([OWNER_EMAIL, OTHER_EMAIL])).delete(synchronize_session=False)
        db.session.commit()


def _register(client, email):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "displayName": "Test User"},
    )
    assert response.get_json()["success"] is True, response.get_json()


def test_patch_updates_title(owner_client):
    create_response = owner_client.post("/api/frameworks", json={"title": "原始標題"})
    framework_id = create_response.get_json()["result"]["id"]

    response = owner_client.patch(f"/api/frameworks/{framework_id}", json={"title": "新標題"})
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["success"] is True
    assert body["result"]["title"] == "新標題"

    get_response = owner_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.get_json()["result"]["title"] == "新標題"

    print("[PASS] PATCH title 成功改名，GET 讀回同一個值")
    return framework_id


def test_patch_rejects_empty_title(owner_client, framework_id):
    response = owner_client.patch(f"/api/frameworks/{framework_id}", json={"title": "   "})
    assert response.status_code == 400
    assert response.get_json()["success"] is False

    get_response = owner_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.get_json()["result"]["title"] == "新標題", "空白 title 不該真的寫進資料庫"

    print("[PASS] PATCH 空白 title 回 400，資料庫裡的值不變")


def test_patch_and_get_reject_other_users_framework(owner_client, other_client, framework_id):
    patch_response = other_client.patch(f"/api/frameworks/{framework_id}", json={"title": "搶別人的框架"})
    assert patch_response.status_code == 404

    get_response = other_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.status_code == 404

    print("[PASS] 非本人操作別人的框架，GET/PATCH 都回 404")


def test_patch_nonexistent_framework_returns_404(owner_client):
    response = owner_client.patch("/api/frameworks/999999999", json={"title": "不存在"})
    assert response.status_code == 404
    print("[PASS] PATCH 不存在的框架 id 回 404")


def main():
    app = create_app()
    app.config["TESTING"] = True
    owner_client = app.test_client()
    other_client = app.test_client()

    cleanup(app)
    try:
        _register(owner_client, OWNER_EMAIL)
        _register(other_client, OTHER_EMAIL)

        framework_id = test_patch_updates_title(owner_client)
        test_patch_rejects_empty_title(owner_client, framework_id)
        test_patch_and_get_reject_other_users_framework(owner_client, other_client, framework_id)
        test_patch_nonexistent_framework_returns_404(owner_client)
        print("\n全部通過")
    finally:
        cleanup(app)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 執行腳本**

Run（在 `backend/` 目錄下，需要 `.env` 裡的 `DATABASE_URL` 能連到開發用資料庫）: `uv run python scripts/test_framework_rename.py`
Expected: 依序印出四行 `[PASS] ...`，最後印出 `全部通過`，沒有 Traceback

- [ ] **Step 4: Commit**

```bash
git add backend/routes/framework.py backend/scripts/test_framework_rename.py
git commit -m "feat: add GET/PATCH endpoints for framework by id"
```

---

### Task 2: 前端 — API client + store action

**Files:**
- Modify: `frontend/src/api/framework.ts`（檔案末尾新增 `UpdateFrameworkPatch` 型別與 `updateFramework` 函式）
- Modify: `frontend/src/store/frameworkStore.ts`

**Interfaces:**
- Consumes: `PATCH /api/frameworks/<id>`（Task 1 產生）
- Produces: `updateFramework(id: number, patch: UpdateFrameworkPatch): Promise<FrameworkDTO>`（`api/framework.ts`）；`frameworkStore.renameFramework(id: number, title: string): Promise<void>` — Task 3 的 UI 會呼叫這個 store action

- [ ] **Step 1: 在 `frontend/src/api/framework.ts` 檔案末尾新增型別與函式**

找到檔案結尾（第 43-52 行，`createFramework` 函式）：

```ts
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

在它後面新增：

```ts

export interface UpdateFrameworkPatch {
  title?: string
}

export async function updateFramework (id: number, patch: UpdateFrameworkPatch): Promise<FrameworkDTO> {
  const response = await fetch(`/api/frameworks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO
}
```

- [ ] **Step 2: 修改 `frontend/src/store/frameworkStore.ts`**

把（第 1-3 行的 import）：

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createFramework, type CreateFrameworkPayload, listFrameworks } from '@/api/framework'
```

改成：

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createFramework, type CreateFrameworkPayload, listFrameworks, updateFramework } from '@/api/framework'
```

把（第 31-38 行）：

```ts
  async function addFramework (fw: CreateFrameworkPayload): Promise<Framework> {
    const created = await createFramework(fw)
    frameworks.value = [created, ...frameworks.value]
    return created
  }

  return { frameworks, loadFrameworks, addFramework }
})
```

改成：

```ts
  async function addFramework (fw: CreateFrameworkPayload): Promise<Framework> {
    const created = await createFramework(fw)
    frameworks.value = [created, ...frameworks.value]
    return created
  }

  async function renameFramework (id: number, title: string): Promise<void> {
    const target = frameworks.value.find(f => f.id === id)
    const previousTitle = target?.title
    if (target) {
      target.title = title
    }
    try {
      await updateFramework(id, { title })
    } catch (error) {
      if (target && previousTitle !== undefined) {
        target.title = previousTitle
      }
      console.error('更新框架名稱失敗', error)
      throw error
    }
  }

  return { frameworks, loadFrameworks, addFramework, renameFramework }
})
```

- [ ] **Step 3: 型別檢查**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/framework.ts frontend/src/store/frameworkStore.ts
git commit -m "feat: add updateFramework API client and renameFramework store action"
```

---

### Task 3: 前端 — 詳情面板編輯 UI

**Files:**
- Modify: `frontend/src/views/hub/FrameworkLibraryView.vue:66-74`（`panel-header` template）
- Modify: `frontend/src/views/hub/FrameworkLibraryView.vue:159-179`（`<script setup>`）
- Modify: `frontend/src/views/hub/FrameworkLibraryView.vue:405-416`（style，`.panel-title`/`.panel-tag` 附近）

**Interfaces:**
- Consumes: `frameworkStore.renameFramework(id, title)`（Task 2 產生）
- Produces: 無（UI 端末端行為，之後沒有其他 task 依賴它）

- [ ] **Step 1: `panel-header` template 加上編輯圖示與輸入框**

找到（第 66-74 行）：

```html
      <!-- Panel header -->
      <div class="panel-header">
        <div class="panel-header-info">
          <div class="panel-title">{{ selectedFramework.title }}</div>
          <div class="panel-tag">{{ selectedFramework.tag }}</div>
        </div>
        <button class="panel-close" @click="selectedId = null">
          <v-icon icon="mdi-close" size="18" />
        </button>
      </div>
```

改成：

```html
      <!-- Panel header -->
      <div class="panel-header">
        <div class="panel-header-info">
          <div v-if="!isEditingTitle" class="panel-title-row">
            <div class="panel-title">{{ selectedFramework.title }}</div>
            <button class="panel-title-edit-btn" title="編輯名稱" @click="startEditingTitle">
              <v-icon icon="mdi-pencil-outline" size="14" />
            </button>
          </div>
          <div v-else class="panel-title-edit-wrap">
            <input
              ref="titleInputRef"
              v-model="titleDraft"
              class="panel-title-input"
              @blur="commitTitleEdit"
              @keydown="handleTitleKeydown"
            >
            <div v-if="titleError" class="panel-title-error">{{ titleError }}</div>
          </div>
          <div class="panel-tag">{{ selectedFramework.tag }}</div>
        </div>
        <button class="panel-close" @click="selectedId = null">
          <v-icon icon="mdi-close" size="18" />
        </button>
      </div>
```

- [ ] **Step 2: `<script setup>` 加上編輯狀態與方法**

找到（第 159-179 行，整個 `<script setup>` 區塊）：

```ts
<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useFrameworkStore } from '@/store/frameworkStore'

const store = useFrameworkStore()
const searchQuery = ref('')
const selectedId = ref<number | null>(null)

const filteredFrameworks = computed(() => {
  if (!searchQuery.value) return store.frameworks
  const q = searchQuery.value.toLowerCase()
  return store.frameworks.filter(
    f => f.title.toLowerCase().includes(q) || f.tag.toLowerCase().includes(q),
  )
})

const selectedFramework = computed(() =>
  selectedId.value === null ? null : store.frameworks.find(f => f.id === selectedId.value) ?? null,
)
</script>
```

改成：

```ts
<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useFrameworkStore } from '@/store/frameworkStore'

const store = useFrameworkStore()
const searchQuery = ref('')
const selectedId = ref<number | null>(null)

const filteredFrameworks = computed(() => {
  if (!searchQuery.value) return store.frameworks
  const q = searchQuery.value.toLowerCase()
  return store.frameworks.filter(
    f => f.title.toLowerCase().includes(q) || f.tag.toLowerCase().includes(q),
  )
})

const selectedFramework = computed(() =>
  selectedId.value === null ? null : store.frameworks.find(f => f.id === selectedId.value) ?? null,
)

const isEditingTitle = ref(false)
const titleDraft = ref('')
const titleError = ref<string | null>(null)
const titleInputRef = ref<HTMLInputElement | null>(null)

watch(selectedId, () => {
  isEditingTitle.value = false
  titleError.value = null
})

function startEditingTitle () {
  if (!selectedFramework.value) return
  titleDraft.value = selectedFramework.value.title
  titleError.value = null
  isEditingTitle.value = true
  nextTick(() => {
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  })
}

function cancelEditingTitle () {
  isEditingTitle.value = false
  titleError.value = null
}

async function commitTitleEdit () {
  if (!isEditingTitle.value || !selectedFramework.value) return

  const trimmed = titleDraft.value.trim()
  if (trimmed === selectedFramework.value.title) {
    isEditingTitle.value = false
    titleError.value = null
    return
  }
  if (!trimmed) {
    titleError.value = '名稱不可為空'
    return
  }

  const frameworkId = selectedFramework.value.id
  try {
    await store.renameFramework(frameworkId, trimmed)
    isEditingTitle.value = false
    titleError.value = null
  } catch (error) {
    console.error('更新框架名稱失敗', error)
    titleError.value = '儲存失敗，請重試'
  }
}

function handleTitleKeydown (event: KeyboardEvent) {
  if (event.key === 'Enter') {
    event.preventDefault()
    commitTitleEdit()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    cancelEditingTitle()
  }
}
</script>
```

- [ ] **Step 3: 新增編輯相關樣式**

找到（第 405-416 行）：

```css
.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-ink);
  line-height: 1.3;
}

.panel-tag {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-top: 3px;
}
```

改成：

```css
.panel-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-ink);
  line-height: 1.3;
}

.panel-title-edit-btn {
  width: 22px;
  height: 22px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  flex-shrink: 0;
  transition: background 0.12s;
}

.panel-title-edit-btn:hover {
  background: #f5f5f5;
}

.panel-title-edit-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.panel-title-input {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-ink);
  line-height: 1.3;
  border: none;
  border-bottom: 1.5px solid var(--color-accent);
  outline: none;
  padding: 0 0 2px;
  width: 100%;
  font-family: inherit;
}

.panel-title-error {
  font-size: 12px;
  color: #dc2626;
}

.panel-tag {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-top: 3px;
}
```

- [ ] **Step 4: 型別檢查**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 5: 人工瀏覽器驗證**

開發模式啟動前端（若尚未啟動：`cd frontend && npm run dev`），登入後走到框架庫頁面（`/hub/library`），點一張框架卡片打開詳情面板。

Expected：
- 標題旁邊看得到鉛筆編輯圖示，點擊後標題變成輸入框並自動 focus、選取全部文字
- 修改文字後按 Enter → 儲存成功，退出編輯狀態，詳情面板與左側卡片列表的標題同步顯示新名稱
- 再次點編輯圖示、修改文字後直接點輸入框外面（失焦）→ 行為跟 Enter 一致，儲存成功
- 點編輯圖示、修改文字後按 Esc → 標題還原成編輯前的原始值，不送出 API 請求（可用瀏覽器 Network 面板確認沒有新的 PATCH 請求）
- 點編輯圖示、把文字整個清空後按 Enter → 輸入框下方出現「名稱不可為空」錯誤文字，輸入框仍保持在編輯狀態
- 點編輯圖示、修改文字，開發者工具切到 Network 面板選 Offline 模擬離線，按 Enter → 顯示「儲存失敗，請重試」，輸入框保留剛才輸入的內容；恢復連線後再按一次 Enter，確認可以正常儲存成功
- 選取別的框架卡片時，若前一個框架還停在編輯狀態，切換後應自動回到唯讀顯示（不殘留另一個框架的編輯狀態）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/hub/FrameworkLibraryView.vue
git commit -m "feat: allow editing framework name in the detail panel"
```
