from __future__ import annotations

import shutil
from pathlib import Path

import typer

from core.config import approved_path_for, rejected_path_for
from core.models import dumps_pretty
from db.graph import GraphStore
from db.sources import SourceStore
from pipeline.ingest import ingest_to_staging, list_staging_documents, load_staging_document


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
    GraphStore().approve_payload(payload, SourceStore())
    destination = approved_path_for(file)
    shutil.move(str(file), destination)
    typer.echo(f"Staging aprovado e movido para {destination}")


@app.command()
def reject(file: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False)) -> None:
    destination = rejected_path_for(file)
    shutil.move(str(file), destination)
    typer.echo(f"Staging movido para {destination}")


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
