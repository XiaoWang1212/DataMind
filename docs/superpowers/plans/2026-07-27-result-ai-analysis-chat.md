# Result 頁面 AI 分析與對話功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `ResultView.vue`（`/hub/projects/:id/result`）加入兩個新功能：(1) 進頁面自動生成的結構化 AI 分析（模型比較、資料洞察、風險提示、後續建議四個面向），(2) 可跟 AI 多輪對話的區塊，AI 可自主判斷是否需要用 Gemini function calling 查詢 arXiv 論文並在回覆中附上可點擊的論文卡片。

**Architecture:** 沿用專案既有的無狀態後端模式（跟 `/api/rag/insight`、`/api/rag/generate-paper` 一致）：前端每次呼叫都把完整 `mining_results`（以及對話歷史）傳給後端，後端不儲存任何 session 狀態；對話歷史與結構化分析結果由前端存進 `localStorage`（沿用 `workflowState_<projectId>` 的按 projectId 分 key 模式）。後端 `PaperRAGService` 新增兩個方法：`generate_structured_analysis`（用 Gemini JSON 輸出模式）與 `chat_about_results`（用 Gemini function calling，工具是查 arXiv 的 `search_arxiv`）。

**Tech Stack:** Flask blueprint（`backend/routes/rag.py`）、`google.generativeai` 0.8.6（`GenerativeModel.start_chat` + function calling + `response_mime_type: application/json`）、Vue 3 `<script setup>` + TypeScript、`localStorage`。

## Global Constraints

- 後端沒有 pytest 測試套件涵蓋 `paper_rag.py`／`rag.py`（`backend/scripts/test_*.py` 都是手動執行腳本，不是 pytest）。本計畫用「透過 `docker exec -w /app datamind-backend uv run python3 -c "..."` 直接呼叫新方法驗證」+ 「對執行中的 Docker backend 做 `curl` 端對端測試」取代自動化測試步驟。
- 前端沒有 vitest/jest 等測試框架；每個前端 task 用 `npm run type-check`（在 `frontend/` 目錄下執行，即 `vue-tsc --build --force`）驗證型別正確，最後一個 task 額外跑 `npm run build`，並輔以手動瀏覽器操作驗證行為。
- Python 檔案風格照 `paper_rag.py`／`rag.py` 現有風格：雙引號字串、標準 4 空白縮排、method docstring 用中文說明。
- 前端檔案風格照 `useWorkflowStorage.ts`／`ResultView.vue` 現有風格：單引號、無分號、2 空白縮排、函式簽名 `functionName (args)` 中間留空格。
- 對話中的 arXiv 搜尋一律用即時查詢（`arxiv_source.search_arxiv`），不寫入向量庫、不呼叫 `classify_topic`（AI 在對話中自己決定查詢字串）。
- 一輪對話最多觸發一次 arXiv 搜尋（不支援多輪 function call 迴圈）；不做串流回覆；不做清除對話紀錄的 UI。
- 本次改動範圍僅限 `ResultView.vue`（`/hub/projects/:id/result`），不動 `ResultsPage.vue`（`/results`）。

---

## Task 1: 後端 — 結構化 AI 分析

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Modify: `backend/routes/rag.py`

**Interfaces:**
- Produces: `PaperRAGService.generate_structured_analysis(mining_results: dict) -> dict`，回傳固定四個字串欄位 `{"model_comparison": str, "data_insights": str, "risks": str, "recommendations": str}`（缺欄位補空字串，不拋例外）。
- Produces: `POST /api/rag/structured-analysis`，body `{"mining_results": dict}`，回傳 `{"success": true, "analysis": {...上面四個欄位}}` 或 `{"success": false, "error": str}`（500）。

- [ ] **Step 1: 在 `paper_rag.py` 加入 `json` import**

Modify `backend/services/rag/paper_rag.py:9-15`：

Old:
```python
import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
```

New:
```python
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
```

- [ ] **Step 2: 加入 `generate_structured_analysis` 方法**

Modify `backend/services/rag/paper_rag.py`，緊接在既有 `generate_insight` 方法（第 327-339 行附近）之後插入：

