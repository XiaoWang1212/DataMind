<template>
  <section
    class="distribution-panel"
    :class="{ 'distribution-panel--full': isFullStage }"
  >
    <div class="distribution-header">
      <div v-if="file && !loading" class="distribution-summary">
        <span>{{ previewColumns.length }} 個欄位</span>
        <span>{{ allRows.length }} 筆資料</span>
      </div>
      <div v-if="fileName" class="distribution-file">
        已選檔案：{{ fileName }}
      </div>
    </div>

    <div v-if="!file">
      <div class="distribution-empty">
        請先在 File 節點上傳 CSV 檔案，這裡會顯示資料視覺化內容。
      </div>
    </div>

    <div v-else>
      <div v-if="loading" class="distribution-loading">
        資料讀取中...
      </div>
      <div v-else>
        <div
          class="distribution-chart-grid"
          :class="{ 'distribution-chart-grid--full': isFullStage }"
        >
          <div
            v-for="(chart, index) in chartData"
            :key="chart.label"
            class="distribution-chart-card"
          >
            <div
              class="distribution-chart-title"
              :class="{ expanded: isChartLabelExpanded(index) }"
            >
              {{ chart.label }}
            </div>
            <button
              v-if="isChartLabelLong(chart.label)"
              class="distribution-title-toggle"
              type="button"
              @click="toggleChartLabel(index)"
            >
              {{ isChartLabelExpanded(index) ? "收起" : "更多" }}
            </button>
            <div class="distribution-chart-subtitle">
              {{ chart.type === "numeric" ? "直方圖" : "類別分布" }}
            </div>
            <div class="distribution-chart-meta">
              <span>{{
                chart.type === "numeric" ? "數值欄位" : "類別欄位"
              }}</span>
              <span>{{ chart.counts.length }} 個區間</span>
            </div>
            <div class="distribution-chart-plot">
              <svg preserveAspectRatio="none" viewBox="0 0 320 170">
                <g v-for="(item, idx) in chart.counts" :key="item.label">
                  <rect
                    fill="var(--color-accent)"
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
                    fill="var(--color-secondary)"
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
                    fill="var(--color-ink)"
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
      </div>
    </div></section>
</template>

<script setup lang="ts">
  import type { Stage } from '@/composables/useDrawerDrag'
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
    drawerStage?: Stage
  }>()

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')
  const isFullStage = computed(() => props.drawerStage === 'full')
  const selectedFile = ref<File | null>(null)
  const previewColumns = ref<string[]>([])
  const allRows = ref<string[][]>([])
  const filePreviewRows = ref<string[][]>([])
  const errorMessage = ref('')
  const expandedCharts = ref<Record<number, boolean>>({})
  const loading = ref(false)

  function isChartLabelLong (label: string): boolean {
    return label.length > 30
  }

  function toggleChartLabel (index: number): void {
    expandedCharts.value = {
      ...expandedCharts.value,
      [index]: !expandedCharts.value[index],
    }
  }

  function isChartLabelExpanded (index: number): boolean {
    return Boolean(expandedCharts.value[index])
  }

  const hasPreview = computed(
    () => previewColumns.value.length > 0 && allRows.value.length > 0,
  )

  watch(
    () => props.file,
    async file => {
      if (!file) {
        selectedFile.value = null
        errorMessage.value = ''
        previewColumns.value = []
        allRows.value = []
        filePreviewRows.value = []
        loading.value = false
        return
      }

      if (file !== selectedFile.value) {
        loading.value = true
        await loadFile(file)
        loading.value = false
      }
    },
    { immediate: true },
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

  async function loadFile (file: File): Promise<void> {
    selectedFile.value = file
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

    return bins.map((count, index) => {
      const start = min + step * index
      const end = index === binCount - 1 ? max : start + step
      return { label: `${start.toFixed(1)} - ${end.toFixed(1)}`, count }
    })
  }
</script>

<style scoped>
  .distribution-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .distribution-panel--full {
    flex: 1;
    min-height: 0;
  }

  .distribution-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .distribution-title {
    font-weight: 700;
    font-size: 16px;
  }

  .distribution-file {
    flex-shrink: 0;
    margin-left: auto;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .distribution-empty {
    padding: 24px;
    border-radius: 12px;
    background: var(--color-surface);
    color: var(--color-secondary);
  }

  .distribution-summary {
    display: flex;
    gap: 14px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .distribution-chart-grid {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .distribution-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .distribution-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .distribution-chart-grid--full {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    align-content: start;
    flex: 1 1 380px;
    min-height: 380px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .distribution-chart-grid--full .distribution-chart-card {
    flex: none;
    min-width: 0;
  }

  .distribution-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    border-radius: 16px;
    background: rgba(248, 250, 252, 0.9);
    color: var(--color-secondary);
    font-size: 14px;
  }

  .distribution-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    padding: 12px;
    border-radius: 16px;
    background: var(--color-surface);
    border: 1px solid rgba(148, 163, 184, 0.16);
    scroll-snap-align: start;
    overflow-wrap: anywhere;
  }

  .distribution-chart-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
    color: var(--color-secondary);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    -webkit-line-clamp: 2;
  }

  .distribution-chart-title.expanded {
    -webkit-line-clamp: unset;
    white-space: normal;
  }

  .distribution-title-toggle {
    border: none;
    background: transparent;
    color: var(--color-accent);
    font-size: 12px;
    padding: 0;
    margin-bottom: 8px;
    cursor: pointer;
    text-align: left;
  }

  .distribution-chart-subtitle {
    font-size: 12px;
    color: var(--color-secondary);
    margin-bottom: 10px;
  }

  .distribution-chart-meta {
    display: flex;
    justify-content: space-between;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 8px;
  }

  .distribution-chart-plot {
    background: var(--color-surface);
    border-radius: 12px;
    padding: 10px;
  }
</style>
