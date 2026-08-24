# RAG 論文索引依 Project 隔離 Design Spec

## 背景

這是「上線前多人並發準備」拆解出的子專案 #2（子專案 #1「補齊 API 存取控制」已完成並上線，見 `docs/superpowers/plans/` 相關紀錄）。

現況：`backend/services/rag/paper_rag.py` 的 `PaperRAGService` 是一個 process 全域單例（`get_paper_rag_service()` 惰性建立、快取在模組層級的 `_instance`），底下只有**一份**共用的 `VectorStore`（`backend/services/rag/vector_store.py`），固定路徑 `artifacts/rag_index/`，用三個攤平的檔案（`chunks.json`／`papers.json`／`embeddings.npy`）持久化，完全沒有 `project_id`/`user_id` 概念——不管哪個使用者、哪個 project 上傳或生成的論文，全部混在同一份索引裡，彼此互相看得到、也互相刪得到。

子專案 #1 已經把 `rag.py` 的 14 條路由都補上 `@login_required`，並在 `ingest_arxiv_selection()`（`/arxiv/generate` 用到，也是目前唯一有接上 UI、會寫入索引的路徑）緊急拿掉了一行無條件 `self.clear()`——原本那行會在任何人生成論文時把所有人的索引整個清空，不只是看得到彼此、是會砍到彼此的資料。這個緊急修復是過渡措施，重複上傳同一篇論文仍會造成索引內容重複，本次一併解決。

## 範圍

把「資料庫是每個人只能看到自己的還是共用」這個問題，從 RAG 論文索引這個子系統徹底解決：改成以 **project** 為隔離單位（跟 `Framework`／`Dataset`／`WorkflowState` 現有的隔離模式一致），儲存層從檔案改成資料庫（重新啟用目前完全沒人用、已經有 `project_id` 外鍵和 pgvector 欄位的 `rag_papers`／`rag_chunks` 兩張表）。

- **在範圍內**：`PaperRAGService` 儲存層改寫、`rag_papers`/`rag_chunks` 的 schema 修正、`rag.py` 8 條會碰到儲存的路由補 `project_id` + 擁有權驗證、前端唯一的即時呼叫點（`/arxiv/generate`）補送 `project_id`、刪除已被取代的檔案式 `VectorStore` 及其測試。
- **不在範圍內**：`Embedder`／`Reranker`（sentence-transformers 模型）維持共用單例，不拆分；`rag.py` 另外 6 條純 Gemini 呼叫（`insight`／`tab-insight`／`chat`／`score-paper`／`structured-analysis`／`arxiv/search`）完全不碰儲存，不需要改；子專案 #3（正式部署設定，例如換成多 worker）留待之後——這次改成資料庫儲存，剛好也讓子專案 #3 不用再回頭重做這塊。
- 舊索引資料（`artifacts/rag_index/` 底下現有的檔案）直接捨棄，不做搬遷（已與使用者確認：目前是開發/測試階段的混合資料，沒有保留價值）。

## 儲存層設計：`DbVectorStore`

新增 `backend/services/rag/db_vector_store.py`，取代 `backend/services/rag/vector_store.py`。維持與現有 `Chunk` dataclass（`backend/services/rag/chunker.py`）完全相同的介面——`PaperRAGService.search()`／`generate_citation()`／`generate_paper()`／`Reranker.rerank()` 全部只操作 `Chunk`／`SearchResult`，不知道底層是檔案還是資料庫，所以**這幾個方法的內部邏輯不需要修改**，只需要多傳一個 `project_id` 參數。

```python
class DbVectorStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder  # 共用單例，注入進來，不自己持有

    def create_paper(self, project_id: int, title: str, metadata: dict) -> str:
        """寫一筆 RagPaper，回傳 str(RagPaper.id) 當 paper_id"""

    def add_chunks(self, project_id: int, chunks: list[Chunk]) -> None:
        """幫 chunks 算向量（沿用 embedder.encode），寫進 RagChunk；
        embedder.backend != "transformers" 時只存 content，之後用 TF-IDF 現算"""

    def search(self, project_id: int, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        """transformers 模式：pgvector cosine_distance，SQL 直接 WHERE project_id 過濾；
        tfidf 模式：抓這個 project 自己的 chunks 進記憶體，用現有 sklearn TF-IDF 邏輯現算
        （比現在的行為更正確——現在 TF-IDF 備援其實是跟全部人的資料混著算分）"""

    def delete_paper(self, project_id: int, paper_id: str) -> bool: ...
    def clear(self, project_id: int) -> None: ...
    def get_status(self, project_id: int) -> dict: ...
    def find_by_arxiv_id(self, project_id: int, arxiv_id: str) -> "RagPaper | None":
        """給 ingest_arxiv_selection 判重複用"""
```

