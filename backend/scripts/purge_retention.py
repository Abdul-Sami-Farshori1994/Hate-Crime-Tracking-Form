#!/usr/bin/env python3
"""
Hard-delete soft-deleted response sessions older than RETENTION_DAYS (default 365).

Usage:
  cd backend
  python scripts/purge_retention.py --dry-run
  python scripts/purge_retention.py --commit
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from database import get_session_factory
from models import Response, ResponseSession


async def run(*, days: int, commit: bool) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with get_session_factory()() as session:
        result = await session.execute(
            select(ResponseSession.session_id).where(
                ResponseSession.deleted_at.is_not(None),
                ResponseSession.deleted_at < cutoff,
            )
        )
        session_ids = [row[0] for row in result.all()]
        print(f"Sessions to purge: {len(session_ids)} (deleted before {cutoff.isoformat()})")
        if not session_ids or not commit:
            return
        await session.execute(delete(Response).where(Response.session_id.in_(session_ids)))
        await session.execute(
            delete(ResponseSession).where(ResponseSession.session_id.in_(session_ids))
        )
        await session.commit()
        print("Purge committed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Apply deletes (default is dry-run)")
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("RETENTION_DAYS", "365")),
        help="Purge soft-deleted sessions older than this many days",
    )
    args = parser.parse_args()
    asyncio.run(run(days=args.days, commit=args.commit))


if __name__ == "__main__":
    main()
