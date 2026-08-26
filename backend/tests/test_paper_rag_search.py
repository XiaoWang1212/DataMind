"""PaperRAGService.search() 的 overfetch → rerank → truncate 整合測試。

不連網：繞過 __init__（不需要 GEMINI_API_KEY），直接注入假的 _store / _reranker。
"""

from dataclasses import dataclass

from services.rag.paper_rag import PaperRAGService


@dataclass
class FakeChunk:
    paper_id: str
    content: str


class FakeStore:
    def __init__(self, chunks_with_scores):
        self._chunks_with_scores = chunks_with_scores
        self.last_top_k = None
        self.last_project_id = None

    def search(self, project_id, query, top_k=5):
        self.last_project_id = project_id
        self.last_top_k = top_k
        return self._chunks_with_scores[:top_k]


class FakeRerankerAvailable:
    available = True

    def rerank(self, query, candidates):
        # 刻意反轉順序並給遞增分數，證明真的是靠 rerank_score 排序、不是原本的 score
        reversed_candidates = list(reversed(candidates))
        return [
            (chunk, orig_score, float(i))
            for i, (chunk, orig_score) in enumerate(reversed_candidates)
        ]


class FakeRerankerUnavailable:
    available = False


def make_chunks(n):
    return [(FakeChunk(paper_id=f"p{i}", content=f"content {i}"), 1.0 - i * 0.1) for i in range(n)]


def test_search_overfetches_reranks_and_truncates_when_available():
    service = PaperRAGService.__new__(PaperRAGService)
    store = FakeStore(make_chunks(10))
    service._store = store
    service._reranker = FakeRerankerAvailable()

    results = service.search(1, "query", top_k=3, use_rerank=True)

    assert store.last_top_k == 12  # top_k * 4
    assert len(results) == 3
    assert all(r.rerank_score is not None for r in results)


def test_search_skips_rerank_when_reranker_unavailable():
    service = PaperRAGService.__new__(PaperRAGService)
    store = FakeStore(make_chunks(10))
    service._store = store
    service._reranker = FakeRerankerUnavailable()

    results = service.search(1, "query", top_k=3, use_rerank=True)

    assert store.last_top_k == 3  # no overfetch when not reranking
    assert len(results) == 3
    assert all(r.rerank_score is None for r in results)
    assert [round(r.score, 4) for r in results] == [1.0, 0.9, 0.8]


def test_search_skips_rerank_when_use_rerank_false():
    service = PaperRAGService.__new__(PaperRAGService)
    store = FakeStore(make_chunks(10))
    service._store = store
    service._reranker = FakeRerankerAvailable()

    results = service.search(1, "query", top_k=3, use_rerank=False)

    assert store.last_top_k == 3
    assert all(r.rerank_score is None for r in results)


class TestIngestArxivSelectionDedup:
    def test_skips_candidate_already_in_project(self, monkeypatch):
        """同一個 project 裡，arxiv_id 已經存在就不該再呼叫 add_paper。"""
        service = PaperRAGService.__new__(PaperRAGService)
        service._store = FakeStore([])
        service._store.find_by_arxiv_id = lambda project_id, arxiv_id: (
            object() if arxiv_id == "1111.1111" else None
        )
        add_paper_calls = []
        service.add_paper = lambda project_id, title, content, metadata=None: (
            add_paper_calls.append(title) or {"success": True}
        )
        monkeypatch.setattr(
            "services.rag.paper_rag.arxiv_source.fetch_pdf_text",
            lambda pdf_url: "some fetched text",
        )

        result = service.ingest_arxiv_selection(
            project_id=1,
            candidates=[
                {"title": "Already ingested", "pdf_url": "http://x/1", "arxiv_id": "1111.1111"},
                {"title": "New paper", "pdf_url": "http://x/2", "arxiv_id": "2222.2222"},
            ],
        )

        # 去重複的那篇不會呼叫 add_paper（沒有真的重複寫入），但仍然算「已在索引裡」，
        # 所以 result["ingested"] 兩篇都要有——這是給呼叫端看的「這個 project 現在有沒有
        # 這篇論文」，不是「這次呼叫有沒有真的寫入新資料」。
        assert add_paper_calls == ["New paper"]
        assert result["ingested"] == ["Already ingested", "New paper"]
