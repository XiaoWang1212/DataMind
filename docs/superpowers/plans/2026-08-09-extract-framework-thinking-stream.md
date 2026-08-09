# 框架提取即時思考串流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「提取框架」頁面的 loading 顯示從輪播假訊息升級成 Gemini 的真實思考過程（thinking / thought summary）即時串流，最終框架結果仍跟現在一樣正確顯示。

**Architecture:** 後端新增 `google-genai`（新版統一 SDK）依賴，`GeminiService` 新增 `analyze_pdf_stream()` 用 SSE 把思考 chunk 和最終結果逐一送出；`backend/routes/gemini.py` 新增一支只支援 PDF 上傳的串流端點。前端 `api/gemini.ts` 新增用 `fetch()` + `ReadableStream` 手動解析 SSE 的 wrapper（原生 `EventSource` 不支援 POST），`ExtractFrameworkView.vue` 把輪播假訊息換成可捲動的即時思考框。只改這個頁面，不動既有的 `/ai-analyze`、`useWorkflowImport.ts`、`paper_rag.py`。

**Tech Stack:** Python 3.11、Flask、`google-genai`（新增）、`google-generativeai`（既有，保留）、Vue 3 `<script setup>`、TypeScript。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-09-extract-framework-thinking-stream-design.md`
- 只改 `ExtractFrameworkView.vue` 這個頁面的提取流程，不動 `/api/gemini/ai-analyze`（非串流）、`useWorkflowImport.ts`、`backend/services/rag/paper_rag.py`
- 新串流端點 `POST /api/gemini/ai-analyze/stream` 只支援 PDF 上傳（`file` 欄位 + 選填 `title`），不支援 txt/md、JSON body、`focus`、`save_output`
- SSE 事件格式固定：`event: thought` → `data: {"text": "..."}`；`event: result` → `data: {"data": {...}}`；`event: error` → `data: {"message": "..."}`
- `thinking_config` 用 `include_thoughts=True, thinking_budget=-1`（讓模型自行決定思考長度，不設固定上限）
- 本專案沒有設定 pytest / vitest 等單元測試框架，一律用手動 curl / python 腳本 / 瀏覽器驗證 + `npm run type-check`
- 測試用 PDF 沿用既有的 `backend/samples/gemini_sample/cin18058.pdf`

---

### Task 1: 後端依賴 — 新增 `google-genai`

**Files:**
- Modify: `backend/pyproject.toml`

**Interfaces:**
- Produces: `google-genai` package 可在 `datamind-backend` 容器的 `.venv` 內 import（供 Task 2 使用）

- [ ] **Step 1: 在 dependencies 清單新增 `google-genai`**

找到 `backend/pyproject.toml` 的（第 7-13 行附近）：

```toml
dependencies = [
  "mineru[core]",
  "torch",
  "pymupdf",
  "flask",
  "flask-cors",
  "scikit-learn",
  "google-generativeai",
```

改成（在 `google-generativeai` 後面加一行）：

```toml
dependencies = [
  "mineru[core]",
  "torch",
  "pymupdf",
  "flask",
  "flask-cors",
  "scikit-learn",
  "google-generativeai",
  "google-genai",
```

- [ ] **Step 2: 更新 lockfile 並安裝**

Run: `docker exec datamind-backend sh -lc "cd /app && uv lock && uv sync --frozen --no-dev"`
Expected: 指令成功結束，輸出裡看得到 `+ google-genai==<version>`（新增安裝）

- [ ] **Step 3: 驗證可以 import**

Run: `docker exec datamind-backend sh -lc "cd /app && .venv/bin/python -c \"from google import genai; from google.genai import types; print('ok')\""`
Expected: 印出 `ok`，無 import error

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: add google-genai dependency for thinking stream"
```

---

### Task 2: 後端 — `GeminiService.analyze_pdf_stream`

**Files:**
- Modify: `backend/services/gemini_service.py`

**Interfaces:**
- Consumes: Task 1 的 `google-genai` package；既有的 `self.model_name`、`_WORKFLOW_SYSTEM_PROMPT`、`_safe_parse_json()`、`_normalize_to_json()`、`_fill_defaults()`、`_usage_dict()`（皆已存在，不改動其實作）
- Produces: `GeminiService.analyze_pdf_stream(pdf_bytes: bytes, title: str = "") -> Generator[dict, None, None]`，yield 的 dict 為以下三種之一：
  - `{"type": "thought", "text": str}`
  - `{"type": "result", "data": {"provider": str, "model": str, "workflow_json": dict, "raw": str | None, "usage": dict}}`
  - `{"type": "error", "message": str}`
  供 Task 3 的路由消費

- [ ] **Step 1: 新增新版 SDK 的 import**

找到 `backend/services/gemini_service.py` 檔案開頭（第 1-9 行）：

```python
import base64
import logging
import os
import json
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
```

改成（新增新版 SDK 的 import，用不同名稱避免跟舊版 `genai` 衝突）：

```python
import base64
import logging
import os
import json
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
from google import genai as genai_client
from google.genai import types as genai_types
```

- [ ] **Step 2: 新增 `analyze_pdf_stream` 方法**

找到 `analyze_pdf` 方法結尾（約第 296-305 行）：

```python
        response = self.model.generate_content(
            [prompt, pdf_part],
            generation_config=self._generation_config(),
        )
        workflow_json, raw, usage = self._parse_response(response)
        return {
            "provider": "gemini",
            "model": self.model_name,
            "workflow_json": self._fill_defaults(workflow_json),
            "raw": raw,
            "usage": self._usage_dict(usage),
        }


def truncate_content(text: str, max_chars: int = 18000) -> str:
```

改成（在 `analyze_pdf` 和 `truncate_content` 之間插入新方法）：

```python
        response = self.model.generate_content(
            [prompt, pdf_part],
            generation_config=self._generation_config(),
        )
        workflow_json, raw, usage = self._parse_response(response)
        return {
            "provider": "gemini",
            "model": self.model_name,
            "workflow_json": self._fill_defaults(workflow_json),
            "raw": raw,
            "usage": self._usage_dict(usage),
        }

    def analyze_pdf_stream(self, pdf_bytes: bytes, title: str = ""):
        """Stream Gemini's thinking process while analyzing a PDF, then the final result.

        Yields dicts of one of three shapes:
        - {"type": "thought", "text": str} — one per thinking chunk
        - {"type": "result", "data": {...same shape as analyze_pdf()'s return value...}}
        - {"type": "error", "message": str}
        """
        prompt = (
            f"{_WORKFLOW_SYSTEM_PROMPT}\n"
            f"論文標題：{title or '（見上傳 PDF）'}\n"
            "請根據上傳的 PDF 論文內容生成 workflow JSON。"
        )

        try:
            client = genai_client.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
            pdf_part = genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

            stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=[prompt, pdf_part],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=genai_types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=-1,
                    ),
                ),
            )

            answer_parts: list[str] = []
            last_chunk = None
            for chunk in stream:
                last_chunk = chunk
                if not chunk.candidates:
                    continue
                content = chunk.candidates[0].content
                if content is None or not content.parts:
                    continue
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if not text:
                        continue
                    if getattr(part, "thought", False):
                        yield {"type": "thought", "text": text}
                    else:
                        answer_parts.append(text)

            answer = "".join(answer_parts)
            workflow_json = self._safe_parse_json(answer)
            raw = None
            if workflow_json is None and answer.strip():
                workflow_json = self._normalize_to_json(answer)
            if workflow_json is None:
                raw = answer.strip()

            usage = getattr(last_chunk, "usage_metadata", None) if last_chunk is not None else None
            yield {
                "type": "result",
                "data": {
                    "provider": "gemini",
                    "model": self.model_name,
                    "workflow_json": self._fill_defaults(workflow_json),
                    "raw": raw,
                    "usage": self._usage_dict(usage),
                },
            }
        except Exception as exc:
            logger.exception("analyze_pdf_stream failed")
            yield {"type": "error", "message": str(exc)}


def truncate_content(text: str, max_chars: int = 18000) -> str:
```

（Fix wave 後補上 `temperature=0.2`，見 commit history——上面 `GenerateContentConfig(...)` 呼叫應包含 `temperature=0.2` 作為第一個參數，對齊 `_generation_config()`。此區塊為歷史紀錄，不重寫。）

- [ ] **Step 3: 手動驗證（跑一段 python 腳本，用既有的樣本 PDF）**

Run:
```bash
docker exec datamind-backend sh -lc "cd /app && .venv/bin/python -c \"
from services.gemini_service import GeminiService
svc = GeminiService()
with open('samples/gemini_sample/cin18058.pdf', 'rb') as f:
    pdf_bytes = f.read()
thought_count = 0
result_seen = False
for event in svc.analyze_pdf_stream(pdf_bytes, title='cin18058'):
    if event['type'] == 'thought':
        thought_count += 1
    elif event['type'] == 'result':
        result_seen = True
        print('models:', event['data']['workflow_json'].get('models'))
    elif event['type'] == 'error':
        print('ERROR:', event['message'])
print('thought_count:', thought_count, 'result_seen:', result_seen)
\""
```
Expected: 過程中看不到 `ERROR:` 開頭的輸出；最後一行 `thought_count` 大於 0，`result_seen` 為 `True`；`models:` 那行印出至少一個模型名稱

- [ ] **Step 4: Commit**

```bash
git add backend/services/gemini_service.py
git commit -m "feat: add GeminiService.analyze_pdf_stream for thinking stream"
```

---

### Task 3: 後端 — SSE 路由 `POST /api/gemini/ai-analyze/stream`

**Files:**
- Modify: `backend/routes/gemini.py`

**Interfaces:**
- Consumes: Task 2 的 `GeminiService.analyze_pdf_stream(pdf_bytes, title) -> Generator[dict, None, None]`
- Produces: `POST /api/gemini/ai-analyze/stream` endpoint，回傳 `text/event-stream`，事件格式見 Global Constraints，供 Task 4 的前端 wrapper 消費

- [ ] **Step 1: 加入 `Response`/`stream_with_context` import**

找到 `backend/routes/gemini.py` 開頭（第 1-9 行）：

```python
import logging
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.gemini_service import AnalysisInput, GeminiService, truncate_content
```

改成：

```python
import logging
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context
from werkzeug.utils import secure_filename

from services.gemini_service import AnalysisInput, GeminiService, truncate_content
```

- [ ] **Step 2: 新增串流路由**

找到現有 `ai_analyze_paper` 函式結尾（檔案最後一段，約第 155-165 行）：

```python
    # ── Save output if requested ─────────────────────────────────────────────
    if save_output and result:
        output_path = _save_result(title, result, output_filename)
        return jsonify({
            "success": True,
            "result": result,
            "saved_file": str(output_path),
        })

    return jsonify({"success": True, "result": result})
```

改成（在檔案最後新增一支路由，`ai_analyze_paper` 本身不動）：

```python
    # ── Save output if requested ─────────────────────────────────────────────
    if save_output and result:
        output_path = _save_result(title, result, output_filename)
        return jsonify({
            "success": True,
            "result": result,
            "saved_file": str(output_path),
        })

    return jsonify({"success": True, "result": result})


@gemini_bp.post("/ai-analyze/stream")
def ai_analyze_paper_stream():
    """論文 PDF → 即時思考串流 + 最終 Workflow JSON（SSE）

    僅支援 multipart/form-data PDF 上傳：
    - `file`：PDF 檔案（必填）
    - `title`：論文標題（選填）

    回傳 text/event-stream，事件：
    - event: thought  data: {"text": "..."}
    - event: result   data: {"data": {...}}
    - event: error    data: {"message": "..."}
    """
    try:
        service = GeminiService()
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "PDF file is required"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext != "pdf":
        return jsonify({"success": False, "error": "Only PDF is supported for streaming"}), 400

    title = request.form.get("title", file.filename)
    pdf_bytes = file.read()

    if len(pdf_bytes) > MAX_PDF_BYTES:
        return jsonify({
            "success": False,
            "error": f"PDF exceeds {MAX_PDF_BYTES // 1024 // 1024} MB limit for inline processing.",
        }), 413

    def _sse_events():
        for event in service.analyze_pdf_stream(pdf_bytes, title=title):
            event_type = event["type"]
            payload = {k: v for k, v in event.items() if k != "type"}
            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

    return Response(stream_with_context(_sse_events()), mimetype="text/event-stream")
```

- [ ] **Step 3: 手動驗證（curl -N 看原始 SSE 輸出）**

Run: `curl -N -X POST http://localhost:5001/api/gemini/ai-analyze/stream -F "file=@backend/samples/gemini_sample/cin18058.pdf" -F "title=cin18058"`
Expected: 陸續印出多個 `event: thought` / `data: {"text": ...}` 區塊，最後一個是 `event: result` / `data: {"data": {"workflow_json": {...}, ...}}`，中間沒有 `event: error`

Run: `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5001/api/gemini/ai-analyze/stream -F "title=no-file"`
Expected: `400`（沒帶 `file` 欄位）

- [ ] **Step 4: Commit**

```bash
git add backend/routes/gemini.py
git commit -m "feat: add SSE route for extract-framework thinking stream"
```

---

### Task 4: 前端 — `streamAnalyzeWorkflowFromPdf` API wrapper

**Files:**
- Modify: `frontend/src/api/gemini.ts`

**Interfaces:**
- Consumes: Task 3 的 `POST /api/gemini/ai-analyze/stream`（SSE，事件格式見 Global Constraints）
- Produces: `streamAnalyzeWorkflowFromPdf(params: { file: File, title?: string }, callbacks: { onThought: (text: string) => void, onResult: (workflowJson: Record<string, unknown>) => void, onError: (message: string) => void }): Promise<void>`，供 Task 5 的 `ExtractFrameworkView.vue` 使用

- [ ] **Step 1: 在檔案結尾新增 `streamAnalyzeWorkflowFromPdf`**

找到 `frontend/src/api/gemini.ts` 現有的 `analyzeWorkflowFromPdf` 函式結尾（第 1-32 行左右）：

```ts
export async function analyzeWorkflowFromPdf (params: {
  file: File
  title?: string
  focus?: string
}): Promise<Record<string, unknown>> {
  const { file, title, focus } = params

  const formData = new FormData()
  formData.append('file', file, file.name)
  if (title) formData.append('title', title)
  if (focus) formData.append('focus', focus)

  const response = await fetch('/api/gemini/ai-analyze', {
    method: 'POST',
    body: formData,
  })

  const result = (await response.json()) as {
    success?: boolean
    result?: { workflow_json?: Record<string, unknown> }
    error?: string
  }

  if (!response.ok || !result.success) {
    throw new Error(result.error ?? `HTTP ${response.status}`)
  }

  const workflowJson = result.result?.workflow_json
  if (!workflowJson || typeof workflowJson !== 'object') {
    throw new Error('Gemini 回傳的 workflow_json 格式錯誤')
  }

  return workflowJson
}
```

改成（保留 `analyzeWorkflowFromPdf` 不動，在後面新增 `streamAnalyzeWorkflowFromPdf`）：

```ts
export async function analyzeWorkflowFromPdf (params: {
  file: File
  title?: string
  focus?: string
}): Promise<Record<string, unknown>> {
  const { file, title, focus } = params

  const formData = new FormData()
  formData.append('file', file, file.name)
  if (title) formData.append('title', title)
  if (focus) formData.append('focus', focus)

  const response = await fetch('/api/gemini/ai-analyze', {
    method: 'POST',
    body: formData,
  })

  const result = (await response.json()) as {
    success?: boolean
    result?: { workflow_json?: Record<string, unknown> }
    error?: string
  }

  if (!response.ok || !result.success) {
    throw new Error(result.error ?? `HTTP ${response.status}`)
  }

  const workflowJson = result.result?.workflow_json
  if (!workflowJson || typeof workflowJson !== 'object') {
    throw new Error('Gemini 回傳的 workflow_json 格式錯誤')
  }

  return workflowJson
}

export async function streamAnalyzeWorkflowFromPdf (
  params: { file: File, title?: string },
  callbacks: {
    onThought: (text: string) => void
    onResult: (workflowJson: Record<string, unknown>) => void
    onError: (message: string) => void
  },
): Promise<void> {
  const { file, title } = params
  const { onThought, onResult, onError } = callbacks

  const formData = new FormData()
  formData.append('file', file, file.name)
  if (title) formData.append('title', title)

  const response = await fetch('/api/gemini/ai-analyze/stream', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok || !response.body) {
    const result = (await response.json().catch(() => null)) as { error?: string } | null
    onError(result?.error ?? `HTTP ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let boundary = buffer.indexOf('\n\n')
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)

      let eventType = 'message'
      let dataLine = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) dataLine = line.slice(6)
      }

      if (dataLine) {
        const payload = JSON.parse(dataLine) as Record<string, unknown>
        if (eventType === 'thought' && typeof payload.text === 'string') {
          onThought(payload.text)
        } else if (eventType === 'result') {
          const data = payload.data as { workflow_json?: Record<string, unknown> } | undefined
          const workflowJson = data?.workflow_json
          if (workflowJson && typeof workflowJson === 'object') {
            onResult(workflowJson)
          } else {
            onError('Gemini 回傳的 workflow_json 格式錯誤')
          }
        } else if (eventType === 'error' && typeof payload.message === 'string') {
          onError(payload.message)
        }
      }

      boundary = buffer.indexOf('\n\n')
    }
  }
}
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/gemini.ts
git commit -m "feat: add streamAnalyzeWorkflowFromPdf SSE client"
```

---

### Task 5: 前端 — `ExtractFrameworkView.vue` 改用即時思考框

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue`

