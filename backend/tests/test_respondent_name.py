"""Tests for deriving respondent_name from form answers."""

from respondent_name import (
    find_name_question,
    normalize_respondent_label,
    respondent_name_from_answers,
)
from models import Question, QuestionType


def _q(qid: int, text: str, *, global_order: int | None = None) -> Question:
    return Question(
        id=qid,
        page_id=1,
        question_text=text,
        question_type=QuestionType.text,
        options=None,
        is_required=True,
        order_index=qid,
        global_order=global_order,
    )


def test_find_name_question_by_marker():
    q1 = _q(1, "Please enter your name", global_order=1)
    q2 = _q(2, "Incident date", global_order=2)
    assert find_name_question([q2, q1]).id == 1


def test_respondent_name_from_answers():
    q1 = _q(1, "Please enter your name", global_order=1)
    q2 = _q(2, "Other field", global_order=2)
    name = respondent_name_from_answers(
        {q1.id: q1, q2.id: q2},
        {q1.id: "  Ada Lovelace  ", q2.id: "x"},
    )
    assert name == "Ada Lovelace"


def test_duplicate_names_allowed_different_sessions():
    """Same label string can be produced for multiple submissions (no uniqueness in helper)."""
    q1 = _q(1, "Please enter your name")
    answers = {q1.id: "Same Person"}
    a = respondent_name_from_answers({q1.id: q1}, answers)
    b = respondent_name_from_answers({q1.id: q1}, answers)
    assert a == b == normalize_respondent_label("Same Person")
