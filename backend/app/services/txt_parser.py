import re
from dataclasses import dataclass

from charset_normalizer import from_bytes

from app.core.errors import AppError

CHAPTER_HEADING = re.compile(
    r"^(?:chapter|part|book)\s+(?:\d+|[ivxlcdm]+|[a-z]+)\b.*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedChapter:
    title: str
    raw_text: str
    paragraphs: list[str]


def decode_txt(payload: bytes) -> str:
    if not payload:
        raise AppError("EMPTY_FILE", "TXT 文件内容为空")

    if payload.startswith(b"\xef\xbb\xbf"):
        return payload.decode("utf-8-sig")

    match = from_bytes(payload).best()
    if match is None:
        raise AppError("TEXT_ENCODING_UNSUPPORTED", "无法识别 TXT 文件编码")

    text = str(match)
    if not text.strip():
        raise AppError("EMPTY_FILE", "TXT 文件内容为空")
    return text


def parse_txt(text: str) -> list[ParsedChapter]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    lines = normalized.split("\n")
    heading_indexes = [
        index
        for index, line in enumerate(lines)
        if len(line.strip()) <= 160 and CHAPTER_HEADING.fullmatch(line.strip())
    ]

    if not heading_indexes:
        chapter = build_chapter("正文", normalized)
        return [chapter] if chapter.paragraphs else []

    chapters: list[ParsedChapter] = []
    first_heading = heading_indexes[0]
    introduction = "\n".join(lines[:first_heading]).strip()
    if introduction:
        introduction_chapter = build_chapter("前言", introduction)
        if introduction_chapter.paragraphs:
            chapters.append(introduction_chapter)

    for position, heading_index in enumerate(heading_indexes):
        end_index = (
            heading_indexes[position + 1] if position + 1 < len(heading_indexes) else len(lines)
        )
        title = " ".join(lines[heading_index].split())
        content = "\n".join(lines[heading_index + 1 : end_index]).strip()
        chapters.append(build_chapter(title, content))

    return chapters


def build_chapter(title: str, raw_text: str) -> ParsedChapter:
    paragraphs = []
    for block in re.split(r"\n\s*\n", raw_text.strip()):
        paragraph = " ".join(line.strip() for line in block.split("\n") if line.strip())
        if paragraph:
            paragraphs.append(paragraph)
    return ParsedChapter(title=title, raw_text=raw_text.strip(), paragraphs=paragraphs)