```python
    def generate_structured_analysis(self, mining_results: dict) -> dict:
        """讀 mining_results 摘要，用 Gemini 生成四個面向的結構化分析，供 ResultView.vue 顯示。"""
        results_text = self._format_datamind_output(mining_results)
        prompt = (
            "你是資料科學顧問。請根據以下機器學習實驗結果，"
            "用繁體中文分別針對四個面向各寫一段簡短分析（每段約 2 到 4 句話）：\n"
            "1. model_comparison：模型表現比較與選擇建議（哪個模型最好、為什麼、實務上該選哪個）\n"
            "2. data_insights：資料與特徵層面的洞察（哪些前處理／特徵工程步驟影響最大、資料品質相關發現）\n"
            "3. risks：風險與限制提示（例如樣本數、過擬合疑慮、指標本身的侷限性）\n"
            "4. recommendations：後續建議行動（建議再嘗試的模型/參數、建議收集的資料、下一步分析方向）\n\n"
            f"【機器學習實驗結果】\n{results_text}\n\n"
            "請輸出 JSON，格式如下（只輸出 JSON，不要有其他文字）：\n"
            '{"model_comparison": "...", "data_insights": "...", "risks": "...", "recommendations": "..."}'
        )

        try:
            resp = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(resp, "text", "") or ""
            data = json.loads(text)
        except Exception as e:
            logger.error("結構化分析生成失敗：%s", e)
            data = {}

        return {
            "model_comparison": str(data.get("model_comparison", "")),
            "data_insights": str(data.get("data_insights", "")),
            "risks": str(data.get("risks", "")),
            "recommendations": str(data.get("recommendations", "")),
        }
```

- [ ] **Step 3: 加入 `/structured-analysis` route**

Modify `backend/routes/rag.py`，緊接在既有 `/insight` route（檔案最後，第 428-452 行）之後插入：

```python
@rag_bp.route("/structured-analysis", methods=["POST"])
def structured_analysis():
    """根據 DataMind 探勘結果，用 Gemini 生成結構化分析（模型比較、資料洞察、風險、建議）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - analysis : { model_comparison, data_insights, risks, recommendations }
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        analysis = service.generate_structured_analysis(data["mining_results"])
        return jsonify({"success": True, "analysis": analysis})

    except Exception as e:
        logger.exception("結構化分析生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 4: 驗證 — 直接呼叫 service 方法**

Run:
```bash
docker exec -w /app datamind-backend uv run python3 -c "
from services.rag.paper_rag import get_paper_rag_service

mining_results = {
    'results': [
        {'model_name': 'RandomForest', 'preprocess_pipeline_index': 0, 'preprocess_steps': [{'type': 'StandardScaler'}], 'feature_engineering_steps': [], 'metrics': [{'metric': 'accuracy', 'value': 0.87}, {'metric': 'f1', 'value': 0.85}]},
        {'model_name': 'LogisticRegression', 'preprocess_pipeline_index': 0, 'preprocess_steps': [{'type': 'StandardScaler'}], 'feature_engineering_steps': [], 'metrics': [{'metric': 'accuracy', 'value': 0.79}, {'metric': 'f1', 'value': 0.77}]},
    ],
}

service = get_paper_rag_service()
analysis = service.generate_structured_analysis(mining_results)
assert set(analysis.keys()) == {'model_comparison', 'data_insights', 'risks', 'recommendations'}, analysis
assert all(isinstance(v, str) and len(v) > 0 for v in analysis.values()), analysis
print('SUCCESS')
print(analysis)
"
```
Expected: 輸出 `SUCCESS`，接著印出四個欄位皆為非空繁體中文段落的 dict，沒有 traceback。

- [ ] **Step 5: 驗證 — curl 打對執行中的 backend**

Run:
```bash
curl -s -X POST http://localhost:5001/api/rag/structured-analysis \
  -H "Content-Type: application/json" \
  -d '{"mining_results": {"results": [{"model_name": "RandomForest", "preprocess_pipeline_index": 0, "preprocess_steps": [{"type": "StandardScaler"}], "feature_engineering_steps": [], "metrics": [{"metric": "accuracy", "value": 0.87}]}]}}'
