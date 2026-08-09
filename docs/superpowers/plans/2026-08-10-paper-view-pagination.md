# 論文檢視模式分頁功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `PaperPage.vue` 的檢視模式以 A4 紙張比例分頁呈現論文內容，內容（含參考文獻）滿一頁自動接續到下一頁；編輯模式維持現有連續捲動行為完全不變。

**Architecture:** 新增一個唯讀元件 `PaginatedPaperView.vue`，用 Tiptap 的 `generateHTML()` 把論文 JSON 內容轉成靜態 HTML，在畫面外的隱藏容器量測每個頂層區塊的實際渲染高度，再用一個貪婪分頁演算法把區塊依序塞進固定高度的頁面預算裡；參考文獻經同一套流程轉成區塊、接續在正文之後一起分頁。編輯模式的 `PaperEditor.vue` 不受影響，只做一個共用擴充清單的抽取重構，避免兩邊的 Tiptap schema 定義日後跑掉。

**Tech Stack:** Vue 3 `<script setup>`、TypeScript、`@tiptap/core`（`generateHTML`，既有依賴，不新增套件）。

## Global Constraints

- 只影響檢視模式（`mode === 'view'`）。編輯模式的 `PaperEditor.vue` 排版、行為、樣式完全不變。
- 單頁尺寸固定 794×1123px（A4，96dpi 換算），四邊留白 96px，內容區 602×931px。
- 每頁下方置中顯示「第 X 頁」（X 從 1 起算）。
- 參考文獻併入分頁流程，跟正文一起排版、一起分頁；標題有孤兒控制——「標題＋緊接的第一個項目」放不下當頁剩餘空間時，兩者一起換到下一頁。
- 分頁只切區塊與區塊之間，不切區塊內部。單一區塊本身比一整頁還高時，整個放在自己的一頁，允許視覺上超出頁面高度（已知限制，不在此次範圍內解決）。
- `PaginatedPaperView` 的 `citation-click` emit 簽章須與 `PaperEditor.vue` 現有的完全一致：`{ citationId: string, target: HTMLElement }`。
- 使用 `@tiptap/core` 既有匯出的 `generateHTML(doc, extensions)`，不新增任何套件依賴。
- **本專案前端沒有安裝自動化測試框架**（無 vitest/jest，`package.json` 沒有 test script）。所有驗證一律採用本專案既有的手動驗證方式：`docker restart datamind-frontend` → 輪詢 `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` 直到回應 `200` → 用瀏覽器（含 `javascript_tool` 對 Vite dev server 的模組動態 `import()`）操作/斷言。不要引入新的測試框架，這超出本次範圍。

---

### Task 1: 抽出共用 Tiptap 內容擴充清單，重構 PaperEditor.vue

**Files:**
- Create: `frontend/src/components/paper/paperExtensions.ts`
- Modify: `frontend/src/components/paper/PaperEditor.vue:398-416`（import 區塊）、`PaperEditor.vue:530-545`（`useEditor` 的 `extensions` 陣列）

**Interfaces:**
- Produces: `buildPaperContentExtensions(citationIndex: Record<string, number>): Extensions`——回傳「會影響 schema／HTML 輸出」的 Tiptap 擴充陣列（不含 `CharacterCount`、`ColumnResizeBalance` 這類只影響互動、不影響渲染輸出的擴充）。這個函式是 Task 4 的 `PaginatedPaperView.vue` 呼叫 `generateHTML()` 時要用的同一份清單，確保兩邊排版規則不會日後跑掉。

- [ ] **Step 1: 建立 `paperExtensions.ts`**

```ts
import { Link } from '@tiptap/extension-link'
import { Subscript } from '@tiptap/extension-subscript'
import { Superscript } from '@tiptap/extension-superscript'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TextAlign } from '@tiptap/extension-text-align'
import { StarterKit } from '@tiptap/starter-kit'
import { AlignableImage } from '@/components/paper/alignableImage'
import { CitationMark } from '@/components/paper/citationMark'
import { ColoredTableCell, ColoredTableHeader } from '@/components/paper/coloredTableCell'

export function buildPaperContentExtensions (citationIndex: Record<string, number>) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Link.configure({ openOnClick: false, autolink: true }),
    Superscript,
    Subscript,
    Table.configure({ resizable: true }),
    TableRow,
    ColoredTableHeader,
    ColoredTableCell,
    AlignableImage.configure({ inline: false }),
    CitationMark.configure({ citationIndex }),
  ]
}
```

