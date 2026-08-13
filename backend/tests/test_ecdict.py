import csv
import sqlite3
from pathlib import Path

from app.services.ecdict import query_ecdict
from app.services.ecdict_builder import build_ecdict_database, read_word_forms


def write_sample_ecdict(path: Path) -> None:
    fieldnames = ["word", "phonetic", "translation", "exchange"]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "word": "trace",
                "phonetic": "treis",
                "translation": "n. 痕迹\\nv. 追踪",
                "exchange": "d:traced/p:traced/i:tracing/3:traces",
            }
        )


def test_build_and_query_ecdict_database(tmp_path: Path) -> None:
    csv_path = tmp_path / "ecdict.csv"
    database_path = tmp_path / "ecdict.db"
    write_sample_ecdict(csv_path)

    result = build_ecdict_database(csv_path, database_path)
    exact = query_ecdict(database_path, "trace")
    inflected = query_ecdict(database_path, "Traced")

    assert result.entries == 1
    assert result.forms == 3
    assert exact is not None
    assert exact.lemma == "trace"
    assert [item.part_of_speech for item in exact.definitions] == ["n.", "v."]
    assert inflected is not None
    assert inflected.lemma == "trace"
    assert inflected.definitions[0].meaning == "痕迹"
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT value FROM metadata WHERE key = 'source'"
        ).fetchone() == ("ECDICT",)


def test_build_replaces_existing_database_atomically(tmp_path: Path) -> None:
    csv_path = tmp_path / "ecdict.csv"
    database_path = tmp_path / "ecdict.db"
    database_path.write_text("old", encoding="utf-8")
    write_sample_ecdict(csv_path)

    build_ecdict_database(csv_path, database_path)

    assert query_ecdict(database_path, "trace") is not None


def test_read_word_forms_uses_explicit_lemma() -> None:
    assert read_word_forms("gave", "0:give/1:p") == [("gave", "give")]
