import random

import pytest

from aceest.fitness import ValidationError
from aceest.generator import EXERCISE_POOL, generate_plan
from aceest.reports import build_client_report


@pytest.mark.parametrize("level,days,per_day", [("beginner", 3, 3), ("Intermediate", 4, 4), ("advanced", 5, 4)])
def test_generate_plan_shape(level, days, per_day):
    result = generate_plan("MG", level, rng=random.Random(42))
    assert result["days"] == days
    assert result["focus"] == "Hypertrophy"
    assert len(result["plan"]) == days * per_day
    assert len({item["day"] for item in result["plan"]}) == days


def test_generate_plan_respects_ranges_and_focus():
    result = generate_plan("FL", "beginner", rng=random.Random(7))
    for item in result["plan"]:
        assert item["exercise"] in EXERCISE_POOL["Conditioning"]
        assert 2 <= item["sets"] <= 3
        assert 8 <= item["reps"] <= 12


def test_generate_plan_unknown_program_defaults_to_full_body():
    assert generate_plan(None, "beginner")["focus"] == "Full Body"


def test_generate_plan_is_deterministic_with_seed():
    assert generate_plan("BG", "advanced", random.Random(1)) == generate_plan("BG", "advanced", random.Random(1))


@pytest.mark.parametrize("level", ["", "expert", None])
def test_generate_plan_rejects_unknown_level(level):
    with pytest.raises(ValidationError):
        generate_plan("BG", level)


def test_plan_api(client, sample_client):
    assert client.get("/api/clients/Arun/plan").status_code == 404
    resp = client.post("/api/clients/Arun/plan", json={"level": "intermediate"})
    assert resp.status_code == 201
    assert resp.get_json()["focus"] == "Conditioning"
    latest = client.get("/api/clients/Arun/plan").get_json()
    assert latest["level"] == "intermediate" and len(latest["plan"]) == 16
    assert client.post("/api/clients/Arun/plan", json={"level": "pro"}).status_code == 400
    assert client.post("/api/clients/ghost/plan", json={"level": "beginner"}).status_code == 404
    assert client.get("/api/clients/ghost/plan").status_code == 404


def test_plan_form_and_page(client, sample_client):
    resp = client.post("/clients/Arun/plan", data={"level": "beginner"}, follow_redirects=True)
    assert b"Workout plan generated" in resp.data
    assert b"Beginner &middot; Conditioning" in resp.data
    resp = client.post("/clients/Arun/plan", data={"level": "x"}, follow_redirects=True)
    assert b"level must be one of" in resp.data


def test_pdf_report_download(client, sample_client):
    client.post("/api/clients/Arun/plan", json={"level": "beginner"})
    resp = client.get("/clients/Arun/report.pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")
    assert 'filename="Arun_report.pdf"' in resp.headers["Content-Disposition"]
    assert client.get("/clients/ghost/report.pdf").status_code == 404


def test_build_report_handles_non_latin_names():
    summary = {"client": {"name": "Kavin க", "age": None, "height": None, "weight": None,
                          "program": "BG", "calories": None},
               "weeks_logged": 0, "average_adherence": 0, "workouts_logged": 0, "training_minutes": 0}
    assert build_client_report(summary).startswith(b"%PDF")
