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
      </div>

      <div
        v-for="group in ciGroups"
        :key="group.model"
        class="ci-model-block"
      >
        <div class="ci-model-block__name">{{ group.model }}</div>

        <div
          v-for="split in group.splits"
          :key="split.split_name"
          class="ci-split"
        >
          <div class="ci-split__label">{{ split.split_name }}</div>

          <div class="ci-table">
            <div class="ci-table__header">
              <span>指標</span>
              <span class="ci-table__num">CI Lower</span>
              <span class="ci-table__num">Value</span>
              <span class="ci-table__num">CI Upper</span>
            </div>
            <div
              v-for="m in split.metrics"
              :key="m.metric"
              class="ci-table__row"
            >
              <span class="ci-table__metric">{{ m.metric }}</span>
              <span class="ci-table__num ci-table__num--lo">{{ fmt(m.ci_lower) }}</span>
              <span class="ci-table__num ci-table__num--val">{{ fmt(m.value) }}</span>
              <span class="ci-table__num ci-table__num--hi">{{ fmt(m.ci_upper) }}</span>
            </div>
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
  import { computed } from 'vue'

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
    color: var(--color-secondary);
  }

  /* ── 模型區塊 ── */
  .ci-model-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    background: color-mix(in oklab, var(--color-accent) 3%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    border-radius: var(--radius-md);
  }

  .ci-model-block__name {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-accent);
  }

  /* ── Split ── */
  .ci-split {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ci-split__label {
    font-size: 11px;
    font-weight: 500;
    color: var(--color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
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
