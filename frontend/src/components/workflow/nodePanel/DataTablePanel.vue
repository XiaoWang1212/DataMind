<template>
  <section class="data-table-panel">
    <div class="data-table-header">
      <div
        v-if="headerState === 'guide'"
        class="data-table-guide"
        :class="{ 'data-table-guide--ready': hasTarget }"
      >
        <span v-if="hasTarget">
          已選定目標變數「{{ targetColumnName }}」，按右下角「繼續」即可進入下一步。
        </span>
        <span v-else>
          請將要預測的欄位在下方「Role」欄選為 <strong>Target</strong>，再按右下角「繼續」。
        </span>
      </div>
      <div v-else-if="headerState === 'summary'" class="data-table-summary-inline">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>

    <div v-if="isLoading" class="data-table-loading-overlay">
      <div class="loader" />
      <div>資料載入中...</div>
    </div>

    <div v-if="!file" class="data-table-empty">
      請先在 File 節點上傳 CSV 檔案，才能顯示資料表。
    </div>

    <div v-else-if="!columnsReady" class="data-table-empty">
      無法解析 CSV 檔案內容。
    </div>

    <div v-else class="data-table-body">
      <div v-if="headerState === 'guide'" class="data-table-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ previewDataRows.length }} 筆已讀取</span>
      </div>

      <div v-if="columnSettings.length > 0" class="data-table-column-settings">
        <div class="column-settings-title">欄位設定</div>
        <div class="column-settings-body">
          <table class="column-settings-table">
            <thead>
              <tr>
                <th>Column Name</th>
                <th>Type</th>
                <th>Role</th>
                <th>Values</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(column, index) in columnSettings"
                :key="index"
                :class="{ 'target-row': column.role === 'target' }"
              >
                <td :class="{ 'target-cell': column.role === 'target' }">
                  <input
                    v-model="column.name"
                    class="column-name-input"
                    :maxlength="nameMaxLength"
                    type="text"
                  >
                </td>
                <td :class="{ 'target-cell': column.role === 'target' }">
                  <select v-model="column.type">
                    <option
                      v-for="type in typeOptions"
                      :key="type"
                      :value="type"
                    >
                      {{ typeLabels[type] }}
                    </option>
                  </select>
                </td>
                <td :class="{ 'target-cell': column.role === 'target' }">
                  <div class="role-select-wrap">
                    <select
                      v-model="column.role"
                      class="role-select"
                      :class="{
                        'role-select--attention': props.loading && !hasTarget && !roleSelectTouched,
                      }"
                      @change="onRoleChange(index)"
                      @focus="handleRoleSelectFocus"
                    >
                      <option
                        v-for="role in roleOptions"
                        :key="role"
                        :value="role"
                      >
                        {{ roleLabels[role] }}
                      </option>
                    </select>
                    <Transition v-if="index === 0" name="tap-hint-fade">
                      <span
                        v-if="props.loading && !roleSelectTouched && !hasTarget"
                        aria-hidden="true"
                        class="tap-hint"
                      >
                        <span class="tap-hint__ring" />
                        <span class="tap-hint__ring tap-hint__ring--delay" />
                        <span class="tap-hint__dot" />
                      </span>
                    </Transition>
                  </div>
                </td>
                <td
                  :class="[
                    'values-cell',
                    { 'target-cell': column.role === 'target' },
                  ]"
                  :title="columnValueLabels[index]"
                >
                  {{ columnValueLabels[index] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="column-settings-actions">
          <button class="btn-reset" type="button" @click="resetColumnSettings">
            Reset
          </button>
          <button
            class="btn-apply"
            :class="{ 'btn-apply--disabled': !hasTarget }"
            :disabled="!hasTarget"
            type="button"
            @click="applyColumnSettings"
          >
            繼續
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'

  type ColumnType = 'numeric' | 'categorial' | 'text' | 'datetime'
  type ColumnRole = 'feature' | 'target' | 'meta' | 'skip'

  interface ColumnConfig {
    name: string
    type: ColumnType
    role: ColumnRole
  }

  interface ColumnSetting extends ColumnConfig {
    availableTypes: ColumnType[]
  }

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
    columnConfig?: ColumnConfig[]
    loading?: boolean
  }>()

  const emit = defineEmits<{
    (e: 'update-column-config', payload: ColumnConfig[]): void
    (e: 'apply-column-config'): void
  }>()

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')
  const previewColumns = ref<string[]>([])
  const columnsReady = computed(() => previewColumns.value.length > 0)
  type HeaderState = 'guide' | 'summary' | 'none'
  const headerState = computed<HeaderState>(() => {
    if (!columnsReady.value) return 'none'
    return props.loading ? 'guide' : 'summary'
  })
  const previewDataRows = ref<string[][]>([])
  const columnSettings = ref<ColumnSetting[]>([])
  const isLoading = ref(false)

  const roleSelectTouched = ref(false)

  function handleRoleSelectFocus (): void {
    roleSelectTouched.value = true
  }

  const roleOptions = ['feature', 'target', 'meta', 'skip'] as const
  const typeOptions = ['numeric', 'categorial', 'text', 'datetime'] as const
  const typeLabels: Record<ColumnType, string> = {
    numeric: 'Numeric',
    categorial: 'Categorical',
    text: 'Text',
    datetime: 'Datetime',
  }

  const roleLabels: Record<ColumnRole, string> = {
    feature: 'Feature',
    target: 'Target',
    meta: 'Meta',
    skip: 'Skip',
  }

  const nameMaxLength = 32

  const hasTarget = computed(() => columnSettings.value.some(c => c.role === 'target'))
  const targetColumnName = computed(
    () => columnSettings.value.find(c => c.role === 'target')?.name ?? '',
  )

  function isLikelyDate (value: string): boolean {
    if (!value || value.trim().length === 0) return false
    if (/^\d+$/.test(value.trim())) return false
    const parsed = Date.parse(value)
    return !Number.isNaN(parsed)
  }

  function getColumnTypeCandidates (values: string[]): ColumnType[] {
    const trimmed = values.map(value => value?.trim() ?? '').filter(Boolean)
    const uniqueValues = new Set(trimmed)

    const allNumeric
      = trimmed.length > 0
        && trimmed.every(value => {
          const numberValue = Number(value)
          return value !== '' && !Number.isNaN(numberValue)
        })

    const allDatetime
      = trimmed.length > 0 && trimmed.every(value => isLikelyDate(value))
    const isCategorical = trimmed.length > 0 && uniqueValues.size <= 20

    const candidates: ColumnType[] = []
    if (allNumeric) candidates.push('numeric')
    if (allDatetime) candidates.push('datetime')
    if (isCategorical || (!allNumeric && !allDatetime))
      candidates.push('categorial')
    candidates.push('text')
    return [...new Set(candidates)]
  }


  function buildColumnSettings (useExisting = true): void {
    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      // 用索引而非名稱對位：Column Name 可編輯，改過名字後就跟 CSV 表頭對不上了
      const existing = useExisting ? props.columnConfig?.[index] : undefined
      const selectedType = existing?.type ?? (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? 'feature'

      return {
        name: existing?.name ?? header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })
  }

  function emitColumnConfig (): void {
    emit(
      'update-column-config',
      columnSettings.value.map(({ name, type, role }) => ({
        name,
        type,
        role,
      })),
    )
  }

  function resetColumnSettings (): void {
    buildColumnSettings(false)
  }

  function applyColumnSettings (): void {
    emit('apply-column-config')
  }

  function onRoleChange (index: number): void {
    if (columnSettings.value[index]?.role !== 'target') return
    columnSettings.value.forEach((col, i) => {
      if (i !== index && col.role === 'target') {
        col.role = 'feature'
      }
    })
  }

  function getColumnRawValues (index: number): string[] {
    return previewDataRows.value
      .map(row => row[index] ?? '')
      .map(value => value.trim())
      .filter(value => value.length > 0)
  }

  function formatNumericValue (value: number): string {
    if (Number.isInteger(value)) return String(value)
    // 小於 1 的值改用有效位數，否則 toFixed(3) 會把 0.0001 這種值壓成 0、看起來像沒有變異
    const rounded = Math.abs(value) < 1
      ? Number(value.toPrecision(3))
      : Number(value.toFixed(3))
    return String(rounded)
  }

  function computeColumnValueLabel (column: ColumnSetting, index: number): string {
    const values = getColumnRawValues(index)
    if (values.length === 0) return '—'

    if (column.type === 'numeric') {
      // min/max 用 for 迴圈算，previewDataRows 沒有截斷列數，展開成函式引數會超過引數上限
      let min = Number.POSITIVE_INFINITY
      let max = Number.NEGATIVE_INFINITY
      for (const value of values) {
        const parsed = Number(value)
        if (Number.isNaN(parsed)) continue
        if (parsed < min) min = parsed
        if (parsed > max) max = parsed
      }
      if (min === Number.POSITIVE_INFINITY) return '—'
      return `${formatNumericValue(min)} – ${formatNumericValue(max)}`
    }

    if (column.type === 'datetime') {
      // 顯示原始字串而非重新格式化，避免時區轉換讓畫面上的日期跟 CSV 差一天
      let minText = ''
      let maxText = ''
      let minTime = Number.POSITIVE_INFINITY
      let maxTime = Number.NEGATIVE_INFINITY
      for (const value of values) {
        const time = Date.parse(value)
        if (Number.isNaN(time)) continue
        if (time < minTime) {
          minTime = time
          minText = value
        }
        if (time > maxTime) {
          maxTime = time
          maxText = value
        }
      }
      if (!minText || !maxText) return '—'
      return `${minText} – ${maxText}`
    }

    const uniqueValues = Array.from(new Set(values))
    const limit = column.type === 'categorial' ? 6 : 3
    return uniqueValues.slice(0, limit).join(', ')
  }

  const columnValueLabels = computed<string[]>(() =>
    columnSettings.value.map((column, index) => computeColumnValueLabel(column, index)),
  )

  watch(
    () => props.file,
    async file => {
      if (!file) {
        previewColumns.value = []
        previewDataRows.value = []
        columnSettings.value = []
        isLoading.value = false
        return
      }
      isLoading.value = true
      await loadFile(file)
      isLoading.value = false
    },
    { immediate: true },
  )

  watch(
    () => props.columnConfig,
    value => {
      if (!value) return
      if (previewColumns.value.length === 0) return
      if (!areColumnConfigsEqual(value, columnSettings.value)) {
        buildColumnSettings()
      }
    },
    { immediate: true, deep: true },
  )

  // 切到別的節點會讓這個面板被 v-if 卸載、本地狀態銷毀，只能靠父層還原，
  // 所以每次改動都要即時寫回去，不能等按「繼續」
  watch(
    columnSettings,
    () => {
      emitColumnConfig()
    },
    { deep: true },
  )

  async function loadFile (file: File): Promise<void> {
    try {
      const text = await decodeFileText(file)
      const lines = text
        .replace(/\r\n/g, '\n')
        .split('\n')
        .filter(line => line.trim().length > 0)

      if (lines.length === 0) {
        previewColumns.value = []
        previewDataRows.value = []
        return
      }

      previewColumns.value = parseCsvLine(lines[0]!)
      previewDataRows.value = lines.slice(1).map(line => parseCsvLine(line))
      buildColumnSettings()
    } catch {
      previewColumns.value = []
      previewDataRows.value = []
      columnSettings.value = []
    }
  }

  function areColumnConfigsEqual (
    a: ColumnConfig[] | undefined,
    b: ColumnSetting[],
  ): boolean {
    if (!a) return false
    if (a.length !== b.length) return false
    return a.every((config, index) => {
      const candidate = b[index]
      return (
        candidate !== undefined
        && config.name === candidate.name
        && config.type === candidate.type
        && config.role === candidate.role
      )
    })
  }

  async function decodeFileText (file: File) {
    const buffer = await file.arrayBuffer()
    const decoderUtf8 = new TextDecoder('utf-8', { fatal: true })
    let utf8Text: string | null = null
    try {
      utf8Text = decoderUtf8.decode(buffer)
    } catch {
      utf8Text = null
    }

    const decoderBig5 = new TextDecoder('big5')
    const big5Text = decoderBig5.decode(buffer)

    if (!utf8Text) {
      return big5Text
    }

    const scoreText = (text: string) => {
      const headerLine = text.split(/\r?\n/, 1)[0] ?? ''
      const cjkCount = (headerLine.match(/[\u4E00-\u9FFF]/g) || []).length
      const replacementCount = (text.match(/\uFFFD/g) || []).length
      return cjkCount * 10 - replacementCount * 20
    }

    const utf8Score = scoreText(utf8Text)
    const big5Score = scoreText(big5Text)

    return big5Score > utf8Score ? big5Text : utf8Text
  }

  function parseCsvLine (line: string): string[] {
    const out: string[] = []
    let cur = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i]
      const next = line[i + 1]

      if (ch === '"' && inQuotes && next === '"') {
        cur += '"'
        i += 1
        continue
      }

      if (ch === '"') {
        inQuotes = !inQuotes
        continue
      }

      if (ch === ',' && !inQuotes) {
        out.push(cur.trim())
        cur = ''
        continue
      }

      cur += ch
    }

    out.push(cur.trim())
    return out
  }
