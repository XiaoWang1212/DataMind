<template>
  <section class="sources-page">
    <HubSidebar />

    <main class="sources-main">
      <PageHeader title="選擇參考文獻">
        <template #back>
          <RouterLink class="back-link" :to="`/hub/projects/${projectId}/result`">
            <v-icon icon="mdi-arrow-left" size="15" />
            返回結果頁
          </RouterLink>
        </template>
      </PageHeader>

      <section v-if="!hasLoaded" class="sources-status">
        載入中...
      </section>

      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
        <AppButton variant="secondary" @click="router.push(`/hub/projects/${projectId}/result`)">
          回到結果頁
        </AppButton>
      </section>

      <template v-else>
        <div class="sources-title-input">
          <label class="sources-title-label" for="user-title-input">技術報告標題（選填）</label>
          <input
            id="user-title-input"
            v-model="userTitle"
            class="sources-title-field"
            placeholder="留空由 AI 自動判斷主題"
            type="text"
            @keyup.enter="loadCandidates"
          >
          <AppButton :loading="loadingSearch" variant="primary" @click="loadCandidates">
            {{ hasSearched ? '重新查詢' : '查詢文獻' }}
          </AppButton>
        </div>

        <template v-if="hasSearched">
          <p v-if="topic" class="sources-topic">研究主題:{{ topic }}</p>

          <div v-if="loadingSearch" class="sources-status" role="status">
            正在分析資料並查詢 arXiv<span aria-hidden="true" class="loading-dots"><i /><i /><i /></span>
          </div>

          <div v-else-if="searchError" class="sources-status sources-status--error">
            {{ searchError }}
            <AppButton variant="ghost" @click="loadCandidates">重試</AppButton>
          </div>

          <div v-else-if="candidates.length === 0" class="sources-status">
            找不到相關文獻,請稍後再試。
          </div>

          <template v-else>
            <ul class="candidate-list">
              <li v-for="candidate in candidates" :key="candidate.arxiv_id" class="candidate-card">
                <label class="candidate-select">
                  <AppCheckbox
                    :aria-label="`選擇 ${candidate.title}`"
                    :model-value="selectedIds.includes(candidate.arxiv_id)"
                    @update:model-value="toggleCandidate(candidate.arxiv_id, $event)"
                  />
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
              <AppButton
                :disabled="selectedIds.length === 0"
                :loading="generating"
                variant="primary"
                @click="handleGenerate"
              >
                確認並生成技術報告 ({{ selectedIds.length }})
              </AppButton>
              <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
            </div>
          </template>
        </template>
      </template>
    </main>

    <PaperGeneratingOverlay :visible="generating" @abandon="handleAbandon" />
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperGeneratingOverlay from '@/components/paper/PaperGeneratingOverlay.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import AppCheckbox from '@/components/ui/AppCheckbox.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
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
  const userTitle = ref('')
  const hasSearched = ref(false)
  const candidates = ref<ArxivCandidate[]>([])
  const selectedIds = ref<string[]>([])

  function toggleCandidate (arxivId: string, checked: boolean): void {
    selectedIds.value = checked
      ? [...selectedIds.value, arxivId]
      : selectedIds.value.filter(id => id !== arxivId)
  }

  const loadingSearch = ref(false)
  const searchError = ref<string | null>(null)

  const generating = ref(false)
  const generateError = ref<string | null>(null)

  async function loadCandidates (): Promise<void> {
    if (!miningResults.value) return
    hasSearched.value = true
    loadingSearch.value = true
    searchError.value = null
    try {
      const result = await searchArxivCandidates(miningResults.value, userTitle.value.trim() || undefined)
      topic.value = result.topic
      candidates.value = result.candidates
      selectedIds.value = []
    } catch (error) {
      searchError.value = error instanceof Error ? error.message : String(error)
    } finally {
      loadingSearch.value = false
    }
  }

  // 生成的請求不會因為離開而中斷。放棄之後這個編號會變，回來的結果就不再套用 ——
  // 否則幾分鐘後的 router.push 會把使用者從當時在看的頁面硬拉走
  let generationToken = 0

  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    const token = ++generationToken
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
      })
      if (token !== generationToken) return
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
      if (token !== generationToken) return
      generateError.value = error instanceof Error ? error.message : String(error)
    } finally {
      if (token === generationToken) generating.value = false
    }
  }

  function handleAbandon (): void {
    generationToken++
    generating.value = false
    generateError.value = '已放棄這次生成。勾選的文獻還在，可以重新送出。'
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
  })
</script>

<style scoped>
  /* 不設背景，讓 .v-application 的頁面漸層透出來，跟 HubLayout 同一套 */
  .sources-page {
    --card-bg: var(--color-surface);
    --line: var(--color-border-strong);
    --line-soft: var(--color-border);
    --text-main: var(--color-text);
    --text-secondary: var(--color-ink-soft);
    min-height: 100vh;
    display: flex;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-main);
  }

  .sources-main {
    flex: 1;
    min-width: 0;
    max-width: var(--content-max-width);
    display: flex;
    flex-direction: column;
    padding: 32px 36px;
    overflow: auto;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-top: 4px;
    font-size: 13px;
    color: var(--color-ink-soft);
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .back-link:hover {
    color: var(--color-ink);
  }

  .sources-title-input {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .sources-title-label {
    font-size: 13px;
    color: var(--text-secondary);
    white-space: nowrap;
  }

  .sources-title-field {
    flex: 1;
    min-width: 0;
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid var(--line);
    border-radius: var(--radius-sm);
    background: var(--card-bg);
    color: var(--text-main);
  }

  .sources-title-field:focus {
    outline: none;
    border-color: var(--color-ink);
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
    color: var(--color-error);
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
    border-radius: var(--radius-md);
    background: var(--card-bg);
    box-shadow: var(--shadow-card);
  }

  .candidate-select {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
  }

  /* checkbox 是固定 18px，標題行高比它高，往下推齊視覺基線 */
  .candidate-select :deep(.app-checkbox) {
    margin-top: 2px;
  }

  .candidate-body {
    flex: 1;
    min-width: 0;
  }

  .candidate-title {
    margin: 0 0 4px;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--color-text);
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
    color: var(--color-ink-soft);
  }

  .sources-actions {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
</style>
