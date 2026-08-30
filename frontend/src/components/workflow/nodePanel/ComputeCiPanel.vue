<template>
  <div class="ci-panel">
    <!-- 有執行結果：顯示 CI 數據 -->
    <template v-if="ciGroups.length > 0">
      <div class="ci-panel__header">
        <v-icon class="ci-panel__icon" icon="mdi-chart-bell-curve" size="22" />
        <div>
          <h4 class="ci-panel__title">Bootstrap 95% 信賴區間</h4>
          <p class="ci-panel__sub">
            圓點是實際數值、橫線是 95% 信賴區間；區間越寬代表這個指標的估計越不穩定，
            標黃色的是這組結果裡區間最寬的指標。
          </p>
        </div>
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

      <div v-if="currentSplitMetrics.length > 0" class="ci-forest">
        <div class="ci-forest__axis">
          <span
            v-for="t in AXIS_TICKS"
            :key="t"
            class="ci-forest__axis-tick"
            :style="{ left: `${t * 100}%` }"
          >{{ t }}</span>
        </div>

        <div
          v-for="m in currentSplitMetrics"
          :key="m.metric"
          class="ci-forest__row"
          :class="{ 'ci-forest__row--widest': m.metric === widestCiMetric }"
        >
          <div class="ci-forest__label">
            {{ m.metric }}
            <span v-if="m.metric === widestCiMetric" class="ci-forest__badge">區間最寬</span>
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
              :style="{ left: `${pct(m.ci_lower)}%`, width: `${pct(m.ci_upper) - pct(m.ci_lower)}%` }"
            />
            <div class="ci-forest__dot" :style="{ left: `${pct(m.value)}%` }" />
          </div>

          <div class="ci-forest__value">
            {{ fmt(m.value) }}
            <span class="ci-forest__ci-range">({{ fmt(m.ci_lower) }}–{{ fmt(m.ci_upper) }})</span>
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
    background: rgba(0, 0, 0, 0.06);
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
