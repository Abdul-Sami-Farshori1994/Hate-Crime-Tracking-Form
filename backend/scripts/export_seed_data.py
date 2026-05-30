"""Export local database rows to backend/data/seed/*.json for production import.

Run on your machine (where the real data lives), from backend/:

  python scripts/export_seed_data.py

Then commit backend/data/seed/ and deploy. On production:

  python seed.py --dry-run
  python seed.py --commit
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import get_session_factory  # noqa: E402
from models import (  # noqa: E402
    AuditEvent,
    FormPage,
    Question,
    QuestionBranchRule,
    Response,
    ResponseSession,
    User,
)
from seed_data import MANIFEST_FILE, SEED_DIR, SEED_TABLES, write_json_rows  # noqa: E402

TABLE_MODELS = {
    "users": User,
    "form_pages": FormPage,
    "questions": Question,
    "question_branch_rules": QuestionBranchRule,
    "response_sessions": ResponseSession,
    "responses": Response,
    "audit_events": AuditEvent,
}


def row_to_dict(row) -> dict:
    return {col.name: getattr(row, col.name) for col in row.__table__.columns}


async def export_all() -> dict[str, int]:
    counts: dict[str, int] = {}
    async with get_session_factory()() as session:
        for table in SEED_TABLES:
            model = TABLE_MODELS[table]
            result = await session.execute(select(model))
            rows = [row_to_dict(r) for r in result.scalars().all()]
            write_json_rows(SEED_DIR / f"{table}.json", rows)
            counts[table] = len(rows)
            print(f"  {table}: {len(rows)} rows")
    return counts


async def main() -> None:
    print(f"Exporting seed data to {SEED_DIR} …")
    counts = await export_all()
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": counts,
    }
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = SEED_DIR / MANIFEST_FILE
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"Wrote {manifest_path}")
    print("Next: commit backend/data/seed/, deploy, then run `python seed.py --commit` on production.")


if __name__ == "__main__":
    asyncio.run(main())
