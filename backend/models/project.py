import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db


class ProjectStatus(enum.Enum):
    draft = "draft"
    running = "running"
    completed = "completed"


class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"), nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"), default=ProjectStatus.draft, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key_finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # { 論文變數名: 使用者欄位名 }，由欄位對齊頁寫入
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )
