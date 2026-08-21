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
        呼叫前應該先檢查 self.available。呼叫期間失敗（OOM、tokenizer 錯誤等）
        會優雅降級，回傳未重排的原始順序，不讓論文生成流程因為這一步掛掉。
        """
        pairs = [(query, chunk.content) for chunk, _ in candidates]
        try:
            scores = self._model.predict(pairs)
        except Exception:
            logger.warning("Reranker: rerank() 呼叫失敗，退回原始相似度排序", exc_info=True)
            return [(chunk, orig_score, orig_score) for chunk, orig_score in candidates]

        combined = [
            (chunk, orig_score, float(rerank_score))
            for (chunk, orig_score), rerank_score in zip(candidates, scores)
        ]
        combined.sort(key=lambda item: item[2], reverse=True)
        return combined
