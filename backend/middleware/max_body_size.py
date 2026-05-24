"""Reject oversized request bodies before handlers run."""

from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import config as app_config


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        max_bytes = app_config.max_request_body_bytes()
        if request.method in ("POST", "PUT", "PATCH"):
            raw = request.headers.get("content-length")
            if raw:
                try:
                    length = int(raw)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header"},
                    )
                if length > max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
        return await call_next(request)
