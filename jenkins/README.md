# Jenkins and SonarQube setup

## 1. Start the stack

```bash
export DOCKERHUB_USER=<your-dockerhub-username>
docker compose -f jenkins/docker-compose.yml up -d --build
docker exec aceest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

* Jenkins: http://localhost:8080 (unlock it with the password printed above and choose *Install suggested plugins*; the plugins in `plugins.txt` are already installed).
* SonarQube: http://localhost:9000 (first login `admin` / `admin`; you will be asked to change the password).

## 2. SonarQube

1. **My Account → Security → Generate Token** (type *Global Analysis Token*). Copy the token.
2. **Administration → Configuration → Webhooks → Create**
   * Name: `jenkins`
   * URL: `http://aceest-jenkins:8080/sonarqube-webhook/`

   Jenkins needs this webhook for the `waitForQualityGate` step.
3. The project uses the default **Sonar way** quality gate. The project key is `aceest-fitness` (see `sonar-project.properties`).

## 3. Jenkins configuration

**Manage Jenkins → Credentials → System → Global → Add Credentials**

| ID | Kind | Value |
|----|------|-------|
| `dockerhub-creds` | Username with password | Docker Hub username + access token |
| `kubeconfig` | Secret file | kubeconfig for the Minikube / cloud cluster (see below) |
| `sonarqube-token` | Secret text | token from step 2.1 |

**Manage Jenkins → System**

* *SonarQube servers*: enable environment variables, then add a server named `SonarQube` with URL `http://aceest-sonarqube:9000` and the `sonarqube-token` credential.
* *Global properties → Environment variables*: `DOCKERHUB_USER = <your-dockerhub-username>`

**Manage Jenkins → Tools**

* *SonarQube Scanner installations*: add one named `SonarScanner` and tick *Install automatically*.

## 4. Pipeline job

1. **New Item → Multibranch Pipeline** (or *Pipeline* with *Pipeline script from SCM*) named `aceest-fitness`.
2. Source: the GitHub repository URL. Script path: `Jenkinsfile`.
3. The `pollSCM('H/2 * * * *')` trigger in the Jenkinsfile polls GitHub every 2 minutes. For instant builds, also add a GitHub webhook: **repo → Settings → Webhooks → `http://<jenkins-host>:8080/github-webhook/`** (needs a public URL, e.g. through ngrok).

## 5. kubeconfig for Minikube

Jenkins runs in a container, so it needs a kubeconfig whose server address it can reach and whose certificates are embedded:

```bash
minikube start --driver=docker
minikube addons enable ingress
kubectl config view --flatten --minify > kubeconfig-jenkins.yaml
# Connect the minikube network to the Jenkins container so the API server is reachable:
docker network connect minikube aceest-jenkins
```

Upload `kubeconfig-jenkins.yaml` as the `kubeconfig` secret file credential.
If Jenkins and Minikube run on different machines, use the cluster's public API address instead.

## 6. Pipeline stages

| Stage | What it does |
|-------|--------------|
| Checkout | reads `VERSION`, sets the image tag `<version>-<build>` |
| Install / Lint | virtualenv + `flake8` |
| Unit Tests | `pytest` with JUnit and coverage reports |
| SonarQube Analysis / Quality Gate | static analysis; the build fails if the gate fails |
| Build Artifact | versioned source archive `dist/aceest-fitness-<version>-build<N>.tar.gz` |
| Docker Build | `test` and `runtime` images from the multi-stage Dockerfile |
| Test In Container | runs the pytest suite inside the built image |
| Push to Docker Hub | pushes `<version>-<build>`, `<version>` and `latest` (main branch only) |
| Deploy to Kubernetes | `scripts/deploy.sh <strategy>`: smoke tests, then automatic rollback on failure |

Run **Build with Parameters → ROLLBACK_ONLY** to roll a strategy back by hand.
