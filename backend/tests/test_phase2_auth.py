"""Phase 2 cookie session and refresh tests."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ALLOW_DEFAULT_USER_SEED", "true")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def cookie_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("USE_COOKIE_AUTH", "true")
    return TestClient(app)


def test_form_login_sets_session_cookie(cookie_client: TestClient):
    response = cookie_client.post("/auth/login", json={"username": "user", "password": "user"})
    assert response.status_code == 200
    assert "hc_access" in response.cookies
    assert response.json()["role"] == "user"


def test_session_endpoint_with_cookie(cookie_client: TestClient):
    login = cookie_client.post("/auth/login", json={"username": "user", "password": "user"})
    session = cookie_client.get("/auth/session", cookies=login.cookies)
    assert session.status_code == 200
    assert session.json()["username"] == "user"


def test_admin_login_issues_session(cookie_client: TestClient):
    response = cookie_client.post("/auth/admin/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert "hc_access" in response.cookies


def test_refresh_rotates_cookie(cookie_client: TestClient):
    login = cookie_client.post("/auth/login", json={"username": "user", "password": "user"})
    refreshed = cookie_client.post("/auth/refresh", cookies=login.cookies)
    assert refreshed.status_code == 200
    assert "hc_access" in refreshed.cookies


def test_logout_clears_session(cookie_client: TestClient):
    login = cookie_client.post("/auth/login", json={"username": "user", "password": "user"})
    cookies = login.cookies
    out = cookie_client.post("/auth/logout", cookies=cookies)
    assert out.status_code == 200
    session = cookie_client.get("/auth/session", cookies=cookies)
    assert session.status_code == 401
