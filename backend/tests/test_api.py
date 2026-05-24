"""Basic API smoke tests (uses SQLite in-memory)."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "false")
os.environ.setdefault("ENVIRONMENT", "development")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")


def test_form_login_requires_valid_body():
    response = client.post("/auth/login", json={})
    assert response.status_code == 422


def test_admin_routes_require_auth():
    response = client.get("/responses/")
    assert response.status_code == 401


def test_analytics_aggregate_module():
    from analytics_aggregate import build_question_analytics, fetch_answer_rows

    assert callable(build_question_analytics)
    assert callable(fetch_answer_rows)


def test_soft_delete_requires_admin():
    response = client.delete("/responses/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


def test_delete_page_requires_admin():
    response = client.delete("/form/pages/1")
    assert response.status_code == 401
