import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import auth as auth_core
from audit_log import record_audit
from database import get_db
from form_flow import build_branch_map, rules_from_rows, sort_questions
from rate_limit import admin_read_limit, admin_write_limit, form_read_limit
from models import FormPage, Question, QuestionBranchRule, QuestionType, User
from soft_delete import active_form_page, active_question, mark_deleted, restore
from schemas import (
    BranchRulesReplaceRequest,
    FormFlowResponse,
    FormPageCreate,
    FormPageEditorRead,
    FormPageRead,
    FormPageUpdate,
    HiddenFormStructureRead,
    HiddenQuestionSummary,
    HiddenSectionSummary,
    QuestionBranchRead,
    QuestionBranchRuleAdminRead,
    QuestionCreate,
    QuestionEditorRead,
    QuestionRead,
    QuestionReorderRequest,
    QuestionUpdate,
)

router = APIRouter(prefix="/form", tags=["form"])

BRANCHING_SOURCE_TYPES = frozenset({QuestionType.radio, QuestionType.select, QuestionType.checkbox})


def ensure_ms_forms_id(question: Question) -> None:
    if not question.ms_forms_id:
        question.ms_forms_id = uuid.uuid4().hex


STAGING_PAGE_TITLE = "_staging"


def _page_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")


def _question_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")


async def _get_active_page(db: AsyncSession, page_id: int) -> FormPage:
    page = await db.get(FormPage, page_id)
    if page is None or page.deleted_at is not None:
        raise _page_not_found()
    return page


async def _get_active_question(db: AsyncSession, question_id: int) -> Question:
    question = await db.get(Question, question_id)
    if question is None or question.deleted_at is not None:
        raise _question_not_found()
    return question


async def _get_hidden_page(db: AsyncSession, page_id: int) -> FormPage:
    page = await db.get(FormPage, page_id)
    if page is None or page.deleted_at is None:
        raise _page_not_found()
    return page


async def _get_hidden_question(db: AsyncSession, question_id: int) -> Question:
    question = await db.get(Question, question_id)
    if question is None or question.deleted_at is None:
        raise _question_not_found()
    return question


async def build_hidden_structure(db: AsyncSession) -> HiddenFormStructureRead:
    hidden_pages = list(
        (
            await db.execute(
                select(FormPage)
                .where(FormPage.deleted_at.is_not(None), FormPage.title != STAGING_PAGE_TITLE)
                .order_by(FormPage.order_index, FormPage.id)
            )
        ).scalars().all()
    )
    sections: list[HiddenSectionSummary] = []
    for page in hidden_pages:
        count_result = await db.execute(
            select(func.count()).select_from(Question).where(Question.page_id == page.id)
        )
        sections.append(
            HiddenSectionSummary(
                id=page.id,
                title=page.title,
                description=page.description,
                order_index=page.order_index,
                question_count=int(count_result.scalar_one()),
            )
        )

    q_result = await db.execute(
        select(Question, FormPage.title)
        .join(FormPage, Question.page_id == FormPage.id)
        .where(Question.deleted_at.is_not(None), active_form_page())
        .order_by(FormPage.order_index, Question.order_index, Question.id)
    )
    questions = [
        HiddenQuestionSummary(
            id=q.id,
            page_id=q.page_id,
            page_title=page_title,
            question_text=q.question_text,
            question_type=q.question_type,
        )
        for q, page_title in q_result.all()
    ]
    return HiddenFormStructureRead(sections=sections, questions=questions)


async def _reindex_active_pages(db: AsyncSession) -> None:
    pages = list(
        (
            await db.execute(
                select(FormPage)
                .where(active_form_page())
                .order_by(FormPage.order_index, FormPage.id)
            )
        ).scalars().all()
    )
    for i, p in enumerate(pages):
        p.order_index = i


async def _audit_form_change(
    db: AsyncSession,
    *,
    admin: User,
    request: Request | None,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: dict | None = None,
) -> None:
    await record_audit(
        db,
        user=admin,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        request=request,
    )


async def sync_global_order(db: AsyncSession) -> None:
    """Align global_order with page order + order_index so the live form matches the editor."""
    pages = list(
        (
            await db.execute(
                select(FormPage)
                .where(active_form_page())
                .order_by(FormPage.order_index, FormPage.id)
            )
        ).scalars().all()
    )
    n = 0
    for page in pages:
        if page.title == STAGING_PAGE_TITLE:
            continue
        result = await db.execute(
            select(Question)
            .where(Question.page_id == page.id, active_question())
            .order_by(Question.order_index, Question.id)
        )
        for question in result.scalars().all():
            question.global_order = n
            n += 1


