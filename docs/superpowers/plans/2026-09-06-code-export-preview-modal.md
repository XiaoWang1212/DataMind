# 程式碼匯出預覽彈窗 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「匯出程式碼」按鈕從「一按就直接下載」改成「先跳出一個像 Discord 檔案預覽的彈窗，顯示語法高亮的 Python 程式碼，使用者確認/複製/改檔名之後才真的下載」。

**Architecture:** 新增一個獨立的 `CodeExportPreviewModal.vue` 元件（backdrop + card 樣式，沿用 `JournalScoreDialog.vue` 的既有慣例），內部用 `highlight.js` 做 Python 語法高亮。`WorkflowWorkspace.vue` 的 `handleExportCode()` 從「呼叫 API → 組 Blob → 觸發下載」改成「呼叫 API → 存資料 → 打開彈窗」，下載/複製動作整段移進新元件。完全不動後端。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript；新增 `highlight.js`（只用 `highlight.js/lib/core` + 註冊 `python` 語言，不用完整版）。

## Global Constraints

- 完全不動後端（`code_export_service.py`／`/workflow/export-code` 路由）——這次純前端改動
- 不新增共用 Modal/Dialog 元件——沿用專案「每個彈窗各自複製 backdrop+card CSS」的既有慣例
- 語法高亮固定深色主題，跟頁面本身的亮/暗模式無關
- 彈窗打開時重置檔名輸入框為後端回傳的預設檔名，不殘留上次編輯的值
- 下載檔名：空白時退回預設檔名；沒有 `.py` 副檔名時自動補上
- 型別檢查在 `datamind-frontend` container 內執行（`docker exec datamind-frontend sh -c "cd /app && npm run type-check"`），host 上因為缺 `@tiptap/*` 套件會有 53 個既有的、跟這次改動無關的錯誤
- 直接在 `main` branch 上工作，不開額外 git worktree
- `npm install` 也在 container 內執行，確保跟 container 內既有的 `node_modules` 版本相容

---

### Task 1: `CodeExportPreviewModal.vue` 元件本身

**Files:**
- Create: `frontend/src/components/workflow/CodeExportPreviewModal.vue`
- Modify: `frontend/package.json`（新增 `highlight.js` 依賴）

**Interfaces:**
- Produces: `CodeExportPreviewModal.vue` 元件，Props `{ visible: boolean, code: string, defaultFilename: string }`，Emits `close: []`

- [ ] **Step 1: 安裝 `highlight.js`**

在 container 內安裝（確保跟 container 內既有的 `node_modules` 版本相容）：
```bash
docker exec -w /app datamind-frontend npm install highlight.js
```
Expected: 指令成功結束，`frontend/package.json` 的 `dependencies` 區塊（第 17 行附近，跟其他套件一樣依字母順序排列）多一行 `"highlight.js": "^版本號"`。

- [ ] **Step 2: 確認安裝結果**

Run: `docker exec -w /app datamind-frontend npm ls highlight.js`
Expected: 印出 `highlight.js@<version>`，沒有 `UNMET DEPENDENCY` 之類的錯誤。

- [ ] **Step 3: 建立元件檔案**

