<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { trainPyCaret } from '@/api/pycaret'

  const file = ref<File | null>(null)
  const columns = ref<string[]>([])
  const rows = ref<string[][]>([])
  const targetCol = ref('')
  const outputDir = ref('artifacts/pycaret')

  const loading = ref(false)
  const errorMsg = ref('')
  const result = ref<any>(null)

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
    rows.value = lines.slice(1, 1 + maxPreviewRows).map(parseCsvLine)

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

    <pre v-if="result">{{ result }}</pre>
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
