"""Optional admin API IP allowlist."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

import config as app_config
from login_alerts import client_ip


def assert_admin_ip_allowed(request: Request) -> None:
    allowed = app_config.admin_ip_allowlist()
    if not allowed:
        return
    ip = client_ip(request)
    if ip not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied from this network",
        )
