# 框架提取即時思考串流 Design Spec

## 背景

`ExtractFrameworkView.vue` 的「提取框架」流程原本用輪播假訊息（見 `docs/superpowers/specs/2026-08-08-extract-framework-progress-messages-design.md`，已上線）模擬處理進度。本次要把它升級成像 Gemini 官網一樣，即時顯示模型「真實思考過程」（thinking / thought summary），而不是預先寫死的階段文字。

此規格取代（superseded）上一版輪播假訊息的前端顯示邏輯，建立在其已合併進 main 的基礎上。

## 現況調查結論

- 後端 `backend/services/gemini_service.py` 用舊版 `google-generativeai` SDK（0.8.6，已棄用）呼叫 `gemini-2.5-flash`，`generate_content()` 為同步、非串流呼叫，`GenerationConfig` 沒有 `thinking_config` 欄位——舊 SDK 不支援 thought summary。
- 新版統一 SDK `google-genai`（已於本機容器內安裝並檢查完 API 後移除，未留在環境中）支援：
  - `client.models.generate_content_stream(model=..., contents=..., config=types.GenerateContentConfig(...))` 逐 chunk 串流
  - `types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)`（`-1` = 讓模型自行決定思考長度）
  - 串流回應的每個 `Part` 有 `part.thought: bool`，`True` 表示這段是思考內容，其餘是正式答案內容
  - `types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")` 對應舊版的 `inline_data` PDF 附件寫法
- `/api/gemini/ai-analyze`（`backend/routes/gemini.py`）目前被兩處呼叫：`ExtractFrameworkView.vue`（僅用 PDF 上傳路徑）與 `useWorkflowImport.ts`（workflow 畫布的 PDF 匯入）。本次**只改 `ExtractFrameworkView.vue`**，新增一支獨立的串流端點，不動現有 `/ai-analyze`、不動 `useWorkflowImport.ts`、不動 `paper_rag.py`（仍用舊 SDK）。

## 範圍

- 新增後端串流端點與 `GeminiService` 方法（僅支援 PDF 上傳，比對現有 `/ai-analyze` 精簡，因為 `ExtractFrameworkView` 只送 PDF + 可選 title）
- 新增前端串流消費 API 與 `ExtractFrameworkView.vue` 的思考顯示區塊
- 不動：`/ai-analyze`（非串流）、`useWorkflowImport.ts`、`paper_rag.py`、舊版 SDK 的既有呼叫

## 後端設計

### 依賴

`backend/pyproject.toml` 新增 `google-genai`，與既有 `google-generativeai` 並存（後者仍被 `paper_rag.py` 與非串流 `/ai-analyze` 使用）。沿用既有環境變數 `GEMINI_API_KEY`、`GEMINI_MODEL`（預設 `gemini-2.5-flash`，支援 thinking）。

### `GeminiService.analyze_pdf_stream(pdf_bytes, title)`

新增於 `backend/services/gemini_service.py`，回傳 generator，yield 以下三種事件之一：

- `{"type": "thought", "text": <str>}`：每收到一個 `part.thought is True` 的 chunk 就 yield 一次，`text` 為該 chunk 的文字片段（非累積，前端自行累加顯示）
- `{"type": "result", "data": {...}}`：串流結束、答案文字組完後 yield 一次，`data` 的結構跟現有 `analyze_pdf()` 回傳值一致（`provider`、`model`、`workflow_json`、`raw`、`usage`）
- `{"type": "error", "message": <str>}`：任何例外（含 JSON 解析最終失敗）時 yield

實作重點：

1. 建立 `genai.Client(api_key=...)`，呼叫 `client.models.generate_content_stream(model=self.model_name, contents=[prompt, types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")], config=types.GenerateContentConfig(response_mime_type="application/json", thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=-1)))`。`prompt` 沿用既有 `_WORKFLOW_SYSTEM_PROMPT` 组合邏輯（與 `analyze_pdf()` 相同的組法）。
2. 逐 chunk 迭代：對每個 `chunk.candidates[0].content.parts`，`part.thought` 為真 → yield thought 事件；否則把 `part.text` 累加進答案緩衝區字串。
3. 串流結束後，對答案緩衝區呼叫既有 `_safe_parse_json()`；失敗則呼叫既有 `_normalize_to_json()`（同步的修復呼叫，沿用舊 SDK，不變動其實作）；仍失敗則 yield error 事件；成功則用既有 `_fill_defaults()` 補齊欄位，組出跟 `analyze_pdf()` 相同形狀的 dict，yield result 事件。
4. 整段包在 try/except，任何未預期例外都 yield error 事件（`message` 用 `str(exc)`），不讓 generator 直接拋出中斷連線。

