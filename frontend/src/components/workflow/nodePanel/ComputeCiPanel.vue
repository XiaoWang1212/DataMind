<template>
  <div class="ci-panel">
    <!-- 有執行結果：顯示 CI 數據 -->
    <template v-if="ciGroups.length > 0">
      <div class="ci-panel__header">
        <v-icon class="ci-panel__icon" icon="mdi-chart-bell-curve" size="22" />
        <div>
          <h4 class="ci-panel__title">Bootstrap 95% 信賴區間</h4>
          <p class="ci-panel__sub">{{ panelCaption }}</p>
        </div>
        <ResultTableActions
          v-if="currentSplitMetrics.length > 0"
          :filename="exportFilename"
          :headers="exportHeaders"
          :rows="exportRows"
        />
      </div>

      <div class="ci-controls">
        <div class="ci-field">
          <span class="ci-field__label">模型</span>
          <CustomSelect
            v-model="selectedModel"
            class="ci-select"
            :options="modelOptions"
          />
        </div>
        <div v-if="viewMode === 'fold'" class="ci-field">
          <span class="ci-field__label">fold</span>
          <CustomSelect
            v-model="selectedFold"
            class="ci-select"
            :options="foldOptions"
          />
        </div>
      </div>

      <div class="ci-tabs">
        <button
          type="button"
          class="ci-tab"
          :class="{ 'ci-tab--active': viewMode === 'fold' }"
          @click="viewMode = 'fold'"
        >
          單一 Fold
        </button>
        <button
          type="button"
          class="ci-tab"
          :class="{ 'ci-tab--active': viewMode === 'summary' }"
          @click="viewMode = 'summary'"
        >
          跨 Fold 摘要
        </button>
      </div>

      <div v-if="displayRows.length > 0" class="ci-forest">
        <div class="ci-forest__axis">
          <span
            v-for="t in AXIS_TICKS"
            :key="t"
            class="ci-forest__axis-tick"
            :style="{ left: `${t * 100}%` }"
          >{{ t }}</span>
        </div>

        <div
          v-for="row in displayRows"
          :key="row.metric"
          class="ci-forest__row"
          :class="{ 'ci-forest__row--widest': row.highlighted }"
        >
          <div class="ci-forest__label">
            {{ row.metric }}
            <span v-if="row.highlighted" class="ci-forest__badge">{{ rowBadgeLabel }}</span>
          </div>

          <div class="ci-forest__track">
            <span
              v-for="t in AXIS_TICKS"
              :key="t"
              class="ci-forest__gridline"
              :style="{ left: `${t * 100}%` }"
            />
            <div
              class="ci-forest__bar"
              :style="{ left: `${pct(row.lo)}%`, width: `${pct(row.hi) - pct(row.lo)}%` }"
            />
            <div class="ci-forest__dot" :style="{ left: `${pct(row.marker)}%` }" />
          </div>

          <div class="ci-forest__value">
            {{ row.primaryLabel }}
            <span class="ci-forest__ci-range">{{ row.secondaryLabel }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- 尚無結果：顯示靜態介紹 -->
    <template v-else>
      <div class="ci-info__header">
        <v-icon class="ci-info__icon" icon="mdi-chart-bell-curve" size="22" />
        <div>
          <h4 class="ci-info__title">Bootstrap 信賴區間</h4>
          <p class="ci-info__sub">
            用重抽樣方式估算每個評估指標的 95% 信賴區間，適合需要量化不確定性的學術場景。
          </p>
        </div>
      </div>

      <div class="ci-info__notice">
        <v-icon icon="mdi-alert-outline" size="16" />
        <p>計算時間會顯著增加，建議模型確認後再開啟；請至 <strong>Settings</strong> 節點啟用或停用。</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import ResultTableActions from '@/components/common/ResultTableActions.vue'

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
  }>()

  interface MetricRow {
    metric: string
    value: number | null
    ci_lower: number | null
    ci_upper: number | null
  }

  interface SplitGroup {
    split_name: string
    metrics: MetricRow[]
  }

  interface ModelGroup {
    model: string
    splits: SplitGroup[]
  }

  function fmt (v: number | null): string {
    if (v == null || !Number.isFinite(v)) return '—'
    return v.toFixed(3)
  }

  const ciGroups = computed<ModelGroup[]>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []

    // 只取有 ci_lower 或 ci_upper 的 result
    const ciResults = (results as Array<Record<string, unknown>>).filter(r => {
      const metrics = r.metrics
      if (!Array.isArray(metrics)) return false
      return (metrics as Array<Record<string, unknown>>).some(
        m => m.ci_lower != null || m.ci_upper != null,
      )
    })
    if (ciResults.length === 0) return []

    // 以 model_name 分組，再以 split_name 分組
    const modelMap = new Map<string, Map<string, MetricRow[]>>()
    for (const r of ciResults) {
      const model = String(r.model_name ?? '')
      const split = String(r.split_name ?? '')
      const metrics = (r.metrics as Array<Record<string, unknown>>)
        .filter(m => m.ci_lower != null || m.ci_upper != null)
        .map(m => ({
          metric: String(m.metric),
          value: m.value != null ? Number(m.value) : null,
          ci_lower: m.ci_lower != null ? Number(m.ci_lower) : null,
          ci_upper: m.ci_upper != null ? Number(m.ci_upper) : null,
        }))

      if (!modelMap.has(model)) modelMap.set(model, new Map())
      modelMap.get(model)!.set(split, metrics)
    }

    return Array.from(modelMap.entries()).map(([model, splitMap]) => ({
      model,
      splits: Array.from(splitMap.entries()).map(([split_name, metrics]) => ({
        split_name,
        metrics,
      })),
    }))
  })

  // 每個模型每個 fold 都是一張獨立的表，一次全部攤開會變成長到滑不完的清單，
  // 改成跟 ConfusionMatrixPanel 一樣的模型/fold 下拉選單，一次只顯示一張表
  const selectedModel = ref('')
  const selectedFold = ref('')

  const modelOptions = computed(() =>
    ciGroups.value.map(g => ({ value: g.model, label: g.model })),
  )

  const currentModelGroup = computed(() =>
    ciGroups.value.find(g => g.model === selectedModel.value) ?? null,
  )

  const foldOptions = computed(() =>
    (currentModelGroup.value?.splits ?? []).map(s => ({ value: s.split_name, label: s.split_name })),
  )

  const currentSplitMetrics = computed(() =>
    currentModelGroup.value?.splits.find(s => s.split_name === selectedFold.value)?.metrics ?? [],
  )

  const exportHeaders = ['指標', 'CI Lower', 'Value', 'CI Upper']

  const exportRows = computed(() =>
    currentSplitMetrics.value.map(m => [m.metric, fmt(m.ci_lower), fmt(m.value), fmt(m.ci_upper)]),
  )

  const exportFilename = computed(() => `bootstrap_ci_${selectedModel.value}_${selectedFold.value}`)

  // 這裡的指標都是 0–1 尺度（AUC/準確率/precision/recall/F1...），直接乘 100 當百分比座標用
  const AXIS_TICKS = [0, 0.25, 0.5, 0.75, 1]

  function pct (v: number | null): number {
    if (v == null || !Number.isFinite(v)) return 0
    return Math.max(0, Math.min(1, v)) * 100
  }

  // 標出信賴區間最寬（最不確定）的指標，比起一排數字，這是使用者實際想先看到的重點
  const widestCiMetric = computed(() => {
    const metrics = currentSplitMetrics.value
    let widest: MetricRow | null = null
    let widestSpan = -1
    for (const m of metrics) {
      if (m.ci_lower == null || m.ci_upper == null) continue
      const span = m.ci_upper - m.ci_lower
      if (span > widestSpan) {
        widestSpan = span
        widest = m
      }
    }
    return widest?.metric ?? null
  })

  // 單一 fold 的信賴區間寬窄，其實會隨切分方式跳動——單看一個 fold「區間最寬」不代表這個指標
  // 真的不穩定。跨 fold 摘要把同一個模型的所有 fold 疊在一起看兩件事：
  // (1) 這個指標平均信賴區間有多寬（跨 fold 都偏寬，才是真的不穩，不是雜訊）
  // (2) 實際數值本身在不同切分之間跳動多大（模型對切分方式敏不敏感）
  interface SummaryRow {
    metric: string
    avgCiWidth: number | null
    minValue: number | null
    maxValue: number | null
    meanValue: number | null
  }

  type ViewMode = 'fold' | 'summary'
  const viewMode = ref<ViewMode>('fold')

  const crossFoldSummary = computed<SummaryRow[]>(() => {
    const splits = currentModelGroup.value?.splits ?? []
    const byMetric = new Map<string, { widths: number[], values: number[] }>()

    for (const split of splits) {
      for (const m of split.metrics) {
        if (!byMetric.has(m.metric)) byMetric.set(m.metric, { widths: [], values: [] })
        const entry = byMetric.get(m.metric)!
        if (m.ci_lower != null && m.ci_upper != null) {
          entry.widths.push(m.ci_upper - m.ci_lower)
        }
        if (m.value != null) {
          entry.values.push(m.value)
        }
      }
    }

    const mean = (nums: number[]): number | null =>
      nums.length > 0 ? nums.reduce((a, b) => a + b, 0) / nums.length : null

    const rows = Array.from(byMetric.entries()).map(([metric, { widths, values }]) => ({
      metric,
      avgCiWidth: mean(widths),
      minValue: values.length > 0 ? Math.min(...values) : null,
      maxValue: values.length > 0 ? Math.max(...values) : null,
      meanValue: mean(values),
    }))

    // 平均信賴區間最寬的排最前面——這才是真正值得留意的重點，不用自己心算 10 個 fold
    return rows.sort((a, b) => (b.avgCiWidth ?? -1) - (a.avgCiWidth ?? -1))
  })

  const leastStableMetric = computed(() => crossFoldSummary.value[0]?.metric ?? null)

  interface ForestRow {
    metric: string
    lo: number | null
    hi: number | null
    marker: number | null
    highlighted: boolean
    primaryLabel: string
    secondaryLabel: string
  }

  // 「單一 fold」跟「跨 fold 摘要」畫的是同一種橫向誤差棒圖，只是每列的數字來源不同，
  // 統一轉成同一種列資料，圖表模板就不用為兩種模式各刻一份
  const displayRows = computed<ForestRow[]>(() => {
    if (viewMode.value === 'fold') {
      return currentSplitMetrics.value.map(m => ({
        metric: m.metric,
        lo: m.ci_lower,
        hi: m.ci_upper,
        marker: m.value,
        highlighted: m.metric === widestCiMetric.value,
        primaryLabel: fmt(m.value),
        secondaryLabel: `(${fmt(m.ci_lower)}–${fmt(m.ci_upper)})`,
      }))
    }
    return crossFoldSummary.value.map(s => ({
      metric: s.metric,
      lo: s.minValue,
      hi: s.maxValue,
      marker: s.meanValue,
      highlighted: s.metric === leastStableMetric.value,
      primaryLabel: fmt(s.meanValue),
      secondaryLabel: `範圍 ${fmt(s.minValue)}–${fmt(s.maxValue)}・平均寬度 ${fmt(s.avgCiWidth)}`,
    }))
  })

  const rowBadgeLabel = computed(() => (viewMode.value === 'fold' ? '區間最寬' : '最不穩定'))

  const panelCaption = computed(() => {
    if (viewMode.value === 'fold') {
      return '圓點是實際數值、橫線是 95% 信賴區間；區間越寬代表這個指標的估計越不穩定，'
        + '標黃色的是這組結果裡區間最寬的指標。'
    }
    return '圓點是這個模型所有 fold 的平均值、橫線是實際數值在各 fold 之間的範圍；'
      + '範圍越寬代表這個指標越容易隨切分方式跳動，標黃色的是平均信賴區間最寬（最不穩定）的指標。'
  })

  // 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
  watch(ciGroups, groups => {
    if (groups.length === 0) {
      selectedModel.value = ''
      return
    }
    if (!groups.some(g => g.model === selectedModel.value)) {
      selectedModel.value = groups[0]!.model
    }
  }, { immediate: true })

  // 換模型（或結果載入）時，fold 一律重置為該模型的第一個
  watch(currentModelGroup, group => {
    const splits = group?.splits ?? []
    selectedFold.value = splits[0]?.split_name ?? ''
  }, { immediate: true })
