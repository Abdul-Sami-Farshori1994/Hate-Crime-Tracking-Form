"""Import Microsoft Form JSON into the database. Run from backend/: python import_microsoft_form.py"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from sqlalchemy import delete, select

from database import get_session_factory
from models import FormPage, Question, QuestionBranchRule, QuestionType, Response, ResponseSession

DATA_PATH = Path(__file__).resolve().parent / "data" / "microsoft_form.json"

TYPE_MAP = {
    "text": QuestionType.text,
    "textarea": QuestionType.text,
    "radio": QuestionType.radio,
    "checkbox": QuestionType.checkbox,
    "dropdown": QuestionType.select,
    "date": QuestionType.date,
    "number": QuestionType.number,
}

# 1-based question numbers (form order, excluding section headers).
FORM_PAGE_SECTIONS: list[tuple[str, str | None, int, int]] = [
    (
        "Incident report",
        None,
        1,
        1,
    ),
    (
        "Section 2: Pretext of Crime",
        "In this section, we ask you to answer questions relating to the alleged reasons behind a hate crime. "
        "While we understand that the following list of alleged reasons may not be exhaustive, please select the "
        "ones most closely mentioned in the media report.",
        2,
        4,
    ),
    (
        "Section 3: Evidence of Hate Crime",
        "In this section, we ask questions regarding the evidence provided in the media report based on which "
        "it can be ascertained that the crime was a hate crime.",
        5,
        9,
    ),
    (
        "Section 4: Place and Date of Violent Crime",
        "In this section, we ask factual questions regarding the place and date of the violent crime. Please note "
        "that the date of the crime may not be the same as the date of reporting. If the date of the crime is not "
        "available, please use the date of reporting as the effective date.",
        10,
        50,
    ),
    (
        "Section 5: Identity of the Victim(s)",
        "In this section, we ask questions regarding the identity of the victim(s).",
        51,
        58,
    ),
    (
        "Section 6: Identity of the Attacker(s)",
        "In this section, we ask questions regarding the identity of the attacker(s).",
        59,
        68,
    ),
    (
        "Section 7: Nature of Harm",
        "In this section, we ask questions regarding the nature of harm caused by the incident of violence.",
        69,
        74,
    ),
    (
        "Section 8: Weapons of Violence",
        "In this section, we ask about the types of weapons used in the violence.",
        75,
        75,
    ),
    (
        "Section 9: Role of the Police / Civil Administration / Elected Representatives",
        "In this section, we ask questions regarding the role of the state and its representatives.",
        76,
        86,
    ),
    (
        "Section 10: Violence as Performance",
        "In this section, we aim to understand the role of onlookers and bystanders.",
        87,
        89,
    ),
    (
        "Section 11: Source of Information",
        "In this section, we ask you to provide the source of information for this incident of violence by adding "
        "at least two credible media sources.",
        90,
        92,
    ),
]


def clean_page_title(text: str) -> str:
    title = re.sub(r"^\[SECTION\]\s*", "", text.strip(), flags=re.IGNORECASE)
    return title or "Form section"


def map_field_type(field_type: str) -> QuestionType | None:
    if field_type == "section_header":
        return None
    if field_type not in TYPE_MAP:
        raise ValueError(f"Unsupported field_type: {field_type}")
    return TYPE_MAP[field_type]


async def clear_existing_form(session) -> None:
    await session.execute(delete(Response))
    await session.execute(delete(ResponseSession))
    await session.execute(delete(QuestionBranchRule))
    await session.execute(delete(Question))
    await session.execute(delete(FormPage))
    await session.flush()


async def apply_page_sections(
    session, ordered_questions: list[Question], staging_page_id: int
) -> list[FormPage]:
    """Assign questions to fixed section pages by 1-based form question number."""
    if len(ordered_questions) != 92:
        raise ValueError(f"Expected 92 questions, got {len(ordered_questions)}")

    pages: list[FormPage] = []
    for order_index, (title, description, _start, _end) in enumerate(FORM_PAGE_SECTIONS):
        page = FormPage(title=title, description=description, order_index=order_index)
        session.add(page)
        pages.append(page)
    await session.flush()

    for q_num, question in enumerate(ordered_questions, start=1):
        section_idx = next(
            i for i, (_t, _d, start, end) in enumerate(FORM_PAGE_SECTIONS) if start <= q_num <= end
        )
        page = pages[section_idx]
        _title, _desc, start, _end = FORM_PAGE_SECTIONS[section_idx]
        question.page_id = page.id
        question.order_index = q_num - start

    await session.flush()

    staging = await session.get(FormPage, staging_page_id)
    if staging is not None:
        await session.delete(staging)
    await session.flush()
    return pages


async def import_form(session, items: list[dict]) -> None:
    await clear_existing_form(session)

    global_order = 0
    ordered_questions: list[Question] = []
    ms_to_question: dict[str, Question] = {}
    pending_branches: list[tuple[str, str, str]] = []

    staging = FormPage(title="_staging", description=None, order_index=0)
    session.add(staging)
    await session.flush()

    if not items:
        raise ValueError("Empty form definition")

    for item in items:
        field_type = item.get("field_type", "")
        if field_type == "section_header":
            continue

        qtype = map_field_type(field_type)
        if qtype is None:
            continue

        options = item.get("options") or []
        if not isinstance(options, list):
            options = []

        help_text = item.get("description")
        if help_text:
            help_text = str(help_text).strip() or None

        question = Question(
            page_id=staging.id,
            question_text=str(item["question_text"]).strip(),
            question_type=qtype,
            options=options if options else None,
            is_required=bool(item.get("required", False)),
            order_index=global_order,
            ms_forms_id=str(item["ms_forms_id"]),
            help_text=help_text,
            global_order=global_order,
        )
        global_order += 1
        session.add(question)
        await session.flush()

        ordered_questions.append(question)
        ms_to_question[question.ms_forms_id] = question

        for branch in item.get("branching") or []:
            pending_branches.append(
                (
                    question.ms_forms_id,
                    str(branch["option"]),
                    str(branch["go_to"]),
                )
            )

    pages = await apply_page_sections(session, ordered_questions, staging.id)

    await session.flush()

    for source_ms, option_value, target_ms in pending_branches:
        source_q = ms_to_question.get(source_ms)
        if source_q is None:
            continue
        target_q = ms_to_question.get(target_ms)
        session.add(
            QuestionBranchRule(
                source_question_id=source_q.id,
                option_value=option_value,
                target_ms_forms_id=target_ms,
                target_question_id=target_q.id if target_q else None,
            )
        )

    await session.commit()
    print(f"Imported {len(ms_to_question)} questions across {len(pages)} pages.")
    print(f"Imported {len(pending_branches)} branch rules.")


async def main() -> None:
    if not DATA_PATH.is_file():
        print(f"Missing {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    items = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        print("JSON root must be an array", file=sys.stderr)
        sys.exit(1)

    factory = get_session_factory()
    async with factory() as session:
        try:
            await import_form(session, items)
        except Exception:
            await session.rollback()
            raise

    async with factory() as session:
        pages = (await session.execute(select(FormPage))).scalars().all()
        questions = (await session.execute(select(Question))).scalars().all()
        rules = (await session.execute(select(QuestionBranchRule))).scalars().all()
        print(f"Verify: {len(pages)} pages, {len(questions)} questions, {len(rules)} rules.")


if __name__ == "__main__":
    asyncio.run(main())
