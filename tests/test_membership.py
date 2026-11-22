import sqlite3
from datetime import date, timedelta

import pytest

from aceest import models
from aceest.fitness import ValidationError
from tests.conftest import make_app

TODAY = date(2026, 6, 10)


def test_membership_status():
    assert models.membership_status(None, TODAY) == "None"
    assert models.membership_status("2026-06-10", TODAY) == "Active"
    assert models.membership_status("2026-06-09", TODAY) == "Expired"


def test_renew_extends_from_today_then_from_end(app, sample_client):
    with app.app_context():
        first = models.renew_membership("Arun", 1, today=TODAY)
        assert first == {"client": "Arun", "membership_end": "2026-07-10", "status": "Active"}
        second = models.renew_membership("Arun", 2, today=TODAY)
        assert second["membership_end"] == "2026-09-08"
        # Expired membership restarts from today.
        later = date(2027, 1, 1)
        assert models.renew_membership("Arun", 1, today=later)["membership_end"] == "2027-01-31"


@pytest.mark.parametrize("months", [0, 25, "x", None])
def test_renew_validation(app, sample_client, months):
    with app.app_context(), pytest.raises(ValidationError):
        models.renew_membership("Arun", months, today=TODAY)


def test_membership_api(client, sample_client):
    assert client.get("/api/clients/Arun/membership").get_json()["status"] == "None"
    resp = client.post("/api/clients/Arun/membership", json={"months": 3})
    assert resp.status_code == 200
    expected_end = (date.today() + timedelta(days=90)).isoformat()
    assert resp.get_json() == {"client": "Arun", "membership_end": expected_end, "status": "Active"}
    assert client.post("/api/clients/Arun/membership", json={"months": 99}).status_code == 400
    assert client.get("/api/clients/ghost/membership").status_code == 404
    assert client.post("/api/clients/ghost/membership", json={"months": 1}).status_code == 404


def test_membership_form(client, sample_client):
    resp = client.post("/clients/Arun/membership", data={"months": "1"}, follow_redirects=True)
    assert b"Membership renewed until" in resp.data
    assert b"Membership : Active" in resp.data
    resp = client.post("/clients/Arun/membership", data={"months": "0"}, follow_redirects=True)
    assert b"months must be between 1 and 24" in resp.data
    assert client.post("/clients/ghost/membership", data={"months": "1"}).status_code == 404


def test_dashboard_stats(app, client):
    client.post("/api/clients", json={"name": "A", "program": "FL"})
    client.post("/api/clients", json={"name": "B", "program": "FL"})
    client.post("/api/clients", json={"name": "C", "program": "MG"})
    client.post("/api/clients/A/progress", json={"adherence": 50})
    client.post("/api/clients/B/progress", json={"adherence": 100})
    client.post("/api/clients/A/workouts", json={"workout_type": "Cardio", "date": "2026-06-09"})
    client.post("/api/clients/A/workouts", json={"workout_type": "Cardio", "date": "2026-06-01"})
    with app.app_context():
        models.renew_membership("A", 1, today=date(2026, 5, 15))   # ends 2026-06-14 -> expiring soon
        models.renew_membership("B", 1, today=date(2026, 4, 1))    # ends 2026-05-01 -> expired
        stats = models.dashboard_stats(today=TODAY)
    assert stats == {
        "total_clients": 3,
        "active_members": 1,
        "expired_members": 1,
        "expiring_within_7_days": 1,
        "average_adherence": 75.0,
        "workouts_this_week": 1,
        "clients_by_program": {"FL": 2, "MG": 1},
    }


def test_dashboard_page_and_api(client, sample_client):
    assert b"Gym Dashboard" in client.get("/dashboard").data
    assert client.get("/api/dashboard").get_json()["total_clients"] == 1


def test_dashboard_empty(client):
    assert b"No clients yet." in client.get("/dashboard").data


def test_dashboard_requires_login(anon_client):
    assert anon_client.get("/api/dashboard").status_code == 401


def test_migration_upgrades_old_database(tmp_path):
    """A database created by release 3.1 (no membership column) is upgraded on start-up."""
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, age INTEGER, "
                     "height REAL, weight REAL, program TEXT, calories INTEGER, target_weight REAL, "
                     "target_adherence INTEGER)")
        conn.execute("INSERT INTO clients (name, program) VALUES ('Legacy', 'BG')")
    app = make_app(tmp_path, DATABASE_PATH=str(db_path))
    with app.app_context():
        assert models.get_membership("Legacy")["status"] == "None"
