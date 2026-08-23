# 混淆矩陣節點補完 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓畫布上原本是死節點的「Confusion Matrix」真正可以運作：後端算出並回傳混淆矩陣，前端有面板能顯示。

**Architecture:** 後端在 `execute_workflow`/`execute_workflow_stream` 組結果的地方各自呼叫一個新增的共用 `@staticmethod`（`_build_confusion_matrix`），把 `{labels, matrix}` 加進每筆結果。前端新增 `ConfusionMatrixPanel.vue`，比照既有 `FeatureImportancePanel.vue` 的「模型 + fold 雙下拉切換」互動模式，`WorkflowOptionsPanel.vue` 新增一個分支接上這個面板。

**Tech Stack:** Python 3.11、scikit-learn、Vue 3 `<script setup>`、TypeScript。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-15-confusion-matrix-design.md`
- 混淆矩陣資料形狀固定為 `{labels: string[], matrix: number[][]}`（NxN，不寫死二分類）
- **不**動 `evaluate_metrics()`/`_specificity()` 等既有 metrics 計算邏輯
- **不**動節點 id、既有的邊連接、`useWorkflowNodes.ts`/`useWorkflowDemo.ts`/`useWorkflowImport.ts` 對 `confusionMatrix` id 的既有引用
- 本專案沒有 pytest/vitest，後端用 `py_compile` 語法檢查 + 人工驗證，前端用 `npm run type-check` + 人工瀏覽器驗證

---

### Task 1: 後端 — 計算並回傳混淆矩陣

**Files:**
- Modify: `backend/services/workflow/workflow_service.py`

**Interfaces:**
- Produces: `WorkflowService._build_confusion_matrix(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]`，回傳 `{"labels": List[str], "matrix": List[List[int]]}`；`execute_workflow`/`execute_workflow_stream` 回傳的每筆 `results` 項目新增 `confusion_matrix` 欄位，供 Task 2 的前端面板消費

- [ ] **Step 1: 新增 sklearn 的 confusion_matrix import**

找到 `backend/services/workflow/workflow_service.py` 的（第 1-9 行）：

```python
from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import (
```

改成（在 `import pandas as pd` 後面加一行）：

```python
from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix as sk_confusion_matrix
from sklearn.model_selection import (
```

- [ ] **Step 2: 新增 `_build_confusion_matrix` 共用方法**

找到（第 125-151 行，`_extract_feature_importance` 方法結尾）：

```python
    @staticmethod
    def _extract_feature_importance(
        estimator: Any, feature_names: List[str]
    ) -> Optional[List[Dict[str, Any]]]:
        if not feature_names:
            return None

        importance_values = None
        if hasattr(estimator, "feature_importances_"):
            importance_values = np.asarray(getattr(estimator, "feature_importances_"))
        elif hasattr(estimator, "coef_"):
            coef = np.asarray(getattr(estimator, "coef_"))
            importance_values = (
                np.abs(coef) if coef.ndim == 1 else np.mean(np.abs(coef), axis=0)
            )

        if importance_values is None or importance_values.shape[0] != len(feature_names):
            return None

        return sorted(
            [
                {"feature": f, "importance": float(v)}
                for f, v in zip(feature_names, importance_values)
            ],
            key=lambda x: x["importance"],
            reverse=True,
        )
```

改成（在後面新增 `_build_confusion_matrix`）：

```python
    @staticmethod
    def _extract_feature_importance(
        estimator: Any, feature_names: List[str]
    ) -> Optional[List[Dict[str, Any]]]:
        if not feature_names:
            return None

        importance_values = None
        if hasattr(estimator, "feature_importances_"):
            importance_values = np.asarray(getattr(estimator, "feature_importances_"))
        elif hasattr(estimator, "coef_"):
            coef = np.asarray(getattr(estimator, "coef_"))
            importance_values = (
                np.abs(coef) if coef.ndim == 1 else np.mean(np.abs(coef), axis=0)
            )

        if importance_values is None or importance_values.shape[0] != len(feature_names):
            return None

        return sorted(
            [
                {"feature": f, "importance": float(v)}
                for f, v in zip(feature_names, importance_values)
            ],
            key=lambda x: x["importance"],
            reverse=True,
        )

    @staticmethod
    def _build_confusion_matrix(y_true: pd.Series, y_pred: pd.Series) -> Dict[str, Any]:
        """算 NxN 混淆矩陣，不寫死二分類——sklearn 本來就支援任意類別數。"""
        labels = sorted(pd.unique(pd.concat([y_true, y_pred]).dropna()), key=str)
        matrix = sk_confusion_matrix(y_true, y_pred, labels=labels)
        return {
            "labels": [str(label) for label in labels],
            "matrix": matrix.tolist(),
        }
```

- [ ] **Step 3: 非串流版 `execute_workflow` 加上 confusion_matrix 欄位**

找到（第 461-478 行）：

```python
                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "preprocess_steps": pipeline_steps,
                            "feature_engineering_steps": feature_steps,
                            "split_name": split_def["name"],
                            "validation_config": split_def["config"],
                            "resampling_method": resampling_method,
                            "best_params": best_params,
                            "metrics": metrics,
                            "feature_importance": cls._extract_feature_importance(
                                estimator, list(X_train.columns)
                            ),
                            "feature_count": int(X_train.shape[1]),
                            "row_count": int(X_train.shape[0]),
                        }
                    )
