# Calibration Curve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有的 `ConfusionMatrixPanel.vue` 加第四個分頁，顯示每個 (model × fold) 結果的校準曲線（reliability diagram）；後端新增計算函式並接進 workflow 執行結果。

**Architecture:** 後端在 `test_score_service.py` 新增 `build_calibration_curve()`，緊接在剛完成的 `build_roc_pr_curve()` 之後，複用同一套二元分類轉換 helper（`_get_score_vector`/`_infer_positive_label`/`_to_binary_array`）與同一套防護結構（guard 檢查之後，所有邏輯包在一個 `try/except Exception: return None` 裡）。`workflow_service.py` 在組每筆結果時呼叫它，寫進 `calibration_curve` 欄位。前端擴充 `ConfusionMatrixPanel.vue`：`TABS`/`TabKey` 加第四項，新增資料型別與 parsing、新增第四個分頁的 SVG 圖表——比照既有折線圖的畫法，但每個資料點額外疊一個 `<circle>` 圓點（reliability diagram 是離散點連線，不是平滑曲線）。

**Tech Stack:** Python (`sklearn.calibration.calibration_curve`)，Vue 3 `<script setup>` + TypeScript，延續既有的手刻 inline SVG（無圖表函式庫）。

## Global Constraints

- 只支援二元分類；多分類或模型無機率輸出時，`calibration_curve` 為 `None`，前端顯示空狀態文字，不報錯
- 不開放 `n_bins`/`strategy` 給使用者調整，固定用 `n_bins=10, strategy='uniform'`（sklearn 預設值）
- 後端函式內部：guard 檢查（`y_score is None`／`score_vec is None`／`len(unique_labels) != 2`）之後的所有邏輯，必須整段包在同一個 `try/except Exception: return None` 裡——這是 ROC/PR 曲線那次最終審查來回兩輪才修好的教訓，`_to_binary_array` 本身可能因為數值型 target 混雜 NaN 而拋出例外，guard 檢查沒辦法擋住這個情況
- 不新增畫布節點，不修改節點 id/label/description（`confusionMatrix` 節點這輪不再變動，上一輪已經改成 `Classification Evaluation`）
- 回傳的浮點陣列一律四捨五入到小數點後 6 位再放進回傳的 dict（控制 payload 大小，比照 `build_roc_pr_curve` 的既有寫法）

---

### Task 1: 後端計算校準曲線並接進 workflow 結果

**Files:**
- Modify: `backend/services/workflow/test_score_service.py`
- Modify: `backend/services/workflow/workflow_service.py`

**Interfaces:**
- Produces: `build_calibration_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]`，回傳形狀 `{"pos_label": str, "prob_true": List[float], "prob_pred": List[float]}`，或 `None`

- [ ] **Step 1: 在 `test_score_service.py` 加 import**

檔案開頭現有：
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
from sklearn.preprocessing import LabelBinarizer
```

在 `from sklearn.metrics import (...)` 這個 import 區塊之後、`from sklearn.preprocessing import LabelBinarizer` 之前，新增一行：

```python
from sklearn.calibration import calibration_curve
```

- [ ] **Step 2: 新增 `build_calibration_curve()` 函式**

檔案裡現有的 `build_roc_pr_curve()` 函式（在 `# Public evaluation function` 區塊、`evaluate_metrics()` 之前）目前是：

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

    try:
        pos_label = _infer_positive_label(y_true)
        binary = _to_binary_array(y_true, pos_label)
        # _to_binary_array 對數值 dtype 是原值透傳（不處理 pos_label），這裡補正成真正的 0/1
        if not np.array_equal(np.unique(binary), np.array([0, 1])):
            binary = (y_true == pos_label).to_numpy(dtype=int)

        fpr, tpr, _ = roc_curve(binary, score_vec)
        precision, recall, _ = precision_recall_curve(binary, score_vec, drop_intermediate=True)
    except Exception:
        return None

    return {
        "pos_label": str(pos_label),
        "roc": {"fpr": [round(v, 6) for v in fpr.tolist()], "tpr": [round(v, 6) for v in tpr.tolist()]},
        "pr": {"precision": [round(v, 6) for v in precision.tolist()], "recall": [round(v, 6) for v in recall.tolist()]},
    }