- [ ] **Step 2: 修改 `PaperEditor.vue` 的 import 區塊**

把現有第 398-416 行：

```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { CharacterCount } from '@tiptap/extension-character-count'
  import { Link } from '@tiptap/extension-link'
  import { Subscript } from '@tiptap/extension-subscript'
  import { Superscript } from '@tiptap/extension-superscript'
  import { Table } from '@tiptap/extension-table'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
  import { StarterKit } from '@tiptap/starter-kit'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import { ColoredTableCell, ColoredTableHeader } from '@/components/paper/coloredTableCell'
  import { ColumnResizeBalance } from '@/components/paper/columnResizeBalance'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'
```

改成：

```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { CharacterCount } from '@tiptap/extension-character-count'
  import { EditorContent, useEditor } from '@tiptap/vue-3'
  import { computed, onMounted, ref, watch } from 'vue'
  import { getProject, type VariableMapping } from '@/api/project'
  import { ColumnResizeBalance } from '@/components/paper/columnResizeBalance'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import { buildPaperContentExtensions } from '@/components/paper/paperExtensions'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'
```

- [ ] **Step 3: 修改 `useEditor` 的 `extensions` 陣列**

把現有第 531-545 行：

```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      CharacterCount.configure({}),
      Link.configure({ openOnClick: false, autolink: true }),
      Superscript,
      Subscript,
      Table.configure({ resizable: true }),
      TableRow,
      ColoredTableHeader,
      ColoredTableCell,
      ColumnResizeBalance,
      AlignableImage.configure({ inline: false }),
      CitationMark.configure({ citationIndex }),
    ],
```

改成：

```ts
    extensions: [
      ...buildPaperContentExtensions(citationIndex),
      CharacterCount.configure({}),
      ColumnResizeBalance,
    ],
```

- [ ] **Step 4: 手動驗證——編輯模式行為完全未變**

```bash
docker restart datamind-frontend
```

輪詢直到就緒：

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器開啟一篇論文頁面、切到編輯模式，確認：
- 輸入文字、插入表格、套用粗體/底線、點插入引註表格都正常（跟改動前行為一致）
- 瀏覽器 DevTools console 沒有新增的錯誤或警告（尤其是「duplicate extension names」這類 Tiptap 警告）

Expected: 所有互動跟改動前完全一致，console 乾淨。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/paperExtensions.ts frontend/src/components/paper/PaperEditor.vue
git commit -m "refactor: extract shared Tiptap content extensions for paper editor"
```

---

### Task 2: 分頁演算法 `paginateBlocks.ts` 與頁面組裝 `assemblePageHtml.ts`

**Files:**
- Create: `frontend/src/components/paper/paginateBlocks.ts`
- Create: `frontend/src/components/paper/assemblePageHtml.ts`

**Interfaces:**
- Consumes: 無（純函式，不依賴 DOM／其他任務的產出）
- Produces:
  - `export type PaginationBlockKind = 'content' | 'referenceHeading' | 'referenceItem'`
  - `export interface PaginationBlock { kind: PaginationBlockKind, html: string, height: number }`
  - `export function paginateBlocks(blocks: PaginationBlock[], maxHeightPx: number): PaginationBlock[][]`——貪婪分頁，依序把 `blocks` 塞進頁面陣列；`kind === 'referenceHeading'` 的區塊會嘗試跟緊接的下一個區塊（通常是第一個 `referenceItem`）綁在一起換頁，避免標題孤立在頁尾。單一區塊（或綁定的一組）比 `maxHeightPx` 還高時，仍會放進當頁（允許超出），不會被丟棄或攔腰切開。
  - `export function assemblePageHtml(blocks: PaginationBlock[]): string`——把一頁的 `PaginationBlock[]` 組成最終要塞進 `v-html` 的 HTML 字串；連續的 `referenceItem` 區塊會被包進同一個 `<ul class="references-list">`，其餘區塊（`content`、`referenceHeading`）直接依序輸出各自的 `html`。

Task 4 的 `PaginatedPaperView.vue` 會直接呼叫這兩個函式。

- [ ] **Step 1: 建立 `paginateBlocks.ts`**

```ts
export type PaginationBlockKind = 'content' | 'referenceHeading' | 'referenceItem'

