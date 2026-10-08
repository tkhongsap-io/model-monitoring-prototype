#!/usr/bin/env bash
# S1-11: undo phase 4 (only before phase 6 deletes monitor_app). Restores backend.env.
set -euo pipefail
BACKUP=/opt/model-monitor/secrets/backend.env.monitor_app.bak
[ -f "$BACKUP" ] || { echo "no backup" >&2; exit 1; }
install -m 0600 "$BACKUP" /opt/model-monitor/backend.env
cd /opt/model-monitor/compose
docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate --wait --wait-timeout 120 backend >/dev/null
echo "readiness: $(curl -s http://127.0.0.1:8000/api/readiness)"
echo "ROLLBACK DONE"
