from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

MONEY_PATTERN = re.compile(r"\b(?:R\$ ?)?\d[\d\.\,]*\s*(?:mil|milhões|bilhões|reais)?\b", flags=re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(?:19|20)\d{2}\b")
ENTITY_PATTERN = re.compile(
    r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ]*(?:\s+(?:de|do|da|dos|das|e)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ]*|\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ]*)+"
)
ACRONYM_PATTERN = re.compile(r"\b[A-Z]{2,}\b")
CLAIM_KIND_RULES = (
    ("investimento", ("invest", "aplic", "expostos", "exposição", "fundos previdenciários")),
    ("investigacao", ("investig", "operação", "busca e apreensão", "mandados")),
    ("liquidacao", ("liquidad", "intervenção", "decretou a liquidação")),
    ("compra", ("compra", "comprou", "aquisição", "adquiriu", "tentativa de venda")),
    ("venda", ("venda", "vendeu", "alienação")),
    ("pagamento", ("pag", "recebeu", "contrato", "repasse")),
    ("prisao", ("preso", "prisão", "detido")),
)


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "master-pptx-mvp/0.1"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _stable_reference_id(note_number: str) -> str:
    suffix = re.sub(r"[^a-zA-Z0-9]+", "_", note_number).strip("_").lower()
    return f"wikipedia_ref_{suffix or 'sem_numero'}"


def _extract_note_number(raw_value: str | None, fallback: str | None = None) -> str | None:
    candidates = [raw_value or "", fallback or ""]
    for value in candidates:
        if not value:
            continue
        if "cite_note-" in value:
            value = value.split("cite_note-", 1)[1]
        value = value.lstrip("#")
        digit_match = re.search(r"(\d+[a-zA-Z]?)", value)
        if digit_match:
            return digit_match.group(1)
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "", value)
        if cleaned:
            return cleaned
    return None


class _FallbackWikipediaReferencesParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_references = False
        self.references_depth = 0
        self.li_depth = 0
        self.in_cite = False
        self.current_entry: dict[str, Any] | None = None
        self.references: list[dict[str, str | None]] = []
        self.references_by_note: dict[str, dict[str, str | None]] = {}
        self.reference_index = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = set((attrs_dict.get("class") or "").split())
        if tag == "ol" and "references" in classes:
            self.in_references = True
            self.references_depth = 1
            return
        if not self.in_references:
            return
        if tag == "ol":
            self.references_depth += 1
        elif tag == "li":
            self.li_depth += 1
            if self.li_depth == 1:
                self.reference_index += 1
                note_number = _extract_note_number(attrs_dict.get("id"), str(self.reference_index)) or str(self.reference_index)
                self.current_entry = {"text": [], "cite": [], "links": [], "numero_nota": note_number}
        elif tag == "cite" and self.current_entry is not None:
            self.in_cite = True
        elif tag == "a" and self.current_entry is not None:
            href = attrs_dict.get("href")
            if href and not href.startswith("#"):
                absolute = urljoin(self.base_url, href)
                if absolute.startswith("http://") or absolute.startswith("https://"):
                    self.current_entry["links"].append(absolute)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_references:
            return
        if tag == "ol":
            self.references_depth -= 1
            if self.references_depth == 0:
                self.in_references = False
        elif tag == "cite":
            self.in_cite = False
        elif tag == "li":
            if self.li_depth == 1 and self.current_entry is not None:
                text = _normalize_space("".join(self.current_entry["text"]))
                cite_text = _normalize_space("".join(self.current_entry["cite"])) or None
                url = next((link for link in self.current_entry["links"] if link.startswith("http")), None)
                note_number = self.current_entry["numero_nota"]
                if url:
                    reference = {
                        "id": _stable_reference_id(note_number),
                        "url": url,
                        "titulo": cite_text or text[:180] or url,
                        "veiculo": infer_vehicle(url, text),
                        "data": infer_date(text),
                        "tipo": infer_source_type(url, text),
                    }
                    self.references.append(reference)
                    self.references_by_note[note_number] = reference
                self.current_entry = None
            self.li_depth = max(self.li_depth - 1, 0)

    def handle_data(self, data: str) -> None:
        if not self.in_references or self.current_entry is None:
            return
        text = data.strip()
        if not text:
            return
        self.current_entry["text"].append(f" {text}")
        if self.in_cite:
            self.current_entry["cite"].append(f" {text}")


