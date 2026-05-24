"""HTTP helpers for end-to-end API tests (TestClient + cookies/CSRF)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from cookie_auth import CSRF_COOKIE
from main import app


@dataclass
class SessionClient:
    """TestClient wrapper that sends session cookies and CSRF on mutating requests."""

    client: TestClient
    cookies: dict[str, str]
    csrf_token: str | None

    def _mutate_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        out = dict(kwargs)
        headers = dict(out.pop("headers", {}) or {})
        if self.csrf_token:
            headers.setdefault("X-CSRF-Token", self.csrf_token)
        out["headers"] = headers
        out["cookies"] = {**self.cookies, **(out.get("cookies") or {})}
        return out

    def get(self, url: str, **kwargs: Any):
        kwargs.setdefault("cookies", self.cookies)
        return self.client.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.client.post(url, **self._mutate_kwargs(kwargs))

    def patch(self, url: str, **kwargs: Any):
        return self.client.patch(url, **self._mutate_kwargs(kwargs))

    def put(self, url: str, **kwargs: Any):
        return self.client.put(url, **self._mutate_kwargs(kwargs))

    def delete(self, url: str, **kwargs: Any):
        return self.client.delete(url, **self._mutate_kwargs(kwargs))


def _csrf_from_cookies(cookies: dict[str, str]) -> str | None:
    return cookies.get(CSRF_COOKIE)


def login_admin(client: TestClient) -> SessionClient:
    response = client.post("/auth/admin/login", json={"username": "admin", "password": "admin"})
    if response.status_code != 200:
        raise RuntimeError(f"admin login failed: {response.status_code} {response.text}")
    cookies = dict(response.cookies)
    return SessionClient(client=client, cookies=cookies, csrf_token=_csrf_from_cookies(cookies))


def login_user(client: TestClient) -> SessionClient:
    response = client.post("/auth/login", json={"username": "user", "password": "user"})
    if response.status_code != 200:
        raise RuntimeError(f"user login failed: {response.status_code} {response.text}")
    cookies = dict(response.cookies)
    return SessionClient(client=client, cookies=cookies, csrf_token=_csrf_from_cookies(cookies))


def make_test_client(*, use_cookie_auth: bool = True) -> TestClient:
    import os

    if use_cookie_auth:
        os.environ["USE_COOKIE_AUTH"] = "true"
    os.environ.setdefault("ADMIN_MFA_REQUIRED", "false")
    return TestClient(app)


def flow_question_ids(session: SessionClient) -> list[int]:
    response = session.get("/form/flow")
    if response.status_code != 200:
        raise RuntimeError(f"/form/flow failed: {response.status_code} {response.text}")
    return [int(q["id"]) for q in response.json().get("questions", [])]


def flow_question_texts(session: SessionClient) -> list[str]:
    response = session.get("/form/flow")
    if response.status_code != 200:
        raise RuntimeError(f"/form/flow failed: {response.status_code} {response.text}")
    return [q["question_text"] for q in response.json().get("questions", [])]


def flow_has_question_id(session: SessionClient, question_id: int) -> bool:
    return question_id in flow_question_ids(session)


def structure_question_by_id(admin: SessionClient, question_id: int) -> dict | None:
    response = admin.get("/form/structure")
    if response.status_code != 200:
        raise RuntimeError(f"/form/structure failed: {response.status_code} {response.text}")
    for page in response.json():
        for q in page.get("questions", []):
            if q.get("id") == question_id:
                return {**q, "page_id": page["id"], "page_is_hidden": page.get("is_hidden", False)}
    return None


def structure_find_question(admin: SessionClient, question_text: str) -> dict | None:
    response = admin.get("/form/structure")
    if response.status_code != 200:
        raise RuntimeError(f"/form/structure failed: {response.status_code} {response.text}")
    for page in response.json():
        for q in page.get("questions", []):
            if q.get("question_text") == question_text:
                return {**q, "page_id": page["id"], "page_is_hidden": page.get("is_hidden", False)}
    return None
