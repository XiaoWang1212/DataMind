# 論文編輯器互動優化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `/paper` 頁面的檢視/編輯切換改成滑動 pill 動畫、把永遠展開的引用側邊欄改成點擊標記才彈出的卡片、並讓編輯工具列能把工作流程的模型比對數值畫成圖表插入論文。

**Architecture:** 三個功能各自獨立、互不依賴，分別新增 `ModeSwitch.vue`（滑動 pill）、`CitationPopover.vue`（Teleport 到 `body` 的定位卡片，取代 `CitationPanel.vue`）、`InsertChartDialog.vue` + 自製 SVG `BarChart.vue`/`RadarChart.vue`（取代不存在的圖表產出物）。全部是前端變更，圖表以 base64 SVG 圖片直接寫進既有 Tiptap `content` JSON，不新增後端 API。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript + Tiptap 3（`@tiptap/vue-3` 系列）、Vuetify 4。

## Global Constraints

- 前端沒有 vitest/jest；每個 task 用 `npm run type-check`(`frontend/` 目錄下，`vue-tsc --build --force`)當自動化把關，其餘用手動瀏覽器驗證。前端 dev server 埠號 **3000**。
- 程式碼風格照現有 `frontend/src/components/paper/` 檔案：單引號、無分號、2 空白縮排、函式簽名 `functionName (args)` 中間留空格、import 依路徑字母序排列。
- 這次全部是前端變更，不新增/修改任何後端檔案，不改 `report_bp`/`ReportStore`。
- Out of scope（見 `docs/superpowers/specs/2026-07-28-paper-editor-ux-enhancements-design.md`）：圖表不做成可重新整理的互動節點（只存靜態圖片快照）、不支援匯出 vue-flow 節點流程圖本身、引用 popover 不做編輯功能、pill 不做鍵盤導覽。
- Citation mark 的 `name: 'citation'`、`citationId` attribute、`data-citation-id`/`data-citation-number` 這些既有慣例（`frontend/src/components/paper/citationMark.ts`）維持不變，本次不動這個檔案。

---

## Task 1: `ModeSwitch.vue` — 滑動 pill 元件

**Files:**
- Create: `frontend/src/components/paper/ModeSwitch.vue`

**Interfaces:**
- Produces: Props `{ modelValue: 'view' | 'edit', disabled?: boolean, locked?: boolean }`；Emits `update:modelValue(mode: 'view' | 'edit')`。Task 2（`PaperPage.vue`）是唯一消費者。

此元件這一步先不接進任何頁面，用型別檢查驗證；瀏覽器手動驗證留到 Task 2。

- [ ] **Step 1: 建立 `frontend/src/components/paper/ModeSwitch.vue`**

```vue
<template>
  <div ref="trackRef" class="mode-switch">
    <span ref="pillRef" class="pill" />
    <button
      ref="viewBtnRef"
      class="mode-switch-btn"
      :class="{ active: modelValue === 'view' }"
      :disabled="disabled || (locked && modelValue !== 'view')"
      type="button"
      @click="select('view')"
    >
      檢視
    </button>
    <button
      ref="editBtnRef"
      class="mode-switch-btn"
      :class="{ active: modelValue === 'edit' }"
      :disabled="disabled"
      type="button"
      @click="select('edit')"
    >
      編輯
    </button>
  </div>
</template>

<script setup lang="ts">
  import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

  const props = withDefaults(defineProps<{
    modelValue: 'view' | 'edit'
    disabled?: boolean
    locked?: boolean
  }>(), {
    disabled: false,
    locked: false,
  })

  const emit = defineEmits<{
    (e: 'update:modelValue', mode: 'view' | 'edit'): void
  }>()

  const trackRef = ref<HTMLElement | null>(null)
  const pillRef = ref<HTMLElement | null>(null)
  const viewBtnRef = ref<HTMLButtonElement | null>(null)
  const editBtnRef = ref<HTMLButtonElement | null>(null)

  function targetBtn (mode: 'view' | 'edit'): HTMLButtonElement | null {
    return mode === 'view' ? viewBtnRef.value : editBtnRef.value
  }

  function movePillTo (mode: 'view' | 'edit') {
    const btn = targetBtn(mode)
    const pill = pillRef.value
    if (!btn || !pill) return
    pill.style.left = `${btn.offsetLeft}px`
    pill.style.width = `${btn.offsetWidth}px`
  }

  function select (mode: 'view' | 'edit') {
    if (props.disabled) return
    if (mode === props.modelValue) return
    if (props.locked) return
    emit('update:modelValue', mode)
  }

  function handleResize () {
    movePillTo(props.modelValue)
  }

  watch(() => props.modelValue, mode => {
    movePillTo(mode)
  })

  onMounted(async () => {
    await nextTick()
    movePillTo(props.modelValue)
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
  })
</script>

<style scoped>
  .mode-switch {
    position: relative;
    display: inline-flex;
    align-items: center;
    padding: 3px;
    border-radius: 999px;
    background: #eceef3;
  }

  .pill {
    position: absolute;
    top: 3px;
    bottom: 3px;
    left: 0;
    width: 0;
    border-radius: 999px;
    background: var(--brand, #1058d6);
    transition:
      left 0.4s cubic-bezier(0.65, 0, 0.35, 1),
      width 0.4s cubic-bezier(0.65, 0, 0.35, 1);
  }

  .mode-switch-btn {
    position: relative;
    z-index: 1;
    padding: 5px 16px;
    border: none;
    background: transparent;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary, #6f7480);
    cursor: pointer;
    transition: color 0.4s cubic-bezier(0.65, 0, 0.35, 1);
  }

  .mode-switch-btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .mode-switch-btn.active {
    color: #ffffff;
  }
</style>
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/ModeSwitch.vue
git commit -m "feat: add ModeSwitch sliding-pill component"
```

