from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
GRAPH_DB_PATH = DATA_DIR / "graph.kuzu"
SOURCES_DB_PATH = DATA_DIR / "sources.db"
STAGING_DIR = DATA_DIR / "staging"
APPROVED_DIR = DATA_DIR / "approved"
REJECTED_DIR = DATA_DIR / "rejected"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
ANTHROPIC_API_URL = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, STAGING_DIR, APPROVED_DIR, REJECTED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def utc_timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def next_staging_path() -> Path:
    ensure_runtime_dirs()
    return STAGING_DIR / f"{utc_timestamp_slug()}.json"


def approved_path_for(path: Path) -> Path:
    ensure_runtime_dirs()
    return APPROVED_DIR / path.name


def rejected_path_for(path: Path) -> Path:
    ensure_runtime_dirs()
    return REJECTED_DIR / path.name
