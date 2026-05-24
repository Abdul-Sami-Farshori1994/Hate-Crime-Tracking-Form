"""Export bulk builder smoke test."""

import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "true")

import auth as auth_core
import models  # noqa: F401
from database import Base, get_engine, get_session_factory
from export_bulk import build_export_payload
from models import FormPage, Question, QuestionType, Response, ResponseSession, User, UserRole
from uuid import uuid4


def test_build_export_payload_batches_answers():
    async def _run() -> None:
        import database as db_module

        db_module._engine = None
        db_module._async_session_factory = None

        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = get_session_factory()
        async with factory() as session:
            session.add(
                User(
                    username="u1",
                    password_hash=auth_core.get_password_hash("x"),
                    role=UserRole.user,
                    is_active=True,
                )
            )
            session.add(FormPage(title="P1", order_index=0))
            await session.flush()
            page_id = 1
            q = Question(
                page_id=page_id,
                question_text="Name?",
                question_type=QuestionType.text,
                is_required=True,
                order_index=0,
            )
            session.add(q)
            await session.flush()
            sid = uuid4()
            session.add(ResponseSession(session_id=sid, respondent_name="Alice", submitted_by_user_id=1))
            session.add(Response(session_id=sid, question_id=q.id, answer_value="Alice Smith"))
            await session.commit()

            payload = await build_export_payload(session, limit=10)
            assert len(payload) == 1
            assert payload[0]["respondent_name"] == "Alice"
            assert len(payload[0]["answers"]) == 1

    asyncio.run(_run())
