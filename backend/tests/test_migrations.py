from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.db.migrations import run_migrations


def test_migrations_create_current_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"

    run_migrations(database_url)

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        user_word_columns = {column["name"] for column in inspector.get_columns("user_words")}
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
        "review_attempts",
    } <= table_names
    assert {
        "review_stage",
        "consecutive_correct",
        "next_review_at",
        "last_reviewed_at",
    } <= user_word_columns