export interface PaginationBlock {
  kind: PaginationBlockKind
  html: string
  height: number
}

export function paginateBlocks (blocks: PaginationBlock[], maxHeightPx: number): PaginationBlock[][] {
  const pages: PaginationBlock[][] = [[]]
  let currentHeight = 0

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i]
    if (!block) continue

    const group = [block]
    let groupHeight = block.height

    if (block.kind === 'referenceHeading') {
      const next = blocks[i + 1]
      if (next) {
        group.push(next)
        groupHeight += next.height
      }
    }

    let currentPage = pages[pages.length - 1]
    if (currentPage === undefined) continue
    const pageHasContent = currentHeight > 0

    if (pageHasContent && currentHeight + groupHeight > maxHeightPx) {
      pages.push([])
      currentHeight = 0
      currentPage = pages[pages.length - 1]
      if (currentPage === undefined) continue
    }

    for (const b of group) {
      currentPage.push(b)
      currentHeight += b.height
    }

    if (group.length > 1) i += 1
  }

  return pages
}
```

- [ ] **Step 2: 建立 `assemblePageHtml.ts`**

```ts
import type { PaginationBlock } from '@/components/paper/paginateBlocks'

export function assemblePageHtml (blocks: PaginationBlock[]): string {
  const parts: string[] = []
  let pendingItems: string[] = []

  const flushItems = () => {
    if (pendingItems.length === 0) return
    parts.push(`<ul class="references-list">${pendingItems.join('')}</ul>`)
    pendingItems = []
  }

  for (const block of blocks) {
    if (block.kind === 'referenceItem') {
      pendingItems.push(block.html)
      continue
    }
    flushItems()
    parts.push(block.html)
  }
  flushItems()

  return parts.join('')
}
```

- [ ] **Step 3: 手動驗證——用瀏覽器對 Vite dev server 動態 import 測試**

```bash
docker restart datamind-frontend
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器打開任一個已登入可見的頁面（例如 `/hub/dashboard`），在 DevTools console（或用 `javascript_tool`）依序執行：

```js
const mod = await import('/src/components/paper/paginateBlocks.ts')

// 一般换页
console.log(JSON.stringify(mod.paginateBlocks([
  { kind: 'content', html: '<p>A</p>', height: 100 },
  { kind: 'content', html: '<p>B</p>', height: 100 },
  { kind: 'content', html: '<p>C</p>', height: 100 },
], 250).map(p => p.map(b => b.html))))
// Expect: [["<p>A</p>","<p>B</p>"],["<p>C</p>"]]

// 孤兒控制：標題跟第一個項目綁在一起
console.log(JSON.stringify(mod.paginateBlocks([
  { kind: 'referenceHeading', html: '<h3>Refs</h3>', height: 40 },
  { kind: 'referenceItem', html: '<li>1</li>', height: 30 },
], 50).map(p => p.map(b => b.html))))
// Expect: [["<h3>Refs</h3>","<li>1</li>"]]

// 單一區塊超出頁面高度仍允許放置（已知限制）
console.log(JSON.stringify(mod.paginateBlocks([
  { kind: 'content', html: '<table>BIG</table>', height: 5000 },
], 931).map(p => p.map(b => b.html))))
// Expect: [["<table>BIG</table>"]]

// 換頁後孤兒控制仍成立
console.log(JSON.stringify(mod.paginateBlocks([
  { kind: 'content', html: '<p>A</p>', height: 900 },
  { kind: 'referenceHeading', html: '<h3>Refs</h3>', height: 40 },
  { kind: 'referenceItem', html: '<li>1</li>', height: 30 },
], 931).map(p => p.map(b => b.html))))
// Expect: [["<p>A</p>"],["<h3>Refs</h3>","<li>1</li>"]]
```

