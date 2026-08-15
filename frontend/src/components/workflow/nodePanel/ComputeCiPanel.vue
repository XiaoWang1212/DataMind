<template>
  <div class="ci-panel">
    <!-- 有執行結果：顯示 CI 數據 -->
    <template v-if="ciGroups.length > 0">
      <div class="ci-panel__header">
        <span class="ci-panel__icon">📊</span>
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
        <span class="ci-info__icon">📊</span>
        <div>
          <h4 class="ci-info__title">Bootstrap 信賴區間</h4>
          <p class="ci-info__sub">對每個評估指標計算 95% 信賴區間</p>
        </div>
      </div>

      <div class="ci-info__section">
        <h5 class="ci-info__section-title">這個節點做什麼？</h5>
        <p class="ci-info__text">
          使用 Bootstrap 重抽樣方法，對模型評估指標（AUC、F1、MCC 等）估算 95% 信賴區間，
          讓結果更具統計嚴謹性，適合學術論文或需要量化不確定性的場景。
        </p>
      </div>

      <div class="ci-info__section">
        <h5 class="ci-info__section-title">運作方式</h5>
        <ul class="ci-info__list">
          <li>從測試集以重抽樣方式產生多組樣本</li>
          <li>對每組樣本計算評估指標</li>
          <li>取第 2.5 與 97.5 百分位數作為信賴區間上下界</li>
        </ul>
      </div>

      <div class="ci-info__notice">
        <span>⚠️</span>
        <p>計算時間顯著增加，建議在模型確認後再開啟。</p>
      </div>

      <div class="ci-info__footer">
        <span>⚙️</span>
        <p>若要啟用或停用 Compute CI，請至 <strong>Settings</strong> 節點調整。</p>
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
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
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
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
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

  .ci-info__section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ci-info__section-title {
    margin: 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .ci-info__text {
    margin: 0;
    font-size: 13px;
    color: var(--color-secondary);
    line-height: 1.6;
  }

  .ci-info__list {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 13px;
    color: var(--color-secondary);
    line-height: 1.5;
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

  .ci-info__notice p,
  .ci-info__footer p {
    margin: 0;
  }

  .ci-info__footer {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--color-secondary);
    line-height: 1.5;
  }

  .ci-info__footer strong {
    color: var(--color-accent);
  }
</style>
