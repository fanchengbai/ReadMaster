from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Book, Chapter, Paragraph, ReadingProgress
from app.schemas.book import ReadingProgressResponse, ReadingProgressUpdate


def get_progress(session: Session, book_id: str) -> ReadingProgressResponse:
    book = session.scalar(
        select(Book)
        .where(Book.id == book_id)
        .options(selectinload(Book.chapters), selectinload(Book.reading_progress))
    )
    if book is None:
        raise AppError("BOOK_NOT_FOUND", "未找到指定书籍", status_code=404)
    if not book.chapters:
        raise AppError("BOOK_HAS_NO_CHAPTERS", "这本书没有可阅读章节", status_code=409)

    progress = book.reading_progress
    if progress is None:
        return ReadingProgressResponse(
            book_id=book.id,
            chapter_id=book.chapters[0].id,
            paragraph_id=None,
            percentage=0.0,
            updated_at=None,
        )
    return to_progress_response(progress)


def update_progress(
    session: Session,
    book_id: str,
    update: ReadingProgressUpdate,
) -> ReadingProgressResponse:
    book = session.scalar(
        select(Book).where(Book.id == book_id).options(selectinload(Book.reading_progress))
    )
    if book is None:
        raise AppError("BOOK_NOT_FOUND", "未找到指定书籍", status_code=404)

    chapter = session.scalar(
        select(Chapter).where(Chapter.id == update.chapter_id, Chapter.book_id == book_id)
    )
    if chapter is None:
        raise AppError("CHAPTER_NOT_IN_BOOK", "章节不属于指定书籍", status_code=400)

    if update.paragraph_id is not None:
        paragraph = session.scalar(
            select(Paragraph).where(
                Paragraph.id == update.paragraph_id,
                Paragraph.chapter_id == update.chapter_id,
            )
        )
        if paragraph is None:
            raise AppError("PARAGRAPH_NOT_IN_CHAPTER", "段落不属于指定章节", status_code=400)

    percentage = max(0.0, min(update.percentage, 100.0))
    progress = book.reading_progress
    if progress is None:
        progress = ReadingProgress(book_id=book_id, chapter_id=update.chapter_id)
        session.add(progress)

    progress.chapter_id = update.chapter_id
    progress.paragraph_id = update.paragraph_id
    progress.percentage = percentage
    session.commit()
    session.refresh(progress)
    return to_progress_response(progress)


def to_progress_response(progress: ReadingProgress) -> ReadingProgressResponse:
    return ReadingProgressResponse(
        book_id=progress.book_id,
        chapter_id=progress.chapter_id,
        paragraph_id=progress.paragraph_id,
        percentage=progress.percentage,
        updated_at=progress.updated_at,
    )
