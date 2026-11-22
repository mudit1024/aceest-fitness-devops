// ACEest Fitness & Gym - CI pipeline
// Required Jenkins setup (see jenkins/README.md):
//   * credentials  : 'dockerhub-creds' (username/password or token)
//   * SonarQube    : server named 'SonarQube' + scanner tool named 'SonarScanner'
pipeline {
    agent any

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
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
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.APP_VERSION = readFile('VERSION').trim()
                    env.GIT_SHORT   = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG   = "${env.APP_VERSION}-${env.BUILD_NUMBER}"
                    currentBuild.displayName = "#${env.BUILD_NUMBER} v${env.APP_VERSION} (${env.GIT_SHORT})"
                }
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install -q -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh 'mkdir -p reports && "$VENV/bin/flake8" --tee --output-file=reports/flake8.txt'
            }
        }

        stage('Unit Tests') {
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
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh "${tool 'SonarScanner'}/bin/sonar-scanner -Dsonar.projectVersion=${env.APP_VERSION}"
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Artifact') {
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
            steps {
                sh '''
                    docker build --target test    -t aceest-fitness-test:${IMAGE_TAG} .
                    docker build --target runtime --build-arg APP_VERSION=${APP_VERSION} \
                        -t ${IMAGE_REPO}:${IMAGE_TAG} -t ${IMAGE_REPO}:${APP_VERSION} .
                '''
            }
        }

        stage('Test In Container') {
            steps {
                sh '''
                    mkdir -p reports
                    docker run --rm -v "$WORKSPACE/reports:/app/reports" aceest-fitness-test:${IMAGE_TAG}
                '''
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'reports/junit-container.xml' }
            }
        }

        stage('Push to Docker Hub') {
            when { branch 'main' }
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
            }
        }
    }

    post {
        always {
            archiveArtifacts allowEmptyArchive: true, artifacts: 'reports/**'
            sh 'docker logout || true'
        }
    }
}
