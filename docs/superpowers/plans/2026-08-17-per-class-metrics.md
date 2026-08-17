# Per-Class 指標 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修掉多分類 precision/recall/f1 因為沒指定 `average` 而拋例外的既有 bug，並新增每個類別各自的 precision/recall/f1/support 顯示。

**Architecture:** 後端在 `test_score_service.py` 的 `_compute_metric()` 補上多分類時的 `average="macro"` 設定（二元分類既有行為不變），並新增 `build_per_class_metrics()`，用 `precision_recall_fscore_support(..., average=None)` 一次算出每個類別的指標。`workflow_service.py` 在組每筆結果時呼叫它，寫進 `per_class_metrics` 欄位。前端擴充 `ConfusionMatrixPanel.vue`：加第五個分頁，純 HTML 表格（不需要圖表），F1 最低的那一列用既有的醒目底色標出來。

**Tech Stack:** Python (`sklearn.metrics.precision_recall_fscore_support`)，Vue 3 `<script setup>` + TypeScript。

## Global Constraints

- 二元分類（`effective_pos` 非 `None`）的既有 precision/recall/f1 聚合值行為完全不變
- 多分類且沒有明確正類時，聚合值改用 `average="macro"`
- `build_per_class_metrics()` 對二元、多分類都要能用，不需要 `y_score`，不需要額外的 try/except 防護（純粹是 `y_true`/`y_pred` 的函式，沒有會拋例外的路徑）
- 前端第五分頁不受「僅支援二元分類」限制，只要有 `confusion_matrix`/`per_class_metrics` 資料就顯示，空狀態文字比照混淆矩陣分頁既有寫法（不是 ROC/PR/校準曲線那種「僅支援二元分類」文字）
- 不新增畫布節點，`confusionMatrix` 節點不再變動
- 浮點數回傳前四捨五入到小數點後 6 位（比照既有的 `build_roc_pr_curve`/`build_calibration_curve` 慣例）

---

### Task 1: 後端修 average bug + 新增 per-class 指標計算

**Files:**
- Modify: `backend/services/workflow/test_score_service.py`
- Modify: `backend/services/workflow/workflow_service.py`

**Interfaces:**
- Produces: `build_per_class_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]`，回傳形狀 `{"labels": List[str], "precision": List[float], "recall": List[float], "f1": List[float], "support": List[int]}`（不會回傳 `None`，永遠有值）

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
```

改成（在 `matthews_corrcoef` 之後、`precision_recall_curve` 之前插入 `precision_recall_fscore_support`，維持字母排序）：

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
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
```

- [ ] **Step 2: 修 `_compute_metric()` 的 average bug**

`test_score_service.py` 現有的 precision/recall/f1 分支（在 `elif metric == "specificity":` 之前、`elif metric == "auc":` 之前的那個區塊）：

```python
    elif metric in {"precision", "recall", "f1"}:
        kwargs: Dict[str, Any] = {"zero_division": 0}
        effective_pos = pos_label or _infer_positive_label(y_true, labels)
        if effective_pos is not None:
            kwargs["pos_label"] = effective_pos
        if labels is not None:
            kwargs["labels"] = labels

        fn_map = {
            "precision": precision_score,
            "recall": recall_score,
            "f1": f1_score,
        }
        fn = fn_map[metric]
        value = fn(y_true, y_pred, **kwargs)
        if compute_ci:
```

改成（在 `if effective_pos is not None:` 這個 if 區塊加一個 `else` 分支，設定 `average="macro"`）：

```python
    elif metric in {"precision", "recall", "f1"}:
        kwargs: Dict[str, Any] = {"zero_division": 0}
        effective_pos = pos_label or _infer_positive_label(y_true, labels)
        if effective_pos is not None:
            kwargs["pos_label"] = effective_pos
        else:
            # 多分類且沒有明確正類：sklearn 預設 average='binary' 對多分類會拋例外，
            # 改用 macro，讓少數類別的表現不被多數類別稀釋掉
            kwargs["average"] = "macro"
        if labels is not None:
            kwargs["labels"] = labels

        fn_map = {
            "precision": precision_score,
            "recall": recall_score,
            "f1": f1_score,
        }
        fn = fn_map[metric]
        value = fn(y_true, y_pred, **kwargs)
        if compute_ci:
```

**注意**：只改動 `if effective_pos is not None:` 底下新增的 `else` 分支，二元分類（`effective_pos` 非 `None`）那條路徑完全不動——不要在 `if` 分支裡加任何東西。

