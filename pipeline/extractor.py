from __future__ import annotations

import re
from collections import Counter
from typing import Any


KEYWORDS = [
    "fraude",
    "desvio",
    "investigação",
    "preso",
    "prisão",
    "CPI",
    "bilhões",
    "milhões",
    "contrato",
    "esquema",
    "lavagem",
    "corrupção",
    "operação",
    "delação",
    "sigilo",
    "liquidação",
    "rombo",
]


def split_sentences(text: str) -> list[str]:
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", text) if chunk.strip()]
    return sentences or [text.strip()]


def _spacy_entities(text: str) -> list[dict[str, Any]]:
    import spacy

    model = spacy.load("pt_core_news_lg")
    doc = model(text)
    entities = []
    for ent in doc.ents:
        if ent.label_ in {"PER", "ORG", "LOC", "DATE", "MONEY"}:
            entities.append(
                {
                    "texto": ent.text,
                    "label": ent.label_,
                    "inicio": ent.start_char,
                    "fim": ent.end_char,
                }
            )
    return entities


def _regex_entities(text: str) -> list[dict[str, Any]]:
    patterns = {
        "MONEY": r"\b(?:R\$ ?)?\d[\d\.\,]*\s*(?:mil|milhões|bilhões|reais)?\b",
        "DATE": r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(?:19|20)\d{2}\b",
    }
    entities: list[dict[str, Any]] = []
    for label, pattern in patterns.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            entities.append(
                {
                    "texto": match.group(0),
                    "label": label,
                    "inicio": match.start(),
                    "fim": match.end(),
                }
            )
    for match in re.finditer(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ]+\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ]+\b", text):
        entities.append(
            {
                "texto": match.group(0),
                "label": "PER",
                "inicio": match.start(),
                "fim": match.end(),
            }
        )
    return entities


def extract_entities(text: str) -> tuple[list[dict[str, Any]], str]:
    try:
        return _spacy_entities(text), "spacy"
    except Exception:
        return _regex_entities(text), "regex"


def _sumy_rank(text: str, sentence_count: int) -> tuple[list[str], str]:
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.summarizers.text_rank import TextRankSummarizer

    parser = PlaintextParser.from_string(text, Tokenizer("portuguese"))
    summarizer = TextRankSummarizer()
    sentences = [str(sentence).strip() for sentence in summarizer(parser.document, sentence_count)]
    return sentences, "sumy"


def _keyword_rank(text: str, sentence_count: int, entities: list[dict[str, Any]]) -> tuple[list[str], str]:
    sentences = split_sentences(text)
    entity_texts = {entity["texto"] for entity in entities}
    scores: Counter[int] = Counter()
    for index, sentence in enumerate(sentences):
        lowered = sentence.lower()
        keyword_hits = sum(1 for keyword in KEYWORDS if keyword.lower() in lowered)
        entity_hits = sum(1 for entity_text in entity_texts if entity_text and entity_text in sentence)
        scores[index] = keyword_hits * 3 + entity_hits * 2 + min(len(sentence) // 80, 3)
    top_indexes = [index for index, _ in scores.most_common(sentence_count)]
    if not top_indexes:
        top_indexes = list(range(min(sentence_count, len(sentences))))
    ranked = [sentences[index] for index in sorted(top_indexes)]
    return ranked, "keyword"


def summarize_text(text: str, entities: list[dict[str, Any]], sentence_count: int = 10) -> tuple[list[str], str]:
    try:
        return _sumy_rank(text, sentence_count)
    except Exception:
        return _keyword_rank(text, sentence_count, entities)


def expand_sentences(text: str, selected_sentences: list[str]) -> str:
    source_sentences = split_sentences(text)
    selected_indexes = {
        index
        for index, sentence in enumerate(source_sentences)
        if sentence in selected_sentences
    }
    expanded_indexes: set[int] = set()
    for index in selected_indexes:
        expanded_indexes.update({max(index - 1, 0), index, min(index + 1, len(source_sentences) - 1)})
    if not expanded_indexes:
        expanded_indexes = set(range(min(5, len(source_sentences))))
    return " ".join(source_sentences[index] for index in sorted(expanded_indexes))


def extract_insights(text: str) -> dict[str, Any]:
    entities, entity_method = extract_entities(text)
    selected_sentences, summary_method = summarize_text(text, entities)
    return {
        "entidades": entities,
        "texto_resumido": expand_sentences(text, selected_sentences),
        "frases_relevantes": selected_sentences,
        "metodos": {"entidades": entity_method, "resumo": summary_method},
    }
