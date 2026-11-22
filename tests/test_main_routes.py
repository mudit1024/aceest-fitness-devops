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