```

在這個函式**之後**（`evaluate_metrics()` 之前）新增：

```python
def build_calibration_curve(y_true: pd.Series, y_score: Any) -> Optional[Dict[str, Any]]:
    """算校準曲線（reliability diagram），只支援二元分類。任何失敗都回傳 None，絕不讓例外往外傳。"""
    if y_score is None:
        return None
    score_vec = _get_score_vector(y_score)
    if score_vec is None:
        return None
    unique_labels = pd.unique(y_true.dropna())
    if len(unique_labels) != 2:
        return None

    try:
        pos_label = _infer_positive_label(y_true)
        binary = _to_binary_array(y_true, pos_label)
        # _to_binary_array 對數值 dtype 是原值透傳（不處理 pos_label），這裡補正成真正的 0/1
        if not np.array_equal(np.unique(binary), np.array([0, 1])):
            binary = (y_true == pos_label).to_numpy(dtype=int)

        prob_true, prob_pred = calibration_curve(binary, score_vec, n_bins=10, strategy="uniform")
    except Exception:
        return None

    return {
        "pos_label": str(pos_label),
        "prob_true": [round(v, 6) for v in prob_true.tolist()],
        "prob_pred": [round(v, 6) for v in prob_pred.tolist()],
    }
```

**注意**：`try` 區塊必須從 `pos_label = _infer_positive_label(y_true)` 這一行就開始（不能只包住 `calibration_curve(...)` 呼叫本身）——`_to_binary_array` 內部對數值型 dtype 是直接 `.astype(int)` 透傳，遇到含 NaN 的數值型 target 會拋出 `pandas.errors.IntCastingNaNError`，如果 try 區塊只包住最後一行，這個例外會直接往外傳、讓整趟 workflow 崩潰。這正是 `build_roc_pr_curve` 在上一輪最終審查中被抓到、修了兩輪才解決的問題，這次直接照正確寫法做，不要重蹈覆轍。

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/test_score_service.py datamind-backend:/tmp/test_score_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/test_score_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 用 repro script 驗證三種情況**

Run（在 `datamind-backend` 容器內，用 inline python 腳本）：
```bash
docker exec datamind-backend .venv/bin/python -c "
import sys
sys.path.insert(0, '/app')
import numpy as np
import pandas as pd
from services.workflow.test_score_service import build_calibration_curve

# Case 1: 數值型 {1,2}，無 NaN，正常情況
rng = np.random.RandomState(0)
y_true = pd.Series([1, 2] * 50)
y_score = {'proba': rng.rand(100, 2), 'classes': [1, 2]}
result = build_calibration_curve(y_true, y_score)
assert result is not None, 'Case 1 failed: expected dict, got None'
assert 'prob_true' in result and 'prob_pred' in result
print('Case 1 (numeric {1,2}, no NaN): OK', len(result['prob_true']), 'bins')

# Case 2: 數值型 target 混雜 NaN，不該拋例外，應回傳 None 或有效 dict
y_true_nan = pd.Series([1.0, 2.0, np.nan] * 34)
y_score_nan = {'proba': rng.rand(102, 2), 'classes': [1, 2]}
result_nan = build_calibration_curve(y_true_nan, y_score_nan)
print('Case 2 (numeric with NaN): no exception raised, result =', 'dict' if result_nan else 'None')

# Case 3: 多分類，應回傳 None
y_true_multi = pd.Series([0, 1, 2] * 34)
y_score_multi = {'proba': rng.rand(102, 3), 'classes': [0, 1, 2]}
result_multi = build_calibration_curve(y_true_multi, y_score_multi)
assert result_multi is None, 'Case 3 failed: expected None for multiclass'
print('Case 3 (multiclass): OK, returned None')

print('ALL CASES PASSED')
"
```
Expected: 三個 case 都印出 OK，最後印出 `ALL CASES PASSED`，過程中沒有任何 Python traceback

- [ ] **Step 5: 在 `workflow_service.py` 加 import**

現有的 import 行：
```python
from .test_score_service import build_roc_pr_curve, evaluate_metrics, generate_score_variants
```
改成：
```python
from .test_score_service import (
    build_calibration_curve,
    build_roc_pr_curve,
    evaluate_metrics,
    generate_score_variants,
)
```

- [ ] **Step 6: 非串流版 `execute_workflow` 接上 `calibration_curve`**

第 487 行現有：
```python
                            "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```
