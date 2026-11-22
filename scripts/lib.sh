#!/usr/bin/env bash
# Shared helpers for the deployment scripts.
set -euo pipefail

NS="${NAMESPACE:-aceest}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K8S_DIR="${ROOT_DIR}/k8s"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

log()  { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }
fail() { printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# Domain used for the ingress hosts, e.g. rolling.<domain>.
# Defaults to <minikube ip>.nip.io which resolves without editing /etc/hosts.
ingress_domain() {
  if [[ -n "${INGRESS_DOMAIN:-}" ]]; then
    echo "${INGRESS_DOMAIN}"
  elif command -v minikube >/dev/null 2>&1; then
    echo "$(minikube ip).nip.io"
  else
    echo "127.0.0.1.nip.io"
  fi
}

# Render manifests (replace __IMAGE__ / __DOMAIN__) and apply them.
apply_dir() {
  local dir="$1" image="$2" domain
  domain="$(ingress_domain)"
  for f in "${K8S_DIR}/${dir}"/*.yaml; do
    echo "---"   # document separator: files must not merge into one object
    sed -e "s#__IMAGE__#${image}#g" -e "s#__DOMAIN__#${domain}#g" "$f"
  done | kubectl apply -f -
}

wait_rollout() {
  kubectl -n "$NS" rollout status "deployment/$1" --timeout="$ROLLOUT_TIMEOUT"
}

set_image() {
  local deploy="$1" image="$2"
  kubectl -n "$NS" set image "deployment/${deploy}" "aceest=${image}"
  kubectl -n "$NS" annotate "deployment/${deploy}" --overwrite \
    "kubernetes.io/change-cause=deploy ${image} (build ${BUILD_NUMBER:-manual})"
}

current_image() {
  kubectl -n "$NS" get "deployment/$1" -o jsonpath='{.spec.template.spec.containers[0].image}'
}

# Calls an endpoint from inside a pod of the given deployment, through the given service.
# Usage: in_cluster_get <deployment> <url>
in_cluster_get() {
  kubectl -n "$NS" exec "deployment/$1" -c aceest -- \
    python -c "import sys,urllib.request; print(urllib.request.urlopen(sys.argv[1], timeout=5).read().decode())" "$2"
}

# Smoke test: /health must be ok and /version must report the expected version.
# Usage: smoke_test <deployment> <service> [expected-version]
smoke_test() {
  local deploy="$1" svc="$2" expected="${3:-}" body
  log "Smoke testing service ${svc}"
  for attempt in 1 2 3 4 5; do
    if body="$(in_cluster_get "$deploy" "http://${svc}/health" 2>/dev/null)" && [[ "$body" == *'"ok"'* ]]; then
      break
    fi
    if [[ $attempt == 5 ]]; then fail "health check failed for ${svc}"; fi
    sleep 3
  done
  body="$(in_cluster_get "$deploy" "http://${svc}/version")"
  echo "  /version -> ${body}"
  if [[ -n "$expected" && "$body" != *"\"version\":\"${expected}\""* ]]; then
    fail "${svc} reports wrong version (expected ${expected})"
  fi
}

# Extracts the application version from an image reference: repo/name:3.2.0-15 -> 3.2.0
version_from_image() {
  local tag="${1##*:}"
  echo "${tag%%-*}"
}
