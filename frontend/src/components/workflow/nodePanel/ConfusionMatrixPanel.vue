<template>
  <section class="confusion-matrix-panel">
    <div v-if="groupedResults.length > 0" class="cm-controls">
      <div class="cm-field">
        <span class="cm-field__label">模型</span>
        <CustomSelect
          v-model="selectedModel"
          class="cm-select"
          :options="modelOptions"
        />
      </div>
      <div class="cm-field">
        <span class="cm-field__label">fold</span>
        <CustomSelect
          v-model="selectedFold"
          class="cm-select"
          :options="foldOptions"
        />
      </div>
    </div>

    <div v-if="groupedResults.length > 0" class="cm-tabs">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="cm-tab"
        :class="{ 'cm-tab--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="groupedResults.length > 0" class="cm-tab-row">
      <div v-if="activeTab === 'matrix' && currentMatrix" class="cm-table-wrap">
        <table class="cm-table">
          <thead>
            <tr>
              <th class="cm-corner" />
              <th
                v-for="label in currentMatrix.labels"
                :key="`pred-${label}`"
                class="cm-header"
              >
                預測：{{ label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in currentMatrix.matrix" :key="`row-${rowIndex}`">
              <th class="cm-header cm-header--row">
                實際：{{ currentMatrix.labels[rowIndex] }}
              </th>
              <td
                v-for="(cell, colIndex) in row"
                :key="`cell-${rowIndex}-${colIndex}`"
                class="cm-cell"
                :class="{ 'cm-cell--diagonal': rowIndex === colIndex }"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="activeTab === 'matrix'" class="summary-empty">
        該抽樣沒有可用的混淆矩陣資訊。
      </div>

      <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
          <path class="cm-chart-line" :d="rocPath" fill="none" />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">FPR (0 – 1)</div>
        <div class="cm-chart-axis-y">TPR (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'roc'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <path class="cm-chart-line" :d="prPath" fill="none" />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">Recall (0 – 1)</div>
        <div class="cm-chart-axis-y">Precision (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'pr'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'calibration' && currentCalibrationCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentCalibrationCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <line class="cm-chart-diagonal" x1="18" y1="82" x2="82" y2="18" />
          <path class="cm-chart-line" :d="calibrationPath" fill="none" />
          <circle
            v-for="(point, index) in calibrationPoints"
            :key="`cal-point-${index}`"
            class="cm-chart-point"
            :cx="point.x"
            :cy="point.y"
            r="1.5"
          />
          <text class="cm-chart-tick" x="13" y="95" text-anchor="middle">0</text>
          <text class="cm-chart-tick" x="50" y="90" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="82" y="90" text-anchor="end">1</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="50">0.5</text>
          <text class="cm-chart-tick" dominant-baseline="middle" text-anchor="end" x="12" y="18">1</text>
        </svg>
        <div class="cm-chart-axis-x">平均預測機率 (0 – 1)</div>
        <div class="cm-chart-axis-y">實際正類比例 (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'calibration'" class="summary-empty">
        此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'perClass' && currentPerClassMetrics" class="cm-table-wrap">
        <table class="cm-table">
          <thead>
            <tr>
              <th class="cm-header">類別</th>
              <th class="cm-header">Precision</th>
              <th class="cm-header">Recall</th>
              <th class="cm-header">F1</th>
              <th class="cm-header">樣本數</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in perClassRows"
              :key="row.label"
              :class="{ 'cm-row--lowest': row.label === lowestF1Label }"
            >
              <td class="cm-cell">{{ row.label }}</td>
              <td class="cm-cell">{{ row.precision.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.recall.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.f1.toFixed(3) }}</td>
              <td class="cm-cell">{{ row.support }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else-if="activeTab === 'perClass'" class="summary-empty">
        該抽樣沒有可用的各類別指標資訊。
      </div>

      <div v-if="hasCurrentTabData" class="cm-insight-panel">
        <div class="cm-insight-header">AI 解讀</div>

        <p v-if="isCurrentTabInsightLoading" class="cm-insight-loading cm-thinking">
          生成中
          <span class="cm-thinking-dots"><span /><span /><span /></span>
        </p>

        <template v-else-if="tabInsightError">
          <p class="cm-insight-error">{{ tabInsightError }}</p>
          <AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
            <v-icon icon="mdi-shimmer" size="14" />
            重試
          </AppButton>
        </template>

        <template v-else-if="currentTabInsight">
          <p class="cm-insight-text">{{ currentTabInsight }}</p>
          <AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
            <v-icon icon="mdi-shimmer" size="14" />
            重新生成
          </AppButton>
        </template>

        <template v-else>
          <p class="cm-insight-empty">點擊下方按鈕，讓 AI 針對目前的圖表/表格生成一段解讀。</p>
          <AppButton :disabled="!props.projectId" variant="ai" @click="generateTabInsight">
            <v-icon icon="mdi-shimmer" size="14" />
            AI 解讀
          </AppButton>
        </template>

        <div class="cm-chat-divider" />

        <div class="cm-chat-thread">
          <p v-if="currentTabChatMessages.length === 0" class="cm-chat-empty">
            針對這個圖表/表格有任何問題，都可以在下方提問。
          </p>
          <div
            v-for="(msg, index) in currentTabChatMessages"
            :key="index"
            class="cm-chat-bubble"
            :class="[`cm-chat-bubble--${msg.role}`, { 'cm-chat-bubble--typing': typingStates.has(chatMessageKey(index)) }]"
          >
            <p class="cm-chat-bubble-text">{{ typingStates.get(chatMessageKey(index)) ?? msg.text }}</p>
          </div>
          <p v-if="isCurrentTabChatLoading" class="cm-insight-loading cm-thinking">
            AI 思考中
            <span class="cm-thinking-dots"><span /><span /><span /></span>
          </p>
          <template v-if="currentTabChatError">
            <p class="cm-insight-error">{{ currentTabChatError }}</p>
            <button
              class="cm-insight-btn"
              :disabled="!props.projectId || isCurrentTabChatLoading"
              type="button"
              @click="retryTabChatMessage"
            >
              重試
            </button>
          </template>
        </div>

        <form class="cm-chat-input-row" @submit.prevent="sendTabChatMessage">
          <input
            v-model="tabChatInput"
            class="cm-chat-input"
            type="text"
            placeholder="針對這個圖表提問..."
            :disabled="!props.projectId || isCurrentTabChatLoading"
          >
          <button
            class="cm-insight-btn"
            type="submit"
            :disabled="!props.projectId || isCurrentTabChatLoading || !tabChatInput.trim()"
          >
            送出
          </button>
        </form>
      </div>
    </div>

    <div v-if="groupedResults.length === 0" class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { fetchTabChatReply, fetchTabInsight, type TabChatMessage } from '@/api/insight'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import {
    loadTabChatFromStorage,
    loadTabInsightFromStorage,
    saveTabChatToStorage,
    saveTabInsightToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'

  interface ConfusionMatrixData {
    labels: string[]
    matrix: number[][]
  }

  interface RocPrCurveData {
    posLabel: string
    roc: { fpr: number[], tpr: number[] }
    pr: { precision: number[], recall: number[] }
  }

  interface CalibrationCurveData {
    posLabel: string
    probTrue: number[]
    probPred: number[]
  }

  interface PerClassMetricsData {
    labels: string[]
    precision: number[]
    recall: number[]
    f1: number[]
    support: number[]
  }

  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
    calibration_curve: CalibrationCurveData | null
    per_class_metrics: PerClassMetricsData | null
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
      roc_pr_curve: RocPrCurveData | null
      calibration_curve: CalibrationCurveData | null
      per_class_metrics: PerClassMetricsData | null
    }>
  }

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
    projectId?: string
  }>()

  function parseConfusionMatrix (value: unknown): ConfusionMatrixData | null {
    if (!value || typeof value !== 'object') return null
    const labels = (value as Record<string, unknown>).labels
    const matrix = (value as Record<string, unknown>).matrix
    if (!Array.isArray(labels) || !Array.isArray(matrix)) return null
    if (!labels.every(l => typeof l === 'string')) return null
    if (!matrix.every(row => Array.isArray(row) && row.every(cell => typeof cell === 'number'))) return null
    return { labels: labels as string[], matrix: matrix as number[][] }
  }

  function parseRocPrCurve (value: unknown): RocPrCurveData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const posLabel = obj.pos_label
    const roc = obj.roc
    const pr = obj.pr
    if (typeof posLabel !== 'string') return null
    if (!roc || typeof roc !== 'object' || !pr || typeof pr !== 'object') return null

    const rocObj = roc as Record<string, unknown>
    const prObj = pr as Record<string, unknown>
    const fpr = rocObj.fpr
    const tpr = rocObj.tpr
    const precision = prObj.precision
    const recall = prObj.recall

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(fpr) || !isNumberArray(tpr)) return null
    if (!isNumberArray(precision) || !isNumberArray(recall)) return null

    return {
      posLabel,
      roc: { fpr, tpr },
      pr: { precision, recall },
    }
  }

  function parseCalibrationCurve (value: unknown): CalibrationCurveData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const posLabel = obj.pos_label
    const probTrue = obj.prob_true
    const probPred = obj.prob_pred
    if (typeof posLabel !== 'string') return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(probTrue) || !isNumberArray(probPred)) return null

    return { posLabel, probTrue, probPred }
  }

  function parsePerClassMetrics (value: unknown): PerClassMetricsData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const labels = obj.labels
    const precision = obj.precision
    const recall = obj.recall
    const f1 = obj.f1
    const support = obj.support

    if (!Array.isArray(labels) || !labels.every(l => typeof l === 'string')) return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(precision) || !isNumberArray(recall) || !isNumberArray(f1) || !isNumberArray(support)) {
      return null
    }
    if (
      precision.length !== labels.length
      || recall.length !== labels.length
      || f1.length !== labels.length
      || support.length !== labels.length
    ) {
      return null
    }

    return { labels, precision, recall, f1, support }
  }

  const rawResults = computed<Array<Record<string, unknown>>>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []
    return results as Array<Record<string, unknown>>
  })

  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value.map(result => {
      const model_name = String(result.model_name ?? 'Unknown model')
      const split_name = String(result.split_name ?? 'Unknown split')
      const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
      const roc_pr_curve = parseRocPrCurve(result.roc_pr_curve)
      const calibration_curve = parseCalibrationCurve(result.calibration_curve)
      const per_class_metrics = parsePerClassMetrics(result.per_class_metrics)
      return { model_name, split_name, confusion_matrix, roc_pr_curve, calibration_curve, per_class_metrics }
    }).filter(item =>
      item.confusion_matrix !== null
      || item.roc_pr_curve !== null
      || item.calibration_curve !== null
      || item.per_class_metrics !== null,
    ),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of confusionResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
        calibration_curve: result.calibration_curve,
        per_class_metrics: result.per_class_metrics,
      }

      if (existing) {
        existing.splits.push(entry)
      } else {
        groups.set(result.model_name, {
          model_name: result.model_name,
          splits: [entry],
        })
      }
    }

    return Array.from(groups.values())
  })

  const selectedModel = ref('')
  const selectedFold = ref('')

  const modelOptions = computed(() =>
    groupedResults.value.map(g => ({ value: g.model_name, label: g.model_name })),
  )

  const currentModel = computed(() =>
    groupedResults.value.find(g => g.model_name === selectedModel.value) ?? null,
  )

  const foldOptions = computed(() =>
    (currentModel.value?.splits ?? []).map(s => ({ value: s.split_name, label: s.split_name })),
  )

  const currentMatrix = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.confusion_matrix ?? null,
  )

  type TabKey = 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
    { key: 'calibration', label: '校準曲線' },
    { key: 'perClass', label: '各類別指標' },
  ]

  const currentRocPrCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve ?? null,
  )

  const currentCalibrationCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.calibration_curve ?? null,
  )

  const currentPerClassMetrics = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.per_class_metrics ?? null,
  )

  interface PerClassRow {
    label: string
    precision: number
    recall: number
    f1: number
    support: number
  }

  const perClassRows = computed<PerClassRow[]>(() => {
    const data = currentPerClassMetrics.value
    if (!data) return []
    return data.labels.map((label, i) => ({
      label,
      precision: data.precision[i]!,
      recall: data.recall[i]!,
      f1: data.f1[i]!,
      support: data.support[i]!,
    }))
  })

  const lowestF1Label = computed(() => {
    const rows = perClassRows.value
    if (rows.length === 0) return null
    return rows.reduce((min, row) => (row.f1 < min.f1 ? row : min)).label
  })

  const hasCurrentTabData = computed(() => {
    switch (activeTab.value) {
      case 'matrix': return currentMatrix.value !== null
      case 'roc':
      case 'pr': return currentRocPrCurve.value !== null
      case 'calibration': return currentCalibrationCurve.value !== null
      case 'perClass': return currentPerClassMetrics.value !== null
      default: return false
    }
  })

  const tabInsightCache = ref<Map<string, string>>(new Map())
  const tabInsightLoadingKey = ref<string | null>(null)
  const tabInsightError = ref<string | null>(null)

  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }

  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value),
  )

  const currentTabInsight = computed(() =>
    tabInsightCache.value.get(currentTabInsightKey.value) ?? null,
  )

  const isCurrentTabInsightLoading = computed(() => tabInsightLoadingKey.value === currentTabInsightKey.value)

  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
    }
  }

  // 每個 (tab, model, fold) 組合各自獨立一串對話，key 格式跟 tabInsightCache 完全一樣，
  // 直接共用 tabInsightCacheKey()/currentTabInsightKey，不需要另外一套 key 邏輯
  const tabChatCache = ref<Map<string, TabChatMessage[]>>(new Map())
  const tabChatInput = ref('')
  // 用 Set 而非單一 ref，讓不同組合可以同時各自處於 loading 狀態，
  // 避免在 A 送出後切到 B 又送出，B 把 A 的 loading 狀態蓋掉
  const tabChatLoadingKeys = ref<Set<string>>(new Set())
  const tabChatError = ref<Map<string, string>>(new Map())
  // 只保留最近 N 則訊息寫入 localStorage，避免單一組合的對話無上限成長撐爆 quota
  // （purgeLegacyDataFileEntries() 的註解記錄過同類問題曾經因為 localStorage 爆量而讓其他地方存檔悄悄失敗）
  const MAX_PERSISTED_MESSAGES = 40

  const currentTabChatMessages = computed(() =>
    tabChatCache.value.get(currentTabInsightKey.value) ?? [],
  )

  const isCurrentTabChatLoading = computed(() => tabChatLoadingKeys.value.has(currentTabInsightKey.value))

  const currentTabChatError = computed(() =>
    tabChatError.value.get(currentTabInsightKey.value) ?? null,
  )

  // 打字機效果：只有「剛收到的這一則」AI 回覆會逐字顯示，從 localStorage/快取讀回來的舊訊息
  // 直接整段顯示，不會每次切回這個分頁又重播一次。key 是 `${組合key}::${訊息在陣列裡的 index}`，
  // 播放中途切走分頁也沒關係——timer 還是會跑完，只是使用者當下看不到（chatMessageKey 是用
  // 目前顯示中的組合算出來的，跟正在播放的訊息 key 對不上時，畫面就直接顯示完整文字）
  const typingStates = ref<Map<string, string>>(new Map())
  const typingTimers = new Map<string, ReturnType<typeof setInterval>>()
  const TYPEWRITER_INTERVAL_MS = 18

  function chatMessageKey (index: number): string {
    return `${currentTabInsightKey.value}::${index}`
  }

  function startTypewriter (msgKey: string, fullText: string): void {
    const existingTimer = typingTimers.get(msgKey)
    if (existingTimer) clearInterval(existingTimer)

    let shown = 0
    const timer = setInterval(() => {
      shown += 1
      typingStates.value = new Map(typingStates.value).set(msgKey, fullText.slice(0, shown))
      if (shown >= fullText.length) {
        clearInterval(timer)
        typingTimers.delete(msgKey)
        const next = new Map(typingStates.value)
        next.delete(msgKey)
        typingStates.value = next
      }
    }, TYPEWRITER_INTERVAL_MS)
    typingTimers.set(msgKey, timer)
  }

  onBeforeUnmount(() => {
    for (const timer of typingTimers.values()) clearInterval(timer)
    typingTimers.clear()
  })

  // 送出問題（sendTabChatMessage）跟按「重試」（retryTabChatMessage）都需要「拿 history 打 API、
  // 拿到回覆後 append 一筆 model 訊息」這段邏輯，抽成共用函式；呼叫端負責先把使用者訊息放進畫面陣列
  async function requestTabChatReply (
    tab: TabKey, model: string, fold: string, history: TabChatMessage[], text: string,
  ): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const key = tabInsightCacheKey(tab, model, fold)

    tabChatLoadingKeys.value = new Set(tabChatLoadingKeys.value).add(key)
    if (tabChatError.value.has(key)) {
      const nextError = new Map(tabChatError.value)
      nextError.delete(key)
      tabChatError.value = nextError
    }
    try {
      const reply = await fetchTabChatReply(props.workflowResult, tab, model, fold, history, text)
      const messages = [...(tabChatCache.value.get(key) ?? []), { role: 'model' as const, text: reply }]
      tabChatCache.value = new Map(tabChatCache.value).set(key, messages)
      saveTabChatToStorage(props.projectId, model, fold, tab, messages.slice(-MAX_PERSISTED_MESSAGES))
      startTypewriter(`${key}::${messages.length - 1}`, reply)
    } catch (error) {
      tabChatError.value = new Map(tabChatError.value).set(
        key, error instanceof Error ? error.message : String(error),
      )
    } finally {
      const nextLoadingKeys = new Set(tabChatLoadingKeys.value)
      nextLoadingKeys.delete(key)
      tabChatLoadingKeys.value = nextLoadingKeys
    }
  }

  async function sendTabChatMessage (): Promise<void> {
    const text = tabChatInput.value.trim()
    if (!text || !props.projectId || !props.workflowResult) return

    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const cachedMessages = tabChatCache.value.get(key) ?? []
    // 如果上一則還是「還沒被回覆的 user 訊息」（送出失敗留下的），視為使用者放棄那次嘗試，
    // 把它從 history 跟畫面快取裡都拿掉，避免產生連續兩筆 user 訊息、破壞跟後端對話輪替的順序
    const hasTrailingUnansweredUserMessage =
      cachedMessages[cachedMessages.length - 1]?.role === 'user'
    const history = hasTrailingUnansweredUserMessage
      ? cachedMessages.slice(0, -1)
      : cachedMessages

    tabChatInput.value = ''
    tabChatCache.value = new Map(tabChatCache.value).set(key, [...history, { role: 'user' as const, text }])
    if (tabChatError.value.has(key)) {
      const nextError = new Map(tabChatError.value)
      nextError.delete(key)
      tabChatError.value = nextError
    }

    await requestTabChatReply(tab, model, fold, history, text)
  }

  // 失敗時使用者的訊息還留在畫面上（陣列最後一筆是 role:'user'），重試就是拿掉那一筆當 history、
  // 用同一則訊息內容再打一次 API，不會讓使用者的問題重複出現在 history 裡
  function retryTabChatMessage (): void {
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const messages = tabChatCache.value.get(key) ?? []
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'user') return
    const history = messages.slice(0, -1)
    void requestTabChatReply(tab, model, fold, history, lastMessage.text)
  }

  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, selectedModel, selectedFold], () => {
    tabInsightError.value = null
    tabChatInput.value = ''
    if (!props.projectId) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (!tabInsightCache.value.has(key)) {
      const cached = loadTabInsightFromStorage(props.projectId, model, fold, tab)
      if (cached !== null) {
        tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
      }
    }
    if (!tabChatCache.value.has(key)) {
      const cachedChat = loadTabChatFromStorage(props.projectId, model, fold, tab)
      if (cachedChat.length > 0) {
        tabChatCache.value = new Map(tabChatCache.value).set(key, cachedChat)
      }
    }
  }, { immediate: true })

  const CHART_SIZE = 100
  const CHART_PADDING = 18

  function toChartX (value: number): number {
    return CHART_PADDING + value * (CHART_SIZE - CHART_PADDING * 2)
  }

  function toChartY (value: number): number {
    return CHART_SIZE - CHART_PADDING - value * (CHART_SIZE - CHART_PADDING * 2)
  }

  function buildLinePath (xs: number[], ys: number[]): string {
    if (xs.length === 0 || xs.length !== ys.length) return ''
    return xs
      .map((x, i) => `${i === 0 ? 'M' : 'L'} ${toChartX(x).toFixed(2)} ${toChartY(ys[i]!).toFixed(2)}`)
      .join(' ')
  }

  const rocPath = computed(() => {
    const curve = currentRocPrCurve.value
    if (!curve) return ''
    return buildLinePath(curve.roc.fpr, curve.roc.tpr)
  })

  const prPath = computed(() => {
    const curve = currentRocPrCurve.value
    if (!curve) return ''
    return buildLinePath(curve.pr.recall, curve.pr.precision)
  })

  const calibrationPath = computed(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return ''
    return buildLinePath(curve.probPred, curve.probTrue)
  })

  interface ChartPoint {
    x: number
    y: number
  }

  const calibrationPoints = computed<ChartPoint[]>(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return []
    return curve.probPred.map((x, i) => ({
      x: toChartX(x),
      y: toChartY(curve.probTrue[i]!),
    }))
  })

  // 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
  watch(groupedResults, groups => {
    if (groups.length === 0) {
      selectedModel.value = ''
      return
    }
    if (!groups.some(g => g.model_name === selectedModel.value)) {
      selectedModel.value = groups[0]!.model_name
    }
  }, { immediate: true })

  // 換模型（或結果載入）時，fold 一律重置為該模型的第一個
  watch(currentModel, model => {
    const splits = model?.splits ?? []
    selectedFold.value = splits[0]?.split_name ?? ''
  }, { immediate: true })