async def build_editor_pages(db: AsyncSession) -> list[FormPageEditorRead]:
    pages_result = await db.execute(
        select(FormPage)
        .where(FormPage.title != STAGING_PAGE_TITLE)
        .order_by(FormPage.order_index, FormPage.id)
    )
    pages = list(pages_result.scalars().all())
    if not pages:
        return []

    page_ids = [p.id for p in pages]
    q_result = await db.execute(
        select(Question)
        .where(Question.page_id.in_(page_ids))
        .options(selectinload(Question.branch_rules))
        .order_by(Question.order_index, Question.id)
    )
    questions = list(q_result.scalars().all())
    by_id = {q.id: q for q in questions}

    by_page: dict[int, list[QuestionEditorRead]] = {pid: [] for pid in page_ids}
    page_hidden = {p.id: p.deleted_at is not None for p in pages}
    for q in questions:
        rules_out = [
            QuestionBranchRuleAdminRead(
                id=rule.id,
                option_value=rule.option_value,
                target_question_id=rule.target_question_id,
                target_question_text=(
                    by_id[rule.target_question_id].question_text[:120]
                    if rule.target_question_id and rule.target_question_id in by_id
                    else None
                ),
            )
            for rule in sorted(q.branch_rules, key=lambda r: r.id)
        ]
        q_hidden = q.deleted_at is not None or page_hidden.get(q.page_id, False)
        by_page[q.page_id].append(
            QuestionEditorRead(
                id=q.id,
                page_id=q.page_id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                order_index=q.order_index,
                ms_forms_id=q.ms_forms_id,
                help_text=q.help_text,
                global_order=q.global_order,
                branch_rules=rules_out,
                is_hidden=q_hidden,
            )
        )

    return [
        FormPageEditorRead(
            id=p.id,
            title=p.title,
            description=p.description,
            order_index=p.order_index,
            questions=by_page.get(p.id, []),
            is_hidden=p.deleted_at is not None,
        )
        for p in pages
    ]


@router.get("/flow", response_model=FormFlowResponse)
async def get_form_flow(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_authenticated)],
    __rate: None = form_read_limit,
) -> FormFlowResponse:
    """Full form definition with branch rules for the respondent flow."""
    pages = list(
        (
            await db.execute(
                select(FormPage).where(active_form_page()).order_by(FormPage.order_index)
            )
        ).scalars().all()
    )
    questions = list(
        (
            await db.execute(
                select(Question)
                .where(active_question())
                .order_by(
                    Question.global_order.nulls_last(),
                    Question.page_id,
                    Question.order_index,
                    Question.id,
                )
            )
        ).scalars().all()
    )
    rules_result = await db.execute(
        select(QuestionBranchRule, Question.ms_forms_id)
        .join(Question, QuestionBranchRule.source_question_id == Question.id)
        .where(active_question())
        .order_by(QuestionBranchRule.id)
    )
    questions = sort_questions(questions, pages)
    branch_map = build_branch_map(rules_from_rows(list(rules_result.all())))
    branches = [
        QuestionBranchRead(
            source_ms_forms_id=source_ms,
            option_value=option_value,
            target_ms_forms_id=target_ms,
        )
        for source_ms, options in branch_map.items()
        for option_value, target_ms in options.items()
    ]
    entry_ms = questions[0].ms_forms_id if questions else None
    return FormFlowResponse(
        pages=pages,
        questions=questions,
        branches=branches,
        entry_ms_forms_id=entry_ms,
    )


@router.get("/pages", response_model=list[FormPageRead])
async def list_pages(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_authenticated)],
    __rate: None = form_read_limit,
) -> list[FormPage]:
    result = await db.execute(
        select(FormPage).where(active_form_page()).order_by(FormPage.order_index)
    )
    return list(result.scalars().all())


