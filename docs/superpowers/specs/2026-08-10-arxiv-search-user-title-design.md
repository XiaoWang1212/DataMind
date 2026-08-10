# arXiv 參考文獻查詢加入使用者標題輸入 Design

## 背景與目標

「選擇參考文獻」頁（`frontend/src/views/PaperSourcesView.vue`）目前一進頁就自動呼叫 `/api/rag/arxiv/search`，查詢主題與 arXiv 關鍵字完全由 Gemini 讀取資料探勘結果（`mining_results`）自行推論（`backend/services/rag/paper_rag.py` 的 `classify_topic()`），使用者從頭到尾沒有任何機會影響查詢方向，只能在結果出來後勾選/取消候選論文。

目標：讓使用者在查詢前，可以選填輸入「想要的論文標題」；Gemini 產生 arXiv 查詢關鍵字時，改成同時參考「使用者給的標題」與「實際的資料探勘結果」，讓查到的文獻既符合使用者想要的方向，也跟實際跑出來的模型/資料相關。

## 範圍

- 只動「選擇參考文獻」頁的查詢前置流程與後端 `classify_topic`/`search_arxiv_candidates` 這條路徑。
- 使用者標題留空時，行為必須跟現在完全一致（AI 完全自動推論主題與查詢字）——這是刻意的相容性要求，不是「以後再做」。
- 不動論文生成（`/api/rag/arxiv/generate`）、候選論文勾選、下載/建索引等後續流程；`topic` 欄位（後面會變成生成論文的標題）繼續原封不動地往下傳遞即可，不需要額外改動。

## 前端：`PaperSourcesView.vue`

**進頁行為改變**：拿掉 `onMounted()` 裡自動呼叫 `loadCandidates()` 的邏輯。`onMounted()` 只負責從 `loadWorkflowStateFromStorage()` 載入 `miningResults` 並設定 `hasLoaded`，不再自動觸發查詢。

**新增查詢前置畫面**：`miningResults` 載入完成、且尚未查詢過時，顯示：
- 一個文字輸入框，`v-model="userTitle"`，placeholder 提示「留空由 AI 自動判斷主題」。
- 一個「查詢文獻」按鈕，點擊呼叫 `loadCandidates()`。

用一個新的 `hasSearched = ref(false)` 狀態（在 `loadCandidates()` 開頭設為 `true`）來區分「查詢前置畫面」與「查詢中/查詢結果」兩個階段。輸入框與按鈕在查詢完成後**不隱藏**，讓使用者可以直接改標題、再點一次查詢，不用重新整理頁面（`loadCandidates()` 本身已經會重置 `candidates`/`selectedIds`，天然支援重查）。

**`loadCandidates()` 修改**：呼叫 `searchArxivCandidates(miningResults.value, userTitle.value.trim() || undefined)`，把使用者輸入（去除頭尾空白，空字串視為未填）一起傳下去。

## 前端 API：`frontend/src/api/arxiv.ts`

`searchArxivCandidates(miningResults: Record<string, unknown>, userTitle?: string)`：新增選填的第二個參數，非空時放進 POST body 的 `user_title` 欄位；未提供則不帶這個欄位（維持現有 request shape，後端沒收到就是「未填」）。

## 後端路由：`backend/routes/rag.py` 的 `/arxiv/search`

`request.get_json()` 多讀一個選填欄位 `user_title`（沒有就是 `None`），傳給 `service.search_arxiv_candidates(mining_results, user_title)`。

## 後端服務：`backend/services/rag/paper_rag.py`

**`search_arxiv_candidates(self, mining_results: dict, user_title: str | None = None) -> dict`**：簽章新增選填參數，原封不動傳給 `classify_topic()`，其餘邏輯（呼叫 `arxiv_source.search_arxiv()`）不變。

**`classify_topic(self, mining_results: dict, user_title: str | None = None) -> dict`**：

- `user_title` 為 `None`/空字串：完全維持現有邏輯與 prompt，不變。
- `user_title` 有值：
  - `topic` 直接用 `user_title`，不再讓 Gemini 猜。
  - 改用新的 prompt，只請 Gemini 產生 arXiv 查詢關鍵字：把使用者的標題與資料探勘結果一起交給它，要求輸出的關鍵字必須同時貼合這個標題方向、也跟實際的模型/資料/方法相關。
  - Prompt 只要求輸出一行 `QUERY: <關鍵字>`（不用再要求 `TOPIC:`，因為主題已經由使用者提供）。
  - 解析失敗時的 fallback：跟現有邏輯一致的精神——找不到 `QUERY:` 這行，就直接拿 `user_title` 當查詢字（不中斷流程，只是查詢字英文關鍵字命中率會比較低）。

具體實作：

```python
def classify_topic(self, mining_results: dict, user_title: str | None = None) -> dict:
    """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢關鍵字。

    user_title 有值時，主題直接採用使用者給的標題，Gemini 只需要根據
    「使用者標題 + 實際資料探勘結果」產生符合兩者的 arXiv 查詢關鍵字。
    """
    results_text = self._format_datamind_output(mining_results)

    if user_title:
        prompt = (
            "你是學術論文寫作助手。使用者想寫一篇標題為"
            f"「{user_title}」的論文，以下是實際的資料探勘實驗結果。\n\n"
            f"【資料探勘實驗結果】\n{results_text}\n\n"
            "請判斷 2 到 6 個適合拿去查 arXiv 的英文關鍵字，"
            "這些關鍵字必須同時符合這個標題的方向、也跟上述實際的模型/資料/方法相關。\n"
            "請「只」輸出以下一行，不要有其他文字：\n"
            "QUERY: <2 到 6 個英文關鍵字，空白分隔，不要加引號或布林運算子>"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)

        query_match = re.search(r"QUERY:\s*(.+)", text)
        arxiv_query = query_match.group(1).strip() if query_match else user_title

        return {"topic": user_title, "arxiv_query": arxiv_query}

    prompt = (
        "你是學術論文寫作助手。請根據以下資料探勘實驗結果，"
        "判斷這份研究適合的研究主題與 arXiv 查詢關鍵字。\n\n"
        f"【資料探勘實驗結果】\n{results_text}\n\n"
        "請「只」輸出以下兩行，不要有其他文字：\n"
        "TOPIC: <繁體中文的研究主題，一句話，供論文標題使用>\n"
        "QUERY: <2 到 6 個英文關鍵字，空白分隔，適合直接拿去查 arXiv，"
        "不要加引號或布林運算子>"
    )
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    text = self._call_gemini(prompt, usage_total)

    topic_match = re.search(r"TOPIC:\s*(.+)", text)
    query_match = re.search(r"QUERY:\s*(.+)", text)

    topic = topic_match.group(1).strip() if topic_match else "資料探勘實驗研究"
    arxiv_query = query_match.group(1).strip() if query_match else topic

    return {"topic": topic, "arxiv_query": arxiv_query}
```

## 測試

- 後端：`backend/scripts/` 慣例的手動驗證腳本，涵蓋「無標題」（沿用現有行為）與「有標題」兩種情況，確認回傳的 `topic`/`arxiv_query` 符合預期、`user_title` 缺漏時不影響現有流程。
- 前端：手動瀏覽器驗證——進頁不再自動查詢、留空點查詢行為跟現在一致、填標題後查詢結果的「研究主題」顯示使用者輸入的標題、改標題重新查詢會重置候選清單。
