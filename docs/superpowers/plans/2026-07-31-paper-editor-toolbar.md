# Paper Editor Toolbar Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance `PaperEditor.vue`'s toolbar with hyperlink, superscript/subscript, table row/column controls, live word count, and image insertion with alignment/preset-sizing — and restyle the toolbar as a glassmorphic floating dock matching `HubSidebar.vue`/`ModeSwitch.vue`, with hover tooltips on every button.

**Architecture:** All changes live in `frontend/src/components/paper/PaperEditor.vue` plus one new file, `frontend/src/components/paper/alignableImage.ts`, which extends Tiptap's `Image` extension with `align`/`width` node attributes. Four new Tiptap extension packages are added. The toolbar's visual redesign (glass dock CSS + a reusable `.toolbar-btn-wrap` tooltip pattern) lands first so every later task's new buttons follow the same established markup pattern instead of needing a second pass.

**Tech Stack:** Vue 3, Vuetify 4, Tiptap v3 (`@tiptap/vue-3`, `@tiptap/core`, `@tiptap/pm`, `@tiptap/starter-kit`), Tailwind CSS v4 tokens, Vite.

## Global Constraints

- New packages pinned to the same floor as existing Tiptap deps (`^3.29.x`): `@tiptap/extension-link`, `@tiptap/extension-superscript`, `@tiptap/extension-subscript`, `@tiptap/extension-character-count`
- Image resizing is preset-percentage buttons only (25% / 50% / 75% / 100%) — no drag-handle resize
- Reuse the project's existing glass CSS pattern (`rgba(255,255,255,0.5)` background + `backdrop-filter: blur(14px)` + `rgba(255,255,255,0.7)` border), already established in `frontend/src/components/hub/HubSidebar.vue` and `frontend/src/components/paper/ModeSwitch.vue` — do not invent a new visual language
- Tooltips are CSS-only (`.toolbar-btn-wrap` + `data-tooltip` + `::after`), not Vuetify's `v-tooltip` — keeps the glass aesthetic consistent, see design spec 段落 G
- Out of scope, do not implement: Word-style auto-pagination, APA/IEEE/MLA citation/bibliography management. The existing `CitationMark`/`CitationPopover` inline-citation mechanism is untouched.
- No unit test framework is configured in `frontend/` — verification is `npm run build` (type-check + build) and a live browser check via `npm run dev`, both run from the `frontend/` directory
- Design spec: `docs/superpowers/specs/2026-07-31-paper-editor-toolbar-design.md`

---

### Task 1: Toolbar glass-dock visual redesign

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue` (template: wrap every existing toolbar button in a tooltip wrapper; style: replace `.editor-toolbar`/`.toolbar-divider`, add `.toolbar-btn-wrap`)

**Interfaces:**
- Consumes: nothing new
- Produces: the `.toolbar-btn-wrap` + `data-tooltip="..."` wrapper pattern that every later task (2–6) uses for its new buttons — wrap every new `<v-btn>` the same way: `<div class="toolbar-btn-wrap" data-tooltip="⟨label⟩"><v-btn ... /></div>`

- [ ] **Step 1: Wrap every existing toolbar button with a tooltip wrapper**

Replace the entire toolbar `<div>` (currently `frontend/src/components/paper/PaperEditor.vue` lines 3–107):

```html
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
      <v-btn
        icon="mdi-chart-bar"
        size="small"
        variant="text"
        @click="chartDialogOpen = true"
      />
      <span class="toolbar-divider" />
      <v-btn icon="mdi-undo" size="small" variant="text" @click="editor?.chain().focus().undo().run()" />
      <v-btn icon="mdi-redo" size="small" variant="text" @click="editor?.chain().focus().redo().run()" />
    </div>
