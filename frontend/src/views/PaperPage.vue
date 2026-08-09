<template>
  <section class="paper-page">
    <HubSidebar />

    <main class="paper-main">
      <header class="paper-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.back()"
        />
        <h2 class="paper-title">{{ report.title }}</h2>

        <div class="toolbar-actions">
          <v-select
            v-model="report.citationStyle"
            class="citation-style-select"
            density="compact"
            :disabled="loading || mode === 'edit'"
            hide-details
            :items="citationStyleItems"
            variant="outlined"
            @update:model-value="onCitationStyleChange"
          />
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <div v-if="mode === 'edit'" class="edit-actions">
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="!projectId"
              :loading="saving"
              size="small"
              @click="save"
            >
              儲存
            </v-btn>
          </div>
          <v-btn
            class="score-btn"
            :class="{ 'score-btn--loading': scoring }"
            :disabled="scoring"
            size="small"
            variant="flat"
            @click="handleScorePaper"
          >
            <template #prepend>
              <v-icon :class="{ 'mdi-spin': scoring }" :icon="scoring ? 'mdi-loading' : 'mdi-star'" />
            </template>
            {{ scoreButtonLabel }}
          </v-btn>
        </div>
      </header>

      <p v-if="scoreError" class="score-error">
        {{ scoreError }}
        <v-btn size="small" variant="text" @click="handleScorePaper">重試</v-btn>
      </p>
      <p v-if="mode === 'edit' && !projectId" class="save-hint">
        此論文尚未關聯專案,無法儲存
      </p>
      <p v-if="saveError" class="save-error">{{ saveError }}</p>

      <p v-if="loading" class="loading-hint">載入中...</p>

      <div v-else class="paper-body">
        <article v-if="mode === 'view'" class="paper-sheet paper-sheet--paginated">
          <PaginatedPaperView
            :citation-style="report.citationStyle"
            :citations="report.citations"
            :content="report.content"
            @citation-click="onCitationClick"
          />
        </article>
        <article v-else class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="true"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
          <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" />
        </article>

        <div class="paper-citations">
          <JournalScorePanel
            :journal-scores="journalScores"
            :scoring="scoring"
            @open-report="scoreDialogVisible = true"
          />
        </div>
      </div>

      <CitationPopover
        :citation="popoverCitation"
        :index="popoverIndex"
        :target="popoverTarget"
        @close="activeCitationId = null"
      />
    </main>

    <JournalScoreDialog
      :failed-journals="failedJournals"
      :journal-scores="journalScores"
      :visible="scoreDialogVisible"
      @close="scoreDialogVisible = false"
    />
  </section>
</template>

