from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

import crawl_kekenet_list as crawler
from crawl_kekenet import CrawlError, DialogueLine, Lesson


def lesson_url(lesson_id: int) -> str:
    return f"https://www.kekenet.com/lesson/18772-{lesson_id}"


def make_lesson(lesson_id: int) -> Lesson:
    return Lesson(
        lesson_id,
        f"Lesson {lesson_id}",
        [DialogueLine(f"English {lesson_id}", f"中文 {lesson_id}")],
    )


def run_download(
    output: Path,
    urls: list[str],
    *,
    adopt_existing_prefix: bool = False,
) -> crawler.DownloadSummary:
    state_file, state = crawler.prepare_progress(
        output,
        urls,
        adopt_existing_prefix=adopt_existing_prefix,
    )
    with output.open("r+b") as file:
        file.seek(0, 2)
        return crawler.download_urls(urls, 0, file, state_file, state)


def test_second_run_skips_completed_urls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    urls = [lesson_url(705200), lesson_url(705201)]
    output = tmp_path / "lessons.txt"
    calls: list[int] = []

    def fetch(_course_id: int, lesson_id: int) -> Lesson:
        calls.append(lesson_id)
        return make_lesson(lesson_id)

    monkeypatch.setattr(crawler, "fetch_lesson", fetch)
    first = run_download(output, urls)
    second = run_download(output, urls)

    assert first.downloaded == 2
    assert second.downloaded == 0
    assert second.skipped == 2
    assert calls == [705200, 705201]
    assert output.read_text(encoding="utf-8").count("Chapter ") == 2


def test_failed_url_is_retried_without_repeating_completed_chapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls = [lesson_url(705200), lesson_url(705201)]
    output = tmp_path / "lessons.txt"
    fail_second = True
    calls: list[int] = []

    def fetch(_course_id: int, lesson_id: int) -> Lesson:
        nonlocal fail_second
        calls.append(lesson_id)
        if lesson_id == 705201 and fail_second:
            fail_second = False
            raise CrawlError("temporary failure")
        return make_lesson(lesson_id)

    monkeypatch.setattr(crawler, "fetch_lesson", fetch)
    first = run_download(output, urls)
    second = run_download(output, urls)

    assert first.downloaded == 1
    assert first.failed == 1
    assert second.skipped == 1
    assert second.downloaded == 1
    assert calls == [705200, 705201, 705201]
    content = output.read_text(encoding="utf-8")
    assert content.count("Chapter 1 -") == 1
    assert content.count("Chapter 2 -") == 1


def test_pending_write_is_rolled_back_before_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls = [lesson_url(705200)]
    output = tmp_path / "lessons.txt"
    state_file, state = crawler.prepare_progress(output, urls)
    crawler.save_state(state_file, crawler.replace(state, pending_url=urls[0]))
    output.write_bytes(b"partial chapter")

    monkeypatch.setattr(crawler, "fetch_lesson", lambda _course, lesson: make_lesson(lesson))
    summary = run_download(output, urls)

    assert summary.downloaded == 1
    assert output.read_text(encoding="utf-8").startswith("Chapter 1 - Lesson 705200")
    assert "partial chapter" not in output.read_text(encoding="utf-8")


def test_old_output_requires_explicit_adoption(tmp_path: Path) -> None:
    urls = [lesson_url(705200), lesson_url(705201)]
    output = tmp_path / "legacy.txt"
    output.write_text("Chapter 1 - Existing\n\nEnglish\n\n中文\n\n", encoding="utf-8")

    with pytest.raises(crawler.ProgressError, match="--adopt-existing-prefix"):
        crawler.prepare_progress(output, urls)

    state_file, state = crawler.prepare_progress(
        output,
        urls,
        adopt_existing_prefix=True,
    )
    assert state_file.exists()
    assert state.completed_urls == [urls[0]]
