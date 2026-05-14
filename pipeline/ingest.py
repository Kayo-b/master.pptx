from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.config import STAGING_DIR, next_staging_path
from core.models import dumps_pretty, validate_staging_payload
from pipeline.cleaner import clean_input
from pipeline.extractor import extract_insights
from pipeline.images import extract_image_suggestions
from pipeline.llm import build_primary_source
from pipeline.wikipedia import extract_wikipedia_evidence


def _is_wikipedia_url(url: str | None) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return "wikipedia.org" in host


def build_staging_document(url: str | None = None, file_path: str | None = None) -> dict[str, Any]:
    cleaned = clean_input(url=url, file_path=file_path)
    insights = extract_insights(cleaned.text)
    wikipedia_evidence = extract_wikipedia_evidence(url) if _is_wikipedia_url(url) else {}
    sources_suggested = wikipedia_evidence.get("fontes_sugeridas", [])
    linked_references = wikipedia_evidence.get("referencias_vinculadas", [])
    image_data = extract_image_suggestions(
        source=cleaned.source,
        source_kind=cleaned.source_kind,
        raw_html=getattr(cleaned, "raw_html", None),
        entities=insights["entidades"],
    )
    primary_source = build_primary_source(cleaned.source, cleaned.source_kind)
    payload = {
        "metadata": {
            "origem": cleaned.source,
            "tipo_origem": cleaned.source_kind,
            "referencias_wikipedia_extraidas": len(sources_suggested),
            "referencias_wikipedia_vinculadas": len(linked_references),
            "metodos_extracao": insights.get("metodos", {}),
            "imagens_sugeridas": image_data["imagens_sugeridas"],
            "imagens_erros": image_data["erros"],
            "imagens_extraidas": len(image_data["imagens_sugeridas"]),
            "extracao_grafo": {
                "modelo": "manual_via_copilot_cli",
                "status": "pendente",
            },
        },
        "texto_limpo": cleaned.text,
        "texto_resumido": insights["texto_resumido"],
        "entidades": insights["entidades"],
        "frases_relevantes": insights["frases_relevantes"],
        "nos": [],
        "arestas": [],
        "fontes": [primary_source],
        "fontes_sugeridas": sources_suggested,
        "referencias_wikipedia_vinculadas": linked_references,
    }
    return validate_staging_payload(payload)


def save_staging_document(payload: dict[str, Any], path: Path | None = None) -> Path:
    target = path or next_staging_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dumps_pretty(validate_staging_payload(payload)), encoding="utf-8")
    return target


def ingest_to_staging(url: str | None = None, file_path: str | None = None) -> Path:
    payload = build_staging_document(url=url, file_path=file_path)
    return save_staging_document(payload)


def load_staging_document(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_staging_payload(raw)


def list_staging_documents() -> list[Path]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(STAGING_DIR.glob("*.json"))
