# 分頁 AI 解讀 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ConfusionMatrixPanel.vue` 的五個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標）各自旁邊加一個「AI 解讀」按鈕，按下才呼叫 Gemini 針對該分頁當前的資料生成一段繁體中文解讀，並依 (分頁, 模型, fold) 組合快取。

**Architecture:** 後端在既有的 `PaperRagService`（`backend/services/rag/paper_rag.py`）新增 `generate_tab_insight()`，複用既有的 `_call_gemini()` 呼叫慣例，只把該分頁需要的精簡資料（不是整條曲線陣列）組成文字丟給 Gemini；新路由 `POST /api/rag/tab-insight` 比照既有 `/insight` 路由的寫法。前端新增一支 API 函式 + 一組 localStorage 快取函式（key 含 tab/model/fold/projectId 四個維度），`projectId` 需要從 `WorkflowWorkspace.vue` 一路往下傳到 `ConfusionMatrixPanel.vue`；面板的每個分頁內容區改成左右兩欄版面，右邊統一用同一個 AI 解讀面板（不因分頁不同而各寫一份，用 `activeTab`/`selectedModel`/`selectedFold` 這三個既有狀態去參數化）。

**Tech Stack:** Python (Flask, 既有的 `google.generativeai` 封裝)，Vue 3 `<script setup>` + TypeScript。

## Global Constraints

- 不自動生成，一律使用者按「AI 解讀」按鈕才觸發（跟既有的 `/insight` 自動生成模式不同，這是刻意的設計決策，因為組合數是 tab × model × fold）
- 不把整條曲線座標陣列（ROC/PR）原始送給 Gemini，取樣最多 5 個點；混淆矩陣、校準曲線（≤10 個 bin）、各類別指標本身資料量就小，直接送
- 快取 key 要包含 tab/model/fold/projectId 四個維度，且要在既有的兩個「重新開始 workflow」時機點（`handleApplyColumnConfig`/`handleContinueSettings`）一併清空
- Gemini 呼叫失敗時比照既有 `_call_gemini()` 慣例（回傳說明字串，不拋例外），只有網路/服務層級的例外才讓路由回 500

---

### Task 1: 後端新增 `generate_tab_insight()` 與路由

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Modify: `backend/routes/rag.py`

**Interfaces:**
- Produces: `PaperRagService.generate_tab_insight(mining_results: dict, tab: str, model_name: str, split_name: str) -> str`（永遠回傳字串，找不到資料或生成失敗都回傳說明文字，不拋例外）
- Produces: 路由 `POST /api/rag/tab-insight`，接 `{mining_results, tab, model_name, split_name}`，回傳 `{"success": true, "insight": "..."}` 或 `{"success": false, "error": "..."}`

- [ ] **Step 1: 在 `paper_rag.py` 新增資料格式化與生成函式**

`paper_rag.py` 現有的 `generate_insight()`（第 411-423 行）之後、`score_paper()`（第 425 行）之前，新增：

