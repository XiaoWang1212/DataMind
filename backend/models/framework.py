import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class Framework(db.Model):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variables: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paper_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    independent_vars: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    dependent_vars: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    hypotheses: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    workflow_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # 上傳的 PDF 內容 SHA-256（小寫十六進位）。本次改動之前建立的框架沒有這個值，
    # 且無法回填——原始 PDF 沒有留存
    pdf_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
