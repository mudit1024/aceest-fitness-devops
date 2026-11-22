#!/usr/bin/env bash
# Creates the namespace, secret and all five deployment-strategy environments,
# every one of them running the same (stable) image.
#
# Usage: scripts/k8s-bootstrap.sh <image>        e.g. myuser/aceest-fitness:3.1.0
# Env:   ADMIN_PASSWORD (required), SECRET_KEY (optional, generated if empty), INGRESS_DOMAIN (optional)
source "$(dirname "$0")/lib.sh"

IMAGE="${1:?usage: $0 <image>}"
: "${ADMIN_PASSWORD:?set ADMIN_PASSWORD for the seeded admin account}"
SECRET_KEY="${SECRET_KEY:-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')}"

log "Namespace and secret"
kubectl apply -f "${K8S_DIR}/base/namespace.yaml"
kubectl -n "$NS" create secret generic aceest-secrets \
  --from-literal=SECRET_KEY="${SECRET_KEY}" \
  --from-literal=ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  --dry-run=client -o yaml | kubectl apply -f -

for env in rolling-update blue-green canary ab-testing shadow; do
  log "Applying ${env} with ${IMAGE}"
  apply_dir "$env" "$IMAGE"
done

log "Waiting for all deployments"
for d in aceest-rolling aceest-blue aceest-green aceest-canary-stable aceest-canary-candidate \
         aceest-ab-a aceest-ab-b aceest-shadow-primary aceest-shadow-candidate aceest-mirror-proxy; do
  wait_rollout "$d"
done

DOMAIN="$(ingress_domain)"
log "Endpoints"
cat <<EOF
  Rolling update : http://rolling.${DOMAIN}
  Blue-green     : http://bluegreen.${DOMAIN}   (preview of idle slot: http://bluegreen-preview.${DOMAIN})
  Canary         : http://canary.${DOMAIN}
  A/B testing    : http://ab.${DOMAIN}          (force B: header 'X-Variant: B' or cookie ab_variant=always)
  Shadow         : http://shadow.${DOMAIN}
EOF