---

## Task 2: 整合 — `ModeSwitch` 取代 `PaperPage.vue` 的編輯按鈕

**Files:**
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes: `ModeSwitch`（Task 1）props/emit 如上。

- [ ] **Step 1: 修改 import**

在 `frontend/src/views/PaperPage.vue` 的 `<script setup>` import 區塊，`CitationPanel` 與 `PaperEditor` 之間插入：

```ts
import ModeSwitch from '@/components/paper/ModeSwitch.vue'
```

- [ ] **Step 2: 修改 `toolbar-actions` 區塊**

Old（`PaperPage.vue:16-39` 內的 `<div class="toolbar-actions">`）:
```html
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
```

New:
```html
        <div class="toolbar-actions">
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <template v-if="mode === 'edit'">
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
```

- [ ] **Step 3: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 4: 手動瀏覽器驗證**

```bash
cd backend && uv run python app.py &
cd frontend && npm run dev &
```

開 `http://localhost:3000/paper`：
1. 確認 pill 初始就對齊「檢視」文字（不是疊在左上角 0/0）
2. 點「編輯」→ pill 用約 0.4 秒滑到「編輯」位置，文字顏色從灰轉白（crossfade），同時右側出現「取消」「儲存」
3. 此時再點「檢視」→ 確認**沒有反應**（`locked` 生效，必須用取消/儲存離開編輯）
4. 點「取消」→ pill 滑回「檢視」，右側按鈕消失
5. 縮放瀏覽器視窗寬度 → 確認 pill 仍準確對齊目前 active 的按鈕（`resize` 監聽生效）

```bash
kill %1 %2
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: integrate ModeSwitch into paper page toolbar"
```

---

## Task 3: `CitationPopover.vue` — 點擊才彈出的引用卡片

**Files:**
- Create: `frontend/src/components/paper/CitationPopover.vue`

**Interfaces:**
- Consumes: `Citation` type（`@/constants/reportData`，不變）。
- Produces: Props `{ citation: Citation | null, target: HTMLElement | null, index: number }`；Emits `close()`。Task 4 是唯一消費者。

用 `Teleport` 到 `body` + 手動用 `target.getBoundingClientRect()` 定位，不依賴 Vuetify `v-menu` 的 activator API（Vuetify 4 是新主版號，避免依賴不確定的 API 細節）。點卡片外的透明背景層即觸發 `close`。

- [ ] **Step 1: 建立 `frontend/src/components/paper/CitationPopover.vue`**

```vue
<template>
  <Teleport to="body">
    <div v-if="citation" class="citation-popover-backdrop" @click="emit('close')">
      <article class="citation-popover-card" :style="cardStyle" @click.stop>
        <p class="citation-label">
          <v-icon icon="mdi-book-open-variant-outline" size="13" />
          來源文獻 [{{ index }}]
        </p>
        <p class="citation-field"><span>標題:</span>{{ citation.title }}</p>
        <p class="citation-field"><span>作者:</span>{{ citation.authors }} ({{ citation.year }})</p>
        <p class="citation-field"><span>期刊:</span>{{ citation.journal }}</p>

        <p class="citation-label snippet-label">
          <v-icon icon="mdi-text-search" size="13" />
          檢索片段
        </p>
        <p class="citation-snippet">{{ citation.snippet }}</p>
      </article>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import type { CSSProperties } from 'vue'
  import type { Citation } from '@/constants/reportData'
  import { computed } from 'vue'

  const props = defineProps<{
    citation: Citation | null
    target: HTMLElement | null
    index: number
  }>()

  const emit = defineEmits<{
    (e: 'close'): void
  }>()

  const cardWidth = 300

  const cardStyle = computed((): CSSProperties => {
    if (!props.target) return { display: 'none' }
    const rect = props.target.getBoundingClientRect()
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - cardWidth - 8)
    return {
      position: 'fixed',
      top: `${rect.bottom + 8}px`,
      left: `${left}px`,
      width: `${cardWidth}px`,
    }
  })
</script>

<style scoped>
  .citation-popover-backdrop {
    position: fixed;
    inset: 0;
    z-index: 2400;
    background: transparent;
  }

  .citation-popover-card {
    background: #fffbe8;
    border: 1px solid #eadf9e;
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
  }

  .citation-label {
    margin: 0 0 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 700;
    color: #8a6d1a;
  }

  .snippet-label {
    margin-top: 10px;
  }

  .citation-field {
    margin: 0 0 3px;
    font-size: 12px;
    line-height: 1.55;
    color: #4a4433;
  }

  .citation-field span {
    font-weight: 700;
    color: #6d5c22;
  }

  .citation-snippet {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    font-style: italic;
    color: #5c5340;
  }
</style>
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/CitationPopover.vue
git commit -m "feat: add CitationPopover for click-to-reveal citation info"
```