```

With:

```html
    <div v-if="editable" class="editor-toolbar">
      <div class="toolbar-btn-wrap" data-tooltip="粗體">
        <v-btn
          icon="mdi-format-bold"
          size="small"
          :variant="editor?.isActive('bold') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleBold().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="斜體">
        <v-btn
          icon="mdi-format-italic"
          size="small"
          :variant="editor?.isActive('italic') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleItalic().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="底線">
        <v-btn
          icon="mdi-format-underline"
          size="small"
          :variant="editor?.isActive('underline') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleUnderline().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="刪除線">
        <v-btn
          icon="mdi-format-strikethrough"
          size="small"
          :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleStrike().run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="標題 1">
        <v-btn
          icon="mdi-format-header-1"
          size="small"
          :variant="editor?.isActive('heading', { level: 1 }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="標題 2">
        <v-btn
          icon="mdi-format-header-2"
          size="small"
          :variant="editor?.isActive('heading', { level: 2 }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="標題 3">
        <v-btn
          icon="mdi-format-header-3"
          size="small"
          :variant="editor?.isActive('heading', { level: 3 }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="項目符號清單">
        <v-btn
          icon="mdi-format-list-bulleted"
          size="small"
          :variant="editor?.isActive('bulletList') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleBulletList().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="編號清單">
        <v-btn
          icon="mdi-format-list-numbered"
          size="small"
          :variant="editor?.isActive('orderedList') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleOrderedList().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="引用">
        <v-btn
          icon="mdi-format-quote-close"
          size="small"
          :variant="editor?.isActive('blockquote') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleBlockquote().run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="靠左對齊">
        <v-btn
          icon="mdi-format-align-left"
          size="small"
          :variant="editor?.isActive({ textAlign: 'left' }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().setTextAlign('left').run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="置中對齊">
        <v-btn
          icon="mdi-format-align-center"
          size="small"
          :variant="editor?.isActive({ textAlign: 'center' }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().setTextAlign('center').run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="靠右對齊">
        <v-btn
          icon="mdi-format-align-right"
          size="small"
          :variant="editor?.isActive({ textAlign: 'right' }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().setTextAlign('right').run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="左右對齊">
        <v-btn
          icon="mdi-format-align-justify"
          size="small"
          :variant="editor?.isActive({ textAlign: 'justify' }) ? 'tonal' : 'text'"
          @click="editor?.chain().focus().setTextAlign('justify').run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="插入表格">
        <v-btn
          icon="mdi-table-plus"
          size="small"
          variant="text"
          @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="插入圖表">
        <v-btn
          icon="mdi-chart-bar"
          size="small"
          variant="text"
          @click="chartDialogOpen = true"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="復原">
        <v-btn icon="mdi-undo" size="small" variant="text" @click="editor?.chain().focus().undo().run()" />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="重做">
        <v-btn icon="mdi-redo" size="small" variant="text" @click="editor?.chain().focus().redo().run()" />
      </div>
    </div>
```

- [ ] **Step 2: Replace the toolbar CSS with the glass-dock treatment**

Replace:

```css
  .editor-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: var(--color-surface);
  }

  .toolbar-divider {
    width: 1px;
    height: 20px;
    margin: 0 4px;
    background: #d8dbe3;
  }
```

With:

```css
  .editor-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 8px 10px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255, 255, 255, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.6),
      0 6px 20px rgba(28, 33, 48, 0.12);
  }

  .toolbar-divider {
    width: 1px;
    height: 20px;
    margin: 0 5px;
    background: rgba(28, 33, 48, 0.15);
  }

  .toolbar-btn-wrap {
    position: relative;
  }

  .toolbar-btn-wrap::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    background: #1c2130;
    color: #fff;
    font-size: 10px;
    padding: 3px 7px;
    border-radius: 5px;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
    z-index: 5;
  }

  .toolbar-btn-wrap:hover::after {
    opacity: 1;
  }

  .toolbar-btn-wrap :deep(.v-btn:hover) {
    transform: translateY(-2px);
  }
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode (e.g. `/paper?project=<id>` then switch to 編輯 mode).

Expected: toolbar renders as a rounded, translucent, blurred floating dock. Hovering any button lifts it slightly and shows a dark tooltip label above it matching the button's function. All existing functionality (bold, headings, lists, alignment, insert table, insert chart, undo/redo) still works exactly as before.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: restyle paper editor toolbar as a glassmorphic dock with tooltips"
```

---

### Task 2: General image insertion with alignment and preset sizing

**Files:**
- Create: `frontend/src/components/paper/alignableImage.ts`
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: the `.toolbar-btn-wrap` pattern from Task 1
- Produces: `AlignableImage` (exported from `alignableImage.ts`, a Tiptap node extension named `'image'` with `align: 'left' | 'center' | 'right'` and `width: string` attributes) — Task 6's `CharacterCount` extension doesn't interact with this, but any future task touching image markup should import `AlignableImage` from this file, not `@tiptap/extension-image` directly

- [ ] **Step 1: Create the AlignableImage extension**

Create `frontend/src/components/paper/alignableImage.ts`:

```ts
import { Image } from '@tiptap/extension-image'