</script>

<style scoped>
  .confusion-matrix-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 0 0 16px;
  }

  .cm-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .cm-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .cm-field__label {
    font-size: 13px;
    color: var(--color-ink-soft);
    white-space: nowrap;
  }

  .cm-select {
    width: 160px;
  }

  .cm-table-wrap {
    overflow-x: auto;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .cm-table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
  }

  .cm-corner {
    background: var(--color-surface);
  }

  .cm-header {
    padding: 10px 14px;
    font-size: 12px;
    font-weight: 700;
    color: var(--color-ink-soft);
    white-space: nowrap;
    text-align: left;
    border-bottom: 1px solid var(--color-border);
  }

  .cm-header--row {
    border-bottom: none;
    border-right: 1px solid var(--color-border);
  }

  .cm-cell {
    padding: 11px 14px;
    text-align: center;
    color: var(--color-ink);
    font-variant-numeric: tabular-nums;
    border-bottom: 1px solid var(--color-border);
  }

  .cm-cell--diagonal {
    background: color-mix(in oklab, var(--color-ink) 12%, transparent);
    font-weight: 700;
  }

  .cm-row--lowest .cm-cell {
    background: color-mix(in oklab, var(--color-ink) 12%, transparent);
    font-weight: 700;
  }

  .cm-tabs {
    display: flex;
    gap: 6px;
  }

  .cm-tab {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--color-border-strong);
    background: transparent;
    color: var(--color-ink-soft);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .cm-tab--active {
    background: var(--color-ink);
    border-color: var(--color-ink);
    color: var(--color-inverted);
  }

  .cm-chart-wrap {
    position: relative;
    padding: 12px 16px 28px 52px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .cm-chart {
    width: 100%;
    max-width: 260px;
    aspect-ratio: 1;
    display: block;
  }

  .cm-chart-label {
    font-size: 12px;
    color: var(--color-ink-soft);
    margin-bottom: 4px;
  }

  .cm-chart-diagonal {
    stroke: var(--color-border-strong);
    stroke-width: 0.6;
    stroke-dasharray: 2 2;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-line {
    stroke: var(--color-ink);
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-point {
    fill: var(--color-ink);
    stroke: var(--color-surface);
    stroke-width: 0.5;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-tick {
    font-size: 7px;
    fill: var(--color-ink-soft);
  }

  .cm-chart-axis-x {
    position: absolute;
    left: 50%;
    bottom: 6px;
    transform: translateX(-50%);
    font-size: 11px;
    color: var(--color-ink-soft);
  }

  .cm-chart-axis-y {
    position: absolute;
    left: 4px;
    top: 50%;
    transform: rotate(-90deg) translateX(-50%);
    transform-origin: left top;
    font-size: 11px;
    color: var(--color-ink-soft);
    white-space: nowrap;
  }

  .cm-tab-row {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }

  .cm-tab-row > .cm-table-wrap,
  .cm-tab-row > .summary-empty {
    flex: 1 1 0;
    min-width: 0;
  }

  .cm-tab-row > .cm-chart-wrap {
    flex: 0 0 auto;
  }

  .cm-insight-panel {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 16px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .cm-insight-header {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .cm-insight-empty,
  .cm-insight-loading,
  .cm-insight-text {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink);
    line-height: 1.6;
  }

  .cm-thinking-dots {
    display: inline-flex;
    gap: 3px;
    margin-left: 4px;
    vertical-align: middle;
  }

  .cm-thinking-dots span {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: currentColor;
    animation: cm-thinking-bounce 1.2s infinite ease-in-out;
  }

  .cm-thinking-dots span:nth-child(2) {
    animation-delay: 0.15s;
  }

  .cm-thinking-dots span:nth-child(3) {
    animation-delay: 0.3s;
  }

  @keyframes cm-thinking-bounce {
    0%, 60%, 100% {
      transform: translateY(0);
      opacity: 0.5;
    }
    30% {
      transform: translateY(-4px);
      opacity: 1;
    }
  }

  .cm-insight-error {
    margin: 0;
    font-size: 13px;
    color: var(--color-error-text);
  }

  .cm-chat-divider {
    height: 1px;
    background: rgba(148, 163, 184, 0.22);
  }

  .cm-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .cm-chat-empty {
    margin: 0;
    font-size: 12px;
    color: var(--color-secondary);
  }

  .cm-chat-bubble {
    max-width: 90%;
    padding: 6px 10px;
    border-radius: 10px;
    background: color-mix(in oklab, var(--color-accent) 8%, transparent);
  }

  .cm-chat-bubble--user {
    align-self: flex-end;
    background: color-mix(in oklab, var(--color-accent) 16%, transparent);
  }

  .cm-chat-bubble--model {
    align-self: flex-start;
  }

  .cm-chat-bubble-text {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink);
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .cm-chat-bubble--typing .cm-chat-bubble-text::after {
    content: '▍';
    display: inline-block;
    margin-left: 1px;
    animation: cm-typing-cursor 0.8s steps(1) infinite;
  }

  @keyframes cm-typing-cursor {
    50% {
      opacity: 0;
    }
  }

  .cm-chat-input-row {
    display: flex;
    gap: 8px;
  }

  .cm-chat-input {
    flex: 1;
    padding: 7px 10px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: var(--color-surface);
    color: var(--color-ink);
    font-size: 13px;
  }

  .cm-chat-input:focus {
    outline: none;
    border-color: var(--color-accent);
  }

  .summary-empty {
    color: var(--color-ink-soft);
    font-size: 13px;
  }
</style>