建立 `frontend/src/components/workflow/CodeExportPreviewModal.vue`：
```vue
<template>
  <div
    v-if="visible"
    class="code-preview-backdrop"
    @click.self="emit('close')"
  >
    <div class="code-preview-card">
      <header class="code-preview-header">
        <input
          v-model="filename"
          class="code-preview-filename-input"
          spellcheck="false"
          type="text"
        >
        <div class="code-preview-actions">
          <AppButton variant="ghost" @click="handleCopy">
            <v-icon :icon="copied ? 'mdi-check' : 'mdi-content-copy'" size="15" />
            {{ copied ? '已複製' : '複製' }}
          </AppButton>
          <AppButton variant="primary" @click="handleDownload">
            <v-icon icon="mdi-download" size="15" />
            下載
          </AppButton>
          <AppButton icon-only title="關閉" variant="ghost" @click="emit('close')">
            <v-icon icon="mdi-close" size="16" />
          </AppButton>
        </div>
      </header>

      <pre class="code-preview-body"><code class="language-python" v-html="highlightedCode" /></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
  import hljs from 'highlight.js/lib/core'
  import python from 'highlight.js/lib/languages/python'
  import 'highlight.js/styles/atom-one-dark.css'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'

  hljs.registerLanguage('python', python)

  const props = defineProps<{
    visible: boolean
    code: string
    defaultFilename: string
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const filename = ref(props.defaultFilename)
  const copied = ref(false)

  // highlight.js 直接對純文字做語法高亮、輸出 HTML 字串，比操作 DOM 節點（highlightElement）
  // 更適合搭配 Vue 的響應式渲染——code 換了 computed 會自動重新算，不用自己在 watch 裡手動觸發
  const highlightedCode = computed(() => hljs.highlight(props.code, { language: 'python' }).value)

  // 每次重新打開彈窗都重置檔名輸入框，避免上次編輯的殘留值蓋過新產生的預設檔名
  watch(() => props.visible, visible => {
    if (visible) {
      filename.value = props.defaultFilename
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  }, { immediate: true })

  function onKeydown (event: KeyboardEvent): void {
    if (event.key === 'Escape') emit('close')
  }

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown)
  })

  async function handleCopy (): Promise<void> {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }

  function resolveFilename (): string {
    const trimmed = filename.value.trim()
    if (!trimmed) return props.defaultFilename
    return trimmed.toLowerCase().endsWith('.py') ? trimmed : `${trimmed}.py`
  }

  function handleDownload (): void {
    const blob = new Blob([props.code], { type: 'text/x-python' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = resolveFilename()
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
</script>

<style scoped>
  .code-preview-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(18, 30, 58, 0.45);
    z-index: 1000;
  }

  .code-preview-card {
    display: flex;
    width: 780px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    flex-direction: column;
    overflow: hidden;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
  }

  .code-preview-header {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid var(--color-border);
  }

  .code-preview-filename-input {
    flex: 1;
    min-width: 0;
    padding: 5px 8px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    outline: none;
    background: transparent;
    color: var(--color-text);
    font-family: var(--font-heading);
    font-size: 15px;
    font-weight: 500;
    transition: background-color var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out);
  }

  .code-preview-filename-input:hover {
    background: color-mix(in oklab, var(--color-ink) 6%, white);
  }

  .code-preview-filename-input:focus {
    border-color: var(--color-border-strong);
    background: var(--color-surface);
  }

  .code-preview-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 6px;
  }

  .code-preview-body {
    flex: 1;
    margin: 0;
    overflow: auto;
    padding: 16px 20px;
    background: #282c34;
    font-family: var(--font-mono, 'SF Mono', Consolas, monospace);
    font-size: 13px;
    line-height: 1.6;
  }
</style>
```

- [ ] **Step 4: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 既有的 53 個 `@tiptap/*` 相關錯誤維持不變（這是 host 環境缺套件的已知問題，跟這次改動無關），新建立的 `CodeExportPreviewModal.vue` 沒有新增任何 `error TS`。用 `npm run type-check 2>&1 | grep -i "CodeExportPreviewModal"` 確認沒有輸出。

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/package.json frontend/package-lock.json frontend/src/components/workflow/CodeExportPreviewModal.vue
git commit -m "feat: add code export preview modal component"
```

---

### Task 2: 整合進 `WorkflowWorkspace.vue`

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: `CodeExportPreviewModal.vue`（Task 1 產出），Props `{ visible, code, defaultFilename }`，Emits `close`
- Consumes: 既有的 `exportWorkflowCode(payload): Promise<{ code: string, filename: string }>`（`frontend/src/api/workflow.ts:81-96`，這次不用改）

- [ ] **Step 1: 新增元件 import**

`frontend/src/components/workflow/WorkflowWorkspace.vue` 第 165-169 行附近，現有的相對路徑 import 區塊：
```typescript
  import IconNode from './IconNode.vue'
  import InterruptConfirmDialog from './InterruptConfirmDialog.vue'
  import UploadDialog from './UploadDialog.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'
