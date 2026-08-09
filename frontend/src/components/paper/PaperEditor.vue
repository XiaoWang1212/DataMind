<template>
  <div class="paper-editor">
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
            icon
            size="small"
            :variant="editor?.isActive('strike') ? 'tonal' : 'text'"
            @click="editor?.chain().focus().toggleStrike().run()"
          >
            <StrikethroughIcon />
          </v-btn>
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
        <div
          class="toolbar-btn-wrap"
          :data-tooltip="hasVariableMapping ? '插入變數表格' : (mappingLoadError ? '無法載入欄位對應資料' : '尚未完成欄位對應')"
        >
          <v-btn
            :disabled="!hasVariableMapping"
            icon="mdi-table-account"
            size="small"
            variant="text"
            @click="insertVariableTable"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="插入圖片">
          <v-btn icon="mdi-image-plus" size="small" variant="text" @click="imageFileInputRef?.click()" />
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

      <div v-if="editor?.isActive('table')" class="editor-table-toolbar">
        <div class="toolbar-btn-wrap" data-tooltip="新增列（前）">
          <v-btn
            icon="mdi-table-row-plus-before"
            size="small"
            variant="text"
            @click="editor?.chain().focus().addRowBefore().run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="新增列（後）">
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
        <div class="toolbar-btn-wrap" data-tooltip="新增欄（前）">
          <v-btn
            icon="mdi-table-column-plus-before"
            size="small"
            variant="text"
            @click="editor?.chain().focus().addColumnBefore().run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="新增欄（後）">
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
        <span class="toolbar-divider" />
        <div v-if="editor?.can().mergeCells()" class="toolbar-btn-wrap" data-tooltip="合併儲存格">
          <v-btn
            icon="mdi-table-merge-cells"
            size="small"
            variant="text"
            @click="editor?.chain().focus().mergeCells().run()"
          />
        </div>
        <div v-if="editor?.can().splitCell()" class="toolbar-btn-wrap" data-tooltip="拆分儲存格">
          <v-btn
            icon="mdi-table-split-cell"
            size="small"
            variant="text"
            @click="editor?.chain().focus().splitCell().run()"
          />
        </div>
        <div class="toolbar-btn-wrap" data-tooltip="刪除表格">
          <v-btn
            icon="mdi-table-remove"
            size="small"
            variant="text"
            @click="editor?.chain().focus().deleteTable().run()"
          />
        </div>
        <v-menu location="bottom">
          <template #activator="{ props: menuProps }">
            <div class="toolbar-btn-wrap" data-tooltip="儲存格底色">
              <v-btn icon="mdi-format-color-fill" size="small" variant="text" v-bind="menuProps" />
            </div>
          </template>
          <v-card class="cell-color-menu-card">
            <button
              v-for="swatch in CELL_BACKGROUND_COLORS"
              :key="swatch.label"
              class="cell-color-swatch"
              :style="{ backgroundColor: swatch.value ?? '#ffffff' }"
              :title="swatch.label"
              type="button"
              @click="setCellBackgroundColor(swatch.value)"
            />
          </v-card>
        </v-menu>
      </div>
    </template>

    <EditorContent :editor="editor" class="editor-content" :class="{ 'editor-content--readonly': !editable }" />

    <div v-if="editable" class="editor-status-bar">
      字數：{{ editor?.storage.characterCount.characters() ?? 0 }}
    </div>

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

