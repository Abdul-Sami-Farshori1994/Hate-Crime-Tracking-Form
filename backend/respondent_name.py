"""Derive session respondent_name from form answers (name question in the form)."""

from __future__ import annotations

import re

from models import Question

NAME_QUESTION_MARKERS = (
    "please enter your name",
    "enter your name",
    "your name",
)


def normalize_question_text(text: str) -> str:
    s = str(text or "").replace("\xa0", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", s.strip().lower())


def normalize_respondent_label(raw: str) -> str:
    """Trim and collapse whitespace for storage on response_sessions."""
    s = re.sub(r"\s+", " ", str(raw or "").strip())
    if len(s) < 2:
        raise ValueError("Name must be at least 2 characters")
    if len(s) > 200:
        return s[:200]
    return s


def find_name_question(questions: list[Question]) -> Question | None:
    """Prefer a question whose text matches name markers; else earliest in form order."""
    if not questions:
        return None

    ordered = sorted(
        questions,
        key=lambda q: (
            q.global_order if q.global_order is not None else q.order_index,
            q.page_id,
            q.id,
        ),
    )
    for q in ordered:
        key = normalize_question_text(q.question_text)
        if any(marker in key for marker in NAME_QUESTION_MARKERS):
            return q
    return ordered[0]


def respondent_name_from_answers(
    questions: dict[int, Question],
    answer_values: dict[int, str],
) -> str | None:
    """Return label for response_sessions, or None if the name answer is missing."""
    name_q = find_name_question(list(questions.values()))
    if name_q is None:
        return None
    raw = answer_values.get(name_q.id)
    if raw is None or not str(raw).strip():
        return None
    try:
        return normalize_respondent_label(str(raw))
    except ValueError:
        return None
