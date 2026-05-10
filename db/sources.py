from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from core.config import SOURCES_DB_PATH, ensure_runtime_dirs
from core.models import validate_source


class SourceStore:
    def __init__(self, db_path: str | Path = SOURCES_DB_PATH) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        ensure_runtime_dirs()
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS fontes (
                  id TEXT PRIMARY KEY,
                  url TEXT NOT NULL,
                  titulo TEXT,
                  autor TEXT,
                  veiculo TEXT,
                  data TEXT,
                  tipo TEXT
                )
                """
            )
            connection.commit()

    def add_source(self, source: dict) -> dict:
        normalized = validate_source(source)
        self.init_db()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO fontes (id, url, titulo, autor, veiculo, data, tipo)
                VALUES (:id, :url, :titulo, :autor, :veiculo, :data, :tipo)
                ON CONFLICT(id) DO UPDATE SET
                  url = excluded.url,
                  titulo = excluded.titulo,
                  autor = excluded.autor,
                  veiculo = excluded.veiculo,
                  data = excluded.data,
                  tipo = excluded.tipo
                """,
                normalized,
            )
            connection.commit()
        return normalized

    def import_sources(self, sources: Iterable[dict]) -> list[dict]:
        return [self.add_source(source) for source in sources]

    def list_sources(self) -> list[dict]:
        self.init_db()
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM fontes ORDER BY COALESCE(data, ''), titulo, id").fetchall()
        return [dict(row) for row in rows]

    def get_source(self, source_id: str) -> dict | None:
        self.init_db()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM fontes WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None

    def ensure_source_ids_exist(self, source_ids: Iterable[str]) -> list[str]:
        ids = sorted(set(source_ids))
        if not ids:
            return []
        self.init_db()
        placeholders = ", ".join("?" for _ in ids)
        with self._connect() as connection:
            rows = connection.execute(f"SELECT id FROM fontes WHERE id IN ({placeholders})", ids).fetchall()
        existing = {row["id"] for row in rows}
        return [source_id for source_id in ids if source_id not in existing]