```python
    _TAB_PROMPT_HINTS: Dict[str, str] = {
        "matrix": "請指出模型最容易把哪個類別誤判成哪個類別，這對臨床判讀有什麼提醒。",
        "roc": "請說明這個 AUC 數值代表模型的判別力好不好，並簡述曲線形狀反映的意義。",
        "pr": "請說明在類別不平衡的情境下 PR 曲線的意義，以及這個結果顯示模型在少數類別上的表現如何。",
        "calibration": "請說明這個模型輸出的機率是否可信賴，是偏樂觀還是偏保守。",
        "perClass": "請指出表現最差的類別，並簡述可能的原因或後續建議。",
    }

    @staticmethod
    def _sample_curve_points(
        xs: List[float], ys: List[float], n: int = 5
    ) -> List[tuple]:
        """均勻取樣最多 n 個點，避免把整條曲線的完整座標陣列丟給 Gemini。"""
        if not xs or not ys:
            return []
        if len(xs) <= n:
            return list(zip(xs, ys))
        step = (len(xs) - 1) / (n - 1)
        indices = sorted({round(i * step) for i in range(n)})
        return [(xs[i], ys[i]) for i in indices]

    def _find_tab_result(
        self, mining_results: dict, model_name: str, split_name: str
    ) -> Optional[dict]:
        for r in mining_results.get("results", []):
            if (
                r.get("model_name") == model_name
                and r.get("split_name") == split_name
                and "error" not in r
            ):
                return r
        return None

    def _format_tab_data(self, result: dict, tab: str) -> Optional[str]:
        """只挑該分頁需要的欄位轉成精簡文字，不送整包原始資料。"""
        if tab == "matrix":
            cm = result.get("confusion_matrix")
            if not cm:
                return None
            labels = cm.get("labels", [])
            matrix = cm.get("matrix", [])
            rows = []
            for i, label in enumerate(labels):
                row = matrix[i] if i < len(matrix) else []
                row_str = "、".join(
                    f"預測{labels[j]}={row[j]}" for j in range(min(len(row), len(labels)))
                )
                rows.append(f"實際{label}：{row_str}")
            return "【混淆矩陣】\n" + "\n".join(rows)

        if tab in ("roc", "pr"):
            curve = result.get("roc_pr_curve")
            if not curve:
                return None
            metric_key = "auc" if tab == "roc" else "auprc"
            metric_val = next(
                (m.get("value") for m in result.get("metrics", []) if m.get("metric") == metric_key),
                None,
            )
            sub = curve.get("roc" if tab == "roc" else "pr", {})
            xs_key, ys_key = ("fpr", "tpr") if tab == "roc" else ("recall", "precision")
            points = self._sample_curve_points(sub.get(xs_key, []), sub.get(ys_key, []))
            points_str = "、".join(f"({x:.2f}, {y:.2f})" for x, y in points) or "N/A"
            metric_label = "AUC" if tab == "roc" else "AUPRC"
            metric_str = f"{metric_val:.4f}" if isinstance(metric_val, (int, float)) else "N/A"
            axis_label = "FPR, TPR" if tab == "roc" else "Recall, Precision"
            return (
                f"【{'ROC' if tab == 'roc' else 'PR'} 曲線】\n"
                f"正類：{curve.get('pos_label', 'N/A')}\n"
                f"{metric_label}：{metric_str}\n"
                f"取樣座標點（{axis_label}）：{points_str}"
            )

        if tab == "calibration":
            curve = result.get("calibration_curve")
            if not curve:
                return None
            prob_true = curve.get("prob_true", [])
            prob_pred = curve.get("prob_pred", [])
            points_str = "、".join(
                f"(預測{p:.2f}, 實際{t:.2f})" for p, t in zip(prob_pred, prob_true)
            ) or "N/A"
            return (
                f"【校準曲線】\n"
                f"正類：{curve.get('pos_label', 'N/A')}\n"
                f"各 bin（預測機率, 實際正類比例）：{points_str}"
            )

        if tab == "perClass":
            pcm = result.get("per_class_metrics")
            if not pcm:
                return None
            labels = pcm.get("labels", [])
            precision = pcm.get("precision", [])
            recall = pcm.get("recall", [])
            f1 = pcm.get("f1", [])
            support = pcm.get("support", [])
            rows = []
            for i, label in enumerate(labels):
                p = precision[i] if i < len(precision) else None
                r = recall[i] if i < len(recall) else None
                f = f1[i] if i < len(f1) else None
                s = support[i] if i < len(support) else None
                p_str = f"{p:.4f}" if isinstance(p, (int, float)) else "N/A"
                r_str = f"{r:.4f}" if isinstance(r, (int, float)) else "N/A"
                f_str = f"{f:.4f}" if isinstance(f, (int, float)) else "N/A"
                rows.append(f"{label}：precision={p_str}, recall={r_str}, f1={f_str}, 樣本數={s}")
            return "【各類別指標】\n" + "\n".join(rows)

        return None

    def generate_tab_insight(
        self, mining_results: dict, tab: str, model_name: str, split_name: str
    ) -> str:
        """針對 workflow 結果裡某個 (model × fold) 的單一分頁資料，生成一段繁體中文解讀。"""
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        hint = self._TAB_PROMPT_HINTS.get(tab, "")
        prompt = (
            "你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果。\n"
            f"以下是模型「{model_name}」在「{split_name}」這筆結果的資料：\n\n"
            f"{tab_text}\n\n"
            f"請用繁體中文寫 2 到 4 句話的解讀。{hint}\n"
            "請「只」輸出解讀本身，不要加上任何標題、條列符號或多餘說明文字。"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        return text.strip()
```