export const AlignableImage = Image.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      align: {
        default: 'center',
        parseHTML: element => element.getAttribute('data-align') || 'center',
        renderHTML: attributes => ({
          'data-align': attributes.align,
        }),
      },
      width: {
        default: '100%',
        parseHTML: element => element.style.width || '100%',
        renderHTML: attributes => ({
          style: `width: ${attributes.width}`,
        }),
      },
    }
  },
})
```

- [ ] **Step 2: Swap the `Image` extension for `AlignableImage`**

Replace:

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
```

With:

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
  import { ref, watch } from 'vue'
  import { AlignableImage } from '@/components/paper/alignableImage'
  import { CitationMark } from '@/components/paper/citationMark'
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
```

Replace:

```ts
      Image.configure({ inline: false }),
```

With:

```ts
      AlignableImage.configure({ inline: false }),
```

- [ ] **Step 3: Add the file input ref and change handler**

Replace:

```ts
  const chartDialogOpen = ref(false)

  function handleInsertChart (dataUrl: string) {
    editor.value?.chain().focus().setImage({ src: dataUrl, alt: '工作流程模型比對圖表' }).run()
  }
```

With:

```ts
  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)

  function handleInsertChart (dataUrl: string) {
    editor.value?.chain().focus().setImage({ src: dataUrl, alt: '工作流程模型比對圖表' }).run()
  }

  function handleImageFileChange (event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const dataUrl = reader.result as string
      editor.value?.chain().focus().setImage({ src: dataUrl, align: 'center', width: '100%' }).run()
    }
    reader.readAsDataURL(file)
    input.value = ''
  }
```

- [ ] **Step 4: Split the toolbar into a normal view and an image-context view**

Replace the toolbar `<div>` produced by Task 1 (the `<div v-if="editable" class="editor-toolbar">...</div>` block):

```html
    <div v-if="editable" class="editor-toolbar">
```

With:

```html
    <template v-if="editable">
      <div v-if="editor?.isActive('image')" class="editor-toolbar">
        <div class="toolbar-btn-wrap" data-tooltip="靠左對齊">
          <v-btn
            icon="mdi-format-align-left"
            size="small"
            :variant="editor?.isActive('image', { align: 'left' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { align: 'left' }).run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="置中對齊">
          <v-btn
            icon="mdi-format-align-center"
            size="small"
            :variant="editor?.isActive('image', { align: 'center' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { align: 'center' }).run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="靠右對齊">
          <v-btn
            icon="mdi-format-align-right"
            size="small"
            :variant="editor?.isActive('image', { align: 'right' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { align: 'right' }).run()"
          />
        </div>
        <span class="toolbar-divider" />
        <div class="toolbar-btn-wrap" data-tooltip="25%">
          <v-btn
            size="small"
            :variant="editor?.isActive('image', { width: '25%' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { width: '25%' }).run()"
          >
            25%
          </v-btn>
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="50%">
          <v-btn
            size="small"
            :variant="editor?.isActive('image', { width: '50%' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { width: '50%' }).run()"
          >
            50%
          </v-btn>
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="75%">
          <v-btn
            size="small"
            :variant="editor?.isActive('image', { width: '75%' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { width: '75%' }).run()"
          >
            75%
          </v-btn>
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="100%">
          <v-btn
            size="small"
            :variant="editor?.isActive('image', { width: '100%' }) ? 'tonal' : 'text'"
            @click="editor?.chain().focus().updateAttributes('image', { width: '100%' }).run()"
          >
            100%
          </v-btn>
        </div>
      </div>

      <div v-else class="editor-toolbar">
```

Then, immediately before the toolbar's closing `</div>` (right after the 重做/redo wrapper, still inside the `v-else` branch), insert the insert-image button before the insert-chart button:

Replace:

```html
      <div class="toolbar-btn-wrap" data-tooltip="插入表格">
        <v-btn
          icon="mdi-table-plus"
          size="small"
          variant="text"
          @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="插入圖表">