---

## Task 4: 整合 — `CitationPopover` 取代 `CitationPanel` 側邊欄

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`
- Modify: `frontend/src/views/PaperPage.vue`
- Delete: `frontend/src/components/paper/CitationPanel.vue`

**Interfaces:**
- Produces: `PaperEditor` 的 `citation-click` emit payload 從 `citationId: string` 改為 `{ citationId: string, target: HTMLElement }`。Task 4 自己是這個改動的唯一消費者（`PaperPage.vue` 同一 task 內一起改）。

- [ ] **Step 1: 修改 `PaperEditor.vue` 的 emit 型別與 `handleClick`**

Old（`PaperEditor.vue:126-129`）:
```ts
  const emit = defineEmits<{
    (e: 'update:modelValue', content: JSONContent): void
    (e: 'citation-click', citationId: string): void
  }>()
```

New:
```ts
  const emit = defineEmits<{
    (e: 'update:modelValue', content: JSONContent): void
    (e: 'citation-click', payload: { citationId: string, target: HTMLElement }): void
  }>()
```

Old（`PaperEditor.vue:148-159`）:
```ts
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
```

New:
```ts
    editorProps: {
      handleClick: (_view, _pos, event) => {
        if (props.editable) return false
        const target = (event.target as HTMLElement).closest<HTMLElement>('[data-citation-id]')
        const citationId = target?.getAttribute('data-citation-id')
        if (citationId && target) {
          emit('citation-click', { citationId, target })
          return true
        }
        return false
      },
    },
```

- [ ] **Step 2: 移除 `PaperEditor.vue` 已無消費者的 `defineExpose`**

Old（`PaperEditor.vue:177-179`）:
```ts
  defineExpose({
    getDom: (): HTMLElement | null => editor.value?.view.dom ?? null,
  })
```

刪除這整段（`onPanelSelect` 是唯一呼叫者，Step 4 會一起移除）。

- [ ] **Step 3: 修改 `PaperPage.vue` import**

Old:
```ts
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
```

New:
```ts
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
```

- [ ] **Step 4: 修改 `PaperPage.vue` 的 refs/computed/函式**

Old（`PaperPage.vue` script 區）:
```ts
  const activeCitationId = ref<string | null>(null)
  const editorRef = ref<InstanceType<typeof PaperEditor> | null>(null)

  let savedSnapshot: PaperReport = mockPaperReport
```

New:
```ts
  const activeCitationId = ref<string | null>(null)
  const popoverTarget = ref<HTMLElement | null>(null)

  const popoverCitation = computed(() =>
    report.value.citations.find(c => c.id === activeCitationId.value) ?? null,
  )
  const popoverIndex = computed(() =>
    report.value.citations.findIndex(c => c.id === activeCitationId.value) + 1,
  )

  let savedSnapshot: PaperReport = mockPaperReport
```

Old:
```ts
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
```

New:
```ts
  function onCitationClick ({ citationId, target }: { citationId: string, target: HTMLElement }) {
    if (activeCitationId.value === citationId) {
      activeCitationId.value = null
      return
    }
    activeCitationId.value = citationId
    popoverTarget.value = target
  }
```

- [ ] **Step 5: 修改 `PaperPage.vue` 樣板**

Old:
```html
      <div v-else class="paper-body">
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
```

New:
```html
      <div v-else class="paper-body">
        <article class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            @citation-click="onCitationClick"
          />
        </article>
      </div>

      <CitationPopover
        :citation="popoverCitation"
        :index="popoverIndex"
        :target="popoverTarget"
        @close="activeCitationId = null"
      />
```

- [ ] **Step 6: 移除 `PaperPage.vue` 的 `.paper-citations` 相關樣式**

Old（`PaperPage.vue` `<style scoped>` 區）:
```css
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
```

New:
```css
  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
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
```

- [ ] **Step 7: 刪除 `CitationPanel.vue`**

```bash
rm frontend/src/components/paper/CitationPanel.vue
```

- [ ] **Step 8: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出（會抓到任何殘留引用舊 `CitationPanel`/`editorRef`/`getDom` 的地方）。

- [ ] **Step 9: 手動瀏覽器驗證**

```bash
cd backend && uv run python app.py &
cd frontend && npm run dev &
```

開 `http://localhost:3000/paper`（檢視模式）：
1. 確認畫面右側**沒有**永遠展開的引用側欄了，正文區改成單欄置中
2. 點正文中的引用標記(黃色高亮 `[1]`)→ 標記正下方彈出卡片，內容含標題/作者/期刊/年份/檢索片段
3. 點卡片外任意空白處 → 卡片關閉
4. 再點同一個標記 → 卡片再次彈出；再點一次同一個標記 → 卡片關閉(toggle)
5. 點另一個引用標記(`[2]`)→ 卡片內容切換成對應文獻,位置也跟著移動到新標記下方
6. 進入編輯模式 → 點引用文字確認**沒有**彈出卡片(編輯模式本來就不綁定 click)

