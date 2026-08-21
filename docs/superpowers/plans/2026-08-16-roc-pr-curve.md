# ROC / PR 曲線 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有的 `ConfusionMatrixPanel.vue` 加上分頁，顯示每個 (model × fold) 結果的 ROC 曲線與 PR 曲線；後端新增計算函式並接進 workflow 執行結果。

**Architecture:** 後端在 `test_score_service.py` 新增 `build_roc_pr_curve()`，複用既有的二元分類轉換 helper（`_get_score_vector`/`_infer_positive_label`/`_to_binary_array`），回傳 `{pos_label, roc: {fpr, tpr}, pr: {precision, recall}}` 或 `None`（多分類/無機率輸出時）。`workflow_service.py` 在組每筆結果時呼叫它，寫進 `roc_pr_curve` 欄位。前端擴充 `ConfusionMatrixPanel.vue`：新增分頁切換 UI（混淆矩陣／ROC 曲線／PR 曲線），共用既有的模型+fold 雙下拉狀態，新增手刻 SVG 折線圖渲染 ROC/PR 曲線。畫布上 `confusionMatrix` 節點的顯示名稱同步更新為「Classification Evaluation」。

**Tech Stack:** Python (scikit-learn `roc_curve`/`precision_recall_curve`), Vue 3 `<script setup>` + TypeScript，手刻 inline SVG（無圖表函式庫）。

## Global Constraints

- 只支援二元分類；多分類或模型無機率輸出時，`roc_pr_curve` 為 `None`，前端顯示空狀態文字，不報錯
- 不新增畫布節點，不修改 `useWorkflowNodes.ts`/`useWorkflowImport.ts`（節點 id `confusionMatrix` 不變，這些檔案的邏輯只依 id 判斷）
- 不引入前端圖表函式庫，比照 `FeatureImportancePanel.vue`/`ConfusionMatrixPanel.vue` 現有的手刻 SVG/HTML 慣例
- 節點 `label` 改為 `"Classification\nEvaluation"`，`description` 改為 `"顯示混淆矩陣與 ROC/PR 曲線"`；`icon`（`mdi-grid`）與 `config`（`{ normalize: "none" }`）維持不變

---

### Task 1: 後端計算 ROC/PR 曲線並接進 workflow 結果

**Files:**
- Modify: `backend/services/workflow/test_score_service.py`
- Modify: `backend/services/workflow/workflow_service.py`

**Interfaces:**
- Produces: `build_roc_pr_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]`，回傳形狀 `{"pos_label": str, "roc": {"fpr": List[float], "tpr": List[float]}, "pr": {"precision": List[float], "recall": List[float]}}`，或 `None`

- [ ] **Step 1: 在 `test_score_service.py` 加 import**

在檔案開頭的 `from sklearn.metrics import (...)` 區塊加入 `precision_recall_curve` 與 `roc_curve`（沿用既有的字母排序慣例）：

```python
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
```

- [ ] **Step 2: 新增 `build_roc_pr_curve()` 函式**

加在 `test_score_service.py` 的 `evaluate_metrics()` 函式定義之前（該函式所在區塊標題是 `# Public evaluation function`，把新函式加在同一個區塊、`evaluate_metrics` 上方即可）：

```python
def build_roc_pr_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]:
    """算 ROC / PR 曲線座標點，只支援二元分類（y_score 為 None 或多分類時回傳 None）"""
    if y_score is None:
        return None
    score_vec = _get_score_vector(y_score)
    if score_vec is None:
        return None
    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        return None

    pos_label = _infer_positive_label(y_true)
    binary = _to_binary_array(y_true, pos_label)

    fpr, tpr, _ = roc_curve(binary, score_vec)
    precision, recall, _ = precision_recall_curve(binary, score_vec)

    return {
        "pos_label": str(pos_label),
        "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
        "pr": {"precision": precision.tolist(), "recall": recall.tolist()},
    }
```

`_get_score_vector`、`_infer_positive_label`、`_to_binary_array` 都已經是這個檔案裡的既有函式，簽名分別是：
- `_get_score_vector(y_score: Any, pos_label: Optional[Any] = None) -> Optional[np.ndarray]`
- `_infer_positive_label(y_true: pd.Series, labels: Optional[List[Any]] = None) -> Optional[Any]`
- `_to_binary_array(y_true: pd.Series, pos_label: Optional[Any] = None) -> np.ndarray`

不用傳 `labels`/`pos_label` 引數，用預設值走既有的自動推斷邏輯即可（跟 `_compute_metric()` 裡 `auc`/`auprc` 分支在沒有指定 `pos_label` 時的行為一致）。

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/test_score_service.py datamind-backend:/tmp/test_score_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/test_score_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 在 `workflow_service.py` 加 import**

第 27 行現在是：
```python
from .test_score_service import evaluate_metrics, generate_score_variants
```
改成：
```python
from .test_score_service import build_roc_pr_curve, evaluate_metrics, generate_score_variants
```

- [ ] **Step 5: 非串流版 `execute_workflow` 接上 `roc_pr_curve`**

