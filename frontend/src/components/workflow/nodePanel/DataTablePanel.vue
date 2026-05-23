<template>
  <section class="data-table-panel">
    <div class="data-table-header">
      <div class="data-table-title">Data Table</div>
      <div v-if="fileName" class="data-table-file">
        已選檔案：{{ fileName }}
      </div>
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

      <div class="data-table-scroll">
        <table>
          <thead>
            <tr>
              <th v-for="header in previewColumns" :key="header">
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in displayRows" :key="rowIndex">
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
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    file?: File | null
    fileName?: string | null
    previewRows?: number
  }>()

  const fileName = computed(() => props.fileName ?? props.file?.name ?? '')
  const previewColumns = ref<string[]>([])
  const previewDataRows = ref<string[][]>([])

  const rowCount = computed(() => Math.max(1, props.previewRows ?? 10))
  const displayRows = computed(() =>
    previewDataRows.value.slice(0, rowCount.value),
  )

  watch(
    () => props.file,
    file => {
      if (file) {
        void loadFile(file)
      } else {
        previewColumns.value = []
        previewDataRows.value = []
      }
    },
    { immediate: true },
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
    } catch {
      previewColumns.value = []
      previewDataRows.value = []
    }
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

  .data-table-scroll {
    overflow-x: auto;
    border-radius: 16px;
    background: #fff;
    border: 1px solid rgba(148, 163, 184, 0.16);
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    text-align: left;
    font-size: 13px;
    color: #0f172a;
  }

  th {
    background: #f8fafc;
    color: #0f172a;
    font-weight: 600;
  }
</style>
