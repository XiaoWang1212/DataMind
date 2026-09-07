# 結果面板 CSV 匯出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 幫 Test & Score、Feature Importance、Classification Evaluation、Compute CI 四個結果節點加上 CSV 匯出（跟現有的 Excel 匯出並存），並順便修掉 Compute CI「跨 Fold 摘要」檢視匯出到舊資料的 bug。

**Architecture:** 純前端改動。共用元件 `ResultTableActions.vue` 的匯出按鈕從「點下去直接匯出 Excel」改成「點下去彈出小選單（Excel / CSV 二選一）」，`tableExport.ts` 新增對應的 CSV 產生函式。因為 Test & Score、Feature Importance 已經在用這個共用元件，改完自動繼承；Compute CI、Classification Evaluation 兩個面板各自的資料處理各修一個 task。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript，沿用既有的 Blob + `<a download>` 下載模式。

## Global Constraints

- 完全不動後端——所有資料前端都已經有
- 不新增通用 Modal/Dropdown 元件——選單直接寫在 `ResultTableActions.vue` 裡，用全站既有的 `glass-menu` 樣式（`frontend/src/styles/glass.css`，在 `@layer vuetify-final` 裡，只提供背景/模糊/邊框/陰影，不會跟自己 scoped 的版面 CSS 衝突——這是 `CustomSelect.vue` 的 `.cs-popup glass-menu` 已經在用的同一個組合模式）
- CSV 內容開頭要加 UTF-8 BOM（用 `﻿` 跳脫序列寫在程式碼裡，不要貼看不見的字元），避免 Excel 開啟中文亂碼
- Test & Score、Feature Importance 兩個節點的檔案完全不用改
- 型別檢查在 `datamind-frontend` container 內執行（`docker exec datamind-frontend sh -c "cd /app && npm run type-check"`）
- 直接在 `main` branch 上工作，不開額外 git worktree

---

### Task 1: `tableExport.ts` 新增 CSV 匯出 + `ResultTableActions.vue` 改成選單

**Files:**
- Modify: `frontend/src/utils/tableExport.ts`
- Modify: `frontend/src/components/common/ResultTableActions.vue`

**Interfaces:**
- Produces: `exportTableToCsv(headers: string[], rows: Array<Array<string | number>>, filename: string): void`
- Produces: `ResultTableActions.vue` 的 props/emits 完全不變（`headers`/`rows`/`filename`），內部行為改變（點匯出按鈕變成開選單），Task 2/3 完全不需要知道這個內部改變，直接沿用現有的 `<ResultTableActions :headers :rows :filename />` 用法即可

- [ ] **Step 1: 新增 `exportTableToCsv()`**

`frontend/src/utils/tableExport.ts` 現有的 `exportTableToExcel()`（第 22-41 行）之後新增：
```typescript
function toCsvCell (cell: string | number): string {
  const text = typeof cell === 'number' ? String(cell) : cell
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

/** 產生 CSV 並觸發瀏覽器下載，開頭加 UTF-8 BOM 避免 Excel 開啟時中文亂碼。 */
export function exportTableToCsv (
  headers: string[],
  rows: Array<Array<string | number>>,
  filename: string,
): void {
  const lines = [headers, ...rows].map(row => row.map(cell => toCsvCell(cell)).join(','))
  const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
```

- [ ] **Step 2: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 沒有新增錯誤（`toCsvCell` 目前只在這個檔案內部使用，不用 export）

- [ ] **Step 3: `ResultTableActions.vue` 改成選單**