```
Expected: HTTP 200，JSON `{"success": true, "analysis": {"model_comparison": "...", "data_insights": "...", "risks": "...", "recommendations": "..."}}`（四個欄位皆非空字串）。若連不上 `localhost:5001`，改用 docker network 內部位址或詢問使用者目前 backend 對外的 port。

- [ ] **Step 6: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/routes/rag.py
git commit -m "feat: add structured AI analysis for result page"
```

---

## Task 2: 後端 — AI 對話功能（含 arXiv function calling）

**Files:**
- Modify: `backend/services/rag/paper_rag.py`

**Interfaces:**
- Consumes: `arxiv_source.search_arxiv(query: str, max_results: int = 8) -> List[dict]`（已存在，`backend/services/rag/arxiv_source.py:18`，每筆 `{arxiv_id, title, authors, year, abstract, pdf_url}`）。
- Produces: `PaperRAGService.chat_about_results(mining_results: dict, history: List[dict], message: str) -> dict`，`history` 為 `[{"role": "user"|"model", "text": str}]`，回傳 `{"reply": str, "papers": List[dict]}`（`papers` 只有本輪真的觸發 arXiv 搜尋時才非空）。
- Produces: `POST /api/rag/chat`，body `{"mining_results": dict, "history": [...], "message": str}`，回傳 `{"success": true, "reply": str, "papers": [...]}` 或 `{"success": false, "error": str}`（500）。

- [ ] **Step 1: 在 `__init__` 建立帶 `search_arxiv` 工具的 chat 專用 model**

Modify `backend/services/rag/paper_rag.py:64-84`（`__init__` 方法）：

Old（第 69-71 行）：
```python
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._model = genai.GenerativeModel(model_name=model_name)
```

New：
```python
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._model = genai.GenerativeModel(model_name=model_name)

        search_arxiv_declaration = genai.protos.FunctionDeclaration(
            name="search_arxiv",
            description=(
                "搜尋 arXiv 上跟指定關鍵字相關的論文，回傳候選論文清單"
                "（標題、作者、年份、摘要、PDF連結）。當使用者的問題涉及"
                "「有沒有相關文獻／論文」「這個發現有沒有學術支持」之類需要"
                "查詢外部學術論文佐證的問題時才呼叫。"
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "query": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="英文搜尋關鍵字，適合直接拿去查 arXiv",
                    ),
                },
                required=["query"],
            ),
        )
        self._chat_model = genai.GenerativeModel(
            model_name=model_name,
            tools=[genai.protos.Tool(function_declarations=[search_arxiv_declaration])],
        )
```

- [ ] **Step 2: 加入 `chat_about_results` 方法**

Modify `backend/services/rag/paper_rag.py`，緊接在 Task 1 加入的 `generate_structured_analysis` 方法之後插入：

```python
    def chat_about_results(self, mining_results: dict, history: List[dict], message: str) -> dict:
        """跟使用者針對 mining_results 進行多輪對話，AI 可自主呼叫 search_arxiv 工具查詢文獻。"""
        results_text = self._format_datamind_output(mining_results)
        context_turns = [
            {
                "role": "user",
                "parts": [
                    "以下是這次機器學習實驗的資料探勘結果，請記住這些資訊，"
                    "之後我會針對這份結果提問，如果我問到跟學術文獻相關的問題，"
                    "你可以呼叫 search_arxiv 工具查詢 arXiv 上的相關論文。\n\n"
                    f"【機器學習實驗結果】\n{results_text}"
                ],
            },
            {"role": "model", "parts": ["好的，我已經了解這次實驗結果，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._chat_model.start_chat(history=context_turns + prior_turns)

        try:
            resp = chat.send_message(message)
        except Exception as e:
            logger.error("對話生成失敗：%s", e)
            return {"reply": f"（對話發生錯誤：{e}）", "papers": []}

        function_call = None
        for part in resp.parts:
            if part.function_call and part.function_call.name:
                function_call = part.function_call
                break

        papers: List[dict] = []
        if function_call is not None:
            query = str(function_call.args.get("query", ""))
            try:
                papers = arxiv_source.search_arxiv(query, max_results=5)
                function_result: dict = {"result": papers}
            except Exception as e:
                logger.warning("對話中 arXiv 搜尋失敗：%s", e)
                papers = []
                function_result = {"error": f"查詢 arXiv 時發生錯誤：{e}"}

            function_response_part = genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_call.name,
                    response=function_result,
                )
            )
            try:
                resp = chat.send_message(function_response_part)
            except Exception as e:
                logger.error("對話生成失敗（function response 後）：%s", e)
                return {"reply": f"（對話發生錯誤：{e}）", "papers": papers}

        return {"reply": (getattr(resp, "text", "") or "").strip(), "papers": papers}
```