### 路由：`POST /api/gemini/ai-analyze/stream`

新增於 `backend/routes/gemini.py`：

- 只接受 `multipart/form-data`，欄位 `file`（必填，PDF）、`title`（選填）——不支援 `/ai-analyze` 既有的 txt/md、JSON body、`focus`、`save_output` 等路徑，因為 `ExtractFrameworkView` 從不使用它們
- 驗證：檔案存在、副檔名為 pdf、大小 ≤ `MAX_PDF_BYTES`（沿用既有常數），驗證失敗時在建立串流前直接回傳一般 JSON 錯誤（`400`/`413`），不進入 SSE
- 驗證通過後，先在 request context 內把 `pdf_bytes = file.read()` 讀出（Flask 的 request 在 generator 開始 streaming 後就不可用），再回傳 `Response(stream_with_context(_sse_events()), mimetype="text/event-stream")`，`_sse_events()` 包裝 `service.analyze_pdf_stream(pdf_bytes, title)`，把每個事件字典格式化成 `f"event: {ev['type']}\ndata: {json.dumps(payload)}\n\n"`。`payload` 是事件字典去掉 `type` 欄位後剩下的內容（`thought` 事件送 `{"text": ...}`、`result` 事件送 `{"data": {...}}`、`error` 事件送 `{"message": ...}`），前端一律用 SSE 的 `event:` 行判斷分派，不再從 `data` 裡讀第二次 type

## 前端設計

### `frontend/src/api/gemini.ts` 新增 `streamAnalyzeWorkflowFromPdf`

```
streamAnalyzeWorkflowFromPdf(
  params: { file: File, title?: string },
  callbacks: {
    onThought: (text: string) => void
    onResult: (workflowJson: Record<string, unknown>) => void
    onError: (message: string) => void
  }
): Promise<void>
```

因為要 POST 帶檔案的 body，瀏覽器原生 `EventSource` 不支援（只能 GET），改用 `fetch()` 取得 `response.body` 的 `ReadableStream`，用 `TextDecoder` 逐塊解碼、以 `\n\n` 切分事件區塊，解析每塊裡的 `event:`/`data:` 行，依 `event` 分派到對應 callback。非 2xx 回應（驗證失敗，走一般 JSON 錯誤）時改讀 JSON body 的 `error` 欄位丟給 `onError`。回傳的 Promise 在串流自然結束（收到 `result` 或 `error` 事件，或連線關閉）後 resolve；網路層例外（fetch 本身失敗）reject，由呼叫端 try/catch 處理。

### `ExtractFrameworkView.vue` 改動

- 移除輪播假訊息版本的 `EXTRACT_MESSAGES`、`messageIndex`、`messageTimer`，以及 template 裡的 `<Transition>` 文字區塊
- 新增 `thoughtLog = ref<string[]>([])`：每收到一個 thought chunk 就 `push` 一筆
- 新增 `thoughtLogEl = ref<HTMLElement | null>(null)` 綁定到思考框的 DOM，每次 `thoughtLog` 更新後透過 `nextTick()` 把 `scrollTop` 設為 `scrollHeight`，自動捲到底部
- Loading 區塊改為：spinner（沿用現有 `v-progress-circular`）+ 固定高度（約 160px）、可捲動的思考框，框內用 `v-for` 逐行渲染 `thoughtLog` 的每個片段
- `startExtract()` 改呼叫 `streamAnalyzeWorkflowFromPdf`：
  - 開始前重置 `thoughtLog.value = []`
  - `onThought`：push 進 `thoughtLog` 並捲到底部
  - `onResult`：沿用現有的欄位映射邏輯（models/preprocessing/featureEngineering/targetCol/metrics 解析），寫入 `extractedData`、`rawWorkflowJson`
  - `onError`：寫入 `extractError`，不自動重試（跟現有行為一致）
  - `finally`：`extracting.value = false`

## 錯誤處理

- 串流中途斷線或後端 yield error 事件 → 直接顯示錯誤訊息（`extractError`），使用者自行按「開始提取」重試，不自動重試
- 檔案驗證失敗（非 PDF、超過大小上限）→ 維持現有行為，在建立串流前就回一般 JSON 錯誤

## 測試

- 前端無單元測試框架，用 `npm run type-check` + 人工瀏覽器驗證：上傳 PDF、觀察思考文字即時捲動顯示、最終框架結果正確顯示（與现有欄位映射邏輯一致）、上傳非 PDF/超大檔案時顯示錯誤
- 後端手動驗證：用 `curl -N -X POST .../ai-analyze/stream -F file=@paper.pdf` 觀察原始 SSE 輸出（`event: thought` 逐段出現、最後一則 `event: result` 帶完整 `workflow_json`）
