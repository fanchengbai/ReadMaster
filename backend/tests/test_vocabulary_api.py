from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.ecdict_builder import build_ecdict_database

SAMPLE_BOOK = b"""CHAPTER 1 Reading

Reading needs attention and curiosity.
"""


def create_test_client(data_dir: Path) -> TestClient:
    settings = Settings(data_dir=data_dir)
    return TestClient(create_app(settings, database_url="sqlite+pysqlite:///:memory:"))


def install_sample_ecdict(data_dir: Path) -> None:
    dictionary_dir = data_dir / "dictionaries"
    dictionary_dir.mkdir(parents=True)
    source = dictionary_dir / "ecdict.csv"
    source.write_text(
        "word,phonetic,translation,exchange\n"
        'trace,treis,"n. 痕迹\\nv. 追踪",d:traced/p:traced/i:tracing/3:traces\n',
        encoding="utf-8",
    )
    build_ecdict_database(source, dictionary_dir / "ecdict.db")


def test_dictionary_lookup_returns_local_definition(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        response = client.get("/api/v1/dictionary/Curiosity")

    assert response.status_code == 200
    assert response.json()["lemma"] == "curiosity"
    assert response.json()["definitions"][0]["meaning"] == "好奇心；求知欲"
    assert response.json()["saved"] is False


def test_dictionary_lookup_uses_installed_ecdict_and_word_forms(tmp_path: Path) -> None:
    install_sample_ecdict(tmp_path)

    with create_test_client(tmp_path) as client:
        response = client.get("/api/v1/dictionary/Traced")

    assert response.status_code == 200
    assert response.json()["lemma"] == "trace"
    assert response.json()["provider"] == "ecdict"
    assert response.json()["definitions"] == [
        {"part_of_speech": "n.", "meaning": "痕迹"},
        {"part_of_speech": "v.", "meaning": "追踪"},
    ]


def test_save_inflected_word_uses_ecdict_lemma_and_definition(tmp_path: Path) -> None:
    install_sample_ecdict(tmp_path)
    sample_book = b"CHAPTER 1 Evidence\n\nTraced evidence reveals a pattern."

    with create_test_client(tmp_path) as client:
        book = client.post(
            "/api/v1/books/import",
            files={"file": ("evidence.txt", sample_book, "text/plain")},
        ).json()
        chapter = client.get(f"/api/v1/chapters/{book['chapters'][0]['id']}").json()
        paragraph = chapter["paragraphs"][0]
        saved = client.post(
            "/api/v1/user-words",
            json={
                "word": "Traced",
                "book_id": book["id"],
                "chapter_id": chapter["id"],
                "paragraph_id": paragraph["id"],
                "char_start": 0,
                "char_end": len("Traced"),
            },
        )

    assert saved.status_code == 201
    assert saved.json()["lemma"] == "trace"
    assert saved.json()["provider"] == "ecdict"
    assert saved.json()["definitions"][0]["meaning"] == "痕迹"


def test_save_update_list_and_delete_user_word(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        book = client.post(
            "/api/v1/books/import",
            files={"file": ("reading.txt", SAMPLE_BOOK, "text/plain")},
        ).json()
        chapter = client.get(f"/api/v1/chapters/{book['chapters'][0]['id']}").json()
        paragraph = chapter["paragraphs"][0]
        start = paragraph["content"].index("curiosity")

        saved = client.post(
            "/api/v1/user-words",
            json={
                "word": "curiosity",
                "book_id": book["id"],
                "chapter_id": chapter["id"],
                "paragraph_id": paragraph["id"],
                "char_start": start,
                "char_end": start + len("curiosity"),
            },
        )
        assert saved.status_code == 201
        user_word = saved.json()
        assert user_word["lemma"] == "curiosity"
        assert user_word["encounter_count"] == 1
        assert user_word["latest_occurrence"]["context"] == paragraph["content"]

        lookup = client.get("/api/v1/dictionary/curiosity")
        assert lookup.json()["saved"] is True

        saved_again = client.post(
            "/api/v1/user-words",
            json={
                "word": "curiosity",
                "book_id": book["id"],
                "chapter_id": chapter["id"],
                "paragraph_id": paragraph["id"],
                "char_start": start,
                "char_end": start + len("curiosity"),
            },
        )
        assert saved_again.json()["encounter_count"] == 2

        updated = client.patch(
            f"/api/v1/user-words/{user_word['id']}",
            json={"familiarity": "learning", "note": "Remember the context."},
        )
        assert updated.json()["familiarity"] == "learning"
        assert updated.json()["note"] == "Remember the context."

        listed = client.get("/api/v1/user-words?familiarity=learning")
        assert len(listed.json()) == 1

        deleted = client.delete(f"/api/v1/user-words/{user_word['id']}")
        assert deleted.status_code == 204
        assert client.get("/api/v1/user-words").json() == []


def test_save_user_word_rejects_mismatched_position(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        book = client.post(
            "/api/v1/books/import",
            files={"file": ("reading.txt", SAMPLE_BOOK, "text/plain")},
        ).json()
        chapter = client.get(f"/api/v1/chapters/{book['chapters'][0]['id']}").json()
        paragraph = chapter["paragraphs"][0]

        response = client.post(
            "/api/v1/user-words",
            json={
                "word": "curiosity",
                "book_id": book["id"],
                "chapter_id": chapter["id"],
                "paragraph_id": paragraph["id"],
                "char_start": 0,
                "char_end": len("curiosity"),
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "WORD_POSITION_MISMATCH"


def test_deleting_book_keeps_word_context_snapshot(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        book = client.post(
            "/api/v1/books/import",
            files={"file": ("reading.txt", SAMPLE_BOOK, "text/plain")},
        ).json()
        chapter = client.get(f"/api/v1/chapters/{book['chapters'][0]['id']}").json()
        paragraph = chapter["paragraphs"][0]
        start = paragraph["content"].index("curiosity")
        saved = client.post(
            "/api/v1/user-words",
            json={
                "word": "curiosity",
                "book_id": book["id"],
                "chapter_id": chapter["id"],
                "paragraph_id": paragraph["id"],
                "char_start": start,
                "char_end": start + len("curiosity"),
            },
        ).json()

        assert client.delete(f"/api/v1/books/{book['id']}").status_code == 204
        words = client.get("/api/v1/user-words").json()

    assert words[0]["id"] == saved["id"]
    assert words[0]["latest_occurrence"]["book_id"] is None
    assert words[0]["latest_occurrence"]["context"] == paragraph["content"]
    assert words[0]["latest_occurrence"]["source_book_title"] == book["title"]
