# ACEest Fitness & Gym - DevOps CI/CD

A Flask web application for ACEest Fitness & Gym, with a fully automated CI/CD pipeline:
Git/GitHub → Jenkins → Pytest → SonarQube → Docker → Docker Hub → Kubernetes. Releases go out with five deployment strategies, and every one has an automatic rollback.

```
 git push ──► GitHub ──(poll / webhook)──► Jenkins
                                              │
   lint ─► pytest + coverage ─► SonarQube + quality gate ─► source artifact
                                              │
   docker build (test + runtime) ─► pytest inside the container ─► push to Docker Hub
                                              │
   scripts/deploy.sh <strategy> ─► smoke tests ─► (failure) scripts/rollback.sh
                                              │
   Kubernetes (Minikube / cloud): rolling | blue-green | canary | A/B | shadow
```

## Repository layout

| Path | Contents |
|---|---|
| `ACEest_Fitness.py` | application entry point (`gunicorn ACEest_Fitness:app`) |
| `aceest/` | Flask package: application factory, blueprints, models, templates |
| `tests/` | Pytest suite (113 tests, 99% coverage) |
| `legacy_versions/` | original Tkinter releases (Aceestver-1.0 … 3.2.4) that were migrated |
| `Dockerfile` | multi-stage build: `test` stage runs pytest, `runtime` stage is the deployable image |
| `Jenkinsfile` | CI/CD pipeline |
| `sonar-project.properties` | SonarQube configuration |
| `k8s/` | Kubernetes manifests, one folder per deployment strategy |
| `scripts/` | bootstrap, deploy, rollback and build-all-versions scripts |
| `jenkins/` | local Jenkins + SonarQube stack and setup guide |
| `docs/` | project report and SonarQube report |

## Application versions

Each release of the original desktop application was ported to Flask on a feature branch, merged to `main` with `--no-ff` and tagged:

| Tag | Ported from | Features |
|---|---|---|
| `v1.0.0` | Aceestver-1.0 | programme catalogue (Fat Loss / Muscle Gain / Beginner), workout + diet charts, `/health`, `/version` |
| `v1.1.0` | Aceestver-1.1, 1.1.2 | calorie calculator (weight × programme factor), input validation |
| `v2.0.0` | Aceestver-2.0.1, 2.1.2 | SQLite persistence: clients and weekly adherence, CSRF protection |
| `v2.2.0` | Aceestver-2.2.1, 2.2.4 | body metrics, workouts with exercises, BMI, progress summary |
| `v3.0.0` | Aceestver-3.0.1 | login, hashed passwords, Admin / Trainer roles |
| `v3.1.0` | Aceestver-3.1.2 | training plan generator, PDF client report |
| `v3.2.0` | Aceestver-3.2.4 | membership renewals, gym dashboard, in-place schema migration |
| `v3.2.1` | hotfix | serialised database start-up (multi-worker / multi-pod race) |
| `v3.2.2` | quality | SonarQube findings resolved (0 issues, gate passed) |

