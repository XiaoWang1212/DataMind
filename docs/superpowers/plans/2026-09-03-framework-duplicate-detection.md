# 框架重複偵測 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用者選擇 PDF 的當下就判斷這份論文是否已在框架庫中，命中即提示，避免花一次 Gemini token 提取出重複的框架。

**Architecture:** 判定依據是 PDF 內容的 SHA-256，在瀏覽器用 Web Crypto 計算，因此不必先上傳檔案。hash 存進 `frameworks.pdf_hash`（新欄位）。比對分兩層：hash 命中即確定同一份檔案；沒命中再比檔名，用來涵蓋沒有 hash 的舊框架與同一篇論文的不同檔案。只提示，不阻擋儲存。

**Tech Stack:** Flask + SQLAlchemy + Alembic（後端）、Vue 3 `<script setup>` + TypeScript（前端）、Web Crypto API、PostgreSQL、Docker Compose。

**Spec:** `docs/superpowers/specs/2026-09-03-framework-duplicate-detection-design.md`

## Global Constraints

- **專案沒有自動化測試框架。** `backend/scripts/test_*.sh` 是手動 curl 煙霧測試。本計畫的驗證步驟一律是可實際執行的指令（python 直接載入模組、curl、`vue-tsc`、`eslint`、psql）或明確的手動操作，不要新增 pytest/vitest。
- **全部服務跑在 Docker。** 後端 `docker compose exec backend …`，資料庫 `docker exec datamind-postgres psql -U datamind -d datamind …`。後端掛載原始碼且 `FLASK_DEBUG=true`，改 Python 檔會自動 reload，不需要重啟容器。
- 目前的 alembic head 是 `4b1d1134b860`。
- 提示框樣式沿用 `ExtractFrameworkView.vue` 已存在的 `.notice`（次級底 `--color-surface-alt`、hairline `--color-border`、文字 `--color-ink-soft`、`--radius-sm`、圖示 `mdi-information-outline`），**不要**改用 warning 的琥珀。

## 起始狀態

工作區已有一批未 commit 的變更，是上一版「方法論指紋」設計的產物。本計畫會把它們改造成 hash 版，不是從乾淨的狀態開始：

| 檔案 | 現況 | 本計畫要做的事 |
|---|---|---|
| `backend/services/framework_signature.py` | 未追蹤的新檔，含 `build_signature()`、`extract_sections()`、`normalize_title()` | Task 2 刪除，`normalize_title()` 搬到新檔 |
| `backend/routes/framework.py` | 已加 `check-duplicate`，查 title 或 workflowJson | Task 2 改寫成查 pdfHash 或 title |
| `frontend/src/api/framework.ts` | 已加 `checkDuplicateByTitle()`、`checkDuplicateByWorkflow()` | Task 3 合併成單一 `checkFrameworkDuplicate()` |
| `frontend/src/views/hub/ExtractFrameworkView.vue` | 按「開始提取」時查檔名；提取後查方法論；已有 `.notice` 樣式 | Task 4 改成選檔時查 hash+檔名，移除提取後那次查詢 |

---

### Task 1: `frameworks.pdf_hash` 欄位與 migration

**Files:**
- Modify: `backend/models/framework.py`
- Create: `backend/migrations/versions/c3f1a7d2e9b4_add_pdf_hash_to_frameworks.py`

**Interfaces:**
- Consumes: 無（第一個 task）
- Produces: `Framework.pdf_hash`（`Mapped[str | None]`，`String(64)`，nullable，有索引）。Task 2 讀寫這個欄位。

- [ ] **Step 1: 在 model 加欄位**

改 `backend/models/framework.py`，在 `workflow_json` 那行之後、`created_at` 之前插入：

```python
    # 上傳的 PDF 內容 SHA-256（小寫十六進位）。本次改動之前建立的框架沒有這個值，
    # 且無法回填——原始 PDF 沒有留存
    pdf_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
```

