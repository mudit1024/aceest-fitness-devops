import pytest

from aceest import create_app
from aceest.config import Config

ADMIN = {"username": "admin", "password": "test-admin-pass"}


def make_app(tmp_path, **overrides):
    settings = {
        "TESTING": True,
        # CSRF is switched off for functional tests; test_security.py covers it.
        "WTF_CSRF_ENABLED": False,
        "DATABASE_PATH": str(tmp_path / "test.db"),
        "SECRET_KEY": "test-secret",
        "ADMIN_PASSWORD": ADMIN["password"],
    }
    settings.update(overrides)
    return create_app(Config, **settings)


@pytest.fixture
def app(tmp_path):
    return make_app(tmp_path)


@pytest.fixture
def anon_client(app):
    return app.test_client()


@pytest.fixture
def client(app):
    """Test client signed in as the seeded admin user."""
    test_client = app.test_client()
    assert test_client.post("/api/login", json=ADMIN).status_code == 200
    return test_client


@pytest.fixture
def sample_client(client):
    payload = {"name": "Arun", "age": 30, "height": 175, "weight": 80, "program": "FL",
               "target_weight": 72, "target_adherence": 85}
    resp = client.post("/api/clients", json=payload)
    assert resp.status_code == 201
    return resp.get_json()