```

改成（新增 `"confusion_matrix"` 那一行）：

```python
                    results.append(
                        {
                            "preprocess_pipeline_index": pipeline_index,
                            "model_name": model_name,
                            "preprocess_steps": pipeline_steps,
                            "feature_engineering_steps": feature_steps,
                            "split_name": split_def["name"],
                            "validation_config": split_def["config"],
                            "resampling_method": resampling_method,
                            "best_params": best_params,
                            "metrics": metrics,
                            "feature_importance": cls._extract_feature_importance(
                                estimator, list(X_train.columns)
                            ),
                            "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                            "feature_count": int(X_train.shape[1]),
                            "row_count": int(X_train.shape[0]),
                        }
                    )
```

- [ ] **Step 4: 串流版 `execute_workflow_stream` 加上 confusion_matrix 欄位**

找到（第 663-678 行）：

```python
                    model_results.append({
                        "preprocess_pipeline_index": pipeline_index,
                        "model_name": model_name,
                        "preprocess_steps": pipeline_steps,
                        "feature_engineering_steps": feature_steps,
                        "split_name": split_def["name"],
                        "validation_config": split_def["config"],
                        "resampling_method": resampling_method,
                        "best_params": best_params,
                        "metrics": metrics,
                        "feature_importance": cls._extract_feature_importance(
                            estimator, list(X_train.columns)
                        ),
                        "feature_count": int(X_train.shape[1]),
                        "row_count": int(X_train.shape[0]),
                    })
```

改成：

```python
                    model_results.append({
                        "preprocess_pipeline_index": pipeline_index,
                        "model_name": model_name,
                        "preprocess_steps": pipeline_steps,
                        "feature_engineering_steps": feature_steps,
                        "split_name": split_def["name"],
                        "validation_config": split_def["config"],
                        "resampling_method": resampling_method,
                        "best_params": best_params,
                        "metrics": metrics,
                        "feature_importance": cls._extract_feature_importance(
                            estimator, list(X_train.columns)
                        ),
                        "confusion_matrix": cls._build_confusion_matrix(y_test, y_pred),
                        "feature_count": int(X_train.shape[1]),
                        "row_count": int(X_train.shape[0]),
                    })
