import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Word
from app.schemas.vocabulary import Definition, DictionaryEntry
from app.services.ecdict import PROVIDER_NAME, query_ecdict


@dataclass(frozen=True)
class LocalDictionaryItem:
    phonetic: str | None
    definitions: tuple[tuple[str, str], ...]


LOCAL_DICTIONARY: dict[str, LocalDictionaryItem] = {
    "attention": LocalDictionaryItem("/əˈtenʃn/", (("n.", "注意；专注"),)),
    "book": LocalDictionaryItem("/bʊk/", (("n.", "书；书籍"), ("v.", "预订"))),
    "chapter": LocalDictionaryItem("/ˈtʃæptər/", (("n.", "章；篇章"),)),
    "context": LocalDictionaryItem("/ˈkɒntekst/", (("n.", "上下文；语境；背景"),)),
    "conversation": LocalDictionaryItem("/ˌkɒnvəˈseɪʃn/", (("n.", "交谈；对话"),)),
    "curiosity": LocalDictionaryItem("/ˌkjʊəriˈɒsəti/", (("n.", "好奇心；求知欲"),)),
    "definition": LocalDictionaryItem("/ˌdefɪˈnɪʃn/", (("n.", "定义；释义"),)),
    "evidence": LocalDictionaryItem("/ˈevɪdəns/", (("n.", "证据；迹象"),)),
    "expression": LocalDictionaryItem("/ɪkˈspreʃn/", (("n.", "表达；词语；表情"),)),
    "familiar": LocalDictionaryItem("/fəˈmɪliər/", (("adj.", "熟悉的；常见的"),)),
    "interpretation": LocalDictionaryItem("/ɪnˌtɜːprəˈteɪʃn/", (("n.", "解释；理解；诠释"),)),
    "language": LocalDictionaryItem("/ˈlæŋɡwɪdʒ/", (("n.", "语言；表达方式"),)),
    "meaning": LocalDictionaryItem("/ˈmiːnɪŋ/", (("n.", "意思；意义"),)),
    "memory": LocalDictionaryItem("/ˈmeməri/", (("n.", "记忆；记忆力"),)),
    "paragraph": LocalDictionaryItem("/ˈpærəɡrɑːf/", (("n.", "段落"),)),
    "practice": LocalDictionaryItem("/ˈpræktɪs/", (("n.", "练习；实践"), ("v.", "练习；实践"))),
    "reader": LocalDictionaryItem("/ˈriːdər/", (("n.", "读者；阅读器"),)),
    "reading": LocalDictionaryItem("/ˈriːdɪŋ/", (("n.", "阅读；读物"),)),
    "recognition": LocalDictionaryItem("/ˌrekəɡˈnɪʃn/", (("n.", "识别；认出；认可"),)),
    "relationship": LocalDictionaryItem("/rɪˈleɪʃnʃɪp/", (("n.", "关系；联系"),)),
    "sentence": LocalDictionaryItem("/ˈsentəns/", (("n.", "句子"),)),
    "understanding": LocalDictionaryItem("/ˌʌndəˈstændɪŋ/", (("n.", "理解；认识"),)),
    "unfamiliar": LocalDictionaryItem("/ˌʌnfəˈmɪliər/", (("adj.", "不熟悉的；陌生的"),)),
    "vocabulary": LocalDictionaryItem("/vəˈkæbjələri/", (("n.", "词汇；词汇量"),)),
    "word": LocalDictionaryItem("/wɜːd/", (("n.", "单词；话语"),)),
}


def normalize_word(surface_form: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z]+|[^A-Za-z'-]+$", "", surface_form).lower()
    return cleaned[:128]


def lookup_dictionary(
    session: Session,
    surface_form: str,
    dictionary_database_path: Path,
) -> DictionaryEntry:
    lemma = normalize_word(surface_form)
    cached = session.scalar(select(Word).where(Word.lemma == lemma)) if lemma else None
    if cached is not None and cached.definitions:
        definitions = [Definition.model_validate(item) for item in cached.definitions or []]
        return DictionaryEntry(
            lemma=lemma,
            surface_form=surface_form,
            phonetic=cached.phonetic,
            definitions=definitions,
            provider=cached.provider or "local",
            found=bool(definitions),
            saved=cached.user_word is not None,
        )

    ecdict_entry = query_ecdict(dictionary_database_path, lemma)
    if ecdict_entry is not None:
        resolved_cached = session.scalar(
            select(Word).where(Word.lemma == ecdict_entry.lemma)
        )
        return DictionaryEntry(
            lemma=ecdict_entry.lemma,
            surface_form=surface_form,
            phonetic=ecdict_entry.phonetic,
            definitions=ecdict_entry.definitions,
            provider=PROVIDER_NAME,
            found=True,
            saved=(
                (resolved_cached is not None and resolved_cached.user_word is not None)
                or (cached is not None and cached.user_word is not None)
            ),
        )

    item = LOCAL_DICTIONARY.get(lemma)
    definitions = (
        [Definition(part_of_speech=part, meaning=meaning) for part, meaning in item.definitions]
        if item
        else []
    )
    return DictionaryEntry(
        lemma=lemma,
        surface_form=surface_form,
        phonetic=item.phonetic if item else None,
        definitions=definitions,
        provider="local-basic",
        found=item is not None,
        saved=False,
    )


def dictionary_data(
    word: str,
    dictionary_database_path: Path,
) -> tuple[str, str | None, list[dict[str, str]], str]:
    ecdict_entry = query_ecdict(dictionary_database_path, word)
    if ecdict_entry is not None:
        return (
            ecdict_entry.lemma,
            ecdict_entry.phonetic,
            [definition.model_dump() for definition in ecdict_entry.definitions],
            PROVIDER_NAME,
        )

    lemma = normalize_word(word)
    item = LOCAL_DICTIONARY.get(lemma)
    if item is None:
        return lemma, None, [], "local-basic"
    definitions = [
        {"part_of_speech": part, "meaning": meaning} for part, meaning in item.definitions
    ]
    return lemma, item.phonetic, definitions, "local-basic"
