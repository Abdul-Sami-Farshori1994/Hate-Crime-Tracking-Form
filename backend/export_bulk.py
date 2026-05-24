"""Batch-build response export payloads (avoids per-session DB round-trips)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Question, Response, ResponseSession
from schemas import ResponseAnswerDetail
from soft_delete import active_response_session


async def build_export_payload(
    db: AsyncSession,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    """Export active sessions with answers in a constant number of queries."""
    result = await db.execute(
        select(ResponseSession)
        .where(active_response_session())
        .order_by(ResponseSession.submitted_at.desc())
        .limit(limit),
    )
    sessions = list(result.scalars().all())
    if not sessions:
        return []

    session_ids = [s.session_id for s in sessions]
    resp_result = await db.execute(
        select(Response)
        .where(Response.session_id.in_(session_ids))
        .order_by(Response.session_id, Response.question_id),
    )
    response_rows = list(resp_result.scalars().all())

    qids = {r.question_id for r in response_rows}
    qmap: dict[int, Question] = {}
    if qids:
        q_result = await db.execute(select(Question).where(Question.id.in_(qids)))
        qmap = {q.id: q for q in q_result.scalars().all()}

    by_session: dict[UUID, list[Response]] = defaultdict(list)
    for row in response_rows:
        by_session[row.session_id].append(row)

    payload: list[dict[str, Any]] = []
    for session in sessions:
        answers: list[dict[str, Any]] = []
        for it in by_session.get(session.session_id, []):
            q = qmap.get(it.question_id)
            if q is None:
                continue
            answers.append(
                ResponseAnswerDetail(
                    question_id=it.question_id,
                    question_text=q.question_text,
                    question_type=q.question_type.value,
                    answer_value=it.answer_value,
                ).model_dump(),
            )
        payload.append(
            {
                "session_id": str(session.session_id),
                "respondent_name": session.respondent_name,
                "submitted_at": session.submitted_at.isoformat(),
                "consent_recorded_at": (
                    session.consent_recorded_at.isoformat()
                    if session.consent_recorded_at is not None
                    else None
                ),
                "answers": answers,
            },
        )
    return payload