**向量距離**：確認過 `Embedder.encode()`（`embedder.py:49-55`）呼叫時帶 `normalize_embeddings=True`，輸出的向量已經是 L2-normalized，跟 pgvector 的 `cosine_distance`（`<=>` 運算子）語意完全對得上（`1 - cosine_distance = 內積 = 現有 _transformer_scores() 算的 cosine similarity`），排序方式對調（distance 由小到大＝similarity 由大到小），score 值換算回 `1 - distance` 回傳，維持跟現在 `score` 欄位一樣的意義。

**`Chunk` 物件重建**：從 DB 查詢結果組回 `Chunk` 時：
- `chunk_id = str(RagChunk.id)`（chunker 產生的 uuid 不再使用，DB 的自增 id 本身就是唯一識別）
- `paper_id = str(RagChunk.paper_id)`（即 `RagPaper.id`，維持字串型別跟現有介面、前端型別 `paper_id: string` 一致，不用改前端型別定義）
- `title = RagPaper.title`
- `metadata = {"author": RagPaper.author, "year": RagPaper.year, "arxiv_id": RagPaper.arxiv_id}`，若 `arxiv_id` 存在再補一個 `"journal": f"arXiv:{arxiv_id}"`（現有 `ingest_arxiv_selection` 傳進來的 `journal` 欄位其實永遠是這個推導值，不需要另外存欄位）

## `PaperRAGService` 改動

`__init__`（`paper_rag.py:104` 附近）：把 `self._store = VectorStore(index_dir=..., embedder=self._embedder)` 換成 `self._store = DbVectorStore(embedder=self._embedder)`，移除 `RAG_INDEX_DIR` 環境變數的讀取（不再需要）。

以下 8 個方法簽章加一個 `project_id: int` 參數，內部把 `self._store.xxx(...)` 呼叫改成 `self._store.xxx(project_id, ...)`，邏輯本身不變：

| 方法 | 改動 |
|---|---|
| `add_paper` | 改成先 `paper_id = self._store.create_paper(project_id, title, metadata)`，再用這個 id 呼叫 `self._chunker.chunk(...)`，最後 `self._store.add_chunks(project_id, chunks)`（DB 自增 id 必須先產生才能拿來標記 chunk，順序跟現在「先生 uuid 再切」相反） |
| `search` | 加 `project_id`，往下傳 |
| `generate_citation` | 加 `project_id`，往下傳給內部的 `self.search` |
| `generate_paper` | 加 `project_id`，往下傳給每個章節的 `self.search` |
| `ingest_arxiv_selection` | 加 `project_id`；新增去重複邏輯——`add_paper` 前先 `self._store.find_by_arxiv_id(project_id, candidate["arxiv_id"])`，找到就跳過（視為已存在），不再重複塞進索引 |
| `get_status` | 加 `project_id`，往下傳 |
| `delete_paper` | 加 `project_id`，往下傳 |
| `clear` | 加 `project_id`，往下傳 |

其餘 6 個純 Gemini 方法（`generate_insight`／`generate_tab_insight`／`score_paper`／`generate_structured_analysis`／`chat_about_results`／`search_arxiv_candidates`／`classify_topic`）完全不動。

## Migration：修正 `rag_papers`/`rag_chunks` 的 schema 缺陷

兩張表目前完全沒有任何程式碼讀寫（`grep -r "RagPaper\|RagChunk" backend` 只有 model 定義本身跟 `__init__.py` 的 import），改動風險為零。新增一支 migration：

- `rag_chunks.paper_id` 外鍵補上 `ondelete="CASCADE"`（現在刪 `RagPaper` 若底下還有 `RagChunk` 會因為外鍵限制失敗，或留下孤兒資料——兩張表都空的，直接修正外鍵比在應用層手動兩步刪除更乾淨）
- `rag_papers.project_id`、`rag_chunks.paper_id` 各加一個索引（Postgres 不會自動幫外鍵欄位建索引，兩張表現在完全沒有索引）
- `rag_chunks.embedding` 目前是 `nullable=False`，但 `Embedder` 落在 TF-IDF 備援模式時沒有向量可存——這次一併把這個欄位改成 `nullable=True`，`add_chunks` 在 tfidf 模式下該欄位存 `NULL`，只存 `content`
- `rag_chunks.embedding` 的向量維度（目前寫死 `Vector(384)`，`backend/models/rag_paper.py:9` 的 `EMBEDDING_DIM = 384`）**實作時第一步要實際跑一次 `Embedder("BAAI/bge-small-zh-v1.5").encode(["test"]).shape[1]` 驗證**，因為這個數字從來沒有被真正接上資料庫驗證過；如果跟實際輸出維度不符，migration 要用驗證後的正確值，不能照抄現有寫死的 384
- 不加向量相似度索引（ivfflat/hnsw）——目前資料量小，brute-force 掃描更準也夠快，之後論文數量真的變多再加

