# 論文引用內容歸屬與檢索品質修復 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修好「同一篇來源論文不管在文中哪裡被引用，彈窗永遠顯示同一段摘錄」的 bug，並讓目前完全沒生效的 `use_rerank` 參數接上真正的 cross-encoder reranker。

**Architecture:** 後端 `paper_rag.py` 的 citation_map 建置要在本地引用編號轉全域編號**之前**執行、直接查表而非用 global_ref_id 反查猜測；新增一個獨立的 `Reranker` 類別接上 `search()`。前端 `paperTransform.ts` 在把 Markdown 轉成 Tiptap 內容時，比照後端的段落切法找出每個段落對應的 `citation_map` 條目，把該段落實際引用到的 chunk 內容存進引用標記的新屬性 `relevantChunk`（跟參考文獻的書目資訊分開存），`PaperPage.vue` 顯示彈窗時優先用被點擊那個標記自帶的內容。

**Tech Stack:** Python 3.11 / Flask（後端），`sentence-transformers`（既有依賴，`CrossEncoder` 拿來做 reranker，不用新增套件），Vue 3 + TypeScript + Tiptap（前端）。

**Spec:** `docs/superpowers/specs/2026-08-21-paper-citation-relevance-fix-design.md`

## Global Constraints

- 不改變任何對外 API 的欄位形狀（`citation_map`、`references` 結構不變）
- 參考文獻列表不重複列出、文中引用編號連續，這個既有行為不能壞
- 後端測試不連網、不需要 `GEMINI_API_KEY`（比照 `backend/tests/test_gemini_field_mapping.py` 的既有慣例：用假物件，不呼叫真的模型）
- 前端目前沒有設定任何測試框架（沒有 vitest，`package.json` 沒有 test script）——這份 plan 不新增測試框架，前端驗證一律用瀏覽器手動驗證（比照這個 session 稍早 A/B/D 三個功能的驗證方式：暫時的 dev-only 路由，驗證完刪掉，不留痕跡）
- 後端跑測試指令：在 `backend/` 目錄下 `uv run pytest tests/<file> -v`
- **前置環境修復（已完成，執行 Task 1/2 前不用再處理）**：`backend/.venv` 原本因為缺了 `Scripts`/`bin` 目錄而無法用，已經用 PowerShell 的 `Remove-Item -Recurse -Force` 手動移除、讓 `uv run` 重新建置乾淨的 venv，並確認既有的 19 個測試全過（baseline 乾淨）
- **`sentence-transformers` 需要真的加成依賴**：`requirements.txt` 有列這個套件，但那份檔案已經跟 `pyproject.toml`/`uv.lock` 脫鉤、沒人維護，實際上這個套件從沒被裝進這個專案的環境。Task 2 動工前要先 `uv add sentence-transformers`（已手動驗證過：因為 `mineru`/`openai-whisper` 已經帶了 `torch`/`transformers` 這些底層套件，`uv add` 只需要多裝 1 個套件、幾秒鐘完成，不會觸發大量下載或版本衝突）

---

## Task 1：修復 citation_map 段落級歸屬（`_build_citation_map` 改用本地編號直接查表）

**Files:**
- Modify: `backend/services/rag/paper_rag.py`（`_localref_to_global` 第 892-905 行、`_build_citation_map` 第 908-960 行、`generate_paper` 第 264-271 行呼叫順序、模組頂部新增共用正則常數）
- Test: `backend/tests/test_paper_rag_citation_map.py`（新檔案）

**Interfaces:**
- Consumes: 無（這是最底層的修復，不依賴其他任務）
- Produces: `PaperRAGService._build_citation_map(section_name, section_text, local_refs, global_ref_list, citation_map)` —— 簽名不變，但現在吃的是**轉換前**（本地編號）的 `section_text`，且每個 `citation_map` entry 的 `sources[].relevant_chunk`/`similarity_score` 會正確對應該段落實際引用的 chunk。`local_refs[local_id]` 的 dict 之後（Task 2）會多一個 `"rerank_score"` key，這個任務要讓讀取端用 `.get("rerank_score")` 讀取（不能用 `[...]` 直接索引，因為 Task 1 完成時這個 key 還不存在）。

- [ ] **Step 1: 寫失敗的測試——驗證同一篇論文在不同段落被引用時，取到的是各自正確的 chunk**

建立 `backend/tests/test_paper_rag_citation_map.py`：

