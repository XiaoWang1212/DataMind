# 分頁圖表問答（Tab Chat）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `ConfusionMatrixPanel.vue` 現有的「AI 解讀」面板下方，新增一個範圍限定在「這個分頁的圖表/表格」的多輪問答功能。

**Architecture:** 後端新增 `PaperRAGService.chat_about_tab()`（重用 `generate_tab_insight()` 抓資料的邏輯 + `chat_about_results()` 組多輪對話的寫法，但不帶 arXiv 工具）與路由 `POST /api/rag/tab-chat`；前端在 `ConfusionMatrixPanel.vue` 新增每個 (tab, model, fold) 組合各自獨立的對話狀態與 UI，比照既有 `tabInsightCache` 的 key 模式，對話紀錄存 localStorage 並跟現有的 tabInsight 快取共用同一套失效規則。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript 前端，Flask + `google.generativeai`（Gemini）後端。

## Global Constraints

- 不帶 arXiv 查詢工具——這個分頁問答只能回答跟該分頁資料直接相關的問題，範圍限制透過 system prompt 引導 AI 婉拒離題問題（軟性限制，不是關鍵字黑名單）
- 每個 (tab, model, fold) 組合各自獨立一串對話，不共用同一個對話串
- 對話紀錄存 localStorage，跟現有 `tabInsight_*` 快取共用同一套失效規則（`WorkflowWorkspace.vue` 的 `handleApplyColumnConfig()`/`handleContinueSettings()` 清除 tabInsight 快取時，一併清除 tabChat 快取）
- 後端失敗一律回傳 `{"success": false, "error": ...}` + HTTP 500（不像 `chat_about_results()` 那樣把錯誤字串包進回覆文字裡）
- 沿用既有 `_MAX_TAB_TEXT_CHARS = 4000` 截斷規則，不新增新的常數
- 後端無既有 pytest 套件覆蓋 `paper_rag.py` 的 Gemini 呼叫邏輯（`generate_tab_insight()`/`chat_about_results()` 當時都沒補測試），這次一致不新增自動化測試；前端無 vitest。兩邊都改用「語法檢查/型別檢查 + 手動驗證」

---

### Task 1: 後端新增 `chat_about_tab()` 與 `/tab-chat` 路由

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Modify: `backend/routes/rag.py`

**Interfaces:**
- Produces: `PaperRAGService.chat_about_tab(self, mining_results: dict, tab: str, model_name: str, split_name: str, history: List[dict], message: str) -> str`
- Consumes（既有，不用修改）: `self._find_tab_result()`、`self._format_tab_data()`、`self._MAX_TAB_TEXT_CHARS`、`self._model`（不帶工具的 plain `GenerativeModel`，`__init__` 第 112 行已建立）

- [ ] **Step 1: 新增 `_TAB_LABELS` 對照表與 `chat_about_tab()` 方法**

`backend/services/rag/paper_rag.py` 現有的 `_TAB_PROMPT_HINTS`（第 452-458 行）：
```python
    _TAB_PROMPT_HINTS: Dict[str, str] = {
        "matrix": "請指出模型最容易把哪個類別誤判成哪個類別，這對臨床判讀有什麼提醒。",
        "roc": "請說明這個 AUC 數值代表模型的判別力好不好，並簡述曲線形狀反映的意義。",
        "pr": "請說明在類別不平衡的情境下 PR 曲線的意義，以及這個結果顯示模型在少數類別上的表現如何。",
        "calibration": "請說明這個模型輸出的機率是否可信賴，是偏樂觀還是偏保守。",
        "perClass": "請指出表現最差的類別，並簡述可能的原因或後續建議。",
    }
```
在它之後（`_MAX_TAB_TEXT_CHARS = 4000` 那一行之前）新增：
```python

    _TAB_LABELS: Dict[str, str] = {
        "matrix": "混淆矩陣",
        "roc": "ROC 曲線",
        "pr": "PR 曲線",
        "calibration": "校準曲線",
        "perClass": "各類別指標",
    }
```

