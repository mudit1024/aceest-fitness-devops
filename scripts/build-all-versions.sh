#!/usr/bin/env bash
# Builds and pushes one Docker image per release tag (v1.0.0 ... v3.2.0) so the
# registry holds every version of the application.
#
# Usage: scripts/build-all-versions.sh <dockerhub-user>/aceest-fitness [--push]
set -euo pipefail

REPO="${1:?usage: $0 <repo> [--push]}"
PUSH="${2:-}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cd "$ROOT_DIR"
for tag in $(git tag --list 'v*' --sort=version:refname); do
  version="${tag#v}"
  echo "==> ${tag}"
  rm -rf "${WORK:?}/src" && mkdir -p "$WORK/src"
  git archive "$tag" | tar -x -C "$WORK/src"
  # Older tags pre-date some build files; always build with the current Dockerfile.
  cp Dockerfile .dockerignore "$WORK/src/"
  docker build --target test -t "aceest-fitness-test:${version}" "$WORK/src"
  docker run --rm "aceest-fitness-test:${version}"
  docker build --target runtime --build-arg APP_VERSION="$version" -t "${REPO}:${version}" "$WORK/src"
  if [[ "$PUSH" == "--push" ]]; then
    docker push "${REPO}:${version}"
  fi
done

latest="$(git tag --list 'v*' --sort=version:refname | tail -1)"
docker tag "${REPO}:${latest#v}" "${REPO}:latest"
if [[ "$PUSH" == "--push" ]]; then docker push "${REPO}:latest"; fi
echo "Built: $(git tag --list 'v*' | tr '\n' ' ')"
