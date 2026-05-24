"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass

_WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me",
        "change-me-to-a-long-random-string",
        "change-me-to-a-long-random-string-for-docker",
        "secret",
        "changeme",
    }
)


def environment() -> str:
    return os.getenv("ENVIRONMENT", "development").strip().lower()


def is_production() -> bool:
    return environment() in ("production", "prod")


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    if is_production():
        return []
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


def consent_required() -> bool:
    return os.getenv("CONSENT_REQUIRED", "false").strip().lower() in ("1", "true", "yes")


def redis_url() -> str | None:
    raw = os.getenv("REDIS_URL", "").strip()
    return raw or None


def max_request_body_bytes() -> int:
    """Maximum JSON body size for POST/PUT/PATCH (default 1 MiB)."""
    default = 1_048_576
    raw = os.getenv("MAX_REQUEST_BODY_BYTES", str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(64_000, min(value, 10_485_760))


def allow_default_user_seed() -> bool:
    default = "false" if is_production() else "true"
    return os.getenv("ALLOW_DEFAULT_USER_SEED", default).strip().lower() in ("1", "true", "yes")


def log_level() -> str:
    default = "INFO" if is_production() else "DEBUG"
    return os.getenv("LOG_LEVEL", default).strip().upper()


def log_format_json() -> bool:
    """Use JSON logs in production by default; plain text in development."""
    raw = os.getenv("LOG_FORMAT", "").strip().lower()
    if raw in ("json", "text"):
        return raw == "json"
    return is_production()


def public_service_unavailable_detail(exc: BaseException | None = None) -> str:
    """Client-safe message for 503 responses (no internals in production)."""
    if is_production():
        return "Service temporarily unavailable"
    if exc is None:
        return "Service temporarily unavailable"
    return f"{type(exc).__name__}: {exc!s}"


def secret_key_bytes() -> bytes:
    return os.getenv("SECRET_KEY", "").strip().encode("utf-8")


def use_cookie_auth() -> bool:
    default = "true"
    return os.getenv("USE_COOKIE_AUTH", default).strip().lower() in ("1", "true", "yes")


def cookie_secure() -> bool:
    raw = os.getenv("COOKIE_SECURE", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return is_production()


def access_token_expire_minutes(role: str) -> int:
    if role == "admin":
        raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES_ADMIN", "15").strip()
    else:
        raw = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30").strip()
    try:
        return max(5, min(int(raw), 24 * 60))
    except ValueError:
        return 15 if role == "admin" else 30


def refresh_token_expire_days() -> int:
    raw = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7").strip()
    try:
        return max(1, min(int(raw), 90))
    except ValueError:
        return 7


def mfa_pending_expire_minutes() -> int:
    raw = os.getenv("MFA_PENDING_EXPIRE_MINUTES", "10").strip()
    try:
        return max(3, min(int(raw), 60))
    except ValueError:
        return 10


def admin_mfa_required() -> bool:
    default = "true" if is_production() else "false"
    return os.getenv("ADMIN_MFA_REQUIRED", default).strip().lower() in ("1", "true", "yes")


def mfa_issuer_name() -> str:
    return os.getenv("MFA_ISSUER_NAME", "Hate Crime Tracking Form").strip() or "Hate Crime Tracking Form"


def admin_ip_allowlist() -> list[str]:
    raw = os.getenv("ADMIN_IP_ALLOWLIST", "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def admin_login_webhook_url() -> str | None:
    raw = os.getenv("ADMIN_LOGIN_WEBHOOK_URL", "").strip()
    return raw or None


def validate_secret_key() -> None:
    key = os.getenv("SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing required environment variable: SECRET_KEY")
    if key.lower() in _WEAK_SECRET_KEYS or len(key) < 32:
        if is_production():
            raise RuntimeError(
                "SECRET_KEY must be at least 32 characters and not a default value in production",
            )