`generate_tab_insight()` 目前結尾（第 590-594 行）：
```python
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        if text.startswith("（生成失敗："):
            raise RuntimeError(text)
        return text.strip()
```
在它之後、`def score_paper(self, paper_text: str) -> dict:`（第 596 行）之前新增：
```python

    def chat_about_tab(
        self,
        mining_results: dict,
        tab: str,
        model_name: str,
        split_name: str,
        history: List[dict],
        message: str,
    ) -> str:
        """針對 workflow 結果裡某個 (model × fold) 的單一分頁資料，跟使用者進行範圍限定的多輪問答。

        跟 chat_about_results() 不同：這裡不帶 arXiv 查詢工具（用不帶 tools 的 self._model，
        不是 self._chat_model），範圍限定在這個分頁的資料，不做例外處理——Gemini 呼叫本身的
        例外、resp.text 解析例外都直接往上拋，讓路由層統一接住、回傳 success:false。
        """
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        tab_label = self._TAB_LABELS.get(tab, tab)
        context_turns = [
            {
                "role": "user",
                "parts": [
                    f"以下是這次機器學習實驗中「{tab_label}」的資料，請記住這些資訊，"
                    "之後我會針對這個圖表/表格提問。"
                    "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                    "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                    "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                    f"{tab_text}"
                ],
            },
            {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._model.start_chat(history=context_turns + prior_turns)
        resp = chat.send_message(message)
        return (getattr(resp, "text", "") or "").strip()
```

- [ ] **Step 2: 語法檢查**

