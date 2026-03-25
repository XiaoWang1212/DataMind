"""Paper RAG Service - 論文引用生成服務

使用 BGE-M3 embedding 和 BGE-reranker 進行論文檢索
支援上傳論文、語意搜尋、生成引用
"""

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PaperChunk:
    """論文片段"""

    chunk_id: str
    paper_id: str
    title: str
    content: str
    chunk_index: int
    embedding: Optional[np.ndarray] = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """搜尋結果"""

    chunk: PaperChunk
    score: float
    rerank_score: Optional[float] = None


class PaperRAGService:
    """論文 RAG 服務

    使用現有的 embedding_model 和 rerank_model
    """

    def __init__(
        self,
        embedding_model_name: str = "BAAI/bge-m3",
        rerank_model_name: str = "BAAI/bge-reranker-base",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
    ):
        self.embedding_model_name = embedding_model_name
        self.rerank_model_name = rerank_model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 延遲載入模型
        self._embedding_model = None
        self._rerank_model = None

        # 儲存論文 chunks (簡易記憶體存儲)
        self.chunks: dict[str, PaperChunk] = {}
        self.papers: dict[str, dict] = {}

    @property
    def embedding_model(self):
        """延遲載入 embedding 模型"""
        if self._embedding_model is None:
            from services.rag.llm.embedding_model import DefaultEmbedding

            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._embedding_model = DefaultEmbedding(
                key=None, model_name=self.embedding_model_name
            )
        return self._embedding_model

    @property
    def rerank_model(self):
        """延遲載入 rerank 模型"""
        if self._rerank_model is None:
            from services.rag.llm.rerank_model import DefaultRerank

            logger.info(f"Loading rerank model: {self.rerank_model_name}")
            self._rerank_model = DefaultRerank(
                key=None, model_name=self.rerank_model_name
            )
        return self._rerank_model

    def _generate_id(self, content: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _chunk_text(self, text: str) -> list[str]:
        """將文本切割成 chunks

        使用句子邊界進行切割，避免截斷句子
        """
        # 按句子切割
        sentences = re.split(r"(?<=[。！？.!?])\s*", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length <= self.chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))

                # 保留重疊部分
                overlap_chars = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_chars + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_chars += len(s)
                    else:
                        break

                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [text]

    def add_paper(
        self,
        title: str,
        content: str,
        paper_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """添加論文到索引

        Args:
            title: 論文標題
            content: 論文內容
            paper_id: 論文 ID (可選，自動生成)
            metadata: 額外的 metadata

        Returns:
            論文資訊
        """
        if paper_id is None:
            paper_id = self._generate_id(f"{title}{content[:100]}")

        # 切割文本
        text_chunks = self._chunk_text(content)
        logger.info(f"Paper '{title}' split into {len(text_chunks)} chunks")

        # 批次計算 embeddings
        embeddings, token_count = self.embedding_model.encode(text_chunks)
        logger.info(f"Computed embeddings, token count: {token_count}")

        # 創建 PaperChunk 對象
        chunk_ids = []
        for i, (text, embedding) in enumerate(zip(text_chunks, embeddings)):
            chunk_id = f"{paper_id}_chunk_{i}"
            chunk = PaperChunk(
                chunk_id=chunk_id,
                paper_id=paper_id,
                title=title,
                content=text,
                chunk_index=i,
                embedding=embedding,
                metadata=metadata or {},
            )
            self.chunks[chunk_id] = chunk
            chunk_ids.append(chunk_id)

        # 儲存論文資訊
        self.papers[paper_id] = {
            "paper_id": paper_id,
            "title": title,
            "chunk_count": len(text_chunks),
            "chunk_ids": chunk_ids,
            "metadata": metadata or {},
        }

        return self.papers[paper_id]

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_rerank: bool = True,
        rerank_top_k: Optional[int] = None,
    ) -> list[SearchResult]:
        """搜尋相關論文片段

        Args:
            query: 搜尋查詢
            top_k: 返回結果數量
            use_rerank: 是否使用 reranker
            rerank_top_k: rerank 前先取的數量

        Returns:
            搜尋結果列表
        """
        if not self.chunks:
            return []

        # 計算 query embedding
        query_embedding, _ = self.embedding_model.encode_queries(query)

        # 計算相似度
        results = []
        for chunk_id, chunk in self.chunks.items():
            if chunk.embedding is not None:
                # cosine similarity
                similarity = np.dot(query_embedding, chunk.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk.embedding)
                )
                results.append(SearchResult(chunk=chunk, score=float(similarity)))

        # 排序
        results.sort(key=lambda x: x.score, reverse=True)

        # Rerank
        if use_rerank and results:
            rerank_count = rerank_top_k or min(len(results), top_k * 3)
            candidates = results[:rerank_count]

            texts = [r.chunk.content for r in candidates]
            rerank_scores, _ = self.rerank_model.similarity(query, texts)

            for i, result in enumerate(candidates):
                result.rerank_score = float(rerank_scores[i])

            # 重新排序
            candidates.sort(key=lambda x: x.rerank_score or 0, reverse=True)
            results = candidates

        return results[:top_k]

    def generate_citation(
        self,
        query: str,
        top_k: int = 3,
        citation_style: str = "apa",
    ) -> dict:
        """生成論文引用

        Args:
            query: 搜尋查詢
            top_k: 引用的論文數量
            citation_style: 引用格式 (apa, mla, chicago)

        Returns:
            引用結果，包含相關段落和引用格式
        """
        results = self.search(query, top_k=top_k, use_rerank=True)

        if not results:
            return {
                "query": query,
                "citations": [],
                "context": "",
                "message": "No relevant papers found",
            }

        # 整理引用
        citations = []
        context_parts = []

        for i, result in enumerate(results):
            chunk = result.chunk
            paper = self.papers.get(chunk.paper_id, {})

            citation = {
                "index": i + 1,
                "title": chunk.title,
                "paper_id": chunk.paper_id,
                "content": chunk.content,
                "score": result.rerank_score or result.score,
                "metadata": chunk.metadata,
            }

            # 格式化引用
            if citation_style == "apa":
                citation["formatted"] = self._format_apa(chunk, paper)
            elif citation_style == "mla":
                citation["formatted"] = self._format_mla(chunk, paper)
            else:
                citation["formatted"] = self._format_chicago(chunk, paper)

            citations.append(citation)
            context_parts.append(f"[{i + 1}] {chunk.content}")

        return {
            "query": query,
            "citations": citations,
            "context": "\n\n".join(context_parts),
            "citation_style": citation_style,
        }

    def _format_apa(self, chunk: PaperChunk, paper: dict) -> str:
        """APA 格式引用"""
        author = chunk.metadata.get("author", "Unknown Author")
        year = chunk.metadata.get("year", "n.d.")
        return f"{author} ({year}). {chunk.title}."

    def _format_mla(self, chunk: PaperChunk, paper: dict) -> str:
        """MLA 格式引用"""
        author = chunk.metadata.get("author", "Unknown Author")
        year = chunk.metadata.get("year", "n.d.")
        return f'{author}. "{chunk.title}." {year}.'

    def _format_chicago(self, chunk: PaperChunk, paper: dict) -> str:
        """Chicago 格式引用"""
        author = chunk.metadata.get("author", "Unknown Author")
        year = chunk.metadata.get("year", "n.d.")
        return f'{author}. "{chunk.title}," {year}.'

    def get_status(self) -> dict:
        """獲取服務狀態"""
        return {
            "paper_count": len(self.papers),
            "chunk_count": len(self.chunks),
            "embedding_model": self.embedding_model_name,
            "rerank_model": self.rerank_model_name,
            "papers": list(self.papers.values()),
        }

    def clear(self) -> dict:
        """清空所有索引"""
        paper_count = len(self.papers)
        chunk_count = len(self.chunks)
        self.papers.clear()
        self.chunks.clear()
        return {
            "cleared_papers": paper_count,
            "cleared_chunks": chunk_count,
        }

    def delete_paper(self, paper_id: str) -> dict:
        """刪除指定論文"""
        if paper_id not in self.papers:
            return {"success": False, "message": f"Paper {paper_id} not found"}

        paper = self.papers.pop(paper_id)
        deleted_chunks = 0

        for chunk_id in paper.get("chunk_ids", []):
            if chunk_id in self.chunks:
                del self.chunks[chunk_id]
                deleted_chunks += 1

        return {
            "success": True,
            "paper_id": paper_id,
            "deleted_chunks": deleted_chunks,
        }


# 全局單例
_paper_rag_service: Optional[PaperRAGService] = None


def get_paper_rag_service() -> PaperRAGService:
    """獲取 Paper RAG 服務單例"""
    global _paper_rag_service
    if _paper_rag_service is None:
        _paper_rag_service = PaperRAGService()
    return _paper_rag_service
