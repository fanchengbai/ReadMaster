r"""从地址列表批量抓取可可英语中英内容，并合并生成一个 TXT 文件。

用法：
    .venv\Scripts\python.exe tools\crawl_kekenet_list.py ^
        tools\kekenet_urls.example.txt ^
        --output-name "可可英语精选对话.txt"

地址列表每行填写一个 lesson 网页地址。空行和以 # 开头的行会被忽略。
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from crawl_kekenet import LESSON_URL, CrawlError, Lesson, fetch_lesson, render_lessons

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def read_urls(list_file: Path) -> list[str]:
    try:
        content = list_file.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise CrawlError(f"地址列表文件不存在：{list_file}") from error
    except OSError as error:
        raise CrawlError(f"无法读取地址列表文件：{error}") from error

    urls: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not LESSON_URL.fullmatch(line):
            print(f"第 {line_number} 行不是有效的 lesson 地址，已跳过：{line}")
            continue
        if line not in seen:
            seen.add(line)
            urls.append(line)

    if not urls:
        raise CrawlError("地址列表中没有有效的可可英语 lesson 地址")
    return urls


def normalize_output_name(value: str) -> str:
    name = Path(value.strip()).name
    name = INVALID_FILENAME.sub("_", name).strip(" .")
    if not name:
        raise CrawlError("输出文件名不能为空")
    if not name.lower().endswith(".txt"):
        name += ".txt"
    return name


def download_urls(urls: list[str], delay: float) -> tuple[list[Lesson], int]:
    lessons: list[Lesson] = []
    failed = 0
    for position, url in enumerate(urls, start=1):
        match = LESSON_URL.fullmatch(url)
        if match is None:
            failed += 1
            continue
        course_id, lesson_id = map(int, match.groups())
        try:
            lesson = fetch_lesson(course_id, lesson_id)
            lessons.append(lesson)
            print(f"[{position}/{len(urls)}] 成功：{lesson_id} {lesson.title}")
        except CrawlError as error:
            failed += 1
            print(f"[{position}/{len(urls)}] 失败：{url}（{error}）")
        if position < len(urls):
            time.sleep(delay)
    return lessons, failed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从地址列表批量抓取可可英语中英内容，生成一个 TXT 文件"
    )
    parser.add_argument("list_file", type=Path, help="地址列表文件，一行一个 lesson 地址")
    parser.add_argument(
        "--output-name",
        required=True,
        help="输出文件名，例如 可可英语精选对话.txt",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "books",
        help="输出目录，默认是项目 books 目录",
    )
    parser.add_argument("--delay", type=float, default=0.6, help="每个网页之间的请求间隔秒数")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.delay < 0.2:
            raise CrawlError("请求间隔不能小于 0.2 秒")
        urls = read_urls(args.list_file)
        output_name = normalize_output_name(args.output_name)
        lessons, failed = download_urls(urls, args.delay)
        if not lessons:
            raise CrawlError("列表中的网页全部下载失败，没有生成 TXT")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / output_name
        output.write_text(render_lessons(lessons), encoding="utf-8")
        pair_count = sum(len(lesson.lines) for lesson in lessons)
        print(f"完成：成功 {len(lessons)} 页，失败 {failed} 页，共 {pair_count} 组中英对照")
        print(f"文件：{output.resolve()}")
        return 0
    except CrawlError as error:
        print(f"下载失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