Run:
```bash
docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 3: 在 `rag.py` 新增路由**

`backend/routes/rag.py` 現有的 `/tab-insight` 路由結尾（第 483-489 行）：
```python
    try:
        insight = service.generate_tab_insight(data["mining_results"], tab, model_name, split_name)
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("分頁解讀生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```
在它之後、`@rag_bp.route("/score-paper", methods=["POST"])`（第 492 行）之前新增：
```python


@rag_bp.route("/tab-chat", methods=["POST"])
def chat_about_tab():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標），進行範圍限定的多輪問答

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要問哪個模型的結果（必填）
        - split_name      : 要問哪個 fold/split（必填）
        - history         : 對話歷史 [{role: "user"|"model", text: str}]（選填，預設空陣列）
        - message         : 本輪使用者輸入（必填）

    回傳：
        - reply : AI 回覆文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    split_name = data.get("split_name")
    message = (data.get("message") or "").strip()
    if not tab or not model_name or not split_name:
        return jsonify({"success": False, "error": "tab、model_name、split_name 為必填欄位"}), 400
    if not message:
        return jsonify({"success": False, "error": "message 為必填欄位"}), 400

    history = data.get("history") or []
    service = get_paper_rag_service()

    try:
        reply = service.chat_about_tab(data["mining_results"], tab, model_name, split_name, history, message)
        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        logger.exception("分頁問答失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 4: 語法檢查**

Run:
```bash
docker cp backend/routes/rag.py datamind-backend:/tmp/rag.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/rag.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 5: 用 repro script 驗證資料處理邏輯（不打真的 Gemini API）**

Run（在 `datamind-backend` 容器內；只驗證 `chat_about_tab()` 裡「找不到結果」「該分頁無資料」這兩條不呼叫 Gemini 的提前 return 路徑，以及 `_TAB_LABELS` 對照表本身，不驗證實際跟 Gemini 對話——那部分留給最後的人工瀏覽器驗證）：
```bash
docker exec datamind-backend .venv/bin/python -c "
import sys
sys.path.insert(0, '/app')
from services.rag.paper_rag import PaperRAGService

svc = PaperRAGService.__new__(PaperRAGService)  # 跳過 __init__（不需要真的連 Gemini 就能測這幾條路徑）

mining_results = {
    'results': [
        {
            'model_name': 'RandomForest', 'split_name': 'fold_1',
            'confusion_matrix': {'labels': ['0', '1'], 'matrix': [[50, 5], [8, 37]]},
        },
    ],
}

# 找不到對應結果
reply = svc.chat_about_tab(mining_results, 'matrix', 'NoSuchModel', 'fold_1', [], '這個模型表現如何？')
assert reply == '找不到對應的結果資料。', reply
print('not-found case: OK')

# 該分頁沒有對應資料（這筆結果沒有 roc_pr_curve）
reply = svc.chat_about_tab(mining_results, 'roc', 'RandomForest', 'fold_1', [], '這個 AUC 好嗎？')
assert reply == '此分頁沒有可供解讀的資料。', reply
print('no-data case: OK')

# _TAB_LABELS 涵蓋全部 5 個分頁 key
for tab in ['matrix', 'roc', 'pr', 'calibration', 'perClass']:
    assert tab in svc._TAB_LABELS, f'{tab} missing from _TAB_LABELS'
print('_TAB_LABELS coverage: OK')

print('ALL CASES PASSED')
"
```
Expected: 印出 `not-found case: OK`、`no-data case: OK`、`_TAB_LABELS coverage: OK`、最後 `ALL CASES PASSED`，過程中沒有任何 Python traceback

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/rag/paper_rag.py backend/routes/rag.py
git commit -m "feat: add scoped per-tab chat endpoint for confusion matrix panel"
```

---

### Task 2: 前端新增 API 函式與 localStorage 函式

**Files:**
- Modify: `frontend/src/api/insight.ts`
- Modify: `frontend/src/composables/workflow/useWorkflowStorage.ts`

**Interfaces:**
- Consumes: `POST /api/rag/tab-chat`（Task 1 產生，body `{mining_results, tab, model_name, split_name, history, message}`，回傳 `{success, reply}`）
- Produces: `TabChatMessage`（`{role: 'user' | 'model', text: string}`，從 `frontend/src/api/insight.ts` 匯出）
- Produces: `fetchTabChatReply(miningResults: Record<string, unknown>, tab: string, modelName: string, splitName: string, history: TabChatMessage[], message: string): Promise<string>`
- Produces: `saveTabChatToStorage(projectId: string, modelName: string, splitName: string, tab: string, messages: TabChatMessage[]): void`
- Produces: `loadTabChatFromStorage(projectId: string, modelName: string, splitName: string, tab: string): TabChatMessage[]`
- Produces: `clearAllTabChatsFromStorage(projectId: string): void`

- [ ] **Step 1: 新增 `TabChatMessage` 型別與 `fetchTabChatReply()`**

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

在它之後新增：
```typescript

export interface TabChatMessage {
  role: 'user' | 'model'
  text: string
}

export async function fetchTabChatReply (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
  history: TabChatMessage[],
  message: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
      history,
      message,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.reply ?? '')
}
```

- [ ] **Step 2: 新增 localStorage 函式**

`useWorkflowStorage.ts` 檔案開頭的 import（第 1-2 行）：
```typescript
import type { EdgeBase, FlowNode } from '@/types/workflow'
import type { ChatMessage, StructuredAnalysis } from '@/api/resultAnalysis'
```
改成（新增一行 import）：
```typescript
import type { EdgeBase, FlowNode } from '@/types/workflow'
import type { TabChatMessage } from '@/api/insight'
import type { ChatMessage, StructuredAnalysis } from '@/api/resultAnalysis'
```

現有的 `clearAllTabInsightsFromStorage()`（第 209-222 行）：
```typescript
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
在它之後、`clearActiveJobIdFromStorage()`（第 224 行的註解）之前新增：
```typescript

const TAB_CHAT_KEY = 'tabChat'

function tabChatStorageKey (
  projectId: string, modelName: string, splitName: string, tab: string,
): string {
  return k(`${TAB_CHAT_KEY}_${tab}_${modelName}_${splitName}`, projectId)
}

export function saveTabChatToStorage (
  projectId: string, modelName: string, splitName: string, tab: string, messages: TabChatMessage[],
): void {
  const key = tabChatStorageKey(projectId, modelName, splitName, tab)
  try {
    localStorage.setItem(key, JSON.stringify(messages))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存分頁問答紀錄:', error)
  }
}

export function loadTabChatFromStorage (
  projectId: string, modelName: string, splitName: string, tab: string,
): TabChatMessage[] {
  const key = tabChatStorageKey(projectId, modelName, splitName, tab)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return []
  }
  try {
    return JSON.parse(raw) as TabChatMessage[]
  } catch (error) {
    console.error('[WF-LOAD] 分頁問答紀錄 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return []
  }
}

// 分頁問答是組合鍵（tab/model/fold 各自獨立一個 key），沒辦法像單一 key 那樣直接刪，
// 要掃描 localStorage 找出屬於這個 projectId 的全部分頁問答 key 再逐一移除
export function clearAllTabChatsFromStorage (projectId: string): void {
  const prefix = `${TAB_CHAT_KEY}_`
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

Expected: 這個專案目前有 53 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件、跟本次改動無關）。用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 53，或用 `grep -iE "insight.ts|useWorkflowStorage"` 確認輸出裡沒有這兩個檔案的錯誤。

- [ ] **Step 4: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/api/insight.ts frontend/src/composables/workflow/useWorkflowStorage.ts
git commit -m "feat: add tab chat API call and localStorage functions"
```

