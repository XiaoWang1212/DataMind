<template>
  <section class="data-table-panel">
    <div class="data-table-header">
      <div class="data-table-title">Data Table</div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
    </div>

    <div v-if="props.loading" class="data-table-loading-overlay">
      <div class="loader" />
      <div>Data Table 正在等待目標變數...</div>
    </div>

    <div v-if="!file" class="data-table-empty">
      請先在 File 節點上傳 CSV 檔案，才能顯示資料表。
    </div>

    <div v-else-if="previewColumns.length === 0" class="data-table-empty">
      無法解析 CSV 檔案內容。
    </div>

    <div v-else>
      <div class="data-table-summary">
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
                  <select v-model="column.role">
                    <option
                      v-for="role in roleOptions"
                      :key="role"
                      :disabled="
                        role === 'target' &&
                          hasOtherTarget(index) &&
                          column.role !== 'target'
                      "
                      :value="role"
                    >
                      {{ roleLabels[role] }}
                    </option>
                  </select>
                </td>
                <td
                  :class="[
                    'values-cell',
                    { 'target-cell': column.role === 'target' },
                  ]"
                >
                  {{ getColumnValueLabel(index) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="column-settings-actions">
          <button class="btn-reset" type="button" @click="resetColumnSettings">
            Reset
          </button>
          <button class="btn-apply" type="button" @click="applyColumnSettings">
            Apply
          </button>
        </div>
      </div>

      <div class="data-table-scroll" :style="tableScrollStyle">
        <table>
          <thead>
            <tr>
              <th
                v-for="(header, index) in previewColumns"
                :key="header"
                class="data-table-header-cell"
              >
                <div
                  class="cell-inner"
                  :class="{ 'cell-inner--expanded': isHeaderExpanded(index) }"
                >
                  {{ getDisplayText(header, isHeaderExpanded(index)) }}
                </div>
                <button
                  v-if="shouldShowToggle(header)"
                  class="toggle-expand"
                  type="button"
                  @click="toggleHeaderExpand(index)"
                >
                  {{ isHeaderExpanded(index) ? "less" : "more..." }}
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in displayRows" :key="rowIndex">
              <td
                v-for="(cell, cellIndex) in row"
                :key="`${rowIndex}-${cellIndex}`"
                class="data-table-cell"
              >
                <div
                  class="cell-inner"
                  :class="{
                    'cell-inner--expanded': isCellExpanded(rowIndex, cellIndex),
                  }"
                >
                  {{
                    getDisplayText(cell, isCellExpanded(rowIndex, cellIndex))
                  }}
                </div>
                <button
                  v-if="shouldShowToggle(cell)"
                  class="toggle-expand"
                  type="button"
                  @click="toggleCellExpand(rowIndex, cellIndex)"
                >
                  {{ isCellExpanded(rowIndex, cellIndex) ? "less" : "more..." }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
  const previewDataRows = ref<string[][]>([])
  const columnSettings = ref<ColumnSetting[]>([])

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

  const rowCount = 10
  const displayRows = computed(() => previewDataRows.value.slice(0, rowCount))
  const tableScrollStyle = computed(() => ({
    maxHeight: `${rowCount * 48 + 80}px`,
  }))

  const originalColumnSettings = ref<ColumnSetting[]>([])
  const nameMaxLength = 32
  const expandedHeaders = ref(new Set<number>())
  const expandedCells = ref(new Set<string>())
  const textLimit = 24

  function shouldShowToggle (value: string): boolean {
    return value.includes('\n') || value.length > textLimit
  }

  function isHeaderExpanded (index: number): boolean {
    return expandedHeaders.value.has(index)
  }

  function toggleHeaderExpand (index: number): void {
    if (expandedHeaders.value.has(index)) {
      expandedHeaders.value.delete(index)
    } else {
      expandedHeaders.value.add(index)
    }
  }

  function cellKey (rowIndex: number, cellIndex: number): string {
    return `${rowIndex}-${cellIndex}`
  }

  function isCellExpanded (rowIndex: number, cellIndex: number): boolean {
    return expandedCells.value.has(cellKey(rowIndex, cellIndex))
  }

  function toggleCellExpand (rowIndex: number, cellIndex: number): void {
    const key = cellKey(rowIndex, cellIndex)
    if (expandedCells.value.has(key)) {
      expandedCells.value.delete(key)
    } else {
      expandedCells.value.add(key)
    }
  }

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

  function hasOtherTarget (index: number): boolean {
    return columnSettings.value.some(
      (item, itemIndex) => itemIndex !== index && item.role === 'target',
    )
  }

  function cloneColumnSetting (item: ColumnSetting): ColumnSetting {
    return {
      name: item.name,
      type: item.type,
      role: item.role,
      availableTypes: [...item.availableTypes],
    }
  }

  function cloneSettings (settings: ColumnSetting[]): ColumnSetting[] {
    return settings.map(setting => cloneColumnSetting(setting))
  }

  function buildColumnSettings (): void {
    const existingMap = new Map(
      (props.columnConfig ?? []).map(config => [config.name, config]),
    )

    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      const existing = existingMap.get(header)
      const selectedType
        = existing && availableTypes.includes(existing.type)
          ? existing.type
          : (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? 'feature'

      return {
        name: header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })

    originalColumnSettings.value = cloneSettings(columnSettings.value)
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
    if (originalColumnSettings.value.length === 0) {
      buildColumnSettings()
      return
    }
    columnSettings.value = cloneSettings(originalColumnSettings.value)
  }

  function applyColumnSettings (): void {
    emitColumnConfig()
    originalColumnSettings.value = cloneSettings(columnSettings.value)
    emit('apply-column-config')
  }

  function getColumnValueLabel (index: number): string {
    const column = columnSettings.value[index]
    if (!column || column.type !== 'categorial') return '—'

    const values = previewDataRows.value
      .map(row => row[index] ?? '')
      .map(value => value.trim())
      .filter(value => value.length > 0)
    const uniqueValues = Array.from(new Set(values))
    return uniqueValues.slice(0, 6).join(', ')
  }

  watch(
    () => props.file,
    file => {
      if (file) {
        void loadFile(file)
      } else {
        previewColumns.value = []
        previewDataRows.value = []
        columnSettings.value = []
        originalColumnSettings.value = []
      }
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

  function getDisplayText (value: string, expanded: boolean): string {
    if (expanded || value.length <= textLimit) return value
    return value.slice(0, textLimit) + '...'
  }

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
    gap: 14px;
  }

  .data-table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .data-table-title {
    font-weight: 700;
    font-size: 16px;
  }

  .data-table-file {
    color: #475569;
    font-size: 13px;
  }

  .data-table-empty {
    padding: 20px;
    border-radius: 12px;
    background: #f8fafc;
    color: #475569;
  }

  .data-table-summary {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }

  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: #ffffff;
    max-height: 380px;
    overflow: hidden;
  }

  .column-settings-title {
    margin-bottom: 10px;
    font-size: 13px;
    color: #475569;
    font-weight: 600;
  }

  .column-settings-body {
    overflow-y: auto;
    flex: 1;
    min-height: 0;
    overscroll-behavior: contain;
  }

  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 14px;
    padding-top: 10px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), #ffffff 70%);
    flex-shrink: 0;
  }

  .column-settings-table {
    width: 100%;
    border-collapse: collapse;
  }

  .column-settings-table thead th {
    position: sticky;
    top: 0;
    background: #f8fafc;
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
    border: 1px solid rgba(148, 163, 184, 0.5);
    border-radius: 10px;
    background: #f8fafc;
    font-size: 13px;
    color: #0f172a;
  }

  .values-cell {
    max-width: 300px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 14px;
  }

  .btn-reset,
  .btn-apply {
    min-width: 88px;
    border: none;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-reset {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid rgba(148, 163, 184, 0.5);
  }

  .btn-apply {
    background: #2563eb;
    color: #fff;
  }

  .column-settings-table th {
    background: #f8fafc;
    font-weight: 600;
  }

  .column-settings-table select {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid rgba(148, 163, 184, 0.5);
    border-radius: 10px;
    background: #f8fafc;
    font-size: 13px;
    color: #0f172a;
    appearance: none;
  }

  .target-row td,
  .target-cell {
    background: rgba(59, 130, 246, 0.12);
  }

  .target-row {
    background: transparent;
  }

  .data-table-loading-overlay {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 16px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.92);
    border: 1px dashed rgba(96, 165, 250, 0.7);
    color: #2563eb;
    font-size: 14px;
  }

  .loader {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(37, 99, 235, 0.25);
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .data-table-scroll {
    overflow-x: auto;
    overflow-y: visible;
    border-radius: 16px;
    background: #fff;
    border: 1px solid rgba(148, 163, 184, 0.16);
  }

  table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    text-align: left;
    font-size: 13px;
    color: #0f172a;
    white-space: normal;
  }

  th {
    background: #f8fafc;
    color: #0f172a;
    font-weight: 600;
  }

  .data-table-header-cell,
  .data-table-cell {
    min-width: 140px;
  }

  .cell-inner {
    display: block;
    width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-height: 1.5em;
  }

  .cell-inner.cell-inner--expanded {
    display: inline-block;
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-all;
    max-height: none;
  }

  .data-table-header-cell .cell-inner.cell-inner--expanded {
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-all;
  }

  .toggle-expand {
    display: inline-flex;
    margin-top: 4px;
    font-size: 12px;
    color: #2563eb;
    background: transparent;
    border: none;
    padding: 0;
    cursor: pointer;
  }

  .toggle-expand:hover {
    text-decoration: underline;
  }
</style>
