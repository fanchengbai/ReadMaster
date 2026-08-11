import pytest

from app.core.errors import AppError
from app.services.txt_parser import decode_txt, parse_txt


def test_parse_txt_detects_chapters_and_paragraphs() -> None:
    text = """A short introduction.

CHAPTER I. START

The first paragraph spans
two wrapped lines.

The second paragraph.

Chapter 2 Another Day

The final paragraph.
"""

    chapters = parse_txt(text)

    assert [chapter.title for chapter in chapters] == [
        "前言",
        "CHAPTER I. START",
        "Chapter 2 Another Day",
    ]
    assert chapters[1].paragraphs == [
        "The first paragraph spans two wrapped lines.",
        "The second paragraph.",
    ]


def test_parse_txt_uses_single_chapter_when_no_heading_exists() -> None:
    chapters = parse_txt("First paragraph.\n\nSecond paragraph.")

    assert len(chapters) == 1
    assert chapters[0].title == "正文"
    assert chapters[0].paragraphs == ["First paragraph.", "Second paragraph."]


def test_decode_txt_rejects_empty_content() -> None:
    with pytest.raises(AppError, match="TXT 文件内容为空"):
        decode_txt(b"")
