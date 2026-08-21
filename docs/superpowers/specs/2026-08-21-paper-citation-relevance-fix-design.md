# 論文引用內容歸屬與檢索品質修復

日期：2026-08-21

## 背景

使用者反映：AI 生成論文時，同一篇被引用的來源論文，不管在全文哪個地方被引用、點開引用彈窗，顯示的摘錄內容永遠是同一段——實際上不同段落應該對應到來源論文裡不同、更貼切的段落。另外，多篇論文同時被引用時，選擇順序看起來像是固定順序而非依相關性排序。

追查後確認是兩個獨立、疊加的問題，外加一個已知但從未真正生效的功能缺口：

### 問題 1：後端 citation_map 歸屬錯誤（`backend/services/rag/paper_rag.py`）

`PaperRAGService.generate_paper()`（第 200-306 行）目前的執行順序：

1. 每個章節用一個固定查詢模板檢索 `top_k` 個候選 chunk，建立 `local_refs: Dict[int, dict]`（本地編號 → chunk + 全域 ref_id + score）
2. Gemini 生成章節文字，內文用本地編號 `[n]` 標記引用
3. `_localref_to_global()`（第 264-265 行）把本地編號轉成全域編號，同一篇論文若有多個 local_id 會被壓成同一個 global ref_id
4. **之後**才呼叫 `_build_citation_map()`（第 269-271 行），這時候傳進去的 `section_text_global` 已經是轉換後的文字，只剩全域編號

`_build_citation_map()`（第 908-960 行）解析文字裡的 `[gid]` 時，因為手上只有全域編號，無法回推「這句話當初引用的到底是 local_refs 裡哪一個 local_id」。第 936-939 行的寫法是：

```python
chunk_info = next(
    (info for info in local_refs.values() if info["global_ref_id"] == gid),
    None,
)
```

如果同一篇論文在這個章節的候選池裡有兩個以上不同的 chunk（例如 local_id 2 跟 7 都屬於同一篇論文），不管 LLM 這句話實際引用的是哪一個，`_build_citation_map` 永遠回傳「第一個符合這個 global_ref_id 的 local_ref」——也就是同一篇論文在整個章節裡，`relevant_chunk`/`similarity_score` 永遠是同一個值。

### 問題 2：前端把逐段落資料攤平成整篇共用（`frontend/src/utils/paperTransform.ts`）

即使問題 1 修好、`citation_map` 裡每個段落的 `sources[].relevant_chunk` 真的各自不同，前端目前的處理方式仍然會把它們攤平：

`buildCitations()`（第 34-52 行）替**每個 ref_id**（不是每次引用）建立一個 `Citation` 物件，`snippet` 抓的是：

```ts
const snippetEntry = result.citation_map
  .flatMap(entry => entry.sources)
  .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)
```

即整份文件裡**第一個**引用到這個 ref_id 的段落。`parseParagraphToContent()`（第 5-32 行）在把 Markdown 轉成 Tiptap 內容時，引用標記（`CitationMark`）的 `citationId` 純粹是 `cite-${全域編號}`，跟該段落在 `citation_map` 裡的位置完全無關。結果是：不管使用者點的是文件裡第幾次出現的 `[n]`，`PaperPage.vue` 的 `popoverCitation`（第 132-134 行，用 `report.citations.find(c => c.id === activeCitationId)` 查找）永遠回傳同一個、對應該 ref_id 唯一存在的 `Citation` 物件，彈窗內容自然不會因為點擊位置不同而變化。

這個「一個 ref_id 一個 Citation」的設計本身不能整個丟掉——`ReferencesSection.vue` 直接拿 `citations` 陣列渲染參考文獻列表，`PaperPage.vue` 的 `citationIndex`（第 152-158 行）也是用這個陣列的順序位置決定文中 `[n]` 顯示的編號。如果改成一個引用實例一個 `Citation`，同一篇論文會在參考文獻列表重複出現、編號也會跳號。

### 問題 3：`use_rerank` 是死代碼

`PaperRAGService.search()`（第 167-169 行）：

```python
def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
    raw = self._store.search(query, top_k=top_k)
    return [SearchResult(chunk=c, score=s) for c, s in raw]
```

