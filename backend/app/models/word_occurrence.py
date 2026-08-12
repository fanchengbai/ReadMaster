from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_word import UserWord


def utc_now() -> datetime:
    return datetime.now(UTC)


class WordOccurrence(Base):
    __tablename__ = "word_occurrences"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_word_id: Mapped[str] = mapped_column(
        ForeignKey("user_words.id", ondelete="CASCADE"),
        index=True,
    )
    book_id: Mapped[str | None] = mapped_column(
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    surface_form: Mapped[str] = mapped_column(String(128))
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    context: Mapped[str] = mapped_column(Text)
    source_book_title: Mapped[str] = mapped_column(String(255))
    source_chapter_title: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    user_word: Mapped["UserWord"] = relationship(back_populates="occurrences")