現有的整個檔案（`frontend/src/components/common/ResultTableActions.vue`）內容：
```vue
<template>
  <div class="result-table-actions">
    <button
      class="result-table-actions__btn"
      :class="{ 'result-table-actions__btn--error': copyState === 'error' }"
      :title="copyState === 'error' ? '複製失敗' : '複製表格'"
      type="button"
      @click="handleCopy"
    >
      <v-icon :icon="copyIcon" size="16" />
    </button>
    <button
      class="result-table-actions__btn"
      title="匯出 Excel"
      type="button"
      @click="handleExport"
    >
      <v-icon icon="mdi-file-excel-outline" size="16" />
    </button>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { copyTableToClipboard, exportTableToExcel } from '@/utils/tableExport'

  const props = defineProps<{
    headers: string[]
    rows: Array<Array<string | number>>
    filename: string
  }>()

  type CopyState = 'idle' | 'copied' | 'error'

  const copyState = ref<CopyState>('idle')
  let resetTimer: ReturnType<typeof setTimeout> | undefined

  const copyIcon = computed(() => {
    if (copyState.value === 'copied') return 'mdi-check'
    if (copyState.value === 'error') return 'mdi-alert-outline'
    return 'mdi-content-copy'
  })

  function flashState (state: CopyState): void {
    copyState.value = state
    clearTimeout(resetTimer)
    resetTimer = setTimeout(() => {
      copyState.value = 'idle'
    }, 1500)
  }

  async function handleCopy (): Promise<void> {
    try {
      await copyTableToClipboard(props.headers, props.rows)
      flashState('copied')
    } catch {
      flashState('error')
    }
  }

  function handleExport (): void {
    exportTableToExcel(props.headers, props.rows, props.filename)
  }
</script>

<style scoped>
  .result-table-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .result-table-actions__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out);
  }

  @media (hover: hover) and (pointer: fine) {
    .result-table-actions__btn:hover {
      background: color-mix(in oklab, var(--color-ink) 8%, transparent);
      color: var(--color-ink);
    }
  }

  .result-table-actions__btn--error {
    color: var(--color-error-text, #dc2626);
  }
</style>
```
整檔改成：
```vue
<template>
  <div class="result-table-actions">
    <button
      class="result-table-actions__btn"
      :class="{ 'result-table-actions__btn--error': copyState === 'error' }"
      :title="copyState === 'error' ? '複製失敗' : '複製表格'"
      type="button"
      @click="handleCopy"
    >
      <v-icon :icon="copyIcon" size="16" />
    </button>
    <div ref="exportWrapRef" class="result-table-actions__export-wrap">
      <button
        class="result-table-actions__btn"
        title="匯出"
        type="button"
        @click="exportMenuOpen = !exportMenuOpen"
      >
        <v-icon icon="mdi-download-outline" size="16" />
      </button>
      <div v-if="exportMenuOpen" class="result-table-actions__menu glass-menu">
        <button class="result-table-actions__menu-item" type="button" @click="handleExportExcel">
          <v-icon icon="mdi-file-excel-outline" size="15" />
          匯出 Excel
        </button>
        <button class="result-table-actions__menu-item" type="button" @click="handleExportCsv">
          <v-icon icon="mdi-file-delimited-outline" size="15" />
          匯出 CSV
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { copyTableToClipboard, exportTableToCsv, exportTableToExcel } from '@/utils/tableExport'

  const props = defineProps<{
    headers: string[]
    rows: Array<Array<string | number>>
    filename: string
  }>()

  type CopyState = 'idle' | 'copied' | 'error'

  const copyState = ref<CopyState>('idle')
  let resetTimer: ReturnType<typeof setTimeout> | undefined

  const copyIcon = computed(() => {
    if (copyState.value === 'copied') return 'mdi-check'
    if (copyState.value === 'error') return 'mdi-alert-outline'
    return 'mdi-content-copy'
  })

  function flashState (state: CopyState): void {
    copyState.value = state
    clearTimeout(resetTimer)
    resetTimer = setTimeout(() => {
      copyState.value = 'idle'
    }, 1500)
  }

  async function handleCopy (): Promise<void> {
    try {
      await copyTableToClipboard(props.headers, props.rows)
      flashState('copied')
    } catch {
      flashState('error')
    }
  }

  const exportMenuOpen = ref(false)
  const exportWrapRef = ref<HTMLElement | null>(null)

  function handleExportExcel (): void {
    exportTableToExcel(props.headers, props.rows, props.filename)
    exportMenuOpen.value = false
  }

  function handleExportCsv (): void {
    exportTableToCsv(props.headers, props.rows, props.filename)
    exportMenuOpen.value = false
  }

  function onDocPointer (e: PointerEvent): void {
    if (exportWrapRef.value?.contains(e.target as Node)) return
    exportMenuOpen.value = false
  }

  watch(exportMenuOpen, isOpen => {
    if (isOpen) document.addEventListener('pointerdown', onDocPointer, true)
    else document.removeEventListener('pointerdown', onDocPointer, true)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocPointer, true)
  })
</script>

<style scoped>
  .result-table-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .result-table-actions__btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    padding: 0;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out);
  }

  @media (hover: hover) and (pointer: fine) {
    .result-table-actions__btn:hover {
      background: color-mix(in oklab, var(--color-ink) 8%, transparent);
      color: var(--color-ink);
    }
  }

  .result-table-actions__btn--error {
    color: var(--color-error-text, #dc2626);
  }

  .result-table-actions__export-wrap {
    position: relative;
  }

  .result-table-actions__menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 4px;
    min-width: 120px;
    border-radius: var(--radius-sm);
  }

  .result-table-actions__menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-text);
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    white-space: nowrap;
  }

  @media (hover: hover) and (pointer: fine) {
    .result-table-actions__menu-item:hover {
      background: color-mix(in oklab, var(--color-ink) 10%, transparent);
    }
  }
</style>
```

- [ ] **Step 4: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "ResultTableActions\|tableExport"` 沒有輸出

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/utils/tableExport.ts frontend/src/components/common/ResultTableActions.vue
git commit -m "feat: add CSV export option alongside Excel in ResultTableActions"
```

