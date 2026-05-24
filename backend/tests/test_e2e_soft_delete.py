"""
End-to-end tests: HTTP API + in-memory DB, full hide/unhide flows.

Run: pytest tests/test_e2e_soft_delete.py -v
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests.e2e_client import (
    flow_has_question_id,
    login_admin,
    login_user,
    make_test_client,
    structure_find_question,
    structure_question_by_id,
)

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "true")
os.environ.setdefault("ENVIRONMENT", "development")

CASTE_QUESTION_TEXT = "Caste of the victims (if known)"


pytestmark = pytest.mark.e2e


@pytest.fixture
def api_client() -> TestClient:
    return make_test_client(use_cookie_auth=True)


@pytest.fixture
def admin(api_client: TestClient):
    return login_admin(api_client)


@pytest.fixture
def user(api_client: TestClient):
    return login_user(api_client)


def _create_two_sections_with_caste_question(admin) -> tuple[int, int, int]:
    """Return (page_a_id, page_b_id, caste_question_id)."""
    p1 = admin.post("/form/pages", json={"title": "E2E Section A"})
    assert p1.status_code == 201, p1.text
    p2 = admin.post("/form/pages", json={"title": "E2E Section B — Victims"})
    assert p2.status_code == 201, p2.text
    page_a_id = p1.json()["id"]
    page_b_id = p2.json()["id"]

    q = admin.post(
        "/form/questions",
        json={
            "page_id": page_b_id,
            "question_text": CASTE_QUESTION_TEXT,
            "question_type": "radio",
            "options": ["Dalit", "Adivasi", "OBC", "General", "Unknown", "Other"],
            "is_required": False,
        },
    )
    assert q.status_code == 201, q.text
    return page_a_id, page_b_id, q.json()["id"]


def test_e2e_caste_question_visible_on_live_form_before_hide(admin, user) -> None:
    _, _, qid = _create_two_sections_with_caste_question(admin)
    assert flow_has_question_id(user, qid)


def test_e2e_hide_question_removes_from_live_form_keeps_in_editor(admin, user) -> None:
    _, _, qid = _create_two_sections_with_caste_question(admin)

    hide = admin.delete(f"/form/questions/{qid}")
    assert hide.status_code == 204, hide.text

    assert not flow_has_question_id(user, qid)

    found = structure_question_by_id(admin, qid)
    assert found is not None
    assert found["is_hidden"] is True

    restore = admin.post(f"/form/questions/{qid}/restore")
    assert restore.status_code == 204, restore.text

    found = structure_question_by_id(admin, qid)
    assert found is not None
    assert found["is_hidden"] is False

    assert flow_has_question_id(user, qid)


def test_e2e_hide_section_cascades_to_live_form_and_editor(admin, user) -> None:
    page_a_id, page_b_id, qid = _create_two_sections_with_caste_question(admin)
    assert flow_has_question_id(user, qid)

    hide = admin.delete(f"/form/pages/{page_b_id}")
    assert hide.status_code == 204, hide.text

    assert not flow_has_question_id(user, qid)

    structure = admin.get("/form/structure").json()
    section_b = next(p for p in structure if p["id"] == page_b_id)
    assert section_b["is_hidden"] is True
    caste = next(q for q in section_b["questions"] if q["id"] == qid)
    assert caste["is_hidden"] is True

    section_a = next(p for p in structure if p["id"] == page_a_id)
    assert section_a["is_hidden"] is False


def test_e2e_restore_section_restores_questions_on_live_form(admin, user) -> None:
    _, page_b_id, qid = _create_two_sections_with_caste_question(admin)
    assert admin.delete(f"/form/pages/{page_b_id}").status_code == 204

    restore = admin.post(f"/form/pages/{page_b_id}/restore")
    assert restore.status_code == 204, restore.text

    found = structure_question_by_id(admin, qid)
    assert found is not None
    assert found["is_hidden"] is False
    assert found["page_is_hidden"] is False

    assert flow_has_question_id(user, qid)


def test_e2e_cannot_restore_question_while_section_hidden(admin) -> None:
    _, page_b_id, qid = _create_two_sections_with_caste_question(admin)
    assert admin.delete(f"/form/pages/{page_b_id}").status_code == 204

    restore_q = admin.post(f"/form/questions/{qid}/restore")
    assert restore_q.status_code == 400
    assert "hidden section" in restore_q.json().get("detail", "").lower()


def test_e2e_hidden_structure_lists_orphan_hidden_question(admin) -> None:
    """Question hidden alone (section visible) appears in hidden-structure.questions."""
    _, page_b_id, qid = _create_two_sections_with_caste_question(admin)
    assert admin.delete(f"/form/questions/{qid}").status_code == 204

    hidden = admin.get("/form/hidden-structure")
    assert hidden.status_code == 200
    body = hidden.json()
    ids = [q["id"] for q in body.get("questions", [])]
    assert qid in ids
    assert not any(s["id"] == page_b_id for s in body.get("sections", []))