`use_rerank` 參數完全沒被讀取，`SearchResult.rerank_score`（第 96 行）永遠是 `None`。`/api/rag/search` 這個路由甚至已經把 `rerank_score` 寫進回傳格式的文件註解裡（`backend/routes/rag.py`），但實際上這個欄位從來沒被填過值——是一個「看起來存在、實際上完全沒生效」的功能。

檢索排序目前完全依賴 `VectorStore.search()`（`backend/services/rag/vector_store.py`）的 embedding cosine 相似度（`sentence-transformers` 可用時）或 TF-IDF 相似度（fallback）。這不是「照順序」，是有做相似度排序的，但向量相似度把整段查詢跟整段候選文字各自壓縮成一個向量再比對，精細度有限，容易出現「大方向相關但不是最貼切」的候選排到前面。

## 目標

1. 同一篇來源論文在文中不同段落被引用時，引用彈窗顯示的摘錄要對應到**該段落實際引用的那個 chunk**，不再整篇共用同一段
2. 章節候選池的排序要用真正的相關性重排（reranker），取代目前形同虛設的 `use_rerank` 參數
3. 參考文獻列表、文中引用編號的既有行為（不重複列出、連續編號）維持不變
4. 不改變任何對外 API 的欄位形狀（`citation_map`、`references` 結構不變），純粹修內部邏輯與新增前端可選欄位

## 非目標

- 不把檢索粒度從「整章節一個查詢」改成「逐段落/逐論點各自查詢」（已經跟使用者確認過，這是後續可能的加強，不在這次範圍）
- 不修「一句話同時引用多篇論文寫成 `[2][5]` 這種連續格式時，前端只會抓第一個編號建立可點擊標記」這個既有限制（跟這次問題無關，另開任務）
- 不動 `RagPaper`/`RagChunk`（來源論文庫本身的新增/管理）、不動 `backend/models/report.py` 那組沒被使用的 SQLAlchemy Report/Citation model（既有死代碼，不在這次範圍）

## 設計

### 1. 後端：citation_map 改用原始本地編號直接查表

`generate_paper()` 呼叫順序調整：`_build_citation_map()` 提前到 `_localref_to_global()` **之前**執行，傳入尚未轉換的 `section_text`（本地編號）而非 `section_text_global`。

`_build_citation_map()` 的解析邏輯跟著改，有一個容易漏掉的細節：`_localref_to_global()` 用的正則是 `r"\[(\d+(?:\s*,\s*\d+)*)\]"`——會比對到 `[2, 5]` 這種同一個中括號內用逗號分隔多個本地編號的組合格式（LLM 有時會這樣寫），不是只有單一數字的 `[n]`。目前 `_build_citation_map()` 用的 `r"\[(\d+)\]"` 之所以夠用，是因為它解析的是**轉換後**的文字，此時組合格式早就被 `_localref_to_global()` 拆成一個個獨立的 `[gid][gid]`。改成解析轉換前的原始文字後，如果沿用 `r"\[(\d+)\]"`，遇到 `[2, 5]` 這種組合格式會直接比對失敗、整個漏掉。

因此正則要改成跟 `_localref_to_global()` 共用同一個 pattern（抽成模組層級常數避免兩處各寫一份、之後改一邊忘記改另一邊），比對到的每個中括號群組再用 `re.findall(r"\d+", ...)` 拆出裡面所有本地編號。每個本地編號直接 `local_refs.get(local_id)` 精準取值，不再用 `global_ref_id` 反查猜測；取到 chunk 後才轉一次 `info["global_ref_id"]` 存進 `cited_ref_ids`／`sources[].ref_id`，維持對外欄位格式不變。

`cited_gids` 目前是「段落內出現的全域編號」去重後的集合，`sources` 陣列一個 ref_id 一筆——這個去重 by ref_id 的既有結構繼續維持不變。唯一新增的情況是：同一個段落如果用了兩個不同的本地編號但剛好指向同一篇論文（例如 `[2][7]` 剛好都是同一篇），沿用去重規則時只留一筆，選用**文字裡先出現的那個本地編號**對應的 chunk（依閱讀順序決定，簡單且結果穩定）——這種「同一段落內用不同 chunk 重複引用同一篇論文」的情況本來就極少見，不是這次要修的「不同段落顯示同一段」的核心症狀，選第一個即可，不用另外設計仲裁邏輯。

