from __future__ import annotations

from collections import Counter
import re
from typing import Any
import unicodedata

from core.models import build_node_id

_PARTY_SIGLAS = {"PL", "PT", "MDB", "UNIÃO", "PP", "PSD", "PSDB", "PSB", "REPUBLICANOS", "PDT"}
_PARTY_NAMES = {"partido liberal", "partido dos trabalhadores", "uniao brasil", "progressistas"}
_PUBLIC_BODY_KEYWORDS = (
    "banco central",
    "policia federal",
    "procuradoria-geral",
    "procuradoria geral",
    "supremo tribunal",
    "stf",
    "pgr",
    "senado",
    "camara",
    "ministério público",
    "ministerio publico",
    "pf",
    "cldf",
)
_ORG_TYPE_KEYWORDS = {
    "banco": "banco",
    "fundo": "fundo",
    "corretora": "corretora",
    "escritorio": "escritorio_advocacia",
    "advocacia": "escritorio_advocacia",
    "instituto": "ong",
    "associacao": "ong",
}
_LOC_ORG_HINTS = (
    "banco",
    "grupo",
    "empresa",
    "operacao",
    "conselho",
    "tribunal",
    "policia",
    "ministerio",
    "secretaria",
    "prefeitura",
    "governo",
    "universidade",
    "fundacao",
    "assembleia",
    "camara",
    "senado",
)
_EVENT_ACTION_KEYWORDS = (
    "admit",
    "pedido",
    "pediu",
    "negoci",
    "cobrou",
    "cobrando",
    "libera",
    "liquid",
    "prend",
    "acus",
    "investig",
    "grav",
    "video-manifesto",
    "manifesto",
    "elabor",
    "divulg",
    "public",
    "assin",
    "anunci",
    "acordo",
    "compra",
    "venda",
    "aporte",
    "custear",
    "financ",
)
_NON_EVENT_PATTERNS = (
    "quem é",
    "quem e",
    "veja trechos",
    "entenda",
    "análise",
    "analise",
    "opinião",
    "opiniao",
    "abre crise",
    "balde de água fria",
    "balde de agua fria",
    "pressiona pré-candidatura",
    "pressiona pre-candidatura",
    "deve pautar eleições",
    "deve pautar eleicoes",
)
_NOISE_PATTERNS = (
    "author,",
    "published",
    "tempo de leitura",
    "role,",
)


def _normalize(value: str) -> str:
    stripped = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(stripped.lower().split())


def _valid_entity_text(text: str) -> bool:
    if not text or "<" in text or ">" in text:
        return False
    if any(marker in text for marker in (".jpg", ".png", "wp-image", "Print-")):
        return False
    return True


def _clean_snippet(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split()).strip(" -\"'“”")


