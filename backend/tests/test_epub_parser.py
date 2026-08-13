import pytest

from app.core.errors import AppError
from app.services import epub_parser
from app.services.epub_parser import parse_epub
from tests.helpers import create_minimal_epub


def test_epub_size_limit_is_200_mb() -> None:
    assert epub_parser.MAX_EPUB_SIZE == 200 * 1024 * 1024


def test_parse_epub_reads_metadata_navigation_and_spine() -> None:
    parsed = parse_epub(create_minimal_epub())

    assert parsed.title == "Learning Through Reading"
    assert parsed.author == "Jane Reader"
    assert [chapter.title for chapter in parsed.chapters] == [
        "A New Beginning",
        "Reading Practice",
    ]
    assert parsed.chapters[0].paragraphs == [
        "Reading connects us with another mind.",
        "Context gives unfamiliar words a place to live.",
    ]
    assert "this text must be ignored" not in parsed.chapters[1].raw_text


def test_parse_epub_rejects_invalid_zip_content() -> None:
    with pytest.raises(AppError, match="不是有效的压缩包"):
        parse_epub(b"not-an-epub")


def test_parse_epub_accepts_files_up_to_200_mb(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = create_minimal_epub()
    monkeypatch.setattr(epub_parser, "MAX_EPUB_SIZE", len(payload))

    assert parse_epub(payload).title == "Learning Through Reading"


def test_parse_epub_rejects_files_over_200_mb(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = create_minimal_epub()
    monkeypatch.setattr(epub_parser, "MAX_EPUB_SIZE", len(payload) - 1)

    with pytest.raises(AppError, match="EPUB 文件不能超过 200 MB"):
        parse_epub(payload)
