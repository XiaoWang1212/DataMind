<template>
  <section class="workflow-summary">
    <h4>Score Summary</h4>

    <div v-if="summary.length > 0" class="summary-table">
      <div class="table-row table-row--header">
        <div class="table-cell">Metric</div>
        <div
          v-for="modelName in modelNames"
          :key="modelName"
          class="table-cell table-cell--model"
        >
          <div class="model-name">{{ modelName }}</div>
          <div class="model-split">{{ modelSplits[modelName] }}</div>
        </div>
      </div>

      <div v-for="row in matrixRows" :key="row.metric" class="table-row">
        <div class="table-cell table-cell--metric">{{ row.metric }}</div>
        <div
          v-for="(value, index) in row.values"
          :key="`${row.metric}-${modelNames[index]}`"
          class="table-cell table-cell--num"
        >
          {{ value }}
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

  const modelNames = computed(() =>
    props.summary.map(item => item.model_name),
  )

  const modelSplits = computed(() =>
    props.summary.reduce(
      (acc, item) => {
        acc[item.model_name] = item.split_name
        return acc
      },
      {} as Record<string, string>,
    ),
  )

  const metricKeys = computed(() => {
    const keys = new Set<string>()
    for (const item of props.summary) {
      for (const metric of item.metrics) keys.add(metric.metric)
    }
    return Array.from(keys)
  })

  const matrixRows = computed(() =>
    metricKeys.value.map(metricName => ({
      metric: metricName,
      values: props.summary.map(item => {
        const metric = item.metrics.find(m => m.metric === metricName)
        return metric?.valueFormatted ?? '-'
      }),
    })),
  )
</script>

<style scoped>
  .workflow-summary {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0;
  }

  .workflow-summary h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }

  .summary-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
  }

  .table-row {
    display: grid;
    grid-template-columns: 160px repeat(auto-fit, minmax(120px, 1fr));
    gap: 0;
    align-items: center;
  }

  /* 分隔線掛在 row 上（不是 cell）：cell 的 border 會被 grid 的欄間切斷成一段一段 */
  .table-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .table-row:not(.table-row--header):hover {
    background: rgba(0, 93, 255, 0.035);
  }

  .table-row--header {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
  }

  /* 標題列比資料列矮：它只是欄位標籤，不需要跟資料列一樣的呼吸空間 */
  .table-row--header .table-cell {
    padding: 8px 14px;
  }

  .table-cell {
    padding: 11px 14px;
    color: #0f172a;
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: left;
  }

  .table-cell--metric {
    font-weight: 600;
    color: #1e293b;
  }

  /* tabular-nums：讓各模型的分數逐位對齊，比置中好比較 */
  .table-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* 表頭的模型名/split 名靠右，才會跟底下那一整欄的數字對齊 */
  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 3px;
    align-items: flex-end;
    background: transparent;
  }

  .model-name {
    font-weight: 700;
    color: #1f2937;
    font-size: 12px;
  }

  .model-split {
    font-size: 11px;
    font-weight: 400;
    color: #94a3b8;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
  }
</style>