<script setup lang="ts">
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { type JournalScore, scorePaper } from '@/api/arxiv'
  import { getReport, saveReport } from '@/api/report'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import JournalScorePanel from '@/components/paper/JournalScorePanel.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaginatedPaperView from '@/components/paper/PaginatedPaperView.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import ReferencesSection from '@/components/paper/ReferencesSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'
  import { citationStyleLabels } from '@/utils/paper/formatCitation'
  import { buildPaperText } from '@/utils/paperTransform'

  const route = useRoute()
  const router = useRouter()
  const paperStore = usePaperStore()

  const projectId = computed(() => route.query.project as string | undefined)

  const report = ref<PaperReport>(mockPaperReport)
  const loading = ref(true)
  const mode = ref<'view' | 'edit'>('view')
  const saving = ref(false)
  const saveError = ref<string | null>(null)
  const activeCitationId = ref<string | null>(null)
  const popoverTarget = ref<HTMLElement | null>(null)

  const popoverCitation = computed(() =>
    report.value.citations.find(c => c.id === activeCitationId.value) ?? null,
  )
  const popoverIndex = computed(() =>
    report.value.citations.findIndex(c => c.id === activeCitationId.value) + 1,
  )

  let savedSnapshot: PaperReport = mockPaperReport

  const scoring = ref(false)
  const scoreError = ref<string | null>(null)
  const scoreDialogVisible = ref(false)
  const journalScores = ref<JournalScore[]>([])
  const failedJournals = ref<string[]>([])

  const scoreButtonLabel = computed(() => {
    if (scoring.value) return '評分中...'
    return journalScores.value.length > 0 ? '再次評分' : '期刊評分'
  })

  const citationIndex = computed(() => {
    const index: Record<string, number> = {}
    for (const [i, citation] of report.value.citations.entries()) {
      index[citation.id] = i + 1
    }
    return index
  })

  onMounted(async () => {
    document.title = 'DataMind'

    if (paperStore.generatedReport) {
      report.value = paperStore.generatedReport
      paperStore.clearGeneratedReport()
    } else if (projectId.value) {
      try {
        const saved = await getReport(projectId.value)
        if (saved) {
          report.value = {
            title: saved.title,
            content: saved.content,
            citations: saved.citations,
            citationStyle: saved.citationStyle ?? 'apa',
          }
        }
      } catch (error) {
        saveError.value = error instanceof Error ? error.message : String(error)
      }
    }

    savedSnapshot = structuredClone(toRaw(report.value))
    loading.value = false
  })

  function onCitationClick ({ citationId, target }: { citationId: string, target: HTMLElement }) {
    if (activeCitationId.value === citationId) {
      activeCitationId.value = null
      return
    }
    activeCitationId.value = citationId
    popoverTarget.value = target
  }

  const citationStyleItems = Object.entries(citationStyleLabels).map(([value, title]) => ({ value, title }))

  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
  }

  async function onCitationStyleChange () {
    if (!projectId.value) return
    const previousStyle = savedSnapshot.citationStyle
    try {
      await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
        citationStyle: report.value.citationStyle,
      })
      savedSnapshot = structuredClone(toRaw(report.value))
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
      report.value.citationStyle = previousStyle
    }
  }

  async function save () {
    if (!projectId.value) return
    saving.value = true
    saveError.value = null
    try {
      const result = await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
        citationStyle: report.value.citationStyle,
      })
      report.value = {
        title: result.title,
        content: result.content,
        citations: result.citations,
        citationStyle: result.citationStyle,
      }
      savedSnapshot = structuredClone(toRaw(report.value))
      mode.value = 'view'
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    } finally {
      saving.value = false
    }
  }

  async function handleScorePaper (): Promise<void> {
    scoring.value = true
    scoreError.value = null
    try {
      const paperText = buildPaperText(report.value, citationIndex.value)
      const result = await scorePaper(paperText)
      journalScores.value = result.journalScores
      failedJournals.value = result.failedJournals
      scoreDialogVisible.value = true
    } catch (error) {
      scoreError.value = error instanceof Error ? error.message : String(error)
    } finally {
      scoring.value = false
    }
  }
</script>

<style scoped>
  .paper-page {
    --page-bg: var(--color-primary);
    --card-bg: var(--color-surface);
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: var(--color-ink);
    --text-secondary: var(--color-secondary);
    --brand: var(--color-accent);
    min-height: 100vh;
    display: flex;
    gap: 0;
    padding: 0;
    background: var(--color-primary);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    background:
      radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
      var(--color-primary);
    padding: 12px 20px 18px;
    overflow: hidden;
  }

  .paper-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    max-width: 1064px;
    margin: 0 auto;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .paper-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }

  .score-btn {
    background: #6f5613 !important;
    color: #ffffff !important;
    opacity: 1 !important;
  }

  .score-btn :deep(.v-icon) {
    color: #ffffff;
  }

  .score-btn.score-btn--loading {
    background: #fffbe8 !important;
    color: #8a6d1a !important;
    border: 1px solid #c9ad2a;
  }

  .score-btn.score-btn--loading :deep(.v-icon) {
    color: #8a6d1a;
  }

  .score-error {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 10px 2px 0;
    font-size: 12px;
    color: #b91c1c;
  }

  .citation-style-select {
    width: 92px;
  }

  .citation-style-select :deep(.v-field) {
    font-size: 12px;
  }

  .edit-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .save-hint {
    margin: 8px 2px 0;
    font-size: 12px;
    color: #b45309;
  }

  .save-error {
    margin: 8px 2px 0;
    font-size: 12px;
    color: #dc2626;
  }

  .loading-hint {
    margin: 24px 2px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
    width: 100%;
    max-width: 1064px;
    gap: 24px;
    margin: 14px auto 0;
    overflow: auto;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 28px 34px;
    height: fit-content;
  }

  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  @media (max-width: 1100px) {
    .paper-body {
      flex-direction: column;
    }

    .paper-citations {
      width: 100%;
      position: static;
      max-height: none;
      overflow-y: visible;
    }
  }

  .paper-sheet--paginated {
    max-width: none;
    background: none;
    border: none;
    border-radius: 0;
    padding: 0;
  }
</style>