def infer_date(text: str) -> str | None:
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_match:
        return iso_match.group(1)
    year_match = re.search(r"\b(19|20)\d{2}\b", text)
    if year_match:
        return year_match.group(0)
    return None


def infer_vehicle(url: str, text: str) -> str | None:
    candidates = (
        "Wikipedia",
        "Banco Central",
        "STJ",
        "PF",
        "Senado",
        "Camara",
        "Estadao",
        "Folha",
        "Valor",
        "G1",
        "Metrópoles",
        "Veja",
    )
    for candidate in candidates:
        if candidate.lower() in text.lower():
            return candidate
    host_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return host_match.group(1) if host_match else None


def infer_source_type(url: str, text: str) -> str | None:
    lowered = f"{url} {text}".lower()
    if "gov.br" in lowered or "camara.leg.br" in lowered or "senado.leg.br" in lowered:
        return "documento_oficial"
    if "cpi" in lowered:
        return "cpi"
    if "transcri" in lowered:
        return "transcript"
    if "relat" in lowered:
        return "relatorio"
    return "artigo"


def _build_reference_source(note_number: str, url: str, text: str, title: str | None) -> dict[str, str | None]:
    return {
        "id": _stable_reference_id(note_number),
        "url": url,
        "titulo": title or text[:180] or url,
        "veiculo": infer_vehicle(url, text),
        "data": infer_date(text),
        "tipo": infer_source_type(url, text),
    }


def _extract_entity_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for pattern in (ENTITY_PATTERN, ACRONYM_PATTERN):
        for match in pattern.finditer(text):
            candidate = _normalize_space(match.group(0))
            if len(candidate) < 2 or candidate in mentions:
                continue
            mentions.append(candidate)
    return mentions


def _extract_claim_kind(text: str) -> str:
    lowered = text.lower()
    for claim_kind, keywords in CLAIM_KIND_RULES:
        if any(keyword in lowered for keyword in keywords):
            return claim_kind
    return "citacao"


def _build_structured_claim(text: str) -> dict[str, Any]:
    return {
        "texto": text,
        "tipo": _extract_claim_kind(text),
        "entidades_mencionadas": _extract_entity_mentions(text),
        "valores_mencionados": MONEY_PATTERN.findall(text),
        "datas_mencionadas": DATE_PATTERN.findall(text),
    }


