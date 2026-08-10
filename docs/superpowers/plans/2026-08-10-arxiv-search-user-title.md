# arXiv 參考文獻查詢加入使用者標題輸入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓「選擇參考文獻」頁在查詢 arXiv 前，先給使用者一個選填的「論文標題」輸入框；有填標題時，Gemini 產生查詢關鍵字要同時參考使用者的標題與實際的資料探勘結果，留空則完全維持現有的全自動推論行為。

**Architecture:** 後端 `classify_topic()` 新增選填參數 `user_title`：有值時直接採用該標題、改用只需要產生查詢關鍵字的精簡 prompt；無值時完全走原本的邏輯（AI 自己推論主題與關鍵字）。前端 `PaperSourcesView.vue` 拿掉進頁自動查詢，改成先顯示標題輸入框 + 查詢按鈕，使用者按下才觸發查詢。

**Tech Stack:** Flask + `google.generativeai`（既有依賴，不新增套件）、Vue 3 `<script setup>` + TypeScript。

## Global Constraints

- 使用者標題輸入框是**選填**，留空時的行為必須跟目前完全一致（不能改變無標題情境下的 prompt、回傳格式或任何行為）。
- 有標題時，`topic` 直接採用使用者輸入的字串（不再讓 Gemini 推論主題），只讓 Gemini 產生 arXiv 查詢關鍵字，且該關鍵字必須同時參考「使用者標題」與「實際的資料探勘結果」兩者。
- 不改動 `/api/rag/arxiv/generate`、候選論文勾選、下載/建索引等後續流程；`topic` 欄位原封不動繼續往下傳遞。
- 本專案後端指令一律透過 `docker exec datamind-backend uv run <command>` 執行（host 端 `backend/.venv` 在 Windows 上是壞的）。前端指令（`npm run type-check` 等）直接在 host 執行。
- `backend/services/rag/paper_rag.py` 這條路徑目前完全沒有 pytest 測試（會真的打 Gemini API，沒有既有的 mock 慣例），本次驗證比照專案既有慣例，寫一支 `backend/scripts/` 底下的手動驗證腳本（`backend/pyproject.toml` 的 `testpaths = ["tests"]` 已經把 `scripts/` 排除在 pytest 自動收集範圍外，不會被誤判成自動化測試）。

---

### Task 1: 後端——`classify_topic` 支援選填的使用者標題

**Files:**
- Modify: `backend/services/rag/paper_rag.py`（`search_arxiv_candidates` 第 331-339 行、`classify_topic` 第 308-329 行）
- Modify: `backend/routes/rag.py`（`/arxiv/search` 路由，第 351-377 行）
- Create: `backend/scripts/test_arxiv_search_user_title.py`

**Interfaces:**
- Consumes: 無（本任務是這條路徑的起點）
- Produces:
  - `PaperRAGService.classify_topic(self, mining_results: dict, user_title: str | None = None) -> dict`——回傳 `{"topic": str, "arxiv_query": str}`。
  - `PaperRAGService.search_arxiv_candidates(self, mining_results: dict, user_title: str | None = None) -> dict`——回傳 `{"topic": str, "arxiv_query": str, "candidates": list}`。
  - `/api/rag/arxiv/search` 這支路由現在會讀取 JSON body 裡選填的 `user_title` 欄位。

Task 2 的前端會呼叫這支路由並帶上（或不帶）`user_title`，依賴以上回傳形狀不變。

- [ ] **Step 1: 修改 `classify_topic`，新增選填的 `user_title` 參數**

把 `backend/services/rag/paper_rag.py` 現有第 308-329 行：

