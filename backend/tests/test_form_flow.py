"""Submit-path validation (branching + required questions)."""

import pytest

from form_flow import (
    BranchRuleRow,
    SubmitValidationError,
    build_branch_map,
    path_question_ids,
    sort_questions,
    submit_answer_ids,
    validate_path_answers,
    visible_question_ids,
)
from models import FormPage, Question, QuestionType


def _q(
    qid: int,
    *,
    page_id: int = 1,
    ms_id: str,
    required: bool = False,
    qtype: QuestionType = QuestionType.text,
    order: int = 0,
) -> Question:
    return Question(
        id=qid,
        page_id=page_id,
        question_text=f"Q{qid}",
        question_type=qtype,
        options=None,
        is_required=required,
        order_index=order,
        ms_forms_id=ms_id,
    )


def test_submit_answer_ids_skips_optional_blank():
    ordered = [
        _q(1, ms_id="a", required=True),
        _q(2, ms_id="b", required=False, qtype=QuestionType.rating),
    ]
    branch_map: dict[str, dict[str, str]] = {}
    path = path_question_ids(ordered, branch_map, {1: "hello"})
    store = submit_answer_ids(path, ordered, {1: "hello"})
    assert store == [1]


def test_required_question_on_path_must_be_answered():
    ordered = [_q(1, ms_id="a", required=True), _q(2, ms_id="b")]
    branch_map: dict[str, dict[str, str]] = {}
    with pytest.raises(SubmitValidationError):
        validate_path_answers(ordered, branch_map, {2: "ok"})


def test_branch_target_hidden_until_triggered():
    ordered = [
        _q(1, ms_id="src", qtype=QuestionType.radio),
        _q(2, ms_id="tgt", required=True),
    ]
    ordered[0].options = ["Yes", "No"]
    branch_map = build_branch_map([BranchRuleRow("src", "Yes", "tgt")])
    visible = visible_question_ids(ordered, branch_map, {})
    assert 1 in visible
    assert 2 not in visible

    visible_yes = visible_question_ids(ordered, branch_map, {1: "Yes"})
    assert 2 in visible_yes


def test_submit_path_rejects_missing_required_on_branch():
    ordered = [
        _q(1, ms_id="src", qtype=QuestionType.radio),
        _q(2, ms_id="tgt", required=True),
    ]
    ordered[0].options = ["Yes", "No"]
    branch_map = build_branch_map([BranchRuleRow("src", "Yes", "tgt")])
    with pytest.raises(SubmitValidationError, match="required"):
        validate_path_answers(ordered, branch_map, {1: "Yes"})


def test_sort_questions_by_page_order():
    pages = [
        FormPage(id=1, title="P1", order_index=0),
        FormPage(id=2, title="P2", order_index=1),
    ]
    questions = [
        _q(10, page_id=2, ms_id="b", order=0),
        _q(11, page_id=1, ms_id="a", order=0),
    ]
    sorted_q = sort_questions(questions, pages)
    assert [q.id for q in sorted_q] == [11, 10]