呼叫順序變動後，`sections_text[section_name]` 賦值（用來組 `paper_markdown`）維持用轉換後的 `section_text_global`，不受影響——只有「餵給 `_build_citation_map` 的是哪一份文字」這件事改變。

### 2. 後端：接上真正的 reranker

新增 `backend/services/rag/reranker.py`：

```python
class Reranker:
    """
    用 CrossEncoder 對查詢/候選 pair 重新評分排序。
    載入失敗（模型下載失敗等）就優雅降級成 no-op，不讓生成流程掛掉。
    """
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None
        self._try_load()

    def _try_load(self) -> None: ...  # 同 Embedder 的 try/except ImportError + 一般 Exception 都要接住

    @property
    def available(self) -> bool:
        return self._model is not None

    def rerank(self, query: str, candidates: list[tuple[Chunk, float]]) -> list[tuple[Chunk, float, float]]:
        """回傳 (chunk, original_score, rerank_score)，依 rerank_score 降冪排序。"""
```

用的是 `sentence-transformers` 套件內建的 `CrossEncoder`（跟現有 `Embedder` 用的 `SentenceTransformer` 同一個套件，`requirements.txt` 已經有，不用新增依賴）。預設模型 `BAAI/bge-reranker-base`，跟現有 embedding model `bge-small-zh-v1.5` 同語系；可用 `RAG_RERANK_MODEL` 環境變數覆蓋，比照 `RAG_EMBED_MODEL` 的既有慣例。

`PaperRAGService.__init__` 比照 `self._embedder` 的建立方式，新增 `self._reranker = Reranker(model_name=os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-base"))`（eager 載入，跟 embedder 一致）。

`search()` 改寫：

```python
def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
    overfetch_k = top_k * 4 if use_rerank and self._reranker.available else top_k
    raw = self._store.search(query, top_k=overfetch_k)

    if use_rerank and self._reranker.available and raw:
        reranked = self._reranker.rerank(query, raw)
        return [
            SearchResult(chunk=c, score=orig_score, rerank_score=rr_score)
            for c, orig_score, rr_score in reranked[:top_k]
        ]

    return [SearchResult(chunk=c, score=s) for c, s in raw[:top_k]]
```

`_build_citation_map()` 寫入 `similarity_score` 時改成優先取 `chunk_info["rerank_score"]`，沒有（reranker 不可用、或 `use_rerank=False`）才退回 `chunk_info["score"]`。`local_refs` 儲存的 dict 需要多存一個 `rerank_score` 欄位（來自 `SearchResult.rerank_score`）。

`generate_citation()`、`/api/rag/search` 路由（既有的獨立搜尋功能，不只是論文生成流程）呼叫的都是同一個 `search()`，會自動一起受益，不用個別修改。

### 3. 前端：引用彈窗依實際點擊的段落顯示對應內容

**前提確認**（已對照程式碼驗證，非推測）：`_assemble_paper()`（後端）組 `paper_markdown` 時，每個章節固定是 `## {section_name}\n\n{section_text_global}`，章節之間用 `\n\n---\n\n` 相接。前端 `transformArxivResultToPaperReport()` 目前切割 `paper_markdown` 也是先按 `\n\n---\n\n` 分區塊，取出 `heading`（= 章節名稱）與 `body`，再對 `body` 做 `split('\n\n')` 取得段落陣列——這與後端 `_build_citation_map()` 對 `section_text` 做 `split("\n\n")` 產生 `paragraph_index` 的方式完全一致（因為兩邊處理的是同一份文字）。也就是說，前端重新切出來的「第幾個章節的第幾個段落」天生就能對上 `citation_map` 裡的 `section` + `paragraph_index`，**不需要後端額外傳遞任何新資料**。

改動：