---

### Task 3: `WorkflowWorkspace.vue` 結果失效時一併清除分頁問答快取

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: `clearAllTabChatsFromStorage(projectId: string): void`（Task 2 產生）

- [ ] **Step 1: 加 import**

`WorkflowWorkspace.vue` 現有的 import 區塊（第 141-149 行）：
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
改成：
```typescript
  import {
    clearAllTabChatsFromStorage,
    clearAllTabInsightsFromStorage,
    clearResultInsightFromStorage,
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    loadWorkflowStateFromStorage,
    saveWorkflowDataFileToStorage,
    saveWorkflowStateToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
```

- [ ] **Step 2: 兩處清除快取的地方各加一行**

`handleApplyColumnConfig()`（第 333-344 行）：
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
```
改成（第 336-337 行之間插入一行）：
```typescript
  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    if (projectId.value) {
      clearResultInsightFromStorage(projectId.value)
      clearAllTabInsightsFromStorage(projectId.value)
      clearAllTabChatsFromStorage(projectId.value)
    }
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

`handleContinueSettings()`（第 346-354 行）：
```typescript
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
改成：
```typescript
  function handleContinueSettings (): void {
    if (projectId.value) {
      clearResultInsightFromStorage(projectId.value)
      clearAllTabInsightsFromStorage(projectId.value)
      clearAllTabChatsFromStorage(projectId.value)
    }
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量還是 53（不含 `WorkflowWorkspace.vue` 的錯誤）。

- [ ] **Step 4: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "fix: clear tab chat cache alongside tab insight cache on result invalidation"
```

---

### Task 4: `ConfusionMatrixPanel.vue` 加對話串 UI 與狀態邏輯

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue`

**Interfaces:**
- Consumes: `fetchTabChatReply`、`TabChatMessage`（`@/api/insight`）、`loadTabChatFromStorage`、`saveTabChatToStorage`（`@/composables/workflow/useWorkflowStorage.ts`，皆為 Task 2 產生）
- Consumes（既有，不用修改）: `TabKey`、`activeTab`、`selectedModel`、`selectedFold`、`tabInsightCacheKey()`、`currentTabInsightKey`、`hasCurrentTabData`

- [ ] **Step 1: import 新函式與型別**

現有的 import（第 191-195 行）：
```typescript
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { fetchTabInsight } from '@/api/insight'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import { loadTabInsightFromStorage, saveTabInsightToStorage } from '@/composables/workflow/useWorkflowStorage.ts'
```
改成：
```typescript
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { fetchTabChatReply, fetchTabInsight, type TabChatMessage } from '@/api/insight'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import {
    loadTabChatFromStorage,
    loadTabInsightFromStorage,
    saveTabChatToStorage,
    saveTabInsightToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
```

- [ ] **Step 2: 新增對話狀態與方法**

現有的 tabInsight 相關區塊結尾（第 459-514 行，watch 一路到 `}, { immediate: true })`）：
```typescript
  const tabInsightCache = ref<Map<string, string>>(new Map())
  const tabInsightLoadingKey = ref<string | null>(null)
  const tabInsightError = ref<string | null>(null)

  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }

  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value),
  )

  const currentTabInsight = computed(() =>
    tabInsightCache.value.get(currentTabInsightKey.value) ?? null,
  )

  const isCurrentTabInsightLoading = computed(() => tabInsightLoadingKey.value === currentTabInsightKey.value)

  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
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
整段改成（`generateTabInsight()` 不變，新增對話狀態/方法，並把最後的 `watch` 擴充成同時載入對話快取）：
```typescript
  const tabInsightCache = ref<Map<string, string>>(new Map())
  const tabInsightLoadingKey = ref<string | null>(null)
  const tabInsightError = ref<string | null>(null)

  function tabInsightCacheKey (tab: TabKey, model: string, fold: string): string {
    return `${tab}::${model}::${fold}`
  }

  const currentTabInsightKey = computed(() =>
    tabInsightCacheKey(activeTab.value, selectedModel.value, selectedFold.value),
  )

  const currentTabInsight = computed(() =>
    tabInsightCache.value.get(currentTabInsightKey.value) ?? null,
  )

  const isCurrentTabInsightLoading = computed(() => tabInsightLoadingKey.value === currentTabInsightKey.value)

  async function generateTabInsight (): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)

    tabInsightLoadingKey.value = key
    tabInsightError.value = null
    try {
      const insight = await fetchTabInsight(props.workflowResult, tab, model, fold)
      tabInsightCache.value = new Map(tabInsightCache.value).set(key, insight)
      saveTabInsightToStorage(props.projectId, model, fold, tab, insight)
    } catch (error) {
      tabInsightError.value = error instanceof Error ? error.message : String(error)
    } finally {
      // 只清自己那把 key 的 loading 狀態——避免使用者切到別的組合又按了一次生成，
      // 這次 finally 執行時把「新的那次」的 loading 狀態誤清掉
      if (tabInsightLoadingKey.value === key) {
        tabInsightLoadingKey.value = null
      }
    }
  }

  // 每個 (tab, model, fold) 組合各自獨立一串對話，key 格式跟 tabInsightCache 完全一樣，
  // 直接共用 tabInsightCacheKey()/currentTabInsightKey，不需要另外一套 key 邏輯
  const tabChatCache = ref<Map<string, TabChatMessage[]>>(new Map())
  const tabChatInput = ref('')
  const tabChatLoadingKey = ref<string | null>(null)
  const tabChatError = ref<string | null>(null)

  const currentTabChatMessages = computed(() =>
    tabChatCache.value.get(currentTabInsightKey.value) ?? [],
  )

  const isCurrentTabChatLoading = computed(() => tabChatLoadingKey.value === currentTabInsightKey.value)

  // 送出問題（sendTabChatMessage）跟按「重試」（retryTabChatMessage）都需要「拿 history 打 API、
  // 拿到回覆後 append 一筆 model 訊息」這段邏輯，抽成共用函式；呼叫端負責先把使用者訊息放進畫面陣列
  async function requestTabChatReply (
    tab: TabKey, model: string, fold: string, history: TabChatMessage[], text: string,
  ): Promise<void> {
    if (!props.projectId || !props.workflowResult) return
    const key = tabInsightCacheKey(tab, model, fold)

    tabChatLoadingKey.value = key
    tabChatError.value = null
    try {
      const reply = await fetchTabChatReply(props.workflowResult, tab, model, fold, history, text)
      const messages = [...(tabChatCache.value.get(key) ?? []), { role: 'model' as const, text: reply }]
      tabChatCache.value = new Map(tabChatCache.value).set(key, messages)
      saveTabChatToStorage(props.projectId, model, fold, tab, messages)
    } catch (error) {
      tabChatError.value = error instanceof Error ? error.message : String(error)
    } finally {
      if (tabChatLoadingKey.value === key) {
        tabChatLoadingKey.value = null
      }
    }
  }

  async function sendTabChatMessage (): Promise<void> {
    const text = tabChatInput.value.trim()
    if (!text || !props.projectId || !props.workflowResult) return

    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const history = tabChatCache.value.get(key) ?? []

    tabChatInput.value = ''
    tabChatCache.value = new Map(tabChatCache.value).set(key, [...history, { role: 'user' as const, text }])

    await requestTabChatReply(tab, model, fold, history, text)
  }

  // 失敗時使用者的訊息還留在畫面上（陣列最後一筆是 role:'user'），重試就是拿掉那一筆當 history、
  // 用同一則訊息內容再打一次 API，不會讓使用者的問題重複出現在 history 裡
  function retryTabChatMessage (): void {
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    const messages = tabChatCache.value.get(key) ?? []
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'user') return
    const history = messages.slice(0, -1)
    void requestTabChatReply(tab, model, fold, history, lastMessage.text)
  }

  // 切換分頁/模型/fold 時，如果 localStorage 已經有這個組合的快取就直接顯示，不用重新打 API
  watch([activeTab, selectedModel, selectedFold], () => {
    tabInsightError.value = null
    tabChatError.value = null
    tabChatInput.value = ''
    if (!props.projectId) return
    const tab = activeTab.value
    const model = selectedModel.value
    const fold = selectedFold.value
    const key = tabInsightCacheKey(tab, model, fold)
    if (!tabInsightCache.value.has(key)) {
      const cached = loadTabInsightFromStorage(props.projectId, model, fold, tab)
      if (cached !== null) {
        tabInsightCache.value = new Map(tabInsightCache.value).set(key, cached)
      }
    }
    if (!tabChatCache.value.has(key)) {
      const cachedChat = loadTabChatFromStorage(props.projectId, model, fold, tab)
      if (cachedChat.length > 0) {
        tabChatCache.value = new Map(tabChatCache.value).set(key, cachedChat)
      }
    }
  }, { immediate: true })
