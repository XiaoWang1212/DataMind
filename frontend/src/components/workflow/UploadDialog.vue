<template>
  <div
    v-if="visible"
    class="upload-dialog-backdrop"
    @click.self="emit('close')"
  >
    <div class="upload-dialog-card">
      <div class="upload-dialog-header">
        <div>
          <AppButton
            aria-label="關閉"
            icon-only
            variant="ghost"
            @click="emit('close')"
          >
            <v-icon icon="mdi-close" size="18" />
          </AppButton>
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
        <AppButton variant="secondary" @click="emit('close')">
          取消
        </AppButton>
        <AppButton :disabled="!selectedFile" variant="primary" @click="handleConfirm">
          上傳
        </AppButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'

  const props = defineProps<{
    visible: boolean
  }>()

  const emit = defineEmits<{
    close: []
    confirm: [file: File]
  }>()

  const selectedFile = ref<File | null>(null)
  const dragActive = ref(false)

  watch(() => props.visible, v => {
    if (!v) {
      selectedFile.value = null
      dragActive.value = false
    }
  })

  function handleFileChange (event: Event): void {
    const target = event.target as HTMLInputElement
    selectedFile.value = target.files?.[0] ?? null
  }

  function handleDrop (event: DragEvent): void {
    dragActive.value = false
    const files = event.dataTransfer?.files
    if (files && files.length > 0) selectedFile.value = files.item(0) ?? null
  }

  function handleConfirm (): void {
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
    border-radius: var(--radius-lg);
    background: var(--color-surface);
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

  .upload-dialog-card h3 {
    margin: 0;
    font-size: 20px;
  }

  .upload-dialog-card p {
    margin: 6px 0 0;
    color: var(--color-secondary);
    font-size: 14px;
    line-height: 1.6;
  }

  .upload-dropzone {
    min-height: 210px;
    padding: 28px 20px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-lg);
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: var(--color-surface-alt);
    transition: border-color var(--dur-base) ease, background var(--dur-base) ease;
  }

  .upload-dropzone--active {
    border-color: var(--color-accent);
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
  }

  .upload-dropzone__icon {
    font-size: 28px;
    color: var(--color-accent);
  }

  .upload-dropzone__text {
    font-size: 18px;
    color: var(--color-text);
    font-weight: 500;
  }

  .upload-dropzone__browse {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 22px;
    border-radius: 999px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-dropzone__file {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .upload-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
</style>
