r"""从地址列表批量抓取可可英语中英内容，并合并生成一个 TXT 文件。

用法：
    .venv\Scripts\python.exe tools\crawl_kekenet_list.py ^
        tools\kekenet_urls.example.txt ^
        --output-name "可可英语精选对话.txt"

地址列表每行填写一个 lesson 网页地址。空行和以 # 开头的行会被忽略。
脚本会在输出文件旁保存 ``.crawl-state.json`` 进度文件，以支持断点续传。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO

from crawl_kekenet import LESSON_URL, CrawlError, Lesson, fetch_lesson

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
CHAPTER_HEADER = re.compile(r"^Chapter \d+ - ", re.MULTILINE)
STATE_VERSION = 1


class ProgressError(CrawlError):
    """进度或输出文件无法安全读写。"""


@dataclass(frozen=True)
class CrawlState:
    completed_urls: list[str]
    output_size: int
    pending_url: str | None = None


@dataclass(frozen=True)
class DownloadSummary:
    downloaded: int
    skipped: int
    failed: int
    pair_count: int
    state: CrawlState


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


def progress_path_for(output: Path) -> Path:
    return output.with_name(f"{output.name}.crawl-state.json")


def render_lesson(chapter_number: int, lesson: Lesson) -> bytes:
    lines = [f"Chapter {chapter_number} - {lesson.title}", ""]
    for line in lesson.lines:
        if line.english:
            lines.extend((line.english, ""))
        if line.chinese:
            lines.extend((line.chinese, ""))
    return ("\n".join(lines).rstrip() + "\n\n").encode("utf-8")


def write_lesson(output: BinaryIO, chapter_number: int, lesson: Lesson) -> int:
    try:
        output.write(render_lesson(chapter_number, lesson))
        output.flush()
        os.fsync(output.fileno())
        return output.tell()
    except OSError as error:
        raise ProgressError(f"章节写入失败：{error}") from error


def save_state(state_file: Path, state: CrawlState) -> None:
    temporary = state_file.with_name(f"{state_file.name}.tmp")
    payload = {
        "version": STATE_VERSION,
        "completed_urls": state.completed_urls,
        "output_size": state.output_size,
        "pending_url": state.pending_url,
    }
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, state_file)
    except OSError as error:
        raise ProgressError(f"无法保存下载进度：{error}") from error


def load_state(state_file: Path) -> CrawlState:
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProgressError(f"进度文件损坏或无法读取：{state_file}") from error

    completed = payload.get("completed_urls")
    output_size = payload.get("output_size")
    pending_url = payload.get("pending_url")
    valid = (
        payload.get("version") == STATE_VERSION
        and isinstance(completed, list)
        and all(isinstance(item, str) and LESSON_URL.fullmatch(item) for item in completed)
        and len(set(completed)) == len(completed)
        and isinstance(output_size, int)
        and not isinstance(output_size, bool)
        and output_size >= 0
        and (pending_url is None or isinstance(pending_url, str))
    )
    if not valid:
        raise ProgressError(f"进度文件格式不正确：{state_file}")
    return CrawlState(completed, output_size, pending_url)


def create_empty_progress(output: Path, state_file: Path) -> CrawlState:
    try:
        with output.open("wb") as file:
            file.flush()
            os.fsync(file.fileno())
    except OSError as error:
        raise ProgressError(f"无法创建输出文件：{error}") from error
    state = CrawlState([], 0)
    save_state(state_file, state)
    return state


def adopt_existing_output(output: Path, state_file: Path, urls: list[str]) -> CrawlState:
    try:
        content = output.read_text(encoding="utf-8")
        output_size = output.stat().st_size
    except (OSError, UnicodeDecodeError) as error:
        raise ProgressError(f"无法接管旧输出文件：{error}") from error

    chapter_count = len(CHAPTER_HEADER.findall(content))
    if chapter_count == 0:
        raise ProgressError("旧输出文件中没有可识别的 Chapter 章节")
    if chapter_count > len(urls):
        raise ProgressError("旧输出文件的章节数超过地址列表，无法安全接管")

    state = CrawlState(urls[:chapter_count], output_size)
    save_state(state_file, state)
    print(f"已接管旧输出：将前 {chapter_count} 个网址标记为已完成")
    return state


def prepare_progress(
    output: Path,
    urls: list[str],
    *,
    restart: bool = False,
    adopt_existing_prefix: bool = False,
) -> tuple[Path, CrawlState]:
    state_file = progress_path_for(output)
    if restart:
        try:
            output.unlink(missing_ok=True)
            state_file.unlink(missing_ok=True)
        except OSError as error:
            raise ProgressError(f"无法清理旧下载文件：{error}") from error

    if state_file.exists():
        if not output.exists():
            raise ProgressError("进度文件存在，但对应的输出 TXT 已不存在")
        state = load_state(state_file)
    elif output.exists():
        if not adopt_existing_prefix:
            raise ProgressError(
                "输出 TXT 已存在但没有进度文件。若它是按当前地址列表连续下载的旧文件，"
                "请增加 --adopt-existing-prefix；若要清空重下，请增加 --restart。"
            )
        state = adopt_existing_output(output, state_file, urls)
    else:
        if adopt_existing_prefix:
            raise ProgressError("没有找到可接管的旧输出 TXT")
        state = create_empty_progress(output, state_file)

    try:
        actual_size = output.stat().st_size
    except OSError as error:
        raise ProgressError(f"无法检查输出文件：{error}") from error

    if state.pending_url is not None:
        if actual_size < state.output_size:
            raise ProgressError("输出 TXT 小于安全进度位置，无法自动恢复")
        try:
            with output.open("r+b") as file:
                file.truncate(state.output_size)
                file.flush()
                os.fsync(file.fileno())
        except OSError as error:
            raise ProgressError(f"无法恢复中断前的输出文件：{error}") from error
        state = replace(state, pending_url=None)
        save_state(state_file, state)
        print("检测到上次写入中断，已回退到最后一个完整章节")
    elif actual_size != state.output_size:
        raise ProgressError(
            "输出 TXT 在脚本外被修改，无法确认断点位置。请改用新的输出文件名，"
            "或确认无需保留后使用 --restart。"
        )

    return state_file, state


def download_urls(
    urls: list[str],
    delay: float,
    output: BinaryIO,
    state_file: Path,
    initial_state: CrawlState,
) -> DownloadSummary:
    downloaded = 0
    skipped = 0
    failed = 0
    pair_count = 0
    state = initial_state
    completed = set(state.completed_urls)

    for position, url in enumerate(urls, start=1):
        if url in completed:
            skipped += 1
            print(f"[{position}/{len(urls)}] 已下载，跳过：{url}")
            continue

        match = LESSON_URL.fullmatch(url)
        if match is None:
            failed += 1
            continue
        course_id, lesson_id = map(int, match.groups())
        try:
            lesson = fetch_lesson(course_id, lesson_id)
        except CrawlError as error:
            failed += 1
            print(f"[{position}/{len(urls)}] 失败：{url}（{error}）")
        else:
            pending_state = replace(state, pending_url=url)
            save_state(state_file, pending_state)
            output_size = write_lesson(output, len(state.completed_urls) + 1, lesson)
            state = CrawlState([*state.completed_urls, url], output_size)
            save_state(state_file, state)
            completed.add(url)
            downloaded += 1
            pair_count += len(lesson.lines)
            print(f"[{position}/{len(urls)}] 已写入：{lesson_id} {lesson.title}")

        if position < len(urls):
            time.sleep(delay)

    return DownloadSummary(downloaded, skipped, failed, pair_count, state)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从地址列表批量抓取可可英语中英内容，生成一个可断点续传的 TXT 文件"
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
    start_mode = parser.add_mutually_exclusive_group()
    start_mode.add_argument(
        "--restart",
        action="store_true",
        help="删除同名输出和进度，从头重新下载",
    )
    start_mode.add_argument(
        "--adopt-existing-prefix",
        action="store_true",
        help="接管旧 TXT，并确认其中章节对应地址列表开头的连续网址",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.delay < 0.2:
            raise CrawlError("请求间隔不能小于 0.2 秒")
        urls = read_urls(args.list_file)
        output_name = normalize_output_name(args.output_name)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / output_name
        state_file, state = prepare_progress(
            output,
            urls,
            restart=args.restart,
            adopt_existing_prefix=args.adopt_existing_prefix,
        )
        with output.open("r+b") as output_file:
            output_file.seek(0, os.SEEK_END)
            summary = download_urls(urls, args.delay, output_file, state_file, state)

        if not summary.state.completed_urls:
            raise CrawlError("列表中的网页全部下载失败，已保留进度供下次重试")

        print(
            f"本次完成：新下载 {summary.downloaded} 页，跳过 {summary.skipped} 页，"
            f"失败 {summary.failed} 页，新增 {summary.pair_count} 组中英对照"
        )
        print(f"累计完成：{len(summary.state.completed_urls)} / {len(urls)} 页")
        print(f"文件：{output.resolve()}")
        print(f"进度：{state_file.resolve()}")
        return 0
    except CrawlError as error:
        print(f"下载失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
