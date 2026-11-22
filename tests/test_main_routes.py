def test_index_lists_programs(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Fat Loss (FL)" in resp.data
    assert b"BREAK-EVEN: 250 Members" in resp.data


def test_program_page(client):
    resp = client.get("/programs/MG")
    assert resp.status_code == 200
    assert b"Squat 5x5" in resp.data


def test_program_page_404(client):
    assert client.get("/programs/NOPE").status_code == 404


def test_api_programs(client):
    data = client.get("/api/programs").get_json()
    assert {"code": "BG", "name": "Beginner (BG)"} in data


def test_api_program_detail_and_404(client):
    assert client.get("/api/programs/fl").get_json()["code"] == "FL"
    assert client.get("/api/programs/zz").status_code == 404


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_version_reports_track(client, app):
    data = client.get("/version").get_json()
    assert data["version"] == app.config["APP_VERSION"]
    assert data["track"] == "stable"


def test_calculator_get(client):
    assert client.get("/calculator").status_code == 200


def test_calculator_post_shows_calories(client):
    resp = client.post("/calculator", data={"name": "Arun", "weight": "80", "program": "MG", "adherence": "75"})
    assert resp.status_code == 200
    assert b"Estimated Calories: 2800 kcal" in resp.data
    assert b"Adherence: 75%" in resp.data


def test_calculator_post_validation_error(client):
    resp = client.post("/calculator", data={"name": "", "weight": "80", "program": "MG"})
    assert b"name is required" in resp.data


def test_api_calories(client):
    expected = {"program": "FL", "calories": 1760}
    assert client.get("/api/calories?weight=80&program=fl").get_json() == expected
    assert client.get("/api/calories?weight=-1&program=fl").status_code == 400
