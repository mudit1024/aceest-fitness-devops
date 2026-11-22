import pytest

from aceest import create_app
from aceest.config import Config


@pytest.fixture
def csrf_client(tmp_path):
    app = create_app(Config, TESTING=True, DATABASE_PATH=str(tmp_path / "csrf.db"))
    return app.test_client()


def test_write_without_csrf_token_is_rejected(csrf_client):
    resp = csrf_client.post("/api/clients", json={"name": "A", "program": "FL"})
    assert resp.status_code == 400


def test_write_with_csrf_token_is_accepted(csrf_client):
    token = csrf_client.get("/api/csrf-token").get_json()["csrf_token"]
    resp = csrf_client.post("/api/clients", json={"name": "A", "program": "FL"},
                            headers={"X-CSRFToken": token})
    assert resp.status_code == 201
