<script setup lang="ts">
  import type { PyCaretTrainResponse } from '../types/pycaret'
  import { computed, ref } from 'vue'
  import { trainPyCaret } from '../api/pycaret'

  const file = ref<File | null>(null)
  const columns = ref<string[]>([])
  const rows = ref<string[][]>([])
  const targetCol = ref('')
  const outputDir = ref('artifacts/pycaret')

  const loading = ref(false)
  const errorMsg = ref('')
  const result = ref<PyCaretTrainResponse | null>(null)

  const maxPreviewRows = 50

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

  async function onPickFile (e: Event) {
    errorMsg.value = ''
    result.value = null
    const input = e.target as HTMLInputElement
    const f = input.files?.[0]
    if (!f) return

    file.value = f

    const text = await f.text()
    const lines = text
      .replace(/\r\n/g, '\n')
      .split('\n')
      .filter(l => l.trim().length > 0)

    if (lines.length < 2) {
      errorMsg.value = 'CSV 內容不足（至少要有標題列 + 1 筆資料）'
      return
    }

    const headerLine = lines[0]
    if (!headerLine) {
      errorMsg.value = 'CSV 標題列為空'
      return
    }

    columns.value = parseCsvLine(headerLine)
    rows.value = lines
      .slice(1, 1 + maxPreviewRows)
      .map(line => parseCsvLine(line))

    if (!targetCol.value || !columns.value.includes(targetCol.value)) {
      targetCol.value = columns.value[0] || ''
    }
  }

  async function submitTrain () {
    if (!file.value) {
      errorMsg.value = '請先選擇 CSV 檔案'
      return
    }
    if (!targetCol.value) {
      errorMsg.value = '請先選擇目標欄位'
      return
    }

    loading.value = true
    errorMsg.value = ''
    result.value = null
    try {
      const res = await trainPyCaret({
        file: file.value,
        targetCol: targetCol.value,
        outputDir: outputDir.value,
      })
      result.value = res
    } catch (error: any) {
      errorMsg.value = error?.message || '訓練失敗'
    } finally {
      loading.value = false
    }
  }

  const hasPreview = computed(
    () => columns.value.length > 0 && rows.value.length > 0,
  )

  const trainResult = computed(() => result.value?.result)

  const confusionLabels = computed(
    () => trainResult.value?.confusion_matrix?.labels || [],
  )

  const confusionMatrix = computed(
    () => trainResult.value?.confusion_matrix?.matrix || [],
  )

  const correlationColumns = computed(
    () => trainResult.value?.correlation_matrix?.columns || [],
  )

  const correlationMatrix = computed(
    () => trainResult.value?.correlation_matrix?.matrix || [],
  )

  const correlationMessage = computed(
    () => trainResult.value?.correlation_matrix?.message || '',
  )

  const resultJson = computed(() => {
    if (!result.value) return ''
    return JSON.stringify(result.value, null, 2)
  })

  function fmtNumber (value: number) {
    if (!Number.isFinite(value)) return '-'
    return Number.isInteger(value) ? `${value}` : value.toFixed(3)
  }
</script>

<template>
  <section class="pc-wrap">
    <h2>PyCaret API 測試</h2>

    <div class="toolbar">
      <input accept=".csv,text/csv" type="file" @change="onPickFile">
      <input
        v-model="outputDir"
        placeholder="output_dir (預設 artifacts/pycaret)"
      >
      <button :disabled="loading || !file || !targetCol" @click="submitTrain">
        {{ loading ? "訓練中..." : "送出訓練" }}
      </button>
    </div>

    <p v-if="errorMsg" class="err">{{ errorMsg }}</p>

    <div v-if="hasPreview" class="target-row">
      <span>目標欄位：</span>
      <select v-model="targetCol">
        <option v-for="c in columns" :key="c" :value="c">{{ c }}</option>
      </select>
      <small>（也可直接點下方表頭）</small>
    </div>

    <div v-if="hasPreview" class="table-wrap">
      <table class="excel">
        <thead>
          <tr>
            <th>#</th>
            <th
              v-for="col in columns"
              :key="col"
              :class="{ active: targetCol === col }"
              @click="targetCol = col"
            >
              {{ col }}
              <span v-if="targetCol === col">🎯</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, idx) in rows" :key="idx">
            <td>{{ idx + 1 }}</td>
            <td v-for="(v, j) in r" :key="`${idx}-${j}`">{{ v }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="confusionLabels.length > 0 && confusionMatrix.length > 0"
      class="matrix-wrap"
    >
      <h3>Confusion Matrix（最佳模型）</h3>
      <div class="table-wrap">
        <table class="excel">
          <thead>
            <tr>
              <th>Actual \ Predicted</th>
              <th v-for="label in confusionLabels" :key="`cm-header-${label}`">
                {{ label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIdx) in confusionMatrix"
              :key="`cm-row-${rowIdx}`"
            >
              <th>{{ confusionLabels[rowIdx] || `Class ${rowIdx + 1}` }}</th>
              <td
                v-for="(cell, colIdx) in row"
                :key="`cm-cell-${rowIdx}-${colIdx}`"
              >
                {{ fmtNumber(cell) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="correlationColumns.length > 0 && correlationMatrix.length > 0"
      class="matrix-wrap"
    >
      <h3>Correlation Matrix</h3>
      <div class="table-wrap">
        <table class="excel">
          <thead>
            <tr>
              <th>Feature</th>
              <th v-for="col in correlationColumns" :key="`corr-header-${col}`">
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, rowIdx) in correlationMatrix"
              :key="`corr-row-${rowIdx}`"
            >
              <th>
                {{ correlationColumns[rowIdx] || `Feature ${rowIdx + 1}` }}
              </th>
              <td
                v-for="(cell, colIdx) in row"
                :key="`corr-cell-${rowIdx}-${colIdx}`"
              >
                {{ fmtNumber(cell) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-else-if="correlationMessage" class="hint">{{ correlationMessage }}</p>

    <pre v-if="resultJson">{{ resultJson }}</pre>
  </section>
</template>

<style scoped>
  .pc-wrap {
    padding: 16px;
  }
  .toolbar {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .err {
    color: #d33;
  }
  .target-row {
    margin-bottom: 8px;
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .table-wrap {
    overflow: auto;
    border: 1px solid #ddd;
    max-height: 480px;
  }
  .matrix-wrap {
    margin-top: 16px;
  }
  .hint {
    margin-top: 8px;
  }
  .excel {
    border-collapse: collapse;
    min-width: 800px;
    width: 100%;
  }
  .excel th,
  .excel td {
    border: 1px solid #ddd;
    padding: 6px 8px;
    white-space: nowrap;
  }
  .excel thead th {
    position: sticky;
    top: 0;
    background: #fafafa;
    cursor: pointer;
  }
  .excel th.active {
    background: #e8f3ff;
    color: #0969da;
  }

  .excel ::selection {
    background: #1d4ed8;
    color: #ffffff;
  }

  .excel ::-moz-selection {
    background: #1d4ed8;
    color: #ffffff;
  }
</style>
