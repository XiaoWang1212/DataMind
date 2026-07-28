<template>
  <div>
    <RouterLink class="back-link" :to="`/hub/projects/${projectId}`">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <div v-if="project" class="page-header">
      <h1 class="page-title">{{ project.name }}</h1>
      <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
    </div>

    <div v-if="!project" class="not-found">找不到該專案</div>

    <template v-else-if="summary.length === 0">
      <div class="empty-state">
        <p class="empty-text">尚未有可用結果</p>
        <RouterLink class="open-workflow-btn" :to="`/workflow?project=${projectId}`">
          <v-icon icon="mdi-sitemap-outline" size="16" />
          在 Workflow 中開啟
        </RouterLink>
      </div>
    </template>

    <template v-else>
      <section class="metric-grid">
        <article
          v-for="card in metricCards"
          :key="card.key"
          class="metric-card"
          :class="{ 'metric-card--accent': card.accent }"
        >
          <p class="metric-title">{{ card.title }}</p>
          <p class="metric-value">{{ card.value }}</p>
          <p class="metric-hint">{{ card.hint }}</p>
        </article>
      </section>

      <section class="comparison-card">
        <div class="comparison-head">
          <h3>模型效能比較</h3>
        </div>

        <div class="table-wrap">
          <table class="result-table">
            <thead>
              <tr>
                <th>模型</th>
                <th v-for="metric in metricNames" :key="metric">{{ metric }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in summary" :key="row.model_name">
                <td class="model-name">{{ row.model_name }}</td>
                <td
                  v-for="metric in metricNames"
                  :key="metric"
                  :class="{ 'score-best': row.model_name === bestModelName && metric === metricNames[0] }"
                >{{ metricValue(row, metric) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useProjectStore } from '@/store/projectStore'
  import { summarizeWorkflowResult, type ModelMetricSummary } from '@/utils/workflow/summarizeWorkflowResult'

  interface MetricCard {
    key: string
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  const route = useRoute()
  const store = useProjectStore()

  const projectId = computed(() => route.params.id as string)

  const project = computed(() =>
    store.projects.find(p => p.id === projectId.value),
  )

  const summary = computed<ModelMetricSummary[]>(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    return summarizeWorkflowResult(state?.workflowResult ?? null)
  })

  const metricNames = computed(() => {
    const names: string[] = []
    for (const row of summary.value) {
      for (const m of row.metrics) {
        if (!names.includes(m.metric)) names.push(m.metric)
      }
    }
    return names
  })

  function bestModelFor (metric: string): { model_name: string, valueFormatted: string } | null {
    let best: { model_name: string, valueFormatted: string, value: number } | null = null
    for (const row of summary.value) {
      const entry = row.metrics.find(m => m.metric === metric)
      if (!entry) continue
      const value = Number(entry.valueFormatted)
      if (Number.isNaN(value)) continue
      if (!best || value > best.value) {
        best = { model_name: row.model_name, valueFormatted: entry.valueFormatted, value }
      }
    }
    return best ? { model_name: best.model_name, valueFormatted: best.valueFormatted } : null
  }

  const bestModelName = computed(() => {
    if (metricNames.value.length === 0) return null
    return bestModelFor(metricNames.value[0]!)?.model_name ?? null
  })

  const metricCards = computed<MetricCard[]>(() => {
    if (metricNames.value.length === 0) return []
    const primaryMetric = metricNames.value[0]!
    const best = bestModelFor(primaryMetric)

    const cards: MetricCard[] = [
      {
        key: 'best-model',
        title: '最佳模型',
        value: best?.model_name ?? '—',
        hint: best ? `${primaryMetric}: ${best.valueFormatted}` : '',
        accent: true,
      },
    ]

    for (const metric of metricNames.value.slice(1, 4)) {
      const metricBest = bestModelFor(metric)
      cards.push({
        key: metric,
        title: metric,
        value: metricBest?.valueFormatted ?? '—',
        hint: metricBest?.model_name ?? '',
      })
    }

    return cards.slice(0, 4)
  })

  function metricValue (row: ModelMetricSummary, metric: string): string {
    const entry = row.metrics.find(m => m.metric === metric)
    if (entry) return entry.valueFormatted
    if (row.errors[metric]) return '錯誤'
    return '—'
  }
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

.not-found {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: #9ca3af;
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: #1b3ca0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  padding: 14px;
}

.metric-card--accent .metric-value {
  color: #18a836;
}

.metric-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #20232a;
}

.metric-value {
  margin: 8px 0 2px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  color: #111827;
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: #6f7480;
}

.comparison-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
}

.comparison-head {
  padding: 14px 18px;
  border-bottom: 1px solid #f0f1f3;
}

.comparison-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.table-wrap {
  overflow: auto;
}

.result-table {
  width: 100%;
  min-width: 480px;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 11px 18px;
  text-align: left;
  border-bottom: 1px solid #f0f1f3;
  font-size: 12px;
  white-space: nowrap;
}

.result-table th {
  font-weight: 700;
  color: #2a2f39;
  background: #fafbff;
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}

.model-name {
  font-weight: 700;
  color: #1f2532;
}

.score-best {
  color: #18a836;
  font-weight: 700;
}

@media (max-width: 1260px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
