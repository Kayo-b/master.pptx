from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import GRAPH_DB_PATH, REPO_ROOT, ensure_runtime_dirs
from core.models import validate_staging_payload
from core.schema import NODE_SCHEMAS, RELATION_SCHEMAS
from db.sources import SourceStore
from pipeline.images import apply_suggested_images_to_nodes


class GraphStore:
    def __init__(self, db_path: str | Path = GRAPH_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def _prepare_db_path(self) -> bool:
        ensure_runtime_dirs()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists() and self.db_path.is_dir():
            extra_entries = [item for item in self.db_path.iterdir() if item.name != ".gitkeep"]
            if extra_entries:
                raise RuntimeError(
                    f"O caminho do banco Kuzu precisa ser um arquivo, mas existe um diretório em {self.db_path}."
                )
            gitkeep = self.db_path / ".gitkeep"
            if gitkeep.exists():
                gitkeep.unlink()
            try:
                self.db_path.rmdir()
            except FileNotFoundError:
                pass
        return self.db_path.exists()

    def _connect(self):
        try:
            import kuzu
        except ImportError as exc:
            raise RuntimeError("Dependencia ausente: instale kuzu para persistir o grafo.") from exc
        self._prepare_db_path()
        database = kuzu.Database(str(self.db_path))
        return kuzu.Connection(database)

    def init_db(self) -> None:
        already_exists = self._prepare_db_path()
        if already_exists:
            self._ensure_node_properties()
            return
        schema_path = REPO_ROOT / "db" / "schema.cypher"
        statements = [statement.strip() for statement in schema_path.read_text(encoding="utf-8").split(";") if statement.strip()]
        connection = self._connect()
        for statement in statements:
            connection.execute(statement)
        self._ensure_node_properties()

    def _ensure_node_properties(self) -> None:
        connection = self._connect()
        for node_type, schema in NODE_SCHEMAS.items():
            for field in schema.fields:
                if field == "id":
                    continue
                try:
                    connection.execute(f"ALTER TABLE {node_type} ADD {field} STRING")
                except RuntimeError as exc:
                    if "already has property" in str(exc):
                        continue
                    raise

    def _fetch_rows(self, query: str, parameters: dict[str, Any] | None = None) -> list[list[Any]]:
        self.init_db()
        connection = self._connect()
        result = connection.execute(query, parameters) if parameters is not None else connection.execute(query)
        rows: list[list[Any]] = []
        while result.has_next():
            rows.append(result.get_next())
        return rows

    def _execute(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        self.init_db()
        connection = self._connect()
        if parameters is not None:
            connection.execute(query, parameters)
        else:
            connection.execute(query)

    def upsert_nodes(self, nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            node_type = node["tipo_no"]
            fields = [field for field in NODE_SCHEMAS[node_type].fields if field != "id"]
            assignments = ", ".join(f"n.{field} = ${field}" for field in fields)
            query = f"MERGE (n:{node_type} {{id: $id}}) SET {assignments}"
            parameters = {field: node.get(field) for field in NODE_SCHEMAS[node_type].fields}
            self._execute(query, parameters)

    def insert_edges(self, edges: list[dict[str, Any]]) -> None:
        for edge in edges:
            schema = RELATION_SCHEMAS[edge["tipo_relacao"]]
            properties = []
            parameters = {"origem_id": edge["origem_id"], "destino_id": edge["destino_id"]}
            for field in schema.fields:
                value = edge.get(field)
                if field == "fonte_ids":
                    value = json.dumps(edge["fonte_ids"], ensure_ascii=False)
                properties.append(f"{field}: ${field}")
                parameters[field] = value
            query = (
                f"MATCH (a:{schema.source_type} {{id: $origem_id}}), (b:{schema.target_type} {{id: $destino_id}}) "
                f"CREATE (a)-[:{edge['tipo_relacao']} {{{', '.join(properties)}}}]->(b)"
            )
            self._execute(query, parameters)

    def list_nodes(self) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for node_type, schema in NODE_SCHEMAS.items():
            projection = ", ".join(f"n.{field}" for field in schema.fields)
            rows = self._fetch_rows(f"MATCH (n:{node_type}) RETURN {projection}")
            for row in rows:
                item = {"tipo_no": node_type}
                for index, field in enumerate(schema.fields):
                    item[field] = row[index]
                nodes.append(item)
        return nodes

    def list_edges(self) -> list[dict[str, Any]]:
        edges: list[dict[str, Any]] = []
        for relation_type, schema in RELATION_SCHEMAS.items():
            projections = ["a.id", "b.id"] + [f"r.{field}" for field in schema.fields]
            rows = self._fetch_rows(
                f"MATCH (a:{schema.source_type})-[r:{relation_type}]->(b:{schema.target_type}) RETURN {', '.join(projections)}"
            )
            for row in rows:
                item = {"tipo_relacao": relation_type, "origem_id": row[0], "destino_id": row[1]}
                for index, field in enumerate(schema.fields, start=2):
                    value = row[index]
                    if field == "fonte_ids" and value:
                        value = json.loads(value)
                    item[field] = value
                edges.append(item)
        return edges

    def graph_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {"nodes": self.list_nodes(), "edges": self.list_edges()}

    def approve_payload(self, payload: dict[str, Any], source_store: SourceStore | None = None) -> dict[str, Any]:
        source_store = source_store or SourceStore()
        normalized = validate_staging_payload(payload)
        normalized = apply_suggested_images_to_nodes(normalized)
        source_store.import_sources(normalized["fontes"])
        referenced_ids = {source_id for edge in normalized["arestas"] for source_id in edge["fonte_ids"]}
        missing_ids = source_store.ensure_source_ids_exist(referenced_ids)
        if missing_ids:
            raise RuntimeError(f"Fonte(s) inexistente(s) referenciada(s) por arestas: {', '.join(missing_ids)}")
        self.upsert_nodes(normalized["nos"])
        self.insert_edges(normalized["arestas"])
        return normalized
