from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["context_fill", "meaning_choice"]


class ReviewQuestion(BaseModel):
    id: str
    type: QuestionType
    prompt: str
    options: list[str]
    lemma: str
    phonetic: str | None
    meanings: list[str]
    context: str
    source_book_title: str | None
    source_chapter_title: str | None


class ReviewSessionResponse(BaseModel):
    questions: list[ReviewQuestion]
    total_available: int
    due_count: int
    scheduled_count: int
    next_review_at: datetime | None


class SubmitReviewRequest(BaseModel):
    question_id: str
    question_type: QuestionType
    prompt: str = Field(min_length=1, max_length=5000)
    answer: str = Field(min_length=1, max_length=128)


class SubmitReviewResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str
    wrong_count: int
    review_stage: int
    next_review_at: datetime
    answered_at: datetime


class ReviewStatsResponse(BaseModel):
    total_attempts: int
    correct_attempts: int
    accuracy: float
    words_practiced: int
    due_count: int
    scheduled_count: int
    next_review_at: datetime | None


class CompleteGateItem(BaseModel):
    question_id: str
    mistake_count: int = Field(ge=0, le=100)


class CompleteGateReviewRequest(BaseModel):
    items: list[CompleteGateItem] = Field(min_length=1, max_length=30)


class CompleteGateReviewResponse(BaseModel):
    completed_count: int
    repaired_count: int
    next_review_at: datetime