**Interfaces:**
- Consumes: Task 4 的 `streamAnalyzeWorkflowFromPdf(params, callbacks): Promise<void>`

- [ ] **Step 1: 拿掉輪播假訊息的 import 與換成新的 API**

找到（第 110-114 行）：

```ts
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { analyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'
```

改成：

```ts
<script setup lang="ts">
  import { nextTick, ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { streamAnalyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'
```

- [ ] **Step 2: 拿掉 `EXTRACT_MESSAGES`／`messageIndex`／`messageTimer`，新增 `thoughtLog`／`thoughtLogEl`**

找到（第 116-142 行）：

```ts
  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const EXTRACT_MESSAGES = [
    '正在解析 PDF 內容...',
    '正在辨識研究方法與模型架構...',
    '正在提取前處理與特徵工程步驟...',
    '正在整理成框架...',
  ]

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const messageIndex = ref(0)
  let messageTimer: ReturnType<typeof setInterval> | null = null
```

改成：

```ts
  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const thoughtLog = ref<string[]>([])
  const thoughtLogEl = ref<HTMLElement | null>(null)

  async function scrollThoughtLogToBottom (): Promise<void> {
    await nextTick()
    if (thoughtLogEl.value) {
      thoughtLogEl.value.scrollTop = thoughtLogEl.value.scrollHeight
    }
  }
```

