<template>
  <div
    class="drop-zone"
    :class="{ 'drop-zone--over': isDragOver, 'drop-zone--filled': modelValue }"
    @click="inputRef?.click()"
    @dragenter.prevent="onDragEnter"
    @dragleave.prevent="onDragLeave"
    @dragover.prevent
    @drop.prevent="onDrop"
  >
    <template v-if="modelValue">
      <AppButton
        v-if="removable"
        aria-label="移除檔案"
        class="dz-file-remove"
        icon-only
        variant="ghost"
        @click.stop="pick(null)"
      >
        <v-icon icon="mdi-close" size="16" />
      </AppButton>
      <div class="dz-file-head">
        <v-icon class="dz-file-icon" :icon="fileIcon" size="20" />
        <span class="dz-file-name" :title="modelValue.name">{{ modelValue.name }}</span>
      </div>
      <div class="dz-file-size">{{ formattedSize }}</div>
      <div class="dz-swap-hint">
        {{ isDragOver ? '放開以更換檔案' : '點擊或拖放可更換檔案' }}
      </div>
    </template>

    <template v-else>
      <v-icon class="dz-icon" :icon="icon" size="48" />
      <div class="dz-text">{{ isDragOver ? '放開以上傳檔案' : text }}</div>
      <div class="dz-hint">{{ hint }}</div>
    </template>

    <p v-if="rejectMessage" class="dz-reject">{{ rejectMessage }}</p>

    <input
      ref="inputRef"
      :accept="accept"
      hidden
      type="file"
      @change="onChange"
    >
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'

  const props = withDefaults(defineProps<{
    modelValue: File | null
    /** 逗號分隔的副檔名，例如 '.csv,.xlsx'。同時給 input 用與拖放驗證用 */
    accept: string
    /** 拒絕訊息裡的人話檔型，例如 'PDF'、'CSV、Excel'。沒給就從 accept 推 */
    acceptLabel?: string
    text: string
    hint: string
    icon: string
    fileIcon: string
    removable?: boolean
  }>(), {
    removable: true,
  })

  const emit = defineEmits<{
    'update:modelValue': [file: File | null]
  }>()

  const inputRef = ref<HTMLInputElement | null>(null)
  const isDragOver = ref(false)
  const rejectMessage = ref('')

  // dragleave 在滑鼠移到子元素時也會觸發，用進出計數才不會誤關
  let dragDepth = 0

  // 沒傳 acceptLabel 時退回副檔名，避免訊息出現 undefined
  const acceptText = computed(() =>
    props.acceptLabel
    ?? props.accept.split(',').map(s => s.trim().replace(/^\./, '').toUpperCase()).filter(Boolean).join('、'),
  )

  const formattedSize = computed(() => {
    const bytes = props.modelValue?.size ?? 0
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  })

  function isAccepted (file: File): boolean {
    const patterns = props.accept.split(',').map(s => s.trim().toLowerCase()).filter(Boolean)
    if (patterns.length === 0) return true
    const name = file.name.toLowerCase()
    return patterns.some(p => (p.startsWith('.') ? name.endsWith(p) : file.type === p))
  }

  function pick (file: File | null): void {
    rejectMessage.value = ''
    emit('update:modelValue', file)
  }

  function onDragEnter (): void {
    dragDepth += 1
    isDragOver.value = true
  }

  function onDragLeave (): void {
    dragDepth -= 1
    if (dragDepth <= 0) {
      dragDepth = 0
      isDragOver.value = false
    }
  }

  function onChange (e: Event): void {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    if (file) pick(file)
    // 清掉值，否則再選同一個檔案不會觸發 change
    input.value = ''
  }

  function onDrop (e: DragEvent): void {
    dragDepth = 0
    isDragOver.value = false
    const file = e.dataTransfer?.files[0]
    if (!file) return
    if (isAccepted(file)) {
      pick(file)
      return
    }
    // 拒絕時保留原本已選的檔案，拖錯一個檔不該把先前選好的弄丟
    rejectMessage.value = `僅接受 ${acceptText.value} 檔案`
  }
</script>

<style scoped>
  /* 空狀態與已選檔共用同一個尺寸，切換時版面不會跳 */
  .drop-zone {
    position: relative;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 198px;
    padding: 24px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface-alt);
    cursor: pointer;
    transition: border-color var(--dur-fast) var(--ease-out),
      background-color var(--dur-fast) var(--ease-out);
  }

  .drop-zone--filled {
    gap: 4px;
    border-color: var(--color-border);
    background: var(--color-surface);
  }

  /* 兩個 class 疊出權重，才蓋得過上面的 --filled */
  .drop-zone:hover,
  .drop-zone.drop-zone--over {
    border-color: var(--color-ink);
    background: color-mix(in oklab, var(--color-ink) 6%, var(--color-surface));
  }

  /* 拖到上方時再明顯一階，讓使用者知道可以放開 */
  .drop-zone.drop-zone--over {
    border-color: var(--color-ink);
    background: color-mix(in oklab, var(--color-ink) 12%, var(--color-surface));
    box-shadow: inset 0 0 0 1px var(--color-ink);
  }

  .dz-icon {
    margin-bottom: 4px;
    color: var(--color-ink-soft);
  }

  .dz-text {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .dz-hint {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .dz-file-head {
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
  }

  .dz-file-icon {
    flex-shrink: 0;
    color: var(--color-ink);
  }

  .dz-file-name {
    min-width: 0;
    overflow: hidden;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dz-file-size {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* 移出排版流釘在右上角，中間那疊才不會被它拉偏 */
  .drop-zone .dz-file-remove {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 32px;
    height: 32px;
    padding: 0;
  }

  /* 看到的圓維持 32px，往外擴一圈透明區把點擊範圍補到 44×44 */
  .drop-zone .dz-file-remove::after {
    content: '';
    position: absolute;
    inset: -6px;
  }

  /* hover 只變底色，圖示顏色不動（蓋掉 AppButton ghost 的 ink-soft → ink） */
  .drop-zone .dz-file-remove:hover:not(:disabled) {
    color: var(--color-ink-soft);
  }

  .dz-swap-hint {
    margin-top: 8px;
    font-size: 12px;
    color: var(--color-ink-soft);
    text-align: center;
  }

  .dz-reject {
    margin: 0;
    font-size: 12px;
    color: var(--color-error-text);
    text-align: center;
  }
</style>