```

- [ ] **Step 5: 語法檢查**

Run: `docker exec datamind-backend sh -lc "cd /app && .venv/bin/python -m py_compile services/workflow/workflow_service.py && echo OK"`
Expected: 印出 `OK`

- [ ] **Step 6: 手動驗證（跑一個真實 workflow，檢查回傳資料）**

用瀏覽器對一個已有資料表的專案跑一次 workflow 執行（沿用 Task 3 步驟裡會做的操作即可，或先用瀏覽器 Network 分頁檢查 `POST /api/workflow/execute` 或對應串流端點的回應），確認 `results[].confusion_matrix` 存在，且 `labels`/`matrix` 是合理的陣列（例如二分類任務應該是 `labels` 長度 2、`matrix` 是 2x2）。

Expected: 每筆結果都有 `confusion_matrix` 欄位，`matrix` 所有數字加總等於該筆結果的測試集樣本數

- [ ] **Step 7: Commit**

```bash
git add backend/services/workflow/workflow_service.py
git commit -m "feat: compute and return confusion matrix per workflow result"
```

---

### Task 2: 前端 — 新增 ConfusionMatrixPanel.vue

**Files:**
- Create: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: Task 1 的 `results[].confusion_matrix: {labels: string[], matrix: number[][]}`（透過 `workflowResult` prop 整包傳入，跟 `FeatureImportancePanel.vue` 讀 `feature_importance` 的方式一致）
- Produces: `ConfusionMatrixPanel` 元件，prop `workflowResult?: Record<string, unknown> | null`，供 Task 3 的 `WorkflowOptionsPanel.vue` 使用

- [ ] **Step 1: 建立元件檔案**

建立 `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`：

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

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add ConfusionMatrixPanel component"
```

---

### Task 3: 前端 — 接上 confusionMatrix 節點

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue`

**Interfaces:**
- Consumes: Task 2 的 `ConfusionMatrixPanel`（prop `workflowResult?: Record<string, unknown> | null`）

- [ ] **Step 1: 匯入元件**

找到 `frontend/src/components/workflow/WorkflowOptionsPanel.vue` 的（第 238-245 行）：

```ts
  import ComputeCiPanel from './nodePanel/ComputeCiPanel.vue'
  import DataTablePanel from './nodePanel/DataTablePanel.vue'
  import DistributionPanel from './nodePanel/DistributionPanel.vue'
  import FeatureEngineeringPanel from './nodePanel/FeatureEngineeringPanel.vue'
  import FeatureImportancePanel from './nodePanel/FeatureImportancePanel.vue'
  import PreprocessorPanel from './nodePanel/PreprocessorPanel.vue'
  import SettingsPanel from './nodePanel/SettingsPanel.vue'
  import TestScorePanel from './nodePanel/TestScorePanel.vue'
```

改成（`ComputeCiPanel` 跟 `DataTablePanel` 之間依字母順序插入）：

```ts
  import ComputeCiPanel from './nodePanel/ComputeCiPanel.vue'
  import ConfusionMatrixPanel from './nodePanel/ConfusionMatrixPanel.vue'
  import DataTablePanel from './nodePanel/DataTablePanel.vue'
  import DistributionPanel from './nodePanel/DistributionPanel.vue'
  import FeatureEngineeringPanel from './nodePanel/FeatureEngineeringPanel.vue'
  import FeatureImportancePanel from './nodePanel/FeatureImportancePanel.vue'
  import PreprocessorPanel from './nodePanel/PreprocessorPanel.vue'
  import SettingsPanel from './nodePanel/SettingsPanel.vue'
  import TestScorePanel from './nodePanel/TestScorePanel.vue'
```

- [ ] **Step 2: 加新的 template 分支**

找到（第 33-37 行）：

```html
        <template v-else-if="selectedNode.id === 'featureImportance'">
          <FeatureImportancePanel
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>
```

改成（在後面新增 `confusionMatrix` 分支）：

```html
        <template v-else-if="selectedNode.id === 'featureImportance'">
          <FeatureImportancePanel
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>

        <template v-else-if="selectedNode.id === 'confusionMatrix'">
          <ConfusionMatrixPanel
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: 人工瀏覽器驗證**

開一個已經有資料表跟框架的專案，進 workflow 頁面，執行一次完整的 workflow。執行完點 `confusionMatrix` 節點。

Expected:
- 面板顯示模型 + fold 下拉選單，不再是空白
- 切換模型/fold，表格內容跟著換
- NxN 表格正確顯示，橫軸「預測：xxx」、縱軸「實際：xxx」，對角線格子有底色
- 表格所有數字加總，等於該筆結果的測試集樣本數（可以對照 `testScore` 節點看到的樣本數/資料筆數）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/WorkflowOptionsPanel.vue
git commit -m "feat: wire ConfusionMatrixPanel to confusionMatrix node"
```
