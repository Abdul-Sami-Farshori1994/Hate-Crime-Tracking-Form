"""Excel export builder tests."""

from io import BytesIO

from openpyxl import load_workbook

from export_excel import build_export_xlsm, format_answer_for_cell
from models import Question, QuestionType


def _question(qid: int, text: str, *, order_index: int = 0) -> Question:
    return Question(
        id=qid,
        page_id=1,
        question_text=text,
        question_type=QuestionType.text,
        is_required=True,
        order_index=order_index,
    )


def test_format_answer_for_cell_checkbox():
    assert format_answer_for_cell('["A", "B"]', "checkbox") == "A, B"


def test_build_export_xlsm_rows_and_headers():
    questions = [
        _question(1, "Name?", order_index=0),
        _question(2, "District", order_index=1),
    ]
    sessions = [
        {
            "session_id": "abc-123",
            "respondent_name": "Alice",
            "submitted_at": "2026-05-22T10:00:00+00:00",
            "answers": [
                {
                    "question_id": 1,
                    "question_text": "Name?",
                    "question_type": "text",
                    "answer_value": "Alice",
                },
                {
                    "question_id": 2,
                    "question_text": "District",
                    "question_type": "select",
                    "answer_value": "Bangalore",
                },
            ],
        },
    ]

    data = build_export_xlsm(sessions, questions)
    workbook = load_workbook(BytesIO(data))
    sheet = workbook.active

    headers = [cell.value for cell in sheet[1]]
    assert headers[:4] == ["Id", "Start time", "Completion time", "Name"]
    assert headers[4:] == ["Name?", "District"]

    row = [cell.value for cell in sheet[2]]
    assert row[0] == "abc-123"
    assert row[3] == "Alice"
    assert row[4] == "Alice"
    assert row[5] == "Bangalore"

    import zipfile

    content_types = zipfile.ZipFile(BytesIO(data)).read("[Content_Types].xml").decode()
    assert "macroEnabled" in content_types
