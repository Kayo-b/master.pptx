from __future__ import annotations

import json
import re
import unicodedata
import uuid
from copy import deepcopy
from typing import Any

from core.schema import CONFIDENCE_VALUES, NODE_ID_PREFIXES, NODE_SCHEMAS, RELATION_SCHEMAS, SOURCE_TYPES


class ValidationError(ValueError):
    pass


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_value).strip("_")
    if not slug:
        raise ValidationError("Nao foi possivel gerar slug a partir do valor informado.")
    return slug


def build_node_id(node_type: str, raw_name: str) -> str:
    prefix = NODE_ID_PREFIXES[node_type]
    return f"{prefix}_{slugify(raw_name)}"


def new_source_id() -> str:
    return str(uuid.uuid4())


def _clean_optional_strings(data: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            stripped = value.strip()
            cleaned[key] = stripped if stripped else None
        else:
            cleaned[key] = value
    return cleaned


def _node_id_basis(node_type: str, node: dict[str, Any]) -> str:
    for key in ("nome", "descricao", "sigla", "tipo"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValidationError(f"Nao foi possivel derivar id para no do tipo {node_type}.")


def validate_source(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValidationError("Fonte invalida: esperado objeto.")
    normalized = _clean_optional_strings(deepcopy(source))
    if not normalized.get("url"):
        raise ValidationError("Fonte invalida: campo 'url' e obrigatorio.")
    if normalized.get("tipo") and normalized["tipo"] not in SOURCE_TYPES:
        raise ValidationError(f"Tipo de fonte invalido: {normalized['tipo']}.")
    normalized["id"] = normalized.get("id") or new_source_id()
    return {
        "id": normalized["id"],
        "url": normalized["url"],
        "titulo": normalized.get("titulo"),
        "autor": normalized.get("autor"),
        "veiculo": normalized.get("veiculo"),
        "data": normalized.get("data"),
        "tipo": normalized.get("tipo"),
    }


def _validate_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError(f"Campo '{field_name}' deve ser uma lista de strings.")
    return [item.strip() for item in value if item.strip()]


def validate_wikipedia_linked_reference(reference: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise ValidationError("Referencia vinculada da Wikipedia invalida: esperado objeto.")
    normalized = _clean_optional_strings(deepcopy(reference))
    if not normalized.get("trecho_artigo"):
        raise ValidationError("Referencia vinculada da Wikipedia sem 'trecho_artigo'.")
    if not normalized.get("numero_nota"):
        raise ValidationError("Referencia vinculada da Wikipedia sem 'numero_nota'.")
    source = validate_source(normalized.get("referencia_correspondente"))
    claim = normalized.get("claim_estruturada")
    if not isinstance(claim, dict):
        raise ValidationError("Referencia vinculada da Wikipedia sem 'claim_estruturada' valida.")
    claim_text = claim.get("texto")
    if not isinstance(claim_text, str) or not claim_text.strip():
        raise ValidationError("Claim estruturada da Wikipedia sem campo 'texto'.")
    return {
        "trecho_artigo": normalized["trecho_artigo"],
        "numero_nota": str(normalized["numero_nota"]),
        "fonte_sugerida_id": normalized.get("fonte_sugerida_id") or source["id"],
        "referencia_correspondente": source,
        "claim_estruturada": {
            "texto": claim_text.strip(),
            "tipo": claim.get("tipo") or "citacao",
            "entidades_mencionadas": _validate_string_list(claim.get("entidades_mencionadas"), "claim_estruturada.entidades_mencionadas"),
            "valores_mencionados": _validate_string_list(claim.get("valores_mencionados"), "claim_estruturada.valores_mencionados"),
            "datas_mencionadas": _validate_string_list(claim.get("datas_mencionadas"), "claim_estruturada.datas_mencionadas"),
        },
    }


def validate_node(node: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(node, dict):
        raise ValidationError("No invalido: esperado objeto.")
    normalized = _clean_optional_strings(deepcopy(node))
    node_type = normalized.get("tipo_no") or normalized.get("tipo")
    if node_type not in NODE_SCHEMAS:
        raise ValidationError(f"Tipo de no invalido: {node_type}.")
    schema = NODE_SCHEMAS[node_type]
    if "tipo" in schema.fields and normalized.get("tipo_no") is None and normalized.get("tipo") == node_type and normalized.get("subtipo"):
        normalized["tipo"] = normalized["subtipo"]
    unknown = set(normalized) - (set(schema.fields) | {"tipo", "tipo_no", "subtipo"})
    if unknown:
        raise ValidationError(f"Campos inesperados no no {node_type}: {', '.join(sorted(unknown))}.")
    for field in schema.required:
        if not normalized.get(field):
            raise ValidationError(f"No {node_type} sem campo obrigatorio '{field}'.")
    for field, accepted in schema.enum_fields.items():
        value = normalized.get(field)
        if value and value not in accepted:
            raise ValidationError(f"Valor invalido para {node_type}.{field}: {value}.")
    normalized["id"] = normalized.get("id") or build_node_id(node_type, _node_id_basis(node_type, normalized))
    return {"tipo_no": node_type, **{field: normalized.get(field) for field in schema.fields}}


def validate_edge(edge: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(edge, dict):
        raise ValidationError("Aresta invalida: esperado objeto.")
    normalized = _clean_optional_strings(deepcopy(edge))
    edge_type = normalized.get("tipo_relacao") or normalized.get("tipo")
    if edge_type not in RELATION_SCHEMAS:
        raise ValidationError(f"Tipo de aresta invalido: {edge_type}.")
    schema = RELATION_SCHEMAS[edge_type]
    if "tipo" in schema.fields and normalized.get("tipo_relacao") is None and normalized.get("tipo") == edge_type and normalized.get("subtipo"):
        normalized["tipo"] = normalized["subtipo"]
    allowed = {"tipo", "tipo_relacao", "subtipo", "origem_id", "destino_id", *schema.fields}
    unknown = set(normalized) - allowed
    if unknown:
        raise ValidationError(f"Campos inesperados na aresta {edge_type}: {', '.join(sorted(unknown))}.")
    for field in ("origem_id", "destino_id", "confianca", "fonte_ids"):
        if field not in normalized or normalized[field] in (None, "", []):
            raise ValidationError(f"Aresta {edge_type} sem campo obrigatorio '{field}'.")
    if normalized["confianca"] not in CONFIDENCE_VALUES:
        raise ValidationError(f"Confianca invalida: {normalized['confianca']}.")
    if not isinstance(normalized["fonte_ids"], list) or not all(isinstance(item, str) and item.strip() for item in normalized["fonte_ids"]):
        raise ValidationError("Campo 'fonte_ids' deve ser uma lista nao vazia de strings.")
    payload = {field: normalized.get(field) for field in schema.fields if field in normalized}
    payload["fonte_ids"] = [item.strip() for item in normalized["fonte_ids"]]
    payload["confianca"] = normalized["confianca"]
    return {
        "tipo_relacao": edge_type,
        "origem_id": normalized["origem_id"],
        "destino_id": normalized["destino_id"],
        **payload,
    }


def validate_staging_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Payload de staging invalido: esperado objeto.")
    normalized = deepcopy(payload)
    normalized.setdefault("metadata", {})
    normalized.setdefault("texto_limpo", "")
    normalized.setdefault("texto_resumido", "")
    normalized.setdefault("entidades", [])
    normalized.setdefault("nos", [])
    normalized.setdefault("arestas", [])
    normalized.setdefault("fontes", [])
    normalized.setdefault("fontes_sugeridas", [])
    normalized.setdefault("referencias_wikipedia_vinculadas", [])
    if not isinstance(normalized["entidades"], list):
        raise ValidationError("Campo 'entidades' deve ser lista.")
    normalized["nos"] = [validate_node(node) for node in normalized["nos"]]
    normalized["arestas"] = [validate_edge(edge) for edge in normalized["arestas"]]
    normalized["fontes"] = [validate_source(source) for source in normalized["fontes"]]
    normalized["fontes_sugeridas"] = [validate_source(source) for source in normalized["fontes_sugeridas"]]
    normalized["referencias_wikipedia_vinculadas"] = [
        validate_wikipedia_linked_reference(reference)
        for reference in normalized["referencias_wikipedia_vinculadas"]
    ]
    node_ids = {node["id"] for node in normalized["nos"]}
    node_types = {node["id"]: node["tipo_no"] for node in normalized["nos"]}
    for edge in normalized["arestas"]:
        if edge["origem_id"] not in node_ids:
            raise ValidationError(f"Aresta {edge['tipo_relacao']} referencia origem inexistente: {edge['origem_id']}.")
        if edge["destino_id"] not in node_ids:
            raise ValidationError(f"Aresta {edge['tipo_relacao']} referencia destino inexistente: {edge['destino_id']}.")
        relation_schema = RELATION_SCHEMAS[edge["tipo_relacao"]]
        if node_types[edge["origem_id"]] != relation_schema.source_type:
            raise ValidationError(
                f"Aresta {edge['tipo_relacao']} exige origem {relation_schema.source_type}, "
                f"mas recebeu {node_types[edge['origem_id']]}."
            )
        if node_types[edge["destino_id"]] != relation_schema.target_type:
            raise ValidationError(
                f"Aresta {edge['tipo_relacao']} exige destino {relation_schema.target_type}, "
                f"mas recebeu {node_types[edge['destino_id']]}."
            )
    return normalized


def source_ids_from_payload(payload: dict[str, Any]) -> set[str]:
    ids = {source["id"] for source in payload.get("fontes", [])}
    for edge in payload.get("arestas", []):
        ids.update(edge["fonte_ids"])
    return ids


def dumps_pretty(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
