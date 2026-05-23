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
          class="table-cell"
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
    gap: 14px;
    padding: 10px 0;
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
    border-radius: 20px;
    overflow: hidden;
    background: #ffffff;
  }

  .table-row {
    display: grid;
    grid-template-columns: 160px repeat(auto-fit, minmax(120px, 1fr));
    gap: 0;
    align-items: center;
  }

  .table-row:not(.table-row--header) {
    background: #ffffff;
  }

  .table-row:nth-child(even):not(.table-row--header) {
    background: #f8fafc;
  }

  .table-row--header {
    font-weight: 700;
    color: #0f172a;
    background: #e7f0ff;
  }

  .table-cell {
    padding: 14px 16px;
    color: #0f172a;
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: center;
  }

  .table-row:last-child .table-cell {
    border-bottom: none;
  }

  .table-cell--metric {
    background: rgba(226, 232, 240, 0.25);
    font-weight: 700;
    color: #0f172a;
  }

  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 3px;
    background: transparent;
  }

  .model-name {
    font-weight: 700;
    color: #1f2937;
    font-size: 13px;
  }

  .model-split {
    font-size: 12px;
    color: #475569;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
  }
</style>