`String` 已在檔案頂端的 `from sqlalchemy import ...` 匯入，不需要改 import。

- [ ] **Step 2: 寫 migration**

建立 `backend/migrations/versions/c3f1a7d2e9b4_add_pdf_hash_to_frameworks.py`：

```python
"""add pdf_hash to frameworks

Revision ID: c3f1a7d2e9b4
Revises: 4b1d1134b860
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3f1a7d2e9b4'
down_revision: Union[str, Sequence[str], None] = '4b1d1134b860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('frameworks', sa.Column('pdf_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_frameworks_pdf_hash', 'frameworks', ['pdf_hash'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_frameworks_pdf_hash', table_name='frameworks')
    op.drop_column('frameworks', 'pdf_hash')
```

- [ ] **Step 3: 套用 migration**

Run: `docker compose exec backend uv run alembic upgrade head`
Expected: 輸出含 `Running upgrade 4b1d1134b860 -> c3f1a7d2e9b4`，無 traceback。

- [ ] **Step 4: 確認欄位與索引真的建好了**

Run:
```bash
docker exec datamind-postgres psql -U datamind -d datamind -c "\d frameworks" | grep -i pdf_hash
```
Expected: 兩行——一行是 `pdf_hash | character varying(64) |`，一行是索引 `"ix_frameworks_pdf_hash" btree (pdf_hash)`。

- [ ] **Step 5: 確認 downgrade 可回滾，再升回來**

Run:
```bash
docker compose exec backend uv run alembic downgrade -1
docker exec datamind-postgres psql -U datamind -d datamind -c "\d frameworks" | grep -c pdf_hash
docker compose exec backend uv run alembic upgrade head
```
Expected: 中間那行輸出 `0`（欄位已移除），最後一行重新升級成功。這一步是為了確認 downgrade 沒寫錯——只寫不跑的 downgrade 常常是壞的。

- [ ] **Step 6: 檢視本 task 的變更**

Run: `git status --short && git diff backend/models/framework.py`
確認只動到 `models/framework.py` 與新的 migration 檔，沒有夾帶其他改動。

---

### Task 2: 後端比對邏輯

**Files:**
- Create: `backend/services/framework_dedupe.py`
- Delete: `backend/services/framework_signature.py`
- Modify: `backend/routes/framework.py`

**Interfaces:**
- Consumes: `Framework.pdf_hash`（Task 1）
- Produces:
  - `normalize_title(value) -> str`
  - `normalize_hash(value) -> str`
  - `POST /api/frameworks/check-duplicate`，body `{"pdfHash"?: str, "title"?: str}`，回 `{"success": true, "result": {"id": int, "title": str, "matchType": "hash" | "title"} | null}`。Task 3 呼叫這支。
  - `POST /api/frameworks` 多接受 `pdfHash` 欄位。Task 4 會送這個值。

- [ ] **Step 1: 寫 `framework_dedupe.py`**

建立 `backend/services/framework_dedupe.py`：

```python
"""框架重複比對用的正規化工具

判定依據是 PDF 內容的 SHA-256；hash 比不到時退而比檔名。
兩種比對都要先把值收斂成同一種寫法再比。
"""

import re

_NOISE = re.compile(r"[\s_\-]+")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def normalize_title(value) -> str:
    """正規化標題或檔名，讓大小寫與空白/底線的差異不影響比對"""
    return _NOISE.sub("", str(value or "").strip().lower())


def normalize_hash(value) -> str:
    """正規化 SHA-256；格式不符時回傳空字串，呼叫端應視為沒有 hash

    長度與字元檢查是為了讓壞掉的輸入落成空字串，而不是拿垃圾值去比對——
    否則兩筆同樣壞掉的值會被判成重複。
    """
    normalized = str(value or "").strip().lower()
    return normalized if _HEX_64.match(normalized) else ""
```

- [ ] **Step 2: 驗證兩個正規化函式**

