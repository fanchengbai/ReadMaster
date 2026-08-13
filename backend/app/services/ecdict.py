import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.schemas.vocabulary import Definition

PROVIDER_NAME = "ecdict"
TRANSLATION_SEPARATOR = re.compile(r"\\n|\r?\n")
PART_OF_SPEECH = re.compile(r"^([a-z]+(?:\.[a-z]+)*\.)\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class EcdictEntry:
    lemma: str
    phonetic: str | None
    definitions: list[Definition]


def query_ecdict(database_path: Path, word: str) -> EcdictEntry | None:
    if not database_path.is_file():
        return None

    normalized = word.casefold()
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute(
            "SELECT word, phonetic, translation FROM dictionary_entries WHERE word = ?",
            (normalized,),
        ).fetchone()
        if row is None:
            row = connection.execute(
            """
            SELECT entry.word, entry.phonetic, entry.translation
            FROM word_forms AS form
            JOIN dictionary_entries AS entry ON entry.word = form.lemma
            WHERE form.form = ?
            """,
            (normalized,),
        ).fetchone()

    if row is None:
        return None
    lemma, phonetic, translation = row
    definitions = parse_definitions(translation)
    if not definitions:
        return None
    return EcdictEntry(
        lemma=lemma,
        phonetic=phonetic or None,
        definitions=definitions,
    )


def parse_definitions(translation: str | None) -> list[Definition]:
    definitions: list[Definition] = []
    for line in TRANSLATION_SEPARATOR.split(translation or ""):
        cleaned = line.strip()
        if not cleaned:
            continue
        match = PART_OF_SPEECH.match(cleaned)
        if match:
            part_of_speech, meaning = match.groups()
        else:
            part_of_speech, meaning = "释义", cleaned
        definitions.append(Definition(part_of_speech=part_of_speech, meaning=meaning))
    return definitions
