<template>
  <div class="mapping-page">
    <RouterLink class="back-link" to="/hub/projects">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案列表
    </RouterLink>

    <div class="page-header">
      <h1 class="page-title">欄位對齊</h1>
      <span v-if="!loading && !loadError" class="page-progress">
        已確認 {{ confirmedCount }} / {{ items.length }}
        <template v-if="reviewCount > 0">
          <span class="page-progress-sep">·</span>
          <span class="page-progress-review">{{ reviewCount }} 個待確認</span>
        </template>
      </span>
      <button
        v-if="reviewCount > 0"
        class="confirm-all-btn"
        type="button"
        @click="confirmAll"
      >
        全部確認
      </button>
    </div>

    <div v-if="loadError" class="load-error">
      <v-icon icon="mdi-alert-circle-outline" size="20" />
      <span>{{ loadError }}</span>
      <RouterLink to="/hub/projects/new" class="load-error-link">重新上傳資料集</RouterLink>
    </div>

    <div v-else class="mapping-layout">
      <!-- 左：對映表 + 資料預覽 -->
      <section class="mapping-main">
        <div v-if="loading" class="mapping-loading">
          <v-progress-circular indeterminate size="28" color="accent" />
          <span>正在自動配對…</span>
        </div>

        <MappingTable
          v-else
          :flashed="flashed"
          :items="items"
          :target-name="targetName"
          :user-columns="userColumns"
          @confirm="confirmRow"
          @unconfirm="unconfirmRow"
          @update:selection="applySelection"
        />

        <DatasetPreview
          v-if="!loading && previewColumns.length"
          :columns="previewColumns"
          :rows="previewRows"
        />

        <div class="mapping-footer">
          <span v-if="saveError" class="footer-error">{{ saveError }}</span>
          <span v-else-if="unmatchedCount > 0" class="footer-hint">
            還有 {{ unmatchedCount }} 個變數未對應
          </span>
          <button class="confirm-btn" :disabled="!canConfirm || confirming" @click="confirmAndRun">
            {{ confirming ? '處理中…' : '確認並執行' }}
            <v-icon v-if="!confirming" icon="mdi-arrow-right" size="17" />
          </button>
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
  import type {
    ChatMessage,
    MappingAction,
    MappingItem,
    PaperVariable,
    UserColumn,
  } from '@/types/fieldMapping'
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { initFieldMapping, refineFieldMapping } from '@/api/fieldMapping'
  import DatasetPreview from '@/components/hub/fieldMapping/DatasetPreview.vue'
  import MappingChatPanel from '@/components/hub/fieldMapping/MappingChatPanel.vue'
  import MappingTable from '@/components/hub/fieldMapping/MappingTable.vue'
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
  import { readTablePreview, rewriteDatasetHeader } from '@/utils/dataset'

  const route = useRoute()
  const router = useRouter()
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // Project.id 在資料庫是 int，useWorkflowStorage 收字串，呼叫時要轉
  const projectId = computed(() => Number(route.params.id ?? 0))

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
      if (other.paper_variable !== item.paper_variable && other.matched_user_column === value) {
        other.matched_user_column = null
        other.sample_values = []
        other.confidence_score = 0
        other.status = 'UNMATCHED'
        flash(other.paper_variable)
      }
    }

    const column = userColumns.value.find(c => c.name === value)
    item.matched_user_column = value
    item.sample_values = column?.sample_values ?? []
    item.candidate_columns = []
    item.confidence_score = 1
    // 使用者自己選的直接視為已確認，不需要再確認一次自己的操作
    item.status = 'CONFIRMED'
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
      | { features?: { name: string, type?: string }[], target_col?: string }
      | undefined

    const features = workflowJson?.features ?? []
    const targetCol = workflowJson?.target_col ?? ''
    targetName.value = targetCol

    const variables: PaperVariable[] = features.map(feature => ({
      name: feature.name,
      type: feature.type ?? '',
      is_target: feature.name === targetCol,
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
        chatHistory.value as unknown as import('@/api/resultAnalysis').ChatMessage[],
      )
    }
  }

  // 依對映改寫表頭後交給 workflow。
  // 只改名不刪欄位，未對應的欄位在 workflow 仍可選用
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

      // 先改寫檔案再寫資料庫，避免寫檔失敗但對映已存檔，下次用到未改寫的資料集
      const renamed = await rewriteDatasetHeader(datasetFile.value, renameByColumn)
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
      router.push(`/workflow?project=${projectId.value}`)
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
          if (seen.has(name)) return false  // 重複欄位名只留第一個
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
  }

  /* 標題、進度、全部確認排在同一列，把垂直空間留給對映表 */
  .page-header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .page-progress {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .page-progress-sep {
    margin: 0 6px;
    color: #cbd5e1;
  }

  .page-progress-review {
    color: #b45309;
  }

  .confirm-all-btn {
    padding: 5px 12px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #fff;
    color: var(--color-secondary);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.15s, border-color 0.15s;
  }

  .confirm-all-btn:hover {
    background: #f0f1f3;
    border-color: #94a3b8;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--color-secondary);
    font-size: 13px;
    text-decoration: none;
  }

  .page-title {
    font-size: 19px;
    font-weight: 700;
    color: var(--color-text);
  }

  .load-error {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px;
    border: 1px solid #fecaca;
    border-radius: 12px;
    background: #fef2f2;
    color: #b91c1c;
    font-size: 14px;
  }

  .load-error-link {
    color: #b91c1c;
    font-weight: 600;
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
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    background: #fff;
  }

  .mapping-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 0;
    justify-content: center;
    color: var(--color-secondary);
    font-size: 14px;
  }

  @media (prefers-reduced-motion: reduce) {
    .confirm-all-btn {
      transition: none;
    }
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
    color: #b91c1c;
  }

  .footer-error {
    font-size: 12px;
    color: #b91c1c;
    font-weight: 600;
  }

  /* 尺寸比照 ProjectsView 的 .new-btn，border: none 不能省，button 預設帶外框 */
  .confirm-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 38px;
    padding: 0 18px;
    border: none;
    border-radius: 7px;
    background: var(--color-accent);
    color: #ffffff;
    font-size: 13.5px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
  }

  .confirm-btn:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }

  .confirm-btn:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
</style>