Run:
```bash
cd backend && python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('fd', 'services/framework_dedupe.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print('title 收斂:', m.normalize_title('IJMI published ') == m.normalize_title('IJMI_published'))
print('title None:', repr(m.normalize_title(None)))
good = 'a' * 64
print('hash 大寫收斂:', m.normalize_hash(good.upper()) == good)
print('hash 太短:', repr(m.normalize_hash('abc')))
print('hash 非十六進位:', repr(m.normalize_hash('z' * 64)))
print('hash None:', repr(m.normalize_hash(None)))
"
```
Expected:
```
title 收斂: True
title None: ''
hash 大寫收斂: True
hash 太短: ''
hash 非十六進位: ''
hash None: ''
```

（用 `importlib` 直接載入檔案是因為 `services/__init__.py` 會連帶匯入 sklearn 等重相依，本機 python 沒裝。）

- [ ] **Step 3: 刪除舊的方法論指紋模組**

Run: `rm backend/services/framework_signature.py`

這個檔案從未 commit，直接刪除即可。它的 `normalize_title()` 已搬進 `framework_dedupe.py`。

- [ ] **Step 4: 改寫 `routes/framework.py` 的比對區塊**

把 import 那行換成：

```python
from services.framework_dedupe import normalize_hash, normalize_title
```

把現有的 `_match`、`_match_by_title`、`_match_by_workflow`、`check_duplicate` 四段（`_user_frameworks()` 保留不動）整段換成：

```python
def _match(framework: Framework, match_type: str) -> dict:
    return {"id": framework.id, "title": framework.title, "matchType": match_type}


def _match_by_hash(pdf_hash: str) -> dict | None:
    """比對 PDF 內容。舊框架沒有 hash，跳過那些筆"""
    for framework in _user_frameworks():
        if framework.pdf_hash and normalize_hash(framework.pdf_hash) == pdf_hash:
            return _match(framework, "hash")
    return None


def _match_by_title(title: str) -> dict | None:
    """比對檔名。paper_title 不受框架改名影響，所以兩個欄位都比"""
    for framework in _user_frameworks():
        if title in {normalize_title(framework.title), normalize_title(framework.paper_title)}:
            return _match(framework, "title")
    return None


@framework_bp.route("/check-duplicate", methods=["POST"])
@login_required
def check_duplicate():
    """找出框架庫中同一份 PDF 或同名的框架

    hash 相同代表確定是同一份檔案；hash 比不到才比檔名，用來涵蓋沒有 hash 的
    舊框架，以及同一篇論文的不同檔案。沒有命中時 result 為 null。
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    pdf_hash = normalize_hash(data.get("pdfHash"))
    if pdf_hash:
        match = _match_by_hash(pdf_hash)
        if match:
            return jsonify({"success": True, "result": match})

    title = normalize_title(data.get("title"))
    if title:
        return jsonify({"success": True, "result": _match_by_title(title)})

    return jsonify({"success": True, "result": None})
```

- [ ] **Step 5: 建立框架時存下 hash**

在 `create_framework()` 的 `Framework(...)` 建構中，`workflow_json=data.get("workflowJson"),` 之後加一行：

```python
        pdf_hash=normalize_hash(data.get("pdfHash")) or None,
```

`or None` 是為了讓格式不符或未提供時存成 NULL 而不是空字串——空字串會被 `_match_by_hash` 的 `framework.pdf_hash` 真值判斷擋掉，但存 NULL 語意才對。

`_serialize_framework()` **不要**加 `pdf_hash`，前端沒有任何地方需要它。

- [ ] **Step 6: 確認語法正確且後端有 reload**

Run:
```bash
cd backend && python3 -m py_compile routes/framework.py services/framework_dedupe.py && echo COMPILE_OK
sleep 3 && docker logs datamind-backend --tail 5
```
Expected: 印出 `COMPILE_OK`；容器 log 沒有 traceback 或 `ImportError`。

