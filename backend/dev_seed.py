"""ORM seed when tables exist but demo form content is missing (e.g. SQLite dev without Alembic)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FormPage, Question, QuestionType


async def seed_demo_form_if_empty(session: AsyncSession) -> None:
    r = await session.execute(select(func.count()).select_from(FormPage))
    if int(r.scalar_one() or 0) > 0:
        return

    p1 = FormPage(
        title="Page 1 — About the incident",
        description="Tell us what happened.",
        order_index=0,
    )
    p2 = FormPage(
        title="Page 2 — Details",
        description="Additional information.",
        order_index=1,
    )
    session.add_all([p1, p2])
    await session.flush()

    session.add_all(
        [
            Question(
                page_id=p1.id,
                question_text="Short description",
                question_type=QuestionType.text,
                options=None,
                is_required=True,
                order_index=0,
            ),
            Question(
                page_id=p1.id,
                question_text="Incident date",
                question_type=QuestionType.date,
                options=None,
                is_required=True,
                order_index=1,
            ),
            Question(
                page_id=p2.id,
                question_text="Was bias motivation present?",
                question_type=QuestionType.radio,
                options=["Yes", "No", "Unsure"],
                is_required=True,
                order_index=0,
            ),
            Question(
                page_id=p2.id,
                question_text="Type of incident (select all that apply)",
                question_type=QuestionType.checkbox,
                options=["Harassment", "Vandalism", "Assault", "Other"],
                is_required=False,
                order_index=1,
            ),
            Question(
                page_id=p2.id,
                question_text="Severity (1–5)",
                question_type=QuestionType.rating,
                options=None,
                is_required=False,
                order_index=2,
            ),
            Question(
                page_id=p2.id,
                question_text="Police report filed?",
                question_type=QuestionType.select,
                options=["Yes", "No"],
                is_required=False,
                order_index=3,
            ),
        ]
    )
    await session.commit()
