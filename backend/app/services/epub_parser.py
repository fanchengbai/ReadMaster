import posixpath
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urldefrag
from zipfile import BadZipFile, ZipFile

from app.core.errors import AppError
from app.services.txt_parser import ParsedChapter

MAX_EPUB_SIZE = 50 * 1024 * 1024
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5000
CONTAINER_NAMESPACE = "urn:oasis:names:tc:opendocument:xmlns:container"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"


@dataclass(frozen=True)
class ParsedEpub:
    title: str | None
    author: str | None
    chapters: list[ParsedChapter]


@dataclass(frozen=True)
class ManifestItem:
    item_id: str
    path: str
    media_type: str
    properties: set[str]


def parse_epub(payload: bytes) -> ParsedEpub:
    if not payload:
        raise AppError("EMPTY_FILE", "EPUB 文件内容为空")
    if len(payload) > MAX_EPUB_SIZE:
        raise AppError("FILE_TOO_LARGE", "EPUB 文件不能超过 50 MB", status_code=413)

    try:
        with ZipFile(BytesIO(payload)) as archive:
            validate_archive(archive)
            opf_path = find_package_path(archive)
            package_root = parse_xml(read_entry(archive, opf_path), "EPUB 包信息损坏")
            title, author = read_metadata(package_root)
            manifest = read_manifest(package_root, opf_path)
            spine = read_spine(package_root)
            navigation_titles = read_navigation_titles(archive, manifest)
            chapters = read_chapters(archive, manifest, spine, navigation_titles)
    except BadZipFile as error:
        raise AppError("INVALID_EPUB", "EPUB 文件不是有效的压缩包") from error

    if not chapters:
        raise AppError("INVALID_EPUB", "EPUB 中没有可阅读的章节内容")
    return ParsedEpub(title=title, author=author, chapters=chapters)


def validate_archive(archive: ZipFile) -> None:
    entries = archive.infolist()
    if len(entries) > MAX_ARCHIVE_ENTRIES:
        raise AppError("INVALID_EPUB", "EPUB 文件包含过多内部文件")

    total_size = 0
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts:
            raise AppError("INVALID_EPUB", "EPUB 文件包含不安全的内部路径")
        if entry.flag_bits & 0x1:
            raise AppError("INVALID_EPUB", "暂不支持加密的 EPUB 文件")
        total_size += entry.file_size
        if total_size > MAX_UNCOMPRESSED_SIZE:
            raise AppError("INVALID_EPUB", "EPUB 解压后的内容过大")


def find_package_path(archive: ZipFile) -> str:
    container = parse_xml(
        read_entry(archive, "META-INF/container.xml"),
        "EPUB 缺少有效的容器信息",
    )
    rootfile = container.find(f".//{{{CONTAINER_NAMESPACE}}}rootfile")
    if rootfile is None or not rootfile.get("full-path"):
        raise AppError("INVALID_EPUB", "EPUB 缺少内容包路径")
    return normalize_archive_path(rootfile.get("full-path", ""))


def read_metadata(package_root: ET.Element) -> tuple[str | None, str | None]:
    title_node = package_root.find(f".//{{{DC_NAMESPACE}}}title")
    author_node = package_root.find(f".//{{{DC_NAMESPACE}}}creator")
    return clean_text(title_node), clean_text(author_node)


def read_manifest(package_root: ET.Element, opf_path: str) -> dict[str, ManifestItem]:
    package_dir = posixpath.dirname(opf_path)
    manifest: dict[str, ManifestItem] = {}
    for item in package_root.findall(".//{*}manifest/{*}item"):
        item_id = item.get("id")
        href = item.get("href")
        if not item_id or not href:
            continue
        manifest[item_id] = ManifestItem(
            item_id=item_id,
            path=resolve_path(package_dir, href),
            media_type=item.get("media-type", ""),
            properties=set(item.get("properties", "").split()),
        )
    if not manifest:
        raise AppError("INVALID_EPUB", "EPUB 缺少资源清单")
    return manifest


def read_spine(package_root: ET.Element) -> list[str]:
    spine = [
        item.get("idref", "")
        for item in package_root.findall(".//{*}spine/{*}itemref")
        if item.get("idref")
    ]
    if not spine:
        raise AppError("INVALID_EPUB", "EPUB 缺少阅读顺序")
    return spine


