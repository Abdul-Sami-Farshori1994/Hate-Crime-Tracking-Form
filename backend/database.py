import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from dotenv import load_dotenv

    # Prefer values from backend/.env so local SQLite/Postgres wins over a stale shell DATABASE_URL.
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass
from sqlalchemy.orm import DeclarativeBase

_engine = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def get_database_url() -> str:
    """Read DB URL from env (PostgreSQL or SQLite for local dev without Docker)."""
    return _require_env("DATABASE_URL")


def is_sqlite_url(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith("sqlite:") or u.startswith("sqlite+")


def normalize_async_database_url(url: str) -> str:
    """Normalize to an async SQLAlchemy URL (asyncpg or aiosqlite)."""
    u = url.strip()
    if u.startswith("postgresql+asyncpg://"):
        return u
    if u.startswith("postgresql://"):
        return "postgresql+asyncpg://" + u[len("postgresql://") :]
    if u.startswith("postgres://"):
        return "postgresql+asyncpg://" + u[len("postgres://") :]
    if u.startswith("sqlite+aiosqlite://"):
        return u
    if u.startswith("sqlite:///"):
        return "sqlite+aiosqlite:///" + u[len("sqlite:///") :]
    raise RuntimeError(
        "DATABASE_URL must be PostgreSQL (postgresql://...) or SQLite (sqlite:///... or sqlite+aiosqlite://...)"
    )


def get_sync_database_url_for_alembic() -> str:
    """Alembic uses a synchronous driver (psycopg2 or sqlite3)."""
    url = get_database_url().strip()
    if is_sqlite_url(url):
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        if url.startswith("sqlite:///"):
            return url
        raise RuntimeError("SQLite DATABASE_URL must use sqlite:///... or sqlite+aiosqlite:///...")
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgresql://"):
        return url
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    raise RuntimeError("DATABASE_URL must be PostgreSQL or SQLite")


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            normalize_async_database_url(get_database_url()),
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        await session.close()