```python
"""_build_citation_map 的段落級歸屬測試。

不連網：直接呼叫 staticmethod，不建構 PaperRAGService（會需要 GEMINI_API_KEY），
不需要任何外部依賴。
"""

from dataclasses import dataclass

from services.rag.paper_rag import PaperRAGService


@dataclass
class FakeChunk:
    paper_id: str
    content: str


def make_local_refs():
    return {
        1: {
            "global_ref_id": 1,
            "chunk": FakeChunk(paper_id="paper-a", content="空氣品質與心血管疾病的關聯研究"),
            "score": 0.91,
        },
        2: {
            "global_ref_id": 1,  # 跟 local_id=1 同一篇論文，不同 chunk
            "chunk": FakeChunk(paper_id="paper-a", content="PM2.5 濃度與呼吸道發炎反應"),
            "score": 0.85,
        },
        3: {
            "global_ref_id": 2,
            "chunk": FakeChunk(paper_id="paper-b", content="糖尿病患者的血糖控制策略"),
            "score": 0.88,
        },
    }


GLOBAL_REF_LIST = [
    {"ref_id": 1, "title": "Paper A", "author": "Wang", "year": "2024"},
    {"ref_id": 2, "title": "Paper B", "author": "Lee", "year": "2023"},
]


def test_same_paper_cited_in_different_paragraphs_gets_correct_chunk_each_time():
    local_refs = make_local_refs()
    section_text = "第一段引用了空氣品質相關的研究[1]。\n\n第二段引用同一篇論文但不同段落[2]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 2

    para0_sources = citation_map[0]["sources"]
    assert len(para0_sources) == 1
    assert para0_sources[0]["ref_id"] == 1
    assert para0_sources[0]["relevant_chunk"] == "空氣品質與心血管疾病的關聯研究"

    para1_sources = citation_map[1]["sources"]
    assert len(para1_sources) == 1
    assert para1_sources[0]["ref_id"] == 1
    # 這是這次修的核心 bug：兩段引用同一篇論文，但實際引用的 chunk 不同，
    # 修好之前這裡會跟 para0 顯示一模一樣的內容
    assert para1_sources[0]["relevant_chunk"] == "PM2.5 濃度與呼吸道發炎反應"


def test_combo_bracket_format_is_parsed_from_raw_local_id_text():
    """LLM 有時會把多個引用寫成 [1, 3] 這種逗號組合格式，不是分開的 [1][3]。"""
    local_refs = make_local_refs()
    section_text = "同時支持兩個論點[1, 3]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 1
    assert citation_map[0]["cited_ref_ids"] == [1, 2]
    sources_by_ref = {s["ref_id"]: s for s in citation_map[0]["sources"]}
    assert sources_by_ref[1]["relevant_chunk"] == "空氣品質與心血管疾病的關聯研究"
    assert sources_by_ref[2]["relevant_chunk"] == "糖尿病患者的血糖控制策略"


def test_same_paragraph_citing_same_paper_twice_keeps_first_occurrence():
    """同一段落用兩個不同 local_id 重複引用同一篇論文：取文字裡先出現的那個。"""
    local_refs = make_local_refs()
    section_text = "先引用[2]再引用同一篇的另一段[1]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 1
    assert citation_map[0]["cited_ref_ids"] == [1]
    assert citation_map[0]["sources"][0]["relevant_chunk"] == "PM2.5 濃度與呼吸道發炎反應"
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `cd backend && uv run pytest tests/test_paper_rag_citation_map.py -v`
Expected: FAIL —— 第一個測試會失敗在 `para1_sources[0]["relevant_chunk"]`，因為現在的實作對兩段都回傳同一個 chunk；第二個測試會失敗，因為現在的正則 `r"\[(\d+)\]"` 比對不到 `[1, 3]` 這種組合格式，`citation_map` 會是空的。

- [ ] **Step 3: 在 `paper_rag.py` 模組頂部新增共用的引用正則常數**

在 `backend/services/rag/paper_rag.py` 現有的 `_DEFAULT_TOP_K = 5`（第 43 行）之後加：

```python
# 引用標記的正則，[n] 或 [n, m, ...] 組合格式都要比對到。
# _localref_to_global 跟 _build_citation_map 共用同一份，避免兩處各寫一份、之後改一邊忘記改另一邊。
_CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
```

- [ ] **Step 4: 改寫 `_localref_to_global` 使用共用常數（行為不變，純粹去重複）**

把第 892-905 行的 `_localref_to_global`：

```python
    @staticmethod
    def _localref_to_global(text: str, local_refs: Dict[int, dict]) -> str:
        """將章節內的本地 [n]（含 [n, m] 組合引用）替換成全域 [n]，並去除相鄰重複引用。"""
        def replace(m: re.Match) -> str:
            local_ids = [int(n) for n in re.findall(r"\d+", m.group(1))]
            global_ids: List[str] = []
            for local_id in local_ids:
                info = local_refs.get(local_id)
                global_ids.append(str(info["global_ref_id"]) if info else str(local_id))
            return "".join(f"[{gid}]" for gid in global_ids)

        text = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", replace, text)
        # 去除相鄰重複引用，如 [1][1] → [1]
        return re.sub(r"(\[\d+\])(?:\1)+", r"\1", text)
```

改成第 6 行的 `re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", replace, text)` 換成 `re.sub(_CITATION_PATTERN, replace, text)`，其餘不動。