def read_navigation_titles(
    archive: ZipFile,
    manifest: dict[str, ManifestItem],
) -> dict[str, str]:
    titles: dict[str, str] = {}
    nav_item = next((item for item in manifest.values() if "nav" in item.properties), None)
    if nav_item is not None:
        navigation_root = parse_xml(read_entry(archive, nav_item.path), "EPUB 目录损坏")
        navigation_dir = posixpath.dirname(nav_item.path)
        for link in navigation_root.findall(".//{*}nav//{*}a"):
            href = link.get("href")
            title = clean_text(link)
            if href and title:
                titles[resolve_path(navigation_dir, href)] = title

    ncx_item = next(
        (item for item in manifest.values() if item.media_type == "application/x-dtbncx+xml"),
        None,
    )
    if ncx_item is not None:
        navigation_root = parse_xml(read_entry(archive, ncx_item.path), "EPUB 目录损坏")
        navigation_dir = posixpath.dirname(ncx_item.path)
        for point in navigation_root.findall(".//{*}navPoint"):
            content = point.find("./{*}content")
            label = point.find("./{*}navLabel/{*}text")
            if content is None or not content.get("src"):
                continue
            title = clean_text(label)
            if title:
                titles[resolve_path(navigation_dir, content.get("src", ""))] = title
    return titles


def read_chapters(
    archive: ZipFile,
    manifest: dict[str, ManifestItem],
    spine: list[str],
    navigation_titles: dict[str, str],
) -> list[ParsedChapter]:
    chapters: list[ParsedChapter] = []
    for item_id in spine:
        item = manifest.get(item_id)
        if item is None or item.media_type not in {"application/xhtml+xml", "text/html"}:
            continue
        content = read_entry(archive, item.path)
        extractor = EpubHtmlExtractor()
        extractor.feed(content.decode("utf-8", errors="replace"))
        extractor.close()
        paragraphs = extractor.paragraphs
        if not paragraphs:
            continue
        title = navigation_titles.get(item.path) or extractor.first_heading or item.item_id
        if paragraphs and normalize_text(paragraphs[0]) == normalize_text(title):
            paragraphs = paragraphs[1:]
        if not paragraphs:
            continue
        raw_text = "\n\n".join(paragraphs)
        chapters.append(ParsedChapter(title=title, raw_text=raw_text, paragraphs=paragraphs))
    return chapters


class EpubHtmlExtractor(HTMLParser):
    block_tags = {
        "article",
        "blockquote",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
    }
    heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}
    skipped_tags = {"script", "style", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self.first_heading: str | None = None
        self._buffer: list[str] = []
        self._heading: str | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, _: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.skipped_tags:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in self.block_tags:
            self._flush()
        if tag in self.heading_tags:
            self._heading = tag
        if tag == "br":
            self._buffer.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.skipped_tags and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self.block_tags:
            text = self._flush()
            if tag in self.heading_tags and text and self.first_heading is None:
                self.first_heading = text
            self._heading = None

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> str | None:
        text = normalize_text(" ".join(self._buffer))
        self._buffer.clear()
        if text and (not self.paragraphs or self.paragraphs[-1] != text):
            self.paragraphs.append(text)
            return text
        return None


def read_entry(archive: ZipFile, path: str) -> bytes:
    normalized = normalize_archive_path(path)
    try:
        return archive.read(normalized)
    except KeyError as error:
        raise AppError("INVALID_EPUB", f"EPUB 缺少内部文件：{normalized}") from error


def parse_xml(content: bytes, message: str) -> ET.Element:
    try:
        return ET.fromstring(content)
    except ET.ParseError as error:
        raise AppError("INVALID_EPUB", message) from error


def resolve_path(base_dir: str, href: str) -> str:
    path, _ = urldefrag(unquote(href))
    return normalize_archive_path(posixpath.join(base_dir, path))


def normalize_archive_path(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
    if normalized == ".." or normalized.startswith("../"):
        raise AppError("INVALID_EPUB", "EPUB 文件包含不安全的内部路径")
    return normalized


def clean_text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    text = normalize_text(" ".join(element.itertext()))
    return text or None


def normalize_text(text: str) -> str:
    return " ".join(text.split())
