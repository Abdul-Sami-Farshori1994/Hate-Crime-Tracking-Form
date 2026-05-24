import json
from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response as HttpResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

import auth as auth_core
import config as app_config
from analytics_aggregate import build_question_analytics, fetch_answer_rows, fetch_total_sessions
from soft_delete import active_form_page, active_question, active_response_session, mark_deleted
from answer_normalize import AnswerValidationError, normalize_answer
from audit_log import record_audit
from database import get_db
from export_bulk import build_export_payload
from export_excel import build_export_xlsm, fetch_ordered_questions
from form_flow import (
    SubmitValidationError,
    load_submit_flow_context,
    submit_answer_ids,
    validate_path_answers,
)
from rate_limit import admin_read_limit, admin_write_limit, submit_limit
from models import FormPage, Question, QuestionType, Response, ResponseSession, User
from respondent_name import respondent_name_from_answers
from schemas import (
    AnalyticsBar,
    AnalyticsQuestionBlock,
    AnalyticsResponse,
    ResponseAnswerDetail,
    ResponseSessionDetail,
    ResponseSessionListResponse,
    ResponseSessionSummary,
    ResponseSubmitRequest,
)

router = APIRouter(prefix="/responses", tags=["responses"])


def _encode_cursor(submitted_at: datetime, session_id: UUID) -> str:
    return f"{submitted_at.isoformat()}|{session_id}"


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        at_str, sid_str = cursor.split("|", 1)
        return datetime.fromisoformat(at_str), UUID(sid_str)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc


async def _answer_counts_for_sessions(db: AsyncSession, session_ids: list[UUID]) -> dict[UUID, int]:
    if not session_ids:
        return {}
    result = await db.execute(
        select(Response.session_id, func.count())
        .where(Response.session_id.in_(session_ids))
        .group_by(Response.session_id)
    )
    return {sid: int(cnt) for sid, cnt in result.all()}


async def _build_session_detail(db: AsyncSession, session_id: UUID) -> ResponseSessionDetail:
    session_row = await db.get(ResponseSession, session_id)
    if session_row is not None and session_row.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response session not found")
    result = await db.execute(
        select(Response).where(Response.session_id == session_id).order_by(Response.question_id)
    )
    items = list(result.scalars().all())
    if not items and session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response session not found")

    qmap: dict[int, Question] = {}
    if items:
        qids = {r.question_id for r in items}
        q_result = await db.execute(select(Question).where(Question.id.in_(qids)))
        qmap = {q.id: q for q in q_result.scalars().all()}

    submitted_at = session_row.submitted_at if session_row is not None else max(i.submitted_at for i in items)
    answers: list[ResponseAnswerDetail] = []
    for it in items:
        q = qmap.get(it.question_id)
        if q is None:
            continue
        answers.append(
            ResponseAnswerDetail(
                question_id=it.question_id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                answer_value=it.answer_value,
            )
        )

    return ResponseSessionDetail(
        session_id=str(session_id),
        respondent_name=session_row.respondent_name if session_row is not None else None,
        submitted_at=submitted_at,
        answers=answers,
    )


def _validate_and_normalize_answer(question: Question, raw: str) -> str:
    try:
        return normalize_answer(question, raw, strict=True)
    except AnswerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/submit")
async def submit_responses(
    body: ResponseSubmitRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(auth_core.require_user)],
    _rate: None = submit_limit,
) -> dict[str, Any]:
    if not body.answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided")

    ordered, branch_map = await load_submit_flow_context(db)
    if not ordered:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Form has no questions")

    answers_by_id: dict[int, object] = {a.question_id: a.answer_value for a in body.answers}
    try:
        path_ids = validate_path_answers(ordered, branch_map, answers_by_id)
    except SubmitValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    questions = {q.id: q for q in ordered if q.id in set(path_ids)}
    store_ids = submit_answer_ids(path_ids, ordered, answers_by_id)
    submitted_ids = set(answers_by_id.keys())
    store_id_set = set(store_ids)
    if submitted_ids != store_id_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission must include each required answer on your path (optional questions may be omitted if left blank)",
        )

    normalized: dict[int, str] = {}
    for qid in store_ids:
        q = questions[qid]
        normalized[qid] = _validate_and_normalize_answer(q, str(answers_by_id[qid]))

    if app_config.consent_required() and not body.consent_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent is required before submitting this form",
        )

    session_id = uuid4()
    respondent_name = respondent_name_from_answers(questions, normalized)
    consent_at = (
        datetime.now(timezone.utc)
        if body.consent_acknowledged or app_config.consent_required()
        else None
    )
    db.add(
        ResponseSession(
            session_id=session_id,
            respondent_name=respondent_name,
            submitted_by_user_id=user.id,
            consent_recorded_at=consent_at,
        )
    )
    for qid, value in normalized.items():
        db.add(
            Response(
                session_id=session_id,
                question_id=qid,
                answer_value=value,
            )
        )
    await record_audit(
        db,
        user=user,
        action="submit_response",
        resource_type="response_session",
        resource_id=str(session_id),
        detail={
            "answer_count": len(normalized),
            "consent_recorded": consent_at is not None,
        },
        request=request,
    )
    await db.commit()
    return {
        "session_id": str(session_id),
        "submitted": True,
        "respondent_name": respondent_name,
    }


