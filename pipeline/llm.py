from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.config import ANTHROPIC_API_KEY, ANTHROPIC_API_URL, ANTHROPIC_MODEL
from core.models import ValidationError, validate_edge, validate_node, validate_source
from core.schema import CONFIDENCE_VALUES, NODE_SCHEMAS, RELATION_SCHEMAS

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", flags=re.DOTALL)


def _compact_text(value: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", value or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _primary_source_id(source: str) -> str:
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]
    return f"fonte_ingest_{digest}"


def _build_primary_source(source: str, source_kind: str) -> dict[str, Any]:
    url = source if source_kind == "url" else f"file://{source}"
    title = source.rsplit("/", 1)[-1] if source_kind == "file" else source
    return validate_source(
        {
            "id": _primary_source_id(source),
            "url": url,
            "titulo": title,
            "tipo": "artigo",
        }
    )


def _build_candidate_sources(
    origin_source: str,
    source_kind: str,
    linked_references: list[dict[str, Any]],
    suggested_sources: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates: dict[str, dict[str, Any]] = {}
    evidence_by_source: dict[str, list[str]] = {}

    primary_source = _build_primary_source(origin_source, source_kind)
    candidates[primary_source["id"]] = primary_source
    evidence_by_source[primary_source["id"]] = ["Fonte principal do texto ingerido."]

    for source in suggested_sources:
        normalized_source = validate_source(source)
        candidates[normalized_source["id"]] = normalized_source
        evidence_by_source.setdefault(normalized_source["id"], [])

    for reference in linked_references:
        normalized_source = validate_source(reference["referencia_correspondente"])
        candidates[normalized_source["id"]] = normalized_source
        evidence_by_source.setdefault(normalized_source["id"], []).append(reference["claim_estruturada"]["texto"])

    scored = []
    for source_id, source in candidates.items():
        evidences = evidence_by_source.get(source_id, [])
        relevance_text = " ".join([source.get("titulo") or "", source.get("url") or "", *evidences]).lower()
        score = sum(token in relevance_text for token in ("master", "vorcaro", "compliance", "brb", "banco central"))
        score += min(len(evidences), 5)
        scored.append(
            {
                **source,
                "evidencias": [_compact_text(item, 260) for item in evidences[:3]],
                "_score": score,
            }
        )
    scored.sort(key=lambda item: (item["_score"], item.get("titulo") or item["url"]), reverse=True)
    ranked = [{key: value for key, value in item.items() if key != "_score"} for item in scored[:60]]
    by_id = {source_id: dict(source) for source_id, source in candidates.items()}
    ranked_ids = {item["id"] for item in ranked}
    if primary_source["id"] not in ranked_ids:
        ranked.insert(0, {**primary_source, "evidencias": evidence_by_source[primary_source["id"]]})
        by_id[primary_source["id"]] = dict(primary_source)
    return ranked, by_id


def _relation_catalog() -> list[dict[str, Any]]:
    relations = []
    for relation_type, schema in RELATION_SCHEMAS.items():
        extra_fields = [field for field in schema.fields if field not in {"fonte_ids", "confianca"}]
        relations.append(
            {
                "tipo_relacao": relation_type,
                "origem": schema.source_type,
                "destino": schema.target_type,
                "campos_extras": extra_fields,
            }
        )
    return relations


def _node_catalog() -> list[dict[str, Any]]:
    nodes = []
    for node_type, schema in NODE_SCHEMAS.items():
        nodes.append(
            {
                "tipo_no": node_type,
                "campos": list(schema.fields),
                "obrigatorios": list(schema.required),
                "enum": schema.enum_fields,
            }
        )
    return nodes


def _build_prompt(
    source: str,
    summary_text: str,
    entities: list[dict[str, Any]],
    candidate_sources: list[dict[str, Any]],
) -> str:
    payload = {
        "origem": source,
        "texto_resumido": _compact_text(summary_text, 9000),
        "entidades_detectadas": entities[:80],
        "fontes_candidatas": candidate_sources,
        "tipos_de_no": _node_catalog(),
        "tipos_de_aresta": _relation_catalog(),
        "confiancas_validas": list(CONFIDENCE_VALUES),
    }
    instructions = """
Você é um extrator estruturado para um grafo investigativo em português.
Responda SOMENTE com JSON válido, sem markdown e sem texto extra.

Objetivo:
- extrair nós e arestas sustentados pelo texto resumido;
- preencher cada aresta com pelo menos um `fonte_id` vindo EXCLUSIVAMENTE de `fontes_candidatas`;
- priorizar conexões ligadas ao caso Master/Vorcaro, mas também manter subgrafos desconectados se forem claramente mencionados no texto;
- não inventar fatos, datas, valores ou relações não apoiadas pelo texto/evidências.

Regras obrigatórias:
- saída com formato `{ "nos": [...], "arestas": [...] }`;
- cada nó deve usar `tipo_no` e campos compatíveis com seu schema;
- cada aresta deve usar `tipo_relacao`, `origem_id`, `destino_id`, `confianca` e `fonte_ids`;
- use ids estáveis em snake_case, por exemplo `pessoa_daniel_vorcaro` e `org_banco_master`;
- não crie arestas sem evidência suficiente;
- se houver múltiplas fontes candidatas aplicáveis, associe mais de uma;
- não inclua `fontes`, `fontes_sugeridas` ou chaves fora do schema.
""".strip()
    return f"{instructions}\n\nDADOS:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


def _extract_json_payload(text: str) -> dict[str, Any]:
    fenced_match = _JSON_BLOCK_RE.search(text)
    candidate = fenced_match.group(1) if fenced_match else text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM retornou JSON inválido: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM retornou payload inválido: esperado objeto JSON.")
    return parsed


def _anthropic_request(prompt: str) -> dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY ausente. Configure a chave do Anthropic para usar a extração automática.")
    request_body = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 4096,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Falha ao chamar Anthropic: HTTP {exc.code} - {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Falha de rede ao chamar Anthropic: {exc.reason}") from exc


def _read_anthropic_text(response_payload: dict[str, Any]) -> str:
    content = response_payload.get("content")
    if not isinstance(content, list):
        raise RuntimeError("Resposta do Anthropic sem bloco de conteúdo.")
    parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
    text = "\n".join(part for part in parts if part.strip()).strip()
    if not text:
        raise RuntimeError("Resposta do Anthropic não contém texto utilizável.")
    return text


def _node_aliases(node: dict[str, Any]) -> list[str]:
    aliases = [node["id"]]
    for key in ("nome", "sigla", "descricao", "tipo"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            aliases.append(value.strip().lower())
    return aliases


def _resolve_node_ref(raw_value: Any, aliases: dict[str, str], field_name: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise RuntimeError(f"LLM não preencheu '{field_name}' de forma válida.")
    normalized = raw_value.strip()
    if normalized in aliases:
        return aliases[normalized]
    lowered = normalized.lower()
    if lowered in aliases:
        return aliases[lowered]
    raise RuntimeError(f"LLM referenciou nó desconhecido em '{field_name}': {raw_value}")


def _normalize_nodes(raw_nodes: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_nodes, list):
        raise RuntimeError("LLM retornou 'nos' fora do formato de lista.")
    try:
        validated_nodes = [validate_node(node) for node in raw_nodes]
    except ValidationError as exc:
        raise RuntimeError(f"Nó inválido gerado pelo LLM: {exc}") from exc
    deduped: dict[str, dict[str, Any]] = {}
    for node in validated_nodes:
        current = deduped.get(node["id"], {})
        deduped[node["id"]] = {**current, **{key: value for key, value in node.items() if value not in (None, "", [])}}
    return list(deduped.values())


def _normalize_edges(raw_edges: Any, aliases: dict[str, str], candidate_source_ids: set[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_edges, list):
        raise RuntimeError("LLM retornou 'arestas' fora do formato de lista.")
    normalized_edges = []
    seen_edges: set[str] = set()
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            raise RuntimeError("LLM retornou aresta inválida: esperado objeto.")
        edge = dict(raw_edge)
        if "tipo_relacao" not in edge and "tipo" in edge:
            edge["tipo_relacao"] = edge["tipo"]
        if "origem_id" not in edge:
            edge["origem_id"] = _resolve_node_ref(edge.get("origem") or edge.get("origem_nome"), aliases, "origem_id")
        else:
            edge["origem_id"] = _resolve_node_ref(edge["origem_id"], aliases, "origem_id")
        if "destino_id" not in edge:
            edge["destino_id"] = _resolve_node_ref(edge.get("destino") or edge.get("destino_nome"), aliases, "destino_id")
        else:
            edge["destino_id"] = _resolve_node_ref(edge["destino_id"], aliases, "destino_id")
        edge.pop("origem", None)
        edge.pop("origem_nome", None)
        edge.pop("destino", None)
        edge.pop("destino_nome", None)
        fonte_ids = edge.get("fonte_ids")
        if not isinstance(fonte_ids, list) or not fonte_ids:
            raise RuntimeError(f"LLM gerou aresta sem 'fonte_ids': {edge.get('tipo_relacao')}")
        invalid_source_ids = [source_id for source_id in fonte_ids if source_id not in candidate_source_ids]
        if invalid_source_ids:
            raise RuntimeError(
                f"LLM referenciou fontes inexistentes na aresta {edge.get('tipo_relacao')}: {', '.join(invalid_source_ids)}"
            )
        try:
            normalized_edge = validate_edge(edge)
        except ValidationError as exc:
            raise RuntimeError(f"Aresta inválida gerada pelo LLM: {exc}") from exc
        dedupe_key = json.dumps(normalized_edge, ensure_ascii=False, sort_keys=True)
        if dedupe_key in seen_edges:
            continue
        seen_edges.add(dedupe_key)
        normalized_edges.append(normalized_edge)
    return normalized_edges


def extract_graph_with_llm(
    source: str,
    source_kind: str,
    summary_text: str,
    entities: list[dict[str, Any]],
    linked_references: list[dict[str, Any]],
    suggested_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_sources, candidate_sources_by_id = _build_candidate_sources(
        source,
        source_kind,
        linked_references,
        suggested_sources,
    )
    prompt = _build_prompt(source, summary_text, entities, candidate_sources)
    raw_response = _anthropic_request(prompt)
    parsed = _extract_json_payload(_read_anthropic_text(raw_response))

    nodes = _normalize_nodes(parsed.get("nos", []))
    aliases: dict[str, str] = {}
    for node in nodes:
        for alias in _node_aliases(node):
            aliases[alias] = node["id"]
    edges = _normalize_edges(parsed.get("arestas", []), aliases, set(candidate_sources_by_id))
    selected_source_ids = sorted({source_id for edge in edges for source_id in edge["fonte_ids"]})
    selected_sources = [candidate_sources_by_id[source_id] for source_id in selected_source_ids]
    return {
        "nos": nodes,
        "arestas": edges,
        "fontes": selected_sources,
    }