- [ ] **Step 5: 改寫 `_build_citation_map`**

把第 908-960 行整段換成：

```python
    @staticmethod
    def _build_citation_map(
        section_name: str,
        section_text: str,
        local_refs: Dict[int, dict],
        global_ref_list: List[dict],
        citation_map: List[dict],
    ) -> None:
        """
        逐段解析引用標記，填入 citation_map。

        section_text 是**尚未**把本地編號轉成全域編號的原始章節文字——
        必須用本地編號直接查 local_refs，才知道這段話實際引用的是哪個 chunk
        （同一篇論文在候選池裡可能有好幾個不同的 chunk，各自對應不同的 local_id）。

        citation_map 的每一筆結構：
        {
            section        : 章節名稱
            paragraph_index: 該段在章節中的位置（0-indexed）
            text           : 段落文字（含 [n] 標記，本地編號）
            cited_ref_ids  : 該段引用的全域 ref_id 列表（去重、由小到大）
            sources        : 每個引用的詳細資訊（供前端展示）
        }
        """
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
        for para_idx, para in enumerate(paragraphs):
            local_ids_in_para: List[int] = []
            for m in _CITATION_PATTERN.finditer(para):
                local_ids_in_para.extend(int(n) for n in re.findall(r"\d+", m.group(1)))
            if not local_ids_in_para:
                continue

            # 同一篇論文（同一個 global_ref_id）被段落內多個不同 local_id 重複引用時，
            # 取文字裡先出現的那個（閱讀順序），不做進一步仲裁
            first_local_id_for_gid: Dict[int, int] = {}
            for local_id in local_ids_in_para:
                info = local_refs.get(local_id)
                if not info:
                    continue
                gid = info["global_ref_id"]
                first_local_id_for_gid.setdefault(gid, local_id)

            if not first_local_id_for_gid:
                continue

            cited_gids = sorted(first_local_id_for_gid)
            sources: List[dict] = []
            for gid in cited_gids:
                info = local_refs[first_local_id_for_gid[gid]]
                ref_meta = next((r for r in global_ref_list if r["ref_id"] == gid), {})
                sources.append({
                    "ref_id": gid,
                    "paper_id": info["chunk"].paper_id,
                    "title": ref_meta.get("title", ""),
                    "author": ref_meta.get("author", ""),
                    "year": ref_meta.get("year", ""),
                    # 提供被引用的原始 chunk 內容，方便前端顯示引用依據
                    "relevant_chunk": info["chunk"].content[:400],
                    # rerank_score 是 Task 2 才會補上的欄位，這裡先用 .get() 讀，
                    # Task 1 完成時還沒有這個 key，會自然 fall back 到 score
                    "similarity_score": round(info.get("rerank_score") or info["score"], 4),
                })

            citation_map.append({
                "section": section_name,
                "paragraph_index": para_idx,
                "text": para,
                "cited_ref_ids": cited_gids,
                "sources": sources,
            })
```

- [ ] **Step 6: 調整 `generate_paper()` 的呼叫順序**

在 `generate_paper()` 裡（第 264-271 行），把：

```python
            # 4. 本地 [n] → 全域 [n]
            section_text_global = self._localref_to_global(section_text, local_refs)
            sections_text[section_name] = section_text_global

            # 5. 建立引用地圖（逐段）
            self._build_citation_map(
                section_name, section_text_global, local_refs, global_ref_list, citation_map
            )
```

改成：

```python
            # 4. 建立引用地圖（逐段）—— 要在轉換全域編號之前做，
            # 這樣才能用本地編號精準查表，不是用全域編號反查猜測
            self._build_citation_map(
                section_name, section_text, local_refs, global_ref_list, citation_map
            )

            # 5. 本地 [n] → 全域 [n]
            section_text_global = self._localref_to_global(section_text, local_refs)
            sections_text[section_name] = section_text_global
```

（原本註解的步驟數字 4/5 對調，其餘章節內容不變）

- [ ] **Step 7: 執行測試，確認通過**

Run: `cd backend && uv run pytest tests/test_paper_rag_citation_map.py -v`
Expected: PASS（3 個測試全過）

- [ ] **Step 8: 確認沒有其他呼叫端還在用舊的參數順序假設**

Run: `cd backend && grep -rn "_build_citation_map\|_localref_to_global" services/ routes/`
Expected: 只有 `paper_rag.py` 內部這幾處呼叫，沒有其他檔案依賴這兩個 method 的內部行為

- [ ] **Step 9: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/tests/test_paper_rag_citation_map.py
git commit -m "fix: attribute citation_map chunks per-paragraph using local ref ids