```bash
kill %1 %2
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue frontend/src/views/PaperPage.vue
git rm frontend/src/components/paper/CitationPanel.vue
git commit -m "feat: replace always-visible citation sidebar with click-to-reveal popover"
```

---

## Task 5: `summarizeWorkflowResult.ts` — 補上 `valueRaw` 數值欄位

**Files:**
- Modify: `frontend/src/utils/workflow/summarizeWorkflowResult.ts`

**Interfaces:**
- Produces: `ModelMetricSummary.metrics` 陣列每個元素新增 `valueRaw: number`(平均值,`toFixed` 之前的原始數字)。Task 7(`InsertChartDialog.vue`)消費這個欄位畫圖;既有呼叫端 `ResultView.vue` 只用 `valueFormatted`,不受影響。

- [ ] **Step 1: 修改型別與計算邏輯**

Old（`summarizeWorkflowResult.ts:1-48`全檔）:
```ts
export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult (
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[] {
  if (!workflowResult) return []
  const results = Array.isArray(workflowResult.results)
    ? workflowResult.results
    : []

  const modelGroups = new Map<string, { count: number, metrics: Record<string, number[]>, errors: Record<string, string> }>()

  for (const result of results.filter((r: any) => r && typeof r === 'object')) {
    const modelName = result.model_name || 'unknown'
    const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

    if (Array.isArray(result.metrics)) {
      for (const metric of result.metrics) {
        const name = metric.metric || 'unknown'
        if (metric?.error) { existing.errors[name] = metric.error; continue }
        const value = Number(metric.value)
        if (!Number.isNaN(value)) {
          existing.metrics[name] = existing.metrics[name] ?? []
          existing.metrics[name].push(value)
        }
      }
    }
    existing.count += 1
    modelGroups.set(modelName, existing)
  }

  return Array.from(modelGroups.entries()).map(([modelName, group]) => ({
    model_name: modelName,
    split_name: `${group.count} splits`,
    metrics: Object.entries(group.metrics).map(([metric, values]) => ({
      metric,
      valueFormatted: values.length > 0
        ? (values.reduce((s, v) => s + v, 0) / values.length).toFixed(4)
        : 'N/A',
    })),
    errors: group.errors,
  }))
}
```

New（整檔）:
```ts
export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string, valueRaw: number }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult (
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[] {
  if (!workflowResult) return []
  const results = Array.isArray(workflowResult.results)
    ? workflowResult.results
    : []

  const modelGroups = new Map<string, { count: number, metrics: Record<string, number[]>, errors: Record<string, string> }>()

  for (const result of results.filter((r: any) => r && typeof r === 'object')) {
    const modelName = result.model_name || 'unknown'
    const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

    if (Array.isArray(result.metrics)) {
      for (const metric of result.metrics) {
        const name = metric.metric || 'unknown'
        if (metric?.error) { existing.errors[name] = metric.error; continue }
        const value = Number(metric.value)
        if (!Number.isNaN(value)) {
          existing.metrics[name] = existing.metrics[name] ?? []
          existing.metrics[name].push(value)
        }
      }
    }
    existing.count += 1
    modelGroups.set(modelName, existing)
  }

  return Array.from(modelGroups.entries()).map(([modelName, group]) => ({
    model_name: modelName,
    split_name: `${group.count} splits`,
    metrics: Object.entries(group.metrics).map(([metric, values]) => {
      const average = values.length > 0 ? values.reduce((s, v) => s + v, 0) / values.length : 0
      return {
        metric,
        valueRaw: average,
        valueFormatted: values.length > 0 ? average.toFixed(4) : 'N/A',
      }
    }),
    errors: group.errors,
  }))
}
```

- [ ] **Step 2: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。`ResultView.vue` 只讀 `valueFormatted`，多出的 `valueRaw` 欄位不會讓它壞掉。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/workflow/summarizeWorkflowResult.ts
git commit -m "feat: expose raw numeric metric values for chart rendering"
```

---

## Task 6: SVG 圖表元件 — `BarChart.vue` / `RadarChart.vue`

**Files:**
- Create: `frontend/src/components/paper/charts/chartColors.ts`
- Create: `frontend/src/components/paper/charts/BarChart.vue`
- Create: `frontend/src/components/paper/charts/RadarChart.vue`

**Interfaces:**
- Produces: 共用型別 `{ model: string, metric: string, value: number }[]` 當作 `series` prop（兩個元件一致）；`colorForIndex(index: number): string`。Task 7（`InsertChartDialog.vue`）是消費者。

- [ ] **Step 1: 建立 `frontend/src/components/paper/charts/chartColors.ts`**

```ts
export const CHART_COLORS = ['#1058d6', '#2fb380', '#e08a1e', '#c2418f', '#5b6dd6', '#d64545']

