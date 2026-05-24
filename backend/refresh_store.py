"""Refresh token rotation backed by refresh_sessions table."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import config as app_config
from models import RefreshSession, User


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_refresh_session(
    db: AsyncSession,
    *,
    user: User,
    refresh_token: str,
    jti: str,
    family_id: str,
) -> RefreshSession:
    expires = datetime.now(timezone.utc) + timedelta(days=app_config.refresh_token_expire_days())
    row = RefreshSession(
        jti=jti,
        user_id=user.id,
        family_id=family_id,
        token_hash=_hash_token(refresh_token),
        expires_at=expires,
    )
    db.add(row)
    await db.flush()
    return row


async def get_active_session(db: AsyncSession, jti: str) -> RefreshSession | None:
    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.jti == jti,
            RefreshSession.revoked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        return None
    return row


async def revoke_jti(db: AsyncSession, jti: str) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.jti == jti, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def revoke_family(db: AsyncSession, family_id: str) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def new_family_id() -> str:
    return uuid.uuid4().hex


def new_jti() -> str:
    return uuid.uuid4().hex