第 486 行現在是：
```python
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
```
改成：
```python
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                            "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```

- [ ] **Step 6: 串流版 `execute_workflow_stream` 接上 `roc_pr_curve`**

第 688 行現在是：
```python
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
```
改成：
```python
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                        "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```

- [ ] **Step 7: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/workflow_service.py datamind-backend:/tmp/workflow_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/workflow_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 8: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/test_score_service.py backend/services/workflow/workflow_service.py
git commit -m "feat: compute and return ROC/PR curve per workflow result"
```

---

### Task 2: 前端 `ConfusionMatrixPanel.vue` 加分頁顯示 ROC/PR 曲線

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: `workflowResult.results[].roc_pr_curve`，形狀 `{pos_label: string, roc: {fpr: number[], tpr: number[]}, pr: {precision: number[], recall: number[]}} | null | undefined`（Task 1 產生）
- Consumes（既有，不變）: `groupedResults`/`currentModel`/`selectedModel`/`selectedFold`/`modelOptions`/`foldOptions` 這幾個既有的 computed/ref，本任務會擴充它們讀取的資料形狀，但變數名稱不變

當前檔案完整內容如下（本任務要在這個基礎上修改）：

```vue
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

    <div v-if="currentMatrix" class="cm-table-wrap">
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

    <div v-else-if="groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>

    <div v-else class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'

  interface ConfusionMatrixData {
    labels: string[]
    matrix: number[][]
  }

  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
    }>
  }

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
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

  const rawResults = computed<Array<Record<string, unknown>>>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []
    return results as Array<Record<string, unknown>>
  })

  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value
      .map(result => {
        const model_name = String(result.model_name ?? 'Unknown model')
        const split_name = String(result.split_name ?? 'Unknown split')
        const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
        return { model_name, split_name, confusion_matrix }
      })
      .filter(item => item.confusion_matrix !== null),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of confusionResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
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
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .cm-select {
    width: 160px;
  }

  .cm-table-wrap {
    overflow-x: auto;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
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
    font-weight: 600;
    color: var(--color-secondary);
    white-space: nowrap;
    text-align: left;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-header--row {
    border-bottom: none;
    border-right: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-cell {
    padding: 11px 14px;
    text-align: center;
    color: var(--color-ink);
    font-variant-numeric: tabular-nums;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .cm-cell--diagonal {
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    font-weight: 700;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
```

- [ ] **Step 1: 加分頁狀態 + 擴充資料型別/parsing**

在 `<script setup>` 裡，`interface ConfusionMatrixData { ... }` 之後、`interface ResultItem { ... }` 之前，新增：

```typescript
  interface RocPrCurveData {
    posLabel: string
    roc: { fpr: number[], tpr: number[] }
    pr: { precision: number[], recall: number[] }
  }
```

`interface ResultItem` 改成：

```typescript
  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
  }
```

`interface GroupedResult` 的 `splits` 陣列元素型別改成：

```typescript
  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
      roc_pr_curve: RocPrCurveData | null
    }>
  }
```

在 `parseConfusionMatrix()` 函式之後新增 `parseRocPrCurve()`：

```typescript
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
```

`confusionResults` computed 裡的 `.map()` 改成同時解析兩個欄位、並且不再用 `confusion_matrix` 過濾掉整筆結果（因為現在一筆結果可能有 `confusion_matrix` 沒有 `roc_pr_curve`，或反過來，兩者是獨立的空狀態）：

```typescript
  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value.map(result => {
      const model_name = String(result.model_name ?? 'Unknown model')
      const split_name = String(result.split_name ?? 'Unknown split')
      const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
      const roc_pr_curve = parseRocPrCurve(result.roc_pr_curve)
      return { model_name, split_name, confusion_matrix, roc_pr_curve }
    }).filter(item => item.confusion_matrix !== null || item.roc_pr_curve !== null),
  )
```

`groupedResults` computed 裡建立 `entry` 的地方也要多帶一個欄位：

```typescript
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
      }
```

- [ ] **Step 2: 加分頁狀態與 currentRocPrCurve computed**

在 `const currentMatrix = computed(...)` 之後新增：

```typescript
  type TabKey = 'matrix' | 'roc' | 'pr'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
  ]

  const currentRocPrCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.roc_pr_curve ?? null,
  )
```

- [ ] **Step 3: 加 SVG 折線圖產生邏輯**

在 `currentRocPrCurve` computed 之後新增座標轉換與 path 產生函式（SVG viewBox 固定 `0 0 100 100`，y 軸從上到下所以要用 `100 - value` 翻轉）：

```typescript
  const CHART_SIZE = 100
  const CHART_PADDING = 4

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
```

- [ ] **Step 4: Template — 加分頁切換 UI**

在 `<div v-if="groupedResults.length > 0" class="cm-controls">` 那個區塊（模型/fold 雙下拉）**之後**，新增分頁切換列：

```html
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
```

- [ ] **Step 5: Template — 混淆矩陣表格加上 `v-if="activeTab === 'matrix'"`**

現有的：
```html
    <div v-if="currentMatrix" class="cm-table-wrap">
