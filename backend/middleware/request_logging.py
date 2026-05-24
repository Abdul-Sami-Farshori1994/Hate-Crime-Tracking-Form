"""Request ID propagation and structured access logs."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import config as app_config
from logging_config import request_id_ctx

logger = logging.getLogger("hatecrime.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming.strip() if incoming else str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        client_ip = request.client.host if request.client else "unknown"
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            try:
                logger.info(
                    "request completed",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "environment": app_config.environment(),
                    },
                )
            finally:
                request_id_ctx.reset(token)