- [ ] **Step 7: 確認端點存在**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:5001/api/frameworks/check-duplicate \
  -H "Content-Type: application/json" -d '{"title":"x"}'
```
Expected: `401`（未登入）。**不可以**是 `404`（路由沒註冊）或 `500`（程式壞了）。

- [ ] **Step 8: 用資料庫直接驗證比對邏輯**

Run:
```bash
docker exec datamind-postgres psql -U datamind -d datamind -tAc \
  "update frameworks set pdf_hash = repeat('a', 64) where id = (select min(id) from frameworks) returning id, pdf_hash;"
```
記下回傳的 id。稍後 Task 5 的手動驗證會用真實檔案覆蓋，這裡只是先確認欄位可寫入。

Expected: 回傳一行 `<id>|aaaa…`（64 個 a）。

- [ ] **Step 9: 檢視本 task 的變更**

Run: `git status --short`
確認：新增 `framework_dedupe.py`、刪除 `framework_signature.py`、`routes/framework.py` 改為 hash→檔名兩層比對。

---

### Task 3: 前端 hash 計算與 API 層

**Files:**
- Create: `frontend/src/utils/pdfHash.ts`
- Modify: `frontend/src/api/framework.ts`

**Interfaces:**
- Consumes: Task 2 的 `POST /api/frameworks/check-duplicate`
- Produces:
  - `computePdfHash(file: File): Promise<string | null>`
  - `checkFrameworkDuplicate(params: { pdfHash?: string | null, title?: string }): Promise<DuplicateFramework | null>`
  - `DuplicateFramework { id: number, title: string, matchType: 'hash' | 'title' }`
  - `CreateFrameworkPayload` 多一個 `pdfHash?: string | null`

  Task 4 會用到以上全部。

- [ ] **Step 1: 寫 `pdfHash.ts`**

建立 `frontend/src/utils/pdfHash.ts`：

```typescript
// 用 PDF 內容而不是檔名判斷重複：同一份檔案必定相同，不同檔案必定不同。
// 在瀏覽器算完就能比對，不必先把檔案上傳到後端
export async function computePdfHash (file: File): Promise<string | null> {
  // crypto.subtle 只在安全情境下存在（https 或 localhost）。用區網 IP 以 http
  // 開發時會沒有，此時回傳 null 讓呼叫端退回只比檔名
  if (!globalThis.crypto?.subtle) return null

  const buffer = await file.arrayBuffer()
  const digest = await globalThis.crypto.subtle.digest('SHA-256', buffer)
  return [...new Uint8Array(digest)]
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
}
```

- [ ] **Step 2: 改寫 `api/framework.ts` 的重複比對區塊**

把檔案末端從 `export type DuplicateMatchType` 開始到檔尾的整段（現有的 `checkDuplicateByTitle`、`checkDuplicateByWorkflow`、`postDuplicateCheck`）換成：

```typescript
export type DuplicateMatchType = 'hash' | 'title'

export interface DuplicateFramework {
  id: number
  title: string
  matchType: DuplicateMatchType
}

export async function checkFrameworkDuplicate (
  params: { pdfHash?: string | null, title?: string },
): Promise<DuplicateFramework | null> {
  const response = await fetch('/api/frameworks/check-duplicate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ pdfHash: params.pdfHash ?? undefined, title: params.title }),
  })
  const result = await parseFrameworkResponse(response)
  return (result.result as DuplicateFramework | null) ?? null
}
```

- [ ] **Step 3: 讓建立框架能帶 hash**

在同一個檔案的 `CreateFrameworkPayload` 介面中，`workflowJson?: Record<string, unknown>` 之後加一行：

```typescript
  pdfHash?: string | null
