# 程式碼匯出預覽彈窗 Design Spec

## 背景

`WorkflowWorkspace.vue` 的「匯出程式碼」按鈕（`2026-09-05-workflow-code-export` 這個 plan 剛完成）目前的行為是：呼叫 `POST /api/models/workflow/export-code` 拿到 `{ code, filename }` 後，直接包成 `Blob` 用隱藏的 `<a download>` 觸發瀏覽器下載——使用者完全看不到程式碼內容，也沒辦法在下載前檢查或修改檔名。

使用者要求：按下「匯出程式碼」之後，先跳出一個類似 Discord 檔案預覽的彈窗，把產生的 Python 程式碼用語法高亮顯示出來，使用者確認內容之後，再從彈窗裡按「下載」才真的存檔；順便要能在下載前修改檔名。

後端 `generate_workflow_script()`／`POST /api/models/workflow/export-code` 已經完成且經過完整測試，這次改動**完全不動後端**，純粹是前端把「產生程式碼」跟「下載檔案」這兩個動作拆開，中間插入一個預覽步驟。

## 範圍

- 前端新增一個程式碼預覽彈窗元件
- 前端新增 `highlight.js` npm 依賴（目前專案沒有任何語法高亮或 Markdown 渲染套件）
- `WorkflowWorkspace.vue` 的 `handleExportCode()` 改成「呼叫 API → 開彈窗」，下載/複製動作移到彈窗內
- 檔名可在彈窗內編輯，下載時使用編輯後的檔名
- **不**動後端 `code_export_service.py`／`/workflow/export-code` 路由——這兩個已經穩定且測試完整
- **不**做通用的 Modal/Dialog 抽象元件重構——沿用現有「每個功能自己複製 backdrop+card 樣式」的慣例（`ConfirmDialog.vue`／`JournalScoreDialog.vue` 都是這樣做），不新增共用元件

## 元件與資料流

### 1. 新增 `frontend/src/components/workflow/CodeExportPreviewModal.vue`

**Props：**
```typescript
visible: boolean
code: string
defaultFilename: string  // 後端回傳的 filename，例如 "workflow_export.py"
```

**Emits：**
```typescript
(e: 'close'): void
```

**內部狀態：**
```typescript
const filename = ref(props.defaultFilename)
const copied = ref(false)  // 複製成功後短暫顯示「已複製」，2 秒後恢復
```
`watch(() => props.visible, v => { if (v) filename.value = props.defaultFilename })`——每次重新打開彈窗都重置檔名輸入框，避免上次編輯的殘留值蓋過新產生的預設檔名。

**Template 結構**（沿用 `JournalScoreDialog.vue` 的 backdrop + card + header 慣例）：
```html
<div v-if="visible" class="code-preview-backdrop" @click.self="emit('close')">
  <div class="code-preview-card">
    <header class="code-preview-header">
      <input
        v-model="filename"
        class="code-preview-filename-input"
        spellcheck="false"
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

    <pre class="code-preview-body"><code ref="codeEl" class="language-python">{{ code }}</code></pre>
  </div>
</div>
```

**語法高亮：** 用 `highlight.js`（`import hljs from 'highlight.js/lib/core'` + `import python from 'highlight.js/lib/languages/python'` + 只註冊 python，不用完整版避免載入用不到的語言包），在 `onMounted` 跟 `watch(() => props.code, ...)` 時對 `codeEl.value` 呼叫 `hljs.highlightElement(codeEl.value)`。樣式固定用深色主題（`highlight.js/styles/atom-one-dark.css`，直接 import），跟網頁本身的亮/暗模式無關——這是程式碼區塊的通用慣例（GitHub、Discord 的程式碼區塊也是這樣，不會跟著頁面主題變色）。

**複製到剪貼簿：**
```typescript
async function handleCopy (): Promise<void> {
  await navigator.clipboard.writeText(props.code)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
```

**下載（檔名處理與驗證）：**
```typescript
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
```
（`appendChild`/`remove()` 與 `setTimeout` 才 `revokeObjectURL` 是這次順便修正的既有下載邏輯小缺陷——舊版 `handleExportCode()` 沒有把 `<a>` 掛進 `document.body`、也是同步立刻 `revokeObjectURL`，在部分瀏覽器歷史上可能導致下載失敗，這次搬過來時一併修正。）