- [ ] **Step 3: 加入 `/chat` route**

Modify `backend/routes/rag.py`，緊接在 Task 1 加入的 `/structured-analysis` route 之後插入：

```python
@rag_bp.route("/chat", methods=["POST"])
def chat():
    """跟 AI 對話，針對 mining_results 提問，AI 可自主查詢 arXiv 論文

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - history         : 對話歷史 [{role: "user"|"model", text: str}]（選填，預設空陣列）
        - message         : 本輪使用者輸入（必填）

    回傳：
        - reply  : AI 回覆文字
        - papers : 本輪若觸發 arXiv 搜尋，附上候選論文清單；否則為空陣列
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "message 為必填欄位"}), 400

    history = data.get("history") or []

    service = get_paper_rag_service()

    try:
        result = service.chat_about_results(data["mining_results"], history, message)
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.exception("對話失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 4: 驗證 — 直接呼叫 service 方法（不觸發搜尋）**

Run:
```bash
docker exec -w /app datamind-backend uv run python3 -c "
from services.rag.paper_rag import get_paper_rag_service

mining_results = {
    'results': [
        {'model_name': 'RandomForest', 'preprocess_pipeline_index': 0, 'preprocess_steps': [{'type': 'StandardScaler'}], 'feature_engineering_steps': [], 'metrics': [{'metric': 'accuracy', 'value': 0.87}]},
    ],
}

service = get_paper_rag_service()
result = service.chat_about_results(mining_results, [], '我的模型準確率是多少？')
assert isinstance(result['reply'], str) and len(result['reply']) > 0, result
assert result['papers'] == [], result
print('SUCCESS (no search branch)')
print(result)
"
```
Expected: 輸出 `SUCCESS (no search branch)`，`reply` 提到 0.87，`papers` 為空 list，沒有 traceback。

- [ ] **Step 5: 驗證 — 直接呼叫 service 方法（觸發 arXiv 搜尋）**

Run:
```bash
docker exec -w /app datamind-backend uv run python3 -c "
from services.rag.paper_rag import get_paper_rag_service

mining_results = {
    'results': [
        {'model_name': 'RandomForest', 'preprocess_pipeline_index': 0, 'preprocess_steps': [{'type': 'StandardScaler'}], 'feature_engineering_steps': [], 'metrics': [{'metric': 'accuracy', 'value': 0.87}]},
    ],
}

service = get_paper_rag_service()
result = service.chat_about_results(mining_results, [], '有沒有相關的學術論文可以佐證隨機森林這種表現？')
assert isinstance(result['reply'], str) and len(result['reply']) > 0, result
print('papers count:', len(result['papers']))
print('SUCCESS (search branch attempted)')
print(result['reply'][:200])
"
```
Expected: 輸出 `SUCCESS (search branch attempted)`，沒有 traceback。`papers count` 通常 > 0（實際是否觸發搜尋取決於 Gemini 當下判斷，只要沒有例外、`reply` 非空即算通過；若這次沒觸發也沒關係，Step 4 已驗證核心對話能力，這步主要驗證 function-calling 分支程式碼路徑沒有寫錯）。

- [ ] **Step 6: 驗證 — curl 打對執行中的 backend**

Run:
```bash
curl -s -X POST http://localhost:5001/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"mining_results": {"results": [{"model_name": "RandomForest", "preprocess_pipeline_index": 0, "preprocess_steps": [{"type": "StandardScaler"}], "feature_engineering_steps": [], "metrics": [{"metric": "accuracy", "value": 0.87}]}]}, "history": [], "message": "我的模型準確率是多少？"}'
```
Expected: HTTP 200，JSON `{"success": true, "reply": "...", "papers": [...]}`。

- [ ] **Step 7: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/routes/rag.py
git commit -m "feat: add AI chat with arXiv function calling for result page"
```