```

With:

```html
      <div class="toolbar-btn-wrap" data-tooltip="插入表格">
        <v-btn
          icon="mdi-table-plus"
          size="small"
          variant="text"
          @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="插入圖片">
        <v-btn icon="mdi-image-plus" size="small" variant="text" @click="imageFileInputRef?.click()" />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="插入圖表">
```

Finally, close the `<template>` wrapper: replace the toolbar's closing tag

```html
    </div>

    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <InsertChartDialog
      v-model="chartDialogOpen"
      :project-id="projectId"
      @insert="handleInsertChart"
    />
  </div>
</template>
```

With:

```html
      </div>
    </template>

    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <InsertChartDialog
      v-model="chartDialogOpen"
      :project-id="projectId"
      @insert="handleInsertChart"
    />

    <input
      ref="imageFileInputRef"
      accept="image/*"
      class="hidden-file-input"
      type="file"
      @change="handleImageFileChange"
    >
  </div>
</template>
```

- [ ] **Step 5: Add CSS for image alignment and the hidden file input**

Add to the `<style scoped>` block, after the `.toolbar-btn-wrap :deep(.v-btn:hover)` rule added in Task 1:

```css
  .hidden-file-input {
    display: none;
  }

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
```

- [ ] **Step 6: Install the confirmed packages and verify the build**

Run (from `frontend/`): `npm install @tiptap/extension-link @tiptap/extension-superscript @tiptap/extension-subscript @tiptap/extension-character-count`

(These four packages are installed together now because they're a single `npm install` invocation touching `package.json`/`package-lock.json`; Tasks 3, 4, and 6 each use one of `extension-link`/`extension-superscript`+`extension-subscript`/`extension-character-count` respectively but the dependency is already present after this step.)

Run: `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 7: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode.

Expected: clicking "插入圖片" opens a file picker; selecting an image inserts it centered at 100% width. Clicking the image switches the toolbar to the align/size controls; clicking 靠左對齊/靠右對齊 moves the image; clicking 25%/50%/75% shrinks it. Clicking outside the image restores the normal toolbar. Inserting a chart via "插入圖表" (existing feature) still works and the chart image is also alignable/resizable through the same image-context toolbar.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/paper/alignableImage.ts frontend/src/components/paper/PaperEditor.vue frontend/package.json frontend/package-lock.json
git commit -m "feat: add image insertion with alignment and preset sizing to paper editor"
```

---

### Task 3: Hyperlink support

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: the `.toolbar-btn-wrap` pattern from Task 1; the `v-else` toolbar branch structure from Task 2
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Import the Link extension and add it to the editor**

Replace:

```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { Table } from '@tiptap/extension-table'
```

With:

```ts
  import type { JSONContent } from '@tiptap/core'
  import type { Citation } from '@/constants/reportData'
  import { Link } from '@tiptap/extension-link'
  import { Table } from '@tiptap/extension-table'
```

Replace:

```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }),
```

With:

```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Link.configure({ openOnClick: false, autolink: true }),
      Table.configure({ resizable: true }),
```

- [ ] **Step 2: Add the link draft state and helper functions**

Replace:

```ts
  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)
```

With:

```ts
  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)
  const linkUrlDraft = ref('')

  function openLinkMenu () {
    linkUrlDraft.value = editor.value?.getAttributes('link').href ?? ''
  }

  function applyLink () {
    if (!linkUrlDraft.value) return
    editor.value?.chain().focus().extendMarkRange('link').setLink({ href: linkUrlDraft.value }).run()
  }

  function removeLink () {
    editor.value?.chain().focus().unsetLink().run()
    linkUrlDraft.value = ''
  }
```

- [ ] **Step 3: Add the link toolbar button with its popover**

Replace:

```html
      <div class="toolbar-btn-wrap" data-tooltip="刪除線">
        <v-btn
          icon="mdi-format-strikethrough"
          size="small"
          :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleStrike().run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="標題 1">
