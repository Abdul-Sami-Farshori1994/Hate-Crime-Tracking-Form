"""HttpOnly session cookies and CSRF double-submit token."""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import Request, Response
from jose import JWTError

import config as app_config

ACCESS_COOKIE = "hc_access"
REFRESH_COOKIE = "hc_refresh"
CSRF_COOKIE = "hc_csrf"
MFA_PENDING_COOKIE = "hc_mfa_pending"
MFA_SETUP_COOKIE = "hc_mfa_setup"


def _cookie_kwargs(*, max_age: int | None) -> dict[str, Any]:
    secure = app_config.cookie_secure()
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "path": "/",
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    return kwargs


def issue_csrf_token(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        secure=app_config.cookie_secure(),
        samesite="lax",
        path="/",
        max_age=app_config.refresh_token_expire_days() * 86400,
    )
    return token


def set_session_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    role: str,
) -> None:
    access_max = app_config.access_token_expire_minutes(role) * 60
    refresh_max = app_config.refresh_token_expire_days() * 86400
    response.set_cookie(ACCESS_COOKIE, access_token, **_cookie_kwargs(max_age=access_max))
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        **_cookie_kwargs(max_age=refresh_max),
    )
    issue_csrf_token(response)


def clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE, MFA_PENDING_COOKIE, MFA_SETUP_COOKIE):
        response.delete_cookie(name, path="/")


def set_mfa_pending_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        MFA_PENDING_COOKIE,
        token,
        **_cookie_kwargs(max_age=app_config.mfa_pending_expire_minutes() * 60),
    )


def set_mfa_setup_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        MFA_SETUP_COOKIE,
        token,
        **_cookie_kwargs(max_age=app_config.mfa_pending_expire_minutes() * 60),
    )


def clear_mfa_cookies(response: Response) -> None:
    response.delete_cookie(MFA_PENDING_COOKIE, path="/")
    response.delete_cookie(MFA_SETUP_COOKIE, path="/")


def get_access_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(ACCESS_COOKIE)
    if cookie:
        return cookie.strip()
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def get_refresh_token_from_request(request: Request) -> str | None:
    cookie = request.cookies.get(REFRESH_COOKIE)
    if cookie:
        return cookie.strip()
    return None


def get_mfa_pending_token(request: Request) -> str | None:
    return request.cookies.get(MFA_PENDING_COOKIE)


def get_mfa_setup_token(request: Request) -> str | None:
    return request.cookies.get(MFA_SETUP_COOKIE)


def decode_mfa_pending_token(token: str) -> dict[str, Any]:
    import auth as auth_core

    payload = auth_core.decode_token(token)
    if payload.get("typ") != "mfa_pending":
        raise JWTError("Invalid MFA pending token")
    return payload
