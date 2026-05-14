from __future__ import annotations

from collections import deque
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import ASSETS_DIR, ensure_runtime_dirs
from db.graph import GraphStore
from db.sources import SourceStore


ensure_runtime_dirs()

app = FastAPI(title="Grafo de Investigacao Brasileira", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

graph_store = GraphStore()
source_store = SourceStore()


def _hydrate_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hydrated = []
    for edge in edges:
        sources = [source_store.get_source(source_id) for source_id in edge.get("fonte_ids", [])]
        hydrated.append({**edge, "fontes": [source for source in sources if source]})
    return hydrated


def _apply_filters(graph: dict[str, list[dict[str, Any]]], confianca: str | None, tipo_no: str | None) -> dict[str, list[dict[str, Any]]]:
    nodes = graph["nodes"]
    edges = _hydrate_edges(graph["edges"])
    if confianca:
        edges = [edge for edge in edges if edge.get("confianca") == confianca]
        active_ids = {edge["origem_id"] for edge in edges} | {edge["destino_id"] for edge in edges}
        nodes = [node for node in nodes if node["id"] in active_ids]
    if tipo_no:
        nodes = [node for node in nodes if node["tipo_no"] == tipo_no]
        active_ids = {node["id"] for node in nodes}
        edges = [edge for edge in edges if edge["origem_id"] in active_ids and edge["destino_id"] in active_ids]
    return {"nodes": nodes, "edges": edges}


def _neighbors(graph: dict[str, list[dict[str, Any]]], node_id: str, degree: int) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, set[str]] = {}
    edge_map: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        adjacency.setdefault(edge["origem_id"], set()).add(edge["destino_id"])
        adjacency.setdefault(edge["destino_id"], set()).add(edge["origem_id"])
        edge_map.append(edge)
    visited = {node_id}
    queue = deque([(node_id, 0)])
    while queue:
        current, current_degree = queue.popleft()
        if current_degree >= degree:
            continue
        for neighbor in adjacency.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, current_degree + 1))
    nodes = [node for node in graph["nodes"] if node["id"] in visited]
    edges = [
        edge
        for edge in edge_map
        if edge["origem_id"] in visited and edge["destino_id"] in visited
    ]
    return {"nodes": nodes, "edges": edges}


def _node_detail(node_id: str) -> dict[str, Any] | None:
    snapshot = graph_store.graph_snapshot()
    node = next((item for item in snapshot["nodes"] if item["id"] == node_id), None)
    if node is None:
        return None
    relations = []
    for edge in _hydrate_edges(snapshot["edges"]):
        if node_id not in {edge["origem_id"], edge["destino_id"]}:
            continue
        relations.append(edge)
    return {**node, "relacoes": relations}


@app.get("/graph")
def get_graph(
    confianca: str | None = Query(default=None),
    tipo_no: str | None = Query(default=None),
    grau: int | None = Query(default=None, ge=1),
    centro_id: str | None = Query(default=None),
) -> dict[str, list[dict[str, Any]]]:
    snapshot = _apply_filters(graph_store.graph_snapshot(), confianca, tipo_no)
    if grau is not None and centro_id:
        return _neighbors(snapshot, centro_id, grau)
    return snapshot


@app.get("/graph/node/{node_id}")
def get_node(node_id: str) -> dict[str, Any]:
    detail = _node_detail(node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="No nao encontrado.")
    return detail


@app.get("/graph/node/{node_id}/neighbors")
def get_neighbors(node_id: str, grau: int = Query(default=1, ge=1)) -> dict[str, list[dict[str, Any]]]:
    snapshot = graph_store.graph_snapshot()
    if not any(node["id"] == node_id for node in snapshot["nodes"]):
        raise HTTPException(status_code=404, detail="No nao encontrado.")
    return _neighbors(snapshot, node_id, grau)


@app.get("/sources")
def list_sources() -> list[dict[str, Any]]:
    return source_store.list_sources()


@app.get("/sources/{source_id}")
def get_source(source_id: str) -> dict[str, Any]:
    source = source_store.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte nao encontrada.")
    return source
