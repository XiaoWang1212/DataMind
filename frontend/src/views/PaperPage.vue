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
          <div class="edit-actions" :class="{ 'edit-actions--hidden': mode !== 'edit' }">
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
        </div>
      </header>

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
      </div>

      <CitationPopover
        :citation="popoverCitation"
        :index="popoverIndex"
        :target="popoverTarget"
        @close="activeCitationId = null"
      />
    </main>
  </section>
</template>

<script setup lang="ts">
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { getReport, saveReport } from '@/api/report'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaginatedPaperView from '@/components/paper/PaginatedPaperView.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import ReferencesSection from '@/components/paper/ReferencesSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'
  import { citationStyleLabels } from '@/utils/paper/formatCitation'

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

  .edit-actions--hidden {
    visibility: hidden;
    pointer-events: none;
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

  .paper-sheet--paginated {
    max-width: none;
    background: none;
    border: none;
    border-radius: 0;
    padding: 0;
  }
</style>