def _parse_references_with_bs4(html: str, base_url: str) -> dict[str, dict[str, str | None]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    references: dict[str, dict[str, str | None]] = {}
    for index, item in enumerate(soup.select("ol.references > li"), start=1):
        raw_id = item.get("id")
        backlink = item.select_one(".mw-cite-backlink a[href*='#cite_ref-']")
        note_number = (
            _extract_note_number(backlink.get_text(" ", strip=True) if backlink else None, raw_id)
            or _extract_note_number(backlink.get("href") if backlink else None, raw_id)
            or str(index)
        )
        link = item.select_one("a.external, a[href^='http']")
        if link is None:
            continue
        href = link.get("href")
        if not href:
            continue
        url = urljoin(base_url, href)
        text = _normalize_space(item.get_text(" ", strip=True))
        cite = item.select_one("cite")
        title = _normalize_space(cite.get_text(" ", strip=True)) if cite else text[:180]
        references[note_number] = _build_reference_source(note_number, url, text, title)
    return references


def _iter_content_blocks(soup) -> Any:
    root = soup.select_one(".mw-parser-output")
    if root is None:
        return
    for child in root.children:
        tag_name = getattr(child, "name", None)
        if tag_name is None:
            continue
        if tag_name == "section":
            heading = child.find(["h1", "h2", "h3", "h4", "h5", "h6"])
            heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
            if heading_text.startswith(("notas", "referências", "ligações externas")):
                break
            for block in child.find_all(["p", "li"], recursive=True):
                yield block
            continue
        if tag_name in {"h2", "h3"} and "referências" in child.get_text(" ", strip=True).lower():
            break
        if tag_name == "ol" and "references" in (child.get("class") or []):
            break
        if tag_name == "p":
            yield child
            continue
        if tag_name in {"ul", "ol"}:
            if "references" in (child.get("class") or []):
                break
            for item in child.find_all("li", recursive=False):
                yield item


def _reference_numbers_from_tag(tag) -> list[str]:
    numbers: list[str] = []
    for link in tag.select("a[href*='#cite_note-']"):
        href = link.get("href")
        note_number = _extract_note_number(link.get_text(" ", strip=True), href)
        if note_number and note_number not in numbers:
            numbers.append(note_number)
    return numbers


def _flatten_text(node: Any, chunks: list[str]) -> None:
    from bs4 import NavigableString, Tag

    if isinstance(node, NavigableString):
        text = _normalize_space(str(node))
        if text:
            chunks.append(text)
        return
    if not isinstance(node, Tag) or node.name in {"style", "script"}:
        return
    for child in node.children:
        _flatten_text(child, chunks)


def _text_from_children(nodes: list[Any]) -> str:
    chunks: list[str] = []
    for node in nodes:
        _flatten_text(node, chunks)
    return _normalize_space(" ".join(chunks))


def _extract_note_anchored_segments(block) -> list[tuple[str, str]]:
    from bs4 import NavigableString, Tag

    linked_segments: list[tuple[str, str]] = []
    pending_nodes: list[Any] = []
    last_anchor_text: str | None = None

    def walk(node: Any) -> None:
        nonlocal pending_nodes, last_anchor_text
        if isinstance(node, NavigableString):
            if _normalize_space(str(node)):
                pending_nodes.append(node)
            return
        if not isinstance(node, Tag) or node.name in {"style", "script"}:
            return
        if node.name == "sup" and "reference" in (node.get("class") or []):
            note_numbers = _reference_numbers_from_tag(node)
            if not note_numbers:
                return
            snippet = _text_from_children(pending_nodes)
            anchor_text = snippet or last_anchor_text
            if anchor_text:
                for note_number in note_numbers:
                    linked_segments.append((note_number, anchor_text))
                last_anchor_text = anchor_text
            pending_nodes = []
            return
        pending_nodes.append(node)

    for child in block.children:
        walk(child)
    return linked_segments


def _build_linked_references_bs4(
    html: str,
    base_url: str,
    references_by_note: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    linked_references: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for block in _iter_content_blocks(soup):
        for note_number, snippet in _extract_note_anchored_segments(block):
            reference = references_by_note.get(note_number)
            if reference is None:
                continue
            dedupe_key = (note_number, snippet)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            linked_references.append(
                {
                    "trecho_artigo": snippet,
                    "numero_nota": note_number,
                    "fonte_sugerida_id": reference["id"],
                    "referencia_correspondente": reference,
                    "claim_estruturada": _build_structured_claim(snippet),
                }
            )
    return linked_references


class _FallbackWikipediaEvidenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_root = False
        self.root_depth = 0
        self.stop_parsing = False
        self.in_heading = False
        self.heading_chunks: list[str] = []
        self.block_depth = 0
        self.pending_chunks: list[str] = []
        self.in_reference_sup = False
        self.reference_note_numbers: list[str] = []
        self.reference_text_chunks: list[str] = []
        self.linked_segments: list[tuple[str, str]] = []
        self.last_anchor_text: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        classes = set((attrs_dict.get("class") or "").split())
        if tag == "div" and "mw-parser-output" in classes and not self.in_root:
            self.in_root = True
            self.root_depth = 1
            return
        if not self.in_root or self.stop_parsing:
            return
        if tag == "div":
            self.root_depth += 1
        if tag in {"h2", "h3"} and self.block_depth == 0:
            self.in_heading = True
            self.heading_chunks = []
            return
        if tag in {"p", "li"}:
            self.block_depth += 1
            return
        if tag == "sup" and "reference" in classes and self.block_depth > 0:
            self.in_reference_sup = True
            self.reference_note_numbers = []
            self.reference_text_chunks = []
            return
        if tag == "a" and self.in_reference_sup:
            note_number = _extract_note_number(attrs_dict.get("href"))
            if note_number and note_number not in self.reference_note_numbers:
                self.reference_note_numbers.append(note_number)

    def handle_endtag(self, tag: str) -> None:
        if not self.in_root:
            return
        if self.in_heading and tag in {"h2", "h3"}:
            heading_text = _normalize_space(" ".join(self.heading_chunks)).lower()
            self.in_heading = False
            self.heading_chunks = []
            if heading_text.startswith(("notas", "referências", "ligações externas")):
                self.stop_parsing = True
            return
        if self.stop_parsing:
            return
        if tag == "sup" and self.in_reference_sup:
            if not self.reference_note_numbers:
                note_number = _extract_note_number(_normalize_space(" ".join(self.reference_text_chunks)))
                if note_number:
                    self.reference_note_numbers.append(note_number)
            snippet = _normalize_space(" ".join(self.pending_chunks))
            anchor_text = snippet or self.last_anchor_text
            if anchor_text:
                for note_number in self.reference_note_numbers:
                    self.linked_segments.append((note_number, anchor_text))
                self.last_anchor_text = anchor_text
            self.pending_chunks = []
            self.in_reference_sup = False
            self.reference_note_numbers = []
            self.reference_text_chunks = []
            return
        if tag in {"p", "li"} and self.block_depth > 0:
            self.block_depth -= 1
            if self.block_depth == 0:
                self.pending_chunks = []
                self.last_anchor_text = None
            return
        if tag == "div":
            self.root_depth -= 1
            if self.root_depth <= 0:
                self.in_root = False

    def handle_data(self, data: str) -> None:
        if not self.in_root:
            return
        text = _normalize_space(data)
        if not text:
            return
        if self.in_heading:
            self.heading_chunks.append(text)
            return
        if self.stop_parsing or self.block_depth == 0:
            return
        if self.in_reference_sup:
            self.reference_text_chunks.append(text)
            return
        self.pending_chunks.append(text)


def _build_linked_references_fallback(
    html: str,
    references_by_note: dict[str, dict[str, str | None]],
) -> list[dict[str, Any]]:
    parser = _FallbackWikipediaEvidenceParser()
    parser.feed(html)
    linked_references: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for note_number, snippet in parser.linked_segments:
        reference = references_by_note.get(note_number)
        if reference is None:
            continue
        dedupe_key = (note_number, snippet)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        linked_references.append(
            {
                "trecho_artigo": snippet,
                "numero_nota": note_number,
                "fonte_sugerida_id": reference["id"],
                "referencia_correspondente": reference,
                "claim_estruturada": _build_structured_claim(snippet),
            }
        )
    return linked_references


def parse_wikipedia_references_html(html: str, base_url: str) -> list[dict[str, str | None]]:
    try:
        return list(_parse_references_with_bs4(html, base_url).values())
    except ImportError:
        parser = _FallbackWikipediaReferencesParser(base_url)
        parser.feed(html)
        return parser.references


def parse_wikipedia_evidence_html(html: str, base_url: str) -> dict[str, list[dict[str, Any]]]:
    references_by_note = {}
    linked_references: list[dict[str, Any]] = []
    try:
        references_by_note = _parse_references_with_bs4(html, base_url)
        linked_references = _build_linked_references_bs4(html, base_url, references_by_note)
    except ImportError:
        parser = _FallbackWikipediaReferencesParser(base_url)
        parser.feed(html)
        references_by_note = parser.references_by_note
        linked_references = _build_linked_references_fallback(html, references_by_note)
    return {
        "fontes_sugeridas": list(references_by_note.values()),
        "referencias_vinculadas": linked_references,
    }


def extract_wikipedia_references(url: str) -> list[dict[str, str | None]]:
    html = fetch_html(url)
    return parse_wikipedia_references_html(html, url)


def extract_wikipedia_evidence(url: str) -> dict[str, list[dict[str, Any]]]:
    html = fetch_html(url)
    return parse_wikipedia_evidence_html(html, url)
