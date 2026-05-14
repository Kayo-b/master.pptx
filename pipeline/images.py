from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
import unicodedata
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from core.config import IMAGE_DIR, ensure_runtime_dirs
from core.models import slugify

_IMAGE_META_KEYS = {"og:image", "twitter:image", "twitter:image:src"}
_ENTITY_LABELS = {"PER", "ORG"}
_ACRONYM_LABELS = {"LOC"}
_REQUEST_RETRY_DELAYS = (0.4, 1.0, 2.0)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value).strip()


def _entity_tokens(value: str) -> list[str]:
    normalized = _normalize_text(value)
    return [token for token in normalized.split() if len(token) >= 3]


def _is_supported_entity(entity: dict[str, Any]) -> bool:
    label = entity.get("label")
    text = entity.get("texto")
    if not isinstance(text, str) or not text.strip():
        return False
    if "<" in text or ">" in text:
        return False
    if label in _ENTITY_LABELS:
        return True
    return label in _ACRONYM_LABELS and text.isupper() and len(text) >= 2


def _rank_entities(entities: list[dict[str, Any]]) -> list[str]:
    counts: Counter[str] = Counter()
    first_seen: dict[str, str] = {}
    for entity in entities:
        if not _is_supported_entity(entity):
            continue
        text = entity["texto"].strip()
        normalized = _normalize_text(text)
        if not normalized:
            continue
        counts[normalized] += 1
        first_seen.setdefault(normalized, text)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
    return [first_seen[normalized] for normalized, _ in ranked[:20]]


class _ImageCandidateParser(HTMLParser):
    def __init__(self, base_url: str | None) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.candidates: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "meta":
            name = (attrs_dict.get("property") or attrs_dict.get("name") or "").strip().lower()
            content = (attrs_dict.get("content") or "").strip()
            if name in _IMAGE_META_KEYS and content:
                url = self._absolute_url(content)
                if url:
                    self.candidates.append({"url": url, "kind": "meta", "alt": "", "title": ""})
            return
        if tag != "img":
            return
        src = (
            attrs_dict.get("src")
            or attrs_dict.get("data-src")
            or attrs_dict.get("data-lazy-src")
            or ""
        ).strip()
        if not src:
            return
        url = self._absolute_url(src)
        if not url:
            return
        self.candidates.append(
            {
                "url": url,
                "kind": "img",
                "alt": (attrs_dict.get("alt") or "").strip(),
                "title": (attrs_dict.get("title") or "").strip(),
            }
        )

    def _absolute_url(self, url: str) -> str | None:
        if url.startswith("data:"):
            return None
        if self.base_url:
            return urljoin(self.base_url, url)
        if url.startswith(("http://", "https://")):
            return url
        return None


def _dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for candidate in candidates:
        url = candidate["url"]
        if url in seen:
            continue
        seen.add(url)
        deduped.append(candidate)
    return deduped


def _candidate_score(entity_name: str, candidate: dict[str, str]) -> int:
    normalized_name = _normalize_text(entity_name)
    haystack = _normalize_text(" ".join([candidate["url"], candidate["alt"], candidate["title"]]))
    if not normalized_name or not haystack:
        return 0
    score = 0
    if normalized_name in haystack:
        score += 12
    tokens = _entity_tokens(entity_name)
    if tokens:
        matched_tokens = sum(token in haystack for token in tokens)
        score += matched_tokens * 3
        if matched_tokens == len(tokens):
            score += 5
    elif entity_name.isupper() and entity_name.lower() in haystack:
        score += 8
    if candidate["kind"] == "img":
        score += 1
    return score


