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

    <div v-if="groupedResults.length > 0" class="cm-tabs">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="cm-tab"
        :class="{ 'cm-tab--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'matrix' && currentMatrix" class="cm-table-wrap">
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

    <div v-else-if="activeTab === 'matrix' && groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>

    <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
      <svg class="cm-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line class="cm-chart-diagonal" x1="4" y1="96" x2="96" y2="4" />
        <path class="cm-chart-line" :d="rocPath" fill="none" />
      </svg>
      <div class="cm-chart-axis-x">FPR (0 – 1)</div>
      <div class="cm-chart-axis-y">TPR (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'roc' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出）。
    </div>

    <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
      <svg class="cm-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path class="cm-chart-line" :d="prPath" fill="none" />
      </svg>
      <div class="cm-chart-axis-x">Recall (0 – 1)</div>
      <div class="cm-chart-axis-y">Precision (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'pr' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出）。
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

  interface RocPrCurveData {
    posLabel: string
    roc: { fpr: number[], tpr: number[] }
    pr: { precision: number[], recall: number[] }
  }

  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
      roc_pr_curve: RocPrCurveData | null
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

  function parseRocPrCurve (value: unknown): RocPrCurveData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const posLabel = obj.pos_label
    const roc = obj.roc
    const pr = obj.pr
    if (typeof posLabel !== 'string') return null
    if (!roc || typeof roc !== 'object' || !pr || typeof pr !== 'object') return null

    const rocObj = roc as Record<string, unknown>
    const prObj = pr as Record<string, unknown>
    const fpr = rocObj.fpr
    const tpr = rocObj.tpr
    const precision = prObj.precision
    const recall = prObj.recall

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(fpr) || !isNumberArray(tpr)) return null
    if (!isNumberArray(precision) || !isNumberArray(recall)) return null

    return {
      posLabel,
      roc: { fpr, tpr },
      pr: { precision, recall },
    }
  }

  const rawResults = computed<Array<Record<string, unknown>>>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []
    return results as Array<Record<string, unknown>>
  })

  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value.map(result => {
      const model_name = String(result.model_name ?? 'Unknown model')
      const split_name = String(result.split_name ?? 'Unknown split')
      const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
      const roc_pr_curve = parseRocPrCurve(result.roc_pr_curve)
      return { model_name, split_name, confusion_matrix, roc_pr_curve }
    }).filter(item => item.confusion_matrix !== null || item.roc_pr_curve !== null),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of confusionResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
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

  type TabKey = 'matrix' | 'roc' | 'pr'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
  ]

  const currentRocPrCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve ?? null,
  )

  const CHART_SIZE = 100
  const CHART_PADDING = 4

  function toChartX (value: number): number {
    return CHART_PADDING + value * (CHART_SIZE - CHART_PADDING * 2)
  }

  function toChartY (value: number): number {
    return CHART_SIZE - CHART_PADDING - value * (CHART_SIZE - CHART_PADDING * 2)
  }

  function buildLinePath (xs: number[], ys: number[]): string {
    if (xs.length === 0 || xs.length !== ys.length) return ''
    return xs
      .map((x, i) => `${i === 0 ? 'M' : 'L'} ${toChartX(x).toFixed(2)} ${toChartY(ys[i]!).toFixed(2)}`)
      .join(' ')
  }

  const rocPath = computed(() => {
    const curve = currentRocPrCurve.value
    if (!curve) return ''
    return buildLinePath(curve.roc.fpr, curve.roc.tpr)
  })

  const prPath = computed(() => {
    const curve = currentRocPrCurve.value
    if (!curve) return ''
    return buildLinePath(curve.pr.recall, curve.pr.precision)
  })

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

  .cm-tabs {
    display: flex;
    gap: 6px;
  }

  .cm-tab {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    background: transparent;
    color: var(--color-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .cm-tab--active {
    background: var(--color-accent);
    border-color: var(--color-accent);
    color: #fff;
  }

  .cm-chart-wrap {
    position: relative;
    padding: 12px 16px 28px 34px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .cm-chart {
    width: 100%;
    height: 260px;
    display: block;
  }

  .cm-chart-diagonal {
    stroke: rgba(148, 163, 184, 0.5);
    stroke-width: 0.6;
    stroke-dasharray: 2 2;
  }

  .cm-chart-line {
    stroke: var(--color-accent);
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-axis-x {
    position: absolute;
    left: 50%;
    bottom: 6px;
    transform: translateX(-50%);
    font-size: 11px;
    color: var(--color-secondary);
  }

  .cm-chart-axis-y {
    position: absolute;
    left: 6px;
    top: 50%;
    transform: translateY(-50%) rotate(-90deg);
    transform-origin: left center;
    font-size: 11px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
