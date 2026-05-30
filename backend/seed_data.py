"""Shared helpers for production seed export/import."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

SEED_DIR = Path(__file__).resolve().parent / "data" / "seed"
MANIFEST_FILE = "manifest.json"

# Import order respects foreign keys.
SEED_TABLES: tuple[str, ...] = (
    "users",
    "form_pages",
    "questions",
    "question_branch_rules",
    "response_sessions",
    "responses",
    "audit_events",
)

# Cleared before import (includes ephemeral tables not in SEED_TABLES).
CLEAR_TABLES: tuple[str, ...] = (
    "responses",
    "response_sessions",
    "question_branch_rules",
    "questions",
    "form_pages",
    "audit_events",
    "refresh_sessions",
    "login_lockouts",
    "users",
)


class SeedJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


def seed_table_path(table: str) -> Path:
    return SEED_DIR / f"{table}.json"


def load_json_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return data


def write_json_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, cls=SeedJSONEncoder, ensure_ascii=False, separators=(",", ":"))
