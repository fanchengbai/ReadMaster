from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Book, Chapter, Paragraph, UserWord, Word, WordOccurrence
from app.schemas.vocabulary import (
    Definition,
    SaveUserWordRequest,
    UpdateUserWordRequest,
    UserWordResponse,
    WordOccurrenceResponse,
)
from app.services.dictionary import dictionary_data, normalize_word


def save_user_word(
    session: Session,
    request: SaveUserWordRequest,
) -> UserWordResponse:
    lemma = normalize_word(request.word)
    if not lemma:
        raise AppError("INVALID_WORD", "请选择一个有效的英文单词")

    book = session.get(Book, request.book_id)
    chapter = session.get(Chapter, request.chapter_id)
    paragraph = session.get(Paragraph, request.paragraph_id)
    if book is None:
        raise AppError("BOOK_NOT_FOUND", "未找到指定书籍", status_code=404)
    if chapter is None or chapter.book_id != book.id:
        raise AppError("CHAPTER_NOT_IN_BOOK", "章节不属于指定书籍")
    if paragraph is None or paragraph.chapter_id != chapter.id:
        raise AppError("PARAGRAPH_NOT_IN_CHAPTER", "段落不属于指定章节")
    if request.char_end > len(paragraph.content):
        raise AppError("INVALID_WORD_POSITION", "单词位置超出段落范围")

    selected_text = paragraph.content[request.char_start : request.char_end]
    if normalize_word(selected_text) != lemma:
        raise AppError("WORD_POSITION_MISMATCH", "单词与原文位置不匹配")

    word = session.scalar(
        select(Word).where(Word.lemma == lemma).options(selectinload(Word.user_word))
    )
    if word is None:
        phonetic, definitions, provider = dictionary_data(lemma)
        word = Word(
            lemma=lemma,
            phonetic=phonetic,
            definitions=definitions,
            provider=provider,
        )
        session.add(word)
        session.flush()

    user_word = word.user_word
    if user_word is None:
        user_word = UserWord(word=word, encounter_count=0)
        session.add(user_word)

    user_word.encounter_count += 1
    user_word.last_seen_at = datetime.now(UTC)
    occurrence = WordOccurrence(
        user_word=user_word,
        book_id=book.id,
        surface_form=selected_text,
        char_start=request.char_start,
        char_end=request.char_end,
        context=paragraph.content,
        source_book_title=book.title,
        source_chapter_title=chapter.title,
    )
    session.add(occurrence)
    session.commit()

    saved = get_user_word(session, user_word.id)
    return saved


def list_user_words(
    session: Session,
    familiarity: str | None = None,
) -> list[UserWordResponse]:
    query = (
        select(UserWord)
        .options(selectinload(UserWord.word), selectinload(UserWord.occurrences))
        .order_by(UserWord.last_seen_at.desc())
    )
    if familiarity:
        query = query.where(UserWord.familiarity == familiarity)
    return [to_user_word_response(item) for item in session.scalars(query).unique().all()]


def get_user_word(session: Session, user_word_id: str) -> UserWordResponse:
    user_word = session.scalar(
        select(UserWord)
        .where(UserWord.id == user_word_id)
        .options(selectinload(UserWord.word), selectinload(UserWord.occurrences))
    )
    if user_word is None:
        raise AppError("USER_WORD_NOT_FOUND", "未找到指定生词", status_code=404)
    return to_user_word_response(user_word)


def update_user_word(
    session: Session,
    user_word_id: str,
    update: UpdateUserWordRequest,
) -> UserWordResponse:
    user_word = session.get(UserWord, user_word_id)
    if user_word is None:
        raise AppError("USER_WORD_NOT_FOUND", "未找到指定生词", status_code=404)
    if update.familiarity is not None:
        user_word.familiarity = update.familiarity
    if update.note is not None:
        user_word.note = update.note.strip() or None
    session.commit()
    return get_user_word(session, user_word.id)


def delete_user_word(session: Session, user_word_id: str) -> None:
    user_word = session.get(UserWord, user_word_id)
    if user_word is None:
        raise AppError("USER_WORD_NOT_FOUND", "未找到指定生词", status_code=404)
    word = session.get(Word, user_word.word_id)
    session.delete(user_word)
    if word is not None:
        session.delete(word)
    session.commit()


def to_user_word_response(user_word: UserWord) -> UserWordResponse:
    latest = user_word.occurrences[0] if user_word.occurrences else None
    return UserWordResponse(
        id=user_word.id,
        lemma=user_word.word.lemma,
        phonetic=user_word.word.phonetic,
        definitions=[Definition.model_validate(item) for item in user_word.word.definitions or []],
        provider=user_word.word.provider,
        familiarity=user_word.familiarity,  # type: ignore[arg-type]
        encounter_count=user_word.encounter_count,
        wrong_count=user_word.wrong_count,
        review_stage=user_word.review_stage,
        consecutive_correct=user_word.consecutive_correct,
        next_review_at=user_word.next_review_at,
        last_reviewed_at=user_word.last_reviewed_at,
        note=user_word.note,
        first_seen_at=user_word.first_seen_at,
        last_seen_at=user_word.last_seen_at,
        latest_occurrence=(
            WordOccurrenceResponse(
                id=latest.id,
                book_id=latest.book_id,
                surface_form=latest.surface_form,
                context=latest.context,
                source_book_title=latest.source_book_title,
                source_chapter_title=latest.source_chapter_title,
                created_at=latest.created_at,
            )
            if latest
            else None
        ),
    )
