"""取代 services/rag/vector_store.py 的資料庫版本，依 project_id 隔離。"""

import logging

from extensions import db
from models.rag_paper import RagChunk, RagPaper
from services.rag.chunker import Chunk
from services.rag.embedder import Embedder

logger = logging.getLogger(__name__)


class DbVectorStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder  # 共用單例，注入進來，不自己持有

    # ── 論文/段落寫入 ──────────────────────────────────────────────────────

    def create_paper(self, project_id: int, title: str, metadata: dict) -> str:
        paper = RagPaper(
            project_id=project_id,
            title=self._sanitize_text(title),
            author=self._sanitize_text(metadata.get("author")) or None,
            year=self._parse_year(metadata.get("year")),
            arxiv_id=metadata.get("arxiv_id") or None,
        )
        db.session.add(paper)
        db.session.commit()
        return str(paper.id)

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        if self.embedder.backend == "transformers":
            vectors = self.embedder.encode([c.content for c in chunks])
        else:
            vectors = [None] * len(chunks)
        for chunk, vector in zip(chunks, vectors):
            db.session.add(RagChunk(
                paper_id=int(chunk.paper_id),
                content=self._sanitize_text(chunk.content),
                embedding=vector,
                chunk_index=chunk.chunk_index,
            ))
        db.session.commit()

    # ── 查詢 ──────────────────────────────────────────────────────────────

    def search(self, project_id: int, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if self.embedder.backend == "transformers":
            return self._transformer_search(project_id, query, top_k)
        return self._tfidf_search(project_id, query, top_k)

    def _transformer_search(self, project_id: int, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        query_vec = self.embedder.encode_query(query)
        distance_expr = RagChunk.embedding.cosine_distance(query_vec)
        rows = (
            db.session.query(RagChunk, RagPaper, distance_expr.label("distance"))
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id, RagChunk.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(top_k)
            .all()
        )

        missing_count = (
            db.session.query(RagChunk)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id, RagChunk.embedding.is_(None))
            .count()
        )
        if missing_count:
            logger.warning(
                "search: %d chunk(s) in project %s have no embedding and were excluded from transformer search",
                missing_count, project_id,
            )

        return [
            (self._row_to_chunk(chunk, paper), 1.0 - float(distance))
            for chunk, paper, distance in rows
        ]

    def _tfidf_search(self, project_id: int, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        rows = (
            db.session.query(RagChunk, RagPaper)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id)
            .all()
        )
        if not rows:
            return []

        corpus = [chunk.content for chunk, _ in rows]
        vec = TfidfVectorizer(max_features=8000, analyzer="char_wb", ngram_range=(2, 4))
        corpus_mat = vec.fit_transform(corpus)
        query_vec = vec.transform([query])
        scores = cosine_similarity(query_vec, corpus_mat).flatten()

        ranked = sorted(zip(rows, scores), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self._row_to_chunk(chunk, paper), float(score)) for (chunk, paper), score in ranked]

    def find_by_arxiv_id(self, project_id: int, arxiv_id: str) -> RagPaper | None:
        if not arxiv_id:
            return None
        return RagPaper.query.filter_by(project_id=project_id, arxiv_id=arxiv_id).first()

    def get_status(self, project_id: int) -> dict:
        papers = RagPaper.query.filter_by(project_id=project_id).all()
        total_chunks = (
            db.session.query(RagChunk)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id)
            .count()
        )
        chunks_missing_embedding = (
            db.session.query(RagChunk)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id, RagChunk.embedding.is_(None))
            .count()
        )
        return {
            "total_papers": len(papers),
            "total_chunks": total_chunks,
            "chunks_missing_embedding": chunks_missing_embedding,
            "embedding_backend": self.embedder.backend,
            "embedding_model": self.embedder.model_name,
            "papers": [
                {
                    "paper_id": str(p.id),
                    "title": p.title,
                    "author": p.author,
                    "year": p.year,
                    "arxiv_id": p.arxiv_id,
                }
                for p in papers
            ],
        }

    # ── 刪除 ──────────────────────────────────────────────────────────────

    def delete_paper(self, project_id: int, paper_id: str) -> bool:
        try:
            pid = int(paper_id)
        except (TypeError, ValueError):
            return False

        paper = RagPaper.query.filter_by(id=pid, project_id=project_id).first()
        if paper is None:
            return False
        db.session.delete(paper)  # ON DELETE CASCADE 會連帶刪除 RagChunk
        db.session.commit()
        return True

    def clear(self, project_id: int) -> None:
        RagPaper.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        db.session.commit()

    # ── 內部工具 ──────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_text(value: str | None) -> str | None:
        """PDF/arXiv 抽字有時會殘留 NUL byte（\x00），Postgres 的 text 欄位不接受，
        插入時整批 insertmany 會因為一筆髒資料而全部失敗，這裡直接濾掉。"""
        if value is None:
            return None
        return value.replace("\x00", "")

    @staticmethod
    def _parse_year(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _row_to_chunk(chunk_row, paper_row) -> Chunk:
        metadata = {}
        if paper_row.author:
            metadata["author"] = paper_row.author
        if paper_row.year:
            metadata["year"] = paper_row.year
        if paper_row.arxiv_id:
            metadata["arxiv_id"] = paper_row.arxiv_id
            metadata["journal"] = f"arXiv:{paper_row.arxiv_id}"
        return Chunk(
            chunk_id=str(chunk_row.id),
            paper_id=str(chunk_row.paper_id),
            title=paper_row.title,
            content=chunk_row.content,
            chunk_index=chunk_row.chunk_index,
            metadata=metadata,
        )