Branches follow `feature/*`, `hotfix/*`, `infra/*`, `chore/*` and `docs/*`. Commits use Conventional Commit prefixes (`feat`, `fix`, `ci`, `deploy`, `refactor`, `docs`).

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export ADMIN_PASSWORD=changeme SECRET_KEY=dev           # Windows: set ADMIN_PASSWORD=changeme
python ACEest_Fitness.py                                # http://localhost:5000  (login: admin / changeme)
pytest --cov=aceest                                     # unit tests + coverage
flake8                                                  # lint
```

With Docker:

```bash
docker build --target test -t aceest-fitness-test . && docker run --rm aceest-fitness-test
docker build --target runtime --build-arg APP_VERSION=$(cat VERSION) -t aceest-fitness:$(cat VERSION) .
docker run -p 5000:5000 -e ADMIN_PASSWORD=changeme -e SECRET_KEY=dev aceest-fitness:$(cat VERSION)
```

## Main endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `/`, `/programs/<FL\|MG\|BG>`, `/calculator` | public | programme catalogue and calorie calculator |
| `/health`, `/version` | public | probes; `/version` shows which release and track served the request |
| `/login`, `/clients`, `/clients/<name>`, `/dashboard` | login | web UI |
| `/api/programs`, `/api/calories?weight=&program=` | public | JSON API |
| `/api/login`, `/api/csrf-token`, `/api/me` | - | API session (send `X-CSRFToken` on writes) |
| `/api/clients[/<name>]` | login | clients CRUD (delete: Admin only) |
| `/api/clients/<name>/{progress,metrics,workouts,bmi,summary,plan,membership}` | login | tracking API |
| `/clients/<name>/report.pdf` | login | PDF report |
| `/api/users` | Admin | create Trainer / Admin accounts |

## CI/CD pipeline (Jenkins)

`Jenkinsfile` stages: **Checkout → Install → Lint → Unit Tests → SonarQube Analysis → Quality Gate → Build Artifact → Docker Build → Test In Container → Push to Docker Hub → Deploy to Kubernetes**.

* Triggered by `pollSCM('H/2 * * * *')`, and by a GitHub webhook if one is configured.
* Build artifacts: `dist/aceest-fitness-<version>-build<N>.tar.gz`, JUnit and coverage reports, plus the pushed image name.
* Images are tagged `<user>/aceest-fitness:<version>-<build>`, `:<version>` and `:latest`.
* The `DEPLOY_STRATEGY` parameter chooses the release strategy; `ROLLBACK_ONLY` rolls a strategy back by hand.

`jenkins/README.md` explains how to stand up Jenkins and SonarQube with Docker Compose and configure credentials.

## Docker Hub: all versions

```bash
docker login
scripts/build-all-versions.sh <dockerhub-user>/aceest-fitness --push
```

The script builds every `v*` tag, runs that version's own test suite inside its image, and pushes `:<version>` and `:latest`.

## Kubernetes deployment strategies

```bash
minikube start --driver=docker
minikube addons enable ingress
export ADMIN_PASSWORD=changeme
scripts/k8s-bootstrap.sh <dockerhub-user>/aceest-fitness:3.2.1     # all environments on the stable release
scripts/deploy.sh <strategy> <dockerhub-user>/aceest-fitness:3.2.2  # release the new version
scripts/rollback.sh <strategy>                                       # back to the last stable version
```

The ingress hosts use `nip.io` (`<name>.<minikube-ip>.nip.io`), so no hosts-file edits are needed. On Docker Desktop / Windows, run `minikube tunnel` and set `INGRESS_DOMAIN=127.0.0.1.nip.io`.

| Strategy | Endpoint | How it works | Rollback |
|---|---|---|---|
| Rolling update | `rolling.<domain>` | 3 replicas, `maxSurge 1`, `maxUnavailable 0`, readiness probes | `kubectl rollout undo` |
| Blue-green | `bluegreen.<domain>` (idle slot: `bluegreen-preview.<domain>`) | new release goes to the idle slot, is smoke-tested through the preview service, then the live service selector is switched | switch the selector back (old slot is still running) |
| Canary | `canary.<domain>` | candidate gets 10 → 25 → 50 → 100 % of traffic (ingress-nginx weight); health and restart checks at each step, then promoted to stable | weight 0 + undo candidate (and stable if already promoted) |
| A/B testing | `ab.<domain>` | variant B by header `X-Variant: B`, cookie `ab_variant=always`, otherwise a 50/50 split | undo variant B |
| Shadow | `shadow.<domain>` | NGINX proxy serves users from the primary and mirrors every request to the shadow, which has its own throw-away database; shadow 5xx errors fail the release | undo shadow |

Check which version and track answered a request with `curl http://<host>/version`.

### Live environment (Minikube on the build machine)

* Docker Hub: <https://hub.docker.com/r/bmudit/aceest-fitness> (tags `1.0.0` … `3.2.2`, `latest` and per-build `3.2.2-<build>`)
* Jenkins job `aceest-fitness-devops`: build #4 released `3.2.2-4` through all five strategies
* With Docker Desktop on Windows the Minikube IP is not reachable from the host. Expose the ingress controller instead:

  ```bash
  kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8088:80
  ```

  then open `http://rolling.127.0.0.1.nip.io:8088`, `bluegreen.…`, `bluegreen-preview.…`, `canary.…`, `ab.…` and `shadow.…` (same port). Alternatively run `minikube tunnel` from an administrator terminal and drop `:8088`.
