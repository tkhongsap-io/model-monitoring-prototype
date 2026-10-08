#!/usr/bin/env bash
# S1-11: run one SQL file of this folder on database `monitor` as one user, over TLS
# (verify-ca), with psql from the postgres:17.11 image. Run on the test host VM:
#   sudo bash /tmp/s1-11/run-sql.sh <user> <sql-file>
# Passwords come from mode-600 files in /opt/model-monitor/secrets and reach psql only as
# environment variables (\getenv in the SQL). Nothing here prints a password.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SECRETS=/opt/model-monitor/secrets
USER_NAME="$1"
SQL="$2"
case "$USER_NAME" in
  postgres)         PW_FILE="$SECRETS/postgres-admin.password.tmp" ;;
  monitor_app)      PW_FILE="$SECRETS/monitor-app.password.tmp" ;;
  monitor_backend)  PW_FILE="$SECRETS/monitor-backend.password" ;;
  monitor_readonly) PW_FILE="$SECRETS/monitor-readonly.password" ;;
  dev_itthisak)     PW_FILE="$SECRETS/dev-itthisak.password" ;;
  dev_prakasit)     PW_FILE="$SECRETS/dev-prakasit.password" ;;
  *) echo "unknown user: $USER_NAME" >&2; exit 2 ;;
esac
PGHOST="$(sed -n 's|.*@\([0-9.]*\):5432/.*|\1|p' /opt/model-monitor/backend.env)"
docker run --rm --network host \
  -e PGPASSWORD="$(cat "$PW_FILE")" \
  -e PW_BACKEND="$(cat "$SECRETS/monitor-backend.password")" \
  -e PW_READONLY="$(cat "$SECRETS/monitor-readonly.password")" \
  -e PW_DEV_ITTHISAK="$(cat "$SECRETS/dev-itthisak.password")" \
  -e PW_DEV_PRAKASIT="$(cat "$SECRETS/dev-prakasit.password")" \
  -v /opt/model-monitor/cloudsql-server-ca.pem:/ca.pem:ro \
  -v "$HERE:/work:ro" \
  postgres:17.11-bookworm \
  psql "host=$PGHOST port=5432 dbname=monitor user=$USER_NAME sslmode=verify-ca sslrootcert=/ca.pem" \
       -v ON_ERROR_STOP=1 -X -q -P pager=off -f "/work/$SQL"
