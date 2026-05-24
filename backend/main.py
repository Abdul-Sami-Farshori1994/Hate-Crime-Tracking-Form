import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

import config as app_config
from logging_config import setup_logging
from middleware.csrf import CsrfMiddleware
from middleware.max_body_size import MaxBodySizeMiddleware
from middleware.request_logging import RequestLoggingMiddleware
from routers import admin, auth, form, responses

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create SQLite schema if needed; seed default users and demo form when allowed."""
    app_config.validate_secret_key()

    import models  # noqa: F401 — register ORM tables on Base.metadata

    import auth as auth_core
    from database import Base, get_database_url, get_engine, get_session_factory, is_sqlite_url
    from dev_seed import seed_demo_form_if_empty
    from models import User, UserRole

    if is_sqlite_url(get_database_url()):
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite schema ensured (DATABASE_URL is sqlite)")

    if app_config.allow_default_user_seed():
        async with get_session_factory()() as session:
            try:
                r = await session.execute(select(func.count()).select_from(User))
                n = int(r.scalar_one() or 0)
            except Exception as exc:
                logger.warning("Could not check users table (run alembic upgrade or use SQLite?): %s", exc)
                await session.rollback()
                n = -1
            if n == 0:
                session.add_all(
                    [
                        User(
                            username="admin",
                            password_hash=auth_core.get_password_hash("admin"),
                            role=UserRole.admin,
                            is_active=True,
                        ),
                        User(
                            username="user",
                            password_hash=auth_core.get_password_hash("user"),
                            role=UserRole.user,
                            is_active=True,
                        ),
                    ]
                )
                await session.commit()
                logger.info("Seeded default users: admin/admin and user/user")
            if n >= 0:
                try:
                    await seed_demo_form_if_empty(session)
                except Exception as exc:
                    logger.warning("Could not seed demo form pages: %s", exc)
                    await session.rollback()
    else:
        logger.info("Default user seed disabled (ALLOW_DEFAULT_USER_SEED=false)")

    yield

    from database import get_engine

    await get_engine().dispose()
    logger.info("Database connection pool disposed")


_docs_url = None if app_config.is_production() else "/docs"
_redoc_url = None if app_config.is_production() else "/redoc"
_openapi_url = None if app_config.is_production() else "/openapi.json"

app = FastAPI(
    title="Hate Crime Tracking API",
    version="0.3.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

_origins = app_config.cors_origins()
if app_config.is_production() and not _origins:
    logger.warning("CORS_ORIGINS is empty in production — browsers will block cross-origin API calls")

app.add_middleware(MaxBodySizeMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=None if app_config.is_production() else r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CsrfMiddleware)

app.include_router(auth.router)
app.include_router(form.router)
app.include_router(responses.router)
app.include_router(admin.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "Unhandled error",
        extra={"path": request.url.path, "method": request.method},
    )
    detail = str(exc) if not app_config.is_production() else "Internal server error"
    response = JSONResponse(status_code=500, content={"detail": detail})
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    from database import get_session_factory

    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        logger.warning("Health check database probe failed: %s", exc)
        return {"status": "degraded", "database": "unavailable"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hate Crime Tracking API"}
