#!/usr/bin/env bash
# S1-07: check that one batch run arrived completely.
#   check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]
# Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
# On the test host (where /opt/model-monitor/check.env exists) run it with sudo; it uses
# compose.testhost.yaml. Elsewhere it uses the local stack (compose.local.yaml).
set -euo pipefail
cd "$(dirname "$0")"
if [ -f /opt/model-monitor/check.env ]; then
  FILES=(-f compose.yaml -f compose.testhost.yaml)
else
  FILES=(-f compose.yaml -f compose.local.yaml)
fi
exec docker compose "${FILES[@]}" --profile tools run --rm -T --no-deps trace-check "$@"