- [ ] **Step 3: 新增 `build_per_class_metrics()` 函式**

`test_score_service.py` 現有的 `build_calibration_curve()` 函式（在 `# Public evaluation function` 區塊、`evaluate_metrics()` 之前）之後，新增：

```python
def build_per_class_metrics(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]:
    """算每個類別各自的 precision/recall/f1/support，二元、多分類皆適用，永遠有值。"""
    labels = sorted(pd.unique(pd.concat([y_true, y_pred]).dropna()), key=str)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    return {
        "labels": [str(label) for label in labels],
        "precision": [round(v, 6) for v in precision.tolist()],
        "recall": [round(v, 6) for v in recall.tolist()],
        "f1": [round(v, 6) for v in f1.tolist()],
        "support": [int(v) for v in support.tolist()],
    }
```

這個函式不需要 try/except（沒有 `_to_binary_array` 那種會因為數值型 target 混雜 NaN 而拋例外的路徑，`precision_recall_fscore_support` 對任意標籤型別都是安全的），也不需要任何 guard 檢查（不像 `build_roc_pr_curve`/`build_calibration_curve` 需要判斷是否為二元分類、是否有機率輸出——這個函式永遠有值可以回傳）。

- [ ] **Step 4: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/test_score_service.py datamind-backend:/tmp/test_score_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/test_score_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 5: 用 repro script 驗證 bug 修好了且新函式正確**

Run（在 `datamind-backend` 容器內）：
```bash
docker exec datamind-backend .venv/bin/python -c "
import sys
sys.path.insert(0, '/app')
import numpy as np
import pandas as pd
from services.workflow.test_score_service import evaluate_metrics, build_per_class_metrics

rng = np.random.RandomState(0)

# Case 1: 三分類，驗證 precision/recall/f1 不再回傳 error
y_true = pd.Series([0, 1, 2] * 34)
y_pred = pd.Series([0, 1, 2] * 30 + [1, 2, 0] * 4)
score_variants = [
    {'id': 'p', 'metric': 'precision'},
    {'id': 'r', 'metric': 'recall'},
    {'id': 'f', 'metric': 'f1'},
]
results = evaluate_metrics(y_true, y_pred, None, score_variants)
for r in results:
    assert r.get('error') is None, f'{r[\"metric\"]} still errors: {r.get(\"error\")}'
    assert isinstance(r.get('value'), float), f'{r[\"metric\"]} has no value'
print('Case 1 (multiclass precision/recall/f1 no longer error): OK', [(r['metric'], round(r['value'], 3)) for r in results])

# Case 2: 二元分類，確認既有行為不變（仍然是單一正類的數值，不是 macro）
y_true_bin = pd.Series([0, 1] * 50)
y_pred_bin = pd.Series([0, 1] * 48 + [1, 0] * 2)
results_bin = evaluate_metrics(y_true_bin, y_pred_bin, None, score_variants)
for r in results_bin:
    assert r.get('error') is None
print('Case 2 (binary precision/recall/f1 unchanged): OK', [(r['metric'], round(r['value'], 3)) for r in results_bin])

# Case 3: build_per_class_metrics 對多分類回傳正確筆數
per_class = build_per_class_metrics(y_true, y_pred)
assert len(per_class['labels']) == 3, f'expected 3 labels, got {len(per_class[\"labels\"])}'
assert len(per_class['precision']) == 3 and len(per_class['recall']) == 3 and len(per_class['f1']) == 3 and len(per_class['support']) == 3
print('Case 3 (per-class metrics, multiclass): OK', per_class)

# Case 4: build_per_class_metrics 對二元分類回傳正確筆數
per_class_bin = build_per_class_metrics(y_true_bin, y_pred_bin)
assert len(per_class_bin['labels']) == 2, f'expected 2 labels, got {len(per_class_bin[\"labels\"])}'
print('Case 4 (per-class metrics, binary): OK', per_class_bin)

print('ALL CASES PASSED')
"
```
Expected: 四個 case 都印出 OK，最後印出 `ALL CASES PASSED`，過程中沒有任何 Python traceback

- [ ] **Step 6: 在 `workflow_service.py` 加 import**

現有的 import：
```python
from .test_score_service import (
    build_calibration_curve,
    build_roc_pr_curve,
    evaluate_metrics,
    generate_score_variants,
)
```
改成：
```python
from .test_score_service import (
    build_calibration_curve,
    build_per_class_metrics,
    build_roc_pr_curve,
    evaluate_metrics,
    generate_score_variants,
)
```

