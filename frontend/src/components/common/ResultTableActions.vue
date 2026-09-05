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
    <button
      class="result-table-actions__btn"
      title="匯出 Excel"
      type="button"
      @click="handleExport"
    >
      <v-icon icon="mdi-file-excel-outline" size="16" />
    </button>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { copyTableToClipboard, exportTableToExcel } from '@/utils/tableExport'

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

  function handleExport (): void {
    exportTableToExcel(props.headers, props.rows, props.filename)
  }
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
</style>
