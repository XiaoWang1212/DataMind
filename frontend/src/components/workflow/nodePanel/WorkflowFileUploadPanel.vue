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
      <AppButton variant="primary" @click="browseFile">
        瀏覽檔案
      </AppButton>
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
  import AppButton from '@/components/ui/AppButton.vue'

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

  .upload-modal-dropzone {
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-lg);
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: var(--color-surface-alt);
    transition:
      border-color var(--dur-base) ease,
      background var(--dur-base) ease;
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
    font-weight: 500;
    color: var(--color-text);
  }

  .upload-modal-line2 {
    color: var(--color-secondary);
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
    color: var(--color-error-text);
    font-size: 13px;
    text-align: center;
  }

  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }
</style>
