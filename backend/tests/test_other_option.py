import json

import pytest

from answer_normalize import AnswerValidationError, normalize_answer
from models import Question, QuestionType
from other_option import (
    choice_matches_option,
    format_other_value,
    is_inline_other_excluded,
    is_other_stored_value,
    normalize_choice_answer,
    uses_inline_other,
)


def _q(text: str, qtype: QuestionType, options: list[str] | None) -> Question:
    return Question(
        id=1,
        page_id=1,
        question_text=text,
        question_type=qtype,
        options=options,
        is_required=True,
        order_index=0,
    )


def test_pretext_excluded_from_inline_other():
    q = _q("Alleged pretext of crime", QuestionType.radio, ["A", "Other"])
    assert is_inline_other_excluded(q)
    assert not uses_inline_other(q)


def test_inline_other_radio_requires_text():
    q = _q("Religion of the victims", QuestionType.radio, ["Muslim", "Other"])
    assert uses_inline_other(q)
    with pytest.raises(AnswerValidationError, match="Other"):
        normalize_answer(q, "Other", strict=True)
    assert normalize_answer(q, format_other_value("custom"), strict=True) == format_other_value("custom")


def test_inline_other_checkbox():
    q = _q("Type of weapon used", QuestionType.checkbox, ["Stones", "Other"])
    raw = json.dumps(["Stones", format_other_value("slingshot")])
    out = json.loads(normalize_answer(q, raw, strict=True))
    assert "Stones" in out
    assert format_other_value("slingshot") in out


def test_branch_match_other_with_prefix():
    assert choice_matches_option(format_other_value("x"), "Other")
    assert not choice_matches_option("Muslim", "Other")


def test_empty_other_suffix_still_recognized_after_strip():
    """format_other_value('') is 'Other: ' which strip() turns into 'Other:'."""
    empty_other = format_other_value("")
    assert is_other_stored_value(empty_other)
    assert choice_matches_option(empty_other, "Other")


def test_normalize_choice_answer_helper():
    q = _q("Caste", QuestionType.select, ["Dalit", "Other"])
    assert normalize_choice_answer(q, format_other_value("unspecified"), strict=True) == format_other_value(
        "unspecified"
    )
