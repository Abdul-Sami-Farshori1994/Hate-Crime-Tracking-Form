"""Branching visibility and submit-path validation (mirrors frontend formFlow.js)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FormPage, Question, QuestionBranchRule, QuestionType
from other_option import choice_matches_option, other_answer_is_complete
from soft_delete import active_form_page, active_question


class SubmitValidationError(ValueError):
    pass


@dataclass(frozen=True)
class BranchRuleRow:
    source_ms_forms_id: str
    option_value: str
    target_ms_forms_id: str


def sort_questions(questions: list[Question], pages: list[FormPage] | None) -> list[Question]:
    if not questions:
        return []
    if pages:
        page_order = {p.id: p.order_index for p in pages}

        def sort_key(q: Question) -> tuple[int, int, int]:
            return (
                page_order.get(q.page_id, 0),
                q.order_index if q.order_index is not None else q.global_order or q.id,
                q.id,
            )

        return sorted(questions, key=sort_key)
    return sorted(
        questions,
        key=lambda q: (q.global_order if q.global_order is not None else q.order_index, q.id),
    )


def build_branch_map(rules: list[BranchRuleRow]) -> dict[str, dict[str, str]]:
    branch_map: dict[str, dict[str, str]] = {}
    for rule in rules:
        branch_map.setdefault(rule.source_ms_forms_id, {})[rule.option_value] = rule.target_ms_forms_id
    return branch_map


def branch_target_ms_ids(branch_map: dict[str, dict[str, str]]) -> set[str]:
    targets: set[str] = set()
    for rules in branch_map.values():
        targets.update(rules.values())
    return targets


def _answer_matches_branch_option(raw: object, option: str, question_type: QuestionType) -> bool:
    if raw is None:
        return False
    if question_type == QuestionType.checkbox:
        try:
            parsed = json.loads(str(raw)) if raw else []
        except json.JSONDecodeError:
            return False
        if not isinstance(parsed, list):
            return False
        return any(choice_matches_option(str(item), option) for item in parsed)
    s = str(raw).strip()
    if not s or s.startswith("["):
        return False
    return choice_matches_option(s, option)


def _branch_target_is_visible(
    q: Question,
    branch_map: dict[str, dict[str, str]],
    by_ms: dict[str, Question],
    answers_by_id: dict[int, object],
) -> bool:
    for source_ms, rules in branch_map.items():
        source_q = by_ms.get(source_ms)
        if source_q is None:
            continue
        raw = answers_by_id.get(source_q.id)
        for option, target_ms in rules.items():
            if target_ms == q.ms_forms_id and _answer_matches_branch_option(
                raw, option, source_q.question_type
            ):
                return True
    return False


def visible_question_ids(
    ordered: list[Question],
    branch_map: dict[str, dict[str, str]],
    answers_by_id: dict[int, object],
) -> set[int]:
    if not ordered:
        return set()

    targets = branch_target_ms_ids(branch_map)
    by_ms = {q.ms_forms_id: q for q in ordered if q.ms_forms_id}
    visible: set[int] = set()

    for q in ordered:
        if not q.ms_forms_id or q.ms_forms_id not in targets:
            visible.add(q.id)
            continue
        if _branch_target_is_visible(q, branch_map, by_ms, answers_by_id):
            visible.add(q.id)

    return visible


def path_question_ids(
    ordered: list[Question],
    branch_map: dict[str, dict[str, str]],
    answers_by_id: dict[int, object],
) -> list[int]:
    visible = visible_question_ids(ordered, branch_map, answers_by_id)
    return [q.id for q in ordered if q.id in visible]


def _answer_is_missing(q: Question, raw: object) -> bool:
    if q.question_type == QuestionType.checkbox:
        try:
            parsed = json.loads(str(raw)) if raw else []
        except json.JSONDecodeError:
            return True
        if not isinstance(parsed, list) or len(parsed) == 0:
            return True
    elif raw is None or str(raw).strip() == "":
        return True
    return not other_answer_is_complete(q, raw)


def validate_path_answers(
    ordered: list[Question],
    branch_map: dict[str, dict[str, str]],
    answers_by_id: dict[int, object],
) -> list[int]:
    """Return question ids on the active path; raise SubmitValidationError if required answers missing."""
    path = path_question_ids(ordered, branch_map, answers_by_id)
    by_id = {q.id: q for q in ordered}

    for qid in path:
        q = by_id.get(qid)
        if q is None or not q.is_required:
            continue
        raw = answers_by_id.get(qid)
        if _answer_is_missing(q, raw):
            raise SubmitValidationError(f"Please answer required question: {q.question_text}")
        if not other_answer_is_complete(q, raw):
            raise SubmitValidationError(f"Please specify your Other answer for: {q.question_text}")

    return path


def submit_answer_ids(
    path: list[int],
    ordered: list[Question],
    answers_by_id: dict[int, object],
) -> list[int]:
    """Question ids to persist: all required on path plus optional questions that were answered."""
    by_id = {q.id: q for q in ordered}
    submit_ids: list[int] = []
    for qid in path:
        q = by_id.get(qid)
        if q is None:
            continue
        if q.is_required or not _answer_is_missing(q, answers_by_id.get(qid)):
            submit_ids.append(qid)
    return submit_ids


async def load_submit_flow_context(
    db: AsyncSession,
) -> tuple[list[Question], dict[str, dict[str, str]]]:
    """Load ordered questions and branch map for submit validation."""
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
    branch_map = build_branch_map(rules_from_rows(list(rules_result.all())))
    return sort_questions(questions, pages), branch_map


def rules_from_rows(
    rule_rows: list[tuple[QuestionBranchRule, str]],
) -> list[BranchRuleRow]:
    out: list[BranchRuleRow] = []
    for rule, source_ms in rule_rows:
        if source_ms:
            out.append(
                BranchRuleRow(
                    source_ms_forms_id=source_ms,
                    option_value=rule.option_value,
                    target_ms_forms_id=rule.target_ms_forms_id,
                )
            )
    return out