</script>

<style scoped>
  .data-table-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 14px;
    position: relative;
  }

  .data-table-loading-overlay {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12px;
    padding: 24px;
    border-radius: 16px;
    border: 1px dashed rgba(96, 165, 250, 0.7);
    background: rgba(255, 255, 255, 0.88);
    color: #005dff;
    font-size: 14px;
    z-index: 10;
  }

  .data-table-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .data-table-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .data-table-file {
    flex-shrink: 0;
    margin-left: auto;
    color: #475569;
    font-size: 13px;
  }

  .data-table-empty {
    padding: 20px;
    border-radius: 12px;
    background: #f8fafc;
    color: #475569;
  }

  .data-table-summary,
  .data-table-summary-inline {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }

  .data-table-summary {
    margin-bottom: 12px;
  }

  .data-table-summary-inline {
    flex: 1 1 auto;
    min-width: 0;
    white-space: nowrap;
  }

  .data-table-guide {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #005dff;
    font-size: 13px;
    line-height: 1.4;
  }

  .data-table-guide strong {
    color: #005dff;
  }

  .data-table-guide--ready {
    color: #10b981;
  }

  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 0;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }

  .column-settings-title {
    flex-shrink: 0;
    padding: 10px 12px;
    font-size: 13px;
    color: #475569;
    font-weight: 600;
  }

  .column-settings-body {
    overflow-y: auto;
    flex: 1;
    min-height: 0;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    scrollbar-color: rgba(148, 163, 184, 0.5) transparent;
  }

  .column-settings-body::-webkit-scrollbar {
    width: 6px;
  }

  .column-settings-body::-webkit-scrollbar-track {
    background: transparent;
  }

  .column-settings-body::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.5);
  }

  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 10px 12px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), #ffffff 70%);
    flex-shrink: 0;
  }

  .column-settings-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }

  .column-settings-table th:nth-child(1),
  .column-settings-table td:nth-child(1) {
    width: 37%;
  }

  .column-settings-table th:nth-child(2),
  .column-settings-table td:nth-child(2) {
    width: 26%;
  }

  .column-settings-table th:nth-child(3),
  .column-settings-table td:nth-child(3) {
    width: 22%;
  }

  .column-settings-table th:nth-child(4),
  .column-settings-table td:nth-child(4) {
    width: 15%;
  }

  .column-settings-table thead th {
    position: sticky;
    top: 0;
    background: #f8fafc;
    font-weight: 600;
    z-index: 1;
  }

  .column-settings-table th,
  .column-settings-table td {
    padding: 10px 8px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    text-align: left;
    font-size: 13px;
    color: #0f172a;
  }

  .column-name-input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid rgba(0, 93, 255, 0.35);
    border-radius: 8px;
    background: #f8fafc;
    font-size: 13px;
    color: #0f172a;
  }

  .values-cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .btn-reset,
  .btn-apply {
    min-width: 88px;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-reset {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid rgba(0, 93, 255, 0.18);
  }

  .btn-apply {
    background: #005dff;
    color: #fff;
  }

  .btn-apply--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .column-settings-table select {
    width: 100%;
    padding: 8px 30px 8px 10px;
    border: 1px solid rgba(0, 93, 255, 0.35);
    border-radius: 8px;
    background-color: #fff;
    font-size: 13px;
    color: #0f172a;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    /* 補上下拉箭頭，明確表示這是可點的下拉選單 */
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23005DFF' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  .column-settings-table select:hover {
    border-color: #005dff;
  }

  .column-settings-table select:focus {
    border-color: #005dff;
    box-shadow: 0 0 0 3px rgba(0, 93, 255, 0.15);
    outline: none;
  }

  /* Role 欄引導：下拉選單右下角的灰色「tap here」漣漪圈 */
  .role-select-wrap {
    position: relative;
  }

  .tap-hint {
    position: absolute;
    right: -7px;
    bottom: -7px;
    width: 24px;
    height: 24px;
    pointer-events: none;
    z-index: 2;
  }

  /* 點過 Role 選單後，圈圈淡出消失，而不是瞬間不見 */
  .tap-hint-fade-leave-active {
    transition: opacity 0.3s ease;
  }

  .tap-hint-fade-leave-to {
    opacity: 0;
  }

  .tap-hint__dot {
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: rgba(100, 116, 139, 0.7);
  }

  .tap-hint__ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2.5px solid rgba(100, 116, 139, 0.85);
    opacity: 0;
    animation: tap-ripple 2.4s ease-out infinite;
  }

  .tap-hint__ring--delay {
    animation-delay: 1.2s;
  }

  /* 從中間點的邊緣(scale 0.75 = 點的大小)往外擴 */
  @keyframes tap-ripple {
    0% {
      transform: scale(0.75);
      opacity: 0.9;
    }
    100% {
      transform: scale(1.5);
      opacity: 0;
    }
  }

  /* 未選 target 前，Role 下拉維持靜態高亮，把動效留給漣漪圈 */
  .role-select--attention {
    border-color: #94a3b8;
  }

  @media (prefers-reduced-motion: reduce) {
    .tap-hint__ring {
      animation: none;
      opacity: 0.5;
    }
  }

  .target-row td,
  .target-cell {
    background: rgba(0, 93, 255, 0.1);
  }

  .target-row {
    background: transparent;
  }

  .loader {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0, 93, 255, 0.25);
    border-top-color: #005dff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