export function colorForIndex (index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length]
}
```

- [ ] **Step 2: 建立 `frontend/src/components/paper/charts/BarChart.vue`**

```vue
<template>
  <div>
    <svg
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      :width="width"
      class="chart-svg"
      xmlns="http://www.w3.org/2000/svg"
    >
      <line
        v-for="tick in yTicks"
        :key="`grid-${tick.value}`"
        class="chart-gridline"
        :x1="padding.left"
        :x2="width - padding.right"
        :y1="tick.y"
        :y2="tick.y"
      />
      <text
        v-for="tick in yTicks"
        :key="`label-${tick.value}`"
        class="chart-axis-label"
        text-anchor="end"
        :x="padding.left - 8"
        :y="tick.y + 4"
      >
        {{ tick.value.toFixed(2) }}
      </text>

      <g v-for="group in groups" :key="group.metric">
        <rect
          v-for="(bar, barIndex) in group.bars"
          :key="bar.model"
          :fill="colorForIndex(barIndex)"
          :height="bar.barHeight"
          :width="barWidth"
          :x="group.groupX + barIndex * (barWidth + barGap)"
          :y="bar.barY"
        />
        <text
          class="chart-axis-label"
          text-anchor="middle"
          :x="group.centerX"
          :y="height - padding.bottom + 18"
        >
          {{ group.metric }}
        </text>
      </g>

      <line
        class="chart-axis-line"
        :x1="padding.left"
        :x2="width - padding.right"
        :y1="height - padding.bottom"
        :y2="height - padding.bottom"
      />
    </svg>

    <ul class="chart-legend">
      <li v-for="(model, modelIndex) in models" :key="model" class="chart-legend-item">
        <span class="chart-legend-swatch" :style="{ background: colorForIndex(modelIndex) }" />
        {{ model }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { colorForIndex } from './chartColors'

  const props = withDefaults(defineProps<{
    series: { model: string, metric: string, value: number }[]
    width?: number
    height?: number
  }>(), {
    width: 520,
    height: 300,
  })

  const padding = { top: 16, right: 16, bottom: 46, left: 48 }
  const barWidth = 18
  const barGap = 6

  const models = computed(() => [...new Set(props.series.map(point => point.model))])
  const metrics = computed(() => [...new Set(props.series.map(point => point.metric))])

  const maxValue = computed(() => {
    const max = Math.max(0, ...props.series.map(point => point.value))
    return max === 0 ? 1 : max
  })

  const chartInnerHeight = computed(() => props.height - padding.top - padding.bottom)
  const chartInnerWidth = computed(() => props.width - padding.left - padding.right)

  const yTicks = computed(() => {
    const tickCount = 4
    return Array.from({ length: tickCount + 1 }, (_, index) => {
      const value = (maxValue.value / tickCount) * (tickCount - index)
      const y = padding.top + (chartInnerHeight.value / tickCount) * index
      return { value, y }
    })
  })

  const groups = computed(() => {
    const groupWidth = models.value.length * (barWidth + barGap)
    const totalGroupsWidth = metrics.value.length * groupWidth
    const gapBetweenGroups = (chartInnerWidth.value - totalGroupsWidth) / (metrics.value.length + 1)

    return metrics.value.map((metric, metricIndex) => {
      const groupX = padding.left + gapBetweenGroups * (metricIndex + 1) + groupWidth * metricIndex
      const bars = models.value.map(model => {
        const point = props.series.find(p => p.metric === metric && p.model === model)
        const value = point?.value ?? 0
        const barHeight = (value / maxValue.value) * chartInnerHeight.value
        return {
          model,
          barHeight,
          barY: padding.top + chartInnerHeight.value - barHeight,
        }
      })
      return { metric, groupX, centerX: groupX + groupWidth / 2, bars }
    })
  })
</script>

<style scoped>
  .chart-svg {
    display: block;
    max-width: 100%;
  }

  .chart-gridline {
    stroke: #e8ebf1;
    stroke-width: 1;
  }

  .chart-axis-line {
    stroke: #d8dbe3;
    stroke-width: 1;
  }

  .chart-axis-label {
    font-size: 10px;
    fill: #6f7480;
  }

  .chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
  }

  .chart-legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #4a4f5c;
  }

  .chart-legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
