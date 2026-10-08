#!/usr/bin/env bash
# S1-11 phase 4, on the test host VM: switch the backend from monitor_app to
# monitor_backend. Keeps a backup of backend.env for phase4-rollback.sh. Prints no password.
set -euo pipefail
ENVFILE=/opt/model-monitor/backend.env
BACKUP=/opt/model-monitor/secrets/backend.env.monitor_app.bak
NEWPW="$(cat /opt/model-monitor/secrets/monitor-backend.password)"
[ -f "$BACKUP" ] || install -m 0600 "$ENVFILE" "$BACKUP"
sed -i "s|://monitor_app:[^@]*@|://monitor_backend:${NEWPW}@|" "$ENVFILE"
unset NEWPW
echo "backend.env user: $(sed -n 's|.*://\([^:]*\):.*|\1|p' "$ENVFILE")"
cd /opt/model-monitor/compose
docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate --wait --wait-timeout 120 backend >/dev/null
echo "readiness: $(curl -s http://127.0.0.1:8000/api/readiness)"
docker compose -f compose.yaml -f compose.testhost.yaml exec -T backend python - <<'PY'
from app import db
with db.engine().connect() as cx:
    print("database user:", cx.exec_driver_sql("select current_user").scalar())
PY
echo "PHASE 4 DONE"
