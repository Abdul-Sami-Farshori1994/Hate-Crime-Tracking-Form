"""Load production database from backend/data/seed/*.json.

Generate the JSON files on your local machine (where data lives):

  cd backend
  python scripts/export_seed_data.py

Deploy the repo, then on production (inside the api container or with DATABASE_URL set):

  python seed.py --dry-run
  python seed.py --commit

Requires `alembic upgrade head` first (empty schema). This replaces all seeded tables.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from sqlalchemy import text

from database import get_session_factory
from seed_data import (
    CLEAR_TABLES,
    MANIFEST_FILE,
    SEED_DIR,
    SEED_TABLES,
    load_json_rows,
    prepare_seed_row,
    seed_table_path,
)

BATCH_SIZE = 500

# PostgreSQL serial sequences after explicit id inserts.
ID_SEQUENCES: dict[str, str] = {
    "users": "users_id_seq",
    "form_pages": "form_pages_id_seq",
    "questions": "questions_id_seq",
    "question_branch_rules": "question_branch_rules_id_seq",
    "responses": "responses_id_seq",
    "audit_events": "audit_events_id_seq",
}


def load_manifest() -> dict:
    path = SEED_DIR / MANIFEST_FILE
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Run: python scripts/export_seed_data.py")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_seed_files(manifest: dict) -> dict[str, int]:
    expected = manifest.get("tables") or {}
    counts: dict[str, int] = {}
    for table in SEED_TABLES:
        path = seed_table_path(table)
        if not path.is_file():
            raise SystemExit(f"Missing seed file: {path}")
        rows = load_json_rows(path)
        counts[table] = len(rows)
        exp = expected.get(table)
        if exp is not None and exp != len(rows):
            print(f"Warning: {table} row count {len(rows)} != manifest {exp}", file=sys.stderr)
    return counts


async def clear_tables(session) -> None:
    tables = ", ".join(CLEAR_TABLES)
    await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


async def insert_rows(session, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    col_sql = ", ".join(columns)
    param_sql = ", ".join(f":{c}" for c in columns)
    stmt = text(f"INSERT INTO {table} ({col_sql}) VALUES ({param_sql})")

    for i in range(0, len(rows), BATCH_SIZE):
        for row in rows[i : i + BATCH_SIZE]:
            await session.execute(stmt, prepare_seed_row(row))


async def reset_sequences(session) -> None:
    for table, seq in ID_SEQUENCES.items():
        await session.execute(
            text(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {table}), 1), true)")
        )


async def run(*, commit: bool) -> None:
    manifest = load_manifest()
    counts = validate_seed_files(manifest)
    print("Seed files OK:")
    for table in SEED_TABLES:
        print(f"  {table}: {counts[table]} rows")
    print(f"Exported at: {manifest.get('exported_at', '?')}")

    if not commit:
        print("\nDry run only — no database changes. Use --commit to import.")
        return

    async with get_session_factory()() as session:
        try:
            print("\nClearing existing data …")
            await clear_tables(session)
            for table in SEED_TABLES:
                rows = load_json_rows(seed_table_path(table))
                print(f"Importing {table} ({len(rows)} rows) …")
                await insert_rows(session, table, rows)
            print("Resetting id sequences …")
            await reset_sequences(session)
            await session.commit()
            print("Done. Production database now matches exported seed data.")
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Import backend/data/seed JSON into the database.")
    parser.add_argument("--dry-run", action="store_true", help="Validate files only (default if no flag)")
    parser.add_argument("--commit", action="store_true", help="Replace DB contents with seed data")
    args = parser.parse_args()
    if args.commit and args.dry_run:
        raise SystemExit("Use either --dry-run or --commit, not both.")
    if not args.commit:
        args.dry_run = True
    asyncio.run(run(commit=args.commit))


if __name__ == "__main__":
    main()
