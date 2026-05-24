"""Force isolated SQLite for all tests (before app modules load DATABASE_URL from .env)."""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "true")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("ADMIN_MFA_REQUIRED", "false")


def pytest_configure() -> None:
    """Reset cached engine so tests always use DATABASE_URL from this file."""
    import asyncio

    import database as db_module
    import models  # noqa: F401 — register all tables on Base.metadata

    db_module._engine = None
    db_module._async_session_factory = None

    async def _ensure_schema() -> None:
        from database import Base, get_engine, get_database_url, is_sqlite_url

        if is_sqlite_url(get_database_url()):
            async with get_engine().begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_ensure_schema())
    asyncio.run(_seed_test_users())


async def _seed_test_users() -> None:
    """Ensure default test accounts exist (independent of app lifespan seed flag)."""
    import auth as auth_core
    from database import get_session_factory
    from models import User, UserRole
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        for username, password, role in (
            ("admin", "admin", UserRole.admin),
            ("user", "user", UserRole.user),
        ):
            result = await session.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none() is None:
                session.add(
                    User(
                        username=username,
                        password_hash=auth_core.get_password_hash(password),
                        role=role,
                        is_active=True,
                    )
                )
        await session.commit()


import pytest


@pytest.fixture(autouse=True)
def _ensure_users_and_clear_lockouts() -> None:
    """Keep lockout state from leaking across tests sharing the in-memory DB."""
    import asyncio

    from sqlalchemy import delete

    from database import get_session_factory
    from models import LoginLockout

    async def _clear() -> None:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(delete(LoginLockout))
            await session.commit()

    asyncio.run(_seed_test_users())
    asyncio.run(_clear())
    yield
    asyncio.run(_clear())