def _split_sentences(text: str) -> list[str]:
    cleaned = _clean_snippet(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\s+-\s+|\n+", cleaned)
    return [part.strip() for part in parts if part and part.strip()]


def _rank_entities(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    people: Counter[str] = Counter()
    orgs: Counter[str] = Counter()
    first_seen: dict[str, str] = {}
    for entity in payload.get("entidades", []):
        text = entity.get("texto")
        label = entity.get("label")
        if not isinstance(text, str) or not _valid_entity_text(text):
            continue
        normalized = _normalize(text)
        if not normalized:
            continue
        first_seen.setdefault(normalized, text.strip())
        if label == "PER":
            people[normalized] += 1
        elif label == "ORG":
            orgs[normalized] += 1
        elif label == "LOC" and _should_keep_loc_entity(text):
            orgs[normalized] += 1
    ranked_people = [first_seen[key] for key, _ in people.most_common(6)]
    ranked_orgs = [first_seen[key] for key, _ in orgs.most_common(8)]
    return ranked_people, ranked_orgs


def _should_keep_loc_entity(name: str) -> bool:
    normalized = _normalize(name)
    if not normalized:
        return False
    if name.upper() in _PARTY_SIGLAS:
        return True
    if any(keyword in normalized for keyword in _PUBLIC_BODY_KEYWORDS):
        return True
    if any(keyword in normalized for keyword in _LOC_ORG_HINTS):
        return True
    return False


def _score_event_candidate(sentence: str, people: list[str], orgs: list[str], article_title: str) -> int:
    cleaned = _clean_snippet(sentence)
    normalized = _normalize(cleaned)
    if len(cleaned) < 32:
        return -100
    if any(pattern in normalized for pattern in _NOISE_PATTERNS):
        return -100
    has_action = any(keyword in normalized for keyword in _EVENT_ACTION_KEYWORDS)
    if not has_action:
        return -100

    score = 0
    score += 8
    if any(marker in normalized for marker in ("nesta ", "neste ", "na quarta", "no fim do ano", "em dezembro", "em novembro")):
        score += 2
    if any(pattern in normalized for pattern in _NON_EVENT_PATTERNS):
        score -= 6
    if normalized == _normalize(article_title):
        score -= 4
    if cleaned.endswith("?"):
        score -= 4
    if len(cleaned) > 220:
        score -= 2

    for person in people:
        normalized_person = _normalize(person)
        if len(normalized_person.split()) >= 2 and normalized_person in normalized:
            score += 3
    for org in orgs:
        normalized_org = _normalize(org)
        if normalized_org in normalized:
            score += 2
    return score


def _best_event_sentence(payload: dict[str, Any], article_title: str, people: list[str], orgs: list[str]) -> str | None:
    candidates: list[str] = []
    for phrase in payload.get("frases_relevantes", []):
        if isinstance(phrase, str):
            candidates.extend(_split_sentences(phrase))
    for field in (payload.get("texto_resumido"), payload.get("texto_limpo"), article_title):
        if isinstance(field, str):
            candidates.extend(_split_sentences(field))

    best_sentence: str | None = None
    best_score = -100
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = _clean_snippet(candidate)
        normalized = _normalize(cleaned)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        score = _score_event_candidate(cleaned, people, orgs, article_title)
        if score > best_score:
            best_score = score
            best_sentence = cleaned
    if best_score < 8:
        return None
    return best_sentence


def _event_name_from_sentence(sentence: str) -> str:
    cleaned = _clean_snippet(sentence).rstrip(".")
    if len(cleaned) <= 140:
        return cleaned
    truncated = cleaned[:140].rsplit(" ", 1)[0].rstrip(",;:")
    return f"{truncated}..."


def _event_type(text: str) -> str:
    lowered = _normalize(text)
    if any(token in lowered for token in ("pris", "mandado", "pf", "opera", "busca e apreens")):
        return "operacao_policial"
    if "cpi" in lowered:
        return "cpi"
    if any(token in lowered for token in ("julg", "stf", "supremo")):
        return "julgamento"
    if "dela" in lowered:
        return "delacao"
    if any(token in lowered for token in ("contrato", "financi", "compra", "venda", "aporte", "acordo")):
        return "contrato"
    return "reuniao"


def _classify_org(name: str) -> str:
    normalized = _normalize(name)
    if name.upper() in _PARTY_SIGLAS or normalized in _PARTY_NAMES:
        return "Partido"
    if any(keyword in normalized for keyword in _PUBLIC_BODY_KEYWORDS):
        return "Orgao"
    return "Organizacao"


def _org_payload(name: str, node_type: str) -> dict[str, Any]:
    if node_type == "Partido":
        sigla = name if name.upper() in _PARTY_SIGLAS and len(name) <= 12 else None
        return {"tipo_no": "Partido", "id": build_node_id("Partido", name), "nome": name, "sigla": sigla}
    if node_type == "Orgao":
        tipo = "policial" if "policia" in _normalize(name) or name.upper() == "PF" else "regulador"
        sigla = name if name.isupper() and len(name) <= 12 else None
        return {"tipo_no": "Orgao", "id": build_node_id("Orgao", name), "nome": name, "sigla": sigla, "tipo": tipo, "descricao": None}
    org_type = "empresa"
    lowered = _normalize(name)
    for keyword, mapped in _ORG_TYPE_KEYWORDS.items():
        if keyword in lowered:
            org_type = mapped
            break
    return {"tipo_no": "Organizacao", "id": build_node_id("Organizacao", name), "nome": name, "tipo": org_type, "cnpj": None, "descricao": None}


def bootstrap_news_payload(payload: dict[str, Any], article_title: str) -> dict[str, Any]:
    people, orgs = _rank_entities(payload)
    source_id = payload["fontes"][0]["id"]
    summary = payload.get("texto_resumido", "")
    event_sentence = _best_event_sentence(payload, article_title, people, orgs)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    event_node: dict[str, Any] | None = None

    if event_sentence:
        event_name = _event_name_from_sentence(event_sentence)
        event_node = {
            "tipo_no": "Evento",
            "id": build_node_id("Evento", event_name),
            "nome": event_name,
            "tipo": _event_type(f"{event_sentence} {summary}"),
            "data_inicio": payload["fontes"][0].get("data"),
            "data_fim": None,
            "descricao": f"Ocorrencia inferida automaticamente da noticia: {event_sentence}",
        }
        nodes.append(event_node)

    for person in people:
        person_node = {
            "tipo_no": "Pessoa",
            "id": build_node_id("Pessoa", person),
            "nome": person,
            "apelido": None,
            "cargo_atual": None,
            "descricao": None,
        }
        if event_node:
            nodes.append(person_node)
            edges.append(
                {
                    "tipo_relacao": "PARTICIPOU_DE",
                    "origem_id": person_node["id"],
                    "destino_id": event_node["id"],
                    "papel": "citado_na_noticia",
                    "fonte_ids": [source_id],
                    "confianca": "investigado",
                }
            )

    for org in orgs:
        node_type = _classify_org(org)
        org_node = _org_payload(org, node_type)
        if event_node:
            nodes.append(org_node)
        if event_node and node_type == "Organizacao":
            edges.append(
                {
                    "tipo_relacao": "ENVOLVIDA_EM",
                    "origem_id": org_node["id"],
                    "destino_id": event_node["id"],
                    "papel": "citada_na_noticia",
                    "fonte_ids": [source_id],
                    "confianca": "investigado",
                }
            )
        elif event_node and node_type == "Partido":
            edges.append(
                {
                    "tipo_relacao": "CITADO_EM",
                    "origem_id": org_node["id"],
                    "destino_id": event_node["id"],
                    "contexto": "citado_na_noticia",
                    "fonte_ids": [source_id],
                    "confianca": "investigado",
                }
            )

    deduped_nodes: dict[str, dict[str, Any]] = {}
    for node in nodes:
        deduped_nodes[node["id"]] = node

    deduped_edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    for edge in edges:
        deduped_edges[(edge["tipo_relacao"], edge["origem_id"], edge["destino_id"])] = edge

    payload["nos"] = list(deduped_nodes.values())
    payload["arestas"] = list(deduped_edges.values())
    status = "concluida" if event_node else "pendente"
    payload["metadata"]["extracao_grafo"] = {"modelo": "heuristica_news", "status": status}
    return payload
