import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db

EMBEDDING_DIM = 512  # BAAI/bge-small-zh-v1.5 的實際輸出維度（hidden_size，無額外投影層）


class RagPaper(db.Model):
    __tablename__ = "rag_papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


class RagChunk(db.Model):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("rag_papers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
