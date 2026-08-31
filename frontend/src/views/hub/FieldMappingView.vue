<template>
  <div class="mapping-page">
    <PageHeader
      :subtitle="INTRO"
      title="欄位對齊"
    >
      <template #back>
        <RouterLink class="back-link" to="/hub/projects">
          <v-icon icon="mdi-arrow-left" size="15" />
          返回專案列表
        </RouterLink>
      </template>
      <template #meta>
        <span v-if="!loading && !loadError" class="page-progress">
          已確認 {{ confirmedCount }} / {{ items.length }}
          <template v-if="reviewCount > 0">
            <span class="page-progress-sep">·</span>
            <span class="page-progress-review">{{ reviewCount }} 個待確認</span>
          </template>
        </span>
        <AppButton v-if="reviewCount > 0" variant="secondary" @click="confirmAll">
          全部確認
        </AppButton>
      </template>
    </PageHeader>

    <div v-if="loadError" class="load-error">
      <v-icon icon="mdi-alert-circle-outline" size="20" />
      <span>{{ loadError }}</span>
      <RouterLink class="load-error-link" to="/hub/projects/new">重新上傳資料集</RouterLink>
    </div>

    <div v-else class="mapping-layout">
      <!-- 左：對映表 + 資料預覽 -->
      <section class="mapping-main">
        <!-- 骨架屏用五行模擬對映表的列，載入前後的版面高度才接近 -->
        <div v-if="loading" aria-live="polite" class="mapping-skeleton" role="status">
          <!-- 對齊要跑三層（比名字、看資料、問 AI），最久的那層要等 Gemini 回來。
               輪替的階段文字讓等待有東西可看，也順便說明系統在做什麼 -->
          <p class="skeleton-caption">{{ LOADING_CAPTIONS[captionIndex] }}</p>
          <div v-for="n in 5" :key="n" class="skeleton-line" />
        </div>

        <MappingTable
          v-else
          :flashed="flashed"
          :items="items"
          :target-name="targetName"
          :user-columns="userColumns"
          @add-custom="addCustomVariable"
          @confirm="confirmRow"
          @remove-custom="removeCustomVariable"
          @unconfirm="unconfirmRow"
          @update:selection="applySelection"
        />

        <DatasetPreview
          v-if="!loading && previewColumns.length > 0"
          :columns="previewColumns"
          :rows="previewRows"
        />

        <div class="mapping-footer">
          <span v-if="saveError" class="footer-error">{{ saveError }}</span>
          <span v-else-if="unmatchedCount > 0" class="footer-hint">
            還有 {{ unmatchedCount }} 個變數未對應
          </span>
          <span v-else-if="!loading && unusedColumns.length > 0" class="footer-hint footer-hint--neutral">
            送出後將移除 {{ unusedColumns.length }} 個未使用欄位（{{ unusedColumnNames }}）
          </span>
          <AppButton variant="ghost" @click="skipToWorkflow">
            略過（開發用）
          </AppButton>
          <AppButton :disabled="!canConfirm || confirming" variant="primary" @click="confirmAndRun">
            {{ confirming ? '處理中…' : '確認並執行' }}
            <v-icon v-if="!confirming" icon="mdi-arrow-right" size="17" />
          </AppButton>
        </div>
      </section>

      <!-- 右：AI 對話 -->
      <MappingChatPanel
        :available="aiAvailable"
        :history="chatHistory"
        :loading="loading"
        :pending="chatPending"
        @send="sendMessage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { ChatMessage as StoredChatMessage } from '@/api/resultAnalysis'
  import type {
    ChatMessage,
    MappingAction,
    MappingItem,
    PaperVariable,
    UserColumn,
  } from '@/types/fieldMapping'
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { initFieldMapping, refineFieldMapping } from '@/api/fieldMapping'
  import DatasetPreview from '@/components/hub/fieldMapping/DatasetPreview.vue'
  import MappingChatPanel from '@/components/hub/fieldMapping/MappingChatPanel.vue'
  import MappingTable from '@/components/hub/fieldMapping/MappingTable.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { useMappingDraft } from '@/composables/fieldMapping/useMappingDraft'
  import { useMappingHistory } from '@/composables/fieldMapping/useMappingHistory'
  import {
    loadChatHistoryFromStorage,
    loadWorkflowDataFileFromStorage,
    saveChatHistoryToStorage,
    saveWorkflowDataFileToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { SKIP_VALUE } from '@/types/fieldMapping'
  import { readTablePreview, rewriteDataset } from '@/utils/dataset'

  const route = useRoute()
  const router = useRouter()
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // Project.id 在資料庫是 int，useWorkflowStorage 收字串，呼叫時要轉
  const projectId = computed(() => Number(route.params.id ?? 0))

  // 不手動斷行，讓它自己折：頁首佔太多高度會把表格擠下去
  const INTRO = '建立論文變數與資料表欄位的對應關係，後續工作流程才能以論文的變數名稱讀取資料。'
    + '系統已自動比對一輪，AI 依語意建議的對應標示為待確認，請逐項檢查後確認。'
    + '若略過此步驟，資料表將維持原本的欄位直接進入工作流程。'

  const loading = ref(true)
  const loadError = ref('')
  const items = ref<MappingItem[]>([])
  const userColumns = ref<UserColumn[]>([])
  const previewColumns = ref<string[]>([])
  const previewRows = ref<string[][]>([])
  const targetName = ref('')
  const datasetFile = ref<File | null>(null)
  const flashed = ref(new Set<string>())
  // 使用者手動選過的變數，後續 AI 建議不覆蓋
  const locked = ref(new Set<string>())

  const aiAvailable = ref(false)
  // 確認並執行失敗時顯示，下次改動就清掉，避免舊錯誤一直留著
  const saveError = ref('')

  const chatHistory = ref<ChatMessage[]>([])
  const chatPending = ref(false)
  const confirming = ref(false)

  // 對應 field_mapping_service 的三層：比名字、看資料、問 Gemini
  const LOADING_CAPTIONS = [
    '比對欄位名稱…',
    '檢查資料型態是否相符…',
    '請 AI 判讀縮寫與同義詞…',
  ]
  const CAPTION_INTERVAL_MS = 2400

  const captionIndex = ref(0)
  let captionTimer: number | undefined

  // 停在最後一句而不是繞回第一句：轉回去會讓人以為卡住重跑了
  function advanceCaption (): void {
    if (captionIndex.value < LOADING_CAPTIONS.length - 1) captionIndex.value += 1
  }

  watch(loading, isLoading => {
    window.clearInterval(captionTimer)
    captionTimer = undefined
    if (isLoading) {
      captionIndex.value = 0
      captionTimer = window.setInterval(advanceCaption, CAPTION_INTERVAL_MS)
    }
  }, { immediate: true })

  onUnmounted(() => window.clearInterval(captionTimer))

  const { saveDraft, loadDraft, clearDraft } = useMappingDraft({
    projectId,
    items,
    locked,
    aiAvailable,
    userColumns,
  })

  const { pushHistory } = useMappingHistory({
    items,
    locked,
    onRestore: () => {
      saveError.value = ''
      saveDraft()
    },
  })

  // 顯示為綠色的兩種狀態，自動配對成功的與使用者確認過的
  const confirmedCount = computed(
    () => items.value.filter(
      i => i.status === 'AUTO_MATCHED' || i.status === 'CONFIRMED',
    ).length,
  )
  const reviewCount = computed(
    () => items.value.filter(i => i.status === 'NEEDS_REVIEW').length,
  )
  const unmatchedCount = computed(
    () => items.value.filter(i => i.status === 'UNMATCHED').length,
  )
  const canConfirm = computed(() => !loading.value && unmatchedCount.value === 0)

  // 沒被任何變數（含自訂變數）認領的原始欄位，確認後會被移除
  const unusedColumns = computed(() => {
    const used = new Set(
      items.value.filter(i => i.matched_user_column).map(i => i.matched_user_column as string),
    )
    return userColumns.value.filter(c => !used.has(c.name))
  })
  const unusedColumnNames = computed(() => unusedColumns.value.map(c => c.name).join('、'))

  // 確認過的列一併鎖住，後續 AI 建議不再改動
  function confirmRow (item: MappingItem): void {
    if (item.status !== 'NEEDS_REVIEW') return
    pushHistory()
    item.status = 'CONFIRMED'
    locked.value.add(item.paper_variable)
    saveError.value = ''
    saveDraft()
  }

  // 讓使用者能取消確認，避免只能整頁重跑
  function unconfirmRow (item: MappingItem): void {
    if (item.status !== 'CONFIRMED') return
    pushHistory()
    item.status = 'NEEDS_REVIEW'
    locked.value.delete(item.paper_variable)
    saveDraft()
  }

  // 使用者整批修改當作一步，避免使用者需要多按 Ctrl+Z
  function confirmAll (): void {
    if (reviewCount.value === 0) return
    pushHistory()
    for (const item of items.value) {
      if (item.status === 'NEEDS_REVIEW') {
        item.status = 'CONFIRMED'
        locked.value.add(item.paper_variable)
      }
    }
    saveError.value = ''
    saveDraft()
  }

  // 使用者自己想抓某個欄位、框架又沒定義對應變數時，讓他自己加一列
  function addCustomVariable (): void {
    pushHistory()
    items.value.push({
      paper_variable: '',
      required_type: '',
      matched_user_column: null,
      confidence_score: 0,
      status: 'UNMATCHED',
      sample_values: [],
      candidate_columns: [],
      definition: null,
      is_custom: true,
    })
    saveError.value = ''
    saveDraft()
  }

  function removeCustomVariable (item: MappingItem): void {
    if (!item.is_custom) return
    pushHistory()
    const index = items.value.indexOf(item)
    if (index === -1) return
    items.value.splice(index, 1)
    locked.value.delete(item.paper_variable)
    saveError.value = ''
    saveDraft()
  }

  // 自訂變數的名稱直接沿用欄位原名；跟別的變數撞名時加序號避免蓋掉對方的對映
  function uniqueCustomName (base: string, excludeItem: MappingItem): string {
    const used = new Set(
      items.value.filter(i => i !== excludeItem).map(i => i.paper_variable),
    )
    if (!used.has(base)) return base
    let serial = 2
    while (used.has(`${base}_${serial}`)) serial += 1
    return `${base}_${serial}`
  }

  function applySelection (item: MappingItem, value: string): void {
    // 選到跟目前相同的值就不處理，避免重新點選同一欄位時狀態被降級
    const unchanged = value === SKIP_VALUE
      ? item.status === 'SKIPPED'
      : value === item.matched_user_column
    if (unchanged) return

    pushHistory()
    locked.value.add(item.paper_variable)
    saveError.value = ''

    if (value === SKIP_VALUE) {
      item.matched_user_column = null
      item.sample_values = []
      item.candidate_columns = []
      item.confidence_score = 0
      item.status = 'SKIPPED'
      saveDraft()
      return
    }

    // 一個欄位只能對應一個變數，原本對應到的變數退回未對應
    for (const other of items.value) {
      if (other !== item && other.matched_user_column === value) {
        flash(other.paper_variable)
        other.matched_user_column = null
        other.sample_values = []
        other.confidence_score = 0
        other.status = 'UNMATCHED'
        // 自訂變數的名稱是借欄位名來的，欄位被搶走了名稱也跟著清掉
        if (other.is_custom) other.paper_variable = ''
      }
    }

    const column = userColumns.value.find(c => c.name === value)
    item.matched_user_column = value
    item.sample_values = column?.sample_values ?? []
    item.candidate_columns = []
    item.confidence_score = 1
    // 使用者自己選的直接視為已確認，不需要再確認一次自己的操作
    item.status = 'CONFIRMED'
    // 自訂變數不用手動命名，直接沿用選到的欄位名稱
    if (item.is_custom) item.paper_variable = uniqueCustomName(value, item)
    saveDraft()
  }

  // 讓被改動的列閃一下，提示改到哪些欄位
  function flash (variable: string): void {
    flashed.value.add(variable)
    setTimeout(() => {
      flashed.value.delete(variable)
      flashed.value = new Set(flashed.value)
    }, 2000)
    flashed.value = new Set(flashed.value)
  }

  // main.ts 的兩個 load 沒有 await，重整時 onMounted 可能先跑完而拿到空陣列
  async function ensureStoresLoaded (): Promise<void> {
    const waiting: Promise<void>[] = []
    if (projectStore.projects.length === 0) waiting.push(projectStore.loadProjects())
    if (frameworkStore.frameworks.length === 0) waiting.push(frameworkStore.loadFrameworks())
    if (waiting.length > 0) await Promise.all(waiting)
  }

  function buildPaperVariables (): PaperVariable[] {
    const project = projectStore.projects.find(p => p.id === projectId.value)
    const framework = frameworkStore.frameworks.find(f => f.id === project?.frameworkId)
    const workflowJson = framework?.workflowJson as
      | {
        features?: { name: string, type?: string, description_zh?: string, descriptionZh?: string }[]
      target_col?: string
      }
      | undefined

    const features = workflowJson?.features ?? []
    const targetCol = workflowJson?.target_col ?? ''
    targetName.value = targetCol

    const variables: PaperVariable[] = features.map(feature => ({
      name: feature.name,
      type: feature.type ?? '',
      is_target: feature.name === targetCol,
      // workflow_json 內層欄位不是 camelCase，descriptionZh 只是防禦性 fallback，
      // 跟現有的 target_col ?? targetCol 是同一套慣例
      definition: feature.description_zh ?? feature.descriptionZh,
    }))

    // 預測目標不在 features 裡時補一筆，否則使用者無從指定
    if (targetCol && !features.some(f => f.name === targetCol)) {
      variables.unshift({ name: targetCol, type: 'categorical', is_target: true })
    }
    return variables
  }

  async function loadDataset (): Promise<File | null> {
    const ctx = projectStore.activeContext
    if (ctx?.datasetFile) return ctx.datasetFile
    return await loadWorkflowDataFileFromStorage(String(projectId.value))
  }

  // 把 AI 回傳的異動套用到本地狀態，使用者手動選過的列不覆蓋
  function applyActions (actions: MappingAction[]): string[] {
    const changed: string[] = []
    for (const action of actions) {
      const item = items.value.find(i => i.paper_variable === action.paper_variable)
      if (!item || locked.value.has(item.paper_variable)) continue

      if (action.matched_user_column) {
        // 欄位被鎖定的列占用時整個動作放棄，避免只完成一半
        const lockedHolder = items.value.find(
          other => other.paper_variable !== item.paper_variable
            && other.matched_user_column === action.matched_user_column
            && locked.value.has(other.paper_variable),
        )
        if (lockedHolder) continue

        // 原本對應到的變數退回未對應，同樣閃一下提示使用者
        for (const other of items.value) {
          if (
            other.paper_variable !== item.paper_variable
            && other.matched_user_column === action.matched_user_column
          ) {
            other.matched_user_column = null
            other.sample_values = []
            other.confidence_score = 0
            other.status = 'UNMATCHED'
            changed.push(other.paper_variable)
          }
        }
        const column = userColumns.value.find(c => c.name === action.matched_user_column)
        item.matched_user_column = action.matched_user_column
        item.sample_values = column?.sample_values ?? []
        item.candidate_columns = []
      } else {
        item.matched_user_column = null
        item.sample_values = []
      }

      item.confidence_score = action.confidence_score
      // AI 提的對應一律要人確認，不直接標為已對應（後端也有擋一層）
      item.status = action.status === 'AUTO_MATCHED' ? 'NEEDS_REVIEW' : action.status
      changed.push(item.paper_variable)
    }
    return changed
  }

  async function sendMessage (message: string): Promise<void> {
    chatHistory.value.push({ role: 'user', content: message })
    chatPending.value = true

    try {
      const { actions, reply } = await refineFieldMapping({
        mappingState: {
          total_required: items.value.length,
          matched_count: confirmedCount.value,
          mapping_status: items.value,
        },
        userColumns: userColumns.value,
        userMessage: message,
        chatHistory: chatHistory.value.slice(0, -1),
      })
      if (actions.length > 0) pushHistory()
      const changed = applyActions(actions)
      for (const variable of changed) flash(variable)
      if (changed.length > 0) saveDraft()
      chatHistory.value.push({ role: 'assistant', content: reply })
    } catch (error) {
      chatHistory.value.push({
        role: 'assistant',
        content: error instanceof Error ? error.message : 'AI 目前無法回應，請改用下拉選單。',
      })
    } finally {
      chatPending.value = false
      // 前綴 mapping- 避免和 ResultView 的聊天撞 key。
      // 那組函式的型別是 { role, text }，這裡是 { role, content }，純本地暫存故直接轉型
      saveChatHistoryToStorage(
        `mapping-${projectId.value}`,
        chatHistory.value as unknown as StoredChatMessage[],
      )
    }
  }

  /**
   * 開發用斷點：不改表頭、不存 column_mapping，直接跳去 workflow。
   *
   * 還是要設 activeContext，否則 WorkflowWorkspace 找不到框架設定，
   * models/preprocessing 節點就不會被載入（跟 confirmAndRun 一樣的機制，
   * 只是這裡帶原始未改名的 datasetFile）。
   */
  function skipToWorkflow (): void {
    const project = projectStore.projects.find(p => p.id === projectId.value)
    projectStore.setActiveContext({
      projectId: projectId.value,
      datasetFile: datasetFile.value,
      frameworkId: project?.frameworkId ?? null,
    })
    // 用 replace 而不是 push：離開欄位對齊頁後，瀏覽器上一頁不該再跳回這個中繼頁
    router.replace(`/workflow?project=${projectId.value}`)
  }

  // 依對映改寫表頭、移除未使用欄位後交給 workflow
  async function confirmAndRun (): Promise<void> {
    if (!datasetFile.value) return
    confirming.value = true

    const mapping: Record<string, { column: string, type: string }> = {}
    for (const item of items.value) {
      if (item.matched_user_column && item.status !== 'SKIPPED') {
        mapping[item.paper_variable] = { column: item.matched_user_column, type: item.required_type }
      }
    }

    try {
      saveError.value = ''

      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, info] of Object.entries(mapping)) {
        renameByColumn.set(info.column, variable)
      }

      // 沒被任何變數（含自訂變數）認領的原始欄位，之後在 workflow 就不會再出現
      const dropColumns = new Set(unusedColumns.value.map(c => c.name))

      // 先改寫檔案再寫資料庫，避免寫檔失敗但對映已存檔，下次用到未改寫的資料集
      const renamed = await rewriteDataset(datasetFile.value, renameByColumn, dropColumns)
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))

      // IndexedDB 寫入失敗不會拋例外，只在 console 留紀錄，因此回讀確認
      const stored = await loadWorkflowDataFileFromStorage(String(projectId.value))
      if (!stored || stored.size !== renamed.size) {
        throw new Error('資料檔案沒有存進瀏覽器儲存空間')
      }

      await projectStore.saveColumnMapping(projectId.value, mapping)
      projectStore.setActiveContext({
        projectId: projectId.value,
        datasetFile: renamed,
        frameworkId:
          projectStore.projects.find(p => p.id === projectId.value)?.frameworkId ?? null,
      })

      // 已經寫進資料庫了，草稿不用留
      clearDraft()
      // 用 replace 而不是 push：欄位對齊完成後這一步已經處理完（資料已存檔、草稿已清），
      // 瀏覽器上一頁不該讓使用者跳回一個「已經對齊過」的頁面
      router.replace(`/workflow?project=${projectId.value}`)
    } catch (error) {
      // 本地狀態雖已復原，仍要顯示錯誤，避免按鈕恢復可按卻沒有任何說明
      const detail = error instanceof Error ? error.message : ''
      saveError.value = detail ? `儲存失敗，請再試一次（${detail}）` : '儲存失敗，請再試一次'
    } finally {
      confirming.value = false
    }
  }

  onMounted(async () => {
    try {
      await ensureStoresLoaded()

      // 對映已經送出過（後端存過 columnMapping）就不要重跑：這時資料集已經被改寫過
      // 一次（改名+刪欄位），拿改寫後的檔案重新配對只會得到不對的結果。用 replace
      // 蓋掉這筆歷史紀錄，瀏覽器上一頁才不會又繞回這個頁面
      const project = projectStore.projects.find(p => p.id === projectId.value)
      if (project?.columnMapping) {
        router.replace(`/workflow?project=${projectId.value}`)
        return
      }

      // 同上，回傳型別是 ResultView 那組，轉成本頁的形狀
      chatHistory.value = loadChatHistoryFromStorage(
        `mapping-${projectId.value}`,
      ) as unknown as ChatMessage[]

      const file = await loadDataset()
      if (!file) {
        loadError.value = '找不到資料集，請回上一步重新上傳。'
        loading.value = false
        return
      }
      datasetFile.value = file

      const preview = await readTablePreview(file, 5)
      if (preview.columns.length === 0) {
        loadError.value = '資料集沒有欄位，請確認檔案內容。'
        loading.value = false
        return
      }
      previewColumns.value = preview.columns
      previewRows.value = preview.rows

      const seen = new Set<string>()
      userColumns.value = preview.columns
        // 先記住原始欄位位置，去重會改變索引，之後用索引取值會取到別欄的資料
        .map((name, index) => ({ name, index }))
        .filter(({ name }) => {
          if (seen.has(name)) return false // 重複欄位名只留第一個
          seen.add(name)
          return true
        })
        .map(({ name, index }) => ({
          name,
          sample_values: preview.rows.map(row => row[index] ?? '').filter(Boolean),
        }))

      const paperVariables = buildPaperVariables()
      if (paperVariables.length === 0) {
        loadError.value = '此框架未擷取到變數清單，請回論文分析重新擷取。'
        loading.value = false
        return
      }

      // 有草稿就直接還原不重跑配對，避免蓋掉使用者的改動並多打一次 Gemini
      if (loadDraft()) return

      const { state, aiAvailable: available } = await initFieldMapping({
        paperVariables,
        userColumns: userColumns.value,
      })
      items.value = state.mapping_status
      aiAvailable.value = available
      saveDraft()
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : '欄位對齊初始化失敗'
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .mapping-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: var(--content-max-width-wide);
    margin-inline: auto;
  }

  .page-progress {
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .page-progress-sep {
    margin: 0 6px;
    color: var(--color-border-strong);
  }

  .page-progress-review {
    color: var(--color-warning-text);
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    /* 對齊 22px 標題的第一行中線 */
    margin-top: 4px;
    color: var(--color-ink-soft);
    font-size: 13px;
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .back-link:hover {
    color: var(--color-ink);
  }

  .load-error {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px;
    /* 邊框取比底色深一階的混色，否則與底色同值會看不出區塊邊界 */
    border: 1px solid color-mix(in oklab, var(--color-error) 20%, var(--color-error-bg));
    border-radius: var(--radius-md);
    background: var(--color-error-bg);
    color: var(--color-error-text);
    font-size: 14px;
  }

  .load-error-link {
    color: var(--color-error-text);
    font-weight: 500;
  }

  /* 這一頁的副標比其他頁長，上下間距各自調：PageHeader 的預設值是給一行短句用的，
     不動元件本身，避免影響其他頁 */
  .mapping-page :deep(.page-header) {
    margin-bottom: 16px;
  }

  .mapping-page :deep(.page-header-titlerow) {
    margin-bottom: 8px;
  }

  .mapping-page :deep(.page-header-sub) {
    max-width: var(--content-measure);
    line-height: 1.6;
    white-space: pre-line;
  }

  .mapping-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 18px;
    align-items: start;
  }

  .mapping-main {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  /* 表格切齊卡片邊緣，不要在外框內再留一圈白邊看起來像卡中卡。
     負邊距寫在這裡而不是子元件裡：padding 是這張卡的，子元件不該去猜它的值 */
  /* 表格切齊卡片邊緣。overflow 讓表格的方角被卡片圓角裁掉 */
  .mapping-main {
    overflow: hidden;
  }

  .mapping-main :deep(.table-shell) {
    margin-inline: -18px;
  }

  .mapping-main > :deep(.table-shell:first-child) {
    margin-top: -18px;
  }

  /* 表頭底色與 row hover 滿版到卡片邊，但首尾欄的內容補回卡片內距，
     不要讓文字貼著外框 */
  .mapping-main :deep(.ds-table th:first-child),
  .mapping-main :deep(.ds-table td:first-child) {
    padding-left: 32px;
  }

  .mapping-main :deep(.ds-table th:last-child),
  .mapping-main :deep(.ds-table td:last-child) {
    padding-right: 18px;
  }

  .mapping-skeleton {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px;
  }

  .mapping-skeleton .skeleton-line {
    height: 20px;
  }

  .skeleton-caption {
    margin: 0 0 2px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .mapping-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 8px;
  }

  .footer-hint {
    font-size: 12px;
    color: var(--color-error-text);
  }

  /* 移除欄位只是提醒、不是擋著不給送出的錯誤，用中性色跟上面那個未對應提示區隔 */
  .footer-hint--neutral {
    color: var(--color-ink-soft);
  }

  .footer-error {
    font-size: 12px;
    color: var(--color-error-text);
    font-weight: 500;
  }
</style>