```

`FrameworkDTO` 不要加——後端不回傳這個欄位。

- [ ] **Step 4: 型別檢查與 lint**

Run:
```bash
cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json && npx eslint src/utils/pdfHash.ts src/api/framework.ts && echo CHECKS_OK
```
Expected: 印出 `CHECKS_OK`。

此時 `ExtractFrameworkView.vue` 仍在呼叫已被刪除的 `checkDuplicateByTitle`/`checkDuplicateByWorkflow`，`vue-tsc` 會報錯。**這是預期的**——Task 4 會修好。若只想先確認本 task 的兩個檔案，可先跳過 `vue-tsc`、只跑 `eslint`，並在 Task 4 結束時補跑完整型別檢查。

- [ ] **Step 5: 檢視本 task 的變更**

Run: `git status --short`
確認：新增 `utils/pdfHash.ts`，`api/framework.ts` 的比對 API 合併為單一入口。

---

### Task 4: 提取頁接線

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue`

**Interfaces:**
- Consumes: `computePdfHash()`、`checkFrameworkDuplicate()`、`DuplicateFramework`、`CreateFrameworkPayload.pdfHash`（Task 3）
- Produces: 無（最終消費端）

- [ ] **Step 1: 換掉 import**

把現有的

```typescript
  import {
    checkDuplicateByTitle,
    checkDuplicateByWorkflow,
    type DuplicateFramework,
  } from '@/api/framework'
```

換成

```typescript
  import { checkFrameworkDuplicate, type DuplicateFramework } from '@/api/framework'
```

並在 `import { useFrameworkStore } from '@/store/frameworkStore'` 之後加：

```typescript
  import { computePdfHash } from '@/utils/pdfHash'
```

（import 排序照 eslint 的規則，`@/utils/...` 排在 `@/store/...` 之後。）

- [ ] **Step 2: 收斂 state**

把現有的三個 ref

```typescript
  const duplicateFramework = ref<DuplicateFramework | null>(null)
  const titleDuplicate = ref<DuplicateFramework | null>(null)
  const checkingTitle = ref(false)
```

換成

```typescript
  const duplicateFramework = ref<DuplicateFramework | null>(null)
  const pdfHash = ref<string | null>(null)
  const checkingDuplicate = ref(false)
```

- [ ] **Step 3: 選檔時算 hash 並比對**

把現有的 `onFileChange` 換成：

```typescript
  function onFileChange (file: File | null): void {
    // 移除檔案時要一併中止進行中的提取，維持原本 removeFile 的行為
    if (!file && extracting.value) abortController?.abort()
    selectedFile.value = file
    duplicateFramework.value = null
    pdfHash.value = null
    if (file) void checkDuplicate(file)
  }

  // 選檔當下就判定，讓使用者在按下提取之前就知道這份論文已經在框架庫裡
  async function checkDuplicate (file: File): Promise<void> {
    checkingDuplicate.value = true
    try {
      pdfHash.value = await computePdfHash(file)
      const hit = await checkFrameworkDuplicate({
        pdfHash: pdfHash.value,
        title: file.name.replace(/\.[^.]+$/, ''),
      })
      // 使用者可能在等待期間換掉或移除檔案，過期的結果不要蓋上去
      if (selectedFile.value === file) duplicateFramework.value = hit
    } catch (error) {
      // 重複只是提示，算不出來或查不到就當作沒有重複，不影響提取
      console.error('比對重複框架失敗', error)
    } finally {
      checkingDuplicate.value = false
    }
  }
```

- [ ] **Step 4: 改寫提取進入點**

把現有的 `extractAnyway()` 與 `startExtract()` 兩個函式整段刪除，並把 `runExtract` 改回 `startExtract`：

```typescript
  // 看過提示後仍要提取，清掉提示直接送出
  function extractAnyway (): void {
    duplicateFramework.value = null
    void startExtract()
  }
```

然後把函式宣告 `async function runExtract (): Promise<void> {` 改回 `async function startExtract (): Promise<void> {`。

- [ ] **Step 5: 移除提取完成後的第二次比對**

在 `startExtract()` 中，把 `await streamAnalyzeWorkflowFromPdf(...)` 之後的這一段整個刪除：