- [ ] **Step 7: 非串流版 `execute_workflow` 接上 `per_class_metrics`**

第 491 行現有：
```python
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                            "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```
改成：
```python
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                            "per_class_metrics": build_per_class_metrics(y_test, y_pred),
                            "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```

- [ ] **Step 8: 串流版 `execute_workflow_stream` 接上 `per_class_metrics`**

第 695 行現有：
```python
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                        "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```
改成：
```python
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                        "per_class_metrics": build_per_class_metrics(y_test, y_pred),
                        "roc_pr_curve": build_roc_pr_curve(y_test, y_score),
```

- [ ] **Step 9: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/workflow_service.py datamind-backend:/tmp/workflow_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/workflow_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 10: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/test_score_service.py backend/services/workflow/workflow_service.py
git commit -m "fix: use macro average for multiclass precision/recall/f1, add per-class metrics"
```

---

### Task 2: 前端 `ConfusionMatrixPanel.vue` 加第五個分頁顯示各類別指標

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: `workflowResult.results[].per_class_metrics`，形狀 `{labels: string[], precision: number[], recall: number[], f1: number[], support: number[]} | null | undefined`（Task 1 產生，正常情況下永遠有值，只有舊版執行結果會缺欄位）
- Consumes（既有，不變）: `groupedResults`/`currentModel`/`selectedModel`/`selectedFold` 這幾個既有的 computed/ref

- [ ] **Step 1: 加資料型別與 parsing**

在 `interface CalibrationCurveData { ... }` 之後新增：

```typescript
  interface PerClassMetricsData {
    labels: string[]
    precision: number[]
    recall: number[]
    f1: number[]
    support: number[]
  }
```

`interface ResultItem` 現有：
```typescript
  interface ResultItem {
    model_name: string
    split_name: string
    confusion_matrix: ConfusionMatrixData | null
    roc_pr_curve: RocPrCurveData | null
    calibration_curve: CalibrationCurveData | null
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
    per_class_metrics: PerClassMetricsData | null
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
      calibration_curve: CalibrationCurveData | null
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
      per_class_metrics: PerClassMetricsData | null
    }>
  }
```

在 `parseCalibrationCurve()` 函式之後新增 `parsePerClassMetrics()`：

```typescript
  function parsePerClassMetrics (value: unknown): PerClassMetricsData | null {
    if (!value || typeof value !== 'object') return null
    const obj = value as Record<string, unknown>
    const labels = obj.labels
    const precision = obj.precision
    const recall = obj.recall
    const f1 = obj.f1
    const support = obj.support

    if (!Array.isArray(labels) || !labels.every(l => typeof l === 'string')) return null

    const isNumberArray = (arr: unknown): arr is number[] =>
      Array.isArray(arr) && arr.every(n => typeof n === 'number')

    if (!isNumberArray(precision) || !isNumberArray(recall) || !isNumberArray(f1) || !isNumberArray(support)) {
      return null
    }
    if (
      precision.length !== labels.length
      || recall.length !== labels.length
      || f1.length !== labels.length
      || support.length !== labels.length
    ) {
      return null
    }

    return { labels, precision, recall, f1, support }
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
      const calibration_curve = parseCalibrationCurve(result.calibration_curve)
      return { model_name, split_name, confusion_matrix, roc_pr_curve, calibration_curve }
    }).filter(item =>
      item.confusion_matrix !== null || item.roc_pr_curve !== null || item.calibration_curve !== null,
    ),
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
      const per_class_metrics = parsePerClassMetrics(result.per_class_metrics)
      return { model_name, split_name, confusion_matrix, roc_pr_curve, calibration_curve, per_class_metrics }
    }).filter(item =>
      item.confusion_matrix !== null
      || item.roc_pr_curve !== null
      || item.calibration_curve !== null
      || item.per_class_metrics !== null,
    ),
  )
```

`groupedResults` computed 裡建立 `entry` 的地方現有：
```typescript
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
        calibration_curve: result.calibration_curve,
      }
```
改成：
```typescript
      const entry = {
        split_name: result.split_name,
        confusion_matrix: result.confusion_matrix,
        roc_pr_curve: result.roc_pr_curve,
        calibration_curve: result.calibration_curve,
        per_class_metrics: result.per_class_metrics,
      }