```js
const asm = await import('/src/components/paper/assemblePageHtml.ts')
console.log(asm.assemblePageHtml([
  { kind: 'content', html: '<p>A</p>', height: 10 },
  { kind: 'referenceHeading', html: '<h3>Refs</h3>', height: 10 },
  { kind: 'referenceItem', html: '<li>1</li>', height: 10 },
  { kind: 'referenceItem', html: '<li>2</li>', height: 10 },
]))
// Expect: '<p>A</p><h3>Refs</h3><ul class="references-list"><li>1</li><li>2</li></ul>'
```

Expected: 上述每一行 `console.log` 的輸出都跟註解裡的 Expect 完全一致。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/paper/paginateBlocks.ts frontend/src/components/paper/assemblePageHtml.ts
git commit -m "feat: add pagination bucketing algorithm and page HTML assembler"
```

---

### Task 3: 參考文獻區塊產生器 `buildReferenceBlocks.ts`

**Files:**
- Create: `frontend/src/components/paper/buildReferenceBlocks.ts`

**Interfaces:**
- Consumes: `formatCitation` from `@/utils/paper/formatCitation`（既有函式，簽章 `formatCitation(citation: Citation, style: CitationStyle, index: number): string`）
- Produces:
  - `export interface ReferenceBlockInput { kind: 'referenceHeading' | 'referenceItem', html: string }`
  - `export function buildReferenceBlocks(citations: Citation[], citationStyle: CitationStyle): ReferenceBlockInput[]`——`citations` 為空陣列時回傳 `[]`；否則回傳陣列第一個元素固定是 `kind: 'referenceHeading'` 的標題區塊，其餘依序是每篇引註各自的 `kind: 'referenceItem'` 區塊。

  這裡刻意不分 `ieee`／其他樣式使用不同的 `<ol>`/`<ul>` 標籤（跟 `ReferencesSection.vue` 目前的行為不同）：因為 `formatCitation` 的 IEEE 輸出本身已經把 `[數字]` 編號寫進文字內容，若每個項目各自包成一個 `<ol>` 好讓它們能分別被分頁到不同頁，瀏覽器原生的 `<ol>` 編號會在每一頁重新從 1 開始、跟文字裡的 `[數字]` 對不上。所以一律用 `<li>`，由 Task 4 的 `assemblePageHtml` 把同一頁裡連續的項目包進同一個 `<ul>`，可見的編號完全靠 `formatCitation` 內嵌的 `[數字]` 文字。

  Task 4 的 `PaginatedPaperView.vue` 會呼叫這個函式取得 blocks，再各自量測高度、組成 `PaginationBlock[]`。

- [ ] **Step 1: 建立 `buildReferenceBlocks.ts`**

```ts
import type { Citation, CitationStyle } from '@/constants/reportData'
import { formatCitation } from '@/utils/paper/formatCitation'

export interface ReferenceBlockInput {
  kind: 'referenceHeading' | 'referenceItem'
  html: string
}

export function buildReferenceBlocks (citations: Citation[], citationStyle: CitationStyle): ReferenceBlockInput[] {
  if (citations.length === 0) return []

  const blocks: ReferenceBlockInput[] = [
    { kind: 'referenceHeading', html: '<h3 class="references-title">參考文獻</h3>' },
  ]

  citations.forEach((citation, index) => {
    const text = escapeHtml(formatCitation(citation, citationStyle, index + 1))
    blocks.push({ kind: 'referenceItem', html: `<li>${text}</li>` })
  })

  return blocks
}