```typescript
      if (rawWorkflowJson.value) {
        // 重複只是提示，查詢失敗就當作沒有重複，不影響提取結果
        try {
          duplicateFramework.value = await checkDuplicateByWorkflow(rawWorkflowJson.value)
        } catch (error) {
          console.error('比對重複框架失敗', error)
        }
      }
```

同時把 `startExtract()` 開頭重置區塊裡的 `duplicateFramework.value = null` 刪掉——提示現在由選檔決定，不該因為開始提取就消失。

- [ ] **Step 6: 儲存時帶上 hash**

在 `saveFramework()` 的 `store.addFramework({...})` 呼叫中，`workflowJson: rawWorkflowJson.value ?? undefined,` 之後加一行：

```typescript
      pdfHash: pdfHash.value,
```

並在該函式結尾的重置區塊中，把

```typescript
    duplicateFramework.value = null
    titleDuplicate.value = null
    selectedFile.value = null
```

換成

```typescript
    duplicateFramework.value = null
    pdfHash.value = null
    selectedFile.value = null
```

- [ ] **Step 7: 更新提示文字與按鈕狀態**

把上傳面板中現有的 `titleDuplicate` 提示區塊與「開始提取」按鈕換成：

```vue
        <div v-if="duplicateFramework" class="notice notice--action">
          <v-icon class="notice-icon" icon="mdi-information-outline" size="16" />
          <span class="notice-text">{{ duplicateMessage }}</span>
          <AppButton class="notice-btn" variant="secondary" @click="extractAnyway">
            仍要提取
          </AppButton>
        </div>
        <AppButton
          v-else-if="selectedFile && !extracting"
          class="extract-btn"
          :loading="checkingDuplicate"
          :variant="extractedData ? 'secondary' : 'primary'"
          @click="startExtract"
        >
          {{ extractedData ? '重新提取' : '開始提取' }}
        </AppButton>
```

把結果面板中現有的那個 `.notice`（提取完成後顯示的那個）整段刪除。

在 script 中加入文案的 computed（放在 `duplicateFramework` 宣告之後）：

```typescript
  const duplicateMessage = computed(() => {
    const hit = duplicateFramework.value
    if (!hit) return ''
    return hit.matchType === 'hash'
      ? `這份檔案已經提取過，框架庫中的《${hit.title}》`
      : `框架庫已有同名的《${hit.title}》`
  })
```

並把 `import { ref } from 'vue'` 改回 `import { computed, ref } from 'vue'`。

- [ ] **Step 8: 型別檢查與 lint**

Run:
```bash
cd frontend && npx vue-tsc --noEmit -p tsconfig.app.json && npx eslint src/views/hub/ExtractFrameworkView.vue && echo CHECKS_OK
```
Expected: 印出 `CHECKS_OK`，且不再有 `checkDuplicateByTitle` / `checkDuplicateByWorkflow` 相關錯誤。

- [ ] **Step 9: 確認沒有殘留的舊識別字**

Run:
```bash
cd frontend && grep -rn "titleDuplicate\|checkingTitle\|runExtract\|checkDuplicateBy" src/ || echo NO_LEFTOVERS
```
Expected: 印出 `NO_LEFTOVERS`。

- [ ] **Step 10: 檢視本 task 的變更**

Run: `git status --short`
確認：提取頁改為選檔即比對，移除提取後的第二次查詢。

---

### Task 5: 端到端驗證

**Files:** 無（只驗證）

**Interfaces:**
- Consumes: Task 1–4 的全部成果
- Produces: 一份給使用者的驗證結果

- [ ] **Step 1: 清掉 Task 2 塞進去的假 hash**

Run:
```bash
docker exec datamind-postgres psql -U datamind -d datamind -tAc \
  "update frameworks set pdf_hash = null where pdf_hash = repeat('a', 64) returning id;"
```
Expected: 回傳先前那一筆的 id（或無輸出，若當時沒改到）。

- [ ] **Step 2: 手動走一次「全新論文」**

