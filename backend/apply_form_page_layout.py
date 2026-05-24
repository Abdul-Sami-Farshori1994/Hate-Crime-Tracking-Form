"""Reassign questions to section pages without re-importing. Run: python apply_form_page_layout.py"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from database import get_session_factory
from import_microsoft_form import FORM_PAGE_SECTIONS, apply_page_sections
from models import FormPage, Question


async def main() -> None:
    factory = get_session_factory()
    async with factory() as session:
        questions = list(
            (
                await session.execute(
                    select(Question).order_by(Question.global_order.nulls_last(), Question.id)
                )
            ).scalars().all()
        )
        if len(questions) != 92:
            raise SystemExit(f"Expected 92 questions, found {len(questions)}. Run import_microsoft_form.py first.")

        staging = FormPage(title="_staging", description=None, order_index=9999)
        session.add(staging)
        await session.flush()
        for q in questions:
            q.page_id = staging.id
        await session.flush()

        for page in (await session.execute(select(FormPage).where(FormPage.id != staging.id))).scalars():
            await session.delete(page)
        await session.flush()

        pages = await apply_page_sections(session, questions, staging.id)
        await session.commit()
        print(f"Updated {len(questions)} questions across {len(pages)} pages.")


if __name__ == "__main__":
    asyncio.run(main())