</style>
```

- [ ] **Step 3: 建立 `frontend/src/components/paper/charts/RadarChart.vue`**

```vue
<template>
  <div>
    <svg
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      :width="size"
      class="chart-svg"
      xmlns="http://www.w3.org/2000/svg"
    >
      <polygon
        v-for="ring in gridRings"
        :key="ring.scale"
        class="chart-gridline"
        fill="none"
        :points="ring.points"
      />
      <line
        v-for="axis in axes"
        :key="`axis-${axis.metric}`"
        class="chart-axis-line"
        :x1="center"
        :x2="axis.labelX"
        :y1="center"
        :y2="axis.labelY"
      />
      <text
        v-for="axis in axes"
        :key="`label-${axis.metric}`"
        class="chart-axis-label"
        :text-anchor="axis.anchor"
        :x="axis.textX"
        :y="axis.textY"
      >
        {{ axis.metric }}
      </text>

      <polygon
        v-for="(model, modelIndex) in models"
        :key="model"
        class="chart-radar-shape"
        :fill="colorForIndex(modelIndex)"
        fill-opacity="0.18"
        :points="polygonPoints(model)"
        :stroke="colorForIndex(modelIndex)"
      />
    </svg>

    <ul class="chart-legend">
      <li v-for="(model, modelIndex) in models" :key="model" class="chart-legend-item">
        <span class="chart-legend-swatch" :style="{ background: colorForIndex(modelIndex) }" />
        {{ model }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { colorForIndex } from './chartColors'

  const props = withDefaults(defineProps<{
    series: { model: string, metric: string, value: number }[]
    size?: number
  }>(), {
    size: 320,
  })

  const center = computed(() => props.size / 2)
  const radius = computed(() => props.size / 2 - 40)

  const models = computed(() => [...new Set(props.series.map(point => point.model))])
  const metrics = computed(() => [...new Set(props.series.map(point => point.metric))])

  const maxByMetric = computed(() => {
    const map = new Map<string, number>()
    for (const metric of metrics.value) {
      const values = props.series.filter(p => p.metric === metric).map(p => p.value)
      map.set(metric, Math.max(...values, 0) || 1)
    }
    return map
  })

  function angleForAxis (axisIndex: number): number {
    return (Math.PI * 2 * axisIndex) / metrics.value.length - Math.PI / 2
  }

  function pointForValue (axisIndex: number, ratio: number): { x: number, y: number } {
    const angle = angleForAxis(axisIndex)
    return {
      x: center.value + Math.cos(angle) * radius.value * ratio,
      y: center.value + Math.sin(angle) * radius.value * ratio,
    }
  }

  const axes = computed(() => metrics.value.map((metric, axisIndex) => {
    const onAxis = pointForValue(axisIndex, 1)
    const label = pointForValue(axisIndex, 1.18)
    const angle = angleForAxis(axisIndex)
    const cos = Math.cos(angle)
    const anchor = cos > 0.2 ? 'start' : cos < -0.2 ? 'end' : 'middle'
    return {
      metric,
      labelX: onAxis.x,
      labelY: onAxis.y,
      textX: label.x,
      textY: label.y,
      anchor,
    }
  }))

  const gridRings = computed(() => [0.25, 0.5, 0.75, 1].map(scale => ({
    scale,
    points: metrics.value
      .map((_, axisIndex) => {
        const point = pointForValue(axisIndex, scale)
        return `${point.x},${point.y}`
      })
      .join(' '),
  })))

  function polygonPoints (model: string): string {
    return metrics.value
      .map((metric, axisIndex) => {
        const point = props.series.find(p => p.metric === metric && p.model === model)
        const max = maxByMetric.value.get(metric) ?? 1
        const ratio = point ? point.value / max : 0
        const { x, y } = pointForValue(axisIndex, ratio)
        return `${x},${y}`
      })
      .join(' ')
  }
</script>

<style scoped>
  .chart-svg {
    display: block;
    max-width: 100%;
  }

  .chart-gridline {
    stroke: #e8ebf1;
    stroke-width: 1;
  }

  .chart-axis-line {
    stroke: #d8dbe3;
    stroke-width: 1;
  }

  .chart-axis-label {
    font-size: 10px;
    fill: #6f7480;
  }

  .chart-radar-shape {
    stroke-width: 1.5;
  }

  .chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
  }

  .chart-legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #4a4f5c;
  }

  .chart-legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
</style>
```

- [ ] **Step 4: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/charts/
git commit -m "feat: add SVG BarChart/RadarChart components for model metric comparison"
```

---

## Task 7: 整合 — 插入圖表對話框與工具列按鈕

**Files:**
- Modify: `frontend/package.json`（新增依賴）
- Modify: `frontend/src/components/paper/PaperEditor.vue`
- Modify: `frontend/src/views/PaperPage.vue`
- Create: `frontend/src/components/paper/InsertChartDialog.vue`

**Interfaces:**
- Consumes: `BarChart`/`RadarChart`（Task 6）、`summarizeWorkflowResult`/`ModelMetricSummary`（Task 5，`@/utils/workflow/summarizeWorkflowResult`）、`loadWorkflowStateFromStorage`（既有，`@/composables/workflow/useWorkflowStorage`）。
- Produces: `PaperEditor` 新增 prop `projectId?: string`；`InsertChartDialog` Props `{ modelValue: boolean, projectId: string | undefined }`，Emits `update:modelValue(boolean)`、`insert(dataUrl: string)`。

- [ ] **Step 1: 安裝 `@tiptap/extension-image`**

```bash
cd frontend
npm install @tiptap/extension-image@^3.29.0
```

Expected: `package.json` 的 `dependencies` 多出 `@tiptap/extension-image`。

- [ ] **Step 2: 建立 `frontend/src/components/paper/InsertChartDialog.vue`**

