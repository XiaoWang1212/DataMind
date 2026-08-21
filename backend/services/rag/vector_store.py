import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .chunker import Chunk
from .embedder import Embedder

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Persists chunks and (optionally) dense embeddings to disk.

    - transformers mode: stores .npy embeddings; search via dot product.
    - tfidf mode: stores raw text only; search re-fits TF-IDF at query time
      (correct but slower; fine for dozens of papers).
    """

    def __init__(self, index_dir: str | Path, embedder: Embedder):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder

        self._chunks: List[Chunk] = []
        self._embeddings: Optional[np.ndarray] = None  # (N, dim) or None
        self._papers: Dict[str, dict] = {}  # paper_id → metadata

        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        chunks_data = [
            {
                "chunk_id": c.chunk_id,
                "paper_id": c.paper_id,
                "title": c.title,
                "content": c.content,
                "chunk_index": c.chunk_index,
                "metadata": c.metadata,
            }
            for c in self._chunks
        ]
        (self.index_dir / "chunks.json").write_text(
            json.dumps(chunks_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.index_dir / "papers.json").write_text(
            json.dumps(self._papers, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self._embeddings is not None:
            np.save(str(self.index_dir / "embeddings.npy"), self._embeddings)

    def _load(self) -> None:
        chunks_file = self.index_dir / "chunks.json"
        papers_file = self.index_dir / "papers.json"
        emb_file = self.index_dir / "embeddings.npy"

        if chunks_file.exists():
            raw = json.loads(chunks_file.read_text(encoding="utf-8"))
            self._chunks = [
                Chunk(
                    chunk_id=d["chunk_id"],
                    paper_id=d["paper_id"],
                    title=d["title"],
                    content=d["content"],
                    chunk_index=d["chunk_index"],
                    metadata=d.get("metadata", {}),
                )
                for d in raw
            ]
            logger.info("VectorStore: loaded %d chunks from disk", len(self._chunks))

        if papers_file.exists():
            self._papers = json.loads(papers_file.read_text(encoding="utf-8"))

        if emb_file.exists() and self.embedder.backend == "transformers":
            self._embeddings = np.load(str(emb_file))
            logger.info("VectorStore: loaded embeddings %s", self._embeddings.shape)

        # 索引可能是在 embedding backend 還是 tfidf fallback 時建的（沒有 embeddings.npy），
        # 或者 add() 曾經在筆數不一致的狀態下被呼叫過。backend 變成 transformers 後
        # 兩者都要重新編碼，不然 search() 會直接因為 None 炸掉，或用對不上的索引
        # 悄悄配到錯的 chunk。
        if self.embedder.backend == "transformers" and self._chunks and (
            self._embeddings is None or len(self._embeddings) != len(self._chunks)
        ):
            logger.warning(
                "VectorStore: 索引缺少或落後於 embeddings（chunks=%d, embeddings=%s），重新編碼全部 chunk",
                len(self._chunks),
                0 if self._embeddings is None else len(self._embeddings),
            )
            self._embeddings = self.embedder.encode([c.content for c in self._chunks])
            self._save()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, chunks: List[Chunk]) -> None:
        if not chunks:
            return

        if self.embedder.backend == "transformers":
            texts = [c.content for c in chunks]
            new_embs = self.embedder.encode(texts)
            self._embeddings = (
                new_embs
                if self._embeddings is None
                else np.vstack([self._embeddings, new_embs])
            )

        self._chunks.extend(chunks)
        self._save()

    def register_paper(self, paper_id: str, metadata: dict) -> None:
        self._papers[paper_id] = metadata
        self._save()

    def delete_paper(self, paper_id: str) -> bool:
        if paper_id not in self._papers:
            return False

        keep = [c.paper_id != paper_id for c in self._chunks]
        self._chunks = [c for c, k in zip(self._chunks, keep) if k]

        if self._embeddings is not None:
            mask = np.array(keep)
            self._embeddings = self._embeddings[mask] if mask.any() else None

        del self._papers[paper_id]
        self._save()
        return True

    def clear(self) -> None:
        self._chunks = []
        self._embeddings = None
        self._papers = {}
        for fname in ["chunks.json", "papers.json", "embeddings.npy"]:
            p = self.index_dir / fname
            if p.exists():
                p.unlink()

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        if not self._chunks:
            return []

        top_k = min(top_k, len(self._chunks))
        scores = (
            self._transformer_scores(query)
            if self.embedder.backend == "transformers"
            else self._tfidf_scores(query)
        )

        # Partial sort: get top_k indices in descending score order
        idx = np.argpartition(scores, -top_k)[-top_k:]
        idx = idx[np.argsort(scores[idx])[::-1]]
        return [(self._chunks[i], float(scores[i])) for i in idx]

    def _transformer_scores(self, query: str) -> np.ndarray:
        q = self.embedder.encode_query(query)
        return self._embeddings @ q  # cosine similarity (both L2-normalised)

    def _tfidf_scores(self, query: str) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [c.content for c in self._chunks]
        vec = TfidfVectorizer(max_features=8000, analyzer="char_wb", ngram_range=(2, 4))
        corpus_mat = vec.fit_transform(corpus)
        query_vec = vec.transform([query])
        return cosine_similarity(query_vec, corpus_mat).flatten()

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "total_papers": len(self._papers),
            "total_chunks": len(self._chunks),
            "embedding_backend": self.embedder.backend,
            "embedding_model": self.embedder.model_name,
            "papers": list(self._papers.values()),
        }