_build_citation_map previously ran after local->global ref id
conversion, so it could only look up chunks by global_ref_id and
always picked the first match — meaning the same paper always showed
the same chunk regardless of which paragraph cited it. Now it parses
the pre-conversion text directly against local_refs, so each
paragraph's citation map entry reflects the chunk actually cited
there."
```

---

## Task 2：接上真正的 reranker

**Files:**
- Create: `backend/services/rag/reranker.py`
- Modify: `backend/services/rag/paper_rag.py`（`PaperRAGService.__init__`、`search()`）
- Modify: `backend/pyproject.toml`、`backend/uv.lock`（新增 `sentence-transformers` 依賴，Step 3）
- Test: `backend/tests/test_reranker.py`（新檔案）

**Interfaces:**
- Consumes: `Chunk`（`backend/services/rag/chunker.py` 既有的 dataclass，不變）
- Produces: `Reranker(model_name: str = "BAAI/bge-reranker-base")`，`.available: bool` 屬性，`.rerank(query: str, candidates: list[tuple[Chunk, float]]) -> list[tuple[Chunk, float, float]]`（回傳 `(chunk, original_score, rerank_score)`，依 `rerank_score` 降冪排序）。`PaperRAGService.search()` 簽名不變，`SearchResult.rerank_score` 現在會被真的填值。

- [ ] **Step 1: 寫失敗的測試——驗證 reranker 正確依分數排序，以及載入失敗時優雅降級**

建立 `backend/tests/test_reranker.py`：

```python
"""Reranker 的排序與降級測試。

不連網：用假的 CrossEncoder 直接注入 _model，或監補
sentence_transformers.CrossEncoder 模擬載入失敗，都不會真的下載模型。
"""

from dataclasses import dataclass

from services.rag.reranker import Reranker


@dataclass
class FakeChunk:
    paper_id: str
    content: str


class FakeCrossEncoder:
    """predict() 回傳跟輸入的候選文字長度成正比的假分數，方便斷言排序結果。"""

    def __init__(self, scores):
        self._scores = scores

    def predict(self, pairs):
        return self._scores


def make_reranker_with_fake_model(scores):
    reranker = Reranker.__new__(Reranker)
    reranker.model_name = "fake-model"
    reranker._model = FakeCrossEncoder(scores)
    return reranker


def test_rerank_sorts_candidates_by_cross_encoder_score_descending():
    candidates = [
        (FakeChunk(paper_id="a", content="不太相關的內容"), 0.5),
        (FakeChunk(paper_id="b", content="非常相關的內容"), 0.4),
        (FakeChunk(paper_id="c", content="普通相關的內容"), 0.6),
    ]
    # 刻意讓 cross-encoder 分數的排序跟原本的 embedding 分數排序不一樣，
    # 驗證真的是照 rerank_score 排，不是照原本的 score
    reranker = make_reranker_with_fake_model(scores=[0.1, 0.9, 0.3])

    result = reranker.rerank("query", candidates)

    assert [chunk.paper_id for chunk, _orig, _rerank in result] == ["b", "c", "a"]
    assert result[0] == (candidates[1][0], 0.4, 0.9)


def test_reranker_unavailable_when_model_fails_to_load(monkeypatch):
    def raise_error(*args, **kwargs):
        raise RuntimeError("model download failed")

    monkeypatch.setattr("sentence_transformers.CrossEncoder", raise_error)

    reranker = Reranker(model_name="fake-model")

    assert reranker.available is False
```

- [ ] **Step 2: 執行測試，確認失敗**

Run: `cd backend && uv run pytest tests/test_reranker.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'services.rag.reranker'`（檔案還沒建立）

- [ ] **Step 3: 把 `sentence-transformers` 加成真的依賴**

`requirements.txt` 雖然列了這個套件，但那份檔案已經跟 `pyproject.toml`/`uv.lock` 脫鉤、沒人維護，實際上這個套件從沒被裝進這個專案的環境（`Embedder` 目前在真實環境裡其實一直是跑 TF-IDF fallback）。

Run: `cd backend && uv add sentence-transformers`
Expected: 成功安裝（`torch`/`transformers`/`huggingface-hub` 這些底層套件已經因為 `mineru`/`openai-whisper` 裝過了，這裡應該只需要多裝 1 個套件、幾秒鐘完成）。`pyproject.toml` 的 `dependencies` 陣列、`uv.lock` 會被更動，這兩個檔案的變動要一起 commit。

- [ ] **Step 4: 建立 `backend/services/rag/reranker.py`**

```python
import logging
from typing import List, Tuple

from .chunker import Chunk

logger = logging.getLogger(__name__)


