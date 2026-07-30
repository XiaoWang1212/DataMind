<template>
  <div class="workflow-file-upload-panel">
    <div
      class="upload-modal-dropzone"
      :class="{ 'upload-modal-dropzone--active': dragActive }"
      @dragenter.prevent="onDragEnter"
      @dragleave.prevent="onDragLeave"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <div class="upload-modal-icon">⇪</div>
      <div class="upload-modal-line1">將檔案拖曳至此處</div>
      <div class="upload-modal-line2">或點擊下方按鈕選擇 CSV 檔案</div>
      <input
        ref="fileInput"
        accept=".csv,.xlsx,.xls,text/csv"
        hidden
        type="file"
        @change="onFileChange"
      >
      <button class="upload-modal-button" type="button" @click="browseFile">
        瀏覽檔案
      </button>
    </div>

    <div v-if="fileName" class="upload-modal-file">
      已選檔案：{{ fileName }}
      <div class="upload-modal-note">已載入資料，可重新上傳以更換內容。</div>
    </div>

    <div v-if="errorMessage" class="upload-modal-error">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
    readonly?: boolean
  }>()

  const emit = defineEmits<{
    (e: 'update:fileName', value: string): void
    (e: 'update:file', value: File): void
  }>()

  const fileInput = ref<HTMLInputElement | null>(null)
  const errorMessage = ref('')
  const dragActive = ref(false)

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')

  function browseFile () {
    if (props.readonly) return
    fileInput.value?.click()
  }

  function onDragEnter () {
    if (props.readonly) return
    dragActive.value = true
  }

  function onDragLeave () {
    if (props.readonly) return
    dragActive.value = false
  }

  function onDrop (event: DragEvent) {
    if (props.readonly) return
    dragActive.value = false
    const files = event.dataTransfer?.files
    const file = files?.item(0)
    if (file) {
      loadFile(file)
    }
  }

  function onFileChange (event: Event) {
    if (props.readonly) return
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) {
      loadFile(file)
    }
  }

  function loadFile (file: File) {
    errorMessage.value = ''
    if (!file.name.toLowerCase().endsWith('.csv')) {
      errorMessage.value = '目前僅支援 CSV 檔案格式。'
      return
    }

    emit('update:file', file)
    emit('update:fileName', file.name)
  }
</script>

<style scoped>
  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed color-mix(in oklab, var(--color-accent) 28%, transparent);
    border-radius: 16px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__desc {
    margin: 0;
    color: var(--color-secondary);
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: var(--color-accent);
    background: color-mix(in oklab, var(--color-accent) 13%, transparent);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: var(--color-accent);
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .upload-modal-line2 {
    color: var(--color-secondary);
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .upload-modal-note {
    margin-top: 6px;
    color: var(--color-secondary);
    font-size: 12px;
    line-height: 1.4;
  }

  .upload-modal-error {
    color: #ef4444;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .upload-modal-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .upload-modal-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .upload-modal-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: var(--color-surface);
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    color: var(--color-ink);
  }

  .upload-modal-chart-subtitle {
    margin-top: 6px;
    color: var(--color-secondary);
    font-size: 12px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: minmax(75px, 1.4fr) 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: var(--color-ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--color-accent);
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: var(--color-ink);
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
    background: var(--color-surface);
    color: var(--color-ink);
  }

  .upload-modal-preview-table table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-ink);
  }

  .upload-modal-preview-table th {
    background: var(--color-surface);
    color: var(--color-ink);
  }

  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }
</style>
