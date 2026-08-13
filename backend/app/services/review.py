import random
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import ReviewAttempt, UserWord
from app.schemas.review import (
    ReviewQuestion,
    ReviewSessionResponse,
    ReviewStatsResponse,
    SubmitReviewRequest,
    SubmitReviewResponse,
)

REVIEW_INTERVAL_DAYS = (1, 3, 7, 14, 30, 60)
WRONG_RETRY_DELAY = timedelta(minutes=10)


def create_review_session(session: Session, limit: int = 10) -> ReviewSessionResponse:
    now = datetime.now(UTC)
    all_words = session.scalars(
        select(UserWord)
        .where(UserWord.familiarity != "mastered")
        .options(selectinload(UserWord.word), selectinload(UserWord.occurrences))
        .order_by(UserWord.next_review_at.asc(), UserWord.wrong_count.desc())
    ).unique().all()
    user_words = [item for item in all_words if as_utc(item.next_review_at) <= now]

    questions: list[ReviewQuestion] = []
    meaning_pool = [
        item.word.definitions[0]["meaning"]
        for item in user_words
        if item.word.definitions
    ]

    for index, user_word in enumerate(user_words[:limit]):
        latest = user_word.occurrences[0] if user_word.occurrences else None
        use_meaning = index % 2 == 1 and user_word.word.definitions and len(set(meaning_pool)) >= 4
        if use_meaning:
            correct = user_word.word.definitions[0]["meaning"]
            distractors = [item for item in dict.fromkeys(meaning_pool) if item != correct]
            rng = random.Random(user_word.id)
            options = rng.sample(distractors, 3) + [correct]
            rng.shuffle(options)
            question = ReviewQuestion(
                id=user_word.id,
                type="meaning_choice",
                prompt=f'“{user_word.word.lemma}”最符合下面哪个释义？',
                options=options,
                source_book_title=latest.source_book_title if latest else None,
                source_chapter_title=latest.source_chapter_title if latest else None,
            )
        else:
            context = latest.context if latest else f"Complete the word: {user_word.word.lemma}"
            prompt = mask_word(context, user_word.word.lemma)
            question = ReviewQuestion(
                id=user_word.id,
                type="context_fill",
                prompt=prompt,
                options=[],
                source_book_title=latest.source_book_title if latest else None,
                source_chapter_title=latest.source_chapter_title if latest else None,
            )
        questions.append(question)

    scheduled = [item for item in all_words if as_utc(item.next_review_at) > now]
    next_review_at = min((as_utc(item.next_review_at) for item in scheduled), default=None)
    return ReviewSessionResponse(
        questions=questions,
        total_available=len(all_words),
        due_count=len(user_words),
        scheduled_count=len(scheduled),
        next_review_at=next_review_at,
    )


def submit_review(session: Session, request: SubmitReviewRequest) -> SubmitReviewResponse:
    user_word = session.scalar(
        select(UserWord)
        .where(UserWord.id == request.question_id)
        .options(selectinload(UserWord.word))
    )
    if user_word is None:
        raise AppError("REVIEW_WORD_NOT_FOUND", "这道训练题对应的生词已不存在", status_code=404)

    if request.question_type == "meaning_choice":
        if not user_word.word.definitions:
            raise AppError("REVIEW_DEFINITION_MISSING", "该生词暂无可用于训练的释义")
        correct_answer = user_word.word.definitions[0]["meaning"]
    else:
        correct_answer = user_word.word.lemma

    is_correct = normalize_answer(request.answer) == normalize_answer(correct_answer)
    attempted_at = datetime.now(UTC)
    if is_correct:
        user_word.review_stage = min(user_word.review_stage + 1, len(REVIEW_INTERVAL_DAYS))
        user_word.consecutive_correct += 1
        interval_days = REVIEW_INTERVAL_DAYS[user_word.review_stage - 1]
        user_word.next_review_at = attempted_at + timedelta(days=interval_days)
    else:
        user_word.wrong_count += 1
        user_word.review_stage = 0
        user_word.consecutive_correct = 0
        user_word.next_review_at = attempted_at + WRONG_RETRY_DELAY
    user_word.last_reviewed_at = attempted_at

    session.add(
        ReviewAttempt(
            user_word=user_word,
            question_type=request.question_type,
            prompt_snapshot=request.prompt,
            correct_answer=correct_answer,
            submitted_answer=request.answer.strip(),
            is_correct=is_correct,
            created_at=attempted_at,
        )
    )
    session.commit()
    explanation = (
        "回答正确，已经完成这次巩固。"
        if is_correct
        else f"正确答案是“{correct_answer}”，可以结合原句再记一次。"
    )
    return SubmitReviewResponse(
        is_correct=is_correct,
        correct_answer=correct_answer,
        explanation=explanation,
        wrong_count=user_word.wrong_count,
        review_stage=user_word.review_stage,
        next_review_at=user_word.next_review_at,
        answered_at=attempted_at,
    )


def get_review_stats(session: Session) -> ReviewStatsResponse:
    total, correct, words = session.execute(
        select(
            func.count(ReviewAttempt.id),
            func.sum(cast(ReviewAttempt.is_correct, Integer)),
            func.count(func.distinct(ReviewAttempt.user_word_id)),
        )
    ).one()
    total_attempts = int(total or 0)
    correct_attempts = int(correct or 0)
    now = datetime.now(UTC)
    review_words = session.scalars(
        select(UserWord).where(UserWord.familiarity != "mastered")
    ).all()
    due_count = sum(as_utc(item.next_review_at) <= now for item in review_words)
    future_dates = [
        as_utc(item.next_review_at)
        for item in review_words
        if as_utc(item.next_review_at) > now
    ]
    return ReviewStatsResponse(
        total_attempts=total_attempts,
        correct_attempts=correct_attempts,
        accuracy=round(correct_attempts / total_attempts * 100, 1) if total_attempts else 0,
        words_practiced=int(words or 0),
        due_count=due_count,
        scheduled_count=len(review_words) - due_count,
        next_review_at=min(future_dates, default=None),
    )


def mask_word(context: str, lemma: str) -> str:
    masked, count = re.subn(
        rf"\b{re.escape(lemma)}\b",
        "_____",
        context,
        count=1,
        flags=re.IGNORECASE,
    )
    return masked if count else f"Complete the word: _____ ({len(lemma)} letters)"


def normalize_answer(answer: str) -> str:
    return " ".join(answer.strip().lower().split())


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