改成：
```python
                            "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
                            "calibration_curve": build_calibration_curve(y_test, y_score),
```

- [ ] **Step 7: 串流版 `execute_workflow_stream` 接上 `calibration_curve`**

第 690 行現有：
```python
                        "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```
改成：
```python
                        "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
                        "calibration_curve": build_calibration_curve(y_test, y_score),
```

- [ ] **Step 8: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/workflow_service.py datamind-backend:/tmp/workflow_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/workflow_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 9: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/test_score_service.py backend/services/workflow/workflow_service.py
git commit -m "feat: compute and return calibration curve per workflow result"
```

---

### Task 2: 前端 `ConfusionMatrixPanel.vue` 加第四個分頁顯示校準曲線

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: `workflowResult.results[].calibration_curve`，形狀 `{pos_label: string, prob_true: number[], prob_pred: number[]} | null | undefined`（Task 1 產生）
- Consumes（既有，不變）: `groupedResults`/`currentModel`/`selectedModel`/`selectedFold`/`toChartX`/`toChartY`/`buildLinePath` 這幾個既有的 computed/函式，本任務擴充它們處理的資料形狀，變數名稱不變

- [ ] **Step 1: 加資料型別與 parsing**

在 `interface RocPrCurveData { ... }` 之後新增：

```typescript
  interface CalibrationCurveData {
    posLabel: string
    probTrue: number[]
    probPred: number[]
  }
```

`interface ResultItem` 現有：
```typescript
  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
  }
```
改成：
```typescript
  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
    calibration_curve: CalibrationCurveData | null
  }
```

`interface GroupedResult` 的 `splits` 元素型別現有：
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
改成：
```typescript
  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      confusion_matrix: ConfusionMatrixData | null
      roc_pr_curve: RocPrCurveData | null
      calibration_curve: CalibrationCurveData | null
    }>
  }
```

在 `parseRocPrCurve()` 函式之後新增 `parseCalibrationCurve()`：

```typescript
  function parseCalibrationCurve (value: unknown): CalibrationCurveData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const posLabel = obj.pos_label
    const probTrue = obj.prob_true
    const probPred = obj.prob_pred
    if (typeof posLabel !== 'string') return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(probTrue) || !isNumberArray(probPred)) return null

    return { posLabel, probTrue, probPred }
  }
```

- [ ] **Step 2: 擴充 `confusionResults`/`groupedResults` 讀取新欄位**

`confusionResults` computed 現有：
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
改成：
```typescript
  const confusionResults = computed<ResultItem[]>(() =>
    rawResults.value.map(result => {
      const model_name = String(result.model_name ?? 'Unknown model')
      const split_name = String(result.split_name ?? 'Unknown split')
      const confusion_matrix = parseConfusionMatrix(result.confusion_matrix)
      const roc_pr_curve = parseRocPrCurve(result.roc_pr_curve)
      const calibration_curve = parseCalibrationCurve(result.calibration_curve)
      return { model_name, split_name, confusion_matrix, roc_pr_curve, calibration_curve }
    }).filter(item =>
      item.confusion_matrix !== null || item.roc_pr_curve !== null || item.calibration_curve !== null,
    ),
  )
```

`groupedResults` computed 裡建立 `entry` 的地方現有：
```typescript
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
      }
```
改成：
```typescript
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
        calibration_curve: result.calibration_curve,
      }
```

- [ ] **Step 3: 加分頁項、`currentCalibrationCurve` computed、圖表資料函式**

現有的 `TabKey`/`TABS`：
```typescript
  type TabKey = 'matrix' | 'roc' | 'pr'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
  ]
```
改成：
```typescript
  type TabKey = 'matrix' | 'roc' | 'pr' | 'calibration'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
    { key: 'calibration', label: '校準曲線' },
  ]
```

在 `const currentRocPrCurve = computed(...)` 之後新增：

```typescript
  const currentCalibrationCurve = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.calibration_curve ?? null,
  )