def _guess_extension(image_url: str, content_type: str | None) -> str:
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed:
            return guessed
    suffix = Path(urlparse(image_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    return ".jpg"


def _download_image(image_url: str, entity_name: str) -> str:
    ensure_runtime_dirs()
    request = Request(image_url, headers={"User-Agent": "master-pptx-mvp/0.1"})
    last_error: Exception | None = None
    for delay in (*_REQUEST_RETRY_DELAYS, None):
        try:
            with urlopen(request, timeout=30) as response:
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    raise RuntimeError(f"Resposta nao era imagem: {content_type or 'sem content-type'}")
                extension = _guess_extension(image_url, content_type)
                digest = hashlib.sha1(image_url.encode("utf-8")).hexdigest()[:10]
                target = IMAGE_DIR / f"{slugify(entity_name)}-{digest}{extension}"
                if not target.exists():
                    target.write_bytes(response.read())
                return f"/assets/images/{target.name}"
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429 or delay is None:
                raise
            time.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("Falha inesperada ao baixar imagem.")


def extract_image_suggestions(
    source: str,
    source_kind: str,
    raw_html: str | None,
    entities: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    if not raw_html:
        return {"imagens_sugeridas": [], "erros": []}
    base_url = source if source_kind == "url" else None
    parser = _ImageCandidateParser(base_url)
    parser.feed(raw_html)
    candidates = _dedupe_candidates(parser.candidates)
    ranked_entities = _rank_entities(entities)
    suggestions: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    used_urls: set[str] = set()
    for entity_name in ranked_entities:
        scored_candidates = sorted(
            (
                (candidate, _candidate_score(entity_name, candidate))
                for candidate in candidates
                if candidate["url"] not in used_urls
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        if not scored_candidates:
            continue
        best_candidate, score = scored_candidates[0]
        if score < 8:
            continue
        try:
            local_image_url = _download_image(best_candidate["url"], entity_name)
        except (HTTPError, URLError, RuntimeError) as exc:
            errors.append({"entidade": entity_name, "url": best_candidate["url"], "erro": str(exc)})
            continue
        used_urls.add(best_candidate["url"])
        suggestions.append(
            {
                "entidade": entity_name,
                "imagem_url": local_image_url,
                "origem_imagem": best_candidate["url"],
                "score": score,
            }
        )
    return {"imagens_sugeridas": suggestions, "erros": errors}


def apply_suggested_images_to_nodes(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    suggestions = metadata.get("imagens_sugeridas", [])
    if not isinstance(suggestions, list):
        return payload
    images_by_entity = {
        _normalize_text(item.get("entidade", "")): item.get("imagem_url")
        for item in suggestions
        if isinstance(item, dict) and isinstance(item.get("imagem_url"), str)
    }
    for node in payload.get("nos", []):
        if node.get("imagem_url"):
            continue
        for key in ("nome", "sigla"):
            value = node.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            image_url = images_by_entity.get(_normalize_text(value))
            if image_url:
                node["imagem_url"] = image_url
                break
    return payload


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "master-pptx-mvp/0.1"})
    last_error: Exception | None = None
    for delay in (*_REQUEST_RETRY_DELAYS, None):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429 or delay is None:
                raise
            time.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("Falha inesperada ao consultar JSON remoto.")


def _wikipedia_page_image(title: str) -> dict[str, Any] | None:
    query_url = (
        "https://pt.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages"
        "&piprop=thumbnail|name&pithumbsize=800&titles="
        + quote(title)
    )
    payload = _fetch_json(query_url)
    pages = payload.get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return None
    for page in pages.values():
        if not isinstance(page, dict) or "missing" in page:
            continue
        thumbnail = page.get("thumbnail", {})
        source = thumbnail.get("source")
        if isinstance(source, str) and source:
            return {"title": page.get("title") or title, "source": source}
    return None


def _wikipedia_search_title(query: str) -> str | None:
    search_url = (
        "https://pt.wikipedia.org/w/api.php?action=query&format=json&list=search"
        "&srlimit=1&srsearch="
        + quote(query)
    )
    payload = _fetch_json(search_url)
    results = payload.get("query", {}).get("search", [])
    if not isinstance(results, list) or not results:
        return None
    top = results[0]
    title = top.get("title")
    return title if isinstance(title, str) and title.strip() else None


def fetch_wikipedia_image(entity_name: str) -> dict[str, str] | None:
    direct = _wikipedia_page_image(entity_name)
    if direct:
        return direct
    search_title = _wikipedia_search_title(entity_name)
    if not search_title:
        return None
    fallback = _wikipedia_page_image(search_title)
    if fallback:
        return fallback
    return None


def backfill_node_images_from_wikipedia(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    updated_nodes: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    skipped = 0
    for node in nodes:
        if node.get("imagem_url"):
            skipped += 1
            continue
        entity_name = None
        for key in ("nome", "sigla"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                entity_name = value.strip()
                break
        if not entity_name:
            skipped += 1
            continue
        try:
            image = fetch_wikipedia_image(entity_name)
            if not image:
                continue
            node["imagem_url"] = _download_image(image["source"], entity_name)
            updated_nodes.append(node)
            time.sleep(0.25)
        except (HTTPError, URLError, RuntimeError, ValueError) as exc:
            errors.append({"node_id": node.get("id", ""), "entidade": entity_name, "erro": str(exc)})
            time.sleep(0.5)
    return {"updated_nodes": updated_nodes, "updated_count": len(updated_nodes), "skipped_count": skipped, "errors": errors}
