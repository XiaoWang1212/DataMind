# Result 頁面 AI 分析與對話功能 設計文件

## 背景

組員要求在 result 頁面加入「AI 分析」與「和 AI 對話」功能。專案裡目前有兩個 results 頁面：`/results`（`ResultsPage.vue`，tako 分支主力開發，已有單段落「AI生成洞察」）與 `/hub/projects/:id/result`（`ResultView.vue`，先前開發的 Hub 子路由結果頁，目前完全沒有 AI 功能）。本次功能目標頁面是 **`ResultView.vue`**。

## 目標

1. 在 `ResultView.vue` 加入**結構化 AI 分析**：涵蓋模型比較與選擇建議、資料/特徵層面洞察、風險與限制提示、後續建議行動四個面向。
2. 在 `ResultView.vue` 加入**AI 對話功能**：使用者可針對這份實驗結果提問，AI 可自主判斷是否需要查詢 arXiv 論文庫並在回覆中附上可點擊的論文卡片。

## 非目標

- 不處理 `/results`（`ResultsPage.vue`）的功能異動。
- 不做串流回覆（chat 為一次性 request/response，不用 SSE/WebSocket）。
- 一輪對話最多觸發一次 arXiv 搜尋（不支援多輪 function call）。
- 不做清除對話紀錄的 UI。
- 不涉及已 ingest 的本地向量庫（`paper_rag` 的 `search()`）；對話中查文獻一律走即時 arXiv 搜尋（`arxiv_source.search_arxiv`），不寫入向量庫。

## 架構總覽

沿用專案現有的**無狀態後端**模式（跟 `/api/rag/insight`、`/api/rag/generate-paper` 一致）：前端每次呼叫都把完整 `mining_results`（以及對話歷史）傳給後端；後端不儲存任何 session 狀態。對話歷史與結構化分析結果由前端存進 `localStorage`（沿用 `workflowState_<projectId>`／`resultInsight_<projectId>` 的按 projectId 分 key 模式）。

## 後端設計

### 依賴確認

後端目前使用 `google.generativeai==0.8.6`（雖然上游已標記 deprecated，但功能仍可用），確認支援：
- `genai.GenerativeModel.start_chat(history=...)` + `chat.send_message(...)`（多輪對話）
- `Tool` / `FunctionDeclaration`（function calling / tool use）
- `GenerationConfig(response_mime_type="application/json")`（JSON 結構化輸出）

### `PaperRAGService` 新增方法（`backend/services/rag/paper_rag.py`）

#### `generate_structured_analysis(mining_results: dict) -> dict`

- 沿用既有 `_format_datamind_output(mining_results)` 產生實驗結果摘要文字。
- 組 prompt 要求 Gemini 針對四個面向（模型比較與選擇建議、資料/特徵層面洞察、風險與限制提示、後續建議行動）分別生成繁體中文段落。
- 用 `GenerationConfig(response_mime_type="application/json")` 讓 Gemini 直接輸出 JSON，避免用正則表達式解析多行文字（`classify_topic` 的 `TOPIC:`/`QUERY:` 正則模式不適合用在多行段落內容上）。
- 回傳固定結構：
  ```python
  {
      "model_comparison": str,
      "data_insights": str,
      "risks": str,
      "recommendations": str,
  }
  ```
- 若 Gemini 回傳的 JSON 解析失敗或缺欄位，該欄位補上空字串，不整個拋錯（沿用 `_call_gemini` 現有的「生成失敗回傳錯誤字串」寬容策略）。

#### `chat_about_results(mining_results: dict, history: list[dict], message: str) -> dict`

- `history` 為 `[{role: "user" | "model", text: str}]` 的清單，由前端傳入（對應 localStorage 存的完整對話紀錄）。
- 定義一個 `search_arxiv` 工具（`FunctionDeclaration`），參數只有 `query: string`（AI 自行決定查詢字串，不透過 `classify_topic` 分類步驟）。
- 建立 `chat = self._model.start_chat(history=[...])`，第一則歷史訊息前插入一則 system context（用 `_format_datamind_output(mining_results)` 產生的實驗結果摘要），讓 AI 知道這個專案的實驗結果。
- `chat.send_message(message)`：
  - 若回應包含 function call（`search_arxiv`），執行 `arxiv_source.search_arxiv(query)` 取得候選論文清單，透過 `send_message` 送出 function response，取得 AI 最終文字回覆。
  - 若 arXiv 搜尋過程拋出例外，不讓整個 request 500，而是把錯誤訊息包成 function response 內容送回給 Gemini，讓 AI 用文字告知使用者「查詢文獻時發生問題」，對話仍可繼續。
- 回傳：
  ```python
  {
      "reply": str,
      "papers": [],  # 或本輪 arXiv 搜尋到的候選論文清單（沿用 search_arxiv_candidates 的候選論文欄位格式：arxiv_id/title/authors/year/abstract/pdf_url）
  }
  ```
  `papers` 只有在本輪真的觸發搜尋時才非空。

### 新增 API Route（`backend/routes/rag.py`）

#### `POST /api/rag/structured-analysis`
- JSON body：`{ mining_results: dict }`（必填）
- 回傳：`{ success: true, analysis: {...四個欄位} }` 或 `{ success: false, error: str }`（500）

#### `POST /api/rag/chat`
- JSON body：`{ mining_results: dict, history: [{role, text}], message: str }`（`mining_results`、`message` 必填，`history` 可為空陣列）
- 回傳：`{ success: true, reply: str, papers: [...] }` 或 `{ success: false, error: str }`（500）

