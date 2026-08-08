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
      </header>

      <p v-if="scoreError" class="score-error">
        {{ scoreError }}
        <v-btn size="small" variant="text" @click="handleScorePaper">重試</v-btn>
      </p>

      <div class="paper-body">
        <article ref="sheetRef" class="paper-sheet">
          <PaperSection
            v-for="section in report.sections"
            :key="section.heading"
            :active-citation-id="activeCitationId"
            :citation-index="citationIndex"
            :section="section"
            @citation-click="onCitationClick"
          />
        </article>

        <div class="paper-citations">
          <JournalScorePanel
            :journal-scores="journalScores"
            :scoring="scoring"
            @open-report="scoreDialogVisible = true"
          />
          <CitationPanel
            :active-citation-id="activeCitationId"
            :citations="report.citations"
            @select="onPanelSelect"
          />
        </div>
      </div>
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
  import { computed, onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { type JournalScore, scorePaper } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import JournalScorePanel from '@/components/paper/JournalScorePanel.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'
  import { buildPaperText } from '@/utils/paperTransform'

  const router = useRouter()
  const paperStore = usePaperStore()
  const report = paperStore.generatedReport ?? mockPaperReport
  paperStore.clearGeneratedReport()

  const citationIndex = Object.fromEntries(
    report.citations.map((citation, index) => [citation.id, index + 1]),
  )

  const activeCitationId = ref<string | null>(null)
  const sheetRef = ref<HTMLElement | null>(null)

  const scoring = ref(false)
  const scoreError = ref<string | null>(null)
  const scoreDialogVisible = ref(false)
  const journalScores = ref<JournalScore[]>([])
  const failedJournals = ref<string[]>([])

  const scoreButtonLabel = computed(() => {
    if (scoring.value) return '評分中...'
    return journalScores.value.length > 0 ? '再次評分' : '期刊評分'
  })

  onMounted(() => {
    document.title = 'DataMind'
  })

  function onCitationClick (citationId: string) {
    activeCitationId.value = citationId
  }

  function onPanelSelect (citationId: string) {
    activeCitationId.value = citationId
    sheetRef.value
      ?.querySelector(`[data-citation-id~="${CSS.escape(citationId)}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  async function handleScorePaper (): Promise<void> {
    scoring.value = true
    scoreError.value = null
    try {
      const paperText = buildPaperText(report, citationIndex)
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
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background:
      radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
      linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: hidden;
  }

  .paper-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
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

  .score-btn {
    margin-left: auto;
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

  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 16px;
    margin-top: 14px;
    overflow: auto;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    max-width: 760px;
    margin: 0 auto;
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
</style>
