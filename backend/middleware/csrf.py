"""CSRF protection for cookie-based sessions (double-submit cookie)."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import config as app_config
from cookie_auth import ACCESS_COOKIE, CSRF_COOKIE

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_EXEMPT_PREFIXES = (
    "/auth/login",
    "/auth/admin/login",
    "/auth/admin/mfa/",
    "/auth/refresh",
    "/auth/logout",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not app_config.use_cookie_auth():
            return await call_next(request)

        if request.method in _SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        if path == "/" or any(path.startswith(prefix) for prefix in _CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        if not request.cookies.get(ACCESS_COOKIE):
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get("X-CSRF-Token", "").strip()
        if not cookie_token or not header_token or cookie_token != header_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)
