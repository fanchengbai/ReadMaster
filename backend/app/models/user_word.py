from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.word import Word
    from app.models.word_occurrence import WordOccurrence


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserWord(Base):
    __tablename__ = "user_words"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    word_id: Mapped[str] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    familiarity: Mapped[str] = mapped_column(String(24), default="new", index=True)
    encounter_count: Mapped[int] = mapped_column(Integer, default=1)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    word: Mapped["Word"] = relationship(back_populates="user_word")
    occurrences: Mapped[list["WordOccurrence"]] = relationship(
        back_populates="user_word",
        cascade="all, delete-orphan",
        order_by="WordOccurrence.created_at.desc()",
    )