兩個 route 都遵循現有 `rag.py` 的錯誤處理慣例：`try/except Exception`，`logger.exception(...)`，回傳 `{"success": False, "error": str(e)}, 500`。

## 前端設計

### 新增檔案

- `frontend/src/api/resultAnalysis.ts`：
  - `fetchStructuredAnalysis(miningResults): Promise<StructuredAnalysis>`
  - `sendChatMessage(miningResults, history, message): Promise<{ reply: string, papers: ArxivCandidate[] }>`
  - 比照 `insight.ts`／`workflow.ts` 的 fetch 封裝風格（`fetch` + 檢查 `response.ok`/`result.success`，失敗拋 `Error`）。

### `useWorkflowStorage.ts` 新增函式

- `saveStructuredAnalysisToStorage(projectId, analysis)` / `loadStructuredAnalysisFromStorage(projectId)` → key: `structuredAnalysis_<projectId>`
- `saveChatHistoryToStorage(projectId, history)` / `loadChatHistoryFromStorage(projectId)` → key: `chatHistory_<projectId>`
- 皆比照現有 `saveResultInsightToStorage`/`loadResultInsightFromStorage` 的寫法（`localStorage.setItem`/`getItem` + JSON 序列化，失敗時 `console.error` 並吞掉錯誤，不拋出）。

### `ResultView.vue` 新增區塊

沿用頁面既有的 metric-card / insight-card 視覺風格（卡片 + icon + 標題）。

**1. AI 結構化分析卡片**
- 4 個子區塊，各自 icon + 標題 + 段落文字：模型比較與選擇建議、資料/特徵層面洞察、風險與限制提示、後續建議行動。
- 掛載時（`onMounted`）：先讀 localStorage 快取（`loadStructuredAnalysisFromStorage`），有快取就直接顯示；沒有才呼叫 `fetchStructuredAnalysis` 並存快取（邏輯結構比照現有 `loadInsight`）。
- loading / error 狀態處理比照現有 `insightLoading`/`insightError`（error 時顯示錯誤訊息 + 「重試」按鈕）。

**2. AI 對話區塊**
- 訊息列表（user/AI 氣泡，區分左右或顏色）+ 輸入框 + 送出按鈕，放在頁面最底部。
- 掛載時讀 `loadChatHistoryFromStorage` 還原歷史對話。
- 送出訊息時：
  1. 樂觀地把使用者訊息 append 進畫面上的訊息列表
  2. disable 輸入框，顯示「AI 思考中...」之類的 loading 狀態
  3. call `sendChatMessage(miningResult, history, message)`
  4. 成功：把 AI 回覆 append 進列表；若 `papers` 非空，在該則訊息下方渲染可點擊論文卡片（標題/作者/年份，點擊在新分頁開啟 `pdf_url`）；把完整更新後的 history 存回 localStorage
  5. 失敗：在該則訊息位置顯示錯誤提示（比照 insight 的錯誤呈現風格），不清空使用者已輸入的訊息紀錄
  6. 恢復輸入框可用狀態

論文卡片的呈現直接複用既有 arXiv 搜尋結果卡片的樣式邏輯（`PaperSourcesView.vue` 應該已有類似卡片元件／樣式可參考），只是換個地方（聊天訊息下方）渲染，不建立全新的視覺樣式。

## 資料流

```
ResultView.vue 掛載
  ├─ loadWorkflowStateFromStorage(projectId) → workflowResult (mining_results)
  ├─ [結構化分析] loadStructuredAnalysisFromStorage(projectId)
  │     └─ 無快取 → POST /api/rag/structured-analysis { mining_results } → 存快取
  └─ [對話] loadChatHistoryFromStorage(projectId) → 還原訊息列表（無自動呼叫 API）

使用者送出訊息
  └─ POST /api/rag/chat { mining_results, history, message }
        └─ 後端視需要呼叫 arxiv_source.search_arxiv(query)（AI function call 觸發）
        └─ 回傳 { reply, papers }
        └─ 前端更新畫面 + 存回 saveChatHistoryToStorage(projectId, history)
```

## 錯誤處理

- 後端兩個新 route 皆遵循現有 `try/except Exception → 500 + { success: false, error }` 慣例。
- `chat_about_results` 內部的 arXiv 搜尋失敗不讓整個 request 500，改把錯誤包進 function response 讓 AI 用自然語言告知使用者，對話可繼續（跟既有 `_call_gemini` 遇錯回傳錯誤字串而非拋例外的寬容風格一致）。
- `generate_structured_analysis` 的 JSON 解析失敗時，缺的欄位補空字串而非整個失敗，讓前端至少能顯示已成功生成的面向。
- 前端 API 呼叫失敗（結構化分析 or 對話）都在 UI 上顯示明確錯誤訊息，並提供重試/重新輸入的路徑，不靜默失敗。

## 驗證方式

專案沒有前端測試框架，也沒有後端自動化測試套件涵蓋 `paper_rag.py`。驗證方式比照先前兩次 bug 修復的作法：
- 後端：透過 `docker exec -w /app datamind-backend uv run python3 -c "..."` 直接呼叫新方法，用真實/模擬的 `mining_results` 驗證回傳結構正確；並對執行中的 Docker backend 做 `curl` 端對端測試（`/api/rag/structured-analysis`、`/api/rag/chat`，含觸發與不觸發 arXiv 搜尋兩種情境）。
- 前端：`npm run type-check` 與 `npm run build` 必須乾淨；請使用者在瀏覽器手動操作 `ResultView.vue` 驗證兩個新區塊的顯示與互動（無瀏覽器自動化工具可用）。