```

- [ ] **Step 3: 加分頁項、`currentPerClassMetrics`/`perClassRows`/`lowestF1Label` computed**

現有的 `TabKey`/`TABS`：
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
改成：
```typescript
  type TabKey = 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'
  const activeTab = ref<TabKey>('matrix')

  const TABS: Array<{ key: TabKey, label: string }> = [
    { key: 'matrix', label: '混淆矩陣' },
    { key: 'roc', label: 'ROC 曲線' },
    { key: 'pr', label: 'PR 曲線' },
    { key: 'calibration', label: '校準曲線' },
    { key: 'perClass', label: '各類別指標' },
  ]
```

在 `const currentCalibrationCurve = computed(...)` 之後新增：

```typescript
  const currentPerClassMetrics = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.per_class_metrics ?? null,
  )

  interface PerClassRow {
    label: string
    precision: number
    recall: number
    f1: number
    support: number
  }

  const perClassRows = computed<PerClassRow[]>(() => {
    const data = currentPerClassMetrics.value
    if (!data) return []
    return data.labels.map((label, i) => ({
      label,
      precision: data.precision[i]!,
      recall: data.recall[i]!,
      f1: data.f1[i]!,
      support: data.support[i]!,
    }))
  })

  const lowestF1Label = computed(() => {
    const rows = perClassRows.value
    if (rows.length === 0) return null
    return rows.reduce((min, row) => (row.f1 < min.f1 ? row : min)).label
  })
```

- [ ] **Step 4: Template — 加各類別指標分頁區塊**

現有的校準曲線分頁區塊結尾是：
```html
    <div v-else-if="activeTab === 'calibration' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
    </div>

    <div v-if="groupedResults.length === 0" class="summary-empty">
      尚未有混淆矩陣結果，請執行 Workflow 後再查看。
    </div>
```

在校準曲線分頁的空狀態區塊**之後**、「尚未有混淆矩陣結果」區塊**之前**，插入各類別指標分頁區塊：

```html
    <div v-if="activeTab === 'perClass' && currentPerClassMetrics" class="cm-table-wrap">
      <table class="cm-table">
        <thead>
          <tr>
            <th class="cm-header">類別</th>
            <th class="cm-header">Precision</th>
            <th class="cm-header">Recall</th>
            <th class="cm-header">F1</th>
            <th class="cm-header">樣本數</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in perClassRows"
            :key="row.label"
            :class="{ 'cm-row--lowest': row.label === lowestF1Label }"
          >
            <td class="cm-cell">{{ row.label }}</td>
            <td class="cm-cell">{{ row.precision.toFixed(3) }}</td>
            <td class="cm-cell">{{ row.recall.toFixed(3) }}</td>
            <td class="cm-cell">{{ row.f1.toFixed(3) }}</td>
            <td class="cm-cell">{{ row.support }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else-if="activeTab === 'perClass' && groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的各類別指標資訊。
    </div>
```

**注意**：這個新區塊必須維持獨立的 `v-if`（不是 `v-else-if`）開頭，就像其他四個分頁區塊彼此獨立一樣。維持它在「尚未有混淆矩陣結果」（`groupedResults.length === 0`）那個獨立 `v-if` 區塊**之前**插入，不要插到它後面，也不要跟前一個（校準曲線）分頁的 `v-else-if` 串在一起。

- [ ] **Step 5: 加對應樣式**

在 `.cm-cell--diagonal { ... }` 規則之後新增：

```css
  .cm-row--lowest .cm-cell {
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    font-weight: 700;
  }
```

- [ ] **Step 6: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟這次改動之前一樣（這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤，環境缺套件、跟本次改動無關），用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 50，或用 `grep -i "ConfusionMatrixPanel"` 確認輸出裡沒有這個檔案的錯誤。

- [ ] **Step 7: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add per-class metrics tab to ConfusionMatrixPanel"
```

---

## 完成後的人工驗證

兩個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 執行一次 workflow（多分類資料集，例如 3 個類別），點畫布上「Classification Evaluation」節點
2. 確認主要結果表格的 precision/recall/f1 不再顯示「error」，有實際數值
3. 確認第五個分頁「各類別指標」正確顯示每個類別的 precision/recall/f1/樣本數，F1 最低的那一列有醒目標示
4. 切換模型 + fold 下拉時，內容跟著變
5. 用一個二元分類資料集跑一次，確認整體指標行為跟這次改動之前一樣（沒有變動），第五個分頁也正常顯示兩個類別各自的指標，其他四個分頁不受影響
