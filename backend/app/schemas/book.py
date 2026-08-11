from datetime import datetime

from pydantic import BaseModel


class BookSummary(BaseModel):
    id: str
    title: str
    author: str | None
    source_filename: str
    chapter_count: int
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