---

### Task 2: `ComputeCiPanel.vue`——修「跨 Fold 摘要」匯出到舊資料的 bug

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue`

**Interfaces:**
- Consumes: Task 1 產出的 `ResultTableActions.vue`（props 不變，不需要改用法）
- Consumes: 這個檔案既有的 `viewMode`（`Ref<'fold' | 'summary'>`）、`currentSplitMetrics`（`ComputedRef<MetricRow[]>`）、`crossFoldSummary`（`ComputedRef<SummaryRow[]>`，`SummaryRow` 有 `metric`/`avgCiWidth`/`minValue`/`maxValue`/`meanValue` 欄位）、`fmt()`、`selectedModel`、`selectedFold`

- [ ] **Step 1: `exportHeaders`/`exportRows`/`exportFilename` 依 `viewMode` 切換**

現有的（第 213-219 行附近）：
```typescript
  const exportHeaders = ['指標', 'CI Lower', 'Value', 'CI Upper']

  const exportRows = computed(() =>
    currentSplitMetrics.value.map(m => [m.metric, fmt(m.ci_lower), fmt(m.value), fmt(m.ci_upper)]),
  )

  const exportFilename = computed(() => `bootstrap_ci_${selectedModel.value}_${selectedFold.value}`)
```
改成：
```typescript
  const exportHeaders = computed(() =>
    viewMode.value === 'fold'
      ? ['指標', 'CI Lower', 'Value', 'CI Upper']
      : ['指標', '平均信賴區間寬度', '最小值', '最大值', '平均值'],
  )

  const exportRows = computed(() => {
    if (viewMode.value === 'fold') {
      return currentSplitMetrics.value.map(m => [m.metric, fmt(m.ci_lower), fmt(m.value), fmt(m.ci_upper)])
    }
    return crossFoldSummary.value.map(s => [
      s.metric, fmt(s.avgCiWidth), fmt(s.minValue), fmt(s.maxValue), fmt(s.meanValue),
    ])
  })

  const exportFilename = computed(() =>
    viewMode.value === 'fold'
      ? `bootstrap_ci_${selectedModel.value}_${selectedFold.value}`
      : `bootstrap_ci_summary_${selectedModel.value}`,
  )
```
（`exportHeaders` 從純陣列改成 `computed`，第 2 步驟要記得把 template 綁定改成 `:headers="exportHeaders"` 依然正確——`computed` 在 template 裡跟 ref 一樣直接用變數名稱綁定，`ResultTableActions` 的 prop 也還是吃 `string[]`，不用額外 `.value`）

- [ ] **Step 2: `<ResultTableActions>` 的 `v-if` 依 `viewMode` 切換**

現有的（第 11-16 行附近）：
```html
        <ResultTableActions
          v-if="currentSplitMetrics.length > 0"
          :filename="exportFilename"
          :headers="exportHeaders"
          :rows="exportRows"
        />
```
改成：
```html
        <ResultTableActions
          v-if="viewMode === 'fold' ? currentSplitMetrics.length > 0 : crossFoldSummary.length > 0"
          :filename="exportFilename"
          :headers="exportHeaders"
          :rows="exportRows"
        />
```

- [ ] **Step 3: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "ComputeCiPanel"` 沒有輸出

- [ ] **Step 4: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue
git commit -m "fix: export cross-fold summary data instead of stale single-fold data"
```

---

### Task 3: `ConfusionMatrixPanel.vue`——ROC/PR/校準曲線補上匯出

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: Task 1 產出的 `ResultTableActions.vue`（props 不變，這個檔案已經在用，不需要改用法——模板上的 `<ResultTableActions v-if="exportableTable">` 完全不用動，只改 `exportableTable` 這個 computed 本身）
- Consumes: 這個檔案既有的 `groupedResults`（`ComputedRef<GroupedResult[]>`）、`visibleModelNames`（`ComputedRef<string[]>`）、`currentCalibrationCurve`（`ComputedRef<CalibrationCurveData | null>`）、`selectedModel`、`selectedFold`、`RocPrCurveData`/`CalibrationCurveData` 型別（第 329-339 行附近：`RocPrCurveData` 有 `posLabel`/`roc: {fpr, tpr}`/`pr: {precision, recall}`，`CalibrationCurveData` 有 `posLabel`/`probTrue`/`probPred`）

- [ ] **Step 1: `exportableTable` 補上 `roc`/`pr`/`calibration` 三個分支**

現有的（第 591-618 行）：
```typescript
  const exportableTable = computed(() => {
    const suffix = `${selectedModel.value}_${selectedFold.value}`

    if (activeTab.value === 'matrix' && currentMatrix.value) {
      const matrix = currentMatrix.value
      return {
        headers: ['', ...matrix.labels.map(label => `預測：${label}`)],
        rows: matrix.matrix.map((row, i) => [`實際：${matrix.labels[i]}`, ...row]),
        filename: `confusion_matrix_${suffix}`,
      }
    }

    if (activeTab.value === 'perClass' && perClassRows.value.length > 0) {
      return {
        headers: ['類別', 'Precision', 'Recall', 'F1', '樣本數'],
        rows: perClassRows.value.map(row => [
          row.label,
          row.precision.toFixed(3),
          row.recall.toFixed(3),
          row.f1.toFixed(3),
          row.support,
        ]),
        filename: `per_class_metrics_${suffix}`,
      }
    }

    return null
  })