---

## Task 3: 前端 — API client 與 localStorage 持久化

**Files:**
- Create: `frontend/src/api/resultAnalysis.ts`
- Modify: `frontend/src/composables/workflow/useWorkflowStorage.ts`

**Interfaces:**
- Consumes: `ArxivCandidate` from `@/api/arxiv`（已存在，`{arxiv_id, title, authors, year, abstract, pdf_url}`）。
- Produces: `fetchStructuredAnalysis(miningResults: Record<string, unknown>): Promise<StructuredAnalysis>`，`StructuredAnalysis { model_comparison: string, data_insights: string, risks: string, recommendations: string }`。
- Produces: `sendChatMessage(miningResults: Record<string, unknown>, history: ChatMessage[], message: string): Promise<ChatReply>`，`ChatMessage { role: 'user' | 'model', text: string }`，`ChatReply { reply: string, papers: ArxivCandidate[] }`。
- Produces: `saveStructuredAnalysisToStorage(projectId: string, analysis: StructuredAnalysis): void` / `loadStructuredAnalysisFromStorage(projectId: string): StructuredAnalysis | null`。
- Produces: `saveChatHistoryToStorage(projectId: string, history: ChatMessage[]): void` / `loadChatHistoryFromStorage(projectId: string): ChatMessage[]`（無資料回傳空陣列，不是 null）。

- [ ] **Step 1: 建立 `frontend/src/api/resultAnalysis.ts`**

```ts
import type { ArxivCandidate } from '@/api/arxiv'

export interface StructuredAnalysis {
  model_comparison: string
  data_insights: string
  risks: string
  recommendations: string
}

export async function fetchStructuredAnalysis (miningResults: Record<string, unknown>): Promise<StructuredAnalysis> {
  const response = await fetch('/api/rag/structured-analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  const analysis = (result.analysis ?? {}) as Record<string, unknown>
  return {
    model_comparison: String(analysis.model_comparison ?? ''),
    data_insights: String(analysis.data_insights ?? ''),
    risks: String(analysis.risks ?? ''),
    recommendations: String(analysis.recommendations ?? ''),
  }
}

export interface ChatMessage {
  role: 'user' | 'model'
  text: string
}

export interface ChatReply {
  reply: string
  papers: ArxivCandidate[]
}

export async function sendChatMessage (
  miningResults: Record<string, unknown>,
  history: ChatMessage[],
  message: string,
): Promise<ChatReply> {
  const response = await fetch('/api/rag/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults, history, message }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return {
    reply: String(result.reply ?? ''),
    papers: Array.isArray(result.papers) ? result.papers as ArxivCandidate[] : [],
  }
}
```

- [ ] **Step 2: 在 `useWorkflowStorage.ts` 加入 import**

Modify `frontend/src/composables/workflow/useWorkflowStorage.ts:1`：

Old:
```ts
import type { EdgeBase, FlowNode } from '@/types/workflow'
```

New:
```ts
import type { EdgeBase, FlowNode } from '@/types/workflow'
import type { ChatMessage, StructuredAnalysis } from '@/api/resultAnalysis'
```

- [ ] **Step 3: 加入結構化分析與對話紀錄的 storage 函式**

Modify `frontend/src/composables/workflow/useWorkflowStorage.ts`，緊接在既有 `clearActiveJobIdFromStorage` 函式（檔案最後，第 181-194 行）之後插入：