```

- [ ] **Step 3: Template — 在 `.cm-insight-panel` 下方加對話區塊**

現有的 `.cm-insight-panel`（第 163-182 行）：
```html
      <div v-if="hasCurrentTabData" class="cm-insight-panel">
        <div class="cm-insight-header">AI 解讀</div>

        <p v-if="isCurrentTabInsightLoading" class="cm-insight-loading">生成中...</p>

        <template v-else-if="tabInsightError">
          <p class="cm-insight-error">{{ tabInsightError }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重試</button>
        </template>

        <template v-else-if="currentTabInsight">
          <p class="cm-insight-text">{{ currentTabInsight }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重新生成</button>
        </template>

        <template v-else>
          <p class="cm-insight-empty">點擊下方按鈕，讓 AI 針對目前的圖表/表格生成一段解讀。</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">AI 解讀</button>
        </template>
      </div>
```
改成（`</template>` 之後、`</div>` 之前插入對話區塊）：
```html
      <div v-if="hasCurrentTabData" class="cm-insight-panel">
        <div class="cm-insight-header">AI 解讀</div>

        <p v-if="isCurrentTabInsightLoading" class="cm-insight-loading">生成中...</p>

        <template v-else-if="tabInsightError">
          <p class="cm-insight-error">{{ tabInsightError }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重試</button>
        </template>

        <template v-else-if="currentTabInsight">
          <p class="cm-insight-text">{{ currentTabInsight }}</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">重新生成</button>
        </template>

        <template v-else>
          <p class="cm-insight-empty">點擊下方按鈕，讓 AI 針對目前的圖表/表格生成一段解讀。</p>
          <button class="cm-insight-btn" :disabled="!props.projectId" type="button" @click="generateTabInsight">AI 解讀</button>
        </template>

        <div class="cm-chat-divider" />

        <div class="cm-chat-thread">
          <p v-if="currentTabChatMessages.length === 0" class="cm-chat-empty">
            針對這個圖表/表格有任何問題，都可以在下方提問。
          </p>
          <div
            v-for="(msg, index) in currentTabChatMessages"
            :key="index"
            class="cm-chat-bubble"
            :class="`cm-chat-bubble--${msg.role}`"
          >
            <p class="cm-chat-bubble-text">{{ msg.text }}</p>
          </div>
          <p v-if="isCurrentTabChatLoading" class="cm-insight-loading">AI 思考中...</p>
          <template v-if="tabChatError">
            <p class="cm-insight-error">{{ tabChatError }}</p>
            <button
              class="cm-insight-btn"
              :disabled="!props.projectId || isCurrentTabChatLoading"
              type="button"
              @click="retryTabChatMessage"
            >
              重試
            </button>
          </template>
        </div>

        <form class="cm-chat-input-row" @submit.prevent="sendTabChatMessage">
          <input
            v-model="tabChatInput"
            class="cm-chat-input"
            type="text"
            placeholder="針對這個圖表提問..."
            :disabled="!props.projectId || isCurrentTabChatLoading"
          >
          <button
            class="cm-insight-btn"
            type="submit"
            :disabled="!props.projectId || isCurrentTabChatLoading || !tabChatInput.trim()"
          >
            送出
          </button>
        </form>
      </div>
```

- [ ] **Step 4: 加對話區塊的樣式**

現有的 `.cm-insight-btn`（第 802-811 行）：
```css
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
在它之後、`.summary-empty`（第 813 行）之前新增：
```css

  .cm-chat-divider {
    height: 1px;
    background: rgba(148, 163, 184, 0.22);
  }

  .cm-chat-thread {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .cm-chat-empty {
    margin: 0;
    font-size: 12px;
    color: var(--color-secondary);
  }

  .cm-chat-bubble {
    max-width: 90%;
    padding: 6px 10px;
    border-radius: 10px;
    background: color-mix(in oklab, var(--color-accent) 8%, transparent);
  }

  .cm-chat-bubble--user {
    align-self: flex-end;
    background: color-mix(in oklab, var(--color-accent) 16%, transparent);
  }

  .cm-chat-bubble--model {
    align-self: flex-start;
  }

  .cm-chat-bubble-text {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink);
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .cm-chat-input-row {
    display: flex;
    gap: 8px;
  }

  .cm-chat-input {
    flex: 1;
    padding: 7px 10px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: var(--color-surface);
    color: var(--color-ink);
    font-size: 13px;
  }

  .cm-chat-input:focus {
    outline: none;
    border-color: var(--color-accent);
  }
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 錯誤數量還是 53（不含 `ConfusionMatrixPanel.vue` 的錯誤）。用 `npm run type-check 2>&1 | grep -c "error TS"` 確認，或 `grep -i "ConfusionMatrixPanel"` 確認輸出裡沒有這個檔案。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/ConfusionMatrixPanel.vue
git commit -m "feat: add scoped chat thread to confusion matrix AI insight panel"
```

---

## 完成後的人工驗證

四個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（後端/前端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 任一分頁按「AI 解讀」拿到解讀文字後，在下方輸入框問一個追問（例如「這個數字算好還是不好？」），確認能拿到回覆，且回覆內容看起來跟這個分頁的資料相關
2. 問一個明顯離題的問題（例如「今天天氣如何」），確認 AI 有禮貌地說明只能討論這個分頁內容，而不是隨意作答
3. 問一個「有沒有論文佐證」的文獻查詢問題，確認 AI 不會嘗試查 arXiv（這個分頁對話沒帶工具），回覆內容裡沒有論文卡片
4. 切到另一個分頁再切回來，確認先前的問答紀錄還在
5. 重新整理頁面，確認問答紀錄還在
6. 修改 dataTable 欄位設定並確認中斷重跑，確認先前分頁的問答紀錄被清空
7. 兩個不同分頁分別問不同問題，確認彼此的對話不會混在一起
8. 沒有 `projectId`（理論上正常流程不會發生）時，確認輸入框/送出按鈕維持 disabled