```vue
<template>
  <v-dialog
    max-width="640"
    :model-value="modelValue"
    @update:model-value="value => emit('update:modelValue', value)"
  >
    <v-card class="insert-chart-dialog">
      <v-card-title>插入圖表</v-card-title>

      <v-card-text>
        <p v-if="summaries.length === 0" class="empty-hint">
          此專案尚無工作流程結果可插入
        </p>

        <template v-else>
          <v-btn-toggle v-model="chartType" class="chart-type-toggle" density="compact" mandatory>
            <v-btn value="bar">長條圖</v-btn>
            <v-btn value="radar">雷達圖</v-btn>
          </v-btn-toggle>

          <div class="picker-row">
            <div class="picker-column">
              <p class="picker-label">模型</p>
              <v-checkbox
                v-for="model in availableModels"
                :key="model"
                v-model="selectedModels"
                density="compact"
                hide-details
                :label="model"
                :value="model"
              />
            </div>
            <div class="picker-column">
              <p class="picker-label">指標</p>
              <v-checkbox
                v-for="metric in availableMetrics"
                :key="metric"
                v-model="selectedMetrics"
                density="compact"
                hide-details
                :label="metric"
                :value="metric"
              />
            </div>
          </div>

          <p v-if="chartSeries.length === 0" class="empty-hint">請至少選擇一項模型與指標</p>
          <div v-else ref="previewRef" class="chart-preview">
            <BarChart v-if="chartType === 'bar'" :series="chartSeries" />
            <RadarChart v-else :series="chartSeries" />
          </div>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="primary" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
  import BarChart from '@/components/paper/charts/BarChart.vue'
  import RadarChart from '@/components/paper/charts/RadarChart.vue'

  const props = defineProps<{
    modelValue: boolean
    projectId: string | undefined
  }>()

  const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void
    (e: 'insert', dataUrl: string): void
  }>()

  const chartType = ref<'bar' | 'radar'>('bar')
  const summaries = ref<ModelMetricSummary[]>([])
  const selectedModels = ref<string[]>([])
  const selectedMetrics = ref<string[]>([])
  const previewRef = ref<HTMLElement | null>(null)

  watch(() => props.modelValue, open => {
    if (!open) return
    const state = loadWorkflowStateFromStorage(props.projectId)
    summaries.value = summarizeWorkflowResult(state?.workflowResult ?? null)
    selectedModels.value = summaries.value.map(s => s.model_name)
    selectedMetrics.value = [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))]
  })

  const availableModels = computed(() => summaries.value.map(s => s.model_name))
  const availableMetrics = computed(() =>
    [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))],
  )

  const chartSeries = computed(() => {
    const points: { model: string, metric: string, value: number }[] = []
    for (const summary of summaries.value) {
      if (!selectedModels.value.includes(summary.model_name)) continue
      for (const metric of summary.metrics) {
        if (!selectedMetrics.value.includes(metric.metric)) continue
        points.push({ model: summary.model_name, metric: metric.metric, value: metric.valueRaw })
      }
    }
    return points
  })

  function svgToDataUrl (svgString: string): string {
    const bytes = new TextEncoder().encode(svgString)
    let binary = ''
    for (const byte of bytes) binary += String.fromCharCode(byte)
    return `data:image/svg+xml;base64,${btoa(binary)}`
  }

  function handleInsert () {
    const svgEl = previewRef.value?.querySelector('svg')
    if (!svgEl) return
    const svgString = new XMLSerializer().serializeToString(svgEl)
    emit('insert', svgToDataUrl(svgString))
    emit('update:modelValue', false)
  }
</script>

<style scoped>
  .insert-chart-dialog {
    padding: 4px;
  }

  .empty-hint {
    font-size: 13px;
    color: #6f7480;
    padding: 12px 0;
  }

  .chart-type-toggle {
    margin-bottom: 14px;
  }

  .picker-row {
    display: flex;
    gap: 24px;
    margin-bottom: 14px;
  }

  .picker-column {
    flex: 1;
    min-width: 0;
    max-height: 160px;
    overflow-y: auto;
  }

  .picker-label {
    margin: 0 0 4px;
    font-size: 12px;
    font-weight: 700;
    color: #4a4f5c;
  }

  .chart-preview {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
  }
</style>
```

- [ ] **Step 3: 修改 `PaperEditor.vue` — import 與 props**

Old（`PaperEditor.vue` script 開頭 import 區,見 Task 4 修改後版本）:
```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { watch } from 'vue'
  import { CitationMark } from '@/components/paper/citationMark'

  const props = defineProps<{
    modelValue: JSONContent
    editable: boolean
    citations: Citation[]
  }>()
```

New:
```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { Image } from '@tiptap/extension-image'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { ref, watch } from 'vue'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'

  const props = defineProps<{
    modelValue: JSONContent
    editable: boolean
    citations: Citation[]
    projectId?: string
  }>()

  const chartDialogOpen = ref(false)

  function handleInsertChart (dataUrl: string) {
    editor.value?.chain().focus().setImage({ src: dataUrl, alt: '工作流程模型比對圖表' }).run()
  }
```

- [ ] **Step 4: 修改 `PaperEditor.vue` — extensions 陣列**

Old:
```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      CitationMark.configure({ citationIndex }),
    ],
```

New:
```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      Image.configure({ inline: false }),
      CitationMark.configure({ citationIndex }),
    ],
```

- [ ] **Step 5: 修改 `PaperEditor.vue` 樣板 — 工具列按鈕與 dialog**

Old（工具列表格按鈕與其後的分隔線,`PaperEditor.vue:92-98`）:
```html
      <v-btn
        icon="mdi-table-plus"
        size="small"
        variant="text"
        @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
      />
      <span class="toolbar-divider" />
```