```ts
const STRUCTURED_ANALYSIS_KEY = 'structuredAnalysis'

export function saveStructuredAnalysisToStorage (projectId: string, analysis: StructuredAnalysis): void {
  const key = k(STRUCTURED_ANALYSIS_KEY, projectId)
  try {
    localStorage.setItem(key, JSON.stringify(analysis))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存結構化分析:', error)
  }
}

export function loadStructuredAnalysisFromStorage (projectId: string): StructuredAnalysis | null {
  const key = k(STRUCTURED_ANALYSIS_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as StructuredAnalysis
  } catch (error) {
    console.error('[WF-LOAD] 結構化分析 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return null
  }
}

const CHAT_HISTORY_KEY = 'chatHistory'

export function saveChatHistoryToStorage (projectId: string, history: ChatMessage[]): void {
  const key = k(CHAT_HISTORY_KEY, projectId)
  try {
    localStorage.setItem(key, JSON.stringify(history))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存對話紀錄:', error)
  }
}

export function loadChatHistoryFromStorage (projectId: string): ChatMessage[] {
  const key = k(CHAT_HISTORY_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return []
  }
  try {
    return JSON.parse(raw) as ChatMessage[]
  } catch (error) {
    console.error('[WF-LOAD] 對話紀錄 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return []
  }
}
```

- [ ] **Step 4: 型別檢查**

Run（在 `frontend/` 目錄下執行）:
```bash
npm run type-check
```
Expected: 無錯誤輸出，結束碼 0。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/resultAnalysis.ts frontend/src/composables/workflow/useWorkflowStorage.ts
git commit -m "feat: add API client and localStorage persistence for result AI features"
```

---

## Task 4: 前端 — `ResultView.vue` UI 整合

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue`

**Interfaces:**
- Consumes（來自 Task 3）: `fetchStructuredAnalysis`、`sendChatMessage`、`StructuredAnalysis`、`ChatMessage`、`ChatReply`（from `@/api/resultAnalysis`）；`saveStructuredAnalysisToStorage`、`loadStructuredAnalysisFromStorage`、`saveChatHistoryToStorage`、`loadChatHistoryFromStorage`（from `@/composables/workflow/useWorkflowStorage`）。
- Consumes: `ArxivCandidate` from `@/api/arxiv`（`{arxiv_id, title, authors, year, abstract, pdf_url}`，已存在）。

- [ ] **Step 1: 擴充 `<script setup>` 的 import**

Modify `frontend/src/views/hub/ResultView.vue:69-74`：

Old:
```ts
  import { computed } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useProjectStore } from '@/store/projectStore'
  import { summarizeWorkflowResult, type ModelMetricSummary } from '@/utils/workflow/summarizeWorkflowResult'
```

New:
```ts
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import type { ArxivCandidate } from '@/api/arxiv'
  import { fetchStructuredAnalysis, sendChatMessage, type ChatMessage, type StructuredAnalysis } from '@/api/resultAnalysis'
  import {
    loadChatHistoryFromStorage,
    loadStructuredAnalysisFromStorage,
    loadWorkflowStateFromStorage,
    saveChatHistoryToStorage,
    saveStructuredAnalysisToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
  import { useProjectStore } from '@/store/projectStore'
  import { summarizeWorkflowResult, type ModelMetricSummary } from '@/utils/workflow/summarizeWorkflowResult'
```

- [ ] **Step 2: 加入結構化分析的 state 與載入邏輯**

Modify `frontend/src/views/hub/ResultView.vue`，緊接在既有 `metricValue` 函式（第 155-160 行）之後插入：