</script>

<style scoped>
  .ci-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* ── 有結果：header ── */
  .ci-panel__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .ci-panel__header > div:nth-child(2) {
    flex: 1;
  }

  .ci-panel__icon {
    flex-shrink: 0;
    color: var(--color-accent);
  }

  .ci-panel__title {
    margin: 0 0 2px;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .ci-panel__sub {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    color: var(--color-secondary);
  }

  /* ── 模型／fold 選擇 ── */
  .ci-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .ci-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .ci-field__label {
    font-size: 13px;
    color: var(--color-ink-soft);
    white-space: nowrap;
  }

  .ci-select {
    width: 160px;
  }

  /* ── 檢視模式切換 ── */
  .ci-tabs {
    display: flex;
    gap: 6px;
  }

  .ci-tab {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--color-border-strong);
    background: transparent;
    color: var(--color-ink-soft);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  /* 實色底另用 --color-ink-solid：ink 在深色主題是淺藍，配淺色文字會看不見 */
  .ci-tab--active {
    background: var(--color-ink-solid);
    border-color: var(--color-ink);
    color: var(--color-inverted);
  }

  /* ── 森林圖（forest plot） ── */
  .ci-forest {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .ci-forest__axis {
    position: relative;
    height: 14px;
    margin: 0 108px 0 138px;
  }

  .ci-forest__axis-tick {
    position: absolute;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--color-secondary);
  }

  .ci-forest__row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 0;
  }

  .ci-forest__label {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 130px;
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ci-forest__row--widest .ci-forest__label {
    color: var(--color-warning-text);
  }

  .ci-forest__badge {
    flex-shrink: 0;
    padding: 1px 5px;
    border-radius: 999px;
    background: color-mix(in oklab, var(--color-warning) 15%, transparent);
    color: var(--color-warning-text);
    font-size: 9px;
    font-weight: 600;
    white-space: nowrap;
  }

  .ci-forest__track {
    position: relative;
    flex: 1;
    height: 20px;
  }

  .ci-forest__gridline {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: color-mix(in oklab, var(--color-text) 8%, transparent);
  }

  .ci-forest__bar {
    position: absolute;
    top: 50%;
    height: 3px;
    transform: translateY(-50%);
    border-radius: 2px;
    background: color-mix(in oklab, var(--color-accent) 45%, transparent);
  }

  .ci-forest__row--widest .ci-forest__bar {
    background: color-mix(in oklab, var(--color-warning) 55%, transparent);
  }

  .ci-forest__dot {
    position: absolute;
    top: 50%;
    width: 8px;
    height: 8px;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: var(--color-accent);
    border: 2px solid var(--color-surface);
  }

  .ci-forest__row--widest .ci-forest__dot {
    background: var(--color-warning);
  }

  .ci-forest__value {
    width: 100px;
    flex-shrink: 0;
    text-align: right;
    font-size: 12px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: var(--color-text);
  }

  .ci-forest__ci-range {
    margin-left: 4px;
    font-size: 11px;
    font-weight: 400;
    color: var(--color-secondary);
  }

  /* ── 無結果：靜態介紹 ── */
  .ci-info__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .ci-info__icon {
    flex-shrink: 0;
    color: var(--color-accent);
  }

  .ci-info__title {
    margin: 0 0 2px;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .ci-info__sub {
    margin: 0;
    font-size: 12px;
    color: var(--color-secondary);
  }

  .ci-info__notice {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: color-mix(in oklab, var(--color-warning) 8%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-warning) 25%, transparent);
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--color-warning-text);
    line-height: 1.5;
  }

  .ci-info__notice p {
    margin: 0;
  }

  .ci-info__notice strong {
    font-weight: 600;
  }
</style>
