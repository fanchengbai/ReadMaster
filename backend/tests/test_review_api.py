from datetime import UTC, datetime, timedelta
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
        assert session["due_count"] == 1
        assert session["scheduled_count"] == 0
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
    assert wrong["review_stage"] == 0
    wrong_delay = datetime.fromisoformat(wrong["next_review_at"]) - datetime.fromisoformat(
        wrong["answered_at"]
    )
    assert timedelta(minutes=9) < wrong_delay < timedelta(minutes=11)
    assert correct["is_correct"] is True
    assert correct["review_stage"] == 1
    assert datetime.fromisoformat(correct["next_review_at"]) > datetime.fromisoformat(
        correct["answered_at"]
    ) + timedelta(hours=23)
    assert saved_word["wrong_count"] == 1
    assert saved_word["consecutive_correct"] == 1
    assert stats["total_attempts"] == 2
    assert stats["correct_attempts"] == 1
    assert stats["accuracy"] == 50.0
    assert stats["words_practiced"] == 1
    assert stats["due_count"] == 0
    assert stats["scheduled_count"] == 1


def test_review_session_adds_meaning_choices_when_pool_is_large_enough(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        for word in ["curiosity", "attention", "context", "meaning"]:
            save_word(client, word)

        questions = client.get("/api/v1/review/session").json()["questions"]

    meaning_questions = [item for item in questions if item["type"] == "meaning_choice"]
    assert meaning_questions
    assert all(len(item["options"]) == 4 for item in meaning_questions)


def test_review_session_only_returns_due_words(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        user_word = save_word(client, "curiosity")
        first_session = client.get("/api/v1/review/session").json()
        question = first_session["questions"][0]
        answer = client.post(
            "/api/v1/review/answer",
            json={
                "question_id": user_word["id"],
                "question_type": question["type"],
                "prompt": question["prompt"],
                "answer": "curiosity",
            },
        ).json()
        next_session = client.get("/api/v1/review/session").json()

    assert datetime.fromisoformat(answer["next_review_at"]) > datetime.now(UTC)
    assert next_session["questions"] == []
    assert next_session["due_count"] == 0
    assert next_session["scheduled_count"] == 1
    assert next_session["next_review_at"] == answer["next_review_at"]


def test_five_gate_completion_records_repairs_and_schedules_once(tmp_path: Path) -> None:
    with create_test_client(tmp_path) as client:
        first = save_word(client, "curiosity")
        second = save_word(client, "attention")
        session = client.get("/api/v1/review/session").json()

        assert session["questions"][0]["lemma"]
        assert session["questions"][0]["context"]
        response = client.post(
            "/api/v1/review/complete",
            json={
                "items": [
                    {"question_id": first["id"], "mistake_count": 0},
                    {"question_id": second["id"], "mistake_count": 2},
                ]
            },
        )
        stats = client.get("/api/v1/review/stats").json()
        words = client.get("/api/v1/user-words").json()

    assert response.status_code == 200
    assert response.json()["completed_count"] == 2
    assert response.json()["repaired_count"] == 1
    assert all(item["review_stage"] == 1 for item in words)
    assert all(
        datetime.fromisoformat(item["next_review_at"]) > datetime.now(UTC).replace(tzinfo=None)
        for item in words
    )
    assert stats["total_attempts"] == 3
    assert stats["correct_attempts"] == 2
    assert stats["due_count"] == 0