function escapeHtml (value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
```

- [ ] **Step 2: 手動驗證**

```bash
docker restart datamind-frontend
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

在瀏覽器 DevTools console（或 `javascript_tool`）執行：

```js
const mod = await import('/src/components/paper/buildReferenceBlocks.ts')

const citations = [
  { id: 'c1', title: 'Paper One', authors: 'Doe, J.', journal: '', year: 2024, snippet: '', arxivId: '2024.00001' },
  { id: 'c2', title: 'Paper Two', authors: 'Roe, R.', journal: 'Nature', year: 2023, snippet: '' },
]

console.log(JSON.stringify(mod.buildReferenceBlocks(citations, 'apa')))
// Expect: [{"kind":"referenceHeading","html":"<h3 class=\"references-title\">參考文獻</h3>"},{"kind":"referenceItem","html":"<li>Doe, J. (2024). Paper One. arXiv. https://arxiv.org/abs/2024.00001</li>"},{"kind":"referenceItem","html":"<li>Roe, R. (2023). Paper Two. Nature.</li>"}]

console.log(JSON.stringify(mod.buildReferenceBlocks([], 'apa')))
// Expect: []

console.log(JSON.stringify(mod.buildReferenceBlocks(citations, 'ieee')))
// Expect items 的 html 各自以 [1]、[2] 開頭，例如 "<li>[1] Doe, J., \"Paper One,\" arXiv:2024.00001, 2024.</li>"
```

Expected: 三個 `console.log` 輸出都符合上面 Expect 描述。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/buildReferenceBlocks.ts
git commit -m "feat: add reference-list block builder for paginated view"
```

---

### Task 4: 共用內容排版樣式、`PaginatedPaperView.vue`、串接 `PaperPage.vue`

**Files:**
- Create: `frontend/src/components/paper/paperContentTypography.css`
- Create: `frontend/src/components/paper/PaginatedPaperView.vue`
- Modify: `frontend/src/components/paper/PaperEditor.vue`（移除已抽到共用樣式表的 CSS 規則、改成 import 該樣式表）
- Modify: `frontend/src/views/PaperPage.vue`（檢視模式改用 `PaginatedPaperView`）

**Interfaces:**
- Consumes:
  - `buildPaperContentExtensions` from `@/components/paper/paperExtensions`（Task 1）
  - `PaginationBlock`, `paginateBlocks` from `@/components/paper/paginateBlocks`（Task 2）
  - `assemblePageHtml` from `@/components/paper/assemblePageHtml`（Task 2）
  - `buildReferenceBlocks` from `@/components/paper/buildReferenceBlocks`（Task 3）
  - `generateHTML` from `@tiptap/core`（既有依賴）
- Produces: `PaginatedPaperView.vue` 元件，props `{ content: JSONContent, citations: Citation[], citationStyle: CitationStyle }`，emits `citation-click: { citationId: string, target: HTMLElement }`（跟 `PaperEditor.vue` 現有 emit 簽章一致）。

- [ ] **Step 1: 建立共用內容排版樣式表 `paperContentTypography.css`**

這份樣式從 `PaperEditor.vue` 現有的 `:deep(.editor-content ...)` 規則中，抽出「不論編輯或檢視都該一樣」的排版／內容外觀規則（標題、段落、表格框線、圖片對齊、引註標記外觀）。互動限定的規則（縮放把手、選取儲存格高亮、`resize-cursor`）留在 `PaperEditor.vue` 自己的 scoped 樣式裡，不搬過來。

```css
.editor-content {
  font-size: 13.5px;
  line-height: 1.9;
  color: var(--color-ink);
}

.editor-content .ProseMirror {
  outline: none;
}

.editor-content h1,
.editor-content h2,
.editor-content h3 {
  margin: 0 0 10px;
  font-weight: 700;
  color: var(--color-ink);
}

.editor-content p {
  margin: 0 0 12px;
  text-align: justify;
  text-indent: 2em;
}

.editor-content table {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;
  margin: 12px 0;
}

.editor-content th,
.editor-content td {
  border: 1px solid #d8dbe3;
  padding: 6px 10px;
  position: relative;
  min-width: 1em;
}

.editor-content .tableWrapper {
  overflow-x: auto;
}

.editor-content img {
  display: block;
  max-width: 100%;
  height: auto;
}

.editor-content img[data-align='left'] {
  margin: 0 auto 0 0;
}

.editor-content img[data-align='center'] {
  margin: 0 auto;
}

.editor-content img[data-align='right'] {
  margin: 0 0 0 auto;
}

.citation-mark {
  background: #fdf0a8;
  padding: 1px 2px;
  border-radius: 3px;
}

.citation-mark::after {
  content: '[' attr(data-citation-number) ']';
  font-size: 0.85em;
  margin-left: 1px;
}
```

- [ ] **Step 2: 修改 `PaperEditor.vue`——改用共用樣式表**

在 `<script setup>` 的 import 區塊（Task 1 改完後的版本）新增一行 CSS import：

```ts
  import '@/components/paper/paperContentTypography.css'
```

放在其他 `@/components/paper/...` import 之前（依專案慣例的字母排序，CSS import 排在最前面即可）。

接著在 `<style scoped>` 區塊裡，把現有這一段（原檔案 707-810 行附近，Task 1 之後行號可能略有偏移，用內容比對）：

```css
  :deep(.editor-content img) {
    display: block;
    max-width: 100%;
    height: auto;
  }

  :deep(.editor-content img[data-align='left']) {
    margin: 0 auto 0 0;
  }

  :deep(.editor-content img[data-align='center']) {
    margin: 0 auto;
  }

  :deep(.editor-content img[data-align='right']) {
    margin: 0 0 0 auto;
  }

  :deep(.editor-content) {
    font-size: 13.5px;
    line-height: 1.9;
    color: var(--color-ink);
  }

  :deep(.editor-content .ProseMirror) {
    outline: none;
  }

  :deep(.editor-content h1),
  :deep(.editor-content h2),
  :deep(.editor-content h3) {
    margin: 0 0 10px;
    font-weight: 700;
    color: var(--color-ink);
  }

  :deep(.editor-content p) {
    margin: 0 0 12px;
    text-align: justify;
    text-indent: 2em;
  }

  :deep(.editor-content table) {
    border-collapse: collapse;
    table-layout: fixed;
    width: 100%;
    margin: 12px 0;
  }

  :deep(.editor-content th),
  :deep(.editor-content td) {
    border: 1px solid #d8dbe3;
    padding: 6px 10px;
    position: relative;
    min-width: 1em;
  }

  :deep(.editor-content .tableWrapper) {
    overflow-x: auto;
  }

  :deep(.editor-content .column-resize-handle) {
    position: absolute;
    right: -2px;
    top: 0;
    bottom: -2px;
    width: 4px;
    background-color: var(--color-accent);
    pointer-events: none;
  }

  :deep(.editor-content .ProseMirror.resize-cursor) {
    cursor: col-resize;
  }

  :deep(.editor-content th.selectedCell)::after,
  :deep(.editor-content td.selectedCell)::after {
    content: '';
    position: absolute;
    inset: 0;
    background: color-mix(in oklab, var(--color-accent) 30%, transparent);
    pointer-events: none;
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
```

改成（只留互動限定的規則，其餘已搬進共用樣式表）：

```css
  :deep(.editor-content .ProseMirror) {
    outline: none;
  }

  :deep(.editor-content .column-resize-handle) {
    position: absolute;
    right: -2px;
    top: 0;
    bottom: -2px;
    width: 4px;
    background-color: var(--color-accent);
    pointer-events: none;
  }

  :deep(.editor-content .ProseMirror.resize-cursor) {
    cursor: col-resize;
  }

  :deep(.editor-content th.selectedCell)::after,
  :deep(.editor-content td.selectedCell)::after {
    content: '';
    position: absolute;
    inset: 0;
    background: color-mix(in oklab, var(--color-accent) 30%, transparent);
    pointer-events: none;
  }

  .editor-content--readonly :deep(.citation-mark) {
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .editor-content--readonly :deep(.citation-mark:hover) {
    background: #fae57e;
  }
```

- [ ] **Step 3: 建立 `PaginatedPaperView.vue`**

```vue
<template>
  <div class="paginated-paper" @click="handleClick">
    <section v-for="(pageHtml, index) in pages" :key="index" class="a4-page">
      <div class="a4-page-content editor-content" v-html="pageHtml" />
      <div class="a4-page-number">第 {{ index + 1 }} 頁</div>
    </section>

    <div ref="measureContentRef" aria-hidden="true" class="measure-container editor-content" />
    <div ref="measureReferencesRef" aria-hidden="true" class="measure-container" />
  </div>
</template>

<script setup lang="ts">
  import type { JSONContent } from '@tiptap/core'
  import type { Citation, CitationStyle } from '@/constants/reportData'
  import { generateHTML } from '@tiptap/core'
  import { onMounted, ref, watch } from 'vue'
  import { assemblePageHtml } from '@/components/paper/assemblePageHtml'
  import { buildReferenceBlocks } from '@/components/paper/buildReferenceBlocks'
  import '@/components/paper/paperContentTypography.css'
  import { buildPaperContentExtensions } from '@/components/paper/paperExtensions'
  import { paginateBlocks, type PaginationBlock } from '@/components/paper/paginateBlocks'

  const A4_CONTENT_HEIGHT_PX = 931

  const props = defineProps<{
    content: JSONContent
    citations: Citation[]
    citationStyle: CitationStyle
  }>()

  const emit = defineEmits<{
    (e: 'citation-click', payload: { citationId: string, target: HTMLElement }): void
  }>()

  const pages = ref<string[]>([])
  const measureContentRef = ref<HTMLDivElement | null>(null)
  const measureReferencesRef = ref<HTMLDivElement | null>(null)

  function measureFlow (elements: HTMLElement[]): number[] {
    return elements.map((el, i) => {
      const next = elements[i + 1]
      return next ? next.offsetTop - el.offsetTop : el.getBoundingClientRect().height
    })
  }

  function computePages () {
    const contentContainer = measureContentRef.value
    const referencesContainer = measureReferencesRef.value
    if (!contentContainer || !referencesContainer) return

    const citationIndex: Record<string, number> = {}
    props.citations.forEach((citation, index) => {
      citationIndex[citation.id] = index + 1
    })

    const contentHtml = generateHTML(props.content, buildPaperContentExtensions(citationIndex))
    contentContainer.innerHTML = contentHtml
    const contentEls = Array.from(contentContainer.children) as HTMLElement[]
    const contentHeights = measureFlow(contentEls)
    const contentBlocks: PaginationBlock[] = contentEls.map((el, i) => ({
      kind: 'content',
      html: el.outerHTML,
      height: contentHeights[i] ?? el.getBoundingClientRect().height,
    }))

    const referenceInputs = buildReferenceBlocks(props.citations, props.citationStyle)
    let referenceBlocks: PaginationBlock[] = []

    if (referenceInputs.length > 0) {
      const heading = referenceInputs[0]!
      const items = referenceInputs.slice(1)
      referencesContainer.innerHTML = `${heading.html}<ul class="references-list">${items.map(item => item.html).join('')}</ul>`

      const headingEl = referencesContainer.children[0] as HTMLElement
      const listEl = referencesContainer.children[1] as HTMLElement
      const liEls = Array.from(listEl.children) as HTMLElement[]
      const flowHeights = measureFlow([headingEl, ...liEls])

      referenceBlocks = [
        { kind: 'referenceHeading', html: heading.html, height: flowHeights[0] ?? headingEl.getBoundingClientRect().height },
        ...items.map((item, i) => ({
          kind: 'referenceItem' as const,
          html: item.html,
          height: flowHeights[i + 1] ?? liEls[i]?.getBoundingClientRect().height ?? 0,
        })),
      ]
    }

    const bucketed = paginateBlocks([...contentBlocks, ...referenceBlocks], A4_CONTENT_HEIGHT_PX)
    pages.value = bucketed.filter(pageBlocks => pageBlocks.length > 0).map(pageBlocks => assemblePageHtml(pageBlocks))

    contentContainer.innerHTML = ''
    referencesContainer.innerHTML = ''
  }

  function handleClick (event: MouseEvent) {
    const target = (event.target as HTMLElement).closest<HTMLElement>('[data-citation-id]')
    const citationId = target?.getAttribute('data-citation-id')
    if (citationId && target) {
      emit('citation-click', { citationId, target })
    }
  }

  onMounted(computePages)

  watch(
    [() => props.content, () => props.citations, () => props.citationStyle],
    computePages,
    { deep: true },
  )
</script>

<style scoped>
.paginated-paper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 24px 0;
}

.a4-page {
  width: 794px;
  min-height: 1123px;
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(28, 33, 48, 0.12);
  padding: 96px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.a4-page-content {
  flex: 1;
}

.a4-page-number {
  margin-top: 16px;
  text-align: center;
  font-size: 11px;
  color: var(--text-secondary);
}

.measure-container {
  position: fixed;
  left: -99999px;
  top: 0;
  width: 602px;
  visibility: hidden;
  pointer-events: none;
}

:deep(.citation-mark) {
  cursor: pointer;
  transition: background 0.2s ease;
}

:deep(.citation-mark:hover) {
  background: #fae57e;
}

:deep(.references-title) {
  margin: 28px 0 12px;
  padding-top: 18px;
  border-top: 1px solid #d8dbe3;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-ink);
}

:deep(.references-list) {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.references-list li) {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--color-ink);
}
</style>
```

- [ ] **Step 4: 修改 `PaperPage.vue`——檢視模式改用 `PaginatedPaperView`**

把現有第 51-62 行：

```html
      <div v-else class="paper-body">
        <article class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
          <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" />
        </article>
      </div>
```

改成：

```html
      <div v-else class="paper-body">
        <article v-if="mode === 'view'" class="paper-sheet paper-sheet--paginated">
          <PaginatedPaperView
            :citation-style="report.citationStyle"
            :citations="report.citations"
            :content="report.content"
            @citation-click="onCitationClick"
          />
        </article>
        <article v-else class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="true"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
          <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" />
        </article>
      </div>
```

在 `<script setup>` 的 import 區塊加入：

```ts
  import PaginatedPaperView from '@/components/paper/PaginatedPaperView.vue'
```

（放在 `import PaperEditor from '@/components/paper/PaperEditor.vue'` 之前，維持字母排序。）

最後在 `<style scoped>` 區塊，把 `.paper-sheet` 樣式（現有第 298-308 行附近）改成分頁模式不套用卡片樣式（因為卡片感已經由內部每一張 `.a4-page` 提供）：

```css
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

  .paper-sheet--paginated {
    max-width: none;
    background: none;
    border: none;
    border-radius: 0;
    padding: 0;
  }
```

- [ ] **Step 5: 手動驗證——完整檢視/編輯模式行為**

```bash
docker restart datamind-frontend
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器打開一篇內容夠長（能跨頁）的論文頁面，確認：
1. **檢視模式**：內容以多張 A4 卡片呈現，每張卡片下方有「第 X 頁」，頁碼從 1 遞增不跳號；捲動可以看到多頁堆疊；點擊引註標記會跳出原本的 `CitationPopover`（跟改動前行為一致）。
2. 若該篇論文有參考文獻，確認參考文獻接在正文之後、如果排到某頁快滿會自動接續到下一頁，不會被硬生生截斷成一半。
3. 切到**編輯模式**：確認畫面回到原本連續捲動的單一卡片，排版、工具列、表格縮放、引註點擊都跟 Task 1 驗證時一致，沒有因為這次改動而受影響。
4. 瀏覽器 DevTools console 沒有錯誤。

Expected: 上述 4 點全部符合，兩種模式切換順暢。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/paper/paperContentTypography.css frontend/src/components/paper/PaginatedPaperView.vue frontend/src/components/paper/PaperEditor.vue frontend/src/views/PaperPage.vue
git commit -m "feat: paginate paper view mode into A4-sized pages"
```
