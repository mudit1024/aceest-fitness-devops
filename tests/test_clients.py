from datetime import date

import pytest

from aceest import models
from aceest.fitness import ValidationError


def test_create_client_derives_calories(sample_client):
    assert sample_client["name"] == "Arun"
    assert sample_client["calories"] == 80 * 22


def test_save_client_updates_existing_record(client, sample_client):
    resp = client.post("/api/clients", json={"name": "Arun", "weight": 90, "program": "MG"})
    assert resp.status_code == 201
    assert resp.get_json()["calories"] == 90 * 35
    assert len(client.get("/api/clients").get_json()) == 1


@pytest.mark.parametrize("payload,message", [
    ({"program": "FL"}, "name is required"),
    ({"name": "X", "program": "ZZ"}, "program must be one of"),
    ({"name": "X", "program": "FL", "age": "old"}, "age must be a number"),
    ({"name": "X", "program": "FL", "height": -1}, "height must not be negative"),
    ({"name": "X", "program": "FL", "target_adherence": 150}, "adherence must be between"),
])
def test_create_client_validation(client, payload, message):
    resp = client.post("/api/clients", json=payload)
    assert resp.status_code == 400
    assert message in resp.get_json()["error"]


def test_get_and_delete_client(client, sample_client):
    assert client.get("/api/clients/Arun").get_json()["program"] == "FL"
    assert client.delete("/api/clients/Arun").status_code == 204
    assert client.get("/api/clients/Arun").status_code == 404
    assert client.delete("/api/clients/Arun").status_code == 404


def test_progress_api(client, sample_client):
    first = {"adherence": 70, "week": "Week 01 - 2026"}
    assert client.post("/api/clients/Arun/progress", json=first).status_code == 201
    assert client.post("/api/clients/Arun/progress", json={"adherence": 90}).status_code == 201
    entries = client.get("/api/clients/Arun/progress").get_json()
    assert [e["adherence"] for e in entries] == [70, 90]
    assert entries[0]["week"] == "Week 01 - 2026"


def test_progress_api_errors(client, sample_client):
    assert client.post("/api/clients/Arun/progress", json={"adherence": 101}).status_code == 400
    assert client.post("/api/clients/Nobody/progress", json={"adherence": 50}).status_code == 404
    assert client.get("/api/clients/Nobody/progress").status_code == 404


def test_current_week_label():
    assert models.current_week_label(date(2026, 1, 15)) == "Week 02 - 2026"


def test_clean_client_without_weight_has_no_calories():
    assert models.clean_client({"name": "Z", "program": "bg"})["calories"] is None
    with pytest.raises(ValidationError):
        models.clean_client({"name": "Z", "program": "BG", "weight": 0, "age": -3})


def test_clients_html_flow(client):
    resp = client.post("/clients", data={"name": "Meena", "weight": "60", "program": "BG"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Client Meena saved" in resp.data
    assert b"1560 kcal/day" in resp.data

    resp = client.post("/clients/Meena/progress", data={"adherence": "80"}, follow_redirects=True)
    assert b"Weekly progress logged" in resp.data
    assert b"width: 80%" in resp.data

    assert b"Meena" in client.get("/clients").data


def test_clients_html_errors(client):
    resp = client.post("/clients", data={"name": "", "program": "BG"})
    assert b"name is required" in resp.data
    assert client.get("/clients/ghost").status_code == 404
    assert client.post("/clients/ghost/progress", data={"adherence": "5"}).status_code == 404


def test_progress_form_validation(client, sample_client):
    resp = client.post("/clients/Arun/progress", data={"adherence": "abc"}, follow_redirects=True)
    assert b"adherence must be an integer" in resp.data
