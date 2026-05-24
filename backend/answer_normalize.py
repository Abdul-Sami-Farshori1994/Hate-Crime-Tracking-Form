"""Normalize and validate answer strings (shared by API and Excel import)."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from models import Question, QuestionType
from other_option import normalize_choice_answer as normalize_inline_other_answer


ANSWER_MAX_LENGTH = 10_000


class AnswerValidationError(ValueError):
    pass


def enforce_answer_max_length(raw: str, *, question_id: int | None = None) -> str:
    if len(raw) > ANSWER_MAX_LENGTH:
        label = f"Question {question_id}: " if question_id is not None else ""
        raise AnswerValidationError(f"{label}answer exceeds maximum length ({ANSWER_MAX_LENGTH} characters)")
    return raw


def options_list(question: Question) -> list[str] | None:
    """Return question choices as strings, or None if not a list-backed question."""
    if question.options is None:
        return None
    if isinstance(question.options, list):
        return [str(x) for x in question.options]
    return None


_options_list = options_list


def cell_to_raw(value: Any) -> str | None:
    """Convert an Excel cell value to a string answer, or None if empty."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return str(value)
    text = str(value).replace("\xa0", " ").replace("\u200b", "").strip()
    return text or None


def normalize_answer(question: Question, raw: str, *, strict: bool = True) -> str:
    """Return DB-ready answer_value. Raises AnswerValidationError when strict and invalid."""
    enforce_answer_max_length(raw, question_id=question.id)
    qt = question.question_type

    if qt == QuestionType.text:
        return raw.strip()

    if qt == QuestionType.number:
        s = raw.strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?", s):
            raise AnswerValidationError(f"Question {question.id}: must be a numeric value")
        return s

    if qt == QuestionType.date:
        s = raw.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        raise AnswerValidationError(f"Question {question.id}: date must be YYYY-MM-DD")

    if qt == QuestionType.rating:
        s = raw.strip()
        if not re.fullmatch(r"[1-5]", s):
            raise AnswerValidationError(f"Question {question.id}: rating must be 1–5")
        return s

    opts = _options_list(question)
    if qt in (QuestionType.radio, QuestionType.select, QuestionType.checkbox):
        if not opts:
            raise AnswerValidationError(f"Question {question.id}: missing options")
        try:
            inline = normalize_inline_other_answer(question, raw, strict=strict)
            if inline is not None:
                return inline
        except ValueError as exc:
            raise AnswerValidationError(f"Question {question.id}: {exc}") from exc

    if qt in (QuestionType.radio, QuestionType.select):
        choice = raw.strip()
        if choice in opts:
            return choice
        if not strict:
            return choice
        raise AnswerValidationError(
            f"Question {question.id}: answer {choice!r} not in options"
        )

    if qt == QuestionType.checkbox:
        choices = _parse_checkbox_raw(raw)
        if not strict:
            choices = [c for c in choices if c in opts] or choices
        else:
            for c in choices:
                if c not in opts:
                    raise AnswerValidationError(
                        f"Question {question.id}: invalid checkbox option {c!r}"
                    )
        return json.dumps(choices)

    raise AnswerValidationError(f"Unknown question_type: {qt}")


def _parse_checkbox_raw(raw: str) -> list[str]:
    stripped = raw.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise AnswerValidationError("checkbox answers must be a JSON array string") from exc
        if not isinstance(parsed, list):
            raise AnswerValidationError("checkbox JSON must be an array")
        return [str(x).strip() for x in parsed if str(x).strip()]
    parts = re.split(r"[;\n]|,(?!\s)", stripped)
    return [p.strip() for p in parts if p.strip()]
