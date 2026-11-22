# Jenkins controller with the tools the ACEest pipeline needs:
# Python 3 (pytest / flake8), Docker CLI (image builds), kubectl (deployments) and bash (deploy scripts).
FROM jenkins/jenkins:2.580.2-alpine-jdk21

USER root
RUN apk add --no-cache python3 py3-pip bash curl ca-certificates

COPY --from=docker:27.4-cli /usr/local/bin/docker /usr/local/bin/docker
RUN curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.31.4/bin/linux/amd64/kubectl \
 && chmod +x /usr/local/bin/kubectl

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
