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
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <template v-if="mode === 'edit'">
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              color="primary"
              :disabled="!projectId"
              :loading="saving"
              size="small"
              @click="save"
            >
              儲存
            </v-btn>
          </template>
        </div>
      </header>

      <p v-if="mode === 'edit' && !projectId" class="save-hint">
        此論文尚未關聯專案,無法儲存
      </p>
      <p v-if="saveError" class="save-error">{{ saveError }}</p>

      <p v-if="loading" class="loading-hint">載入中...</p>

      <div v-else class="paper-body">
        <article class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            @citation-click="onCitationClick"
          />
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
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'

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
          report.value = { title: saved.title, content: saved.content, citations: saved.citations }
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

  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
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
      })
      report.value = { title: result.title, content: result.content, citations: result.citations }
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

  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
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
</style>
