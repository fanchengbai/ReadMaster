from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_word import UserWord


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReviewAttempt(Base):
    __tablename__ = "review_attempts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_word_id: Mapped[str] = mapped_column(
        ForeignKey("user_words.id", ondelete="CASCADE"),
        index=True,
    )
    question_type: Mapped[str] = mapped_column(String(32))
    prompt_snapshot: Mapped[str] = mapped_column(Text)
    correct_answer: Mapped[str] = mapped_column(String(128))
    submitted_answer: Mapped[str] = mapped_column(String(128))
    is_correct: Mapped[bool] = mapped_column(Boolean, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    user_word: Mapped["UserWord"] = relationship(back_populates="review_attempts")