New:
```html
      <v-btn
        icon="mdi-table-plus"
        size="small"
        variant="text"
        @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
      />
      <v-btn
        icon="mdi-chart-bar"
        size="small"
        variant="text"
        @click="chartDialogOpen = true"
      />
      <span class="toolbar-divider" />
```

Old（樣板結尾,`PaperEditor.vue:103-104`）:
```html
    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />
  </div>
</template>
```

New:
```html
    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <InsertChartDialog
      v-model="chartDialogOpen"
      :project-id="projectId"
      @insert="handleInsertChart"
    />
  </div>
</template>
```

- [ ] **Step 6: 修改 `PaperPage.vue` — 傳入 `project-id`**

Old（`PaperPage.vue` 樣板,Task 4 修改後版本）:
```html
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            @citation-click="onCitationClick"
          />
```

New:
```html
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
```

- [ ] **Step 7: 型別檢查**

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤輸出。

- [ ] **Step 8: 手動瀏覽器驗證**

需要先在 `/workflow` 頁面對某個專案跑過一次模型訓練，讓 `localStorage` 裡有 `workflowResult`（沒有的話，Dialog 應顯示「尚無工作流程結果」提示，也要驗證這個分支）。

```bash
cd backend && uv run python app.py &
cd frontend && npm run dev &
```

開 `http://localhost:3000/paper?project=<有跑過工作流程的專案 id>`，點「編輯」：

1. 點工具列「插入圖表」圖示（`mdi-chart-bar`）→ Dialog 開啟，預設全選模型與指標，預覽區顯示長條圖
2. 切到「雷達圖」→ 預覽即時變成雷達圖
3. 取消勾選某個模型/指標 → 預覽即時更新（圖上少一組長條/一個軸的資料）
4. 全部取消勾選模型 → 預覽區改顯示「請至少選擇一項」，「插入」按鈕變灰
5. 重新勾選、點「插入」→ Dialog 關閉，游標處出現一張圖片（放大確認圖片內容與剛才預覽一致，包含中文模型/指標文字沒有亂碼）
6. 點「儲存」→ 重新整理頁面（保留 `?project=` query）→ 確認圖片仍在
7. 開一個**沒有**跑過工作流程的專案 `/paper?project=<空專案 id>` → 編輯模式點「插入圖表」→ 確認顯示「此專案尚無工作流程結果可插入」，無法插入

```bash
kill %1 %2
```

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/paper/PaperEditor.vue frontend/src/components/paper/InsertChartDialog.vue frontend/src/views/PaperPage.vue
git commit -m "feat: insert workflow model comparison charts into paper editor"
```

---

## Self-Review Notes

- **Spec coverage**：spec（`docs/superpowers/specs/2026-07-28-paper-editor-ux-enhancements-design.md`）三個「做」項目——(A) `offsetLeft`/`offsetWidth` 滑動 pill + cubic-bezier 0.4s + crossfade → Task 1、2；(B) 移除側邊欄、點擊標記才彈出完整引用卡片 → Task 3、4；(C) 插入圖表（長條/雷達、模型/指標複選、即時預覽、靜態圖片插入、`@tiptap/extension-image`、`valueRaw`）→ Task 5、6、7。「不做」清單（互動式圖表節點、vue-flow 流程圖匯出、popover 編輯功能、pill 鍵盤導覽）都沒有出現在任何 task。
- **型別一致性**：`ModeSwitch` 的 `modelValue: 'view'|'edit'`／`disabled`／`locked` 在 Task 1 定義，Task 2 的 `v-model="mode"` `:disabled="loading"` `:locked="mode==='edit'"` 用法一致（`mode` 本身型別在 `PaperPage.vue` 既有程式碼中就是 `ref<'view'|'edit'>`，未變動）。`CitationPopover` 的 `citation`/`target`/`index` props 與 `close` emit 在 Task 3 定義，Task 4 的 `:citation="popoverCitation"` `:index="popoverIndex"` `:target="popoverTarget"` `@close="activeCitationId = null"` 用法一致。`PaperEditor` 的 `citation-click` payload `{citationId, target}` 在 Task 4 同時改了 emit 定義與 `PaperPage.vue` 的 `onCitationClick` 簽名，兩邊一致。`ModelMetricSummary.metrics[].valueRaw: number` 在 Task 5 定義，Task 7 的 `InsertChartDialog.vue` 用 `metric.valueRaw` 組出 `chartSeries`。`BarChart`/`RadarChart` 的 `series: {model,metric,value}[]` 在 Task 6 定義，Task 7 的 `chartSeries` computed 回傳型別完全一致。`InsertChartDialog` 的 `projectId: string | undefined` prop 與 `insert(dataUrl: string)` emit 在 Task 7 定義並在同一 task 內的 `PaperEditor.vue` 消費（`:project-id="projectId"`、`@insert="handleInsertChart"`）。
- **無佔位符**：所有 step 都是完整可執行的程式碼或指令，沒有「之後補」「視情況處理」這類字眼。Task 4 的 `defineExpose` 移除、Task 4 的 CSS 移除都給出明確的 old/new 對照，不是含糊描述。
