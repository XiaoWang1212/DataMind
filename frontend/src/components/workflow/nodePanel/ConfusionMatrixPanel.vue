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

    <div v-if="groupedResults.length > 0" class="cm-tab-row">
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

      <div v-else-if="activeTab === 'matrix'" class="summary-empty">
        該抽樣沒有可用的混淆矩陣資訊。
      </div>

      <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
          <path class="cm-chart-line" :d="rocPath" fill="none" />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">FPR (0 – 1)</div>
        <div class="cm-chart-axis-y">TPR (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'roc'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <path class="cm-chart-line" :d="prPath" fill="none" />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">Recall (0 – 1)</div>
        <div class="cm-chart-axis-y">Precision (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'pr'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'calibration' && currentCalibrationCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentCalibrationCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
          <path class="cm-chart-line" :d="calibrationPath" fill="none" />
          <circle
            v-for="(point, index) in calibrationPoints"
            :key="`cal-point-${index}`"
            class="cm-chart-point"
            :cx="point.x"
            :cy="point.y"
            r="1.5"
          />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">平均預測機率 (0 – 1)</div>
        <div class="cm-chart-axis-y">實際正類比例 (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'calibration'" class="summary-empty">
        此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'perClass' && currentPerClassMetrics" class="cm-table-wrap">
        <table class="cm-table">
          <thead>
            <tr>
              <th class="cm-header">類別</th>
              <th class="cm-header">Precision</th>
              <th class="cm-header">Recall</th>
              <th class="cm-header">F1</th>
              <th class="cm-header">樣本數</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in perClassRows"
              :key="row.label"
              :class="{ 'cm-row--lowest': row.label === lowestF1Label }"
            >
              <td class="cm-cell">{{ row.label }}</td>
              <td class="cm-cell">{{ row.precision.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.recall.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.f1.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.support }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="activeTab === 'perClass'" class="summary-empty">
        該抽樣沒有可用的各類別指標資訊。
      </div>

      <div v-if="hasCurrentTabData" class="cm-insight-panel">
        <div class="cm-insight-header">AI 解讀</div>

        <p v-if="isCurrentTabInsightLoading" class="cm-insight-loading">生成中...</p>

        <template v-else-if="tabInsightError">
          <p class="cm-insight-error">{{ tabInsightError }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重試</button>
        </template>

        <template v-else-if="currentTabInsight">
          <p class="cm-insight-text">{{ currentTabInsight }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重新生成</button>
        </template>

        <template v-else>
          <p class="cm-insight-empty">點擊下方按鈕，讓 AI 針對目前的圖表/表格生成一段解讀。</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">AI 解讀</button>
        </template>
      </div>
    </div>

    <div v-if="groupedResults.length === 0" class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { fetchTabInsight } from '@/api/insight'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import { loadTabInsightFromStorage, saveTabInsightToStorage } from '@/composables/workflow/useWorkflowStorage.ts'

  interface ConfusionMatrixData {
    labels: string[]
    matrix: number[][]
  }

  interface RocPrCurveData {
    posLabel: string
    roc: { fpr: number[], tpr: number[] }
    pr: { precision: number[], recall: number[] }
  }

  interface CalibrationCurveData {
    posLabel: string
    probTrue: number[]
    probPred: number[]
  }

  interface PerClassMetricsData {
    labels: string[]
    precision: number[]
    recall: number[]
    f1: number[]
    support: number[]
  }

  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
    calibration_curve: CalibrationCurveData | null
    per_class_metrics: PerClassMetricsData | null
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
      roc_pr_curve: RocPrCurveData | null
      calibration_curve: CalibrationCurveData | null
      per_class_metrics: PerClassMetricsData | null
    }>
  }

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
    projectId?: string
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

  function parseCalibrationCurve (value: unknown): CalibrationCurveData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const posLabel = obj.pos_label
    const probTrue = obj.prob_true
    const probPred = obj.prob_pred
    if (typeof posLabel !== 'string') return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(probTrue) || !isNumberArray(probPred)) return null

    return { posLabel, probTrue, probPred }
  }

  function parsePerClassMetrics (value: unknown): PerClassMetricsData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const labels = obj.labels
    const precision = obj.precision
    const recall = obj.recall
    const f1 = obj.f1
    const support = obj.support

    if (!Array.isArray(labels) || !labels.every(l => typeof l === 'string')) return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(precision) || !isNumberArray(recall) || !isNumberArray(f1) || !isNumberArray(support)) {
      return null
    }
    if (
      precision.length !== labels.length
      || recall.length !== labels.length
      || f1.length !== labels.length
      || support.length !== labels.length
    ) {
      return null
    }

    return { labels, precision, recall, f1, support }
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
      const calibration_curve = parseCalibrationCurve(result.calibration_curve)
      const per_class_metrics = parsePerClassMetrics(result.per_class_metrics)
      return { model_name, split_name, confusion_matrix, roc_pr_curve, calibration_curve, per_class_metrics }
    }).filter(item =>
      item.confusion_matrix !== null
      || item.roc_pr_curve !== null
      || item.calibration_curve !== null
      || item.per_class_metrics !== null,
    ),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of confusionResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
        calibration_curve: result.calibration_curve,
        per_class_metrics: result.per_class_metrics,
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

  type TabKey = 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
    { key: 'calibration', label: '校準曲線' },
    { key: 'perClass', label: '各類別指標' },
  ]

  const currentRocPrCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve ?? null,
  )

  const currentCalibrationCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.calibration_curve ?? null,
  )

  const currentPerClassMetrics = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.per_class_metrics ?? null,
  )

  interface PerClassRow {
    label: string
    precision: number
    recall: number
    f1: number
    support: number
  }

  const perClassRows = computed<PerClassRow[]>(() => {
    const data = currentPerClassMetrics.value
    if (!data) return []
    return data.labels.map((label, i) => ({
      label,
      precision: data.precision[i]!,
      recall: data.recall[i]!,
      f1: data.f1[i]!,
      support: data.support[i]!,
    }))
  })

  const lowestF1Label = computed(() => {
    const rows = perClassRows.value
    if (rows.length === 0) return null
    return rows.reduce((min, row) => (row.f1 < min.f1 ? row : min)).label
  })

  const hasCurrentTabData = computed(() => {
    switch (activeTab.value) {
      case 'matrix': return currentMatrix.value !== null
      case 'roc':
      case 'pr': return currentRocPrCurve.value !== null
      case 'calibration': return currentCalibrationCurve.value !== null
      case 'perClass': return currentPerClassMetrics.value !== null
      default: return false
    }
  })

  const tabInsightCache = ref<Map<string, string>>(new Map())
  const tabInsightLoadingKey = ref<string | null>(null)
  const tabInsightError = ref<string | null>(null)

  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }

  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value),
  )

  const currentTabInsight = computed(() =>
    tabInsightCache.value.get(currentTabInsightKey.value) ?? null,
  )

  const isCurrentTabInsightLoading = computed(() => tabInsightLoadingKey.value === currentTabInsightKey.value)

  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
    }
  }

  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, selectedModel, selectedFold], () => {
    tabInsightError.value = null
    if (!props.projectId) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (tabInsightCache.value.has(key)) return
    const cached = loadTabInsightFromStorage(props.projectId, model, fold, tab)
    if (cached !== null) {
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
    }
  }, { immediate: true })

  const CHART_SIZE = 100
  const CHART_PADDING = 18

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

  const calibrationPath = computed(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return ''
    return buildLinePath(curve.probPred, curve.probTrue)
  })

  interface ChartPoint {
    x: number
    y: number
  }

  const calibrationPoints = computed<ChartPoint[]>(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return []
    return curve.probPred.map((x, i) => ({
      x: toChartX(x),
      y: toChartY(curve.probTrue[i]!),
    }))
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

  .cm-row--lowest .cm-cell {
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
    max-width: 260px;
    aspect-ratio: 1;
    display: block;
  }

  .cm-chart-label {
    font-size: 12px;
    color: var(--color-secondary);
    margin-bottom: 4px;
  }

  .cm-chart-diagonal {
    stroke: rgba(148, 163, 184, 0.5);
    stroke-width: 0.6;
    stroke-dasharray: 2 2;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-line {
    stroke: var(--color-accent);
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-point {
    fill: var(--color-accent);
    stroke: var(--color-surface);
    stroke-width: 0.5;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-tick {
    font-size: 7px;
    fill: var(--color-secondary);
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

  .cm-tab-row {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }

  .cm-tab-row > .cm-table-wrap,
  .cm-tab-row > .cm-chart-wrap,
  .cm-tab-row > .summary-empty {
    flex: 1 1 0;
    min-width: 0;
  }

  .cm-insight-panel {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 16px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .cm-insight-header {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-secondary);
  }

  .cm-insight-empty,
  .cm-insight-loading,
  .cm-insight-text {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink);
    line-height: 1.6;
  }

  .cm-insight-error {
    margin: 0;
    font-size: 13px;
    color: #b91c1c;
  }

  .cm-insight-btn {
    align-self: flex-start;
    padding: 7px 14px;
    border-radius: 8px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 35%, transparent);
    background: var(--color-accent);
    color: #fff;
    font-size: 13px;
    cursor: pointer;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
