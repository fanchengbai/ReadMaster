import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Word
from app.schemas.vocabulary import Definition, DictionaryEntry


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


def lookup_dictionary(session: Session, surface_form: str) -> DictionaryEntry:
    lemma = normalize_word(surface_form)
    cached = session.scalar(select(Word).where(Word.lemma == lemma)) if lemma else None
    if cached is not None:
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


def dictionary_data(lemma: str) -> tuple[str | None, list[dict[str, str]], str]:
    item = LOCAL_DICTIONARY.get(lemma)
    if item is None:
        return None, [], "local-basic"
    definitions = [
        {"part_of_speech": part, "meaning": meaning} for part, meaning in item.definitions
    ]
    return item.phonetic, definitions, "local-basic"
