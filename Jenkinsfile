// ACEest Fitness & Gym - CI/CD pipeline
//
// Required Jenkins setup (see jenkins/README.md):
//   * credentials  : 'dockerhub-creds' (username + access token)
//                    'kubeconfig'      (secret file for the Minikube / cloud cluster)
//   * SonarQube    : server named 'SonarQube' + scanner tool named 'SonarScanner'
//   * global env   : DOCKERHUB_USER (Docker Hub account / namespace)
pipeline {
    agent any

    parameters {
        choice(name: 'DEPLOY_STRATEGY',
               choices: ['rolling', 'blue-green', 'canary', 'ab-testing', 'shadow', 'all', 'none'],
               description: 'Deployment strategy used for this release (main branch only)')
        booleanParam(name: 'ROLLBACK_ONLY', defaultValue: false,
                     description: 'Skip the build and roll the selected strategy back to its last stable version')
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
        timeout(time: 45, unit: 'MINUTES')
    }

    triggers {
        // Poll GitHub every 2 minutes; a GitHub webhook also triggers immediately.
        pollSCM('H/2 * * * *')
    }

    environment {
        IMAGE_REPO = "${env.DOCKERHUB_USER ?: 'aceest'}/aceest-fitness"
        VENV       = "${WORKSPACE}/.venv"
    }

    stages {
        stage('Rollback') {
            when { expression { params.ROLLBACK_ONLY } }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh "bash scripts/rollback.sh ${params.DEPLOY_STRATEGY}"
                }
            }
        }

        stage('Checkout') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                script {
                    def scmVars   = checkout scm
                    env.GIT_BRANCH = scmVars.GIT_BRANCH ?: env.GIT_BRANCH
                    env.APP_VERSION = readFile('VERSION').trim()
                    env.GIT_SHORT   = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG   = "${env.APP_VERSION}-${env.BUILD_NUMBER}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.APP_VERSION} (${env.GIT_SHORT})"
                }
            }
        }

        stage('Install') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                sh '''
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install -q -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                sh 'mkdir -p reports && "$VENV/bin/flake8" --tee --output-file=reports/flake8.txt'
            }
        }

        stage('Unit Tests') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                sh '''
                    mkdir -p reports
                    "$VENV/bin/pytest" --junitxml=reports/junit.xml \
                        --cov=aceest --cov-report=xml:reports/coverage.xml --cov-report=term
                '''
            }
            post {
                always { junit 'reports/junit.xml' }
            }
        }

        stage('SonarQube Analysis') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh "${tool 'SonarScanner'}/bin/sonar-scanner -Dsonar.projectVersion=${env.APP_VERSION}"
                }
            }
        }

        stage('Quality Gate') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Artifact') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                sh '''
                    mkdir -p dist
                    git archive --format=tar.gz --prefix=aceest-fitness-${APP_VERSION}/ \
                        -o dist/aceest-fitness-${APP_VERSION}-build${BUILD_NUMBER}.tar.gz HEAD
                '''
                archiveArtifacts artifacts: 'dist/*.tar.gz', fingerprint: true
            }
        }

        stage('Docker Build') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                sh '''
                    docker build --target test    -t aceest-fitness-test:${IMAGE_TAG} .
                    docker build --target runtime --build-arg APP_VERSION=${APP_VERSION} \
                        -t ${IMAGE_REPO}:${IMAGE_TAG} -t ${IMAGE_REPO}:${APP_VERSION} .
                '''
            }
        }

        stage('Test In Container') {
            when { expression { !params.ROLLBACK_ONLY } }
            steps {
                // The Docker daemon may not see the Jenkins workspace path (Jenkins in a container),
                // so the JUnit report is copied out of the test container instead of bind-mounted.
                sh '''
                    mkdir -p reports
                    docker rm -f aceest-test-${BUILD_NUMBER} >/dev/null 2>&1 || true
                    set +e
                    docker run --name aceest-test-${BUILD_NUMBER} aceest-fitness-test:${IMAGE_TAG}
                    rc=$?
                    set -e
                    docker cp aceest-test-${BUILD_NUMBER}:/app/reports/junit-container.xml reports/junit-container.xml || true
                    docker rm -f aceest-test-${BUILD_NUMBER} >/dev/null
                    exit $rc
                '''
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'reports/junit-container.xml' }
            }
        }

        stage('Push to Docker Hub') {
            when { allOf { expression { isMainBranch() }; expression { !params.ROLLBACK_ONLY } } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                                  usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE_REPO}:${IMAGE_TAG}
                        docker push ${IMAGE_REPO}:${APP_VERSION}
                        docker tag  ${IMAGE_REPO}:${IMAGE_TAG} ${IMAGE_REPO}:latest
                        docker push ${IMAGE_REPO}:latest
                    '''
                }
                sh 'echo "${IMAGE_REPO}:${IMAGE_TAG}" > dist/image.txt'
                archiveArtifacts artifacts: 'dist/image.txt', fingerprint: true
            }
        }

        stage('Deploy to Kubernetes') {
            when {
                allOf {
                    expression { isMainBranch() }
                    expression { !params.ROLLBACK_ONLY && params.DEPLOY_STRATEGY != 'none' }
                }
            }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    // deploy.sh smoke-tests the release and rolls back automatically on failure
                    sh "bash scripts/deploy.sh ${params.DEPLOY_STRATEGY} ${env.IMAGE_REPO}:${env.IMAGE_TAG}"
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
            sh 'docker logout || true'
        }
        success {
            echo "Build ${currentBuild.displayName} succeeded"
        }
        failure {
            echo "Build ${currentBuild.displayName} failed - see stage logs; deployments are rolled back by scripts/deploy.sh"
        }
    }
}

// Works for both multibranch jobs (BRANCH_NAME) and plain pipeline jobs (GIT_BRANCH).
def isMainBranch() {
    return env.BRANCH_NAME == 'main' || (env.GIT_BRANCH ?: '') ==~ /(origin\/)?main/
}
