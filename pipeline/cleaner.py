from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


@dataclass(slots=True)
class CleanedDocument:
    source: str
    text: str
    source_kind: str


def _extract_text_from_html(html: str) -> str:
    try:
        import trafilatura
    except ImportError:
        stripper = _HTMLStripper()
        stripper.feed(html)
        return stripper.get_text()
    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    return extracted or ""


def clean_url(url: str) -> CleanedDocument:
    try:
        import trafilatura
    except ImportError as exc:
        raise RuntimeError("Dependencia ausente: instale trafilatura para processar URLs.") from exc
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise RuntimeError(f"Nao foi possivel baixar o conteudo de {url}.")
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text or not text.strip():
        raise RuntimeError(f"trafilatura nao conseguiu extrair conteudo util de {url}.")
    return CleanedDocument(source=url, text=text.strip(), source_kind="url")


def clean_file(file_path: str | Path) -> CleanedDocument:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    elif suffix in {".html", ".htm"}:
        text = _extract_text_from_html(path.read_text(encoding="utf-8"))
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Dependencia ausente: instale pypdf para processar PDFs.") from exc
        reader = PdfReader(str(path))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    else:
        raise RuntimeError(f"Formato de arquivo nao suportado: {suffix}")
    if not text or not text.strip():
        raise RuntimeError(f"Nao foi possivel extrair texto util de {path}.")
    return CleanedDocument(source=str(path), text=text.strip(), source_kind="file")


def clean_input(url: str | None = None, file_path: str | Path | None = None) -> CleanedDocument:
    if bool(url) == bool(file_path):
        raise RuntimeError("Informe exatamente uma origem: --url ou --file.")
    if url:
        return clean_url(url)
    return clean_file(file_path)
