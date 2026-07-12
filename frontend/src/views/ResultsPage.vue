<template>
  <section class="results-page">

    <HubSidebar />

    <main class="results-main">
      <header class="results-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
        />

        <div class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="toolbar-tab"
            :class="{ 'toolbar-tab--active': tab.active }"
            type="button"
            @click="setActiveTab(tab.key)"
          >
            <v-icon :icon="tab.icon" size="14" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <v-btn
          class="generate-paper-btn"
          color="primary"
          size="small"
          @click="router.push('/paper/sources')"
        >
          生成論文
        </v-btn>
      </header>

      <section v-if="!hasLoaded" class="empty-state">
        載入中...
      </section>

      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn color="primary" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
      </section>

      <template v-else>
        <section class="metric-grid">
          <article
            v-for="card in metricCards"
            :key="card.title"
            class="metric-card"
            :class="{ 'metric-card--accent': card.accent }"
          >
            <p class="metric-title">{{ card.title }}</p>
            <p class="metric-value">{{ card.value }}</p>
            <p class="metric-hint">{{ card.hint }}</p>
          </article>
        </section>

        <section class="insight-card">
          <div class="insight-header">
            <div class="insight-icon-wrap">
              <v-icon icon="mdi-shimmer" size="18" />
            </div>
            <h2 class="insight-title">AI生成洞察</h2>
          </div>

          <p v-if="insightLoading" class="insight-text">正在生成洞察...</p>
          <template v-else-if="insightError">
            <p class="insight-text">洞察生成失敗:{{ insightError }}</p>
            <v-btn size="small" variant="text" @click="loadInsight">重試</v-btn>
          </template>
          <p v-else class="insight-text">{{ insightText }}</p>
        </section>

        <section class="comparison-card">
          <div class="comparison-head">
            <h3>模型效能比較</h3>
            <p>各模型依實際設定的驗證方法訓練</p>
          </div>

          <div class="table-wrap">
            <table class="result-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th v-for="metric in allMetricNames" :key="metric">
                    {{ metricLabel(metric) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in modelRows" :key="row.model">
                  <td class="model-name">{{ row.model }}</td>
                  <td
                    v-for="metric in allMetricNames"
                    :key="metric"
                    :class="{ 'score-best': row.best && metric === rankingMetric }"
                  >
                    {{ row.values[metric] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { fetchResultInsight } from '@/api/insight'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import {
    loadResultInsightFromStorage,
    loadWorkflowStateFromStorage,
    saveResultInsightToStorage,
  } from '@/composables/workflow/useWorkflowStorage'

  const route = useRoute()
  const router = useRouter()

  const projectId = computed(() => route.query.project as string | undefined)

  onMounted(() => {
    document.title = 'DataMind'
  })

  interface ToolbarTab {
    key: string
    label: string
    icon: string
    active?: boolean
  }

  const tabs = ref<ToolbarTab[]>([
    { key: 'report', label: '報告', icon: 'mdi-file-document-outline', active: true },
    { key: 'code', label: '程式碼', icon: 'mdi-code-tags', active: false },
  ])

  function setActiveTab (targetKey: ToolbarTab['key']): void {
    for (const tab of tabs.value) {
      tab.active = tab.key === targetKey
    }
  }

  // ─── 讀取真實 workflow 結果 ──────────────────────────────────────────────────

  const workflowResult = ref<Record<string, unknown> | null>(null)
  const hasLoaded = ref(false)

  interface ModelMetric {
    metric: string
    value: number | null
  }

  interface ModelResult {
    model_name: string
    metrics: ModelMetric[]
  }

  const modelResults = computed<ModelResult[]>(() => {
    const raw = workflowResult.value?.results
    if (!Array.isArray(raw)) return []
    return raw
      .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object' && !('error' in r))
      .map(r => ({
        model_name: String(r.model_name ?? 'Unknown'),
        metrics: Array.isArray(r.metrics)
          ? r.metrics.map((m: Record<string, unknown>) => ({
            metric: String(m.metric),
            value: typeof m.value === 'number' ? m.value : null,
          }))
          : [],
      }))
  })

  const METRIC_LABELS: Record<string, string> = {
    accuracy: '準確率',
    balanced_accuracy: '平衡準確率',
    precision: '精準度',
    recall: '召回率',
    specificity: '特異度',
    f1: 'F1 分數',
    auc: 'AUC_ROC',
    auprc: 'AUPRC',
    mcc: 'MCC',
    kappa: 'Kappa',
  }

  const PREFERRED_METRIC_ORDER = [
    'balanced_accuracy', 'accuracy', 'f1', 'auc', 'auprc', 'precision', 'recall', 'specificity', 'mcc', 'kappa',
  ]

  const RANKING_PRIORITY = ['balanced_accuracy', 'accuracy', 'auc']

  function metricLabel (metric: string): string {
    return METRIC_LABELS[metric] ?? metric.toUpperCase()
  }

  function metricValueOf (result: ModelResult, metric: string): number | null {
    return result.metrics.find(m => m.metric === metric)?.value ?? null
  }

  const rankingMetric = computed<string | null>(() => {
    const results = modelResults.value
    if (results.length === 0) return null
    for (const candidate of RANKING_PRIORITY) {
      if (results.every(r => metricValueOf(r, candidate) !== null)) return candidate
    }
    return results[0]?.metrics[0]?.metric ?? null
  })

  const bestResult = computed<ModelResult | null>(() => {
    const metric = rankingMetric.value
    const results = modelResults.value
    if (!metric || results.length === 0) return null
    return results.reduce((best, current) => {
      const bestValue = metricValueOf(best, metric) ?? Number.NEGATIVE_INFINITY
      const currentValue = metricValueOf(current, metric) ?? Number.NEGATIVE_INFINITY
      return currentValue > bestValue ? current : best
    })
  })

  const allMetricNames = computed<string[]>(() => {
    const seen = new Set<string>()
    for (const result of modelResults.value) {
      for (const m of result.metrics) seen.add(m.metric)
    }
    const ordered = PREFERRED_METRIC_ORDER.filter(m => seen.has(m))
    const rest = [...seen].filter(m => !ordered.includes(m))
    return [...ordered, ...rest]
  })

  interface MetricCard {
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  const metricCards = computed<MetricCard[]>(() => {
    const best = bestResult.value
    const ranking = rankingMetric.value
    if (!best || !ranking) return []

    const cards: MetricCard[] = [
      { title: '最佳模型', value: best.model_name, hint: `依 ${metricLabel(ranking)} 排名` },
    ]

    const otherMetrics = allMetricNames.value.filter(m => m !== ranking)
    const cardMetrics = [ranking, ...otherMetrics].slice(0, 3)
    for (const metric of cardMetrics) {
      const value = metricValueOf(best, metric)
      cards.push({
        title: metricLabel(metric),
        value: value === null ? 'N/A' : value.toFixed(3),
        hint: metric,
        accent: metric === ranking,
      })
    }
    return cards
  })

  interface ResultRow {
    model: string
    values: Record<string, string>
    best: boolean
  }

  const modelRows = computed<ResultRow[]>(() => {
    const bestName = bestResult.value?.model_name
    return modelResults.value.map(result => {
      const values: Record<string, string> = {}
      for (const metric of allMetricNames.value) {
        const value = metricValueOf(result, metric)
        values[metric] = value === null ? 'N/A' : value.toFixed(3)
      }
      return {
        model: result.model_name,
        values,
        best: result.model_name === bestName,
      }
    })
  })

  // ─── AI 洞察文字(快取) ───────────────────────────────────────────────────────

  const insightText = ref<string | null>(null)
  const insightLoading = ref(false)
  const insightError = ref<string | null>(null)

  async function loadInsight (): Promise<void> {
    if (!projectId.value || !workflowResult.value) return
    const cached = loadResultInsightFromStorage(projectId.value)
    if (cached) {
      insightText.value = cached
      return
    }
    insightLoading.value = true
    insightError.value = null
    try {
      const insight = await fetchResultInsight(workflowResult.value)
      insightText.value = insight
      saveResultInsightToStorage(projectId.value, insight)
    } catch (error) {
      insightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      insightLoading.value = false
    }
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    workflowResult.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (workflowResult.value) {
      loadInsight()
    }
  })
</script>

<style scoped>
  .results-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    --brand-soft: #ebf2ff;
    --good: #18a836;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    position: relative;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .results-main {
    flex: 1;
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: auto;
  }

  .results-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
    animation: slide-in 0.45s ease both;
  }

  .back-btn {
    color: #1f2430;
  }

  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

  .generate-paper-btn {
    margin-left: 12px;
  }

  .toolbar-tab {
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #5f6571;
    cursor: pointer;
    background: transparent;
    transition: all 0.2s ease;
  }

  .toolbar-tab--active {
    background: #ffffff;
    color: #192235;
    box-shadow: 0 1px 3px rgba(20, 38, 84, 0.12);
  }

  .metric-grid {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
    animation: reveal-up 0.42s ease both;
  }

  .metric-card:nth-child(2) {
    animation-delay: 0.05s;
  }

  .metric-card:nth-child(3) {
    animation-delay: 0.1s;
  }

  .metric-card:nth-child(4) {
    animation-delay: 0.15s;
  }

  .metric-card--accent .metric-value {
    color: var(--good);
  }

  .metric-title {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    color: #20232a;
  }

  .metric-value {
    margin: 8px 0 2px;
    font-size: 36px;
    font-weight: 700;
    line-height: 1.05;
  }

  .metric-hint {
    margin: 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .insight-card {
    margin-top: 12px;
    border-radius: 14px;
    color: #f7f9ff;
    padding: 14px 16px;
    background: linear-gradient(102deg, #4f86f0 0%, #4554df 100%);
    animation: reveal-up 0.5s ease both;
    animation-delay: 0.12s;
  }

  .insight-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .insight-icon-wrap {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.2);
  }

  .insight-title {
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
    font-weight: 700;
  }

  .insight-text {
    margin: 8px 0 10px;
    font-size: 13px;
    color: rgba(248, 251, 255, 0.93);
    line-height: 1.45;
  }

  .insight-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .insight-tag {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    background: rgba(255, 255, 255, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.35);
  }

  .comparison-card {
    margin-top: 12px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: #ffffff;
    overflow: hidden;
    animation: reveal-up 0.55s ease both;
    animation-delay: 0.18s;
  }

  .comparison-head {
    padding: 14px 18px;
    border-bottom: 1px solid var(--line-soft);
  }

  .comparison-head h3 {
    margin: 0;
    font-size: 29px;
  }

  .comparison-head p {
    margin: 3px 0 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .table-wrap {
    overflow: auto;
  }

  .result-table {
    width: 100%;
    min-width: 680px;
    border-collapse: collapse;
  }

  .result-table th,
  .result-table td {
    padding: 11px 18px;
    text-align: left;
    border-bottom: 1px solid var(--line-soft);
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
    color: var(--good);
    font-weight: 700;
  }

  @keyframes reveal-up {
    from {
      opacity: 0;
      transform: translateY(10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1260px) {
    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 920px) {
    .results-page {
      display: block;
      padding: 12px;
    }

    .results-main {
      margin-top: 10px;
      border-radius: 12px;
      padding: 12px;
    }

    .insight-title,
    .comparison-head h3,
    .metric-value {
      font-size: clamp(20px, 4.2vw, 30px);
    }
  }

  @media (max-width: 640px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .results-toolbar {
      align-items: flex-start;
      gap: 8px;
      flex-direction: column;
    }

    .toolbar-tabs {
      width: 100%;
      justify-content: space-between;
    }

    .toolbar-tab {
      flex: 1;
      justify-content: center;
    }

    .result-table {
      min-width: 620px;
    }
  }
</style>
