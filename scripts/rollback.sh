#!/usr/bin/env bash
# Reverts the most recent release for a strategy to the last stable version.
#
# Usage: scripts/rollback.sh <rolling|blue-green|canary|ab-testing|shadow|all>
source "$(dirname "$0")/lib.sh"

STRATEGY="${1:?usage: $0 <strategy>}"

undo() {
  log "kubectl rollout undo deployment/$1"
  kubectl -n "$NS" rollout undo "deployment/$1"
  wait_rollout "$1"
  echo "  now running: $(current_image "$1")"
}

case "$STRATEGY" in
  rolling|rolling-update)
    undo aceest-rolling
    ;;
  blue-green)
    # The previous slot is still running, so rollback is just switching the selector back.
    live="$(kubectl -n "$NS" get svc aceest-bg -o jsonpath='{.spec.selector.slot}')"
    previous=$([[ "$live" == "blue" ]] && echo green || echo blue)
    if kubectl -n "$NS" rollout status "deployment/aceest-${previous}" --timeout=5s >/dev/null 2>&1; then
      log "Switching live traffic ${live} -> ${previous}"
      kubectl -n "$NS" patch svc aceest-bg -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"${previous}\"}}}"
      kubectl -n "$NS" patch svc aceest-bg-preview -p "{\"spec\":{\"selector\":{\"app\":\"aceest-bg\",\"slot\":\"${live}\"}}}"
    else
      log "Previous slot not healthy - keeping ${live} live and undoing the idle slot instead"
      undo "aceest-${previous}"
    fi
    ;;
  canary)
    log "Sending 0% traffic to the canary"
    kubectl -n "$NS" annotate ingress aceest-canary-candidate --overwrite nginx.ingress.kubernetes.io/canary-weight=0
    undo aceest-canary-candidate
    # If the stable track was already promoted, revert it too.
    if [[ "$(current_image aceest-canary-stable)" != "$(current_image aceest-canary-candidate)" ]]; then
      undo aceest-canary-stable
    fi
    ;;
  ab-testing|ab)
    undo aceest-ab-b
    ;;
  shadow)
    undo aceest-shadow-candidate
    ;;
  all)
    for s in rolling blue-green canary ab-testing shadow; do bash "$0" "$s"; done
    ;;
  *) fail "unknown strategy '${STRATEGY}'" ;;
esac
log "Rollback for '${STRATEGY}' completed"