```
改成：
```html
    <div v-if="activeTab === 'matrix' && currentMatrix" class="cm-table-wrap">
```

現有的：
```html
    <div v-else-if="groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>
```
改成（只在混淆矩陣分頁、且沒有資料時顯示這句）：
```html
    <div v-else-if="activeTab === 'matrix' && groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>
```

- [ ] **Step 6: Template — 加 ROC/PR 曲線區塊**

緊接在上一步那個 `summary-empty` 區塊之後、原本的 `<div v-else class="summary-empty">`（尚未有結果的空狀態）**之前**，插入：

```html
    <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
      <svg class="cm-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line class="cm-chart-diagonal" x1="4" y1="96" x2="96" y2="4" />
        <path class="cm-chart-line" :d="rocPath" fill="none" />
      </svg>
      <div class="cm-chart-axis-x">FPR (0 – 1)</div>
      <div class="cm-chart-axis-y">TPR (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'roc' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出）。
    </div>

    <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
      <svg class="cm-chart" viewBox="0 0 100 100" preserveAspectRatio="none">
        <path class="cm-chart-line" :d="prPath" fill="none" />
      </svg>
      <div class="cm-chart-axis-x">Recall (0 – 1)</div>
      <div class="cm-chart-axis-y">Precision (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'pr' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出）。
    </div>
```

- [ ] **Step 7: 加對應樣式**

在 `.summary-empty { ... }` 規則之前（style block 結尾附近）新增：

```css
  .cm-tabs {
    display: flex;
    gap: 6px;
  }

  .cm-tab {
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    background: transparent;
    color: var(--color-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .cm-tab--active {
    background: var(--color-accent);
    border-color: var(--color-accent);
    color: #fff;
  }

  .cm-chart-wrap {
    position: relative;
    padding: 12px 16px 28px 34px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .cm-chart {
    width: 100%;
    height: 260px;
    display: block;
  }

  .cm-chart-diagonal {
    stroke: rgba(148, 163, 184, 0.5);
    stroke-width: 0.6;
    stroke-dasharray: 2 2;
  }

  .cm-chart-line {
    stroke: var(--color-accent);
    stroke-width: 1.4;
    vector-effect: non-scaling-stroke;
  }

  .cm-chart-axis-x {
    position: absolute;
    left: 50%;
    bottom: 6px;
    transform: translateX(-50%);
    font-size: 11px;
    color: var(--color-secondary);
  }

  .cm-chart-axis-y {
    position: absolute;
    left: 6px;
    top: 50%;
    transform: translateY(-50%) rotate(-90deg);
    transform-origin: left center;
    font-size: 11px;
    color: var(--color-secondary);
    white-space: nowrap;
  }
```

- [ ] **Step 8: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 沒有新增的 `error TS` 行——這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件，跟本次改動無關），確認錯誤數量沒有增加即可（`npm run type-check 2>&1 | grep -c "error TS"` 應該還是 50，或用 `grep -i "ConfusionMatrixPanel"` 確認輸出裡沒有這個檔案的錯誤）。

- [ ] **Step 9: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add ROC/PR curve tabs to ConfusionMatrixPanel"
```

---

### Task 3: 更新畫布節點顯示名稱

**Files:**
- Modify: `frontend/src/constants/workflowData.ts`

**Interfaces:**
- Consumes: 無新增介面，純資料調整
- Produces: 無新增介面

- [ ] **Step 1: 修改 `confusionMatrix` 節點的 `label`/`description`**

`INITIAL_NODES` 陣列裡 id 為 `"confusionMatrix"` 的項目，現在是：

```typescript
  {
    id: "confusionMatrix",
    type: "iconNode",
    position: { x: 660, y: 380 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-grid",
      label: "Confusion\nMatrix",
      colorClass: "node-pending",
      description: "輸出混淆矩陣",
      fields: [],
      config: { normalize: "none" },
    },
  },
```

把 `label` 跟 `description` 改成：

```typescript
      label: "Classification\nEvaluation",
      description: "顯示混淆矩陣與 ROC/PR 曲線",
```

`id`、`icon`、`position`、`config` 不動。

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟 Task 2 結束時一樣（沒有新增）

- [ ] **Step 3: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/constants/workflowData.ts
git commit -m "chore: rename confusionMatrix node to Classification Evaluation"
```

---

## 完成後的人工驗證

三個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 執行一次 workflow（二元分類資料集），點畫布上「Classification Evaluation」節點（原「Confusion Matrix」節點，位置不變）
2. 確認三個分頁都能正常切換：混淆矩陣 / ROC 曲線 / PR 曲線
3. 切換模型 + fold 下拉時，三個分頁的內容都跟著變
4. ROC 曲線有畫出對角線參考線；PR 曲線座標軸範圍正確（0–1）
5. 用一個多分類資料集跑一次，確認 ROC/PR 分頁顯示「此模型或此類別數不支援 ROC/PR 曲線」的空狀態文字，混淆矩陣分頁不受影響、正常顯示 NxN 表格
