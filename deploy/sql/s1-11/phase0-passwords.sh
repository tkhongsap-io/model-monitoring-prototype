#!/usr/bin/env bash
# S1-11 phase 0, on the test host VM. Moves the Cloud SQL admin password (the file
# admin-password.tmp that was copied with this folder from Secret Manager) into
# /opt/model-monitor/secrets, makes the new passwords there (folder mode 700, files mode
# 600), and deletes the copy. Prints names and modes only, never a password.
# Each new password has lower, upper, digit and a URL-safe special character (Cloud SQL
# policy; a DATABASE_URL needs no encoding).
set -euo pipefail
SECRETS=/opt/model-monitor/secrets
umask 077
install -d -m 0700 "$SECRETS"
HERE="$(cd "$(dirname "$0")" && pwd)"
rm -rf /tmp/model-monitor-s111                    # old inspection files (admin password)
[ -s "$HERE/admin-password.tmp" ] || { echo "admin-password.tmp is missing" >&2; exit 1; }
tr -d '\r\n' < "$HERE/admin-password.tmp" > "$SECRETS/postgres-admin.password.tmp"
rm -f "$HERE/admin-password.tmp"
sed -n 's|.*://monitor_app:\([^@]*\)@.*|\1|p' /opt/model-monitor/backend.env | tr -d '\n' \
  > "$SECRETS/monitor-app.password.tmp"
[ -s "$SECRETS/monitor-app.password.tmp" ] || { echo "backend.env does not use monitor_app" >&2; exit 1; }
for name in monitor-backend monitor-readonly dev-itthisak dev-prakasit; do
  if [ ! -s "$SECRETS/$name.password" ]; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(32) + "Kq7-", end="")' > "$SECRETS/$name.password"
  fi
done
stat -c '%a %U %n' "$SECRETS"/*
echo "PHASE 0 DONE"