- [ ] **Step 3: 改寫 `startExtract`**

找到（第 155-201 行）：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    messageIndex.value = 0
    messageTimer = setInterval(() => {
      if (messageIndex.value < EXTRACT_MESSAGES.length - 1) {
        messageIndex.value += 1
      }
    }, 2500)

    try {
      const result = await analyzeWorkflowFromPdf({
        file: selectedFile.value,
        title: selectedFile.value.name.replace(/\.[^.]+$/, ''),
      })

      const models = (Array.isArray(result.models) ? result.models : []).map((m: unknown) =>
        typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? ''),
      )
      const preprocessing = (Array.isArray(result.preprocessing) ? result.preprocessing : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )
      const featureEngineering = (Array.isArray(result.featureEngineering) ? result.featureEngineering : []).map(
        (s: unknown) => String((s as Record<string, unknown>).type ?? s),
      )

      rawWorkflowJson.value = result
      extractedData.value = {
        name: selectedFile.value.name.replace(/\.[^.]+$/, ''),
        models,
        preprocessing,
        featureEngineering,
        targetCol: String(result.target_col ?? result.targetCol ?? ''),
        metrics: Array.isArray(result.metrics) ? result.metrics.map(String) : [],
      }
    } catch (error) {
      extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
    } finally {
      extracting.value = false
      if (messageTimer !== null) {
        clearInterval(messageTimer)
        messageTimer = null
      }
    }
  }
