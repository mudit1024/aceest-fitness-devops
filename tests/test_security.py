import pytest

from tests.conftest import ADMIN, make_app


@pytest.fixture
def csrf_client(tmp_path):
    return make_app(tmp_path, WTF_CSRF_ENABLED=True).test_client()


def test_write_without_csrf_token_is_rejected(csrf_client):
    assert csrf_client.post("/api/login", json=ADMIN).status_code == 400


def test_write_with_csrf_token_is_accepted(csrf_client):
    token = csrf_client.get("/api/csrf-token").get_json()["csrf_token"]
    assert csrf_client.post("/api/login", json=ADMIN, headers={"X-CSRFToken": token}).status_code == 200
    # Login rotates the session, so a fresh token is needed afterwards.
    headers = {"X-CSRFToken": csrf_client.get("/api/csrf-token").get_json()["csrf_token"]}
    resp = csrf_client.post("/api/clients", json={"name": "A", "program": "FL"}, headers=headers)
    assert resp.status_code == 201
