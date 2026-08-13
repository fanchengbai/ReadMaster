from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

SAMPLE_BOOK = b"""CHAPTER 1 Learning

Curiosity gives attention to context and meaning during reading practice.
"""


def create_test_client(data_dir: Path) -> TestClient:
    settings = Settings(data_dir=data_dir)
    return TestClient(create_app(settings, database_url="sqlite+pysqlite:///:memory:"))


def save_word(client: TestClient, word: str) -> dict:
    books = client.get("/api/v1/books").json()
    if books:
        book = client.get(f"/api/v1/books/{books[0]['id']}").json()
    else:
        book = client.post(
            "/api/v1/books/import",
            files={"file": ("learning.txt", SAMPLE_BOOK, "text/plain")},
        ).json()
    chapter = client.get(f"/api/v1/chapters/{book['chapters'][0]['id']}").json()
    paragraph = chapter["paragraphs"][0]
    start = paragraph["content"].lower().index(word)
    return client.post(
        "/api/v1/user-words",
        json={
            "word": word,
            "book_id": book["id"],
            "chapter_id": chapter["id"],
            "paragraph_id": paragraph["id"],
            "char_start": start,
            "char_end": start + len(word),
        },
    ).json()


def test_review_session_masks_context_and_records_answers(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        user_word = save_word(client, "curiosity")

        session = client.get("/api/v1/review/session").json()
        question = session["questions"][0]

        assert session["total_available"] == 1
        assert question["type"] == "context_fill"
        assert "_____" in question["prompt"]
        assert "Curiosity" not in question["prompt"]

        wrong = client.post(
            "/api/v1/review/answer",
            json={
                "question_id": user_word["id"],
                "question_type": question["type"],
                "prompt": question["prompt"],
                "answer": "attention",
            },
        ).json()
        correct = client.post(
            "/api/v1/review/answer",
            json={
                "question_id": user_word["id"],
                "question_type": question["type"],
                "prompt": question["prompt"],
                "answer": "Curiosity",
            },
        ).json()
        stats = client.get("/api/v1/review/stats").json()
        saved_word = client.get("/api/v1/user-words").json()[0]

    assert wrong["is_correct"] is False
    assert wrong["correct_answer"] == "curiosity"
    assert correct["is_correct"] is True
    assert saved_word["wrong_count"] == 1
    assert stats == {
        "total_attempts": 2,
        "correct_attempts": 1,
        "accuracy": 50.0,
        "words_practiced": 1,
    }


def test_review_session_adds_meaning_choices_when_pool_is_large_enough(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        for word in ["curiosity", "attention", "context", "meaning"]:
            save_word(client, word)

        questions = client.get("/api/v1/review/session").json()["questions"]

    meaning_questions = [item for item in questions if item["type"] == "meaning_choice"]
    assert meaning_questions
    assert all(len(item["options"]) == 4 for item in meaning_questions)