## 路由層改動（`backend/routes/rag.py`）

以下 8 條路由的 request 都要求帶 `project_id`（POST 走 JSON body，`/status` 是 GET 走 query string），驗證方式比照 `report.py` 現有的 `_get_owned_project`（`Project.query.get(project_id)`，`user_id != current_user.id` 就回 404）：

`/upload`、`/search`、`/cite`、`/status`、`/clear`、`/paper/<paper_id>` DELETE、`/generate-paper`、`/arxiv/generate`

另外 6 條（`/arxiv/search`、`/insight`、`/tab-insight`、`/score-paper`、`/structured-analysis`、`/chat`）不動——這些純粹是拿前端傳來的 `mining_results`/文字丟給 Gemini，完全不碰 `PaperRAGService` 的儲存方法。

## 前端改動

探勘過，這 8 條路由裡目前**只有 `/arxiv/generate` 真的有接上 UI**（其他 7 條沒有任何呼叫點，是還沒串接的 API 或已廢棄）：

- `frontend/src/api/arxiv.ts` 的 `generateFromArxiv()`：參數加 `projectId: string`，request body 加 `project_id: params.projectId`
- 呼叫點 `frontend/src/views/PaperSourcesView.vue:151` 的 `handleGenerate()`：呼叫時多帶 `projectId: projectId.value`（該元件第 112 行已經有 `projectId = computed(() => route.query.project as string | undefined)`）；若 `projectId.value` 是 `undefined` 應提前擋下並提示錯誤，不要送出一個沒有 project 的請求

## 清理死碼

- 刪除 `backend/services/rag/vector_store.py`（已被 `DbVectorStore` 取代）
- 刪除 `backend/tests/test_vector_store_self_heal.py`（測試對象已刪除）
- `artifacts/rag_index/` 目錄不再使用，不需要程式碼特別清理（單純不會再寫入）

## 錯誤處理 / 相容性

- `project_id` 缺漏或不是合法整數：回 400
- `project_id` 存在但不屬於目前登入的使用者：回 404（不回 403，避免洩漏「這個 project 存在，只是不是你的」——比照 `project.py`/`report.py` 現有慣例）
- `Embedder` 落在 TF-IDF 備援模式時，`search()` 抓這個 project 自己的 chunks 進記憶體現算——如果這個 project 完全沒有論文，直接回空結果，不要因為 corpus 是空的讓 sklearn 的 `TfidfVectorizer.fit_transform` 噴例外
- transformer 模式的 SQL 相似度查詢只比對 `embedding IS NOT NULL` 的 chunk——`Embedder` 的 backend 是進程啟動時決定、不會中途切換，但如果曾經在 tfidf 模式下寫入過資料、後來重啟後 transformer 模型可用了，舊資料會沒有向量，查詢時單純跳過這些列，不視為錯誤
- `ingest_arxiv_selection` 的去重複判斷（`find_by_arxiv_id`）只在同一個 project 內比對，不同 project 各自獨立，允許同一篇 arXiv 論文被不同 project 各自引用一份

## 測試

- `test_paper_rag_search.py`、`test_paper_rag_citation_map.py` 目前繞過 `PaperRAGService.__init__`、直接把假的 `_store` 物件注入 `service._store`（不連網、不碰真的儲存層）。這個手法可以維持，但測試裡呼叫 `service.search(...)` 等方法、以及假 `_store` 物件本身的方法簽章，都要補上 `project_id` 參數（值可以隨便給一個固定整數，反正是假物件不會真的過濾）——這是必要的小改動，不是「可能要改」
- 跑過上述調整後，`backend/tests/` 全部測試要能通過
- 手動驗證：兩個不同 project 各自上傳論文，互相搜尋（`/search`）、生成引用（`/cite`）都看不到對方的論文
- 手動驗證：project A 刪除自己的論文成功；帶 project B 的 id 但傳 project A 的 `paper_id` 應該回「找不到」
- 手動驗證：`/arxiv/generate` 走一次完整流程，確認生成的論文內容、`references`、`citation_map` 格式跟改動前一致（因為 `Chunk` 介面沒變，這裡預期是完全一致的輸出格式）
- 手動驗證：同一個 project 對同一篇 arXiv 論文重複執行 `/arxiv/generate` 兩次，第二次不會產生重複的論文條目
- migration 跑一次 `alembic upgrade head`／`downgrade` 確認可逆