```

改成：

```ts
  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    thoughtLog.value = []

    const file = selectedFile.value
    const baseName = file.name.replace(/\.[^.]+$/, '')

    try {
      await streamAnalyzeWorkflowFromPdf(
        { file, title: baseName },
        {
          onThought: text => {
            thoughtLog.value.push(text)
            void scrollThoughtLogToBottom()
          },
          onResult: result => {
            const models = (Array.isArray(result.models) ? result.models : []).map((m: unknown) =>
              typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? ''),
            )
            const preprocessing = (Array.isArray(result.preprocessing) ? result.preprocessing : []).map(
              (s: unknown) => String((s as Record<string, unknown>).type ?? s),
            )
            const featureEngineering = (Array.isArray(result.featureEngineering) ? result.featureEngineering : []).map(
              (s: unknown) => String((s as Record<string, unknown>).type ?? s),
            )

            rawWorkflowJson.value = result
            extractedData.value = {
              name: baseName,
              models,
              preprocessing,
              featureEngineering,
              targetCol: String(result.target_col ?? result.targetCol ?? ''),
              metrics: Array.isArray(result.metrics) ? result.metrics.map(String) : [],
            }
          },
          onError: message => {
            extractError.value = message
          },
        },
      )
    } catch (error) {
      extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
    } finally {
      extracting.value = false
    }
  }
