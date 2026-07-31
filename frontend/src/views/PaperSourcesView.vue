<template>
  <section class="sources-page">
    <HubSidebar />

    <main class="sources-main">
      <header class="sources-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.push(`/hub/projects/${projectId}/result`)"
        />
        <h2 class="sources-title">選擇參考文獻</h2>
      </header>

      <section v-if="!hasLoaded" class="sources-status">
        載入中...
      </section>

      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/hub/projects/${projectId}/result`)">
          回到結果頁
        </v-btn>
      </section>

      <template v-else>
        <p v-if="topic" class="sources-topic">研究主題:{{ topic }}</p>

        <div v-if="loadingSearch" class="sources-status">
          正在分析資料並查詢 arXiv...
        </div>

        <div v-else-if="searchError" class="sources-status sources-status--error">
          {{ searchError }}
          <v-btn size="small" variant="text" @click="loadCandidates">重試</v-btn>
        </div>

        <div v-else-if="candidates.length === 0" class="sources-status">
          找不到相關文獻,請稍後再試。
        </div>

        <template v-else>
          <ul class="candidate-list">
            <li v-for="candidate in candidates" :key="candidate.arxiv_id" class="candidate-card">
              <label class="candidate-select">
                <input
                  v-model="selectedIds"
                  type="checkbox"
                  :value="candidate.arxiv_id"
                >
                <div class="candidate-body">
                  <p class="candidate-title">{{ candidate.title }}</p>
                  <p class="candidate-meta">
                    {{ candidate.authors }}
                    <span v-if="candidate.year">({{ candidate.year }})</span>
                  </p>
                  <p class="candidate-abstract">{{ candidate.abstract }}</p>
                </div>
              </label>
            </li>
          </ul>

          <div class="sources-actions">
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
            >
              {{ generating ? '生成中...' : `確認並生成論文 (${selectedIds.length})` }}
            </v-btn>
            <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
          </div>
        </template>
      </template>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { usePaperStore } from '@/store/paperStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'

  const route = useRoute()
  const router = useRouter()
  const paperStore = usePaperStore()

  const projectId = computed(() => route.query.project as string | undefined)
  const miningResults = ref<Record<string, unknown> | null>(null)
  const hasLoaded = ref(false)

  const topic = ref('')
  const candidates = ref<ArxivCandidate[]>([])
  const selectedIds = ref<string[]>([])

  const loadingSearch = ref(false)
  const searchError = ref<string | null>(null)

  const generating = ref(false)
  const generateError = ref<string | null>(null)

  async function loadCandidates (): Promise<void> {
    if (!miningResults.value) return
    loadingSearch.value = true
    searchError.value = null
    try {
      const result = await searchArxivCandidates(miningResults.value)
      topic.value = result.topic
      candidates.value = result.candidates
      selectedIds.value = []
    } catch (error) {
      searchError.value = error instanceof Error ? error.message : String(error)
    } finally {
      loadingSearch.value = false
    }
  }

  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
      generateError.value = error instanceof Error ? error.message : String(error)
    } finally {
      generating.value = false
    }
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (miningResults.value) {
      loadCandidates()
    }
  })
</script>

<style scoped>
  .sources-page {
    --page-bg: var(--color-primary);
    --card-bg: var(--color-surface);
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: var(--color-ink);
    --text-secondary: var(--color-secondary);
    min-height: calc(100vh - 64px);
    display: flex;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
      var(--page-bg);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-main);
  }

  .sources-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: var(--card-bg);
    padding: 12px 20px 24px;
    overflow: auto;
  }

  .sources-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: var(--color-ink);
  }

  .sources-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .sources-topic {
    margin: 14px 2px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status {
    margin: 20px 2px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status--error {
    color: #ef4444;
  }

  .candidate-list {
    list-style: none;
    margin: 14px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .candidate-card {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--card-bg);
  }

  .candidate-select {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
  }

  .candidate-body {
    flex: 1;
    min-width: 0;
  }

  .candidate-title {
    margin: 0 0 4px;
    font-size: 13.5px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .candidate-meta {
    margin: 0 0 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .candidate-abstract {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: var(--color-secondary);
  }

  .sources-actions {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
</style>
