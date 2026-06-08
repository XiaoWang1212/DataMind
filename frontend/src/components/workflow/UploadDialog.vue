<template>
  <div
    v-if="visible"
    class="upload-dialog-backdrop"
    @click.self="emit('close')"
  >
    <div class="upload-dialog-card">
      <div class="upload-dialog-header">
        <div>
          <button
            class="upload-dialog-close"
            type="button"
            @click="emit('close')"
          >
            ×
          </button>
          <h3>上傳模型檔案</h3>
          <p>將檔案拖曳到此處，或點擊瀏覽選擇模型檔案。</p>
        </div>
      </div>

      <div
        class="upload-dropzone"
        :class="{ 'upload-dropzone--active': dragActive }"
        @dragenter.prevent="dragActive = true"
        @dragleave.prevent="dragActive = false"
        @dragover.prevent
        @drop.prevent="handleDrop"
      >
        <div class="upload-dropzone__icon">⇪</div>
        <div class="upload-dropzone__text">Drop files here!</div>
        <label class="upload-dropzone__browse">
          瀏覽
          <input
            accept=".csv,.xlsx,.model"
            hidden
            type="file"
            @change="handleFileChange"
          >
        </label>
        <div v-if="selectedFile" class="upload-dropzone__file">
          已選檔案：{{ selectedFile.name }}
        </div>
      </div>

      <div class="upload-dialog-actions">
        <button
          class="btn btn-secondary"
          type="button"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="btn btn-primary"
          :disabled="!selectedFile"
          type="button"
          @click="handleConfirm"
        >
          上傳
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'

  const props = defineProps<{
    visible: boolean
  }>()

  const emit = defineEmits<{
    close: []
    confirm: [file: File]
  }>()

  const selectedFile = ref<File | null>(null)
  const dragActive = ref(false)

  watch(() => props.visible, (v) => {
    if (!v) { selectedFile.value = null; dragActive.value = false }
  })

  function handleFileChange(event: Event): void {
    const target = event.target as HTMLInputElement
    selectedFile.value = target.files?.[0] ?? null
  }

  function handleDrop(event: DragEvent): void {
    dragActive.value = false
    const files = event.dataTransfer?.files
    if (files && files.length > 0) selectedFile.value = files.item(0) ?? null
  }

  function handleConfirm(): void {
    if (!selectedFile.value) return
    emit('confirm', selectedFile.value)
    selectedFile.value = null
  }
</script>

<style scoped>
  .upload-dialog-backdrop {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(8px);
  }

  .upload-dialog-card {
    width: min(560px, calc(100% - 32px));
    border-radius: 20px;
    background: #ffffff;
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .upload-dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .upload-dialog-close {
    border: none;
    background: rgba(243, 244, 246, 0.9);
    width: 36px;
    height: 36px;
    border-radius: 999px;
    color: #1f2937;
    font-size: 18px;
    cursor: pointer;
  }

  .upload-dialog-card h3 {
    margin: 0;
    font-size: 20px;
  }

  .upload-dialog-card p {
    margin: 6px 0 0;
    color: #475569;
    font-size: 14px;
    line-height: 1.6;
  }

  .upload-dropzone {
    min-height: 210px;
    padding: 28px 20px;
    border: 2px dashed rgba(148, 163, 184, 0.8);
    border-radius: 18px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: rgba(236, 246, 255, 0.68);
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .upload-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.12);
  }

  .upload-dropzone__icon {
    font-size: 28px;
    color: #2563eb;
  }

  .upload-dropzone__text {
    font-size: 18px;
    color: #1f2937;
    font-weight: 600;
  }

  .upload-dropzone__browse {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 22px;
    border-radius: 999px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-dropzone__file {
    font-size: 13px;
    color: #475569;
  }

  .upload-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
</style>
