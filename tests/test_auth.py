import logging

import pytest

from tests.conftest import ADMIN, make_app


def test_api_requires_login(anon_client):
    assert anon_client.get("/api/clients").status_code == 401
    assert anon_client.get("/api/clients/x/summary").status_code == 401
    assert anon_client.get("/api/me").status_code == 401


def test_html_redirects_to_login(anon_client):
    resp = anon_client.get("/clients")
    assert resp.status_code == 302
    assert "/login?next=/clients" in resp.headers["Location"]


def test_public_pages_stay_public(anon_client):
    for url in ("/", "/programs/FL", "/calculator", "/health", "/version", "/api/programs", "/login"):
        assert anon_client.get(url).status_code == 200, url


def test_api_login_and_me(anon_client):
    assert anon_client.post("/api/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert anon_client.post("/api/login", json=ADMIN).get_json() == {"username": "admin", "role": "Admin"}
    assert anon_client.get("/api/me").get_json()["role"] == "Admin"


def test_html_login_logout_flow(anon_client):
    resp = anon_client.post("/login?next=/clients", data=ADMIN)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/clients")
    assert b"Logout admin (Admin)" in anon_client.get("/clients").data
    anon_client.post("/logout")
    assert anon_client.get("/clients").status_code == 302


def test_html_login_failure_and_open_redirect_blocked(anon_client):
    assert b"Invalid credentials" in anon_client.post("/login", data={"username": "admin", "password": "x"}).data
    resp = anon_client.post("/login?next=//evil.example.com", data=ADMIN)
    assert resp.headers["Location"].endswith("/clients")


def test_admin_creates_trainer_who_cannot_delete(client, app, sample_client):
    resp = client.post("/api/users", json={"username": "ravi", "password": "pw-123", "role": "Trainer"})
    assert resp.status_code == 201
    assert client.post("/api/users", json={"username": "ravi", "password": "x"}).status_code == 409
    assert client.post("/api/users", json={"username": "", "password": "x"}).status_code == 400
    assert client.post("/api/users", json={"username": "z", "password": "x", "role": "Boss"}).status_code == 400

    trainer = app.test_client()
    trainer.post("/api/login", json={"username": "ravi", "password": "pw-123"})
    assert trainer.get("/api/clients").status_code == 200
    assert trainer.delete("/api/clients/Arun").status_code == 403
    assert trainer.post("/api/users", json={"username": "a", "password": "b"}).status_code == 403


def test_role_required_html_redirect(app):
    from aceest.auth import role_required

    @app.route("/admin-only-page")
    @role_required("Admin")
    def admin_only_page():
        return "secret"

    resp = app.test_client().get("/admin-only-page")
    assert resp.status_code == 302


def test_generated_admin_password_is_logged(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        make_app(tmp_path, ADMIN_PASSWORD=None, DATABASE_PATH=str(tmp_path / "gen.db"))
    assert "generated one-time admin password" in caplog.text


@pytest.mark.parametrize("username,password", [("", "x"), ("u", "")])
def test_create_user_requires_fields(app, username, password):
    from aceest.auth import create_user
    with app.app_context(), pytest.raises(ValueError):
        create_user(username, password, "Trainer")
