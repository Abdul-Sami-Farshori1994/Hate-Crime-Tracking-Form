"""Per-username login lockout after repeated failed attempts."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import LoginLockout

_DEFAULT_MAX_FAILURES = 5
_DEFAULT_LOCKOUT_MINUTES = 15


def max_login_failures() -> int:
    raw = os.getenv("LOGIN_MAX_FAILURES", str(_DEFAULT_MAX_FAILURES)).strip()
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_MAX_FAILURES
    return max(1, min(value, 50))


def lockout_minutes() -> int:
    raw = os.getenv("LOGIN_LOCKOUT_MINUTES", str(_DEFAULT_LOCKOUT_MINUTES)).strip()
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_LOCKOUT_MINUTES
    return max(1, min(value, 24 * 60))


def _normalize_username(username: str) -> str:
    return username.strip().lower()[:255]


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def assert_not_locked(db: AsyncSession, username: str) -> None:
    key = _normalize_username(username)
    row = await db.get(LoginLockout, key)
    if row is None:
        return

    now = datetime.now(timezone.utc)
    locked_until = _as_utc(row.locked_until)
    if int(row.failed_attempts or 0) >= max_login_failures():
        if locked_until is None or locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later.",
            )

    if locked_until is not None and locked_until <= now:
        row.failed_attempts = 0
        row.locked_until = None


async def record_failed_login(db: AsyncSession, username: str) -> int:
    """Increment failures; set lockout when threshold reached. Returns new failure count."""
    key = _normalize_username(username)
    now = datetime.now(timezone.utc)
    row = await db.get(LoginLockout, key)
    if row is None:
        row = LoginLockout(username=key, failed_attempts=0, locked_until=None)
        db.add(row)

    row.failed_attempts = int(row.failed_attempts or 0) + 1
    failures = row.failed_attempts
    if failures >= max_login_failures():
        row.locked_until = now + timedelta(minutes=lockout_minutes())
    else:
        row.locked_until = None
    await db.flush()
    return failures


async def clear_login_lockout(db: AsyncSession, username: str) -> None:
    key = _normalize_username(username)
    row = await db.get(LoginLockout, key)
    if row is None:
        return
    row.failed_attempts = 0
    row.locked_until = None
    await db.flush()
