import pytest

from aceest import create_app
from aceest.config import Config


@pytest.fixture
def app(tmp_path):
    # CSRF is switched off for functional tests; test_security.py covers it.
    return create_app(Config, TESTING=True, WTF_CSRF_ENABLED=False, DATABASE_PATH=str(tmp_path / "test.db"))


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_client(client):
    payload = {"name": "Arun", "age": 30, "height": 175, "weight": 80, "program": "FL",
               "target_weight": 72, "target_adherence": 85}
    resp = client.post("/api/clients", json=payload)
    assert resp.status_code == 201
    return resp.get_json()
