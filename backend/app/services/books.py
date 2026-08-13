import hashlib
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.models import Book, Chapter, Paragraph
from app.schemas.book import (
    BookDetail,
    BookSummary,
    ChapterContent,
    ChapterSummary,
    ParagraphResponse,
)
from app.services.epub_parser import MAX_EPUB_SIZE, ParsedEpub, parse_epub
from app.services.pdf_parser import MAX_PDF_SIZE, ParsedPdf, parse_pdf
from app.services.txt_parser import ParsedChapter, decode_txt, parse_txt

MAX_TXT_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_SIZE = max(MAX_EPUB_SIZE, MAX_PDF_SIZE)
SUPPORTED_EXTENSIONS = {".txt", ".epub", ".pdf"}


def import_book(
    session: Session,
    *,
    payload: bytes,
    filename: str,
    data_dir: Path,
    title: str | None = None,
    author: str | None = None,
) -> BookDetail:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise AppError("UNSUPPORTED_FILE_TYPE", "目前仅支持导入 TXT、EPUB 和 PDF 文件")

    file_hash = hashlib.sha256(payload).hexdigest()
    duplicate = session.scalar(select(Book.id).where(Book.file_hash == file_hash))
    if duplicate is not None:
        raise AppError("BOOK_ALREADY_EXISTS", "这本书已经导入", status_code=409)

    if extension == ".txt":
        parsed_chapters, detected_title, detected_author, stored_payload = prepare_txt(
            payload,
            filename,
        )
    elif extension == ".epub":
        parsed_chapters, detected_title, detected_author, stored_payload = prepare_epub(
            payload,
            filename,
        )
    else:
        parsed_chapters, detected_title, detected_author, stored_payload = prepare_pdf(
            payload,
            filename,
        )

    book_id = str(uuid4())
    books_dir = data_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    relative_path = Path("books") / f"{book_id}{extension}"
    stored_file = data_dir / relative_path
    stored_file.write_bytes(stored_payload)

    book = Book(
        id=book_id,
        title=(title or detected_title).strip() or "未命名书籍",
        author=(author or detected_author or "").strip() or None,
        source_filename=Path(filename).name,
        stored_path=relative_path.as_posix(),
        file_hash=file_hash,
    )
    for chapter_index, parsed in enumerate(parsed_chapters):
        chapter = Chapter(
            title=parsed.title,
            order_index=chapter_index,
            raw_text=parsed.raw_text,
        )
        chapter.paragraphs = [
            Paragraph(order_index=paragraph_index, content=content)
            for paragraph_index, content in enumerate(parsed.paragraphs)
        ]
        book.chapters.append(chapter)

    try:
        session.add(book)
        session.commit()
    except Exception:
        session.rollback()
        stored_file.unlink(missing_ok=True)
        raise

    return to_book_detail(book)


def prepare_txt(
    payload: bytes,
    filename: str,
) -> tuple[list[ParsedChapter], str, None, bytes]:
    if len(payload) > MAX_TXT_SIZE:
        raise AppError("FILE_TOO_LARGE", "TXT 文件不能超过 10 MB", status_code=413)
    text = decode_txt(payload)
    chapters = parse_txt(text)
    if not chapters:
        raise AppError("EMPTY_FILE", "TXT 文件中没有可阅读的内容")
    return chapters, Path(filename).stem, None, text.encode("utf-8")


def prepare_epub(
    payload: bytes,
    filename: str,
) -> tuple[list[ParsedChapter], str, str | None, bytes]:
    parsed: ParsedEpub = parse_epub(payload)
    return parsed.chapters, parsed.title or Path(filename).stem, parsed.author, payload


def prepare_pdf(
    payload: bytes,
    filename: str,
) -> tuple[list[ParsedChapter], str, str | None, bytes]:
    parsed: ParsedPdf = parse_pdf(payload)
    return parsed.chapters, parsed.title or Path(filename).stem, parsed.author, payload


def list_books(session: Session) -> list[BookSummary]:
    books = session.scalars(
        select(Book)
        .options(selectinload(Book.chapters), selectinload(Book.reading_progress))
        .order_by(Book.created_at.desc())
    ).all()
    return [to_book_summary(book) for book in books]


def get_book(session: Session, book_id: str) -> BookDetail:
    book = session.scalar(
        select(Book)
        .where(Book.id == book_id)
        .options(
            selectinload(Book.chapters).selectinload(Chapter.paragraphs),
            selectinload(Book.reading_progress),
        )
    )
    if book is None:
        raise AppError("BOOK_NOT_FOUND", "未找到指定书籍", status_code=404)
    return to_book_detail(book)


def get_chapter(session: Session, chapter_id: str) -> ChapterContent:
    chapter = session.scalar(
        select(Chapter)
        .where(Chapter.id == chapter_id)
        .options(selectinload(Chapter.paragraphs))
    )
    if chapter is None:
        raise AppError("CHAPTER_NOT_FOUND", "未找到指定章节", status_code=404)
    return ChapterContent(
        id=chapter.id,
        book_id=chapter.book_id,
        title=chapter.title,
        order_index=chapter.order_index,
        paragraph_count=len(chapter.paragraphs),
        paragraphs=[
            ParagraphResponse(
                id=paragraph.id,
                order_index=paragraph.order_index,
                content=paragraph.content,
            )
            for paragraph in chapter.paragraphs
        ],
    )


def delete_book(session: Session, book_id: str, data_dir: Path) -> None:
    book = session.get(Book, book_id)
    if book is None:
        raise AppError("BOOK_NOT_FOUND", "未找到指定书籍", status_code=404)

    stored_file = data_dir / book.stored_path
    session.delete(book)
    session.commit()
    stored_file.unlink(missing_ok=True)


def to_book_summary(book: Book) -> BookSummary:
    return BookSummary(
        id=book.id,
        title=book.title,
        author=book.author,
        source_filename=book.source_filename,
        format=Path(book.source_filename).suffix.removeprefix(".").upper(),
        chapter_count=len(book.chapters),
        progress_percentage=book.reading_progress.percentage if book.reading_progress else 0.0,
        current_chapter_id=(book.reading_progress.chapter_id if book.reading_progress else None),
        created_at=book.created_at,
    )


def to_book_detail(book: Book) -> BookDetail:
    summary = to_book_summary(book)
    return BookDetail(
        **summary.model_dump(),
        chapters=[
            ChapterSummary(
                id=chapter.id,
                title=chapter.title,
                order_index=chapter.order_index,
                paragraph_count=len(chapter.paragraphs),
            )
            for chapter in book.chapters
        ],
    )