@router.get("/hidden-structure", response_model=HiddenFormStructureRead)
async def get_hidden_form_structure(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> HiddenFormStructureRead:
    """Sections and questions hidden from the live form (admin restore list)."""
    return await build_hidden_structure(db)


@router.get("/structure", response_model=list[FormPageEditorRead])
async def get_form_structure(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> list[FormPageEditorRead]:
    """All pages with nested questions and branch rules (admin form editor)."""
    return await build_editor_pages(db)


@router.post("/pages", response_model=FormPageRead, status_code=status.HTTP_201_CREATED)
async def create_page(
    body: FormPageCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> FormPage:
    result = await db.execute(select(func.coalesce(func.max(FormPage.order_index), -1)))
    next_order = int(result.scalar_one()) + 1
    page = FormPage(
        title=body.title.strip() or "New page",
        description=body.description,
        order_index=body.order_index if body.order_index is not None else next_order,
    )
    db.add(page)
    await db.flush()
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="create_form_page",
        resource_type="form_page",
        resource_id=str(page.id),
        detail={"title": page.title},
    )
    await db.commit()
    await db.refresh(page)
    return page


@router.patch("/pages/{page_id}", response_model=FormPageRead)
async def update_page(
    page_id: int,
    body: FormPageUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> FormPage:
    page = await _get_active_page(db, page_id)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    for field, value in data.items():
        setattr(page, field, value)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="update_form_page",
        resource_type="form_page",
        resource_id=str(page_id),
        detail={"fields": list(data.keys())},
    )
    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> None:
    page = await _get_active_page(db, page_id)

    if page.title != STAGING_PAGE_TITLE:
        remaining = await db.execute(
            select(func.count())
            .select_from(FormPage)
            .where(
                FormPage.title != STAGING_PAGE_TITLE,
                FormPage.id != page_id,
                active_form_page(),
            )
        )
        if int(remaining.scalar_one()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot hide the only section. Add another section first, or keep at least one visible.",
            )

    mark_deleted(page, deleted_by_id=admin.id)
    await db.execute(
        update(Question)
        .where(Question.page_id == page_id, active_question())
        .values(deleted_at=page.deleted_at, deleted_by_id=admin.id)
    )

    await _reindex_active_pages(db)
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="delete_form_page",
        resource_type="form_page",
        resource_id=str(page_id),
        detail={"title": page.title},
    )
    await db.commit()


@router.post("/pages/{page_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_page(
    page_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> None:
    page = await _get_hidden_page(db, page_id)
    restore(page)
    q_result = await db.execute(select(Question).where(Question.page_id == page_id))
    for question in q_result.scalars().all():
        if question.deleted_at is not None:
            restore(question)

    await _reindex_active_pages(db)
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="restore_form_page",
        resource_type="form_page",
        resource_id=str(page_id),
        detail={"title": page.title},
    )
    await db.commit()


@router.get("/pages/{page_id}/questions", response_model=list[QuestionRead])
async def list_questions_for_page(
    page_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_authenticated)],
    __rate: None = form_read_limit,
) -> list[Question]:
    page = await _get_active_page(db, page_id)
    result = await db.execute(
        select(Question)
        .where(Question.page_id == page_id, active_question())
        .order_by(Question.order_index)
    )
    return list(result.scalars().all())


async def _resolve_target_page(db: AsyncSession, page_id: int | None) -> FormPage:
    if page_id is not None:
        return await _get_active_page(db, page_id)
    result = await db.execute(
        select(FormPage)
        .where(active_form_page())
        .order_by(FormPage.order_index.desc())
        .limit(1)
    )
    page = result.scalar_one_or_none()
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No form pages exist")
    return page


@router.post("/questions/sync-global-order")
async def resync_global_order(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> dict[str, bool]:
    """Align global_order with editor page + question order (live form path)."""
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="sync_global_order",
        resource_type="form",
        resource_id="all",
    )
    await db.commit()
    return {"ok": True}


