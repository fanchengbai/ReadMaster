import csv
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = {"word", "phonetic", "translation", "exchange"}
FORM_TYPES = {"p", "d", "i", "3", "r", "t", "s"}


@dataclass(frozen=True)
class BuildResult:
    entries: int
    forms: int
    database_size: int


def build_ecdict_database(csv_path: Path, database_path: Path) -> BuildResult:
    if not csv_path.is_file():
        raise FileNotFoundError(f"ECDICT CSV 不存在：{csv_path}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = database_path.with_suffix(f"{database_path.suffix}.building")
    if temporary_path.exists():
        temporary_path.unlink()

    try:
        entries, forms = _build(csv_path, temporary_path)
        os.replace(temporary_path, database_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return BuildResult(entries=entries, forms=forms, database_size=database_path.stat().st_size)


def _build(csv_path: Path, database_path: Path) -> tuple[int, int]:
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            PRAGMA temp_store = MEMORY;

            CREATE TABLE dictionary_entries (
                word TEXT PRIMARY KEY COLLATE NOCASE,
                phonetic TEXT,
                translation TEXT NOT NULL,
                exchange TEXT
            ) WITHOUT ROWID;

            CREATE TABLE word_forms (
                form TEXT PRIMARY KEY COLLATE NOCASE,
                lemma TEXT NOT NULL
            ) WITHOUT ROWID;

            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) WITHOUT ROWID;
            """
        )
        entry_count, form_count = _import_rows(connection, csv_path)
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            (
                ("source", "ECDICT"),
                ("entry_count", str(entry_count)),
                ("form_count", str(form_count)),
                ("schema_version", "1"),
            ),
        )
        connection.execute("ANALYZE")
        connection.commit()
        return entry_count, form_count
    finally:
        connection.close()


def _import_rows(connection: sqlite3.Connection, csv_path: Path) -> tuple[int, int]:
    csv.field_size_limit(10_000_000)
    entries: list[tuple[str, str | None, str, str | None]] = []
    forms: list[tuple[str, str]] = []
    entry_count = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"ECDICT CSV 缺少字段：{', '.join(sorted(missing))}")

        for row in reader:
            word = (row.get("word") or "").strip().casefold()
            translation = (row.get("translation") or "").strip()
            if not word or not translation:
                continue
            exchange = (row.get("exchange") or "").strip() or None
            entries.append(
                (word, (row.get("phonetic") or "").strip() or None, translation, exchange)
            )
            forms.extend(read_word_forms(word, exchange))
            entry_count += 1
            if len(entries) >= 5000:
                _flush(connection, entries, forms)

    _flush(connection, entries, forms)
    stored_entry_count = connection.execute("SELECT COUNT(*) FROM dictionary_entries").fetchone()[0]
    form_count = connection.execute("SELECT COUNT(*) FROM word_forms").fetchone()[0]
    return int(stored_entry_count), int(form_count)


def _flush(
    connection: sqlite3.Connection,
    entries: list[tuple[str, str | None, str, str | None]],
    forms: list[tuple[str, str]],
) -> None:
    if entries:
        connection.executemany(
            """
            INSERT OR REPLACE INTO dictionary_entries(word, phonetic, translation, exchange)
            VALUES (?, ?, ?, ?)
            """,
            entries,
        )
        entries.clear()
    if forms:
        connection.executemany(
            "INSERT OR IGNORE INTO word_forms(form, lemma) VALUES (?, ?)",
            forms,
        )
        forms.clear()


def read_word_forms(word: str, exchange: str | None) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for item in (exchange or "").split("/"):
        kind, separator, value = item.partition(":")
        if separator and value:
            values.append((kind, value.strip().casefold()))

    explicit_lemma = next((value for kind, value in values if kind == "0"), None)
    lemma = explicit_lemma or word
    forms = [(word, lemma)] if explicit_lemma and word != lemma else []
    forms.extend((value, lemma) for kind, value in values if kind in FORM_TYPES and value)
    return forms
