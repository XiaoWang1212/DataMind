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
  import { computed, onBeforeUnmount, onMounted, ref, toRaw } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { initFieldMapping, refineFieldMapping } from '@/api/fieldMapping'
  import DatasetPreview from '@/components/hub/fieldMapping/DatasetPreview.vue'
  import MappingChatPanel from '@/components/hub/fieldMapping/MappingChatPanel.vue'
  import MappingTable from '@/components/hub/fieldMapping/MappingTable.vue'
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

  // Project.id 在資料庫裡是 int；useWorkflowStorage 的參數是字串，呼叫時要轉
  const projectId = computed(() => Number(route.params.id ?? 0))
  const draftKey = computed(() => `datamind_field_mapping_draft_${projectId.value}`)

  const loading = ref(true)
  const loadError = ref('')
  const items = ref<MappingItem[]>([])
  const userColumns = ref<UserColumn[]>([])
  const previewColumns = ref<string[]>([])
  const previewRows = ref<string[][]>([])
  const targetName = ref('')
  const datasetFile = ref<File | null>(null)
  const flashed = ref(new Set<string>())
  // 使用者手動選過的變數：後續 AI 建議不覆蓋
  const locked = ref(new Set<string>())

  const aiAvailable = ref(false)
  // 確認並執行失敗時顯示給使用者；下次改選項就清掉，避免舊錯誤一直卡著
  const saveError = ref('')

  const chatHistory = ref<ChatMessage[]>([])
  const chatPending = ref(false)
  const confirming = ref(false)

  // Ctrl+Z 用的快照堆疊。上限避免使用者改很久之後記憶體一直長大
  const MAX_UNDO = 50
  interface Snapshot { items: MappingItem[], locked: string[] }
  const undoStack = ref<Snapshot[]>([])
  const redoStack = ref<Snapshot[]>([])

  // 綠色的兩種：演算法有把握的，和使用者親自點過確認的
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

  /** 順手鎖住：親自確認過的列，後續 AI 建議不該再改動它。 */
  function confirmRow (item: MappingItem): void {
    if (item.status !== 'NEEDS_REVIEW') return
    pushHistory()
    item.status = 'CONFIRMED'
    locked.value.add(item.paper_variable)
    saveError.value = ''
    saveDraft()
  }

  /**
   * 改動前先存快照。沒有復原的話，點錯一步只能整頁重跑。
   *
   * locked 一定要跟著存：只還原 items 的話，復原後那一列看起來回到未對應，
   * 但它還留在 locked 裡，之後所有 AI 建議都會被靜默忽略，而聊天仍回「已更新」。
   */
  function snapshot (): Snapshot {
    return { items: structuredClone(toRaw(items.value)), locked: [...locked.value] }
  }

  function restore (snap: Snapshot): void {
    items.value = snap.items
    locked.value = new Set(snap.locked)
    saveError.value = ''
    saveDraft()
  }

  function pushHistory (): void {
    undoStack.value.push(snapshot())
    if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
    // 做了新動作，原本能重做的那條分支就失效了
    redoStack.value = []
  }

  function undo (): void {
    const previous = undoStack.value.pop()
    if (!previous) return
    redoStack.value.push(snapshot())
    restore(previous)
  }

  function redo (): void {
    const next = redoStack.value.pop()
    if (!next) return
    undoStack.value.push(snapshot())
    restore(next)
  }

  /** 焦點在輸入框時不攔截：那時使用者要復原的是自己打的字。 */
  function onKeydown (event: KeyboardEvent): void {
    if (!(event.metaKey || event.ctrlKey)) return

    // 重做的按法各家不同：Mac 是 ⌘⇧Z，Windows 上 Ctrl+Y 與 Ctrl+Shift+Z 都常見，三種都收
    const key = event.key.toLowerCase()
    const isRedo = (key === 'z' && event.shiftKey) || key === 'y'
    const isUndo = key === 'z' && !event.shiftKey
    if (!isRedo && !isUndo) return

    const target = event.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return

    event.preventDefault()
    if (isRedo) redo()
    else undo()
  }

  /** 按錯了要能反悔，不然使用者只敢把整頁重跑一次。 */
  function unconfirmRow (item: MappingItem): void {
    if (item.status !== 'CONFIRMED') return
    pushHistory()
    item.status = 'NEEDS_REVIEW'
    locked.value.delete(item.paper_variable)
    saveDraft()
  }

  /** 整批當成一步：不然使用者要按 N 次 Ctrl+Z 才回得去 */
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
    // 選到跟現在一樣的東西就什麼都不做。少了這道，使用者只是打開下拉看一眼、
    // 又點回原本那個，「已對應」就會莫名其妙降成「待確認」
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

    // 同一個欄位不能同時服務兩個變數：搶過來，原持有者退回未對應
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
    // 自己從下拉挑的就是已確認：標成「待確認」等於要他確認自己剛做的動作
    item.status = 'CONFIRMED'
    saveDraft()
  }

  /**
   * 存編輯中的草稿。沒有它的話重新整理會把改過的全部沖掉，還會再打一次 Gemini。
   * 真正的結果是按下「確認並執行」才寫進資料庫。
   */
  function saveDraft (): void {
    if (!projectId.value) return
    try {
      localStorage.setItem(draftKey.value, JSON.stringify({
        columns: columnSignature(),
        items: items.value,
        locked: [...locked.value],
        aiAvailable: aiAvailable.value,
      }))
    } catch (error) {
      console.warn('無法保存欄位對映草稿', error)
    }
  }

  function loadDraft (): boolean {
    try {
      const raw = localStorage.getItem(draftKey.value)
      if (!raw) return false
      const saved = JSON.parse(raw) as {
        columns?: string
        items?: MappingItem[]
        locked?: string[]
        aiAvailable?: boolean
      }
      // 換了資料集就不能沿用舊草稿，裡面的欄位名已經對不上了
      if (saved.columns !== columnSignature()) {
        clearDraft()
        return false
      }
      if (!Array.isArray(saved.items) || saved.items.length === 0) return false
      items.value = saved.items
      locked.value = new Set<string>(saved.locked)
      // 沿用當初的可用狀態：寫死 true 的話，Gemini 掛掉時重整會讓離線提示消失、
      // 輸入框又變成可打，送出才發現還是不通
      aiAvailable.value = saved.aiAvailable ?? true
      return true
    } catch {
      localStorage.removeItem(draftKey.value)
      return false
    }
  }

  function columnSignature (): string {
    return userColumns.value.map(c => c.name).join('|')
  }

  function clearDraft (): void {
    localStorage.removeItem(draftKey.value)
  }

  /** 被改動的列閃一下：沒有這個提示，使用者不知道剛才那一步改到了哪裡。 */
  function flash (variable: string): void {
    flashed.value.add(variable)
    setTimeout(() => {
      flashed.value.delete(variable)
      flashed.value = new Set(flashed.value)
    }, 2000)
    flashed.value = new Set(flashed.value)
  }

  /**
   * main.ts 那兩個 load 沒有 await，重新整理時 onMounted 可能先跑完，
   * 拿到空陣列就會誤判成「框架沒有變數清單」。
   */
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

    // target 不在 features 裡時自己補一筆，否則使用者無從指定預測目標
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

  /** 把 AI 回傳的 diff 套用到本地狀態；使用者手動選過的列不覆蓋。 */
  function applyActions (actions: MappingAction[]): string[] {
    const changed: string[] = []
    for (const action of actions) {
      const item = items.value.find(i => i.paper_variable === action.paper_variable)
      if (!item || locked.value.has(item.paper_variable)) continue

      if (action.matched_user_column) {
        // 欄位被手動鎖定的列占用時，整個動作放棄。
        // 只做一半（新的設了、舊的沒清）比什麼都不做更糟。
        const lockedHolder = items.value.find(
          other => other.paper_variable !== item.paper_variable
            && other.matched_user_column === action.matched_user_column
            && locked.value.has(other.paper_variable),
        )
        if (lockedHolder) continue

        // 搶欄位：原持有者退回未對應，同樣要閃給使用者看
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
      // 後端已擋一層，這裡再擋一層：AI 提的對應一律要人確認，不能自己變綠
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
      // 前綴 mapping- 才不會和 ResultView 的聊天撞 key。
      // 那組函式的型別是 { role, text }，這裡是 { role, content }，純本地暫存所以轉型即可。
      saveChatHistoryToStorage(
        `mapping-${projectId.value}`,
        chatHistory.value as unknown as import('@/api/resultAnalysis').ChatMessage[],
      )
    }
  }

  /**
   * 依對映改寫表頭後交給 workflow。
   *
   * 只改名、不刪欄位：使用者沒對應到的欄位在 workflow 那邊還是可以選用，
   * 在這裡刪掉只會讓他失去選擇。
   */
  async function confirmAndRun (): Promise<void> {
    if (!datasetFile.value) return
    confirming.value = true

    const mapping: Record<string, string> = {}
    for (const item of items.value) {
      if (item.matched_user_column && item.status !== 'SKIPPED') {
        mapping[item.paper_variable] = item.matched_user_column
      }
    }

    try {
      saveError.value = ''

      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, column] of Object.entries(mapping)) {
        renameByColumn.set(column, variable)
      }

      // 先改寫檔案再寫資料庫：反過來的話，檔案沒寫成功但對映已存檔，
      // 下次點專案就會帶著沒改過表頭的資料集直接進 workflow，錯得無聲無息
      const renamed = await rewriteDatasetHeader(datasetFile.value, renameByColumn)
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))

      // IndexedDB 寫入失敗只會在 console 留紀錄、不會拋例外，只好回讀確認
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
      // 失敗時本地狀態都已復原，但畫面上必須告訴使用者，
      // 不然按鈕悄悄恢復可按，使用者只會覺得「怎麼沒反應」再按一次
      const detail = error instanceof Error ? error.message : ''
      saveError.value = detail ? `儲存失敗，請再試一次（${detail}）` : '儲存失敗，請再試一次'
    } finally {
      confirming.value = false
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

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
        // 先綁住原始欄位位置：dedup 會改變陣列索引，之後再用索引取值就會取到別欄的資料
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

      // 有草稿就直接還原，不重跑配對：重跑會蓋掉使用者改過的東西，也會白花一次 Gemini
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

  /* 標題、進度、全部確認擠在同一列，把垂直空間留給對映表 */
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

  /* 有人對動態效果敏感（會頭暈）；改成靜態底色淡出，資訊不減 */
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

  /* 尺寸比照 ProjectsView 的 .new-btn。border: none 不能省，<button> 預設帶外框 */
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
