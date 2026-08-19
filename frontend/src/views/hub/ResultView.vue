<template>
  <div class="result-view">
    <PageHeader
      v-if="project"
      :subtitle="`結果總覽 · 框架：${frameworkTitle}`"
      :title="project.name"
    >
      <template #back>
        <RouterLink class="back-link" :to="`/hub/projects/${projectId}`">
          <v-icon icon="mdi-arrow-left" size="15" />
          返回專案
        </RouterLink>
      </template>
      <template v-if="summary.length > 0" #actions>
        <RouterLink class="generate-paper-btn" :to="`/paper/sources?project=${projectId}`">
          生成論文
        </RouterLink>
      </template>
    </PageHeader>
    <RouterLink v-else class="back-link back-link--standalone" :to="`/hub/projects/${projectId}`">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

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

      <TableShell class="comparison-card">
        <div class="comparison-head">
          <h3>模型效能比較</h3>
        </div>

        <!-- 捲動交給內層，表頭列不會跟著表格橫向移出視野 -->
        <div class="table-wrap">
          <table class="ds-table result-table">
            <thead>
              <tr>
                <th>模型</th>
                <th v-for="metric in metricNames" :key="metric" class="ds-identifier">{{ metric }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in summary" :key="row.model_name">
                <td class="model-name ds-identifier">{{ row.model_name }}</td>
                <td
                  v-for="metric in metricNames"
                  :key="metric"
                  :class="{ 'score-best': row.model_name === bestModelName && metric === metricNames[0] }"
                >{{ metricValue(row, metric) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </TableShell>

      <section v-if="analysisLoading || analysisError || analysis" class="analysis-card glass-panel">
        <div class="analysis-header">
          <div class="analysis-icon-wrap">
            <v-icon icon="mdi-shimmer" size="18" />
          </div>
          <h2 class="analysis-title">AI 結構化分析</h2>
        </div>

        <p v-if="analysisLoading" class="analysis-loading">正在生成分析...</p>
        <template v-else-if="analysisError">
          <p class="analysis-error">分析生成失敗：{{ analysisError }}</p>
          <AppButton variant="ghost" @click="loadAnalysis">重試</AppButton>
        </template>
        <div v-else-if="analysis" class="analysis-grid">
          <article class="analysis-block">
            <h3>模型比較與選擇建議</h3>
            <p>{{ analysis.model_comparison }}</p>
          </article>
          <article class="analysis-block">
            <h3>資料與特徵層面洞察</h3>
            <p>{{ analysis.data_insights }}</p>
          </article>
          <article class="analysis-block">
            <h3>風險與限制提示</h3>
            <p>{{ analysis.risks }}</p>
          </article>
          <article class="analysis-block">
            <h3>後續建議行動</h3>
            <p>{{ analysis.recommendations }}</p>
          </article>
        </div>
      </section>

      <section class="chat-card glass-panel">
        <div class="analysis-header">
          <div class="analysis-icon-wrap">
            <v-icon icon="mdi-chat-processing-outline" size="18" />
          </div>
          <h2 class="analysis-title">與 AI 對話</h2>
        </div>

        <div class="chat-messages">
          <p v-if="chatMessages.length === 0" class="chat-empty">針對這份結果有任何問題，都可以在下方提問。</p>
          <div
            v-for="(msg, index) in chatMessages"
            :key="index"
            class="chat-bubble"
            :class="[msg.role === 'user' ? 'chat-bubble--user' : 'chat-bubble--model', { 'chat-bubble--failed': msg.failed }]"
          >
            <p class="chat-bubble-text">{{ msg.text }}</p>
            <p v-if="msg.failed" class="chat-bubble-failed-hint">傳送失敗</p>
            <div v-if="msg.papers && msg.papers.length > 0" class="chat-papers">
              <a
                v-for="paper in msg.papers"
                :key="paper.arxiv_id"
                class="chat-paper-card"
                :href="paper.pdf_url"
                rel="noopener noreferrer"
                target="_blank"
              >
                <p class="chat-paper-title">{{ paper.title }}</p>
                <p class="chat-paper-meta">{{ paper.authors }}<span v-if="paper.year">（{{ paper.year }}）</span></p>
              </a>
            </div>
          </div>
          <p v-if="chatLoading" class="chat-loading">AI 思考中...</p>
          <p v-if="chatError" class="chat-error">傳送失敗：{{ chatError }}</p>
        </div>

        <form class="chat-input-row" @submit.prevent="sendMessage">
          <input
            v-model="chatInput"
            class="chat-input"
            :disabled="chatLoading"
            placeholder="針對這份結果提問..."
            type="text"
          >
          <AppButton :disabled="!chatInput.trim()" :loading="chatLoading" type="submit" variant="primary">
            送出
          </AppButton>
        </form>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import type { ArxivCandidate } from '@/api/arxiv'
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { type ChatMessage, fetchStructuredAnalysis, sendChatMessage, type StructuredAnalysis } from '@/api/resultAnalysis'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import TableShell from '@/components/ui/TableShell.vue'
  import {
    loadChatHistoryFromStorage,
    loadStructuredAnalysisFromStorage,
    loadWorkflowStateFromStorage,
    saveChatHistoryToStorage,
    saveStructuredAnalysisToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'

  interface MetricCard {
    key: string
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  const route = useRoute()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // 注意：projectId 維持字串型別——這個變數後面還會拿去當 localStorage 的 key
  // （loadWorkflowStateFromStorage 等函式都吃字串），只有跟 store.projects 比對時才轉數字
  const projectId = computed(() => route.params.id as string)

  const project = computed(() =>
    store.projects.find(p => p.id === Number(projectId.value)),
  )

  const frameworkTitle = computed(() =>
    frameworkStore.frameworks.find(fw => fw.id === project.value?.frameworkId)?.title ?? '（未選擇）',
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

  interface DisplayChatMessage extends ChatMessage {
    papers?: ArxivCandidate[]
    failed?: boolean
  }

  const analysis = ref<StructuredAnalysis | null>(null)
  const analysisLoading = ref(false)
  const analysisError = ref<string | null>(null)

  async function loadAnalysis (): Promise<void> {
    const cached = loadStructuredAnalysisFromStorage(projectId.value)
    if (cached) {
      analysis.value = cached
      return
    }

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return

    analysisLoading.value = true
    analysisError.value = null
    try {
      analysis.value = await fetchStructuredAnalysis(miningResult)
      const isAllEmpty = Object.values(analysis.value).every(v => v === '')
      if (isAllEmpty) {
        analysis.value = null
        throw new Error('AI 分析生成失敗，請稍後重試')
      }
      saveStructuredAnalysisToStorage(projectId.value, analysis.value)
    } catch (error) {
      analysisError.value = error instanceof Error ? error.message : String(error)
    } finally {
      analysisLoading.value = false
    }
  }

  const chatMessages = ref<DisplayChatMessage[]>([])
  const chatInput = ref('')
  const chatLoading = ref(false)
  const chatError = ref<string | null>(null)

  async function sendMessage (): Promise<void> {
    const text = chatInput.value.trim()
    if (!text || chatLoading.value) return

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return

    chatMessages.value.push({ role: 'user', text })
    chatInput.value = ''
    chatLoading.value = true
    chatError.value = null

    try {
      const historyForApi: ChatMessage[] = chatMessages.value
        .slice(0, -1)
        .filter(m => !m.failed)
        .map(m => ({ role: m.role, text: m.text }))
      const { reply, papers } = await sendChatMessage(miningResult, historyForApi, text)
      chatMessages.value.push({ role: 'model', text: reply, papers: papers.length > 0 ? papers : undefined })
      saveChatHistoryToStorage(projectId.value, chatMessages.value)
    } catch (error) {
      chatError.value = error instanceof Error ? error.message : String(error)
      const lastMessage = chatMessages.value.at(-1)
      if (lastMessage) lastMessage.failed = true
    } finally {
      chatLoading.value = false
    }
  }

  onMounted(() => {
    if (summary.value.length === 0) return
    loadAnalysis()
    chatMessages.value = loadChatHistoryFromStorage(projectId.value) as DisplayChatMessage[]
  })
</script>

<style scoped>
/* 結果頁是資料密集頁，容器用較寬的上限（§8.2） */
.result-view {
  max-width: var(--content-max-width-wide);
  margin-inline: auto;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  /* 對齊 22px 標題的第一行中線 */
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-ink-soft);
  text-decoration: none;
  transition: color var(--dur-fast) var(--ease-out);
}

.back-link:hover {
  color: var(--color-ink);
}

.back-link--standalone {
  margin-top: 0;
  margin-bottom: 20px;
}

.generate-paper-btn,
.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 18px;
  border-radius: 999px;
  background: var(--color-ink);
  color: var(--color-surface);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background var(--dur-fast) var(--ease-out);
}

.generate-paper-btn:hover,
.open-workflow-btn:hover {
  background: var(--color-ink-strong);
}

.not-found {
  padding: 48px;
  font-size: 14px;
  text-align: center;
  color: var(--color-ink-soft);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: var(--color-ink-soft);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.metric-card--accent .metric-value {
  color: var(--color-success-text);
}

.metric-title {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ink-soft);
}

.metric-value {
  margin: 8px 0 2px;
  font-size: 24px;
  font-weight: 500;
  line-height: 1.15;
  color: var(--color-text);
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-ink-soft);
}

/* 底色、圓角、陰影由 TableShell 提供，這裡不能重寫 */
.comparison-card {
  margin-top: 16px;
}

.comparison-head {
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
}

.comparison-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
}

.table-wrap {
  overflow: auto;
}

.result-table {
  min-width: 480px;
}

.result-table th,
.result-table td {
  padding: 11px 18px;
  white-space: nowrap;
}

.model-name {
  color: var(--color-text);
}

.score-best {
  color: var(--color-success-text);
  font-weight: 500;
}

/* 底色、邊框、圓角、陰影由 .glass-panel 提供。scoped 樣式不在 CSS layer 內、
   優先權高於 glass.css，在這裡重寫任何一項都會蓋掉玻璃 */
.analysis-card,
.chat-card {
  margin-top: 16px;
  padding: 18px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.analysis-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: color-mix(in oklab, var(--color-ink) 8%, white);
  color: var(--color-ink);
}

.analysis-title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
}

.analysis-loading {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-soft);
}

