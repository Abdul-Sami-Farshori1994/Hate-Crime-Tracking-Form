"""Issue access + refresh cookies and persist refresh session."""

from __future__ import annotations

from fastapi import Response
from sqlalchemy.ext.asyncio import AsyncSession

import auth as auth_core
import config as app_config
from cookie_auth import set_session_cookies
from models import User, UserRole
from refresh_store import create_refresh_session, new_family_id, new_jti, revoke_all_for_user
from schemas import SessionResponse


async def issue_user_session(
    db: AsyncSession,
    response: Response,
    user: User,
    *,
    role: UserRole,
) -> SessionResponse:
    await revoke_all_for_user(db, user.id)
    family_id = new_family_id()
    jti = new_jti()
    tv = getattr(user, "token_version", 1) or 1
    access = auth_core.create_access_token(
        username=user.username,
        uid=user.id,
        role=role.value,
        token_version=tv,
    )
    refresh = auth_core.create_refresh_token(
        username=user.username,
        uid=user.id,
        role=role.value,
        token_version=tv,
        jti=jti,
        family_id=family_id,
    )
    await create_refresh_session(
        db,
        user=user,
        refresh_token=refresh,
        jti=jti,
        family_id=family_id,
    )
    if app_config.use_cookie_auth():
        set_session_cookies(response, access_token=access, refresh_token=refresh, role=role.value)
    return SessionResponse(
        role=role.value,
        username=user.username,
        access_token=access,
    )
