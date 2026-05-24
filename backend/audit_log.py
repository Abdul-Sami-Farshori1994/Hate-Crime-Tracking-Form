"""Record admin and security-sensitive actions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models import AuditEvent, User

logger = logging.getLogger(__name__)


def _client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    if request.client:
        return request.client.host[:45]
    return None


async def record_audit(
    db: AsyncSession,
    *,
    user: User | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    row = AuditEvent(
        user_id=user.id if user else None,
        action=action[:64],
        resource_type=resource_type[:64],
        resource_id=(resource_id[:128] if resource_id else None),
        detail=detail,
        ip_address=_client_ip(request),
    )
    db.add(row)
    try:
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit event", extra={"action": action})
