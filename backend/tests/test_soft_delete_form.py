"""Soft-delete form pages and questions."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from database import get_session_factory
from models import FormPage, Question, QuestionType, User, UserRole
from routers import form as form_router
from soft_delete import active_form_page, active_question


async def _test_soft_delete_page_hides_questions() -> None:
    async with get_session_factory()() as db:
        admin = User(
            username="admin-soft-del",
            password_hash="x",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        page = FormPage(title="Section A", order_index=0)
        other = FormPage(title="Section B", order_index=1)
        db.add_all([page, other])
        await db.flush()

        q = Question(
            page_id=page.id,
            question_text="Q1",
            question_type=QuestionType.text,
            order_index=0,
            ms_forms_id="abc123",
        )
        db.add(q)
        await db.commit()

        await form_router.delete_page(page.id, request=None, db=db, admin=admin, __rate=None)
        await db.refresh(page)
        await db.refresh(q)

        assert page.deleted_at is not None
        assert page.deleted_by_id == admin.id
        assert q.deleted_at is not None

        visible_pages = (
            await db.execute(select(FormPage).where(active_form_page()))
        ).scalars().all()
        assert len(visible_pages) == 1
        assert visible_pages[0].id == other.id

        visible_questions = (
            await db.execute(select(Question).where(active_question()))
        ).scalars().all()
        assert visible_questions == []


async def _test_soft_delete_question_keeps_row() -> None:
    async with get_session_factory()() as db:
        admin = User(
            username="admin-soft-q",
            password_hash="x",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        page = FormPage(title="Only", order_index=0)
        db.add(page)
        await db.flush()

        q = Question(
            page_id=page.id,
            question_text="Hidden later",
            question_type=QuestionType.text,
            order_index=0,
            ms_forms_id="def456",
        )
        db.add(q)
        await db.commit()

        await form_router.delete_question(q.id, request=None, db=db, admin=admin, __rate=None)
        await db.refresh(q)

        assert q.deleted_at is not None
        row = await db.get(Question, q.id)
        assert row is not None
        assert row.deleted_at is not None


async def _test_restore_page_unhides_questions() -> None:
    async with get_session_factory()() as db:
        admin = User(
            username="admin-restore-page",
            password_hash="x",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        page = FormPage(title="Section A", order_index=0)
        other = FormPage(title="Section B", order_index=1)
        db.add_all([page, other])
        await db.flush()

        q = Question(
            page_id=page.id,
            question_text="Q1",
            question_type=QuestionType.text,
            order_index=0,
            ms_forms_id="restore123",
        )
        db.add(q)
        await db.commit()

        await form_router.delete_page(page.id, request=None, db=db, admin=admin, __rate=None)
        await form_router.restore_page(page.id, request=None, db=db, admin=admin, __rate=None)
        await db.refresh(page)
        await db.refresh(q)

        assert page.deleted_at is None
        assert q.deleted_at is None


async def _test_restore_question() -> None:
    async with get_session_factory()() as db:
        admin = User(
            username="admin-restore-q",
            password_hash="x",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)
        await db.flush()

        page = FormPage(title="Only", order_index=0)
        db.add(page)
        await db.flush()

        q = Question(
            page_id=page.id,
            question_text="Back again",
            question_type=QuestionType.text,
            order_index=0,
            ms_forms_id="restore456",
        )
        db.add(q)
        await db.commit()

        await form_router.delete_question(q.id, request=None, db=db, admin=admin, __rate=None)
        await form_router.restore_question(q.id, request=None, db=db, admin=admin, __rate=None)
        await db.refresh(q)

        assert q.deleted_at is None


def test_soft_delete_page_hides_questions() -> None:
    asyncio.run(_test_soft_delete_page_hides_questions())


def test_soft_delete_question_keeps_row() -> None:
    asyncio.run(_test_soft_delete_question_keeps_row())


def test_restore_page_unhides_questions() -> None:
    asyncio.run(_test_restore_page_unhides_questions())


def test_restore_question() -> None:
    asyncio.run(_test_restore_question())