class Reranker:
    """
    用 CrossEncoder 對「查詢 / 候選段落」重新評分排序，取代單純的向量相似度排名。

    跟 Embedder（embedder.py）用同一個 sentence-transformers 套件（CrossEncoder）。
    模型載入失敗（下載失敗等）就優雅降級成不可用，呼叫端要自己檢查
    available 並 fall back 成不重排，不能讓整個論文生成流程掛掉。
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None
        self._try_load()

    def _try_load(self) -> None:
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            logger.info("Reranker: CrossEncoder loaded (%s)", self.model_name)
        except Exception:
            logger.warning(
                "Reranker: 載入 %s 失敗，重排功能停用，檢索結果將維持原本的相似度排序",
                self.model_name,
                exc_info=True,
            )

    @property
    def available(self) -> bool:
        return self._model is not None

    def rerank(
        self, query: str, candidates: List[Tuple[Chunk, float]]
    ) -> List[Tuple[Chunk, float, float]]:
        """
        candidates: [(chunk, original_score), ...]
        回傳依 rerank_score 由高到低排序的 [(chunk, original_score, rerank_score), ...]。
        呼叫前應該先檢查 self.available。
        """
        pairs = [(query, chunk.content) for chunk, _ in candidates]
        scores = self._model.predict(pairs)

        combined = [
            (chunk, orig_score, float(rerank_score))
            for (chunk, orig_score), rerank_score in zip(candidates, scores)
        ]
        combined.sort(key=lambda item: item[2], reverse=True)
        return combined
```

- [ ] **Step 5: 執行測試，確認通過**

Run: `cd backend && uv run pytest tests/test_reranker.py -v`
Expected: PASS（2 個測試都過）

- [ ] **Step 6: 把 `Reranker` 接進 `PaperRAGService`**

在 `backend/services/rag/paper_rag.py` 頂部的 import 區塊（第 21-24 行）加一行：

```python
from .reranker import Reranker
```

`PaperRAGService.__init__`（第 133-144 行）在 `self._embedder = Embedder(model_name=embed_model)` 之後加：

```python
        rerank_model = os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-base")
        self._reranker = Reranker(model_name=rerank_model)
```

`SearchResult` dataclass（第 92-96 行）已經有 `rerank_score: Optional[float] = None`，不用改。

`search()`（第 167-169 行）改成：

```python
    def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
        should_rerank = use_rerank and self._reranker.available
        overfetch_k = top_k * 4 if should_rerank else top_k

        raw = self._store.search(query, top_k=overfetch_k)

        if should_rerank and raw:
            reranked = self._reranker.rerank(query, raw)
            return [
                SearchResult(chunk=c, score=orig_score, rerank_score=rerank_score)
                for c, orig_score, rerank_score in reranked[:top_k]
            ]

        return [SearchResult(chunk=c, score=s) for c, s in raw[:top_k]]
```

- [ ] **Step 7: 讓 `local_refs` 帶上 `rerank_score`，Task 1 寫的 `.get("rerank_score")` 才吃得到值**

在 `generate_paper()` 建立 `local_refs` 的迴圈（第 241-256 行）：

```python
            local_refs: Dict[int, dict] = {}
            for local_id, sr in enumerate(search_results, 1):
                pid = sr.chunk.paper_id
                if pid not in global_ref_map:
                    global_ref_map[pid] = len(global_ref_map) + 1
                    global_ref_list.append({
                        "ref_id": global_ref_map[pid],
                        "paper_id": pid,
                        "title": sr.chunk.title,
                        **sr.chunk.metadata,
                    })
                local_refs[local_id] = {
                    "global_ref_id": global_ref_map[pid],
                    "chunk": sr.chunk,
                    "score": sr.score,
                }
```

最後三行的 dict 多加一個 key：

```python
                local_refs[local_id] = {
                    "global_ref_id": global_ref_map[pid],
                    "chunk": sr.chunk,
                    "score": sr.score,
                    "rerank_score": sr.rerank_score,
                }
```

- [ ] **Step 8: 執行全部後端測試，確認沒有連帶弄壞其他東西**

Run: `cd backend && uv run pytest tests/test_reranker.py tests/test_paper_rag_citation_map.py -v`
Expected: PASS（全部 5 個測試都過——`sr.rerank_score` 在 Task 1 的測試裡沒有被用到真的 `search()`，`local_refs` 是手動構造的，不受這個改動影響）

- [ ] **Step 9: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/services/rag/reranker.py backend/services/rag/paper_rag.py backend/tests/test_reranker.py
git commit -m "feat: wire up a real cross-encoder reranker for RAG search

use_rerank was accepted by search() but never read, and
SearchResult.rerank_score was always None — a documented API surface
that did nothing. requirements.txt claimed sentence-transformers was
already a dependency, but it had drifted out of sync with
pyproject.toml/uv.lock and was never actually installed — Embedder has
been silently running in TF-IDF fallback mode. Adds sentence-transformers
as a real dependency and a Reranker wrapping its CrossEncoder,
over-fetches candidates and reranks them down to top_k. citation_map's
similarity_score now prefers the rerank score when available."
```

---

## Task 3：`CitationMark` extension 新增 `relevantChunk` 屬性

**Files:**
- Modify: `frontend/src/components/paper/citationMark.ts`

**Interfaces:**
- Consumes: 無
- Produces: `CitationMark` mark 現在多接受一個 `relevantChunk: string | null` 屬性，渲染成 `data-relevant-chunk` HTML 屬性（沒有值時不渲染這個屬性，維持乾淨的 HTML）。Task 4 會在建立 mark 時傳入這個屬性；Task 5 會從渲染出來的 `data-relevant-chunk` 讀值。

- [ ] **Step 1: 修改 `citationMark.ts`**

把 `addAttributes()`（第 16-27 行）：

```ts
  addAttributes () {
    return {
      citationId: {
        default: null,
        parseHTML: element => element.getAttribute('data-citation-id'),
        renderHTML: attributes => {
          if (!attributes.citationId) return {}
          return { 'data-citation-id': attributes.citationId }
        },
      },
    }
  },
```

改成：

```ts
  addAttributes () {
    return {
      citationId: {
        default: null,
        parseHTML: element => element.getAttribute('data-citation-id'),
        renderHTML: attributes => {
          if (!attributes.citationId) return {}
          return { 'data-citation-id': attributes.citationId }
        },
      },
      // 這次引用實際依據的來源片段，跟書目資訊（標題/作者/期刊）分開存——
      // 同一篇論文在不同段落被引用時，這個值可能不一樣
      relevantChunk: {
        default: null,
        parseHTML: element => element.getAttribute('data-relevant-chunk'),
        renderHTML: attributes => {
          if (!attributes.relevantChunk) return {}
          return { 'data-relevant-chunk': attributes.relevantChunk }
        },
      },
    }
  },
```

其餘（`parseHTML`、`renderHTML` 的 mark-level 那個 function）不用改——`mergeAttributes(HTMLAttributes, {...})` 已經會自動把每個屬性各自 `renderHTML` 出來的結果併進去。

- [ ] **Step 2: 型別檢查跟 lint**

Run: `cd frontend && npx eslint src/components/paper/citationMark.ts && npx vue-tsc --build --force`
Expected: 都乾淨過關，沒有錯誤

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/citationMark.ts
git commit -m "feat: add relevantChunk attribute to CitationMark

Carries the specific source snippet a citation occurrence was actually
grounded on, separately from the shared bibliographic info (title/
author/journal) used for the reference list."
```

---

## Task 4：`paperTransform.ts` 依段落對照 `citation_map`，把對應的 chunk 內容寫進引用標記

**Files:**
- Modify: `frontend/src/utils/paperTransform.ts`

**Interfaces:**
- Consumes: `CitationMark` 的 `relevantChunk` 屬性（Task 3）；`ArxivCitationSource`/`ArxivCitationMapEntry`（`frontend/src/api/arxiv.ts` 既有型別，不變）
- Produces: `transformArxivResultToPaperReport()` 的對外行為不變（回傳的 `PaperReport` 形狀一樣），但產生的 Tiptap content 裡，每個引用標記現在帶有正確的 `relevantChunk`。Task 5 會用到這個屬性。

- [ ] **Step 1: 修改 `parseParagraphToContent`，多接受一個 `sources` 參數**

把第 5-32 行：

```ts
function parseParagraphToContent (paragraphText: string): JSONContent[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const nodes: JSONContent[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const firstDigits = token.match(/\d+/)?.[0]
      if (!firstDigits) {
        continue
      }
      const citationId = `cite-${firstDigits}`
      const prev = nodes.at(-1)

      if (prev && prev.type === 'text' && !prev.marks) {
        // 引用標記依附在「前一句」文字上,不寫進文字內容本身
        prev.marks = [{ type: 'citation', attrs: { citationId } }]
      } else {
        // 沒有前一句可依附(例如段落一開頭就是引用標記):用零寬空白當文字節點,
        // 只是為了承載 citation mark,避免 ProseMirror 不允許空文字節點
        nodes.push({ type: 'text', text: '​', marks: [{ type: 'citation', attrs: { citationId } }] })
      }
    } else {
      nodes.push({ type: 'text', text: token })
    }
  }

  return nodes
}
```

改成：

```ts
function parseParagraphToContent (
  paragraphText: string,
  sources: ArxivCitationSource[] | undefined,
): JSONContent[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const nodes: JSONContent[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const firstDigits = token.match(/\d+/)?.[0]
      if (!firstDigits) {
        continue
      }
      const citationId = `cite-${firstDigits}`
      // 這段話實際引用到的 chunk，跟 citations 陣列裡「這篇論文預設摘錄」分開存，
      // 找不到（例如非 arXiv 生成的內容）就是 null，彈窗會 fall back 用預設摘錄
      const relevantChunk = sources?.find(s => s.ref_id === Number(firstDigits))?.relevant_chunk ?? null
      const attrs = { citationId, relevantChunk }
      const prev = nodes.at(-1)

      if (prev && prev.type === 'text' && !prev.marks) {
        // 引用標記依附在「前一句」文字上,不寫進文字內容本身
        prev.marks = [{ type: 'citation', attrs }]
      } else {
        // 沒有前一句可依附(例如段落一開頭就是引用標記):用零寬空白當文字節點,
        // 只是為了承載 citation mark,避免 ProseMirror 不允許空文字節點
        nodes.push({ type: 'text', text: '​', marks: [{ type: 'citation', attrs }] })
      }
    } else {
      nodes.push({ type: 'text', text: token })
    }
  }

  return nodes
}
```

- [ ] **Step 2: 修改 import，加上 `ArxivCitationSource` 型別**

把第 2 行：

```ts
import type { ArxivGenerateResult } from '@/api/arxiv'
```

改成：

```ts
import type { ArxivCitationSource, ArxivGenerateResult } from '@/api/arxiv'
```

- [ ] **Step 3: 修改 `transformArxivResultToPaperReport`，依段落對照 `citation_map`**

把第 74-81 行：

```ts
    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const paragraph of paragraphs) {
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph) })
    }
```

改成：

```ts
    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const [index, paragraph] of paragraphs.entries()) {
      // 前端這裡切段落的規則（\n\n---\n\n 分章節、\n\n 分段落）跟後端組
      // paper_markdown、_build_citation_map 切 paragraph_index 用的是同一份文字、
      // 同一套規則，兩邊算出來的段落序號天生對得上，不需要後端多傳任何資料
      const sources = result.citation_map.find(
        entry => entry.section === heading && entry.paragraph_index === index,
      )?.sources
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph, sources) })
    }
```

- [ ] **Step 4: 型別檢查跟 lint**

Run: `cd frontend && npx eslint src/utils/paperTransform.ts && npx vue-tsc --build --force`
Expected: 都乾淨過關

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/paperTransform.ts
git commit -m "fix: attach per-paragraph relevant chunk to citation marks

transformArxivResultToPaperReport now looks up each paragraph's
matching citation_map entry (paragraph splitting uses the exact same
rule as the backend, so indices line up without any new data from the
server) and passes its sources down so each citation mark carries the
chunk actually cited in that specific paragraph."
```

---

## Task 5：`PaperPage.vue` 彈窗優先顯示被點擊那個引用實例的內容

**Files:**
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes: `CitationMark` 渲染出的 `data-relevant-chunk`（Task 3+4）
- Produces: `popoverCitation` 對外行為：沒有 `relevantChunk` 資料時（mock 資料、舊格式內容）跟現在完全一樣；有的話 `snippet` 欄位改用該次引用實際對應的內容

- [ ] **Step 1: 修改 `popoverCitation` computed**

把第 132-134 行：

```ts
  const popoverCitation = computed(() =>
    report.value.citations.find(c => c.id === activeCitationId.value) ?? null,
  )
```

改成：

```ts
  const popoverCitation = computed(() => {
    const base = report.value.citations.find(c => c.id === activeCitationId.value) ?? null
    if (!base) return null
    // 同一篇論文在不同段落被引用時，優先顯示「被點擊的那一次引用」實際依據的片段，
    // 找不到（mock 資料、非 arXiv 生成的內容）才退回這篇論文的預設摘錄
    const relevantChunk = popoverTarget.value?.dataset.relevantChunk
    return relevantChunk ? { ...base, snippet: relevantChunk } : base
  })
```

- [ ] **Step 2: 型別檢查跟 lint**

Run: `cd frontend && npx eslint src/views/PaperPage.vue && npx vue-tsc --build --force`
Expected: 都乾淨過關

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "fix: show the clicked citation occurrence's own snippet in the popover

popoverCitation now prefers the relevantChunk carried by the specific
mark that was clicked (via its data-relevant-chunk attribute) over the
citation's shared default snippet, so the popover content reflects
which paragraph the reader is actually looking at."
```

---

## Task 6：瀏覽器手動驗證前端整條鏈路

**Files:**
- Create（暫時，驗證完刪除）：`frontend/src/views/__DevCitationRelevanceTest.vue`
- Modify（暫時加一條路由，驗證完還原）：`frontend/src/router/index.ts`

**Interfaces:**
- Consumes: Task 3、4、5 完成後的完整前端鏈路
- Produces: 無程式碼產出——這是驗證任務，確認 Task 3-5 三個改動組合起來真的解決了使用者回報的症狀（同一篇論文在不同段落顯示不同摘錄），而且沒有弄壞參考文獻列表

**背景**：真正觸發 `generate_paper()` 需要 `GEMINI_API_KEY`、已索引的來源論文、還要花錢呼叫 Gemini，不適合當作驗證步驟。改用手造一份 `ArxivGenerateResult` 形狀的假資料，跑過 `transformArxivResultToPaperReport()`，直接驗證這條轉換鏈路——這就是 Task 3-5 唯一會影響到的路徑。

- [ ] **Step 1: 建立暫時的驗證頁面**

建立 `frontend/src/views/__DevCitationRelevanceTest.vue`：

```vue
<template>
  <div style="padding: 40px; max-width: 800px;">
    <PaperEditor
      v-model="report.content"
      :citations="report.citations"
      :editable="false"
      @citation-click="onCitationClick"
    />
    <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" />
    <CitationPopover
      :citation="popoverCitation"
      :index="1"
      :target="popoverTarget"
      @close="activeCitationId = null"
    />
  </div>
</template>

<script setup lang="ts">
  import type { ArxivGenerateResult } from '@/api/arxiv'
  import { computed, ref } from 'vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import ReferencesSection from '@/components/paper/ReferencesSection.vue'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'

  // 同一篇論文（ref_id 1）在兩個不同段落被引用，relevant_chunk 刻意不同——
  // 這就是這次要修的 bug 場景
  const fakeResult: ArxivGenerateResult = {
    paper_markdown: [
      '# 測試論文',
      '## 前言\n\n第一段引用空氣品質研究[1]。\n\n第二段引用同一篇論文但不同重點[1]。',
      '## 參考文獻\n\n[1] Wang (2024). Paper A.',
    ].join('\n\n---\n\n'),
    citation_map: [
      {
        section: '前言',
        paragraph_index: 0,
        text: '第一段引用空氣品質研究[1]。',
        cited_ref_ids: [1],
        sources: [{
          ref_id: 1,
          paper_id: 'paper-a',
          title: 'Paper A',
          author: 'Wang',
          year: '2024',
          relevant_chunk: '空氣品質與心血管疾病的關聯研究（第一段的版本）',
          similarity_score: 0.9,
        }],
      },
      {
        section: '前言',
        paragraph_index: 1,
        text: '第二段引用同一篇論文但不同重點[1]。',
        cited_ref_ids: [1],
        sources: [{
          ref_id: 1,
          paper_id: 'paper-a',
          title: 'Paper A',
          author: 'Wang',
          year: '2024',
          relevant_chunk: 'PM2.5 濃度與呼吸道發炎反應（第二段的版本）',
          similarity_score: 0.85,
        }],
      },
    ],
    references: [{ ref_id: 1, paper_id: 'paper-a', title: 'Paper A', author: 'Wang', year: '2024' }],
    citation_report: '',
    sections_generated: ['前言'],
    usage: {},
  }

  const report = ref(transformArxivResultToPaperReport(fakeResult, '測試論文'))

  const activeCitationId = ref<string | null>(null)
  const popoverTarget = ref<HTMLElement | null>(null)

  const popoverCitation = computed(() => {
    const base = report.value.citations.find(c => c.id === activeCitationId.value) ?? null
    if (!base) return null
    const relevantChunk = popoverTarget.value?.dataset.relevantChunk
    return relevantChunk ? { ...base, snippet: relevantChunk } : base
  })

  function onCitationClick ({ citationId, target }: { citationId: string, target: HTMLElement }) {
    activeCitationId.value = citationId
    popoverTarget.value = target
  }
</script>
```

- [ ] **Step 2: 暫時掛一條 dev-only 路由**

在 `frontend/src/router/index.ts` 的 `devOnlyRoutes` 陣列（比照既有的 `/style-guide` 那筆）加：

```ts
      {
        path: "/__dev-citation-relevance-test",
        name: "__dev-citation-relevance-test",
        component: () => import("@/views/__DevCitationRelevanceTest.vue"),
      },
```

- [ ] **Step 3: 用瀏覽器打開驗證**

開發伺服器跑在 `http://localhost:3000`（這個 session 稍早已確認）。導到 `http://localhost:3000/__dev-citation-relevance-test`，點文中第一個 `[1]`，記下彈窗顯示的內容；關掉，點第二個 `[1]`，確認彈窗顯示的是「PM2.5 濃度與呼吸道發炎反應（第二段的版本）」——**必須跟第一次點的內容不一樣**，這就是這次修復的核心驗證點。另外確認參考文獻列表只列出一筆「Paper A」（不會因為被引用兩次就重複列出）。

- [ ] **Step 4: 清掉暫時的驗證頁面跟路由**

```bash
rm frontend/src/views/__DevCitationRelevanceTest.vue
```

把 Step 2 加進 `router/index.ts` 的那幾行移除，還原成加之前的樣子。

Run: `cd frontend && git diff --stat src/router/index.ts`
Expected: 沒有輸出（完全還原，沒有殘留 diff）

- [ ] **Step 5: 最後跑一次全專案 lint 跟 type-check，確認 Task 1-5 的所有改動都乾淨**

Run: `cd frontend && npx eslint src/components/paper/citationMark.ts src/utils/paperTransform.ts src/views/PaperPage.vue && npx vue-tsc --build --force`

Run: `cd backend && uv run pytest tests/test_paper_rag_citation_map.py tests/test_reranker.py -v`

Expected: 全部乾淨過關
