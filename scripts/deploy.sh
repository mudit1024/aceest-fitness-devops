#!/usr/bin/env bash
# Releases a new image using one of the deployment strategies.
#
# Usage: scripts/deploy.sh <rolling|blue-green|canary|ab-testing|shadow|all> <image>
#
# Every strategy verifies the new version with a smoke test and rolls back
# automatically (scripts/rollback.sh) if the release fails.
source "$(dirname "$0")/lib.sh"

STRATEGY="${1:?usage: $0 <strategy> <image>}"
IMAGE="${2:?usage: $0 <strategy> <image>}"
VERSION="$(version_from_image "$IMAGE")"
CANARY_STEPS="${CANARY_STEPS:-10 25 50 100}"
CANARY_PAUSE="${CANARY_PAUSE:-20}"

on_failure() {
  log "Release of ${IMAGE} with strategy '${STRATEGY}' FAILED - rolling back"
  bash "$(dirname "$0")/rollback.sh" "$STRATEGY" || true
  exit 1
}

# ---------------------------------------------------------------- rolling
deploy_rolling() {
  set_image aceest-rolling "$IMAGE"
  wait_rollout aceest-rolling
  smoke_test aceest-rolling aceest-rolling "$VERSION"
}

# ---------------------------------------------------------------- blue-green
deploy_blue_green() {
  local live idle
  live="$(kubectl -n "$NS" get svc aceest-bg -o jsonpath='{.spec.selector.slot}')"
  idle=$([[ "$live" == "blue" ]] && echo green || echo blue)
  log "Live slot: ${live}; deploying ${IMAGE} to idle slot: ${idle}"

  set_image "aceest-${idle}" "$IMAGE"
  wait_rollout "aceest-${idle}"
  kubectl -n "$NS" patch svc aceest-bg-preview -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"${idle}\"}}}"
  smoke_test "aceest-${idle}" aceest-bg-preview "$VERSION"

  log "Switching live traffic ${live} -> ${idle}"
  kubectl -n "$NS" patch svc aceest-bg -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"${idle}\"}}}"
  # Preview now points at the old slot, which stays running for instant rollback.
  kubectl -n "$NS" patch svc aceest-bg-preview -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"${live}\"}}}"
  smoke_test "aceest-${idle}" aceest-bg "$VERSION"
}

# ---------------------------------------------------------------- canary
set_canary_weight() {
  kubectl -n "$NS" annotate ingress aceest-canary-candidate --overwrite \
    "nginx.ingress.kubernetes.io/canary-weight=$1"
}

deploy_canary() {
  set_image aceest-canary-candidate "$IMAGE"
  wait_rollout aceest-canary-candidate
  smoke_test aceest-canary-candidate aceest-canary-candidate "$VERSION"

  for weight in $CANARY_STEPS; do
    log "Canary weight ${weight}%"
    set_canary_weight "$weight"
    sleep "$CANARY_PAUSE"
    # Gate: the candidate must stay healthy with no restarts while it takes traffic.
    smoke_test aceest-canary-candidate aceest-canary-candidate "$VERSION"
    restarts="$(kubectl -n "$NS" get pods -l app=aceest-canary,track=canary \
      -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' | sort -n | tail -1)"
    if [[ "${restarts:-0}" -gt 0 ]]; then fail "canary pods restarted ${restarts} time(s)"; fi
  done

  log "Promoting canary: stable track -> ${IMAGE}"
  set_image aceest-canary-stable "$IMAGE"
  wait_rollout aceest-canary-stable
  set_canary_weight 0
  smoke_test aceest-canary-stable aceest-canary-stable "$VERSION"
}

# ---------------------------------------------------------------- A/B testing
deploy_ab() {
  # Variant B gets the new build; variant A (control) keeps the current one.
  set_image aceest-ab-b "$IMAGE"
  wait_rollout aceest-ab-b
  smoke_test aceest-ab-b aceest-ab-b "$VERSION"
  log "Variant B live for 50% of users (header X-Variant: B or cookie ab_variant=always to force it)"
}

# ---------------------------------------------------------------- shadow
deploy_shadow() {
  set_image aceest-shadow-candidate "$IMAGE"
  wait_rollout aceest-shadow-candidate
  smoke_test aceest-shadow-candidate aceest-shadow-candidate "$VERSION"

  log "Sending sample traffic through the mirror proxy"
  for path in / /programs/FL /api/programs /calculator /version; do
    in_cluster_get aceest-shadow-primary "http://aceest-mirror-proxy${path}" >/dev/null
  done
  sleep 2
  log "Shadow received (mirrored) requests:"
  kubectl -n "$NS" logs deployment/aceest-shadow-candidate -c aceest --since=2m | grep -E '"(GET|POST)' | tail -5 || true
  errors="$(kubectl -n "$NS" logs deployment/aceest-shadow-candidate -c aceest --since=2m | grep -cE '" 5[0-9]{2} ' || true)"
  if [[ "${errors:-0}" -gt 0 ]]; then fail "shadow returned ${errors} server error(s) on mirrored traffic"; fi
  log "Shadow release healthy - promote with: scripts/deploy.sh rolling ${IMAGE} (or update aceest-shadow-primary)"
}

case "$STRATEGY" in
  rolling|rolling-update) fn=deploy_rolling ;;
  blue-green)             fn=deploy_blue_green ;;
  canary)                 fn=deploy_canary ;;
  ab-testing|ab)          fn=deploy_ab ;;
  shadow)                 fn=deploy_shadow ;;
  all)
    for s in rolling blue-green canary ab-testing shadow; do
      bash "$0" "$s" "$IMAGE"
    done
    exit 0
    ;;
  *) fail "unknown strategy '${STRATEGY}'" ;;
esac

# Run the release in a subshell with errexit so that any failing command or
# failed smoke test (fail -> exit 1) ends up in the rollback branch.
set +e
( set -e; "$fn" )
rc=$?
set -e
if [[ $rc -ne 0 ]]; then
  on_failure
fi
log "Release of ${IMAGE} via '${STRATEGY}' completed"
