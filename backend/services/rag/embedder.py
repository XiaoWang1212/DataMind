import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class Embedder:
    """
    Wraps sentence-transformers for dense retrieval.
    Falls back to TF-IDF (via sklearn, already in requirements) if
    sentence-transformers is not installed.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self.model_name = model_name
        self._model = None
        self.backend = "tfidf"
        self._try_load_transformers()

    def _try_load_transformers(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self.backend = "transformers"
            logger.info("Embedder: sentence-transformers loaded (%s)", self.model_name)
        except ImportError:
            logger.warning(
                "sentence-transformers not installed — using TF-IDF fallback. "
                "For better retrieval quality: pip install sentence-transformers"
            )

    def encode(self, texts: List[str]) -> np.ndarray:
        """Encode a list of texts → (N, dim) float32 array. Transformers mode only."""
        if self.backend != "transformers":
            raise RuntimeError(
                "Embedder.encode() requires sentence-transformers. "
                "Install it or use VectorStore (which handles TF-IDF internally)."
            )
        vecs = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return np.array(vecs, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        return self.encode([query])[0]