```python
    def classify_topic(self, mining_results: dict) -> dict:
        """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢字串。"""
        results_text = self._format_datamind_output(mining_results)
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

改成：

```python
    def classify_topic(self, mining_results: dict, user_title: str | None = None) -> dict:
        """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢字串。

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

- [ ] **Step 2: 修改 `search_arxiv_candidates`，把 `user_title` 傳下去**

把現有第 331-339 行：

```python
    def search_arxiv_candidates(self, mining_results: dict) -> dict:
        """分類 mining_results 產生查詢字，查詢 arXiv 取得候選論文清單（不寫入向量庫）。"""
        classification = self.classify_topic(mining_results)
        candidates = arxiv_source.search_arxiv(classification["arxiv_query"])
        return {
            "topic": classification["topic"],
            "arxiv_query": classification["arxiv_query"],
            "candidates": candidates,
        }
```

改成：

```python
    def search_arxiv_candidates(self, mining_results: dict, user_title: str | None = None) -> dict:
        """分類 mining_results 產生查詢字，查詢 arXiv 取得候選論文清單（不寫入向量庫）。"""
        classification = self.classify_topic(mining_results, user_title)
        candidates = arxiv_source.search_arxiv(classification["arxiv_query"])
        return {
            "topic": classification["topic"],
            "arxiv_query": classification["arxiv_query"],
            "candidates": candidates,
        }
```

- [ ] **Step 3: 修改 `/arxiv/search` 路由，讀取選填的 `user_title`**

把 `backend/routes/rag.py` 現有第 351-377 行：

```python
@rag_bp.route("/arxiv/search", methods=["POST"])
def arxiv_search():
    """分類 DataMind 探勘結果並查詢 arXiv 候選論文（不寫入向量庫）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - topic       : AI 產生的研究主題
        - arxiv_query : 用於查詢 arXiv 的關鍵字字串
        - candidates  : 候選論文清單（arxiv_id/title/authors/year/abstract/pdf_url）
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        result = service.search_arxiv_candidates(data["mining_results"])
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.exception("arXiv 查詢失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

改成：

```python
@rag_bp.route("/arxiv/search", methods=["POST"])
def arxiv_search():
    """分類 DataMind 探勘結果並查詢 arXiv 候選論文（不寫入向量庫）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - user_title     : 使用者想要的論文標題（選填，留空則主題完全由 AI 推論）

    回傳：
        - topic       : 使用者標題（若有填）或 AI 產生的研究主題
        - arxiv_query : 用於查詢 arXiv 的關鍵字字串
        - candidates  : 候選論文清單（arxiv_id/title/authors/year/abstract/pdf_url）
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    user_title = data.get("user_title") or None
    service = get_paper_rag_service()

    try:
        result = service.search_arxiv_candidates(data["mining_results"], user_title)
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.exception("arXiv 查詢失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 4: 建立手動驗證腳本 `backend/scripts/test_arxiv_search_user_title.py`**

```python
"""手動驗證腳本：classify_topic() 在有/無 user_title 時的行為。

會真的呼叫 Gemini API（需要 GEMINI_API_KEY），不進 pytest 自動收集範圍
（backend/pyproject.toml 的 testpaths 已排除 scripts/）。用法：

    docker exec datamind-backend uv run python scripts/test_arxiv_search_user_title.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.rag.paper_rag import get_paper_rag_service  # noqa: E402

FAKE_MINING_RESULTS = {
    "class_distribution": {"counts": {"流失": 320, "未流失": 1680}, "imbalance_ratio": 5.25},
    "results": [
        {
            "preprocess_pipeline_index": 0,
            "preprocess_steps": [{"type": "標準化"}],
            "feature_engineering_steps": [{"type": "One-Hot 編碼"}],
        },
    ],
}


def main() -> None:
    service = get_paper_rag_service()

    print("=== 情境 1：無 user_title（維持現有全自動推論行為）===")
    result_auto = service.classify_topic(FAKE_MINING_RESULTS)
    print(f"topic: {result_auto['topic']}")
    print(f"arxiv_query: {result_auto['arxiv_query']}")
    assert result_auto["topic"], "無標題情境下 topic 不應該是空字串"
    assert result_auto["arxiv_query"], "無標題情境下 arxiv_query 不應該是空字串"

    print()
    print("=== 情境 2：有 user_title（主題直接採用使用者輸入）===")
    user_title = "機器學習於電信客戶流失預測之特徵重要性分析"
    result_titled = service.classify_topic(FAKE_MINING_RESULTS, user_title)
    print(f"topic: {result_titled['topic']}")
    print(f"arxiv_query: {result_titled['arxiv_query']}")
    assert result_titled["topic"] == user_title, "有標題情境下 topic 必須完全等於使用者輸入"
    assert result_titled["arxiv_query"], "有標題情境下 arxiv_query 不應該是空字串"
    assert result_titled["arxiv_query"] != result_auto["arxiv_query"], (
        "有標題跟無標題理論上應該問出不同的查詢字（人工檢查這條的合理性，"
        "非嚴格保證，Gemini 有極小機率剛好給出一樣的關鍵字）"
    )

    print()
    print("全部情境通過。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 執行手動驗證腳本**

```bash
docker exec datamind-backend uv run python scripts/test_arxiv_search_user_title.py
```

Expected: 印出兩種情境的 `topic`/`arxiv_query`，兩個 `assert` 都不噴錯，最後印出「全部情境通過。」。人工檢查：情境 2 印出來的 `arxiv_query` 應該要看起來跟「電信客戶流失預測」「特徵重要性」這個方向有關，而不是隨便兜出來的關鍵字。

- [ ] **Step 6: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/routes/rag.py backend/scripts/test_arxiv_search_user_title.py
git commit -m "feat: let classify_topic take an optional user-supplied paper title"
```

---

### Task 2: 前端——查詢前的標題輸入框

**Files:**
- Modify: `frontend/src/api/arxiv.ts`（`searchArxivCandidates`，第 16-33 行）
- Modify: `frontend/src/views/PaperSourcesView.vue`（模板第 17-77 行、`<script setup>` 第 82-153 行）

**Interfaces:**
- Consumes: Task 1 的 `/api/rag/arxiv/search` 路由，body 新增選填的 `user_title` 欄位；回傳形狀不變（`{success, topic, arxiv_query, candidates}`）。
- Produces: 無（此頁面沒有其他頁面依賴它的內部狀態）。

- [ ] **Step 1: 修改 `searchArxivCandidates`，新增選填的 `userTitle` 參數**

把 `frontend/src/api/arxiv.ts` 現有第 16-21 行：

```ts
export async function searchArxivCandidates (miningResults: Record<string, unknown>): Promise<ArxivSearchResult> {
  const response = await fetch('/api/rag/arxiv/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })
```

改成：

```ts
export async function searchArxivCandidates (
  miningResults: Record<string, unknown>,
  userTitle?: string,
): Promise<ArxivSearchResult> {
  const response = await fetch('/api/rag/arxiv/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      ...(userTitle ? { user_title: userTitle } : {}),
    }),
  })
```

其餘（`const result = ...` 開始的部分）保持不變。

- [ ] **Step 2: 修改 `PaperSourcesView.vue` 的模板——新增查詢前置畫面**

把現有第 17-77 行整段（`<section v-if="!hasLoaded">` 開始，到候選清單/生成按鈕那個 `</template>` 結束為止，也就是 `<template v-else>` 那個最外層 `v-else` 分支的完整內容）：

```html
      <section v-if="!hasLoaded" class="sources-status">
        載入中...
      </section>

      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/hub/projects/${projectId}/result`)">
          回到結果頁
        </v-btn>
      </section>

      <template v-else>
        <p v-if="topic" class="sources-topic">研究主題:{{ topic }}</p>

        <div v-if="loadingSearch" class="sources-status">
          正在分析資料並查詢 arXiv...
        </div>

        <div v-else-if="searchError" class="sources-status sources-status--error">
          {{ searchError }}
          <v-btn size="small" variant="text" @click="loadCandidates">重試</v-btn>
        </div>

        <div v-else-if="candidates.length === 0" class="sources-status">
          找不到相關文獻,請稍後再試。
        </div>

        <template v-else>
          <ul class="candidate-list">
            <li v-for="candidate in candidates" :key="candidate.arxiv_id" class="candidate-card">
              <label class="candidate-select">
                <input
                  v-model="selectedIds"
                  type="checkbox"
                  :value="candidate.arxiv_id"
                >
                <div class="candidate-body">
                  <p class="candidate-title">{{ candidate.title }}</p>
                  <p class="candidate-meta">
                    {{ candidate.authors }}
                    <span v-if="candidate.year">({{ candidate.year }})</span>
                  </p>
                  <p class="candidate-abstract">{{ candidate.abstract }}</p>
                </div>
              </label>
            </li>
          </ul>

          <div class="sources-actions">
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
            >
              {{ generating ? '生成中...' : `確認並生成論文 (${selectedIds.length})` }}
            </v-btn>
            <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
          </div>
        </template>
      </template>
```

改成（新增標題輸入框，並把原本「loading/error/空清單/候選清單」那整條 if-else-if 鏈包進 `<template v-if="hasSearched">`——這條鏈最後一段是沒有條件的 `v-else`，如果不整段包起來，還沒查詢過時 `hasSearched` 還是 `false`，但候選清單那個 `v-else` 依然會命中，畫面會在查詢前就跑出空的候選清單和「確認並生成論文 (0)」按鈕）：

```html
      <section v-if="!hasLoaded" class="sources-status">
        載入中...
      </section>

      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/hub/projects/${projectId}/result`)">
          回到結果頁
        </v-btn>
      </section>

      <template v-else>
        <div class="sources-title-input">
          <label class="sources-title-label" for="user-title-input">論文標題（選填）</label>
          <input
            id="user-title-input"
            v-model="userTitle"
            class="sources-title-field"
            placeholder="留空由 AI 自動判斷主題"
            type="text"
          >
          <v-btn class="bg-accent" color="accent" :loading="loadingSearch" size="small" @click="loadCandidates">
            {{ hasSearched ? '重新查詢' : '查詢文獻' }}
          </v-btn>
        </div>

        <template v-if="hasSearched">
          <p v-if="topic" class="sources-topic">研究主題:{{ topic }}</p>

          <div v-if="loadingSearch" class="sources-status">
            正在分析資料並查詢 arXiv...
          </div>

          <div v-else-if="searchError" class="sources-status sources-status--error">
            {{ searchError }}
            <v-btn size="small" variant="text" @click="loadCandidates">重試</v-btn>
          </div>

          <div v-else-if="candidates.length === 0" class="sources-status">
            找不到相關文獻,請稍後再試。
          </div>

          <template v-else>
            <ul class="candidate-list">
              <li v-for="candidate in candidates" :key="candidate.arxiv_id" class="candidate-card">
                <label class="candidate-select">
                  <input
                    v-model="selectedIds"
                    type="checkbox"
                    :value="candidate.arxiv_id"
                  >
                  <div class="candidate-body">
                    <p class="candidate-title">{{ candidate.title }}</p>
                    <p class="candidate-meta">
                      {{ candidate.authors }}
                      <span v-if="candidate.year">({{ candidate.year }})</span>
                    </p>
                    <p class="candidate-abstract">{{ candidate.abstract }}</p>
                  </div>
                </label>
              </li>
            </ul>

            <div class="sources-actions">
              <v-btn
                class="bg-accent"
                color="accent"
                :disabled="selectedIds.length === 0 || generating"
                @click="handleGenerate"
              >
                {{ generating ? '生成中...' : `確認並生成論文 (${selectedIds.length})` }}
              </v-btn>
              <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
            </div>
          </template>
        </template>
      </template>
```

- [ ] **Step 3: 修改 `<script setup>`——拿掉自動查詢，新增 `userTitle`/`hasSearched` 狀態**

把現有第 99-153 行：

```ts
  const topic = ref('')
  const candidates = ref<ArxivCandidate[]>([])
  const selectedIds = ref<string[]>([])

  const loadingSearch = ref(false)
  const searchError = ref<string | null>(null)

  const generating = ref(false)
  const generateError = ref<string | null>(null)

  async function loadCandidates (): Promise<void> {
    if (!miningResults.value) return
    loadingSearch.value = true
    searchError.value = null
    try {
      const result = await searchArxivCandidates(miningResults.value)
      topic.value = result.topic
      candidates.value = result.candidates
      selectedIds.value = []
    } catch (error) {
      searchError.value = error instanceof Error ? error.message : String(error)
    } finally {
      loadingSearch.value = false
    }
  }

  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
      generateError.value = error instanceof Error ? error.message : String(error)
    } finally {
      generating.value = false
    }
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
    if (miningResults.value) {
      loadCandidates()
    }
  })
```

改成：

```ts
  const topic = ref('')
  const userTitle = ref('')
  const hasSearched = ref(false)
  const candidates = ref<ArxivCandidate[]>([])
  const selectedIds = ref<string[]>([])

  const loadingSearch = ref(false)
  const searchError = ref<string | null>(null)

  const generating = ref(false)
  const generateError = ref<string | null>(null)

  async function loadCandidates (): Promise<void> {
    if (!miningResults.value) return
    hasSearched.value = true
    loadingSearch.value = true
    searchError.value = null
    try {
      const result = await searchArxivCandidates(miningResults.value, userTitle.value.trim() || undefined)
      topic.value = result.topic
      candidates.value = result.candidates
      selectedIds.value = []
    } catch (error) {
      searchError.value = error instanceof Error ? error.message : String(error)
    } finally {
      loadingSearch.value = false
    }
  }

  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
      generateError.value = error instanceof Error ? error.message : String(error)
    } finally {
      generating.value = false
    }
  }

  onMounted(() => {
    const state = loadWorkflowStateFromStorage(projectId.value)
    miningResults.value = state?.workflowResult ?? null
    hasLoaded.value = true
  })
```

- [ ] **Step 4: 補上輸入框的樣式**

在 `frontend/src/views/PaperSourcesView.vue` 的 `<style scoped>` 區塊裡，找到 `.sources-topic` 規則（可用內容比對，不用管確切行號），在它前面加入：

```css
  .sources-title-input {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  .sources-title-label {
    font-size: 13px;
    color: var(--text-secondary);
    white-space: nowrap;
  }

  .sources-title-field {
    flex: 1;
    min-width: 0;
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid var(--line);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text-main);
  }

  .sources-title-field:focus {
    outline: none;
    border-color: var(--color-accent);
  }
```

- [ ] **Step 5: 手動驗證**

本專案前端沒有自動化測試框架，驗證方式：

```bash
cd frontend
npm run type-check
```

Expected: 無錯誤。

```bash
docker restart datamind-frontend
```

輪詢直到就緒：

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/)" = "200" ]; do sleep 1; done
```

用瀏覽器進入一個有探勘結果的專案的「選擇參考文獻」頁（`/hub/projects/<id>/sources`），確認：
1. 進頁**不會**自動查詢——先看到標題輸入框（placeholder「留空由 AI 自動判斷主題」）跟「查詢文獻」按鈕，沒有候選清單、沒有 loading 中的文字。
2. 留空直接點「查詢文獻」，行為應該跟改動前完全一樣：跑出 loading 文字，之後顯示 AI 推論的「研究主題」跟候選論文清單。
3. 在標題輸入框填一個標題（例如「機器學習於電信客戶流失預測之特徵重要性分析」），點「查詢文獻」（此時按鈕文字應該變成「重新查詢」），確認查詢完後「研究主題」顯示的就是剛剛輸入的那個標題（一字不差），候選論文清單有更新、看起來跟輸入的標題方向相關。
4. 瀏覽器 DevTools console 沒有錯誤。

Expected: 上述 4 點全部符合。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/arxiv.ts frontend/src/views/PaperSourcesView.vue
git commit -m "feat: add optional paper-title input before arXiv reference search"
```
