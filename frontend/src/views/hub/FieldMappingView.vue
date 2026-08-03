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

        <div v-else class="mapping-scroll">
        <table class="mapping-table">
          <thead>
            <tr>
              <th class="col-var">論文變數</th>
              <th class="col-col">你的欄位</th>
              <th class="col-status">狀態</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedItems"
              :key="item.paper_variable"
              :class="{ 'row-flash': flashed.has(item.paper_variable) }"
            >
              <td class="col-var">
                <span
                  v-if="isTarget(item)"
                  aria-label="預測目標"
                  class="target-badge"
                  role="img"
                >★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
              <td class="col-col">
                <CustomSelect
                  :aria-label="`${item.paper_variable} 對應到的資料表欄位`"
                  :highlight="item.status === 'UNMATCHED'"
                  :model-value="item.matched_user_column ?? selectionKey(item)"
                  :options="optionsFor(item)"
                  placeholder="請選擇"
                  @update:model-value="value => applySelection(item, value)"
                />
                <div v-if="item.sample_values.length" class="col-samples">
                  {{ item.sample_values.slice(0, 3).join('、') }}
                </div>
              </td>
              <td class="col-status">
                <div class="status-cell">
                  <!-- 用 v-tooltip 而非 CSS 絕對定位：外層 .mapping-scroll 有 overflow，
                       自製的提示會被裁掉，v-tooltip 會 teleport 出去 -->
                  <v-tooltip
                    content-class="status-tooltip"
                    location="bottom end"
                    max-width="210"
                    :text="STATUS_HINT[item.status]"
                  >
                    <template #activator="{ props }">
                      <span
                        v-bind="props"
                        class="status-chip"
                        :class="`status-chip--${item.status.toLowerCase()}`"
                        tabindex="0"
                      >
                        {{ STATUS_LABEL[item.status] }}
                      </span>
                    </template>
                  </v-tooltip>
                  <button
                    v-if="item.status === 'NEEDS_REVIEW'"
                    :aria-label="`${item.paper_variable}：對應正確，標記為已確認`"
                    class="check-btn"
                    title="對應正確，標記為已確認"
                    type="button"
                    @click="confirmRow(item)"
                  >
                    <v-icon icon="mdi-check" size="16" />
                  </button>
                  <button
                    v-else-if="item.status === 'CONFIRMED'"
                    :aria-label="`${item.paper_variable}：取消確認`"
                    class="undo-btn"
                    title="取消確認"
                    type="button"
                    @click="unconfirmRow(item)"
                  >
                    <v-icon icon="mdi-undo-variant" size="14" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        </div>

        <div v-if="!loading && previewColumns.length" class="preview-block">
          <div class="preview-title">資料預覽（前 {{ previewRows.length }} 筆）</div>
          <div class="preview-scroll">
            <table class="preview-table">
              <thead>
                <tr><th v-for="col in previewColumns" :key="col">{{ col }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in previewRows" :key="i">
                  <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

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
      <aside class="mapping-chat">
        <div class="chat-head">
          <div class="chat-head-icon">
            <v-icon icon="mdi-chat-processing-outline" size="18" />
          </div>
          <span>AI 助理</span>
        </div>

        <div v-if="!aiAvailable" class="chat-offline">
          AI 建議暫時無法使用，可用左側下拉選單手動對應。
        </div>

        <div ref="chatScroll" class="chat-body">
          <div
            v-for="(message, i) in chatHistory"
            :key="i"
            class="chat-bubble"
            :class="`chat-bubble--${message.role}`"
          >
            {{ message.content }}
          </div>
          <div v-if="chatPending" class="chat-bubble chat-bubble--assistant chat-bubble--pending">
            思考中…
          </div>
        </div>

        <form class="chat-input" @submit.prevent="sendMessage">
          <input
            v-model="chatDraft"
            class="chat-field"
            :disabled="!aiAvailable || chatPending"
            placeholder="例如：Braden 分數是 braden_total"
          />
          <button
            class="chat-send"
            type="submit"
            :disabled="!aiAvailable || chatPending || !chatDraft.trim()"
          >
            送出
          </button>
        </form>
      </aside>
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
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRaw } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { initFieldMapping, refineFieldMapping } from '@/api/fieldMapping'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import {
    loadChatHistoryFromStorage,
    loadWorkflowDataFileFromStorage,
    saveChatHistoryToStorage,
    saveWorkflowDataFileToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { decodeFileText, parseCsvLine, parseCsvPreview } from '@/utils/csv'

  const SKIP_VALUE = '__skip__'

  const STATUS_LABEL: Record<string, string> = {
    CONFIRMED: '已確認',
    AUTO_MATCHED: '已對應',
    NEEDS_REVIEW: '待確認',
    UNMATCHED: '未對應',
    SKIPPED: '不使用',
  }

  // 滑過標籤時顯示。避免「信心度」這類系統內部用語，但維持正式的語氣
  const STATUS_HINT: Record<string, string> = {
    CONFIRMED: '您已確認此對應正確。如需修改，請點選右側的復原按鈕。',
    AUTO_MATCHED: '欄位名稱與資料內容皆相符，可直接使用。',
    NEEDS_REVIEW: '兩邊名稱不同，此為 AI 依語意提供的建議對應，請確認無誤後點選右側的勾選按鈕。',
    UNMATCHED: '資料表中沒有相符的欄位，請由左側選單自行指定。',
    SKIPPED: '您已指定資料表中沒有此變數，執行時將會略過。',
  }

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
  const chatDraft = ref('')
  const chatPending = ref(false)
  const chatScroll = ref<HTMLElement | null>(null)
  const confirming = ref(false)

  // Ctrl+Z 用的快照堆疊。上限避免使用者改很久之後記憶體一直長大
  const MAX_UNDO = 50
  const undoStack = ref<MappingItem[][]>([])

  function isTarget (item: MappingItem): boolean {
    return item.paper_variable === targetName.value
  }

  // target 永遠排最前面：它配錯的話整個實驗都白做，不能混在幾十列裡被滑過去
  const sortedItems = computed(() => {
    const list = [...items.value]
    list.sort((a, b) => Number(isTarget(b)) - Number(isTarget(a)))
    return list
  })

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

  function selectionKey (item: MappingItem): string {
    return item.status === 'SKIPPED' ? SKIP_VALUE : ''
  }

  function optionsFor (item: MappingItem) {
    const taken = new Map<string, string>()
    for (const other of items.value) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column) {
        taken.set(other.matched_user_column, other.paper_variable)
      }
    }
    const options = userColumns.value.map(column => ({
      value: column.name,
      label: taken.has(column.name)
        ? `${column.name}（已對應至 ${taken.get(column.name)}）`
        : column.name,
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '資料表中沒有此變數' })
    }
    return options
  }

  /**
   * 使用者看過這一列、覺得沒問題。
   *
   * 順手鎖住：既然已經親自確認過，後續 AI 建議就不該再改動它。
   */
  function confirmRow (item: MappingItem): void {
    if (item.status !== 'NEEDS_REVIEW') return
    pushHistory()
    item.status = 'CONFIRMED'
    locked.value.add(item.paper_variable)
    saveError.value = ''
    saveDraft()
  }

  /**
   * 每次改動前先存一份快照，供 Ctrl+Z 復原。
   *
   * 這一頁是「一連串小編輯」的操作，使用者難免點錯；沒有復原的話，
   * 唯一的退路是把整頁重跑，等於把先前的確認全部作廢。
   */
  function pushHistory (): void {
    undoStack.value.push(structuredClone(toRaw(items.value)))
    if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
  }

  function undo (): void {
    const previous = undoStack.value.pop()
    if (!previous) return
    items.value = previous
    saveError.value = ''
    saveDraft()
  }

  /**
   * 焦點在輸入框時不攔截 —— 那時候使用者要復原的是自己打的字，
   * 那是瀏覽器的事，搶過來會很難用。
   */
  function onKeydown (event: KeyboardEvent): void {
    const key = event.key.toLowerCase()
    if (key !== 'z' || !(event.metaKey || event.ctrlKey) || event.shiftKey) return

    const target = event.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return

    event.preventDefault()
    undo()
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
    item.status = 'NEEDS_REVIEW'
    saveDraft()
  }

  /**
   * 把編輯中的對映存進瀏覽器。
   *
   * 沒有這個的話，使用者在這一頁按重新整理就會前功盡棄：手動改的全部消失，
   * 而且會再打一次 Gemini。存的是「還沒按確認並執行」的草稿，
   * 真正的結果在按下按鈕時才寫進資料庫。
   */
  function saveDraft (): void {
    if (!projectId.value) return
    try {
      localStorage.setItem(draftKey.value, JSON.stringify({
        columns: columnSignature(),
        items: items.value,
        locked: [...locked.value],
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
      }
      // 換了資料集就不能沿用舊草稿，裡面的欄位名已經對不上了
      if (saved.columns !== columnSignature()) {
        clearDraft()
        return false
      }
      if (!Array.isArray(saved.items) || saved.items.length === 0) return false
      items.value = saved.items
      locked.value = new Set<string>(saved.locked)
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
   * 確保 store 已經載好。
   *
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
      item.status = action.status
      changed.push(item.paper_variable)
    }
    return changed
  }

  async function sendMessage (): Promise<void> {
    const message = chatDraft.value.trim()
    if (!message || chatPending.value) return

    chatDraft.value = ''
    chatHistory.value.push({ role: 'user', content: message })
    chatPending.value = true
    await scrollChatToBottom()

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
      await scrollChatToBottom()
    }
  }

  async function scrollChatToBottom (): Promise<void> {
    await nextTick()
    if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight
  }

  /**
   * 依對映改寫 CSV 表頭後交給 workflow。
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
      await projectStore.saveColumnMapping(projectId.value, mapping)
      saveError.value = ''

      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, column] of Object.entries(mapping)) {
        renameByColumn.set(column, variable)
      }

      const text = await decodeFileText(datasetFile.value)
      const lines = text.replace(/\r\n/g, '\n').split('\n')
      const headerIndex = lines.findIndex(line => line.trim().length > 0)
      if (headerIndex >= 0) {
        const header = parseCsvLine(lines[headerIndex]!)
        lines[headerIndex] = header
          .map(name => escapeCsvCell(renameByColumn.get(name) ?? name))
          .join(',')
      }

      const renamed = new File(
        [lines.join('\n')],
        datasetFile.value.name,
        { type: datasetFile.value.type || 'text/csv' },
      )
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))
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
      // saveColumnMapping 失敗時已經把本地狀態復原，但畫面上必須告訴使用者，
      // 不然按鈕悄悄恢復可按，使用者只會覺得「怎麼沒反應」再按一次
      const detail = error instanceof Error ? error.message : ''
      saveError.value = detail ? `儲存失敗，請再試一次（${detail}）` : '儲存失敗，請再試一次'
    } finally {
      confirming.value = false
    }
  }

  /** 欄位名含逗號或引號時要包起來，否則改寫後的表頭會被拆錯欄。 */
  function escapeCsvCell (value: string): string {
    if (!/[",\n]/.test(value)) return value
    return `"${value.replace(/"/g, '""')}"`
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

      const preview = await parseCsvPreview(file, 5)
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
      if (loadDraft()) {
        aiAvailable.value = true
        return
      }

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
    color: var(--color-ink);
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

  .mapping-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }

  .mapping-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--color-ink);
  }

  .mapping-count {
    font-size: 13px;
    color: var(--color-secondary);
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

  /* 下拉欄固定寬度，視窗窄的時候讓表格自己捲，不要把整頁撐開 */
  .mapping-scroll {
    overflow-x: auto;
  }

  .mapping-table {
    width: 100%;
    min-width: 520px;
    border-collapse: collapse;
    font-size: 13px;
  }

  .mapping-table th {
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    color: var(--color-secondary);
    border-bottom: 1px solid #e8e8e8;
  }

  .mapping-table td {
    padding: 10px;
    border-bottom: 1px solid #f0f1f3;
    vertical-align: top;
  }

  /* 要放得下「待確認」標籤 + 勾勾按鈕，不然標籤會被擠到換行 */
  .col-status {
    width: 124px;
  }

  .col-col {
    width: 260px;
  }

  .target-badge {
    color: #d97706;
    margin-right: 4px;
  }

  .var-name {
    font-weight: 600;
    color: var(--color-ink);
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }

  .col-samples {
    margin-top: 4px;
    font-size: 11px;
    color: #94a3b8;
  }

  .status-chip {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    /* 不換行：三個字被擠成兩行的話，圓角會把它變成一顆球 */
    white-space: nowrap;
  }

  .status-chip--auto_matched {
    background: #dcfce7;
    color: #15803d;
  }

  .status-chip--needs_review {
    background: #fef3c7;
    color: #b45309;
  }

  .status-chip--unmatched {
    background: #fee2e2;
    color: #b91c1c;
  }

  .status-chip--skipped {
    background: #f0f1f3;
    color: var(--color-secondary);
  }

  .status-chip--confirmed {
    background: #dcfce7;
    color: #15803d;
  }

  /* 三種顏色一次講完。比寫一整段說明好掃，而且直接用真的標籤當範例 */
  .status-chip[tabindex] {
    cursor: help;
  }

  .status-chip[tabindex]:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .status-cell {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* 狀態標籤照舊顯示，勾勾另外放旁邊：
     使用者要先看懂「這是待確認的」，才知道按勾勾是什麼意思 */
  .check-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border: 1px solid #cbd5e1;
    border-radius: 50%;
    background: #fff;
    color: #94a3b8;
    cursor: pointer;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s;
  }

  .check-btn:hover {
    background: #dcfce7;
    border-color: #22c55e;
    color: #15803d;
  }

  .check-btn:focus-visible,
  .undo-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  /* 視覺上 26px，但用 ::after 把可點範圍撐到 40px，手指才按得到 */
  .check-btn::after,
  .undo-btn::after {
    content: '';
    position: absolute;
    inset: -7px;
  }

  .undo-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 7px;
    background: none;
    color: #cbd5e1;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
  }

  .undo-btn:hover {
    background: #f0f1f3;
    color: var(--color-secondary);
  }

  /* AI 或搶欄位造成的變動閃一下，讓使用者看見改到哪一列 */
  .row-flash {
    animation: row-flash 2s ease-out;
  }

  @keyframes row-flash {
    0%, 40% { background: #fef9c3; }
    100% { background: transparent; }
  }

  /* 有人對動態效果敏感（會頭暈）；改成靜態底色淡出，資訊不減 */
  @media (prefers-reduced-motion: reduce) {
    .row-flash {
      animation: none;
      background: #fef9c3;
    }

    .confirm-all-btn,
    .confirm-row-btn {
      transition: none;
    }
  }

  .preview-block {
    padding-top: 4px;
  }

  .preview-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-secondary);
    margin-bottom: 8px;
  }

  .preview-scroll {
    overflow-x: auto;
  }

  .preview-table {
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-table th,
  .preview-table td {
    padding: 6px 10px;
    border: 1px solid #f0f1f3;
    color: var(--color-secondary);
  }

  .preview-table th {
    background: var(--color-background);
    font-weight: 600;
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

  /* 尺寸與圓角比照 ProjectsView 的 .new-btn。
     border: none 是必要的 —— <button> 會帶瀏覽器預設外框，那圈深色不是設計 */
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

  .confirm-btn:hover:not(:disabled),
  .chat-send:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }

  .confirm-btn:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }

  .mapping-chat {
    display: flex;
    flex-direction: column;
    /* 跟著視窗高度走：筆電上不會被擠到要捲，大螢幕也不會留一大片空白 */
    height: clamp(420px, calc(100vh - 190px), 720px);
    border: 1px solid #e8e8e8;
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
  }

  /* 圖示樣式比照 ResultView 的 .analysis-icon-wrap，兩邊的 AI 區塊看起來才是一組的 */
  .chat-head-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #eef1ff;
    color: var(--color-accent);
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid #e8e8e8;
    font-size: 14px;
    font-weight: 600;
    color: var(--color-ink);
  }

  .chat-offline {
    padding: 10px 16px;
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
    font-size: 12px;
    color: #b45309;
  }

  .chat-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .chat-bubble {
    max-width: 88%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .chat-bubble--user {
    align-self: flex-end;
    background: var(--color-chat-user);
    color: var(--color-inverted);
  }

  .chat-bubble--assistant {
    align-self: flex-start;
    background: var(--color-chat-system);
    color: var(--color-ink);
  }

  .chat-bubble--pending {
    color: #94a3b8;
  }

  .chat-input {
    display: flex;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid #e8e8e8;
  }

  .chat-field {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    font-size: 13px;
  }

  .chat-field:disabled {
    background: var(--color-background);
  }

  .chat-send {
    padding: 0 16px;
    height: 36px;
    border: none;
    border-radius: 7px;
    background: var(--color-accent);
    color: #ffffff;
    cursor: pointer;
    transition: background 0.15s;
    font-size: 13px;
    font-weight: 600;
  }

  .chat-send:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
</style>

<!-- v-tooltip 會 teleport 到元件外，scoped 樣式管不到，所以另開一個全域區塊 -->
<style>
  .status-tooltip {
    padding: 7px 10px !important;
    font-size: 12px !important;
    line-height: 1.55 !important;
  }
</style>
