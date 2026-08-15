<template>
  <section class="confusion-matrix-panel">
    <div v-if="groupedResults.length > 0" class="cm-controls">
      <div class="cm-field">
        <span class="cm-field__label">模型</span>
        <CustomSelect
          v-model="selectedModel"
          class="cm-select"
          :options="modelOptions"
        />
      </div>
      <div class="cm-field">
        <span class="cm-field__label">fold</span>
        <CustomSelect
          v-model="selectedFold"
          class="cm-select"
          :options="foldOptions"
        />
      </div>
    </div>

    <div v-if="currentMatrix" class="cm-table-wrap">
      <table class="cm-table">
        <thead>
          <tr>
            <th class="cm-corner" />
            <th
              v-for="label in currentMatrix.labels"
              :key="`pred-${label}`"
              class="cm-header"
            >
              預測：{{ label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in currentMatrix.matrix" :key="`row-${rowIndex}`">
            <th class="cm-header cm-header--row">
              實際：{{ currentMatrix.labels[rowIndex] }}
            </th>
            <td
              v-for="(cell, colIndex) in row"
              :key="`cell-${rowIndex}-${colIndex}`"
              class="cm-cell"
              :class="{ 'cm-cell--diagonal': rowIndex === colIndex }"
            >
              {{ cell }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>

    <div v-else class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'

  interface ConfusionMatrixData {
    labels: string[]
    matrix: number[][]
  }

  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
    }>
  }

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
  }>()

  function parseConfusionMatrix (value: unknown): ConfusionMatrixData | null {
    if (!value || typeof value !== 'object') return null
    const labels = (value as Record<string, unknown>).labels
    const matrix = (value as Record<string, unknown>).matrix
    if (!Array.isArray(labels) || !Array.isArray(matrix)) return null
    if (!labels.every(l => typeof l === 'string')) return null
    if (!matrix.every(row => Array.isArray(row) && row.every(cell => typeof cell === 'number'))) return null
    return { labels: labels as string[], matrix: matrix as number[][] }
  }

  const rawResults = computed<Array<Record<string, unknown>>>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []
    return results as Array<Record<string, unknown>>
  })

  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value
      .map(result => {
        const model_name = String(result.model_name ?? 'Unknown model')
        const split_name = String(result.split_name ?? 'Unknown split')
        const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
        return { model_name, split_name, confusion_matrix }
      })
      .filter(item => item.confusion_matrix !== null),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of confusionResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
      }

      if (existing) {
        existing.splits.push(entry)
      } else {
        groups.set(result.model_name, {
          model_name: result.model_name,
          splits: [entry],
        })
      }
    }

    return Array.from(groups.values())
  })

  const selectedModel = ref('')
  const selectedFold = ref('')

  const modelOptions = computed(() =>
    groupedResults.value.map(g => ({ value: g.model_name, label: g.model_name })),
  )

  const currentModel = computed(() =>
    groupedResults.value.find(g => g.model_name === selectedModel.value) ?? null,
  )

  const foldOptions = computed(() =>
    (currentModel.value?.splits ?? []).map(s => ({ value: s.split_name, label: s.split_name })),
  )

  const currentMatrix = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.confusion_matrix ?? null,
  )

  // 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
  watch(groupedResults, groups => {
    if (groups.length === 0) {
      selectedModel.value = ''
      return
    }
    if (!groups.some(g => g.model_name === selectedModel.value)) {
      selectedModel.value = groups[0]!.model_name
    }
  }, { immediate: true })

  // 換模型（或結果載入）時，fold 一律重置為該模型的第一個
  watch(currentModel, model => {
    const splits = model?.splits ?? []
    selectedFold.value = splits[0]?.split_name ?? ''
  }, { immediate: true })
</script>

<style scoped>
  .confusion-matrix-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 0 0 16px;
  }

  .cm-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .cm-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .cm-field__label {
    font-size: 13px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .cm-select {
    width: 160px;
  }

  .cm-table-wrap {
    overflow-x: auto;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .cm-table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
  }

  .cm-corner {
    background: var(--color-surface);
  }

  .cm-header {
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 600;
    color: var(--color-secondary);
    white-space: nowrap;
    text-align: left;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-header--row {
    border-bottom: none;
    border-right: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-cell {
    padding: 11px 14px;
    text-align: center;
    color: var(--color-ink);
    font-variant-numeric: tabular-nums;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-cell--diagonal {
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    font-weight: 700;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