@router.post("/questions/reorder")
async def reorder_questions(
    body: QuestionReorderRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> dict[str, bool]:
    ids = [item.id for item in body.items]
    result = await db.execute(select(Question).where(Question.id.in_(ids)))
    found = {q.id: q for q in result.scalars().all()}
    if len(found) != len(ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown question id in reorder payload")

    page_ids = {item.page_id for item in body.items}
    page_result = await db.execute(
        select(FormPage.id).where(
            FormPage.id.in_(page_ids),
            FormPage.title != STAGING_PAGE_TITLE,
        )
    )
    existing_pages = {row[0] for row in page_result.all()}
    if existing_pages != page_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown page id in reorder payload")

    for item in body.items:
        q = found[item.id]
        q.page_id = item.page_id
        q.order_index = item.order_index
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="reorder_questions",
        resource_type="form",
        resource_id="questions",
        detail={"count": len(body.items)},
    )
    await db.commit()
    return {"ok": True}


@router.post("/questions", response_model=QuestionRead, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> Question:
    page = await _resolve_target_page(db, body.page_id)
    result = await db.execute(
        select(func.coalesce(func.max(Question.order_index), -1))
        .select_from(Question)
        .where(Question.page_id == page.id, active_question())
    )
    next_order = int(result.scalar_one()) + 1
    order_index = body.order_index if body.order_index is not None else next_order
    question = Question(
        page_id=page.id,
        question_text=body.question_text,
        question_type=body.question_type,
        options=body.options,
        is_required=body.is_required,
        order_index=order_index,
        ms_forms_id=uuid.uuid4().hex,
    )
    db.add(question)
    await sync_global_order(db)
    await db.flush()
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="create_question",
        resource_type="question",
        resource_id=str(question.id),
        detail={"page_id": question.page_id, "type": question.question_type.value},
    )
    await db.commit()
    await db.refresh(question)
    return question


@router.put("/questions/{question_id}/branch-rules", response_model=list[QuestionBranchRuleAdminRead])
async def replace_question_branch_rules(
    question_id: int,
    body: BranchRulesReplaceRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> list[QuestionBranchRuleAdminRead]:
    source = await _get_active_question(db, question_id)
    if source.question_type not in BRANCHING_SOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branching is only supported for radio, select, and checkbox questions",
        )

    ensure_ms_forms_id(source)
    options = source.options if isinstance(source.options, list) else []
    option_strings = {str(o) for o in options}

    target_ids = {item.target_question_id for item in body.rules}
    if question_id in target_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A question cannot branch to itself",
        )

    targets: dict[int, Question] = {}
    if target_ids:
        result = await db.execute(
            select(Question).where(Question.id.in_(target_ids), active_question())
        )
        targets = {q.id: q for q in result.scalars().all()}
        if len(targets) != len(target_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown target question")

    seen_options: set[str] = set()
    for item in body.rules:
        if item.option_value in seen_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate branch for option: {item.option_value}",
            )
        seen_options.add(item.option_value)
        if option_strings and item.option_value not in option_strings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Option not defined on this question: {item.option_value}",
            )
        target = targets[item.target_question_id]
        ensure_ms_forms_id(target)

    await db.execute(
        delete(QuestionBranchRule).where(QuestionBranchRule.source_question_id == question_id)
    )

    created: list[QuestionBranchRule] = []
    for item in body.rules:
        target = targets[item.target_question_id]
        rule = QuestionBranchRule(
            source_question_id=question_id,
            option_value=item.option_value,
            target_ms_forms_id=target.ms_forms_id or "",
            target_question_id=target.id,
        )
        db.add(rule)
        created.append(rule)

    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="replace_branch_rules",
        resource_type="question",
        resource_id=str(question_id),
        detail={"rule_count": len(created)},
    )
    await db.commit()
    for rule in created:
        await db.refresh(rule)

    return [
        QuestionBranchRuleAdminRead(
            id=rule.id,
            option_value=rule.option_value,
            target_question_id=rule.target_question_id,
            target_question_text=(
                targets[rule.target_question_id].question_text[:120]
                if rule.target_question_id and rule.target_question_id in targets
                else None
            ),
        )
        for rule in created
    ]


@router.put("/questions/{question_id}", response_model=QuestionRead)
async def update_question(
    question_id: int,
    body: QuestionUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> Question:
    question = await _get_active_question(db, question_id)
    data = body.model_dump(exclude_unset=True)
    if "page_id" in data and data["page_id"] is not None:
        await _get_active_page(db, data["page_id"])
    for field, value in data.items():
        setattr(question, field, value)
    ensure_ms_forms_id(question)
    if {"page_id", "order_index"} & data.keys():
        await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="update_question",
        resource_type="question",
        resource_id=str(question_id),
        detail={"fields": list(data.keys())},
    )
    await db.commit()
    await db.refresh(question)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> None:
    question = await _get_active_question(db, question_id)
    mark_deleted(question, deleted_by_id=admin.id)
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="delete_question",
        resource_type="question",
        resource_id=str(question_id),
        detail={"question_text": question.question_text[:120]},
    )
    await db.commit()


@router.post("/questions/{question_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_question(
    question_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> None:
    question = await _get_hidden_question(db, question_id)
    page = await db.get(FormPage, question.page_id)
    if page is not None and page.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This question belongs to a hidden section. Unhide the section first.",
        )

    restore(question)
    await sync_global_order(db)
    await _audit_form_change(
        db,
        admin=admin,
        request=request,
        action="restore_question",
        resource_type="question",
        resource_id=str(question_id),
        detail={"question_text": question.question_text[:120]},
    )
    await db.commit()
