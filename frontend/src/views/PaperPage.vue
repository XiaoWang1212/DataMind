<template>
  <section class="paper-page">
    <HubSidebar />

    <main ref="mainRef" class="paper-main">
      <header ref="toolbarRef" class="paper-toolbar">
        <AppButton aria-label="返回" icon-only variant="ghost" @click="router.back()">
          <v-icon icon="mdi-arrow-left" size="18" />
        </AppButton>
        <h2 class="paper-title">{{ report.title }}</h2>

        <div class="toolbar-actions">
          <CustomSelect
            aria-label="引用格式"
            class="citation-style-select"
            :disabled="loading || mode === 'edit'"
            :model-value="report.citationStyle"
            :options="citationStyleOptions"
            @update:model-value="onCitationStyleChange"
          />
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <div v-if="mode === 'edit'" class="edit-actions">
            <AppButton variant="ghost" @click="cancelEdit">取消</AppButton>
            <AppButton :disabled="!projectId" :loading="saving" variant="primary" @click="save">
              儲存
            </AppButton>
          </div>
          <AppButton :loading="scoring" variant="secondary" @click="handleScorePaper">
            <v-icon icon="mdi-star-outline" size="16" />
            {{ scoreButtonLabel }}
          </AppButton>
          <AppButton v-if="mode === 'view'" :loading="downloadingPdf" variant="secondary" @click="downloadPdf">
            <v-icon icon="mdi-download-outline" size="16" />
            下載 PDF
          </AppButton>
        </div>
      </header>

      <p v-if="scoreError" class="score-error">
        {{ scoreError }}
        <AppButton variant="ghost" @click="handleScorePaper">重試</AppButton>
      </p>
      <p v-if="mode === 'edit' && !projectId" class="save-hint">
        此技術報告尚未關聯專案,無法儲存
      </p>
      <p v-if="saveError" class="save-error">{{ saveError }}</p>
      <p v-if="pdfError" class="save-error">{{ pdfError }}</p>

      <div v-if="loading" aria-label="載入中" class="paper-skeleton" role="status">
        <div class="skeleton-line" style="width: 45%" />
        <div class="skeleton-line" style="width: 100%" />
        <div class="skeleton-line" style="width: 94%" />
        <div class="skeleton-line" style="width: 76%" />
      </div>

      <div v-else class="paper-body enter-rise">
        <article v-if="mode === 'view'" class="paper-sheet paper-sheet--paginated">
          <PaginatedPaperView
            ref="paginatedViewRef"
            :citation-style="report.citationStyle"
            :citations="report.citations"
            :content="report.content"
            @citation-click="onCitationClick"
          />
        </article>
        <article v-else class="paper-sheet paper-sheet--editing">
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
  import type { CitationStyle, PaperReport } from '@/constants/reportData'
  import { computed, onBeforeUnmount, onMounted, ref, toRaw } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { type JournalScore, scorePaper } from '@/api/arxiv'
  import { downloadReportPdf, getReport, saveReport } from '@/api/report'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import { buildPaperExportHtml } from '@/components/paper/exportPaperHtml'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import JournalScorePanel from '@/components/paper/JournalScorePanel.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaginatedPaperView from '@/components/paper/PaginatedPaperView.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import ReferencesSection from '@/components/paper/ReferencesSection.vue'
  import AppButton from '@/components/ui/AppButton.vue'
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
  const paginatedViewRef = ref<InstanceType<typeof PaginatedPaperView> | null>(null)
  const downloadingPdf = ref(false)
  const pdfError = ref<string | null>(null)
  const mainRef = ref<HTMLElement | null>(null)
  const toolbarRef = ref<HTMLElement | null>(null)

  const popoverCitation = computed(() => {
    const base = report.value.citations.find(c => c.id === activeCitationId.value) ?? null
    if (!base) return null
    // 同一篇論文在不同段落被引用時，優先顯示「被點擊的那一次引用」實際依據的片段，
    // 找不到（mock 資料、非 arXiv 生成的內容）才退回這篇論文的預設摘錄
    const relevantChunk = popoverTarget.value?.dataset.relevantChunk
    return relevantChunk ? { ...base, snippet: relevantChunk } : base
  })
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

  // 編輯模式的富文本工具列（PaperEditor 的 .editor-toolbar）也要 sticky 在這條工具列
  // 下方，但它的高度會隨標題換行變動，所以量測後寫成 CSS 變數，讓子元件的
  // sticky top 可以跟著動態調整，不用寫死一個容易對不上的固定值
  let toolbarResizeObserver: ResizeObserver | null = null

  onMounted(() => {
    if (!toolbarRef.value || !mainRef.value) return
    const updateToolbarHeight = () => {
      mainRef.value?.style.setProperty('--paper-toolbar-height', `${toolbarRef.value?.offsetHeight ?? 0}px`)
    }
    updateToolbarHeight()
    toolbarResizeObserver = new ResizeObserver(updateToolbarHeight)
    toolbarResizeObserver.observe(toolbarRef.value)
  })

  onBeforeUnmount(() => {
    toolbarResizeObserver?.disconnect()
  })

  function onCitationClick ({ citationId, target }: { citationId: string, target: HTMLElement }) {
    if (activeCitationId.value === citationId) {
      activeCitationId.value = null
      return
    }
    activeCitationId.value = citationId
    popoverTarget.value = target
  }

  const citationStyleOptions = Object.entries(citationStyleLabels).map(([value, label]) => ({ value, label }))

  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
  }

  async function onCitationStyleChange (style: string) {
    const previousStyle = report.value.citationStyle
    report.value.citationStyle = style as CitationStyle
    if (!projectId.value) return
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

  async function downloadPdf (): Promise<void> {
    if (!projectId.value || downloadingPdf.value) return
    const root = paginatedViewRef.value?.$el as HTMLElement | undefined
    if (!root) return

    // 關掉可能開著的引用彈窗，避免它被一起複製進匯出的 HTML
    activeCitationId.value = null
    downloadingPdf.value = true
    pdfError.value = null
    try {
      const html = buildPaperExportHtml(root)
      const blob = await downloadReportPdf(projectId.value, html, report.value.title || 'paper')

      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${report.value.title || 'paper'}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      pdfError.value = error instanceof Error ? error.message : 'PDF 下載失敗'
    } finally {
      downloadingPdf.value = false
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
  /* 不設背景，讓 .v-application 的頁面漸層透出來，側邊欄與工具列上的玻璃才有東西可透 */
  .paper-page {
    /* 閱讀欄的寬度由 A4 頁寬（794px）決定，比 --content-measure 寬；
       再加 24px 間距與 280px 評分面板 */
    --paper-column: 1100px;
    min-height: 100vh;
    display: flex;
    gap: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: var(--color-text);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    padding: 12px 20px 18px;
  }

  .paper-toolbar {
    /* .paper-page 只設 min-height，內容一長（尤其編輯模式沒有高度上限）就會撐開
       整頁，變成瀏覽器視窗本身在捲動；工具列要 sticky 才不會跟著捲走。
       .paper-main 不能設 overflow:hidden/auto——那樣它會變成 sticky 的捲動邊界，
       但它本身永遠不會真的捲動（高度就是內容高度），sticky 就會完全失效。
       不做卡片外觀（沒有底色/陰影/模糊）：文字跟按鈕就是直接浮在頁面背景上，
       捲動到底下內容重疊時不再靠模糊/陰影隔開 */
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    max-width: var(--paper-column);
    margin: 0 auto;
    padding: 10px 2px;
    background: transparent;
  }

  .paper-title {
    /* min-width:0 才能讓標題在空間不夠時換行/縮小，而不是撐開整列、
       把 .toolbar-actions 擠到變形（flex item 預設 min-width:auto 不會自己讓步）。
       overflow-wrap:anywhere 是防長標題裡有不含空白/中日韓字元斷點的長字串
       （例如英文專有名詞、無空格的長字串）時，文字會直接溢出這個縮到很窄的
       box，蓋到右邊的 toolbar-actions 按鈕上 */
    flex: 1 1 0;
    min-width: 0;
    overflow-wrap: anywhere;
    margin: 0;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.4;
    color: var(--color-text);
  }

  .toolbar-actions {
    display: flex;
    flex-wrap: wrap;
    /* 不管標題多長都不能被壓縮，按鈕才不會變形 */
    flex-shrink: 0;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    margin-left: auto;
  }

  /* 三段提示都對齊內容欄，不要貼在視窗左緣 */
  .score-error,
  .save-hint,
  .save-error {
    width: 100%;
    max-width: var(--paper-column);
    margin: 10px auto 0;
    font-size: 13px;
  }

  .score-error {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--color-error-text);
  }

  .citation-style-select {
    width: 92px;
  }

  .edit-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .save-hint {
    color: var(--color-warning-text);
  }

  .save-error {
    color: var(--color-error-text);
  }

  /* 骨架屏跟技術報告紙張同一個外框，載入完換上內容時版面不跳 */
  .paper-skeleton {
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
    max-width: var(--paper-column);
    margin: 14px auto 0;
    padding: 28px 34px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }

  .paper-body {
    /* 不設 overflow:auto——寬表格已經有 TipTap 自己的 .tableWrapper { overflow-x:auto }
       擋著，這裡如果也設 overflow，會變成 .editor-toolbar sticky 的捲動邊界，但這個
       box 本身跟 .paper-main 一樣永遠不會真的捲動，sticky 就會失效（同 .paper-main
       overflow:hidden 那個問題） */
    flex: 1;
    min-height: 0;
    display: flex;
    width: 100%;
    max-width: var(--paper-column);
    gap: 24px;
    margin: 14px auto 0;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    padding: 28px 34px;
    height: fit-content;
  }

  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    margin-left: auto;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .paper-body:has(.paper-sheet--paginated) .paper-citations {
    /* 對齊第一張 A4 頁面的頂端：.paginated-paper 有 24px 的上留白 */
    top: 24px;
  }

  .paper-sheet--paginated {
    max-width: none;
    background: none;
    border: none;
    border-radius: 0;
    padding: 0;
    overflow-x: auto;
  }

  /* 固定寬度、不可壓縮（flex:none），跟檢視模式 A4 頁面的內容區同寬：
     794px 頁寬 − 1px×2 border − 96px×2 padding = 670px − 1px×2 border − 34px×2 padding
     = 兩邊都是 600px 內容區，兩種模式排版一致（WYSIWYG）。
     這條規則要放在下面 @media 區塊「之前」：往後若要在該 media query 裡疊加這個
     class 的響應式覆寫，同權重下 CSS 一律看原始碼順序決定勝負，寫在後面的規則即使
     沒被媒體查詢條件挑中也會贏過寫在前面、條件外的規則——把它放前面，媒體查詢裡的
     覆寫才會如預期生效。 */
  .paper-sheet--editing {
    flex: none;
    width: 670px;
  }

  /* .paper-sheet--editing 固定 670px、不可壓縮，跟 280px 評分面板、24px gap 並排
     最少要 974px；再加上左側 210px 側欄跟 .paper-main 左右 40px padding，視窗寬度
     低於 1224px 就會塞不下、觸發 .paper-body 的橫向捲軸。斷點抓 1240px 留一點餘裕，
     讓 row 布局撐不下時能提早切成 column，避免橫向捲軸。 */
  @media (max-width: 1240px) {
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