```
改成（依字母順序插入 `CodeExportPreviewModal`）：
```typescript
  import CodeExportPreviewModal from './CodeExportPreviewModal.vue'
  import IconNode from './IconNode.vue'
  import InterruptConfirmDialog from './InterruptConfirmDialog.vue'
  import UploadDialog from './UploadDialog.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'
```

- [ ] **Step 2: 加入彈窗到 template**

第 34-39 行附近，現有的 `<UploadDialog>`：
```html
    <!-- 上傳 model 檔案 dialog -->
    <UploadDialog
      :visible="uploadDialogVisible"
      @close="uploadDialogVisible = false"
      @confirm="confirmUpload"
    />
```
之後新增：
```html
    <CodeExportPreviewModal
      :code="exportedCode"
      :default-filename="exportedFilename"
      :visible="codePreviewVisible"
      @close="codePreviewVisible = false"
    />
```

- [ ] **Step 3: 改寫 `handleExportCode()`**

第 393-413 行附近，現有的：
```typescript
  const exportingCode = ref(false)

  async function handleExportCode (): Promise<void> {
    exportingCode.value = true
    try {
      const payload = buildWorkflowPayload()
      const { code, filename } = await exportWorkflowCode(payload)

      const blob = new Blob([code], { type: 'text/x-python' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      workflowError.value = error instanceof Error ? error.message : String(error)
    } finally {
      exportingCode.value = false
    }
  }
```
改成：
```typescript
  const exportingCode = ref(false)
  const codePreviewVisible = ref(false)
  const exportedCode = ref('')
  const exportedFilename = ref('workflow_export.py')

  async function handleExportCode (): Promise<void> {
    exportingCode.value = true
    try {
      const payload = buildWorkflowPayload()
      const { code, filename } = await exportWorkflowCode(payload)
      exportedCode.value = code
      exportedFilename.value = filename
      codePreviewVisible.value = true
    } catch (error) {
      workflowError.value = error instanceof Error ? error.message : String(error)
    } finally {
      exportingCode.value = false
    }
  }
```
（組 `Blob`／觸發下載那段程式碼已經整段搬進 `CodeExportPreviewModal.vue` 的 `handleDownload()`，這裡不再直接碰 DOM 下載邏輯。`workflowError` 已經是這個檔案既有的 ref，不用額外宣告。）

- [ ] **Step 4: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`

Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "WorkflowWorkspace"` 沒有輸出（沒有新增錯誤）。

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: open code preview modal instead of downloading directly"
```

---

## 完成後的人工驗證

兩個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（前端/後端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 開一個有模型設定的 workflow，按「匯出程式碼」，確認跳出預覽彈窗、程式碼內容正確且有語法高亮（關鍵字、字串、註解要有不同顏色，背景是深色）
2. 按「複製」，貼到別處（例如記事本）確認內容跟彈窗裡顯示的一致，按鈕文字短暫變成「已複製」、2 秒後恢復
3. 修改檔名輸入框（例如改成 `my_test`），按「下載」，確認下載出來的檔案叫 `my_test.py`
4. 清空檔名輸入框，按「下載」，確認退回 `workflow_export.py`
5. 按右上角 X 或點擊背景遮罩或按 Esc，確認彈窗關閉且不影響畫布其他操作
6. 沒有選任何模型時按「匯出程式碼」，確認顯示錯誤訊息、彈窗不會打開
7. 重新按一次「匯出程式碼」（在上次彈窗已經關閉之後），確認檔名輸入框重置回預設值，不會殘留上次手動修改過的檔名
