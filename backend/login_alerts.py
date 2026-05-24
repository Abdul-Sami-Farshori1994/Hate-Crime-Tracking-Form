"""Notify on admin login from a new IP (audit + optional webhook)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

import config as app_config
from audit_log import record_audit
from models import User

logger = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    if request.client:
        return request.client.host[:45]
    return "unknown"


async def record_admin_login(
    db: AsyncSession,
    *,
    user: User,
    request: Request,
) -> None:
    ip = client_ip(request)
    previous = (getattr(user, "last_login_ip", None) or "").strip()
    is_new_ip = bool(previous and previous != ip)
    user.last_login_ip = ip

    detail: dict[str, Any] = {"ip": ip, "new_ip": is_new_ip}
    if is_new_ip:
        detail["previous_ip"] = previous

    await record_audit(
        db,
        user=user,
        action="admin_login_new_ip" if is_new_ip else "login_success",
        resource_type="auth",
        resource_id="admin",
        detail=detail,
        request=request,
    )

    if is_new_ip:
        await _post_webhook(
            {
                "event": "admin_login_new_ip",
                "username": user.username,
                "ip": ip,
                "previous_ip": previous,
            }
        )


async def _post_webhook(payload: dict[str, Any]) -> None:
    url = app_config.admin_login_webhook_url()
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload)
    except Exception:
        logger.exception("Admin login webhook failed")