**`paperTransform.ts`**
- `transformArxivResultToPaperReport()` 迭代每個章節的段落時，改用 `.entries()` 取得段落在該章節內的索引，並用 `(heading, index)` 去 `result.citation_map` 裡找對應的條目（`entry.section === heading && entry.paragraph_index === index`），把找到的 `entry.sources`（可能是 `undefined`，代表這段沒有引用）一併傳給 `parseParagraphToContent()`
- `parseParagraphToContent(paragraphText, sources?)` 建立引用 mark 時，除了現有的 `citationId`，多帶一個 `relevantChunk` 屬性：用當下這個 `[n]` 的編號去 `sources` 陣列裡找 `ref_id` 相符的項目，取其 `relevant_chunk`；找不到就是 `null`（沿用目前行為，不影響任何東西）
- `buildCitations()` 維持不變——`citations` 陣列還是一個 ref_id 一筆，参考文獻列表、編號邏輯完全不動

**`CitationMark.ts`**
新增一個屬性：

```ts
relevantChunk: {
  default: null,
  parseHTML: element => element.getAttribute('data-relevant-chunk'),
  renderHTML: attributes =>
    attributes.relevantChunk ? { 'data-relevant-chunk': attributes.relevantChunk } : {},
}
```

**`PaperPage.vue`**
`popoverCitation` computed 改成：先用既有方式找到該 ref_id 對應的共用 `Citation`（書目資訊來源），再看 `popoverTarget.value?.dataset.relevantChunk` 是否有值，有的話用它覆蓋 `snippet` 欄位；沒有（例如 mock 資料、非 arXiv 生成的內容，這些內容天生沒有這個屬性）就維持用 `Citation` 自己的 `snippet` 當退回值，行為與現在完全一樣。

`citationIndex`、`ReferencesSection.vue`、`CitationPopover.vue` 的 props 形狀都不需要改動——`CitationPopover` 收到的還是一個 `Citation` 形狀的物件，只是 `snippet` 欄位的來源在 `PaperPage.vue` 這一層被替換掉。

## 資料流總覽

```
後端 generate_paper()
  └─ 章節檢索 → search()（新：overfetch + rerank）→ local_refs（新：含 rerank_score）
  └─ Gemini 生成本地編號文字
  └─ _build_citation_map()（新順序：用本地編號原文，直接查 local_refs）
  └─ _localref_to_global()（維持在後面，只影響最終顯示的 paper_markdown）
  └─ 回傳 paper_markdown + citation_map（欄位形狀不變，但同段落內容不再被錯誤合併）

前端 transformArxivResultToPaperReport()
  └─ 依 \n\n---\n\n / \n\n 切出 (section, paragraph_index)（新：對照 citation_map 找該段落的 sources）
  └─ parseParagraphToContent()（新：mark 多帶 relevantChunk）
  └─ CitationMark 渲染（新：data-relevant-chunk）

PaperPage.vue 點擊引用
  └─ popoverCitation（新：優先用點擊標記自帶的 relevantChunk 覆蓋 snippet）
```

## 測試計畫

- 後端：針對 `_build_citation_map` 寫單元測試，構造一個章節文字，其中同一篇論文用兩個不同 local_id 在不同段落被引用，驗證兩個段落的 `sources[].relevant_chunk` 確實不同、且各自對應正確的 chunk 內容
- 後端：`Reranker` 在 `sentence-transformers`/模型不可用時的降級路徑要有測試覆蓋（`available` 回傳 `False`、`search()` 正常運作不拋錯）
- 前端：對 `transformArxivResultToPaperReport()` 補測試，構造一個 mock `ArxivGenerateResult`，其中同一個 ref_id 在兩個不同段落各自有不同的 `relevant_chunk`，驗證兩個對應的 citation mark 的 `relevantChunk` 屬性確實不同
- 手動驗證：用瀏覽器實際生成一篇會引用同一篇來源論文兩次以上的論文（或用暫時的假資料模擬），點擊文中不同位置的同一個 `[n]`，確認彈窗內容不同；確認參考文獻列表沒有重複列出、編號連續正確

## 已知限制（本次不修）

- 一句話同時引用多篇論文寫成 `[2][5]` 這種連續 bracket 格式時，前端只會抓第一個編號建立可點擊標記
- 檢索粒度仍是整章節一個固定查詢，不是逐段落/逐論點各自檢索——reranker 只能在「同一個查詢撈出來的候選池」裡面重新排序，沒辦法讓完全不同主題的候選被撈進來
