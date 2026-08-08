import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


@login_manager.user_loader
def load_user(user_id: str) -> "User | None":
    return db.session.get(User, int(user_id))
