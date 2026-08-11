from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_app_settings, get_session
from app.core.config import Settings
from app.schemas.book import BookDetail, BookSummary, ChapterContent, ChapterSummary
from app.services.books import (
    MAX_UPLOAD_SIZE,
    delete_book,
    get_book,
    get_chapter,
    import_book,
    list_books,
)

router = APIRouter(tags=["books"])


@router.post("/books/import", response_model=BookDetail, status_code=status.HTTP_201_CREATED)
async def import_book_endpoint(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    title: Annotated[str | None, Form()] = None,
    author: Annotated[str | None, Form()] = None,
) -> BookDetail:
    filename = file.filename or ""
    try:
        payload = await file.read(MAX_UPLOAD_SIZE + 1)
    finally:
        await file.close()
    return import_book(
        session,
        payload=payload,
        filename=filename,
        data_dir=settings.data_dir,
        title=title,
        author=author,
    )


@router.get("/books", response_model=list[BookSummary])
def list_books_endpoint(
    session: Annotated[Session, Depends(get_session)],
) -> list[BookSummary]:
    return list_books(session)


@router.get("/books/{book_id}", response_model=BookDetail)
def get_book_endpoint(
    book_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> BookDetail:
    return get_book(session, book_id)


@router.get("/books/{book_id}/chapters", response_model=list[ChapterSummary])
def list_chapters_endpoint(
    book_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> list[ChapterSummary]:
    book = get_book(session, book_id)
    return book.chapters


@router.get("/chapters/{chapter_id}", response_model=ChapterContent)
def get_chapter_endpoint(
    chapter_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ChapterContent:
    return get_chapter(session, chapter_id)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book_endpoint(
    book_id: str,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> Response:
    delete_book(session, book_id, settings.data_dir)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
