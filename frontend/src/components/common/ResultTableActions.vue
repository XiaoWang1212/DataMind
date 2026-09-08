<template>
  <div class="result-table-actions">
    <button
      class="result-table-actions__btn"
      :class="{ 'result-table-actions__btn--error': copyState === 'error' }"
      :title="copyState === 'error' ? '複製失敗' : '複製表格'"
      type="button"
      @click="handleCopy"
    >
      <v-icon :icon="copyIcon" size="16" />
    </button>
    <div ref="exportWrapRef" class="result-table-actions__export-wrap">
      <button
        class="result-table-actions__btn"
        title="匯出"
        type="button"
        @click="exportMenuOpen = !exportMenuOpen"
      >
        <v-icon icon="mdi-download-outline" size="16" />
      </button>
      <div v-if="exportMenuOpen" class="result-table-actions__menu glass-menu">
        <button class="result-table-actions__menu-item" type="button" @click="handleExportExcel">
          <v-icon icon="mdi-file-excel-outline" size="15" />
          匯出 Excel
        </button>
        <button class="result-table-actions__menu-item" type="button" @click="handleExportCsv">
          <v-icon icon="mdi-file-delimited-outline" size="15" />
          匯出 CSV
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { copyTableToClipboard, exportTableToCsv, exportTableToExcel } from '@/utils/tableExport'

  const props = defineProps<{
    headers: string[]
    rows: Array<Array<string | number>>
    filename: string
  }>()

  type CopyState = 'idle' | 'copied' | 'error'

  const copyState = ref<CopyState>('idle')
  let resetTimer: ReturnType<typeof setTimeout> | undefined

  const copyIcon = computed(() => {
    if (copyState.value === 'copied') return 'mdi-check'
    if (copyState.value === 'error') return 'mdi-alert-outline'
    return 'mdi-content-copy'
  })

  function flashState (state: CopyState): void {
    copyState.value = state
    clearTimeout(resetTimer)
    resetTimer = setTimeout(() => {
      copyState.value = 'idle'
    }, 1500)
  }

  async function handleCopy (): Promise<void> {
    try {
      await copyTableToClipboard(props.headers, props.rows)
      flashState('copied')
    } catch {
      flashState('error')
    }
  }

  const exportMenuOpen = ref(false)
  const exportWrapRef = ref<HTMLElement | null>(null)

  function handleExportExcel (): void {
    exportTableToExcel(props.headers, props.rows, props.filename)
    exportMenuOpen.value = false
  }

  function handleExportCsv (): void {
    exportTableToCsv(props.headers, props.rows, props.filename)
    exportMenuOpen.value = false
  }

  function onDocPointer (e: PointerEvent): void {
    if (exportWrapRef.value?.contains(e.target as Node)) return
    exportMenuOpen.value = false
  }

  watch(exportMenuOpen, isOpen => {
    if (isOpen) document.addEventListener('pointerdown', onDocPointer, true)
    else document.removeEventListener('pointerdown', onDocPointer, true)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocPointer, true)
  })
</script>

<style scoped>
  .result-table-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .result-table-actions__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out);
  }

  @media (hover: hover) and (pointer: fine) {
    .result-table-actions__btn:hover {
      background: color-mix(in oklab, var(--color-ink) 8%, transparent);
      color: var(--color-ink);
    }
  }

  .result-table-actions__btn--error {
    color: var(--color-error-text, #dc2626);
  }

  .result-table-actions__export-wrap {
    position: relative;
  }

  .result-table-actions__menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 4px;
    min-width: 120px;
    border-radius: var(--radius-sm);
  }

  .result-table-actions__menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-text);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    white-space: nowrap;
  }

  @media (hover: hover) and (pointer: fine) {
    .result-table-actions__menu-item:hover {
      background: color-mix(in oklab, var(--color-ink) 10%, transparent);
    }
  }
</style>
