"""Unit tests for login lockout helpers."""

import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ["LOGIN_MAX_FAILURES"] = "2"
os.environ["LOGIN_LOCKOUT_MINUTES"] = "15"

import pytest

import models  # noqa: F401
from database import Base, get_engine, get_session_factory
from fastapi import HTTPException
from login_lockout import assert_not_locked, clear_login_lockout, record_failed_login


def test_clear_lockout_resets_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "2")

    async def _run() -> None:
        import database as db_module

        db_module._engine = None
        db_module._async_session_factory = None

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = get_session_factory()
        async with factory() as session:
            await record_failed_login(session, "alice")
            await record_failed_login(session, "alice")
            await session.commit()

            try:
                await assert_not_locked(session, "alice")
                raise AssertionError("expected lockout")
            except HTTPException as exc:
                assert exc.status_code == 429

            await clear_login_lockout(session, "alice")
            await session.commit()
            await assert_not_locked(session, "alice")

    asyncio.run(_run())
