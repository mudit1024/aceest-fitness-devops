# ACEest Fitness & Gym: CI/CD Pipeline Implementation

Introduction to DevOps (CSIZG514/SEZG514), Assignment 2

Student: Mudit Kumar Bhatnagar   ID: 2025TM93024   GitHub: https://github.com/mudit1024/aceest-fitness-devops

## 1. CI/CD Architecture Overview

The ACEest desktop application (ten Tkinter releases, Aceestver-1.0 to 3.2.4) was migrated to a modular Flask web application and delivered through a fully automated pipeline. The application package (`aceest/`) uses an application factory with separate blueprints for the catalogue, clients, tracking, membership and authentication. Data is stored in SQLite with parameterised queries and an in-place schema migration step.

The pipeline flows from a developer commit to a running Kubernetes release:

- **Version control (Git/GitHub):** each legacy release was ported on its own `feature/*` branch, merged with `--no-ff` and tagged (v1.0.0 to v3.2.0). Fixes and infrastructure work used `hotfix/*`, `infra/*`, `chore/*` and `docs/*` branches, leading to releases v3.2.1 and v3.2.2. Commits follow Conventional Commit prefixes.
- **Jenkins:** the declarative `Jenkinsfile` polls GitHub every two minutes (`pollSCM`); a GitHub webhook can trigger it instantly. Stages: Checkout → Install → Lint (flake8) → Unit Tests (pytest, JUnit and coverage) → SonarQube Analysis → Quality Gate → Build Artifact → Docker Build → Test In Container → Push to Docker Hub → Deploy to Kubernetes.
- **Testing:** 113 Pytest tests, at 99% line and branch coverage, run against an isolated temporary database. They cover business rules (calories, BMI, plan generation, membership dates), every HTML and JSON route, authentication, roles, CSRF protection, schema migration and concurrent start-up.
- **Code quality:** SonarQube analyses every build with the coverage and test reports. `waitForQualityGate abortPipeline: true` stops the build before any image is produced if the "Sonar way" gate fails.
- **Containerisation:** a multi-stage Dockerfile builds a `test` image (which runs the Pytest suite inside the container) and a slim, non-root `runtime` image served by gunicorn with a health check. Images are pushed to Docker Hub as `<version>-<build>`, `<version>` and `latest`. `scripts/build-all-versions.sh` publishes an image for every release tag.
- **Kubernetes:** five isolated environments in the `aceest` namespace, exposed through ingress-nginx on Minikube (`<strategy>.<minikube-ip>.nip.io`). Every Deployment has readiness and liveness probes, resource limits, a non-root security context, a 10-revision history and secrets injected from a Kubernetes Secret.

| Strategy | Mechanism | Rollback |
|---|---|---|
| Rolling update | 3 replicas, maxSurge 1, maxUnavailable 0 (zero downtime) | `kubectl rollout undo` |
| Blue-green | Release goes to the idle slot, is tested through a preview service, then the live Service selector is switched | Switch the selector back; the old slot is still running |
| Canary | Ingress weight 10 → 25 → 50 → 100 %, with health and restart checks at each step, then promotion | Weight 0 and undo the candidate (and stable if promoted) |
| A/B testing | Variant B by `X-Variant: B` header, `ab_variant` cookie, or a 50/50 split | Undo variant B |
| Shadow | NGINX mirrors every request to a shadow with its own database; its responses are discarded | Undo the shadow |

`scripts/deploy.sh` runs each release in a fail-fast subshell. It smoke-tests `/health` and `/version` (which must report the expected version) from inside the cluster, and calls `scripts/rollback.sh` automatically if any step fails. A `ROLLBACK_ONLY` pipeline parameter allows manual rollback from Jenkins.

## 2. Challenges Faced and Mitigation Strategies

- **Desktop code is not testable or deployable.** The legacy versions mixed Tkinter widgets, SQL and business logic in one class. *Mitigation:* the calculations were extracted into pure functions (`fitness.py`, `generator.py`) and data access into `models.py`, with thin Flask views on top. The logic can now be unit-tested without a UI, and it reached 99% coverage.
- **Race condition found during container testing.** Running the v3.2.0 image with two gunicorn workers crashed at start-up: both processes initialised the database at once and the second admin insert broke a UNIQUE constraint. The same would happen when pods of two releases share a volume during a rollout. Unit tests run in a single process, so they could not catch it. *Mitigation:* hotfix v3.2.1 wraps initialisation in `BEGIN IMMEDIATE`, makes seeding idempotent and adds a regression test with eight concurrent start-ups. The test fails without the fix.
- **Schema changes during zero-downtime releases.** Old and new pods run side by side during rolling, blue-green and canary releases. *Mitigation:* migrations are additive only (`ALTER TABLE … ADD COLUMN`), so the previous release keeps working against the upgraded schema and a rollback never needs a database downgrade.
- **Shadow traffic must not corrupt production data.** Mirrored POST requests would otherwise be written twice. *Mitigation:* the shadow Deployment uses its own throw-away database (emptyDir), and its responses are discarded by the NGINX `mirror` directive. Mirroring was verified end to end with Docker containers before writing the manifests.
- **Security findings and quality-gate failures.** SonarQube reported CSRF hotspots (views accepting both GET and POST) and duplicated literals. *Mitigation:* CSRF protection via Flask-WTF on every write, separate GET and POST views, shared helpers and constants. Secrets come only from environment variables or Kubernetes Secrets, and passwords are hashed. Release v3.2.2 has 0 bugs, 0 vulnerabilities, 0 code smells and 0 open hotspots.
- **Coverage not imported by SonarQube.** Tests ran inside a container, so `coverage.xml` contained container paths the scanner could not resolve. *Mitigation:* a `.coveragerc` with `relative_files = True`, which works both in Jenkins and in the container.
- **Building old tags with a newer pipeline.** Early tags pre-date some build files. *Mitigation:* `build-all-versions.sh` extracts each tag with `git archive`, builds it with the current Dockerfile and runs that version's own test suite inside its image. All eight releases pass (12 to 113 tests).
- **Rollback could be skipped silently.** An early version of the deploy script relied on an `ERR` trap, which does not fire when a helper calls `exit`, so a failed smoke test would not have triggered rollback. *Mitigation:* each strategy runs in a `set -e` subshell and its exit code is checked explicitly.

## 3. Key Automation Outcomes

- **Every commit is validated automatically:** lint, 113 unit tests, static analysis with an enforced quality gate, and the same tests again inside the built container image. A defect stops the pipeline before an image reaches the registry.
- **Traceable, versioned artifacts:** each build archives a versioned source bundle, JUnit and coverage reports, and the pushed image name. The registry holds an image for every application version (v1.0.0 to v3.2.2).
- **Measured quality:** SonarQube quality gate passed with A ratings for reliability, security, security review and maintainability, 99.1% coverage and 0% duplication.
- **Zero-downtime releases with five strategies:** rolling, blue-green, canary, A/B and shadow releases are driven by one script and one Jenkins parameter. Each is smoke-tested in the cluster before it takes traffic.
- **Automatic and manual rollback:** a failed release reverts to the last stable version without manual steps. A previous version can be restored on demand: in seconds for blue-green (selector switch) and through `kubectl rollout undo` for the others.
- **Reproducible environments:** the same image runs on a laptop, in Jenkins and in Kubernetes. Jenkins and SonarQube themselves are defined in `jenkins/docker-compose.yml`, so the whole toolchain can be rebuilt from the repository.

In summary, the project moved ACEest from manually distributed desktop builds to a test-driven, continuously delivered web service. Quality and release safety are now enforced by the pipeline rather than by manual checks.