.analysis-error {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-error-text);
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-block h3 {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.analysis-block p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-ink-soft);
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.chat-empty {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-soft);
}

/* 氣泡樣式與 MappingChatPanel 對齊，同一種元件在兩個地方要長一樣 */
.chat-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13.5px;
  line-height: 1.6;
}

.chat-bubble--user {
  align-self: flex-end;
  background: var(--color-chat-user);
  color: var(--color-inverted);
}

/* tint 與半透明玻璃的明度差只有 1.2:1，加一道藏青描邊讓氣泡邊界讀得出來 */
.chat-bubble--model {
  align-self: flex-start;
  background: var(--color-chat-system);
  box-shadow:
    0 1px 2px rgba(14, 30, 66, 0.1),
    0 6px 16px rgba(14, 30, 66, 0.07);
  color: var(--color-text);
}

.chat-bubble--failed {
  opacity: 0.65;
  outline: 1px solid var(--color-error);
}

.chat-bubble-failed-hint {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: var(--color-error-bg);
}

.chat-bubble-text {
  margin: 0;
  white-space: pre-wrap;
}

.chat-papers {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.chat-paper-card {
  display: block;
  padding: 8px 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  text-decoration: none;
}

.chat-paper-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--color-ink);
}

.chat-paper-meta {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: var(--color-ink-soft);
}

.chat-loading,
.chat-error {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-ink-soft);
}

.chat-error {
  color: var(--color-error-text);
}

.chat-input-row {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  height: 38px;
  padding: 0 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  font-size: 13px;
}

.chat-input:disabled {
  background: var(--color-surface-alt);
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
