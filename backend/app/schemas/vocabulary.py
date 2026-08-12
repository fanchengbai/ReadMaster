from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Familiarity = Literal["new", "learning", "familiar", "mastered"]


class Definition(BaseModel):
    part_of_speech: str
    meaning: str


class DictionaryEntry(BaseModel):
    lemma: str
    surface_form: str
    phonetic: str | None
    definitions: list[Definition]
    provider: str
    found: bool
    saved: bool


class SaveUserWordRequest(BaseModel):
    word: str = Field(min_length=1, max_length=128)
    book_id: str
    chapter_id: str
    paragraph_id: str
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)


class UpdateUserWordRequest(BaseModel):
    familiarity: Familiarity | None = None
    note: str | None = Field(default=None, max_length=2000)


class WordOccurrenceResponse(BaseModel):
    id: str
    book_id: str | None
    surface_form: str
    context: str
    source_book_title: str
    source_chapter_title: str
    created_at: datetime


class UserWordResponse(BaseModel):
    id: str
    lemma: str
    phonetic: str | None
    definitions: list[Definition]
    provider: str | None
    familiarity: Familiarity
    encounter_count: int
    wrong_count: int
    note: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    latest_occurrence: WordOccurrenceResponse | None