`List`、`Dict`、`Optional` 這個檔案開頭（第 17 行）已經從 `typing` 匯入，不需要新增 import。

- [ ] **Step 2: 語法檢查**

Run:
```bash
docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 3: 在 `rag.py` 新增路由**

`rag.py` 檔案結尾（現有的 `generate_insight()` 路由，第 430-454 行）之後新增：

```python


@rag_bp.route("/tab-insight", methods=["POST"])
def generate_tab_insight():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標）生成 AI 解讀文字

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要解讀哪個模型（必填）
        - split_name      : 要解讀哪個 fold/split（必填）

    回傳：
        - insight : AI 生成的解讀文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    split_name = data.get("split_name")
    if not tab or not model_name or not split_name:
        return jsonify({"success": False, "error": "tab、model_name、split_name 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_tab_insight(data["mining_results"], tab, model_name, split_name)
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("分頁解讀生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 4: 語法檢查**

Run:
```bash
docker cp backend/routes/rag.py datamind-backend:/tmp/rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 5: 用 repro script 驗證資料格式化與生成邏輯**

Run（在 `datamind-backend` 容器內；這裡用假資料測 `_format_tab_data`/`_find_tab_result`，不必真的打 Gemini API，只驗證資料處理邏輯本身不會拋例外）：
```bash
docker exec datamind-backend .venv/bin/python -c "
import sys
sys.path.insert(0, '/app')
from services.rag.paper_rag import PaperRagService

svc = PaperRagService.__new__(PaperRagService)  # 跳過 __init__（不需要真的連 Gemini/DB 就能測資料格式化）

mining_results = {
    'results': [
        {
            'model_name': 'RandomForest', 'split_name': 'fold_1',
            'metrics': [{'metric': 'auc', 'value': 0.87}, {'metric': 'auprc', 'value': 0.81}],
            'confusion_matrix': {'labels': ['0', '1'], 'matrix': [[50, 5], [8, 37]]},
            'roc_pr_curve': {
                'pos_label': '1',
                'roc': {'fpr': [0.0, 0.1, 0.3, 0.6, 1.0], 'tpr': [0.0, 0.4, 0.7, 0.9, 1.0]},
                'pr': {'precision': [1.0, 0.9, 0.8, 0.6, 0.4], 'recall': [0.0, 0.3, 0.6, 0.8, 1.0]},
            },
            'calibration_curve': {'pos_label': '1', 'prob_true': [0.1, 0.5, 0.9], 'prob_pred': [0.15, 0.48, 0.85]},
            'per_class_metrics': {'labels': ['0', '1'], 'precision': [0.86, 0.88], 'recall': [0.91, 0.82], 'f1': [0.88, 0.85], 'support': [55, 45]},
        },
    ],
}

for tab in ['matrix', 'roc', 'pr', 'calibration', 'perClass']:
    text = svc._format_tab_data(mining_results['results'][0], tab)
    assert text is not None, f'{tab} unexpectedly returned None'
    print(f'--- {tab} ---')
    print(text)
    print()

# 找不到對應結果的情況
result = svc._find_tab_result(mining_results, 'NoSuchModel', 'fold_1')
assert result is None
print('_find_tab_result correctly returns None for unknown model: OK')

# 缺欄位的情況（例如舊版結果沒有 calibration_curve）
old_result = {'model_name': 'X', 'split_name': 'Y', 'metrics': []}
assert svc._format_tab_data(old_result, 'calibration') is None
print('_format_tab_data correctly returns None when field missing: OK')

print('ALL CASES PASSED')
"
```
Expected: 五個分頁都印出對應的格式化文字，最後印出 `ALL CASES PASSED`，過程中沒有任何 Python traceback

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/rag/paper_rag.py backend/routes/rag.py
git commit -m "feat: add per-tab AI insight generation endpoint"
```

---

### Task 2: 前端新增 API 函式與快取函式

**Files:**
- Modify: `frontend/src/api/insight.ts`
- Modify: `frontend/src/composables/workflow/useWorkflowStorage.ts`

**Interfaces:**
- Produces: `fetchTabInsight(miningResults: Record<string, unknown>, tab: string, modelName: string, splitName: string): Promise<string>`
- Produces: `saveTabInsightToStorage(projectId: string, modelName: string, splitName: string, tab: string, insight: string): void`
- Produces: `loadTabInsightFromStorage(projectId: string, modelName: string, splitName: string, tab: string): string | null`
- Produces: `clearAllTabInsightsFromStorage(projectId: string): void`

- [ ] **Step 1: 新增 `fetchTabInsight()`**

`frontend/src/api/insight.ts` 現有完整內容：
```typescript
export async function fetchResultInsight (miningResults: Record<string, unknown>): Promise<string> {
  const response = await fetch('/api/rag/insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}
```

在它之後新增：
```typescript

export async function fetchTabInsight (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}
```

- [ ] **Step 2: 新增快取函式**

`useWorkflowStorage.ts` 現有的 `clearResultInsightFromStorage()`（第 176-179 行）之後新增：

```typescript

const TAB_INSIGHT_KEY = 'tabInsight'

function tabInsightStorageKey (
  projectId: string, modelName: string, splitName: string, tab: string,
): string {
  return k(`${TAB_INSIGHT_KEY}_${tab}_${modelName}_${splitName}`, projectId)
}

export function saveTabInsightToStorage (
  projectId: string, modelName: string, splitName: string, tab: string, insight: string,
): void {
  const key = tabInsightStorageKey(projectId, modelName, splitName, tab)
  try {
    localStorage.setItem(key, insight)
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存分頁解讀文字:', error)
  }
}

export function loadTabInsightFromStorage (
  projectId: string, modelName: string, splitName: string, tab: string,
): string | null {
  const key = tabInsightStorageKey(projectId, modelName, splitName, tab)
  return localStorage.getItem(key)
}

// 分頁解讀是組合鍵（tab/model/fold 各自獨立一個 key），沒辦法像單一 key 那樣直接刪，
// 要掃描 localStorage 找出屬於這個 projectId 的全部分頁解讀 key 再逐一移除
export function clearAllTabInsightsFromStorage (projectId: string): void {
  const prefix = `${TAB_INSIGHT_KEY}_`
  const suffix = `_${projectId}`
  const staleKeys: string[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (key && key.startsWith(prefix) && key.endsWith(suffix)) {
      staleKeys.push(key)
    }
  }
  for (const key of staleKeys) {
    localStorage.removeItem(key)
  }
}
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件、跟本次改動無關）。用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 50，或用 `grep -iE "insight.ts|useWorkflowStorage"` 確認輸出裡沒有這兩個檔案的錯誤。

- [ ] **Step 4: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/api/insight.ts frontend/src/composables/workflow/useWorkflowStorage.ts
git commit -m "feat: add tab insight API call and localStorage cache functions"
```

---

### Task 3: 把 `projectId` 從 `WorkflowWorkspace.vue` 傳到 `ConfusionMatrixPanel.vue`，接上快取清空

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue`

**Interfaces:**
- Consumes: `clearAllTabInsightsFromStorage`（Task 2 產生）
- Produces: `WorkflowOptionsPanel` 新增 `projectId?: string` prop，往下傳給 `ConfusionMatrixPanel`（Task 4 會在那邊消費這個 prop）

- [ ] **Step 1: `WorkflowWorkspace.vue` 匯入 `clearAllTabInsightsFromStorage`**

現有的 import（第 139-146 行）：
```typescript
  import {
    clearResultInsightFromStorage,
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    loadWorkflowStateFromStorage,
    saveWorkflowDataFileToStorage,
    saveWorkflowStateToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
```
改成（按字母順序插入 `clearAllTabInsightsFromStorage`）：
```typescript
  import {
    clearAllTabInsightsFromStorage,
    clearResultInsightFromStorage,
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    loadWorkflowStateFromStorage,
    saveWorkflowDataFileToStorage,
    saveWorkflowStateToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
```

- [ ] **Step 2: 在既有的兩個清快取時機點一併清空分頁解讀快取**

現有的 `handleApplyColumnConfig`/`handleContinueSettings`（第 330-345 行）：
```typescript
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    if (projectId.value) clearResultInsightFromStorage(projectId.value)
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleContinueSettings (): void {
    if (projectId.value) clearResultInsightFromStorage(projectId.value)
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```
改成：
```typescript
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    if (projectId.value) {
      clearResultInsightFromStorage(projectId.value)
      clearAllTabInsightsFromStorage(projectId.value)
    }
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleContinueSettings (): void {
    if (projectId.value) {
      clearResultInsightFromStorage(projectId.value)
      clearAllTabInsightsFromStorage(projectId.value)
    }
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

- [ ] **Step 3: 把 `projectId` 傳給 `<WorkflowOptionsPanel>`**

現有的呼叫（第 82-104 行）：
```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :dataset-columns="dataTableColumns"
                :drawer-stage="drawerStage"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :validation-config="testScoreValidationConfig"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
                @add-model="handleAddModel"
                @apply-column-config="handleApplyColumnConfig"
                @back-node="handleBackToDataTable"
                @continue-settings="handleContinueSettings"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @settings-step-change="step => { settingsStep = step }"
                @update-config="handleUpdateConfig"
                @update:file="handleDataFile"
              />
```
改成（在 `:paused-node-id` 之後、`:selected-node` 之前插入 `:project-id`，維持字母順序）：
```html
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :dataset-columns="dataTableColumns"
                :drawer-stage="drawerStage"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :project-id="projectId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :validation-config="testScoreValidationConfig"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
                @add-model="handleAddModel"
                @apply-column-config="handleApplyColumnConfig"
                @back-node="handleBackToDataTable"
                @continue-settings="handleContinueSettings"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @settings-step-change="step => { settingsStep = step }"
                @update-config="handleUpdateConfig"
                @update:file="handleDataFile"
              />
```

- [ ] **Step 4: `WorkflowOptionsPanel.vue` 新增 `projectId` prop 並往下傳**

現有的 `defineProps`（第 269-282 行）：
```typescript
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
    validationConfig?: Record<string, unknown>
    datasetColumns?: Array<{ name: string, type: string, role: string }>
  }>()
```
改成（新增 `projectId?: string`）：
```typescript
  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
    validationConfig?: Record<string, unknown>
    datasetColumns?: Array<{ name: string, type: string, role: string }>
    projectId?: string
  }>()
```

現有的 `<ConfusionMatrixPanel>` 呼叫（第 39-43 行）：
```html
        <template v-else-if="selectedNode.id === 'confusionMatrix'">
          <ConfusionMatrixPanel
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>
```
改成：
```html
        <template v-else-if="selectedNode.id === 'confusionMatrix'">
          <ConfusionMatrixPanel
            :project-id="props.projectId"
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟 Task 2 結束時一樣（沒有新增，不含 `WorkflowWorkspace.vue`/`WorkflowOptionsPanel.vue` 的錯誤）。這一步 `ConfusionMatrixPanel.vue` 還沒有 `projectId` prop 的定義（那是 Task 4 的範圍），Vue 會允許傳入元件沒宣告的 prop（只是不會被用到），不會造成型別錯誤。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/WorkflowWorkspace.vue frontend/src/components/workflow/WorkflowOptionsPanel.vue
git commit -m "feat: thread projectId down to ConfusionMatrixPanel, clear tab insight cache on workflow restart"
```

---

### Task 4: `ConfusionMatrixPanel.vue` 加 AI 解讀面板

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: `fetchTabInsight`（Task 2）、`loadTabInsightFromStorage`/`saveTabInsightToStorage`（Task 2）、`projectId` prop（Task 3 已經從父層傳下來，這裡是第一次在這個檔案宣告它）

- [ ] **Step 1: 新增 import 與 `projectId` prop**

現有的 import 與 props（第 172-222 行附近）：
```typescript
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'
```
改成：
```typescript
  import { computed, ref, watch } from 'vue'
  import { fetchTabInsight } from '@/api/insight'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import { loadTabInsightFromStorage, saveTabInsightToStorage } from '@/composables/workflow/useWorkflowStorage.ts'
```

現有的：
```typescript
  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
  }>()
```
改成：
```typescript
  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
    projectId?: string
  }>()
```

- [ ] **Step 2: 新增 AI 解讀狀態與邏輯**

在 `const lowestF1Label = computed(...)`（第 419-423 行）之後新增：

```typescript
  const hasCurrentTabData = computed(() => {
    switch (activeTab.value) {
      case 'matrix': return currentMatrix.value !== null
      case 'roc':
      case 'pr': return currentRocPrCurve.value !== null
      case 'calibration': return currentCalibrationCurve.value !== null
      case 'perClass': return currentPerClassMetrics.value !== null
      default: return false
    }
  })

  const tabInsightCache = ref<Map<string, string>>(new Map())
  const tabInsightLoading = ref(false)
  const tabInsightError = ref<string | null>(null)

  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }

  const currentTabInsight = computed(() =>
    tabInsightCache.value.get(tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value)) ?? null,
  )

  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoading.value = true
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      tabInsightLoading.value = false
    }
  }

  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, selectedModel, selectedFold], () => {
    tabInsightError.value = null
    if (!props.projectId) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (tabInsightCache.value.has(key)) return
    const cached = loadTabInsightFromStorage(props.projectId, model, fold, tab)
    if (cached !== null) {
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
    }
  }, { immediate: true })
```

- [ ] **Step 3: Template — 包一層 `.cm-tab-row`，加共用的 AI 解讀面板**

現有的五個分頁內容區塊（第 35-163 行，完整內容）：
```html
    <div v-if="activeTab === 'matrix' && currentMatrix" class="cm-table-wrap">
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

    <div v-else-if="activeTab === 'matrix' && groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的混淆矩陣資訊。
    </div>

    <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
      <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
      <svg class="cm-chart" viewBox="0 0 100 100">
        <line class="cm-chart-diagonal" x1="4" y1="96" x2="96" y2="4" />
        <path class="cm-chart-line" :d="rocPath" fill="none" />
        <text class="cm-chart-tick" x="4" y="100">0</text>
        <text class="cm-chart-tick" x="50" y="100" text-anchor="middle">0.5</text>
        <text class="cm-chart-tick" x="96" y="100" text-anchor="end">1</text>
        <text class="cm-chart-tick" x="0" y="96">0</text>
        <text class="cm-chart-tick" x="0" y="50">0.5</text>
        <text class="cm-chart-tick" x="0" y="4">1</text>
      </svg>
      <div class="cm-chart-axis-x">FPR (0 – 1)</div>
      <div class="cm-chart-axis-y">TPR (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'roc' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
    </div>

    <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
      <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
      <svg class="cm-chart" viewBox="0 0 100 100">
        <path class="cm-chart-line" :d="prPath" fill="none" />
        <text class="cm-chart-tick" x="4" y="100">0</text>
        <text class="cm-chart-tick" x="50" y="100" text-anchor="middle">0.5</text>
        <text class="cm-chart-tick" x="96" y="100" text-anchor="end">1</text>
        <text class="cm-chart-tick" x="0" y="96">0</text>
        <text class="cm-chart-tick" x="0" y="50">0.5</text>
        <text class="cm-chart-tick" x="0" y="4">1</text>
      </svg>
      <div class="cm-chart-axis-x">Recall (0 – 1)</div>
      <div class="cm-chart-axis-y">Precision (0 – 1)</div>
    </div>
    <div v-else-if="activeTab === 'pr' && groupedResults.length > 0" class="summary-empty">
      此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
    </div>

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

整段包進一個新的 `.cm-tab-row` 容器，並在既有五個區塊之後、`</div>`（新容器結尾）之前加入共用的 AI 解讀面板（新容器本身用 `v-if="groupedResults.length > 0"` 包住，這樣「尚未有結果」那個獨立區塊（第 165-167 行，不動）才不會被牽連）：

```html
    <div v-if="groupedResults.length > 0" class="cm-tab-row">
      <div v-if="activeTab === 'matrix' && currentMatrix" class="cm-table-wrap">
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

      <div v-else-if="activeTab === 'matrix'" class="summary-empty">
        該抽樣沒有可用的混淆矩陣資訊。
      </div>

      <div v-if="activeTab === 'roc' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <line class="cm-chart-diagonal" x1="4" y1="96" x2="96" y2="4" />
          <path class="cm-chart-line" :d="rocPath" fill="none" />
          <text class="cm-chart-tick" x="4" y="100">0</text>
          <text class="cm-chart-tick" x="50" y="100" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="96" y="100" text-anchor="end">1</text>
          <text class="cm-chart-tick" x="0" y="96">0</text>
          <text class="cm-chart-tick" x="0" y="50">0.5</text>
          <text class="cm-chart-tick" x="0" y="4">1</text>
        </svg>
        <div class="cm-chart-axis-x">FPR (0 – 1)</div>
        <div class="cm-chart-axis-y">TPR (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'roc'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

      <div v-if="activeTab === 'pr' && currentRocPrCurve" class="cm-chart-wrap">
        <div class="cm-chart-label">正類：{{ currentRocPrCurve?.posLabel }}</div>
        <svg class="cm-chart" viewBox="0 0 100 100">
          <path class="cm-chart-line" :d="prPath" fill="none" />
          <text class="cm-chart-tick" x="4" y="100">0</text>
          <text class="cm-chart-tick" x="50" y="100" text-anchor="middle">0.5</text>
          <text class="cm-chart-tick" x="96" y="100" text-anchor="end">1</text>
          <text class="cm-chart-tick" x="0" y="96">0</text>
          <text class="cm-chart-tick" x="0" y="50">0.5</text>
          <text class="cm-chart-tick" x="0" y="4">1</text>
        </svg>
        <div class="cm-chart-axis-x">Recall (0 – 1)</div>
        <div class="cm-chart-axis-y">Precision (0 – 1)</div>
      </div>
      <div v-else-if="activeTab === 'pr'" class="summary-empty">
        此模型或此類別數不支援 ROC/PR 曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

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
      <div v-else-if="activeTab === 'calibration'" class="summary-empty">
        此模型或此類別數不支援校準曲線（僅支援二元分類，且模型需提供機率輸出），或此結果為舊版執行結果，請重新執行 Workflow。
      </div>

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
      <div v-else-if="activeTab === 'perClass'" class="summary-empty">
        該抽樣沒有可用的各類別指標資訊。
      </div>

      <div v-if="hasCurrentTabData" class="cm-insight-panel">
        <div class="cm-insight-header">AI 解讀</div>

        <p v-if="tabInsightLoading" class="cm-insight-loading">生成中...</p>

        <template v-else-if="tabInsightError">
          <p class="cm-insight-error">{{ tabInsightError }}</p>
          <button class="cm-insight-btn" type="button" @click="generateTabInsight">重試</button>
        </template>

        <template v-else-if="currentTabInsight">
          <p class="cm-insight-text">{{ currentTabInsight }}</p>
          <button class="cm-insight-btn" type="button" @click="generateTabInsight">重新生成</button>
        </template>

        <template v-else>
          <p class="cm-insight-empty">點擊下方按鈕，讓 AI 針對目前的圖表/表格生成一段解讀。</p>
          <button class="cm-insight-btn" type="button" @click="generateTabInsight">AI 解讀</button>
        </template>
      </div>
    </div>
```

**注意**：五個分頁區塊原本各自的 `v-else-if="activeTab === '...' && groupedResults.length > 0"` 空狀態條件，因為現在整組已經被外層的 `v-if="groupedResults.length > 0" class="cm-tab-row"` 包住、`groupedResults.length > 0` 恆成立，所以簡化成 `v-else-if="activeTab === '...'"`（拿掉多餘的 `&& groupedResults.length > 0`）——這是語意上的等價簡化，不是行為改變。五組 `v-if`/`v-else-if` 配對彼此依然要維持獨立（每組自己的 `v-if` 開頭，不要被前一組的 `v-else-if` 串走），這點跟包裝之前完全一樣，只是現在整組都在 `.cm-tab-row` 容器裡面。

- [ ] **Step 4: 加對應樣式**

`.summary-empty { ... }` 規則（第 662-665 行）之前新增：

```css
  .cm-tab-row {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }

  .cm-tab-row > .cm-table-wrap,
  .cm-tab-row > .cm-chart-wrap,
  .cm-tab-row > .summary-empty {
    flex: 1 1 0;
    min-width: 0;
  }

  .cm-insight-panel {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 16px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: var(--color-surface);
  }

  .cm-insight-header {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-secondary);
  }

  .cm-insight-empty,
  .cm-insight-loading,
  .cm-insight-text {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink);
    line-height: 1.6;
  }

  .cm-insight-error {
    margin: 0;
    font-size: 13px;
    color: #b91c1c;
  }

  .cm-insight-btn {
    align-self: flex-start;
    padding: 7px 14px;
    border-radius: 8px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 35%, transparent);
    background: var(--color-accent);
    color: #fff;
    font-size: 13px;
    cursor: pointer;
  }
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量跟這次改動之前一樣（這個專案目前有 50 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤，環境缺套件、跟本次改動無關），用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 50，或用 `grep -i "ConfusionMatrixPanel"` 確認輸出裡沒有這個檔案的錯誤。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add per-tab AI insight panel to ConfusionMatrixPanel"
```

---

## 完成後的人工驗證

四個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 執行一次 workflow，點「Classification Evaluation」節點，確認五個分頁都變成左右兩欄版面，左邊圖表/表格沒有跑版
2. 每個分頁右邊按一次「AI 解讀」，確認都能正常生成文字，內容跟該分頁的資料相關（不是空泛的通用文字）
3. 切換模型/fold 下拉後，同一分頁要重新按才生成（不同組合各自獨立、互不影響）；切回先前按過的組合要立刻顯示文字、不會重新打 API（可用瀏覽器 Network 分頁確認沒有新的 `/api/rag/tab-insight` 請求）
4. 重新整理頁面後，先前生成過的組合仍然能從快取立刻顯示
5. 重新套用 dataTable 欄位設定或按「繼續」後，先前所有分頁解讀的快取都要被清空（重新整理後該分頁應該回到「尚未生成」的狀態）
6. 用一個多分類資料集跑一次，切到 ROC/PR/校準曲線分頁（顯示空狀態文字的情況），確認右邊沒有出現「AI 解讀」按鈕（`hasCurrentTabData` 應該是 `false`）