```

With:

```html
      <div class="toolbar-btn-wrap" data-tooltip="刪除線">
        <v-btn
          icon="mdi-format-strikethrough"
          size="small"
          :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleStrike().run()"
        />
      </div>
      <v-menu :close-on-content-click="false" location="bottom">
        <template #activator="{ props: menuProps }">
          <div class="toolbar-btn-wrap" data-tooltip="插入連結">
            <v-btn
              icon="mdi-link-variant"
              size="small"
              :variant="editor?.isActive('link') ? 'tonal' : 'text'"
              v-bind="menuProps"
              @click="openLinkMenu"
            />
          </div>
        </template>
        <v-card class="link-menu-card">
          <v-text-field
            v-model="linkUrlDraft"
            density="compact"
            hide-details
            label="網址"
            placeholder="https://"
          />
          <div class="link-menu-actions">
            <v-btn size="small" variant="text" @click="removeLink">移除連結</v-btn>
            <v-btn class="bg-accent" color="accent" size="small" @click="applyLink">套用</v-btn>
          </div>
        </v-card>
      </v-menu>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="標題 1">
```

- [ ] **Step 4: Add the link popover CSS**

Add to the `<style scoped>` block, after the `.hidden-file-input` rule added in Task 2:

```css
  .link-menu-card {
    padding: 12px;
    width: 260px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .link-menu-actions {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
  }
```

- [ ] **Step 5: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 6: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode.

Expected: selecting text and clicking 插入連結 opens a popover with a URL field; entering a URL and clicking 套用 turns the selection into a clickable-styled link. Clicking into that same linked text and reopening the popover shows the existing URL pre-filled. Clicking 移除連結 removes the link styling.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add hyperlink support to paper editor"
```

---

### Task 4: Superscript and subscript

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: the `.toolbar-btn-wrap` pattern from Task 1; the link button placement from Task 3
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Import the extensions and add them to the editor**

Replace:

```ts
  import { Link } from '@tiptap/extension-link'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
```

With:

```ts
  import { Link } from '@tiptap/extension-link'
  import { Subscript } from '@tiptap/extension-subscript'
  import { Superscript } from '@tiptap/extension-superscript'
  import { Table } from '@tiptap/extension-table'
  import { TableCell } from '@tiptap/extension-table-cell'
  import { TableHeader } from '@tiptap/extension-table-header'
  import { TableRow } from '@tiptap/extension-table-row'
  import { TextAlign } from '@tiptap/extension-text-align'
```

Replace:

```ts
      Link.configure({ openOnClick: false, autolink: true }),
      Table.configure({ resizable: true }),
```

With:

```ts
      Link.configure({ openOnClick: false, autolink: true }),
      Superscript,
      Subscript,
      Table.configure({ resizable: true }),
```

- [ ] **Step 2: Add the superscript/subscript toolbar buttons**

Replace the `</v-menu>` closing tag and the divider that follows it (from Task 3's Step 3):

```html
      </v-menu>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="標題 1">
```

With:

```html
      </v-menu>
      <div class="toolbar-btn-wrap" data-tooltip="上標">
        <v-btn
          icon="mdi-format-superscript"
          size="small"
          :variant="editor?.isActive('superscript') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleSuperscript().run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="下標">
        <v-btn
          icon="mdi-format-subscript"
          size="small"
          :variant="editor?.isActive('subscript') ? 'tonal' : 'text'"
          @click="editor?.chain().focus().toggleSubscript().run()"
        />
      </div>
      <span class="toolbar-divider" />
      <div class="toolbar-btn-wrap" data-tooltip="標題 1">
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode.

Expected: selecting text and clicking 上標 renders it as superscript (e.g. `x²`); clicking 下標 on other text renders it as subscript (e.g. `H₂O`). Both buttons highlight (tonal) when the cursor is inside superscript/subscript text.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add superscript and subscript to paper editor"
```

---

### Task 5: Table row/column controls

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: the `.toolbar-btn-wrap` pattern from Task 1; the insert-table button placement from Task 2
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Add the contextual table controls after the insert-table button**

Replace:

```html
      <div class="toolbar-btn-wrap" data-tooltip="插入表格">
        <v-btn
          icon="mdi-table-plus"
          size="small"
          variant="text"
          @click="editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()"
        />
      </div>
      <div class="toolbar-btn-wrap" data-tooltip="插入圖片">
```

With:

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
      <div class="toolbar-btn-wrap" data-tooltip="插入圖片">
```

- [ ] **Step 2: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 3: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode.

Expected: with the cursor outside any table, only 插入表格/插入圖片/插入圖表 show (no row/column buttons). Clicking 插入表格 then placing the cursor inside the new table reveals 新增列/刪除列/新增欄/刪除欄. Clicking each button correctly adds/removes a row or column. Moving the cursor back outside the table hides the four buttons again.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add contextual table row/column controls to paper editor"
```

---

### Task 6: Live word count

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Import CharacterCount and add it to the editor**

Replace:

```ts
  import { Link } from '@tiptap/extension-link'
```

With:

```ts
  import { CharacterCount } from '@tiptap/extension-character-count'
  import { Link } from '@tiptap/extension-link'
```

Replace:

```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Link.configure({ openOnClick: false, autolink: true }),
```

With:

```ts
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      CharacterCount.configure({}),
      Link.configure({ openOnClick: false, autolink: true }),
```

- [ ] **Step 2: Add the status bar to the template**

Replace:

```html
    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <InsertChartDialog
```

With:

```html
    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <div v-if="editable" class="editor-status-bar">
      字數：{{ editor?.storage.characterCount.words() ?? 0 }}
    </div>

    <InsertChartDialog
```

- [ ] **Step 3: Add the status bar CSS**

Add to the `<style scoped>` block, after the `.link-menu-actions` rule added in Task 3:

```css
  .editor-status-bar {
    font-size: 11px;
    color: var(--color-secondary);
    text-align: right;
    padding: 0 4px;
  }
```

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Live browser check**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode.

Expected: a right-aligned "字數：N" line appears below the editor content and updates immediately as text is typed or deleted. Switching to 檢視 (view) mode hides the status bar (matches the existing `v-if="editable"` toolbar behavior).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: add live word count to paper editor"
```

---

### Task 7: Full verification pass

**Files:**
- No file modifications — this task only verifies the combined state of Tasks 1–6.

**Interfaces:**
- Consumes: the completed state of Tasks 1–6
- Produces: nothing (terminal task)

- [ ] **Step 1: Verify the build and lint both succeed**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

Run (from `frontend/`): `npm run lint`
Expected: exits 0, no errors.

- [ ] **Step 2: Live browser walkthrough of every feature together**

Run (from `frontend/`): `npm run dev`. Open the paper editor in edit mode and, in one continuous pass:

1. Confirm the toolbar renders as the glass dock with working hover tooltips on every button (Task 1).
2. Insert an image via 插入圖片, align it right, resize it to 50% (Task 2).
3. Select text, insert a link via 插入連結, confirm it's clickable-styled; reopen the popover on that text and confirm the URL is pre-filled (Task 3).
4. Apply superscript to one word and subscript to another (Task 4).
5. Insert a table, add a row and a column, then delete a row and a column; confirm the four buttons disappear when the cursor leaves the table (Task 5).
6. Confirm the word count updates as you type anywhere in the document (Task 6).
7. Insert a chart via the existing 插入圖表 flow and confirm it still works and is also alignable via the image-context toolbar.
8. Switch to 檢視 (view) mode and confirm the toolbar and status bar disappear, the document renders read-only, and existing citation-click behavior (`CitationMark`/`CitationPopover`) still works.

Expected: all of the above work with no console errors.

- [ ] **Step 3: Stop the dev server after checking**

Stop the `npm run dev` process started in Step 2.

---

## Plan Self-Review

**Spec coverage:** 段落 A (packages) → Task 2 Step 6. 段落 B (image insert/align/size) → Task 2. 段落 C (link) → Task 3. 段落 D (superscript/subscript) → Task 4. 段落 E (table controls) → Task 5. 段落 F (word count) → Task 6. 段落 G (glass dock + tooltips) → Task 1.

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" — every step shows complete before/after code, exact commands, and exact expected output.

**Type consistency:** `AlignableImage` (Task 2) is the single node named `'image'` used by every later `editor?.isActive('image', {...})`/`updateAttributes('image', {...})` call in Tasks 2 and by the pre-existing `handleInsertChart`. `linkUrlDraft`/`openLinkMenu`/`applyLink`/`removeLink` (Task 3) are used consistently in the template and script. `imageFileInputRef`/`handleImageFileChange` (Task 2) match between the `ref` declaration, the `<input ref="...">` binding, and the `@click`/`@change` handlers.