**樣式重點：**
- `.code-preview-backdrop`／`.code-preview-card` 完全比照 `journal-score-backdrop`／`journal-score-card` 的既有 CSS（`position: fixed; inset: 0` 置中遮罩、卡片 `width` 改大一點例如 `780px` 因為程式碼需要更寬的顯示空間、`max-height: calc(100vh - 64px)`、`overflow: hidden` 讓內部各自捲動）
- `.code-preview-filename-input`：無邊框、背景透明、字體跟標題一樣大小，看起來像標題文字但滑鼠移上去/點擊時有可編輯的視覺提示（例如 `:hover`/`:focus` 時出現底線或淺色背景）
- `.code-preview-body`：`overflow: auto`（雙向捲動，程式碼行可能很長）、深色背景（跟隨 highlight.js 主題）、等寬字體、`padding`、`flex: 1`（佔滿卡片剩餘高度）

### 2. 修改 `frontend/src/components/workflow/WorkflowWorkspace.vue`

**新增 import：**
```typescript
import CodeExportPreviewModal from '@/components/workflow/CodeExportPreviewModal.vue'
```

**新增 template（放在既有 `<UploadDialog>` 附近）：**
```html
<CodeExportPreviewModal
  :code="exportedCode"
  :default-filename="exportedFilename"
  :visible="codePreviewVisible"
  @close="codePreviewVisible = false"
/>
```

**`handleExportCode()` 改動：**
```typescript
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
原本 `handleExportCode()` 裡組 `Blob`／觸發下載的邏輯整段搬進 `CodeExportPreviewModal.vue` 的 `handleDownload()`（並順便修正上面提到的兩個小缺陷），這裡不再直接碰 DOM 下載邏輯。

### 3. 新增 npm 依賴

`frontend/package.json` 加入 `highlight.js`（目前最新穩定版）。因為用 `highlight.js/lib/core` + 只註冊 `python` 語言，bundle 增量很小（不含用不到的上百種語言文法檔）。

## 錯誤處理 / 邊界情況

- API 呼叫失敗（跟現在一樣）：`workflowError.value` 顯示錯誤訊息，`codePreviewVisible` 維持 `false`，彈窗不會打開
- 使用者把檔名清空後按下載：`resolveFilename()` 退回 `defaultFilename`（`workflow_export.py`），不會下載出一個空檔名的檔案
- 使用者輸入的檔名沒有 `.py` 副檔名：自動補上（例如輸入 `test` 會下載成 `test.py`）
- `navigator.clipboard.writeText` 在非 HTTPS/非 localhost 環境可能不可用：由瀏覽器原生拋出的 rejection 目前不特別 catch——這個 app 的開發/使用環境是 localhost，屬於安全環境，`clipboard.writeText` 可以正常運作，不特別處理屬於合理範圍內的簡化
- 使用者連續點兩次「匯出程式碼」按鈕：跟現在一樣由 `exportingCode`／按鈕 `disabled` 擋掉，不會觸發兩次 API 呼叫

## 測試

前端沒有自動化測試框架（vitest 未安裝），比照這個專案其他前端改動的慣例：
1. `npm run type-check`（在 `datamind-frontend` container 內跑，host 上因為缺 `@tiptap/*` 套件會有既有的 53 個不相關錯誤）確認新增/修改的檔案沒有新增型別錯誤
2. 人工瀏覽器驗證：
   - 開一個有模型設定的 workflow，按「匯出程式碼」，確認跳出預覽彈窗、程式碼內容正確且有語法高亮（關鍵字、字串、註解要有不同顏色）
   - 按「複製」，貼到別處確認內容一致，按鈕文字短暫變成「已複製」
   - 修改檔名輸入框（例如改成 `my_test`），按「下載」，確認下載出來的檔案叫 `my_test.py`
   - 清空檔名輸入框，按「下載」，確認退回 `workflow_export.py`
   - 按右上角 X 或點擊背景遮罩，確認彈窗關閉且不影響畫布其他操作
   - 沒有選任何模型時按「匯出程式碼」，確認顯示錯誤訊息、彈窗不會打開