```ts
  interface DisplayChatMessage extends ChatMessage {
    papers?: ArxivCandidate[]
  }

  const analysis = ref<StructuredAnalysis | null>(null)
  const analysisLoading = ref(false)
  const analysisError = ref<string | null>(null)

  async function loadAnalysis (): Promise<void> {
    const cached = loadStructuredAnalysisFromStorage(projectId.value)
    if (cached) {
      analysis.value = cached
      return
    }

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return

    analysisLoading.value = true
    analysisError.value = null
    try {
      analysis.value = await fetchStructuredAnalysis(miningResult)
      saveStructuredAnalysisToStorage(projectId.value, analysis.value)
    } catch (error) {
      analysisError.value = error instanceof Error ? error.message : String(error)
    } finally {
      analysisLoading.value = false
    }
  }

  const chatMessages = ref<DisplayChatMessage[]>([])
  const chatInput = ref('')
  const chatLoading = ref(false)
  const chatError = ref<string | null>(null)

  async function sendMessage (): Promise<void> {
    const text = chatInput.value.trim()
    if (!text || chatLoading.value) return

    const miningResult = loadWorkflowStateFromStorage(projectId.value)?.workflowResult
    if (!miningResult) return

    chatMessages.value.push({ role: 'user', text })
    chatInput.value = ''
    chatLoading.value = true
    chatError.value = null

    try {
      const historyForApi: ChatMessage[] = chatMessages.value
        .slice(0, -1)
        .map(m => ({ role: m.role, text: m.text }))
      const { reply, papers } = await sendChatMessage(miningResult, historyForApi, text)
      chatMessages.value.push({ role: 'model', text: reply, papers: papers.length > 0 ? papers : undefined })
      saveChatHistoryToStorage(projectId.value, chatMessages.value)
    } catch (error) {
      chatError.value = error instanceof Error ? error.message : String(error)
    } finally {
      chatLoading.value = false
    }
  }

  onMounted(() => {
    if (summary.value.length === 0) return
    loadAnalysis()
    chatMessages.value = loadChatHistoryFromStorage(projectId.value) as DisplayChatMessage[]
  })
```

- [ ] **Step 3: 在模板加入 AI 結構化分析與對話區塊**

Modify `frontend/src/views/hub/ResultView.vue:39-65`（`.comparison-card` 區塊結尾到 `</template>` 之間）：

Old（第 62-65 行）：
```html
          </table>
        </div>
      </section>
    </template>
```

New：
```html
          </table>
        </div>
      </section>

      <section v-if="analysisLoading || analysisError || analysis" class="analysis-card">
        <div class="analysis-header">
          <div class="analysis-icon-wrap">
            <v-icon icon="mdi-shimmer" size="18" />
          </div>
          <h2 class="analysis-title">AI 結構化分析</h2>
        </div>

        <p v-if="analysisLoading" class="analysis-loading">正在生成分析...</p>
        <template v-else-if="analysisError">
          <p class="analysis-error">分析生成失敗：{{ analysisError }}</p>
          <button class="analysis-retry-btn" type="button" @click="loadAnalysis">重試</button>
        </template>
        <div v-else-if="analysis" class="analysis-grid">
          <article class="analysis-block">
            <h3>模型比較與選擇建議</h3>
            <p>{{ analysis.model_comparison }}</p>
          </article>
          <article class="analysis-block">
            <h3>資料與特徵層面洞察</h3>
            <p>{{ analysis.data_insights }}</p>
          </article>
          <article class="analysis-block">
            <h3>風險與限制提示</h3>
            <p>{{ analysis.risks }}</p>
          </article>
          <article class="analysis-block">
            <h3>後續建議行動</h3>
            <p>{{ analysis.recommendations }}</p>
          </article>
        </div>
      </section>

      <section class="chat-card">
        <div class="analysis-header">
          <div class="analysis-icon-wrap">
            <v-icon icon="mdi-chat-processing-outline" size="18" />
          </div>
          <h2 class="analysis-title">與 AI 對話</h2>
        </div>

        <div class="chat-messages">
          <p v-if="chatMessages.length === 0" class="chat-empty">針對這份結果有任何問題，都可以在下方提問。</p>
          <div
            v-for="(msg, index) in chatMessages"
            :key="index"
            class="chat-bubble"
            :class="msg.role === 'user' ? 'chat-bubble--user' : 'chat-bubble--model'"
          >
            <p class="chat-bubble-text">{{ msg.text }}</p>
            <div v-if="msg.papers && msg.papers.length > 0" class="chat-papers">
              <a
                v-for="paper in msg.papers"
                :key="paper.arxiv_id"
                class="chat-paper-card"
                :href="paper.pdf_url"
                rel="noopener noreferrer"
                target="_blank"
              >
                <p class="chat-paper-title">{{ paper.title }}</p>
                <p class="chat-paper-meta">{{ paper.authors }}<span v-if="paper.year">（{{ paper.year }}）</span></p>
              </a>
            </div>
          </div>
          <p v-if="chatLoading" class="chat-loading">AI 思考中...</p>
          <p v-if="chatError" class="chat-error">傳送失敗：{{ chatError }}</p>
        </div>

        <form class="chat-input-row" @submit.prevent="sendMessage">
          <input
            v-model="chatInput"
            class="chat-input"
            :disabled="chatLoading"
            placeholder="針對這份結果提問..."
            type="text"
          >
          <button class="chat-send-btn" :disabled="chatLoading || !chatInput.trim()" type="submit">
            送出
          </button>
        </form>
      </section>
    </template>
```

