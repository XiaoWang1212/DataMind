<template>
  <div class="ci-panel">
    <!-- 有執行結果：顯示 CI 數據 -->
    <template v-if="ciGroups.length > 0">
      <div class="ci-panel__header">
        <v-icon class="ci-panel__icon" icon="mdi-chart-bell-curve" size="22" />
        <div>
          <h4 class="ci-panel__title">Bootstrap 95% 信賴區間</h4>
          <p class="ci-panel__sub">每個指標的 CI Lower / Value / CI Upper</p>
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
        <div class="ci-field">
          <span class="ci-field__label">fold</span>
          <CustomSelect
            v-model="selectedFold"
            class="ci-select"
            :options="foldOptions"
          />
        </div>
      </div>

      <div v-if="currentSplitMetrics.length > 0" class="ci-table">
        <div class="ci-table__header">
          <span>指標</span>
          <span class="ci-table__num">CI Lower</span>
          <span class="ci-table__num">Value</span>
          <span class="ci-table__num">CI Upper</span>
        </div>
        <div
          v-for="m in currentSplitMetrics"
          :key="m.metric"
          class="ci-table__row"
        >
          <span class="ci-table__metric">{{ m.metric }}</span>
          <span class="ci-table__num ci-table__num--lo">{{ fmt(m.ci_lower) }}</span>
          <span class="ci-table__num ci-table__num--val">{{ fmt(m.value) }}</span>
          <span class="ci-table__num ci-table__num--hi">{{ fmt(m.ci_upper) }}</span>
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

  /* ── 表格 ── */
  .ci-table {
    display: flex;
    flex-direction: column;
    gap: 1px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }

  .ci-table__header,
  .ci-table__row {
    display: grid;
    grid-template-columns: 1.6fr 1fr 1fr 1fr;
    font-size: 12px;
    padding: 5px 8px;
  }

  .ci-table__header {
    font-weight: 500;
    color: var(--color-secondary);
    background: var(--color-surface);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  .ci-table__header span:not(:first-child) {
    text-align: center;
  }

  .ci-table__row {
    background: var(--color-surface);
  }

  .ci-table__row:nth-child(even) {
    background: var(--color-surface);
  }

  .ci-table__metric {
    color: var(--color-secondary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ci-table__num {
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: var(--color-secondary);
  }

  .ci-table__num--val {
    font-weight: 500;
    color: var(--color-text);
  }

  .ci-table__num--lo,
  .ci-table__num--hi {
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
