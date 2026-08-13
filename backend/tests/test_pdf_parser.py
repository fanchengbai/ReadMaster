import pytest

from app.core.errors import AppError
from app.services.pdf_parser import parse_pdf, split_paragraphs
from tests.helpers import create_image_only_pdf, create_minimal_pdf


def test_parse_pdf_reads_metadata_and_pages() -> None:
    parsed = parse_pdf(create_minimal_pdf())

    assert parsed.title == "Learning From PDF"
    assert parsed.author == "Jane Reader"
    assert [chapter.title for chapter in parsed.chapters] == ["第 1 页", "第 2 页"]
    assert parsed.chapters[0].paragraphs == [
        "Curiosity makes reading active.",
        "Context gives words meaning.",
    ]
    assert parsed.chapters[1].paragraphs == [
        "Practice turns recognition into understanding."
    ]


def test_parse_pdf_rejects_invalid_content() -> None:
    with pytest.raises(AppError, match="不是有效的 PDF"):
        parse_pdf(b"not-a-pdf")


def test_parse_pdf_explains_that_image_only_files_need_ocr() -> None:
    with pytest.raises(AppError, match="扫描版 PDF 暂不支持 OCR"):
        parse_pdf(create_image_only_pdf())


def test_split_paragraphs_keeps_short_title_separate() -> None:
    assert split_paragraphs(
        "A New Page\nCuriosity makes reading active.\nContext gives words meaning."
    ) == [
        "A New Page",
        "Curiosity makes reading active.",
        "Context gives words meaning.",
    ]
