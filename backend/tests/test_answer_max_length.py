import pytest

from answer_normalize import ANSWER_MAX_LENGTH, AnswerValidationError, enforce_answer_max_length, normalize_answer
from models import Question, QuestionType


def test_enforce_answer_max_length():
    with pytest.raises(AnswerValidationError):
        enforce_answer_max_length("x" * (ANSWER_MAX_LENGTH + 1), question_id=1)


def test_normalize_text_respects_max_length():
    q = Question(
        id=1,
        page_id=1,
        question_text="T",
        question_type=QuestionType.text,
        is_required=False,
        order_index=0,
    )
    with pytest.raises(AnswerValidationError):
        normalize_answer(q, "a" * (ANSWER_MAX_LENGTH + 1))
