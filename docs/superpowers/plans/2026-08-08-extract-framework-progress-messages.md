# 框架提取 Loading 進度訊息 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「提取框架」頁面等待期間固定不變的「正在提取框架...」文字，改成每 2.5 秒輪播一則預先寫好的階段訊息，播完最後一則就停留在該訊息不再循環。

**Architecture:** 純前端改動，只動 `frontend/src/views/hub/ExtractFrameworkView.vue` 一個檔案。不新增檔案、不動後端、不動 API。用一個 `messageIndex` ref 搭配 `setInterval` 遞增索引，`<Transition>` 做文字切換的淡入淡出。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、Vuetify（既有 `v-progress-circular`）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-08-extract-framework-progress-messages-design.md`
- 訊息陣列固定 4 則，順序如下（不可增減或改順序，設計文件已定案）：
  1. `正在解析 PDF 內容...`
  2. `正在辨識研究方法與模型架構...`
  3. `正在提取前處理與特徵工程步驟...`
  4. `正在整理成框架...`
- 每則顯示 2.5 秒（`2500` ms）後切下一則，到第 4 則後停住不循環。
- 本專案 frontend 沒有設定任何單元測試框架（無 `vitest`、無 `*.spec.ts`），驗證一律用 `npm run type-check` + 人工瀏覽器操作，不需要也不要新增測試框架。

---

### Task 1: 輪播進度訊息

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:53-56`（template，loading 區塊）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:108-131`（script，新增常數與 state）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:144-180`（`startExtract` 函式）
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue:341-348`（style，新增 fade transition class）

**Interfaces:** 無（單一任務，純前端單檔案改動，不被其他任務消費）

- [x] **Step 1: 在 `<script setup>` 內新增訊息常數與 state**

找到目前的區塊（第 108-131 行）：

```ts
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { analyzeWorkflowFromPdf } from '@/api/gemini'
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
```

改成（新增 `EXTRACT_MESSAGES` 常數、`messageIndex` ref、`messageTimer` 變數，其餘不變）：

```ts
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { analyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'

  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const EXTRACT_MESSAGES = [
    '正在解析 PDF 內容...',
    '正在辨識研究方法與模型架構...',
    '正在提取前處理與特徵工程步驟...',
    '正在整理成框架...',
  ]

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const messageIndex = ref(0)
  let messageTimer: ReturnType<typeof setInterval> | null = null
```

- [x] **Step 2: 在 `startExtract` 內啟動與清除計時器**

找到目前的函式（第 144-180 行）：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null

    try {
      const result = await analyzeWorkflowFromPdf({
        file: selectedFile.value,
        title: selectedFile.value.name.replace(/\.[^.]+$/, ''),
      })

      const models = (Array.isArray(result.models) ? result.models : []).map((m: unknown) =>
        typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? ''),
      )
      const preprocessing = (Array.isArray(result.preprocessing) ? result.preprocessing : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )
      const featureEngineering = (Array.isArray(result.featureEngineering) ? result.featureEngineering : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )

      rawWorkflowJson.value = result
      extractedData.value = {
        name: selectedFile.value.name.replace(/\.[^.]+$/, ''),
        models,
        preprocessing,
        featureEngineering,
        targetCol: String(result.target_col ?? result.targetCol ?? ''),
        metrics: Array.isArray(result.metrics) ? result.metrics.map(String) : [],
      }
    } catch (error) {
      extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
    } finally {
      extracting.value = false
    }
  }
```

改成（新增 `messageIndex` 重置與計時器啟動/清除，其餘邏輯不變）：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    messageIndex.value = 0
    messageTimer = setInterval(() => {
      if (messageIndex.value < EXTRACT_MESSAGES.length - 1) {
        messageIndex.value += 1
      }
    }, 2500)

    try {
      const result = await analyzeWorkflowFromPdf({
        file: selectedFile.value,
        title: selectedFile.value.name.replace(/\.[^.]+$/, ''),
      })

      const models = (Array.isArray(result.models) ? result.models : []).map((m: unknown) =>
        typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? ''),
      )
      const preprocessing = (Array.isArray(result.preprocessing) ? result.preprocessing : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )
      const featureEngineering = (Array.isArray(result.featureEngineering) ? result.featureEngineering : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )

      rawWorkflowJson.value = result
      extractedData.value = {
        name: selectedFile.value.name.replace(/\.[^.]+$/, ''),
        models,
        preprocessing,
        featureEngineering,
        targetCol: String(result.target_col ?? result.targetCol ?? ''),
        metrics: Array.isArray(result.metrics) ? result.metrics.map(String) : [],
      }
    } catch (error) {
      extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
    } finally {
      extracting.value = false
      if (messageTimer !== null) {
        clearInterval(messageTimer)
        messageTimer = null
      }
    }
  }
```

- [x] **Step 3: template 改用輪播訊息 + 淡入淡出**

找到（第 53-56 行）：

```html
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
          <span>正在提取框架...</span>
        </div>
```

改成：

```html
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
          <Transition mode="out-in" name="fade">
            <span :key="messageIndex">{{ EXTRACT_MESSAGES[messageIndex] }}</span>
          </Transition>
        </div>
```

- [x] **Step 4: 新增 fade transition CSS**

找到（第 341-348 行）：

```css
.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--color-secondary);
}
```

改成（在後面新增 fade class，`.extracting-indicator` 本身不變）：

```css
.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--color-secondary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
```

- [x] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 6: 人工瀏覽器驗證**

啟動前端（`docker compose up -d frontend` 或既有跑著的 dev server），登入後到「框架庫 → 從論文提取框架」，上傳一份 PDF 並點「開始提取」。

Expected:
- 文字每 2.5 秒切換一次，共 4 則，切換時有淡入淡出（不是瞬間跳字）
- 播完第 4 則「正在整理成框架...」後停在該句，不會跳回第 1 則
- 提取完成（成功或失敗）後文字與 spinner 一起消失，計時器不再跑（可用瀏覽器開發者工具觀察沒有殘留的 interval log，或重新點一次「開始提取」確認又從第 1 則開始，沒有疊加變快）

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "feat: rotate progress messages while extracting framework"
```
