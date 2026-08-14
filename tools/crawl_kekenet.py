"""独立抓取可可英语逐句中英对话，不依赖 ReadMaster 后端代码。

首次使用：
    python -m pip install cryptography

抓取单课：
    python tools/crawl_kekenet.py https://www.kekenet.com/lesson/18772-705200

按网页编号递增抓取 100 课（705200 到 705299）：
    python tools/crawl_kekenet.py https://www.kekenet.com/lesson/18772-705200 --count 100

抓取指定编号范围：
    python tools/crawl_kekenet.py https://www.kekenet.com/lesson/18772-705200 --end-id 705299
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
except ImportError:
    print("缺少 cryptography，请先运行：python -m pip install cryptography", file=sys.stderr)
    raise SystemExit(2) from None

API_URL = "https://mob2015.kekenet.com/keke/mobile/index.php"
AES_KEY = b"51E881E6F2A6Y9K8"
AES_IV = b"9F0885C2D686C418"
LESSON_URL = re.compile(
    r"https?://(?:www\.)?kekenet\.com/lesson/(\d+)-(\d+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
HTML_TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


class CrawlError(RuntimeError):
    pass


@dataclass(frozen=True)
class DialogueLine:
    english: str
    chinese: str


@dataclass(frozen=True)
class Lesson:
    lesson_id: int
    title: str
    lines: list[DialogueLine]


def decrypt_payload(ciphertext: str) -> Any:
    try:
        encrypted = bytes.fromhex(ciphertext)
        decryptor = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV)).decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = PKCS7(algorithms.AES.block_size).unpadder()
        decoded = unpadder.update(padded) + unpadder.finalize()
        return json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CrawlError("网站数据无法解码，接口格式可能已经变化") from error


def make_request_body(lesson_id: int) -> bytes:
    payload = {
        "Method": "web_waikan_wkgetcontent",
        "Params": {"id": lesson_id, "version_flag": 1},
        "Token": "",
        "Terminal": 13,
        "Version": "4.0",
        "UID": "",
        "AppFlag": 18,
        "Sign": "",
        "ApTime": int(time.time() * 1000),
        "ApVersionCode": 100,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def request_lesson_data(course_id: int, lesson_id: int, retries: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = Request(
            API_URL,
            data=make_request_body(lesson_id),
            headers={
                "Content-Type": "text/plain",
                "Origin": "https://www.kekenet.com",
                "Referer": f"https://www.kekenet.com/lesson/{course_id}-{lesson_id}",
                "User-Agent": "ReadMaster dialogue crawler/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            if envelope.get("Code") != 200:
                raise CrawlError(envelope.get("Msg") or "网页没有这节课")
            data = envelope.get("Data")
            return decrypt_payload(data) if envelope.get("IsDecode") == 1 else data
        except CrawlError:
            raise
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise CrawlError(f"网络请求连续失败：{last_error}") from last_error


def clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = HTML_TAG.sub(" ", text)
    return SPACE.sub(" ", text).strip()


def fetch_lesson(course_id: int, lesson_id: int) -> Lesson:
    data = request_lesson_data(course_id, lesson_id)
    if not isinstance(data, dict) or not isinstance(data.get("content"), list):
        raise CrawlError("网页没有可读取的逐句内容")

    title = clean_text(data.get("title")) or f"Lesson {lesson_id}"
    lines: list[DialogueLine] = []
    for item in data["content"]:
        if not isinstance(item, dict):
            continue
        english = clean_text(item.get("en"))
        chinese = clean_text(item.get("cn"))
        if english or chinese:
            lines.append(DialogueLine(english, chinese))
    if not lines:
        raise CrawlError("网页没有中英对话")
    return Lesson(lesson_id, title, lines)


def render_lessons(lessons: list[Lesson]) -> str:
    output: list[str] = []
    for chapter_number, lesson in enumerate(lessons, start=1):
        output.append(f"Chapter {chapter_number} - {lesson.title}")
        output.append("")
        for line in lesson.lines:
            if line.english:
                output.append(line.english)
            if line.chinese:
                output.append(line.chinese)
            output.append("")
    return "\n".join(output).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按课文编号递增抓取可可英语中英对话，生成 ReadMaster 可导入的 TXT"
    )
    parser.add_argument("url", help="起始课文地址，例如 .../lesson/18772-705200")
    range_group = parser.add_mutually_exclusive_group()
    range_group.add_argument("--count", type=int, default=1, help="连续尝试的网页数量")
    range_group.add_argument("--end-id", type=int, help="抓取到这个课文编号（包含）")
    parser.add_argument("--output", type=Path, help="输出 TXT 文件路径")
    parser.add_argument("--delay", type=float, default=0.6, help="请求间隔秒数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    match = LESSON_URL.fullmatch(args.url.strip())
    if not match:
        print("网址格式不正确，应类似 /lesson/18772-705200", file=sys.stderr)
        return 1

    course_id, start_id = map(int, match.groups())
    end_id = args.end_id if args.end_id is not None else start_id + args.count - 1
    if end_id < start_id or args.count < 1:
        print("结束编号或抓取数量不正确", file=sys.stderr)
        return 1
    if args.delay < 0.2:
        print("请求间隔不能小于 0.2 秒", file=sys.stderr)
        return 1

    lessons: list[Lesson] = []
    total = end_id - start_id + 1
    for position, lesson_id in enumerate(range(start_id, end_id + 1), start=1):
        try:
            lesson = fetch_lesson(course_id, lesson_id)
            lessons.append(lesson)
            print(f"[{position}/{total}] 成功：{lesson_id} {lesson.title}")
        except CrawlError as error:
            print(f"[{position}/{total}] 跳过：{lesson_id}（{error}）")
        if position < total:
            time.sleep(args.delay)

    if not lessons:
        print("没有抓取到任何课文", file=sys.stderr)
        return 1

    default_output = (
        Path(__file__).resolve().parents[1]
        / "books"
        / f"可可英语-{course_id}-{start_id}-{end_id}-中英双语.txt"
    )
    output = args.output or default_output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_lessons(lessons), encoding="utf-8")
    pair_count = sum(len(lesson.lines) for lesson in lessons)
    print(f"完成：{len(lessons)} 课，{pair_count} 组中英对照")
    print(f"文件：{output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
