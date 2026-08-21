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
