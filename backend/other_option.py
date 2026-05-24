"""Inline 'Other' choice answers: stored as 'Other: <user text>'."""

from __future__ import annotations

import json
import re

from models import Question, QuestionType
from respondent_name import normalize_question_text

OTHER_OPTION_LABEL = "Other"
OTHER_VALUE_PREFIX = "Other: "

# Uses branching follow-up text instead of inline Other (see microsoft_form.json).
INLINE_OTHER_EXCLUDED_TEXT = "alleged pretext of crime"


def is_other_option_label(label: str) -> bool:
    return str(label).strip().lower() == OTHER_OPTION_LABEL.lower()


def is_inline_other_excluded(question: Question) -> bool:
    return normalize_question_text(question.question_text) == INLINE_OTHER_EXCLUDED_TEXT


def question_has_other_option(question: Question) -> bool:
    opts = question.options if isinstance(question.options, list) else []
    return any(is_other_option_label(str(o)) for o in opts)


def uses_inline_other(question: Question) -> bool:
    if question.question_type not in (QuestionType.radio, QuestionType.select, QuestionType.checkbox):
        return False
    if is_inline_other_excluded(question):
        return False
    return question_has_other_option(question)


def other_option_label_in_list(options: list[str]) -> str | None:
    for opt in options:
        if is_other_option_label(opt):
            return str(opt)
    return None


def is_other_stored_value(raw: str) -> bool:
    s = str(raw).strip()
    if s.lower() == OTHER_OPTION_LABEL.lower():
        return True
    # "Other: " becomes "Other:" after strip — match Other: with optional detail
    return bool(re.match(r"^Other:\s*", s, re.I))


def other_text_from_stored(raw: str) -> str:
    s = str(raw).strip()
    match = re.match(r"^Other:\s*(.*)$", s, re.I)
    if match:
        return match.group(1).strip()
    return ""


def format_other_value(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", str(text or "").strip())
    return f"{OTHER_VALUE_PREFIX}{collapsed}"


def normalize_other_text(text: str, *, required: bool) -> str:
    collapsed = re.sub(r"\s+", " ", str(text or "").strip())
    if not collapsed:
        if required:
            raise ValueError("Please specify your Other answer")
        return format_other_value("")
    if len(collapsed) > 500:
        collapsed = collapsed[:500]
    return format_other_value(collapsed)


def choice_matches_option(stored: str, option: str) -> bool:
    """True if stored value selects this option (handles Other: text for Other label)."""
    s = str(stored).strip()
    if is_other_option_label(option):
        return is_other_stored_value(s)
    return s == str(option).strip()


def normalize_radio_or_select_other(raw: str, options: list[str], *, strict: bool) -> str:
    choice = raw.strip()
    other_label = other_option_label_in_list(options)
    if other_label is None:
        return choice
    if not is_other_stored_value(choice):
        if choice in options:
            return choice
        if not strict:
            return choice
        raise ValueError(f"answer {choice!r} not in options")
    text = other_text_from_stored(choice)
    if strict and not text:
        raise ValueError("Please specify your Other answer")
    return format_other_value(text) if text or not strict else OTHER_OPTION_LABEL


def normalize_checkbox_other_entries(
    choices: list[str],
    options: list[str],
    *,
    strict: bool,
) -> list[str]:
    other_label = other_option_label_in_list(options)
    out: list[str] = []
    for item in choices:
        item = str(item).strip()
        if not item:
            continue
        if other_label and is_other_stored_value(item):
            text = other_text_from_stored(item)
            if strict and not text:
                raise ValueError("Please specify your Other answer")
            if text:
                out.append(format_other_value(text))
            elif not strict:
                out.append(OTHER_OPTION_LABEL)
            continue
        if item in options:
            out.append(item)
        elif not strict:
            out.append(item)
        else:
            raise ValueError(f"invalid checkbox option {item!r}")
    return out


def other_answer_is_complete(question: Question, value: object) -> bool:
    """True when inline Other is not selected, or Other text is provided."""
    if not uses_inline_other(question):
        return True
    opts = [str(x) for x in question.options] if isinstance(question.options, list) else []
    other_label = other_option_label_in_list(opts)
    if other_label is None:
        return True

    if question.question_type == QuestionType.checkbox:
        stripped = str(value or "").strip()
        try:
            parsed = json.loads(stripped) if stripped.startswith("[") else []
        except json.JSONDecodeError:
            parsed = []
        if not isinstance(parsed, list):
            return True
        other_selected = any(is_other_stored_value(str(item)) for item in parsed)
        if not other_selected:
            return True
        for item in parsed:
            if is_other_stored_value(str(item)):
                return bool(other_text_from_stored(str(item)))
        return True

    if not choice_matches_option(str(value or ""), other_label):
        return True
    return bool(other_text_from_stored(str(value or "")))


def normalize_choice_answer(question: Question, raw: str, *, strict: bool = True) -> str | None:
    """Apply inline-Other rules; return None if this question does not use inline Other."""
    if not uses_inline_other(question):
        return None
    opts = [str(x) for x in question.options] if isinstance(question.options, list) else []
    qt = question.question_type
    if qt in (QuestionType.radio, QuestionType.select):
        return normalize_radio_or_select_other(raw, opts, strict=strict)
    if qt == QuestionType.checkbox:
        stripped = raw.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
        else:
            parts = re.split(r"[;\n]|,(?!\s)", stripped)
            parsed = [p.strip() for p in parts if p.strip()]
        normalized = normalize_checkbox_other_entries(
            [str(x) for x in parsed] if isinstance(parsed, list) else [],
            opts,
            strict=strict,
        )
        return json.dumps(normalized)
    return None