<script setup lang="ts">
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
  import InsertChartDialog from '@/components/paper/InsertChartDialog.vue'
  import StrikethroughIcon from '@/components/paper/StrikethroughIcon.vue'

  const props = defineProps<{
    modelValue: JSONContent
    editable: boolean
    citations: Citation[]
    projectId?: string
  }>()

  const chartDialogOpen = ref(false)
  const imageFileInputRef = ref<HTMLInputElement | null>(null)
  const linkUrlDraft = ref('')
  const projectColumnMapping = ref<Record<string, VariableMapping>>({})
  const mappingLoadError = ref(false)

  function normalizeColumnMapping (raw: Record<string, VariableMapping | string> | null | undefined): Record<string, VariableMapping> {
    const normalized: Record<string, VariableMapping> = {}
    if (!raw) return normalized
    for (const [key, value] of Object.entries(raw)) {
      normalized[key] = typeof value === 'string'
        ? { column: value, type: '' }
        : { column: value?.column ?? '', type: value?.type ?? '' }
    }
    return normalized
  }

  onMounted(async () => {
    if (!props.projectId) return
    try {
      const project = await getProject(Number(props.projectId))
      projectColumnMapping.value = normalizeColumnMapping(project.columnMapping)
    } catch {
      projectColumnMapping.value = {}
      mappingLoadError.value = true
    }
  })

  const hasVariableMapping = computed(
    () => Object.keys(projectColumnMapping.value).length > 0,
  )

  function escapeHtml (value: string): string {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
  }

  function insertVariableTable () {
    const rows = Object.entries(projectColumnMapping.value)
      .map(([name, info]) => `<tr><td>${escapeHtml(name)}</td><td></td><td>${escapeHtml(info.type || '型態未指定')}</td></tr>`)
      .join('')
    const html = `<table><tbody><tr><th>變數名稱</th><th>定義</th><th>型別</th></tr>${rows}</tbody></table>`
    editor.value?.chain().focus().insertContent(html).run()
  }

  const CELL_BACKGROUND_COLORS: { label: string, value: string | null }[] = [
    { label: '橘', value: '#fdecd2' },
    { label: '灰藍', value: '#e2e8f0' },
    { label: '淡黃', value: '#fdf6b2' },
    { label: '淡綠', value: '#dcf5e3' },
    { label: '無', value: null },
  ]

  function setCellBackgroundColor (color: string | null) {
    editor.value?.chain().focus().setCellAttribute('backgroundColor', color).run()
  }

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

  function handleInsertChart (dataUrl: string) {
    editor.value?.chain().focus().setImage({ src: dataUrl, alt: '工作流程模型比對圖表' }).run()
  }

  function handleImageFileChange (event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.addEventListener('load', () => {
      const dataUrl = reader.result as string
      editor.value?.chain().focus().setImage({ src: dataUrl }).updateAttributes('image', { align: 'center', width: '100%' }).run()
    })
    reader.readAsDataURL(file)
    input.value = ''
  }

  const emit = defineEmits<{
    (e: 'update:modelValue', content: JSONContent): void
    (e: 'citation-click', payload: { citationId: string, target: HTMLElement }): void
  }>()

  const citationIndex: Record<string, number> = {}
  for (const [index, citation] of props.citations.entries()) {
    citationIndex[citation.id] = index + 1
  }

  const editor = useEditor({
    content: props.modelValue,
    // 一律用 editable:true 建立編輯器：Table 擴充套件的欄位縮放功能（resizable）
    // 只在建立當下判斷 editor.isEditable 決定要不要註冊，之後用 setEditable()
    // 切換可編輯狀態不會補註冊。真正的可編輯狀態交給下面的 watch（immediate）同步。
    editable: true,
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
      AlignableImage.configure({ inline: false }),
      CitationMark.configure({ citationIndex }),
    ],
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
    onUpdate: ({ editor: instance }) => {
      emit('update:modelValue', instance.getJSON())
    },
  })

  watch(() => props.editable, value => {
    editor.value?.setEditable(value)
  }, { immediate: true })

  watch(() => props.modelValue, value => {
    if (!editor.value) return
    const current = JSON.stringify(editor.value.getJSON())
    if (current !== JSON.stringify(value)) {
      editor.value.commands.setContent(value, { emitUpdate: false })
    }
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
    padding: 8px 10px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.55);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.85);
    box-shadow:
      inset 0 1px 1px rgba(255, 255, 255, 0.75),
      inset 0 -1px 1px rgba(28, 33, 48, 0.04),
      0 2px 6px rgba(28, 33, 48, 0.06),
      0 10px 28px rgba(28, 33, 48, 0.14);
  }

  .editor-table-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 6px 10px;
    border-radius: 12px;
    background: color-mix(in oklab, var(--color-accent) 12%, rgba(255, 255, 255, 0.55));
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.85);
    box-shadow:
      inset 0 1px 1px rgba(255, 255, 255, 0.75),
      inset 0 -1px 1px rgba(28, 33, 48, 0.04),
      0 2px 6px rgba(28, 33, 48, 0.06),
      0 10px 28px rgba(28, 33, 48, 0.14);
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

  .hidden-file-input {
    display: none;
  }

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

  .cell-color-menu-card {
    padding: 10px;
    display: flex;
    gap: 8px;
  }

  .cell-color-swatch {
    width: 22px;
    height: 22px;
    border-radius: 5px;
    border: 1.5px solid rgba(28, 33, 48, 0.15);
    cursor: pointer;
  }

  .cell-color-swatch:hover {
    border-color: rgba(28, 33, 48, 0.4);
  }

  .editor-status-bar {
    font-size: 11px;
    color: var(--color-secondary);
    text-align: right;
    padding: 0 4px;
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
</style>
