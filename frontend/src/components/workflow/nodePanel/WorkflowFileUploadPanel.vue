<template>
  <div class="workflow-file-upload-panel">
    <div
      v-if="!hasPreview"
      class="upload-modal-dropzone"
      :class="{ 'upload-modal-dropzone--active': dragActive }"
      @dragenter.prevent="onDragEnter"
      @dragleave.prevent="onDragLeave"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <div class="upload-modal-icon">⇪</div>
      <div class="upload-modal-line1">將檔案拖曳至此處</div>
      <div class="upload-modal-line2">或點擊下方按鈕選擇 CSV 檔案</div>
      <input
        ref="fileInput"
        accept=".csv,text/csv"
        hidden
        type="file"
        @change="onFileChange"
      >
      <button class="upload-modal-button" type="button" @click="browseFile">
        瀏覽檔案
      </button>
      <div v-if="fileName" class="upload-modal-file">
        已選檔案：{{ fileName }}
      </div>
    </div>

    <div v-if="errorMessage" class="upload-modal-error">
      {{ errorMessage }}
    </div>

    <div v-if="hasPreview" class="upload-modal-preview">
      <div class="upload-modal-preview-header">資料視覺化</div>
      <div class="upload-modal-preview-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ allRows.length }} 筆資料</span>
      </div>

      <div class="upload-modal-chart-grid">
        <div
          v-for="chart in chartData"
          :key="chart.label"
          class="upload-modal-chart-card"
        >
          <div class="upload-modal-chart-title">{{ chart.label }}</div>
          <div class="upload-modal-chart-subtitle">
            {{ chart.type === "numeric" ? "直方圖" : "類別分布" }}
          </div>
          <div class="upload-modal-chart-meta">
            <span>{{
              chart.type === "numeric" ? "數值欄位" : "類別欄位"
            }}</span>
            <span>{{ chart.counts.length }} 個區間</span>
          </div>
          <div class="upload-modal-chart-plot">
            <svg preserveAspectRatio="none" viewBox="0 0 320 170">
              <g v-for="(item, idx) in chart.counts" :key="item.label">
                <rect
                  fill="#2563eb"
                  :height="
                    Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                  "
                  rx="6"
                  :width="Math.max(24, 280 / chart.counts.length - 8)"
                  :x="12 + idx * (300 / chart.counts.length)"
                  :y="
                    150 -
                      Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                  "
                />
                <text
                  fill="#475569"
                  font-size="10"
                  text-anchor="middle"
                  :x="
                    12 +
                      idx * (300 / chart.counts.length) +
                      Math.max(24, 280 / chart.counts.length - 8) / 2
                  "
                  y="165"
                >
                  {{ item.label }}
                </text>
                <text
                  fill="#0f172a"
                  font-size="10"
                  text-anchor="middle"
                  :x="
                    12 +
                      idx * (300 / chart.counts.length) +
                      Math.max(24, 280 / chart.counts.length - 8) / 2
                  "
                  :y="
                    140 -
                      Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                  "
                >
                  {{ item.count }}
                </text>
              </g>
            </svg>
          </div>
        </div>
      </div>

      <div class="upload-modal-preview-table">
        <table>
          <thead>
            <tr>
              <th v-for="column in previewColumns" :key="column">
                {{ column }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in filePreviewRows" :key="rowIndex">
              <td
                v-for="(cell, cellIndex) in row"
                :key="`${rowIndex}-${cellIndex}`"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'

  const props = defineProps<{
    fileName?: string | null
  }>()

  const emit = defineEmits<{
    (e: 'update:fileName', value: string): void
    (e: 'update:file', value: File): void
  }>()

  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const errorMessage = ref('')
  const previewColumns = ref<string[]>([])
  const allRows = ref<string[][]>([])
  const filePreviewRows = ref<string[][]>([])
  const dragActive = ref(false)

  const fileName = computed(() => props.fileName ?? '')
  const hasPreview = computed(
    () => previewColumns.value.length > 0 && allRows.value.length > 0,
  )

  const chartData = computed(() => {
    if (!hasPreview.value) {
      return [] as Array<{
        label: string
        type: 'numeric' | 'categorical'
        counts: { label: string, count: number }[]
        maxCount: number
      }>
    }

    return previewColumns.value.map((label, index) => {
      const values = allRows.value.map(row => row[index] ?? '')
      const cleanedValues = values.map(value => value.trim())
      const numericValues = cleanedValues
        .filter(value => value !== '' && !Number.isNaN(Number(value)))
        .map(Number)
      const isNumeric
        = numericValues.length
          === cleanedValues.filter(value => value !== '').length
          && numericValues.length > 0

      if (isNumeric) {
        const counts = computeNumericBins(numericValues)
        const maxCount = Math.max(...counts.map(item => item.count), 1)
        return {
          label,
          type: 'numeric' as const,
          counts,
          maxCount,
        }
      }

      const frequency: Record<string, number> = {}
      for (const value of cleanedValues) {
        const key = value || '(空值)'
        frequency[key] = (frequency[key] || 0) + 1
      }

      const frequencyEntries = Object.entries(frequency) as [string, number][]
      const counts = frequencyEntries
        .toSorted(([, a], [, b]) => b - a)
        .slice(0, 8)
        .map(([label, count]) => ({ label, count }))
      const maxCount = Math.max(...counts.map(item => item.count), 1)

      return {
        label,
        type: 'categorical' as const,
        counts,
        maxCount,
      }
    })
  })

  function browseFile () {
    fileInput.value?.click()
  }

  function onDragEnter () {
    dragActive.value = true
  }

  function onDragLeave () {
    dragActive.value = false
  }

  function onDrop (event: DragEvent) {
    dragActive.value = false
    const files = event.dataTransfer?.files
    const file = files?.item(0)
    if (file) {
      loadFile(file)
    }
  }

  function onFileChange (event: Event) {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) {
      loadFile(file)
    }
  }

  async function loadFile (file: File) {
    selectedFile.value = file
    emit('update:file', file)
    errorMessage.value = ''
    previewColumns.value = []
    filePreviewRows.value = []

    if (!file.name.toLowerCase().endsWith('.csv')) {
      errorMessage.value = '目前僅支援 CSV 檔案格式。'
      return
    }

    const text = await decodeFileText(file)
    const lines: string[] = text
      .replace(/\r\n/g, '\n')
      .split('\n')
      .filter(line => typeof line === 'string' && line.trim().length > 0)

    if (lines.length === 0) {
      errorMessage.value = 'CSV 檔案為空。'
      return
    }

    const headerLine = lines[0]!
    previewColumns.value = parseCsvLine(headerLine)
    const allDataRows = lines.slice(1).map(line => parseCsvLine(line))
    allRows.value = allDataRows
    filePreviewRows.value = allDataRows.slice(0, 10)
    emit('update:fileName', file.name)
  }

  async function decodeFileText (file: File) {
    const buffer = await file.arrayBuffer()
    const decoderUtf8 = new TextDecoder('utf-8', { fatal: true })
    try {
      return decoderUtf8.decode(buffer)
    } catch {
      const decoderBig5 = new TextDecoder('big5')
      return decoderBig5.decode(buffer)
    }
  }

  function parseCsvLine (line: string): string[] {
    const out: string[] = []
    let cur = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const ch = line[i]
      const next = line[i + 1]

      if (ch === '"' && inQuotes && next === '"') {
        cur += '"'
        i++
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

  function computeNumericBins (values: number[]) {
    if (values.length === 0) {
      return [] as Array<{ label: string, count: number }>
    }

    const min = Math.min(...values)
    const max = Math.max(...values)
    const binCount = Math.min(
      6,
      Math.max(3, Math.ceil(Math.sqrt(values.length))),
    )
    const step = max === min ? 1 : (max - min) / binCount
    const bins = Array.from({ length: binCount }, () => 0)

    for (const value of values) {
      const index
        = max === min
          ? 0
          : Math.min(binCount - 1, Math.floor((value - min) / step))
      bins[index] = (bins[index] ?? 0) + 1
    }

    return bins
      .map((count, index) => {
        const start = min + step * index
        const end = index === binCount - 1 ? max : start + step
        const label
          = max === min ? `${min}` : `${Math.round(start)} - ${Math.round(end)}`
        return { label, count }
      })
      .filter(item => item.count > 0)
  }
</script>

<style scoped>
  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed rgba(0, 93, 255, 0.28);
    border-radius: 16px;
    background: rgba(0, 93, 255, 0.04);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__desc {
    margin: 0;
    color: #475569;
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.13);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: #2563eb;
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }

  .upload-modal-line2 {
    color: #475569;
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: #475569;
  }

  .upload-modal-error {
    color: #b91c1c;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: #475569;
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .upload-modal-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .upload-modal-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .upload-modal-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: #f8fafc;
    scroll-snap-align: start;
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #0f172a;
  }

  .upload-modal-chart-subtitle {
    margin-top: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #475569;
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: minmax(75px, 1.4fr) 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: #2563eb;
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: #0f172a;
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
    background: #ffffff;
    color: #0f172a;
  }

  .upload-modal-preview-table table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
    color: #0f172a;
  }

  .upload-modal-preview-table th {
    background: #f8fafc;
    color: #0f172a;
  }

  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }
</style>
