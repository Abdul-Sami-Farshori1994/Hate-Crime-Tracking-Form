"""Phase 1 security hardening tests."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "true")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from database import get_session_factory
from main import app
from models import AuditEvent

client = TestClient(app)


def test_login_password_max_length_rejected():
    response = client.post(
        "/auth/login",
        json={"username": "user", "password": "x" * 129},
    )
    assert response.status_code == 422


def test_request_body_too_large_by_content_length():
    response = client.post(
        "/auth/login",
        content=b'{"username":"user","password":"x"}',
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(2_000_000),
        },
    )
    assert response.status_code == 413


def test_login_lockout_after_repeated_failures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "3")
    username = "lockout_probe_user"
    for _ in range(3):
        r = client.post("/auth/login", json={"username": username, "password": "wrong"})
        assert r.status_code == 401

    locked = client.post("/auth/login", json={"username": username, "password": "wrong"})
    assert locked.status_code == 429


async def _fetch_audit_actions() -> list[str]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AuditEvent.action).order_by(AuditEvent.id.desc()).limit(20)
        )
        return [row[0] for row in result.all()]


def test_login_failure_writes_audit_event():
    import asyncio

    client.post("/auth/admin/login", json={"username": "nobody", "password": "bad"})
    actions = asyncio.run(_fetch_audit_actions())
    assert "login_failed" in actions


def test_form_pages_endpoints_exist():
    assert client.get("/form/pages").status_code == 401
