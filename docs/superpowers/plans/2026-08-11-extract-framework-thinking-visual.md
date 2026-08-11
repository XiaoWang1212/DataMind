# 框架提取思考顯示視覺重新設計 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「提取框架」頁面的思考顯示從灰色捲動方框，換成流動漸層光暈卡片，且只顯示最新兩句（上一句變小變淡、目前這句淡入），取代整段純文字堆疊。

**Architecture:** 純前端改動，只動 `frontend/src/views/hub/ExtractFrameworkView.vue` 一個檔案。移除累積字串 `thoughtLog`/捲動邏輯，改用 `currentLine`/`previousLine` 兩個 ref，每次收到 SSE `thought` 事件就更新一次（不是計時器），搭配 `<Transition>` 做淡入效果，CSS 用 `::before` 偽元素做流動漸層光暈邊框。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、CSS `@keyframes` + `mask`。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-11-extract-framework-thinking-visual-design.md`
- 只改 `ExtractFrameworkView.vue` 的思考顯示呈現層，不動 SSE 串流、`streamAnalyzeWorkflowFromPdf`、`onResult`/`onError` 邏輯、最終框架結果顯示
- 兩行文字切換的觸發時機是**每次收到後端 SSE 的一個 `thought` 事件**，不是固定時間間隔的計時器
- 本專案 frontend 沒有設定任何單元測試框架，驗證一律用 `npm run type-check` + 人工瀏覽器操作

---

### Task 1: 思考卡片視覺重新設計

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:53-61`（template，loading 區塊）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:113-146`（script，imports 與 state）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:159-176`（`startExtract` 內的重置與 `onThought`）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:369-401`（style，移除舊 class、新增卡片動畫 class）

**Interfaces:** 無（單一任務，純前端單檔案改動，不被其他任務消費）

- [ ] **Step 1: template — loading 區塊換成思考卡片**

找到（第 53-61 行）：

```html
        <div v-if="extracting" class="extracting-indicator">
          <div class="extracting-header">
            <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
            <span>正在提取框架...</span>
          </div>
          <div ref="thoughtLogEl" class="thought-log">
            <p class="thought-log-line">{{ displayedThought }}</p>
          </div>
        </div>
```

改成：

```html
        <div v-if="extracting" class="thinking-card">
          <div class="thinking-header">
            <span class="thinking-dot" />
            AI 正在思考
          </div>
          <p v-if="previousLine" class="thinking-line thinking-line--prev">{{ previousLine }}</p>
          <Transition mode="out-in" name="thinking-swap">
            <p :key="currentLine" class="thinking-line thinking-line--current">{{ currentLine }}</p>
          </Transition>
        </div>
```

- [ ] **Step 2: script — imports 與 state**

找到（第 113-146 行）：

```ts
<script setup lang="ts">
  import { computed, nextTick, ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { streamAnalyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'

  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const thoughtLog = ref('')
  const thoughtLogEl = ref<HTMLElement | null>(null)
  const displayedThought = computed(() => thoughtLog.value.replace(/\*\*?/g, ''))

  async function scrollThoughtLogToBottom (): Promise<void> {
    await nextTick()
    if (thoughtLogEl.value) {
      thoughtLogEl.value.scrollTop = thoughtLogEl.value.scrollHeight
    }
  }
```

改成：

```ts
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { streamAnalyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'

  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const currentLine = ref('')
  const previousLine = ref('')

  function stripMarkdownAsterisks (text: string): string {
    return text.replace(/\*\*?/g, '')
  }
```

- [ ] **Step 3: `startExtract` — 重置狀態與 `onThought`**

找到（第 159-176 行）：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    thoughtLog.value = ''

    const file = selectedFile.value
    const baseName = file.name.replace(/\.[^.]+$/, '')

    try {
      await streamAnalyzeWorkflowFromPdf(
        { file, title: baseName },
        {
          onThought: text => {
            thoughtLog.value += text
            void scrollThoughtLogToBottom()
          },
```

改成：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    currentLine.value = ''
    previousLine.value = ''

    const file = selectedFile.value
    const baseName = file.name.replace(/\.[^.]+$/, '')

    try {
      await streamAnalyzeWorkflowFromPdf(
        { file, title: baseName },
        {
          onThought: text => {
            previousLine.value = currentLine.value
            currentLine.value = stripMarkdownAsterisks(text)
          },
```

- [ ] **Step 4: style — 移除舊 class，新增思考卡片動畫**

找到（第 369-401 行）：

```css
.extracting-indicator {
  margin-top: 14px;
}

.extracting-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--color-secondary);
}

.thought-log {
  margin-top: 10px;
  max-height: 160px;
  overflow-y: auto;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  font-size: 12.5px;
  color: var(--color-secondary);
  line-height: 1.6;
}

.thought-log-line {
  margin: 0 0 6px;
  white-space: pre-wrap;
}

.thought-log-line:last-child {
  margin-bottom: 0;
}
```

改成：

```css
.thinking-card {
  position: relative;
  margin-top: 14px;
  border-radius: 12px;
  padding: 16px 18px;
  background: #fafaff;
  overflow: hidden;
  min-height: 3.4em;
}

.thinking-card::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 1.5px;
  border-radius: 12px;
  background: linear-gradient(120deg, #6366f1, #a855f7, #6366f1, #a855f7);
  background-size: 300% 300%;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: thinking-gradient-move 3s ease infinite;
}

@keyframes thinking-gradient-move {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #6366f1;
  margin-bottom: 8px;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6366f1;
  animation: thinking-pulse 1.2s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 100% { opacity: .3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.15); }
}

.thinking-line {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #4b5563;
  white-space: pre-wrap;
}

.thinking-line--prev {
  font-size: 12.5px;
  color: #b8bccb;
  margin-bottom: 4px;
}

.thinking-swap-enter-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.thinking-swap-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 6: 人工瀏覽器驗證**

啟動前端後登入，到「框架庫 → 從論文提取框架」，上傳 `backend/samples/gemini_sample/cin18058.pdf` 並點「開始提取」。

Expected:
- 卡片邊框有緩慢流動的漸層光暈動畫，標題「AI 正在思考」旁的小圓點有跳動效果
- 每次收到新的思考內容時，上一句變小變淡移到上方，新一句淡入顯示在下方
- 文字裡沒有殘留 `*`/`**` 星號
- 提取完成後卡片連同思考內容一起消失，右側正確顯示框架結果，跟改動前行為一致
- 上傳非 PDF 或超過大小上限的檔案時顯示錯誤訊息，卡片不會卡住

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "feat: redesign thinking display as gradient-glow card with two-line swap"
```