```

- [ ] **Step 4: template 改用可捲動思考框**

找到（第 53-58 行）：

```html
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
          <Transition mode="out-in" name="fade">
            <span :key="messageIndex">{{ EXTRACT_MESSAGES[messageIndex] }}</span>
          </Transition>
        </div>
```

改成：

```html
        <div v-if="extracting" class="extracting-indicator">
          <div class="extracting-header">
            <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
            <span>正在提取框架...</span>
          </div>
          <div ref="thoughtLogEl" class="thought-log">
            <p v-for="(t, i) in thoughtLog" :key="i" class="thought-log-line">{{ t }}</p>
          </div>
        </div>
```

- [ ] **Step 5: 更新 style，拿掉 fade class 改成 thought-log class**

找到（第 362-379 行）：

```css
.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--color-secondary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
```

改成：

```css
.extracting-indicator {
  margin-top: 14px;
}

.extracting-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--color-secondary);
}

.thought-log {
  margin-top: 10px;
  max-height: 160px;
  overflow-y: auto;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  font-size: 12.5px;
  color: var(--color-secondary);
  line-height: 1.6;
}

.thought-log-line {
  margin: 0 0 6px;
}

.thought-log-line:last-child {
  margin-bottom: 0;
}
```

- [ ] **Step 6: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 7: 人工瀏覽器驗證**

啟動前端後登入，到「框架庫 → 從論文提取框架」，上傳 `backend/samples/gemini_sample/cin18058.pdf` 並點「開始提取」。

Expected:
- 思考框逐段出現文字，自動捲到最新一行
- 提取完成後，右側「已提取框架」欄位正確顯示（模型、前處理、特徵工程、評估指標），跟改動前行為一致
- 上傳非 PDF 檔案或超過 10MB 的檔案時顯示錯誤訊息，思考框不會卡住

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "feat: show real Gemini thinking stream while extracting framework"
```
