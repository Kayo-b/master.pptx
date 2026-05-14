from __future__ import annotations

import shutil
from pathlib import Path

import typer

from core.config import approved_path_for, rejected_path_for
from core.models import dumps_pretty
from db.graph import GraphStore
from db.sources import SourceStore
from pipeline.bootstrap import bootstrap_news_payload
from pipeline.ingest import build_staging_document, ingest_to_staging, list_staging_documents, load_staging_document, save_staging_document
from pipeline.images import backfill_node_images_from_wikipedia
from pipeline.news import fetch_google_news_items


app = typer.Typer(no_args_is_help=True)
source_app = typer.Typer(no_args_is_help=True)
app.add_typer(source_app, name="source")


@app.command()
def ingest(
    url: str | None = typer.Option(default=None, help="URL de artigo ou Wikipedia."),
    file: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False, help="Arquivo local."),
) -> None:
    path = ingest_to_staging(url=url, file_path=str(file) if file else None)
    typer.echo(f"Staging criado em {path}")


@app.command()
def review(file: Path | None = typer.Option(default=None, exists=True, dir_okay=False)) -> None:
    if file is None:
        documents = list_staging_documents()
        if not documents:
            typer.echo("Nenhum staging pendente.")
            return
        for item in documents:
            typer.echo(item)
        return
    payload = load_staging_document(file)
    typer.echo(dumps_pretty(payload))


@app.command()
def approve(file: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False)) -> None:
    payload = load_staging_document(file)
    SourceStore().init_db()
    approved_payload = GraphStore().approve_payload(payload, SourceStore())
    file.write_text(dumps_pretty(approved_payload), encoding="utf-8")
    destination = approved_path_for(file)
    shutil.move(str(file), destination)
    typer.echo(f"Staging aprovado e movido para {destination}")


@app.command()
def reject(file: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False)) -> None:
    destination = rejected_path_for(file)
    shutil.move(str(file), destination)
    typer.echo(f"Staging movido para {destination}")


@app.command("backfill-images")
def backfill_images() -> None:
    store = GraphStore()
    nodes = store.list_nodes()
    result = backfill_node_images_from_wikipedia(nodes)
    if result["updated_nodes"]:
        store.upsert_nodes(result["updated_nodes"])
    typer.echo(
        "Imagens atualizadas: "
        f"{result['updated_count']} | "
        f"sem alteracao: {len(nodes) - result['updated_count']} | "
        f"erros: {len(result['errors'])}"
    )
    for error in result["errors"][:20]:
        typer.echo(f"ERRO {error['node_id']} {error['entidade']}: {error['erro']}")


@app.command("sync-news")
def sync_news(
    query: str = typer.Option(..., help="Consulta para o Google Noticias."),
    hours: int = typer.Option(4, min=1, help="Janela de horas para buscar noticias recentes."),
    limit: int = typer.Option(10, min=1, help="Numero maximo de noticias para processar."),
    auto_approve: bool = typer.Option(True, help="Aprova automaticamente apos o ingest."),
) -> None:
    source_store = SourceStore()
    graph_store = GraphStore()
    source_store.init_db()
    items = fetch_google_news_items(query, hours=hours, limit=limit)
    processed = 0
    skipped = 0
    errors: list[str] = []
    for item in items:
        if source_store.get_source_by_url(item.article_url):
            skipped += 1
            continue
        try:
            payload = build_staging_document(url=item.article_url)
            payload["fontes"][0]["titulo"] = item.title
            payload["fontes"][0]["veiculo"] = item.source_name
            payload["fontes"][0]["data"] = item.published_at.date().isoformat()
            payload = bootstrap_news_payload(payload, item.title)
            path = save_staging_document(payload)
            if auto_approve:
                approved_payload = graph_store.approve_payload(payload, source_store)
                path.write_text(dumps_pretty(approved_payload), encoding="utf-8")
                destination = approved_path_for(path)
                shutil.move(str(path), destination)
            processed += 1
        except Exception as exc:
            errors.append(f"{item.article_url}: {exc}")
    typer.echo(f"Noticias processadas: {processed} | ignoradas: {skipped} | erros: {len(errors)}")
    for error in errors[:20]:
        typer.echo(f"ERRO {error}")


@source_app.command("add")
def add_source(
    url: str = typer.Option(...),
    titulo: str | None = typer.Option(default=None),
    autor: str | None = typer.Option(default=None),
    veiculo: str | None = typer.Option(default=None),
    data: str | None = typer.Option(default=None),
    tipo: str | None = typer.Option(default=None),
    id: str | None = typer.Option(default=None),
) -> None:
    source = SourceStore().add_source(
        {
            "id": id,
            "url": url,
            "titulo": titulo,
            "autor": autor,
            "veiculo": veiculo,
            "data": data,
            "tipo": tipo,
        }
    )
    typer.echo(f"Fonte salva: {source['id']}")


@source_app.command("list")
def list_sources() -> None:
    sources = SourceStore().list_sources()
    if not sources:
        typer.echo("Nenhuma fonte cadastrada.")
        return
    for source in sources:
        label = source["titulo"] or source["url"]
        typer.echo(f"{source['id']} {label}")


if __name__ == "__main__":
    app()