```

在 `const prPath = computed(...)` 之後新增（連接線路徑，複用既有的 `buildLinePath`；再加一個回傳每個點座標的 computed，供 Step 4 畫 `<circle>` 用）：

```typescript
  const calibrationPath = computed(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return ''
    return buildLinePath(curve.probPred, curve.probTrue)
  })

  interface ChartPoint {
    x: number
    y: number
  }

  const calibrationPoints = computed<ChartPoint[]>(() => {
    const curve = currentCalibrationCurve.value
    if (!curve) return []
    return curve.probPred.map((x, i) => ({
      x: toChartX(x),
      y: toChartY(curve.probTrue[i]!),
    }))
  })
```

- [ ] **Step 4: Template — 加校準曲線分頁區塊**

現有的 PR 曲線區塊結尾是：
```html
    <div v-else-if="activeTab === 'pr' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
    </div>

    <div v-if="groupedResults.length === 0" class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
```

在 PR 分頁的空狀態區塊**之後**、「尚未有混淆矩陣結果」區塊**之前**，插入校準曲線分頁區塊：

```html
    <div v-if="activeTab === 'calibration' && currentCalibrationCurve" class="cm-chart-wrap">
      <div class="cm-chart-label">正類：{{ currentCalibrationCurve?.posLabel }}</div>
      <svg class="cm-chart" viewBox="0 0 100 100">
        <line class="cm-chart-diagonal" x1="4" y1="96" x2="96" y2="4" />
        <path class="cm-chart-line" :d="calibrationPath" fill="none" />
        <circle
          v-for="(point, index) in calibrationPoints"
          :key="`cal-point-${index}`"
          class="cm-chart-point"
          :cx="point.x"
          :cy="point.y"
          r="1.5"
        />
        <text class="cm-chart-tick" x="4" y="100">0</text>
        <text class="cm-chart-tick" x="50" y="100" text-anchor="middle">0.5</text>
        <text class="cm-chart-tick" x="96" y="100" text-anchor="end">1</text>
        <text class="cm-chart-tick" x="0" y="96">0</text>
        <text class="cm-chart-tick" x="0" y="50">0.5</text>
        <text class="cm-chart-tick" x="0" y="4">1</text>
      </svg>
      <div class="cm-chart-axis-x">平均預測機率 (0 – 1)</div>
      <div class="cm-chart-axis-y">實際正類比例 (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'calibration' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
    </div>
```

**注意**：這個新區塊必須維持獨立的 `v-if`（不是 `v-else-if`）開頭，就像 `roc`/`pr` 分頁區塊之間彼此獨立一樣——每個分頁自成一組 `v-if`/`v-else-if` pair，不要跟前一組或後一組串起來，否則會重蹈 ROC/PR 曲線那次 plan 裡發生過的 `v-if`/`v-else` 串接 bug。維持它在「尚未有混淆矩陣結果」（`groupedResults.length === 0`）那個獨立 `v-if` 區塊**之前**插入，不要插到它後面。

- [ ] **Step 5: 加對應樣式**

在 `.cm-chart-line { ... }` 規則之後新增：

```css
  .cm-chart-point {
    fill: var(--color-accent);
    stroke: var(--color-surface);
    stroke-width: 0.5;
    vector-effect: non-scaling-stroke;
  }
```

- [ ] **Step 6: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟這次改動之前一樣（這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤，環境缺套件、跟本次改動無關），用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 50，或用 `grep -i "ConfusionMatrixPanel"` 確認輸出裡沒有這個檔案的錯誤。

- [ ] **Step 7: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add calibration curve tab to ConfusionMatrixPanel"
```

---

## 完成後的人工驗證

兩個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 執行一次 workflow（二元分類資料集），點畫布上「Classification Evaluation」節點
2. 確認第四個分頁「校準曲線」能正常切換，且切換模型 + fold 下拉時，內容跟著變
3. 校準曲線圖上看得到資料點（圓點）跟連接線，加上對角線（完美校準）參考線
4. 其他三個分頁（混淆矩陣／ROC 曲線／PR 曲線）不受影響，行為維持原樣
5. 用一個多分類資料集跑一次，確認校準曲線分頁顯示「此模型或此類別數不支援校準曲線」的空狀態文字
