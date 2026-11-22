import pytest

from aceest.fitness import ValidationError, calculate_bmi


@pytest.mark.parametrize("height,weight,bmi,category", [
    (175, 50, 16.3, "Underweight"),
    (175, 70, 22.9, "Normal"),
    (175, 80, 26.1, "Overweight"),
    (170, 100, 34.6, "Obese"),
])
def test_calculate_bmi_categories(height, weight, bmi, category):
    result = calculate_bmi(height, weight)
    assert result["bmi"] == bmi
    assert result["category"] == category
    assert result["risk"]


@pytest.mark.parametrize("height,weight", [(0, 70), (175, None), ("tall", 70)])
def test_calculate_bmi_invalid(height, weight):
    with pytest.raises(ValidationError):
        calculate_bmi(height, weight)


def test_metrics_api(client, sample_client):
    resp = client.post("/api/clients/Arun/metrics", json={"date": "2026-03-01", "weight": 79.5, "waist": 88})
    assert resp.status_code == 201
    client.post("/api/clients/Arun/metrics", json={"date": "2026-03-08", "bodyfat": 19.5})
    metrics = client.get("/api/clients/Arun/metrics").get_json()
    assert [m["date"] for m in metrics] == ["2026-03-01", "2026-03-08"]


@pytest.mark.parametrize("payload", [{}, {"date": "01/03/2026", "weight": 80}, {"weight": -2}])
def test_metrics_api_validation(client, sample_client, payload):
    assert client.post("/api/clients/Arun/metrics", json=payload).status_code == 400


def test_workouts_api_with_exercises(client, sample_client):
    payload = {"date": "2026-03-02", "workout_type": "strength", "duration_min": 55, "notes": "PR day",
               "exercises": [{"name": "Back Squat", "sets": 5, "reps": 5, "weight": 120}]}
    resp = client.post("/api/clients/Arun/workouts", json=payload)
    assert resp.status_code == 201
    assert resp.get_json()["workout_type"] == "Strength"
    workouts = client.get("/api/clients/Arun/workouts").get_json()
    assert workouts[0]["exercises"][0] == {"name": "Back Squat", "sets": 5, "reps": 5, "weight": 120.0}


@pytest.mark.parametrize("payload", [
    {"workout_type": "Yoga"},
    {"workout_type": "Cardio", "exercises": [{"sets": 3}]},
    {"workout_type": "Cardio", "duration_min": "long"},
])
def test_workouts_api_validation(client, sample_client, payload):
    assert client.post("/api/clients/Arun/workouts", json=payload).status_code == 400


def test_bmi_and_summary_api(client, sample_client):
    assert client.get("/api/clients/Arun/bmi").get_json()["category"] == "Overweight"
    client.post("/api/clients/Arun/progress", json={"adherence": 60})
    client.post("/api/clients/Arun/progress", json={"adherence": 81})
    client.post("/api/clients/Arun/workouts", json={"workout_type": "Cardio", "duration_min": 30})
    client.post("/api/clients/Arun/metrics", json={"weight": 78})
    summary = client.get("/api/clients/Arun/summary").get_json()
    assert summary["weeks_logged"] == 2
    assert summary["average_adherence"] == 70.5
    assert summary["workouts_logged"] == 1
    assert summary["training_minutes"] == 30
    assert summary["last_metric"]["weight"] == 78


def test_bmi_requires_height_and_weight(client):
    client.post("/api/clients", json={"name": "NoData", "program": "BG"})
    assert client.get("/api/clients/NoData/bmi").status_code == 400


@pytest.mark.parametrize("url", ["metrics", "workouts", "bmi", "summary"])
def test_tracking_api_unknown_client(client, url):
    assert client.get(f"/api/clients/ghost/{url}").status_code == 404


def test_tracking_api_unknown_client_writes(client):
    assert client.post("/api/clients/ghost/metrics", json={"weight": 70}).status_code == 404
    assert client.post("/api/clients/ghost/workouts", json={"workout_type": "Cardio"}).status_code == 404


def test_client_page_forms(client, sample_client):
    resp = client.post("/clients/Arun/metrics", data={"weight": "79", "waist": "86"}, follow_redirects=True)
    assert b"Body metrics logged" in resp.data
    resp = client.post("/clients/Arun/workouts", data={
        "workout_type": "Hypertrophy", "duration_min": "45", "exercise_name": "Bench",
        "exercise_sets": "4", "exercise_reps": "10", "exercise_weight": "60"}, follow_redirects=True)
    assert b"Workout logged" in resp.data
    assert b"Bench 4x10 @60.0kg" in resp.data
    assert b"BMI      : 26.1 (Overweight)" in resp.data


def test_client_page_form_errors(client, sample_client):
    resp = client.post("/clients/Arun/metrics", data={}, follow_redirects=True)
    assert b"at least one of weight" in resp.data
    resp = client.post("/clients/Arun/workouts", data={"workout_type": "Dance"}, follow_redirects=True)
    assert b"workout_type must be one of" in resp.data
    assert client.post("/clients/ghost/metrics", data={"weight": "1"}).status_code == 404
