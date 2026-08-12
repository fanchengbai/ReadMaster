from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_word import UserWord


def utc_now() -> datetime:
    return datetime.now(UTC)


class Word(Base):
    __tablename__ = "words"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    lemma: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    phonetic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    definitions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
    user_word: Mapped["UserWord | None"] = relationship(
        back_populates="word",
        cascade="all, delete-orphan",
        uselist=False,
    )
