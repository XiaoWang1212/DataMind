<template>
  <section class="workflow-summary">
    <h4>Score Summary</h4>

    <div v-if="summary.length > 0" class="summary-table">
      <div class="table-row table-row--header">
        <div class="table-cell">Model</div>
        <div
          v-for="metricName in metricKeys"
          :key="metricName"
          class="table-cell table-cell--num"
        >
          {{ metricName }}
        </div>
      </div>

      <div v-for="row in modelRows" :key="row.model_name" class="table-row">
        <div class="table-cell table-cell--model">
          <div class="model-name">{{ row.model_name }}</div>
          <div class="model-split">{{ row.split_name }}</div>
        </div>
        <div
          v-for="cell in row.values"
          :key="`${row.model_name}-${cell.metric}`"
          class="table-cell table-cell--num"
          :class="{ 'table-cell--best': cell.isBest }"
        >
          {{ cell.text }}
        </div>
      </div>
    </div>

    <div v-else class="summary-empty">
      尚未有測試評分結果，請執行 Workflow 後在此查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const props = defineProps<{
    summary: Array<{
      model_name: string
      split_name: string
      metrics: Array<{ metric: string, valueFormatted: string }>
    }>
  }>()

  const metricKeys = computed(() => {
    const keys = new Set<string>()
    for (const item of props.summary) {
      for (const metric of item.metrics) keys.add(metric.metric)
    }
    return Array.from(keys)
  })

  // 每個 metric 的最佳值（後端的 10 個 metric——accuracy / balanced_accuracy / precision /
  // recall / specificity / f1 / mcc / kappa / auc / auprc——全部都是越高越好，沒有反向指標）
  const bestByMetric = computed(() => {
    const best: Record<string, number> = {}
    for (const item of props.summary) {
      for (const metric of item.metrics) {
        const value = Number(metric.valueFormatted)
        if (Number.isNaN(value)) continue
        const current = best[metric.metric]
        if (current === undefined || value > current) best[metric.metric] = value
      }
    }
    return best
  })

  // 一個模型一列、metric 當欄：模型數會隨使用者加減而成長，metric 相對固定，
  // 讓會成長的那一維走垂直方向，表格才不會橫向擠爆
  const modelRows = computed(() =>
    props.summary.map(item => ({
      model_name: item.model_name,
      split_name: item.split_name,
      values: metricKeys.value.map(metricName => {
        const text
          = item.metrics.find(m => m.metric === metricName)?.valueFormatted ?? '-'
        const value = Number(text)
        return {
          metric: metricName,
          text,
          isBest:
            !Number.isNaN(value) && bestByMetric.value[metricName] === value,
        }
      }),
    })),
  )
</script>

<style scoped>
  .workflow-summary {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0 0 16px;
  }

  .workflow-summary h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
    color: var(--color-text);
  }

  .summary-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--color-surface);
  }

  .table-row {
    display: grid;
    grid-template-columns: 180px repeat(auto-fit, minmax(80px, 1fr));
    gap: 0;
    align-items: center;
  }

  /* 分隔線掛在 row 上（不是 cell）：cell 的 border 會被 grid 的欄間切斷成一段一段 */
  .table-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .table-row:not(.table-row--header):hover {
    background: color-mix(in oklab, var(--color-accent) 3.5%, transparent);
  }

  .table-row--header {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-secondary);
    background: var(--color-surface);
  }

  /* 標題列比資料列矮：它只是欄位標籤，不需要跟資料列一樣的呼吸空間 */
  .table-row--header .table-cell {
    padding: 8px 14px;
  }

  .table-cell {
    padding: 11px 14px;
    color: var(--color-text);
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: left;
  }

  /* tabular-nums：讓同一欄的分數逐位對齊，比置中好比較。
     metric 表頭也套這條，標題才會跟底下那一整欄的數字切齊 */
  .table-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* 該 metric 表現最好的模型。這是 leaderboard 真正要回答的問題，
     不用逐格比對小數點就看得出誰贏 */
  .table-cell--best {
    font-weight: 500;
  }

  /* 最左欄：模型名 + split 名兩行堆疊，靠左 */
  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 2px;
    align-items: flex-start;
    background: transparent;
  }

  .model-name {
    font-weight: 500;
    color: var(--color-text);
    font-size: 13px;
  }

  .model-split {
    font-size: 11px;
    font-weight: 400;
    color: var(--color-secondary);
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
