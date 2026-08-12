from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.migrations import run_migrations


def test_migrations_create_current_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    run_migrations(database_url)

    engine = create_engine(database_url)
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert {
        "alembic_version",
        "books",
        "chapters",
        "paragraphs",
        "reading_progress",
        "words",
        "user_words",
        "word_occurrences",
    } <= table_names
