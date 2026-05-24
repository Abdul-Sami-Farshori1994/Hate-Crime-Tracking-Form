import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config as app_config

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass

from cookie_auth import get_access_token_from_request
from database import get_db
from ip_allowlist import assert_admin_ip_allowed
from models import User, UserRole, normalize_user_role
from schemas import TokenPayload

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
reusable_bearer = HTTPBearer(auto_error=False)


def _secret_key() -> str:
    app_config.validate_secret_key()
    return os.getenv("SECRET_KEY", "").strip()


def _algorithm() -> str:
    return os.getenv("ALGORITHM", "HS256")


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, _secret_key(), algorithm=_algorithm())


def create_access_token(
    *,
    username: str,
    uid: int,
    role: str,
    token_version: int = 1,
) -> str:
    minutes = app_config.access_token_expire_minutes(role)
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    to_encode: dict[str, Any] = {
        "sub": username,
        "uid": uid,
        "role": role,
        "tv": int(token_version),
        "typ": "access",
        "exp": expire,
    }
    return _encode(to_encode)


def create_refresh_token(
    *,
    username: str,
    uid: int,
    role: str,
    token_version: int,
    jti: str,
    family_id: str,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=app_config.refresh_token_expire_days())
    to_encode: dict[str, Any] = {
        "sub": username,
        "uid": uid,
        "role": role,
        "tv": int(token_version),
        "typ": "refresh",
        "jti": jti,
        "fid": family_id,
        "exp": expire,
    }
    return _encode(to_encode)


def create_mfa_pending_token(*, username: str, uid: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=app_config.mfa_pending_expire_minutes())
    return _encode(
        {
            "sub": username,
            "uid": uid,
            "typ": "mfa_pending",
            "exp": expire,
        }
    )


def create_mfa_setup_token(*, username: str, uid: int, setup_secret: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=app_config.mfa_pending_expire_minutes())
    return _encode(
        {
            "sub": username,
            "uid": uid,
            "typ": "mfa_setup",
            "mfa_secret": setup_secret,
            "exp": expire,
        }
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret_key(), algorithms=[_algorithm()])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def _user_from_token_string(
    token: str | None,
    db: AsyncSession,
) -> tuple[TokenPayload, User]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        if payload.get("typ") not in (None, "access"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        token_data = TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if token_data.sub is None or token_data.uid is None or token_data.role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    result = await db.execute(select(User).where(User.id == int(token_data.uid)))
    user = result.scalar_one_or_none()
    if user is None or user.username != token_data.sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    expected_tv = getattr(user, "token_version", 1) or 1
    token_tv = token_data.tv if token_data.tv is not None else 1
    if token_tv != expected_tv:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked; please sign in again",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return token_data, user


async def _user_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> tuple[TokenPayload, User]:
    token = get_access_token_from_request(request)
    if not token and credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    return await _user_from_token_string(token, db)


async def require_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(reusable_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    token_data, user = await _user_from_request(request, credentials, db)
    if token_data.role != UserRole.user.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User role required")
    nr = normalize_user_role(user.role)
    if nr != UserRole.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account required")
    return user


async def require_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(reusable_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    assert_admin_ip_allowed(request)
    token_data, user = await _user_from_request(request, credentials, db)
    if token_data.role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    nr = normalize_user_role(user.role)
    if nr != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin account required")
    return user


async def require_authenticated(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(reusable_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Valid JWT where token role matches the stored account role (user or admin)."""
    token_data, user = await _user_from_request(request, credentials, db)
    nr = normalize_user_role(user.role)
    if nr is None or token_data.role != nr.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token role mismatch")
    return user
