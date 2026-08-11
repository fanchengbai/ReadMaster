from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.helpers import create_minimal_epub

SAMPLE_BOOK = b"""CHAPTER 1 Beginning

Reading is a conversation with another mind.

CHAPTER 2 Practice

Practice turns recognition into understanding.
"""


def create_test_client(data_dir: Path) -> TestClient:
    settings = Settings(data_dir=data_dir)
    app = create_app(settings, database_url="sqlite+pysqlite:///:memory:")
    return TestClient(app)


def test_import_list_and_read_book(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        import_response = client.post(
            "/api/v1/books/import",
            files={"file": ("sample.txt", SAMPLE_BOOK, "text/plain")},
            data={"title": "Reading Sample", "author": "ReadMaster"},
        )

        assert import_response.status_code == 201
        imported = import_response.json()
        assert imported["title"] == "Reading Sample"
        assert imported["author"] == "ReadMaster"
        assert imported["chapter_count"] == 2
        assert [chapter["title"] for chapter in imported["chapters"]] == [
            "CHAPTER 1 Beginning",
            "CHAPTER 2 Practice",
        ]

        books_response = client.get("/api/v1/books")
        assert books_response.status_code == 200
        assert books_response.json()[0]["source_filename"] == "sample.txt"

        chapter_id = imported["chapters"][0]["id"]
        chapter_response = client.get(f"/api/v1/chapters/{chapter_id}")
        assert chapter_response.status_code == 200
        assert chapter_response.json()["paragraphs"][0]["content"] == (
            "Reading is a conversation with another mind."
        )

    stored_books = list((tmp_path / "books").glob("*.txt"))
    assert len(stored_books) == 1
    assert stored_books[0].read_text(encoding="utf-8").startswith("CHAPTER 1")


def test_import_epub_uses_embedded_metadata_and_navigation(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/v1/books/import",
            files={
                "file": (
                    "learning.epub",
                    create_minimal_epub(),
                    "application/epub+zip",
                )
            },
        )

        assert response.status_code == 201
        imported = response.json()
        assert imported["title"] == "Learning Through Reading"
        assert imported["author"] == "Jane Reader"
        assert imported["format"] == "EPUB"
        assert imported["chapter_count"] == 2
        assert imported["chapters"][0]["title"] == "A New Beginning"

    stored_books = list((tmp_path / "books").glob("*.epub"))
    assert len(stored_books) == 1
    assert stored_books[0].read_bytes().startswith(b"PK")


def test_duplicate_book_returns_conflict(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        first_response = client.post(
            "/api/v1/books/import",
            files={"file": ("sample.txt", SAMPLE_BOOK, "text/plain")},
        )
        duplicate_response = client.post(
            "/api/v1/books/import",
            files={"file": ("another-name.txt", SAMPLE_BOOK, "text/plain")},
        )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "BOOK_ALREADY_EXISTS"


def test_import_rejects_non_txt_file(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.post(
            "/api/v1/books/import",
            files={"file": ("notes.md", b"English notes", "text/markdown")},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_delete_book_removes_database_records_and_stored_file(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        imported = client.post(
            "/api/v1/books/import",
            files={"file": ("sample.txt", SAMPLE_BOOK, "text/plain")},
        ).json()

        response = client.delete(f"/api/v1/books/{imported['id']}")

        assert response.status_code == 204
        assert client.get("/api/v1/books").json() == []

    assert list((tmp_path / "books").glob("*.txt")) == []
