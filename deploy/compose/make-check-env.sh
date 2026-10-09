#!/usr/bin/env bash
# S1-07, test host only: writes /opt/model-monitor/check.env (mode 600, root) for the trace
# check tool, with the read-only database user monitor_readonly (S1-11). Run once with sudo.
# Prints the file name and mode only, never the password.
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
PW_FILE=/opt/model-monitor/secrets/monitor-readonly.password
OUT=/opt/model-monitor/check.env
DB_HOST=10.188.112.8
CA=/etc/model-monitor/cloudsql-server-ca.pem
[ -s "$PW_FILE" ] || {
  echo "read-only password file is missing or empty" >&2
  exit 1
}
umask 077
PW="$(tr -d '\r\n' < "$PW_FILE")"
# printf is a shell builtin: the password is not in a process argument list.
printf 'CHECK_DATABASE_URL=postgresql://monitor_readonly:%s@%s:5432/monitor?sslmode=verify-ca&sslrootcert=%s\n' \
  "$PW" "$DB_HOST" "$CA" > "$OUT.tmp"
chown root:root "$OUT.tmp"
chmod 600 "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
stat -c '%a %U %n' "$OUT"
echo "CHECK ENV DONE"
