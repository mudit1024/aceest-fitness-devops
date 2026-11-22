# SonarQube Report - ACEest Fitness & Gym

| | |
|---|---|
| Project key | `aceest-fitness` |
| Analysed version | 3.2.2 (`main`) |
| Server | SonarQube 10.7 Community (`jenkins/docker-compose.yml`) |
| Scanner | SonarScanner CLI 11.1, configured by `sonar-project.properties` |
| Quality gate | **Sonar way: PASSED** |

The raw API exports are in this folder: `measures.json`, `quality-gate.json` and `analyses.json` (exported after Jenkins builds #2 to #4), plus `quality-gate-definition.json` and `files.json`.

The Jenkins pipeline analyses every build. Its latest analysis (build #4, Python 3.14 agent) also **passed** the gate: 0 bugs, 0 vulnerabilities, 0 code smells, 0 hotspots, 98.6 % coverage. The figures below come from the detailed analysis of 3.2.2 in the Python 3.12 test container.

## Overall result

| Metric | Value | Rating |
|---|---|---|
| Bugs | 0 | Reliability **A** |
| Vulnerabilities | 0 | Security **A** |
| Security hotspots | 0 open | Security review **A** |
| Code smells | 0 | Maintainability **A** (technical debt 0 min) |
| Coverage | 99.1 % (line 99.1 %, branch 99.3 %) | |
| Duplications | 0.0 % | |
| Unit tests | 113 passed, 0 failed, 0 errors | |
| Size | 1,298 lines of code, 23 files, 97 functions | |
| Complexity | cyclomatic 234, cognitive 156 | |

## Quality gate conditions (Sonar way, new code since 3.2.1)

| Condition | Threshold | Actual | Status |
|---|---|---|---|
| New issues | > 0 fails | 0 | OK |
| Coverage on new code | < 80 % fails | 98.1 % | OK |
| Duplicated lines on new code | > 3 % fails | 0.0 % | OK |
| Security hotspots reviewed | < 100 % fails | no open hotspots | OK |

Jenkins enforces the gate in the **Quality Gate** stage with `waitForQualityGate abortPipeline: true`. A failing gate stops the build before any image is built or pushed.

## Findings and how they were resolved

The first analysis of release 3.2.1 passed the gate but reported findings. All of them were fixed in release 3.2.2 rather than marked as "won't fix":

| Rule | Where | Finding | Fix |
|---|---|---|---|
| python:S4502 / S6965 (hotspot, CSRF) | `auth.py` login, `clients.py` clients page, `main.py` calculator | One view accepted both safe (GET) and unsafe (POST) methods | Split into separate GET and POST views; all POSTs are protected by Flask-WTF `CSRFProtect` |
| python:S1192 | `routes/clients.py`, `membership.py`, `tracking.py` | `"client not found"` and `"clients.client_page"` repeated | Shared `client_not_found()` / `back_to_client()` helpers in `aceest/routes/__init__.py` |
| python:S1192 | `generator.py` | `"Full Body"` repeated 3 times | `FULL_BODY` constant |
| Web:S6840 | `templates/login.html` | `autocomplete` used on an input without an explicit `type` | Added `type="text"` |

Issues avoided during development, because SonarLint flagged them in the editor:

* routes without explicit HTTP methods (S6965): every route declares `methods=[...]`
* CSRF protection disabled in application config (S4502): the test-only override lives in `tests/conftest.py`
* hard-coded secret key: `SECRET_KEY` comes from the environment (a Kubernetes Secret), with a random fallback
* SQL built with string formatting: all queries use bound parameters
* pseudo-random generator in application code (S2245): the plan generator uses `secrets.SystemRandom`

## Per-file coverage

| File | Lines of code | Coverage |
|---|---|---|
| aceest/models.py | 245 | 100 % |
| aceest/routes/tracking.py | 124 | 99.3 % |
| aceest/auth.py | 111 | 100 % |
| aceest/db.py | 108 | 100 % |
| aceest/routes/clients.py | 95 | 100 % |
| aceest/programs.py | 66 | 100 % |
| aceest/routes/main.py | 66 | 100 % |
| aceest/fitness.py | 39 | 100 % |
| aceest/routes/membership.py | 39 | 100 % |
| aceest/generator.py | 35 | 100 % |
| aceest/reports.py | 30 | 100 % |
| aceest/__init__.py | 26 | 100 % |
| aceest/config.py | 20 | 90.9 % |
| ACEest_Fitness.py | 5 | entry point (run by gunicorn) |

## Reproducing the analysis

```bash
docker compose -f jenkins/docker-compose.yml up -d sonarqube
# run the tests inside the test image to produce reports/coverage.xml and reports/junit.xml
docker build --target test -t aceest-fitness-test .
docker run --rm -v "$PWD/reports:/app/reports" aceest-fitness-test \
  python -m pytest --junitxml=/app/reports/junit.xml --cov=aceest --cov-report=xml:/app/reports/coverage.xml
docker run --rm -e SONAR_HOST_URL=http://host.docker.internal:9000 -e SONAR_TOKEN=<token> \
  -v "$PWD:/usr/src" sonarsource/sonar-scanner-cli:11.1
```
