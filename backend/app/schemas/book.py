from datetime import datetime

from pydantic import BaseModel


class BookSummary(BaseModel):
    id: str
    title: str
    author: str | None
    source_filename: str
    format: str
    chapter_count: int
    progress_percentage: float
    current_chapter_id: str | None
    created_at: datetime


class ChapterSummary(BaseModel):
    id: str
    title: str
    order_index: int
    paragraph_count: int


class BookDetail(BookSummary):
    chapters: list[ChapterSummary]


class ParagraphResponse(BaseModel):
    id: str
    order_index: int
    content: str


class ChapterContent(ChapterSummary):
    book_id: str
    paragraphs: list[ParagraphResponse]


class ReadingProgressResponse(BaseModel):
    book_id: str
    chapter_id: str
    paragraph_id: str | None
    percentage: float
    updated_at: datetime | None


class ReadingProgressUpdate(BaseModel):
    chapter_id: str
    paragraph_id: str | None = None
    percentage: float
