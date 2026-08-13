import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from app.core.errors import AppError
from app.services.txt_parser import ParsedChapter

MAX_PDF_SIZE = 50 * 1024 * 1024
MAX_PDF_PAGES = 2000
MAX_EXTRACTED_CHARACTERS = 20_000_000


@dataclass(frozen=True)
class ParsedPdf:
    title: str | None
    author: str | None
    chapters: list[ParsedChapter]


def parse_pdf(payload: bytes) -> ParsedPdf:
    if not payload:
        raise AppError("EMPTY_FILE", "PDF 文件内容为空")
    if len(payload) > MAX_PDF_SIZE:
        raise AppError("FILE_TOO_LARGE", "PDF 文件不能超过 50 MB", status_code=413)
    if not payload.startswith(b"%PDF-"):
        raise AppError("INVALID_PDF", "文件不是有效的 PDF")

    try:
        reader = PdfReader(BytesIO(payload), strict=False)
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    raise AppError("ENCRYPTED_PDF", "暂不支持需要密码的 PDF 文件")
            except AppError:
                raise
            except Exception as error:
                raise AppError("ENCRYPTED_PDF", "暂不支持需要密码的 PDF 文件") from error
        if len(reader.pages) > MAX_PDF_PAGES:
            raise AppError("PDF_TOO_MANY_PAGES", "PDF 页数不能超过 2000 页")

        chapters: list[ParsedChapter] = []
        extracted_characters = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = clean_page_text(page.extract_text() or "")
            if not text:
                continue
            extracted_characters += len(text)
            if extracted_characters > MAX_EXTRACTED_CHARACTERS:
                raise AppError("PDF_TEXT_TOO_LARGE", "PDF 提取出的正文内容过大")
            paragraphs = split_paragraphs(text)
            if paragraphs:
                chapters.append(
                    ParsedChapter(
                        title=f"第 {page_number} 页",
                        raw_text=text,
                        paragraphs=paragraphs,
                    )
                )
    except AppError:
        raise
    except Exception as error:
        raise AppError("INVALID_PDF", "PDF 文件已损坏或结构无效") from error

    if not chapters:
        raise AppError(
            "PDF_TEXT_NOT_FOUND",
            "PDF 中没有可提取的文字；扫描版 PDF 暂不支持 OCR",
        )

    metadata = reader.metadata
    return ParsedPdf(
        title=clean_metadata(metadata.title if metadata else None),
        author=clean_metadata(metadata.author if metadata else None),
        chapters=chapters,
    )


def clean_page_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    normalized = re.sub(r"(?<=\w)-\n(?=\w)", "", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


def split_paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
    if len(blocks) == 1:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        blocks = join_wrapped_lines(lines)
    return [re.sub(r"\s+", " ", block).strip() for block in blocks if block.strip()]


def join_wrapped_lines(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not current and looks_like_heading(line):
            paragraphs.append(line)
            continue
        current.append(line)
        if re.search(r"[.!?][\"')\]]?$", line):
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def looks_like_heading(line: str) -> bool:
    words = line.split()
    if not 1 <= len(words) <= 12 or len(line) > 100:
        return False
    if re.search(r"[.!?;:]$", line):
        return False
    letter_words = [word.strip("\"'()[]") for word in words if any(char.isalpha() for char in word)]
    return bool(letter_words) and all(word[:1].isupper() for word in letter_words)


def clean_metadata(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.replace("\x00", "").split())[:255]
    return cleaned or None