- [ ] **Step 4: 加入對應的 CSS**

Modify `frontend/src/views/hub/ResultView.vue`，在 `<style scoped>` 區塊內、`.score-best` 規則（第 334-337 行）之後、`@media (max-width: 1260px)` 之前插入：

```css
.analysis-card,
.chat-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  padding: 18px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.analysis-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #eef1ff;
  color: #2347c5;
}

.analysis-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.analysis-loading {
  margin: 0;
  font-size: 13px;
  color: #6f7480;
}

.analysis-error {
  margin: 0 0 8px;
  font-size: 13px;
  color: #d64545;
}

.analysis-retry-btn {
  border: none;
  background: none;
  color: #2347c5;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-block h3 {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #20232a;
}

.analysis-block p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5160;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.chat-empty {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}

.chat-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.6;
}

.chat-bubble--user {
  align-self: flex-end;
  background: #2347c5;
  color: #ffffff;
}

.chat-bubble--model {
  align-self: flex-start;
  background: #f4f5f8;
  color: #1f2532;
}

.chat-bubble-text {
  margin: 0;
  white-space: pre-wrap;
}

.chat-papers {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.chat-paper-card {
  display: block;
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  text-decoration: none;
  border: 1px solid #e2e4ea;
}

.chat-paper-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #2347c5;
}

.chat-paper-meta {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: #6f7480;
}

.chat-loading,
.chat-error {
  margin: 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.chat-error {
  color: #d64545;
}

.chat-input-row {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #e2e4ea;
  border-radius: 8px;
  font-size: 13px;
}

.chat-input:disabled {
  background: #f7f7f9;
}

.chat-send-btn {
  height: 38px;
  padding: 0 18px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.chat-send-btn:disabled {
  background: #b7c2e6;
  cursor: not-allowed;
}
```

- [ ] **Step 5: 型別檢查與 build**

Run（在 `frontend/` 目錄下執行）:
```bash
npm run type-check && npm run build
```
Expected: 兩個指令都無錯誤輸出，結束碼 0。

- [ ] **Step 6: 手動瀏覽器驗證**

沒有瀏覽器自動化工具可用，請依下列步驟手動驗證（或請使用者操作後回報結果）：
1. 開一個已經跑完 workflow 的專案，前往 `/hub/projects/:id/result`
2. 確認頁面自動出現「AI 結構化分析」卡片，loading 一段時間後顯示四段分析文字
3. 重新整理頁面，確認結構化分析直接從快取顯示（不重新 loading）
4. 在「與 AI 對話」輸入框問一個一般問題（例如「這次最好的模型是什麼？」），確認送出後訊息正確顯示在對話串、AI 有回覆
5. 問一個涉及文獻查詢的問題（例如「有沒有相關論文支持這個結果？」），確認 AI 回覆下方有出現可點擊的論文卡片，點擊會開新分頁到 pdf
6. 重新整理頁面，確認對話紀錄仍在（從 localStorage 還原）

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "feat: add AI structured analysis and chat UI to result page"
```
