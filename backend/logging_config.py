"""Structured logging to stdout (JSON in production, plain text in development)."""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

import config as app_config

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_REDACT_PATTERNS = (
    re.compile(
        r"(?i)(password|passwd|secret|authorization|access_token|refresh_token)\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
)


class RequestContextFilter(logging.Filter):
    """Attach request_id from context to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()  # type: ignore[attr-defined]
        return True


class RedactSensitiveFilter(logging.Filter):
    """Redact obvious secrets if they appear in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for pattern in _REDACT_PATTERNS:
            redacted = pattern.sub("***", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line for log aggregators (CloudWatch, Datadog, Loki, etc.)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key in (
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "environment",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure root and uvicorn loggers once at process start."""
    level_name = app_config.log_level()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if app_config.log_format_json():
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )

    handler.addFilter(RequestContextFilter())
    handler.addFilter(RedactSensitiveFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_log = logging.getLogger(name)
        uv_log.handlers.clear()
        uv_log.propagate = True
        uv_log.setLevel(level)

    logging.getLogger(__name__).debug(
        "Logging configured",
        extra={"environment": app_config.environment(), "log_level": level_name},
    )
