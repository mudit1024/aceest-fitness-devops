# Jenkins controller with the tools the ACEest pipeline needs:
# Python 3 (pytest / flake8), Docker CLI (image builds) and kubectl (deployments).
FROM jenkins/jenkins:2.479.3-lts-jdk17

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=docker:27.4-cli /usr/local/bin/docker /usr/local/bin/docker
RUN curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.31.4/bin/linux/amd64/kubectl \
 && chmod +x /usr/local/bin/kubectl

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
