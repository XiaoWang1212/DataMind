# 結果面板 CSV 匯出 Design Spec

## 背景

老師希望 Test & Score、Feature Importance、Classification Evaluation（混淆矩陣節點）、Compute CI 這四個結果節點都能把資料匯出成 CSV，方便帶進統計/分析工具。

查過現況後發現落差比預期小：
- Test & Score、Feature Importance、Compute CI 三個節點**已經有**匯出按鈕（`ResultTableActions.vue`），但匯出的是 **.xlsx（Excel）**，沒有 CSV
- Classification Evaluation（`ConfusionMatrixPanel.vue`）也已經有這顆按鈕，但只涵蓋「混淆矩陣」「各類別指標」兩個表格分頁；ROC、PR、校準曲線三個分頁是圖表，目前完全沒有匯出
- 附帶發現一個真的 bug：Compute CI 節點切到「跨 Fold 摘要」檢視時，匯出按鈕匯出的還是單一 Fold 的舊資料，不是摘要資料

這次要做的事：
1. 幫既有的匯出按鈕加上 CSV 選項（跟 Excel 並存，使用者自己選）
2. 補上 ROC/PR/校準曲線三個分頁的匯出
3. 修掉 Compute CI 摘要檢視的匯出 bug

## 範圍

- **不**動後端——所有資料前端都已經有，純前端改動
- **不**新增通用 Modal/Dropdown 元件——`ResultTableActions.vue` 自己內建一個簡單的選單，不重用 `CustomSelect.vue`（那個是給表單選值用的，有一整套鍵盤導覽/viewport 定位邏輯，這裡不需要）
- Test & Score、Feature Importance 兩個節點完全不用改——它們已經在用 `ResultTableActions.vue`，元件升級後自動繼承 CSV 選項

## 元件改動

### 1. `frontend/src/utils/tableExport.ts`——新增 `exportTableToCsv()`

在既有的 `exportTableToExcel()` 之後新增：
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
  const blob = new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' })
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
（`appendChild`/`remove()` + 直接 `revokeObjectURL` 不用延遲——這裡沒有前一次那個 highlight.js 動態 `<style>` 注入的特殊情境，跟既有 `exportTableToExcel()` 的下載寫法一致即可）

### 2. `frontend/src/components/common/ResultTableActions.vue`——匯出按鈕改成選單

現有的匯出按鈕（第 12-19 行）點下去直接呼叫 `exportTableToExcel()`。改成點下去彈出一個小選單，選單本身用全站既有的 `glass-menu` 毛玻璃樣式（`frontend/src/styles/glass.css` 已定義，`CustomSelect.vue` 也是用同一個 class）：

```html
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
```
新增的 CSS（其餘既有樣式不動）：
```css
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
```

### 3. `ComputeCiPanel.vue`——修「跨 Fold 摘要」匯出到舊資料的 bug

現有的（第 213-219 行附近）：
```typescript
const exportHeaders = ['指標', 'CI Lower', 'Value', 'CI Upper']

const exportRows = computed(() =>
  currentSplitMetrics.value.map(m => [m.metric, fmt(m.ci_lower), fmt(m.value), fmt(m.ci_upper)]),
)

const exportFilename = computed(() => `bootstrap_ci_${selectedModel.value}_${selectedFold.value}`)
```
改成依 `viewMode` 切換，跟畫面上已經在用的 `displayRows`（第 306-327 行）同一個判斷邏輯：
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
`<ResultTableActions>` 的 `v-if`（第 12 行附近，目前是 `v-if="currentSplitMetrics.length > 0"`）也要跟著改成依模式判斷：
```html
v-if="viewMode === 'fold' ? currentSplitMetrics.length > 0 : crossFoldSummary.length > 0"
```

### 4. `ConfusionMatrixPanel.vue`——ROC/PR/校準曲線補上匯出

好消息：這個元件已經有一個共用的 `exportableTable` computed（第 591-618 行）跟一個共用的 `<ResultTableActions v-if="exportableTable">`（第 33-39 行，放在分頁列上，不分頁面各自一顆）。混淆矩陣、逐類別指標兩個分頁的匯出就是靠這個 computed 依 `activeTab` 分支出對應的表格資料。這次**不用新增元件或新的 template 位置**，只要在同一個 computed 裡，`return null`（第 617 行）之前，補上 `roc`/`pr`/`calibration` 三個分支：

```typescript
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
```
（`suffix`、`groupedResults`、`visibleModelNames`、`currentCalibrationCurve`、`selectedModel`、`selectedFold` 都是這個檔案裡已經存在的既有變數，直接沿用）

ROC/PR 因為是多模型疊圖，匯出的是「目前圖例顯示中的每個模型」各自完整的曲線座標點（不是給 AI 解讀用的取樣 5 點），攤平成一張表、用「模型」欄位分開每一列屬於哪個模型。校準曲線分頁本身還是單模型檢視，維持單一模型的座標點表格。

## 邊界情況

- ROC/PR 分頁圖例全部關掉：`visibleModelNames.value.length > 0` 為 false，`exportableTable` 回傳 `null`，匯出按鈕跟著消失（跟現在「沒有資料就不顯示按鈕」的既有慣例一致）
- 某個可見模型在目前 fold 沒有曲線資料：迴圈裡 `if (!curve) continue` 跳過，不會讓整個匯出失敗，只是那個模型不會出現在表格裡
- CSV 儲存格內容包含逗號、雙引號或換行：`toCsvCell()` 用雙引號包住並跳脫內部雙引號，符合 CSV 標準格式
- 表格內容含中文字（模型名稱、指標中文標籤等）：CSV 開頭加 UTF-8 BOM，Excel 開啟時才不會誤判編碼變亂碼
- Compute CI 摘要檢視但目前選中的模型完全沒有任何 fold 資料：`crossFoldSummary.length > 0` 為 false，按鈕不顯示（不會嘗試匯出空表格）

## 測試

前端沒有自動化測試框架，比照這個 session 其他前端改動的慣例：
1. `npm run type-check`（在 `datamind-frontend` container 內跑）
2. 人工瀏覽器驗證：
   - Test & Score／Feature Importance 節點：確認匯出按鈕點下去出現選單、Excel 跟 CSV 都能正常下載，內容正確
   - Compute CI 節點：切到「單一 Fold」匯出一次、切到「跨 Fold 摘要」再匯出一次，確認兩次匯出的內容分別對應畫面上顯示的資料，不會兩次都是同一份
   - Classification Evaluation 節點：切到 ROC 分頁，關掉圖例上某個模型，匯出 CSV，確認被關掉的模型沒有出現在匯出檔案裡；PR、校準曲線分頁重複驗證
   - CSV 檔案用 Excel 開啟，確認中文欄位/模型名稱沒有亂碼
   - 匯出的 CSV 用文字編輯器打開，確認欄位用逗號分隔、格式正確可以被其他分析工具讀取