在瀏覽器開 `http://localhost:5173`，登入後進「框架庫 → 上傳論文」，選一份**框架庫裡沒有的** PDF。

Expected: 不出現任何提示，「開始提取」按鈕正常顯示。按下去能正常提取並儲存。

- [ ] **Step 3: 確認 hash 有寫進資料庫**

Run:
```bash
docker exec datamind-postgres psql -U datamind -d datamind -tAc \
  "select id, title, pdf_hash from frameworks order by id desc limit 1;"
```
Expected: 最新那筆的 `pdf_hash` 是 64 字元的十六進位字串，不是空的。

- [ ] **Step 4: 手動走一次「同一份檔案」**

回到提取頁，選**剛剛那份一模一樣的 PDF**。

Expected: 選檔後隨即出現提示「這份檔案已經提取過，框架庫中的《…》」，且 backend log 中**沒有**新的 `POST /api/gemini/ai-analyze/stream`（用 `docker logs datamind-backend --tail 20` 確認）——這是省 token 的關鍵，一定要確認。

- [ ] **Step 5: 手動走一次「改了檔名的同一篇論文」**

把那份 PDF 複製一份並改成不同檔名，重新選它。

Expected: 仍出現 hash 提示（內容沒變，hash 就沒變），文字是「這份檔案已經提取過…」。

- [ ] **Step 6: 手動驗證檔名那一層**

挑一個 `pdf_hash` 為 null 的舊框架（`select id, title from frameworks where pdf_hash is null limit 1;`），把任意一份 PDF 改成跟它一樣的檔名後選取。

Expected: 出現「框架庫已有同名的《…》」。這證明沒有 hash 的舊資料仍能被第二層抓到。

- [ ] **Step 7: 確認「仍要提取」可用**

在上一步的提示狀態下按「仍要提取」。

Expected: 提示消失、開始提取、能正常儲存，新框架的 `pdf_hash` 有值。

- [ ] **Step 8: 回報驗證結果**

把上述每一步的實際結果（成功或失敗）逐項列出，附上 `git status --short`。

---

## 自我檢查

**Spec 覆蓋率**

| Spec 要求 | 對應 |
|---|---|
| 前端算 SHA-256、提取前比對 | Task 3 Step 1、Task 4 Step 3 |
| `pdf_hash` 欄位與 migration | Task 1 |
| hash → 檔名兩層查 | Task 2 Step 4 |
| 儲存時寫入 hash | Task 2 Step 5、Task 4 Step 6 |
| 移除方法論指紋 | Task 2 Step 3、Task 4 Step 5 |
| 不阻擋儲存、只提示 | Task 4 Step 7（「仍要提取」保留） |
| 不給跳轉連結 | Task 4 Step 7 的提示只有文字與按鈕 |
| `crypto.subtle` 不可用時退回檔名 | Task 3 Step 1 的 null 分支 |
| 比對失敗不影響提取 | Task 4 Step 3 的 catch |
| `_serialize_framework` 不回傳 hash | Task 2 Step 5 |
| 錯誤處理表各列 | Task 2 Step 4/5（後端）、Task 4 Step 3（前端） |
| 手動驗證項目 | Task 5 |

**型別一致性**：`DuplicateFramework.matchType` 在 Task 2（後端回傳 `"hash"`/`"title"`）、Task 3（TS 型別 `'hash' | 'title'`）、Task 4（`duplicateMessage` 判斷 `'hash'`）三處一致。`computePdfHash` 回傳 `string | null`，`checkFrameworkDuplicate` 的 `pdfHash` 參數接受 `string | null | undefined`，`CreateFrameworkPayload.pdfHash` 為 `string | null`，皆相容。

**已知的暫時性錯誤**：Task 3 結束時 `vue-tsc` 會因為 `ExtractFrameworkView.vue` 仍引用舊 API 而失敗，Task 4 Step 8 修復。這在 Task 3 Step 4 有明講。