@router.get("/", response_model=ResponseSessionListResponse)
async def list_response_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
    limit: Annotated[int, Query(ge=1, le=50)] = 15,
    cursor: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> ResponseSessionListResponse:
    search = q.strip() if q else None
    filters = [active_response_session()]
    if search:
        filters.append(ResponseSession.respondent_name.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(ResponseSession)
    for clause in filters:
        count_stmt = count_stmt.where(clause)
    total_result = await db.execute(count_stmt)
    total_count = int(total_result.scalar_one() or 0)

    stmt = select(ResponseSession).order_by(
        ResponseSession.submitted_at.desc(),
        ResponseSession.session_id.desc(),
    )
    for clause in filters:
        stmt = stmt.where(clause)
    if cursor is not None:
        cursor_at, cursor_sid = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                ResponseSession.submitted_at < cursor_at,
                and_(
                    ResponseSession.submitted_at == cursor_at,
                    ResponseSession.session_id < cursor_sid,
                ),
            )
        )

    result = await db.execute(stmt.limit(limit + 1))
    sessions = list(result.scalars().all())

    next_cursor: str | None = None
    if len(sessions) > limit:
        sessions = sessions[:limit]
        last = sessions[-1]
        next_cursor = _encode_cursor(last.submitted_at, last.session_id)

    count_map = await _answer_counts_for_sessions(db, [s.session_id for s in sessions])
    items = [
        ResponseSessionSummary(
            session_id=str(s.session_id),
            respondent_name=s.respondent_name,
            submitted_at=s.submitted_at,
            answer_count=count_map.get(s.session_id, 0),
        )
        for s in sessions
    ]
    return ResponseSessionListResponse(items=items, next_cursor=next_cursor, total_count=total_count)


PIE_CHART_MAX_OPTIONS = 5
EXPORT_MAX_SESSIONS = 5000


def _pick_chart_type(qt: QuestionType, breakdown_len: int) -> Literal["summary", "pie", "bar"]:
    if qt in (QuestionType.text, QuestionType.date):
        return "summary"
    if qt == QuestionType.rating:
        return "bar"
    if qt == QuestionType.checkbox:
        return "bar"
    if qt in (QuestionType.radio, QuestionType.select):
        return "pie" if breakdown_len <= PIE_CHART_MAX_OPTIONS else "bar"
    return "summary"


@router.get("/export")
async def export_response_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    request: Request,
    __rate: None = admin_read_limit,
) -> HttpResponse:
    """Export active submissions as Excel (.xlsm) for reporting."""
    payload = await build_export_payload(db, limit=EXPORT_MAX_SESSIONS)
    questions = await fetch_ordered_questions(db)
    content = build_export_xlsm(payload, questions)
    exported_count = len(payload)

    await record_audit(
        db,
        user=admin,
        action="export_responses",
        resource_type="responses",
        resource_id="bulk",
        detail={"count": exported_count, "format": "xlsm"},
        request=request,
    )
    await db.commit()

    filename = f"hatecrime-export-{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsm"
    return HttpResponse(
        content=content,
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Exported-Count": str(exported_count),
        },
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def responses_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> AnalyticsResponse:
    q_result = await db.execute(
        select(Question)
        .join(FormPage, Question.page_id == FormPage.id)
        .where(active_form_page(), active_question())
        .order_by(FormPage.order_index, Question.order_index, Question.id),
    )
    questions = list(q_result.scalars().all())
    total_sessions = await fetch_total_sessions(db)
    answer_rows = await fetch_answer_rows(db)
    stats = build_question_analytics(questions, answer_rows)

    blocks: list[AnalyticsQuestionBlock] = []
    for index, q in enumerate(questions, start=1):
        qt = q.question_type
        breakdown, total, latest = stats.get(q.id, ([], 0, []))
        chart_type = _pick_chart_type(qt, len(breakdown))
        blocks.append(
            AnalyticsQuestionBlock(
                question_id=q.id,
                question_text=q.question_text,
                question_type=qt.value,
                question_number=index,
                chart_type=chart_type,
                total_responses=total,
                breakdown=breakdown,
                latest_responses=latest,
            ),
        )
    return AnalyticsResponse(questions=blocks, total_sessions=total_sessions)


@router.get("/{session_id}", response_model=ResponseSessionDetail)
async def get_response_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> ResponseSessionDetail:
    return await _build_session_detail(db, session_id)


@router.delete("/{session_id}")
async def soft_delete_response_session(
    session_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> dict[str, Any]:
    """Soft-delete a submission (hidden from lists and analytics; answers kept in DB)."""
    session = await db.get(ResponseSession, session_id)
    if session is None or session.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response session not found")
    mark_deleted(session, deleted_by_id=admin.id)
    await record_audit(
        db,
        user=admin,
        action="soft_delete_response",
        resource_type="response_session",
        resource_id=str(session_id),
        request=request,
    )
    await db.commit()
    return {"session_id": str(session_id), "deleted": True}
