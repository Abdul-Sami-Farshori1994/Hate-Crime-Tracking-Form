"""Shared soft-delete helpers for models with deleted_at / deleted_by_id."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ColumnElement

from models import FormPage, Question, ResponseSession


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mark_deleted(entity: object, *, deleted_by_id: int | None) -> None:
    entity.deleted_at = utc_now()  # type: ignore[attr-defined]
    if hasattr(entity, "deleted_by_id"):
        entity.deleted_by_id = deleted_by_id  # type: ignore[attr-defined]


def restore(entity: object) -> None:
    entity.deleted_at = None  # type: ignore[attr-defined]
    if hasattr(entity, "deleted_by_id"):
        entity.deleted_by_id = None  # type: ignore[attr-defined]


def active_response_session() -> ColumnElement[bool]:
    return ResponseSession.deleted_at.is_(None)


def active_form_page() -> ColumnElement[bool]:
    return FormPage.deleted_at.is_(None)


def active_question() -> ColumnElement[bool]:
    return Question.deleted_at.is_(None)