```
改成（在 `perClass` 分支之後、`return null` 之前插入三個新分支）：
```typescript
  const exportableTable = computed(() => {
    const suffix = `${selectedModel.value}_${selectedFold.value}`

    if (activeTab.value === 'matrix' && currentMatrix.value) {
      const matrix = currentMatrix.value
      return {
        headers: ['', ...matrix.labels.map(label => `預測：${label}`)],
        rows: matrix.matrix.map((row, i) => [`實際：${matrix.labels[i]}`, ...row]),
        filename: `confusion_matrix_${suffix}`,
      }
    }

    if (activeTab.value === 'perClass' && perClassRows.value.length > 0) {
      return {
        headers: ['類別', 'Precision', 'Recall', 'F1', '樣本數'],
        rows: perClassRows.value.map(row => [
          row.label,
          row.precision.toFixed(3),
          row.recall.toFixed(3),
          row.f1.toFixed(3),
          row.support,
        ]),
        filename: `per_class_metrics_${suffix}`,
      }
    }

    if (activeTab.value === 'roc' && visibleModelNames.value.length > 0) {
      const rows: Array<[string, string, string]> = []
      for (const modelName of visibleModelNames.value) {
        const curve = groupedResults.value
          .find(g => g.model_name === modelName)
          ?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve
        if (!curve) continue
        curve.roc.fpr.forEach((fpr, i) => {
          rows.push([modelName, fpr.toFixed(4), (curve.roc.tpr[i] ?? 0).toFixed(4)])
        })
      }
      if (rows.length === 0) return null
      return { headers: ['模型', 'FPR', 'TPR'], rows, filename: `roc_curve_${selectedFold.value}` }
    }

    if (activeTab.value === 'pr' && visibleModelNames.value.length > 0) {
      const rows: Array<[string, string, string]> = []
      for (const modelName of visibleModelNames.value) {
        const curve = groupedResults.value
          .find(g => g.model_name === modelName)
          ?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve
        if (!curve) continue
        curve.pr.recall.forEach((recall, i) => {
          rows.push([modelName, recall.toFixed(4), (curve.pr.precision[i] ?? 0).toFixed(4)])
        })
      }
      if (rows.length === 0) return null
      return { headers: ['模型', 'Recall', 'Precision'], rows, filename: `pr_curve_${selectedFold.value}` }
    }

    if (activeTab.value === 'calibration' && currentCalibrationCurve.value) {
      const curve = currentCalibrationCurve.value
      return {
        headers: ['模型', '預測機率', '實際正類比例'],
        rows: curve.probPred.map((p, i) => [
          selectedModel.value, p.toFixed(4), (curve.probTrue[i] ?? 0).toFixed(4),
        ]),
        filename: `calibration_curve_${suffix}`,
      }
    }

    return null
  })
```

- [ ] **Step 2: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 既有的 53 個 `@tiptap/*` 錯誤不變，`npm run type-check 2>&1 | grep -i "ConfusionMatrixPanel"` 沒有輸出

- [ ] **Step 3: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add CSV/Excel export for ROC, PR, and calibration curve data"
```

---

## 完成後的人工驗證

三個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證：

1. Test & Score／Feature Importance 節點：確認匯出按鈕點下去出現選單、Excel 跟 CSV 都能正常下載，內容正確
2. Compute CI 節點：切到「單一 Fold」匯出一次、切到「跨 Fold 摘要」再匯出一次，確認兩次匯出的內容分別對應畫面上顯示的資料，不會兩次都是同一份
3. Classification Evaluation 節點：切到 ROC 分頁，關掉圖例上某個模型，匯出 CSV，確認被關掉的模型沒有出現在匯出檔案裡；PR、校準曲線分頁重複驗證
4. CSV 檔案用 Excel 開啟，確認中文欄位/模型名稱沒有亂碼
5. 匯出的 CSV 用文字編輯器打開，確認欄位用逗號分隔、格式正確可以被其他分析工具讀取
6. 點擊匯出按鈕彈出選單後，點選單外面的地方，確認選單會收起來
