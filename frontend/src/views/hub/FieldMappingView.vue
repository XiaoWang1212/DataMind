<template>
  <div class="mapping-page">
    <RouterLink :to="`/hub/projects/${projectId}`" class="back-link">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <div class="page-header">
      <h1 class="page-title">欄位對齊</h1>
      <p class="page-sub">確認論文需要的變數對應到資料表的哪一個欄位</p>
    </div>

    <div v-if="loadError" class="load-error">
      <v-icon icon="mdi-alert-circle-outline" size="20" />
      <span>{{ loadError }}</span>
      <RouterLink to="/hub/projects/new" class="load-error-link">重新上傳資料集</RouterLink>
    </div>

    <div v-else class="mapping-layout">
      <!-- 左：對映表 + 資料預覽 -->
      <section class="mapping-main">
        <div class="mapping-head">
          <span class="mapping-title">論文變數對應</span>
          <span class="mapping-count">
            已對照 {{ matchedCount }} / {{ items.length }}
          </span>
        </div>

        <div v-if="loading" class="mapping-loading">
          <v-progress-circular indeterminate size="28" color="#2347c5" />
          <span>正在自動配對…</span>
        </div>

        <table v-else class="mapping-table">
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
                <span v-if="isTarget(item)" class="target-badge" title="預測目標">★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
              <td class="col-col">
                <CustomSelect
                  :model-value="item.matched_user_column ?? selectionKey(item)"
                  :options="optionsFor(item)"
                  placeholder="請選擇"
                  :highlight="item.status === 'UNMATCHED'"
                  @update:model-value="value => applySelection(item, value)"
                />
                <div v-if="item.sample_values.length" class="col-samples">
                  {{ item.sample_values.slice(0, 3).join('、') }}
                </div>
              </td>
              <td class="col-status">
                <span class="status-chip" :class="`status-chip--${item.status.toLowerCase()}`">
                  {{ STATUS_LABEL[item.status] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

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
          <v-icon icon="mdi-robot-outline" size="18" color="#2347c5" />
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
  import { computed, nextTick, onMounted, ref } from 'vue'
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
    AUTO_MATCHED: '已對應',
    NEEDS_REVIEW: '待確認',
    UNMATCHED: '未對應',
    SKIPPED: '不使用',
  }

  const route = useRoute()
  const router = useRouter()
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // Project.id 在資料庫裡是 int；useWorkflowStorage 的參數是字串，呼叫時要轉
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

  function isTarget (item: MappingItem): boolean {
    return item.paper_variable === targetName.value
  }

  // target 永遠排最前面：它配錯的話整個實驗都白做，不能混在幾十列裡被滑過去
  const sortedItems = computed(() => {
    const list = [...items.value]
    list.sort((a, b) => Number(isTarget(b)) - Number(isTarget(a)))
    return list
  })

  // SKIPPED 不算「已對照」：使用者是主動表示資料裡沒有這個變數
  const matchedCount = computed(
    () => items.value.filter(
      i => i.status !== 'UNMATCHED' && i.status !== 'SKIPPED',
    ).length,
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
        ? `${column.name}（目前給 ${taken.get(column.name)}）`
        : column.name,
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '我的資料沒有這個變數' })
    }
    return options
  }

  function applySelection (item: MappingItem, value: string): void {
    locked.value.add(item.paper_variable)
    saveError.value = ''

    if (value === SKIP_VALUE) {
      item.matched_user_column = null
      item.sample_values = []
      item.candidate_columns = []
      item.confidence_score = 0
      item.status = 'SKIPPED'
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
   * main.ts 的 loadProjects() / loadFrameworks() 是 fire-and-forget 的，
   * 使用者直接開這個網址或按重新整理時，onMounted 可能比它們先跑完，
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
        // 這個欄位如果目前是被使用者手動鎖定的列占用，整個動作直接放棄：
        // 使用者手動選過的列不容許被 AI 建議覆蓋，而半套用（新列設定了、
        // 舊列卻沒清，或反過來）比什麼都不做更糟，所以連目標列都不動。
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
          matched_count: matchedCount.value,
          mapping_status: items.value,
        },
        userColumns: userColumns.value,
        userMessage: message,
        chatHistory: chatHistory.value.slice(0, -1),
      })
      for (const variable of applyActions(actions)) flash(variable)
      chatHistory.value.push({ role: 'assistant', content: reply })
    } catch (error) {
      chatHistory.value.push({
        role: 'assistant',
        content: error instanceof Error ? error.message : 'AI 目前無法回應，請改用下拉選單。',
      })
    } finally {
      chatPending.value = false
      // key 加 mapping- 前綴，避免和 ResultView 的結果分析聊天撞在一起
      // saveChatHistoryToStorage 是共用 ResultView 的結果分析聊天沿用的函式，
      // 型別綁在 { role, text }；這裡的 ChatMessage 是 { role, content }，形狀不同但都是純本地暫存，用 unknown 轉型即可
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

  onMounted(async () => {
    try {
      await ensureStoresLoaded()

      // 同上，loadChatHistoryFromStorage 回傳的型別也是 ResultView 那組 { role, text }，轉成本頁用的形狀
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

      const { state, aiAvailable: available } = await initFieldMapping({
        paperVariables,
        userColumns: userColumns.value,
      })
      items.value = state.mapping_status
      aiAvailable.value = available
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
    gap: 18px;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #64748b;
    font-size: 13px;
    text-decoration: none;
  }

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
  }

  .page-sub {
    margin-top: 4px;
    font-size: 13px;
    color: #64748b;
  }

  .load-error {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px;
    border: 1px solid #fecaca;
    border-radius: 10px;
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
    border: 1px solid #e2e8f0;
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
    color: #0f172a;
  }

  .mapping-count {
    font-size: 13px;
    color: #64748b;
  }

  .mapping-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 0;
    justify-content: center;
    color: #64748b;
    font-size: 14px;
  }

  .mapping-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .mapping-table th {
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    color: #64748b;
    border-bottom: 1px solid #e2e8f0;
  }

  .mapping-table td {
    padding: 10px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
  }

  .col-status {
    width: 92px;
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
    color: #0f172a;
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
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
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
    background: #f1f5f9;
    color: #64748b;
  }

  /* AI 或搶欄位造成的變動閃一下，讓使用者看見改到哪一列 */
  .row-flash {
    animation: row-flash 2s ease-out;
  }

  @keyframes row-flash {
    0%, 40% { background: #fef9c3; }
    100% { background: transparent; }
  }

  .preview-block {
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
  }

  .preview-title {
    font-size: 13px;
    font-weight: 600;
    color: #475569;
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
    border: 1px solid #f1f5f9;
    color: #475569;
  }

  .preview-table th {
    background: #f8fafc;
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

  .confirm-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 18px;
    border-radius: 8px;
    background: #2347c5;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
  }

  .confirm-btn:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }

  .mapping-chat {
    display: flex;
    flex-direction: column;
    height: 620px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
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
    padding: 9px 12px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .chat-bubble--user {
    align-self: flex-end;
    background: #2347c5;
    color: #fff;
  }

  .chat-bubble--assistant {
    align-self: flex-start;
    background: #f1f5f9;
    color: #0f172a;
  }

  .chat-bubble--pending {
    color: #94a3b8;
  }

  .chat-input {
    display: flex;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid #e2e8f0;
  }

  .chat-field {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 13px;
  }

  .chat-field:disabled {
    background: #f8fafc;
  }

  .chat-send {
    padding: 8px 14px;
    border-radius: 8px;
    background: #2347c5;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }

  .chat-send:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
</style>
