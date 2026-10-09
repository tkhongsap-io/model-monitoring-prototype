#!/usr/bin/env bash
# S1-06, test host only: writes /opt/model-monitor/collector.env (mode 600, root) with the
# OTLP token of the GCP jobs, from a token file copied from Secret Manager (otlp-token).
#   sudo bash make-collector-env.sh /tmp/s1-06/otlp-token.tmp
# Deletes the copied file. Prints the file name and mode only, never the token.
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
SRC="${1:-}"
OUT=/opt/model-monitor/collector.env
[ -n "$SRC" ] && [ -s "$SRC" ] || { echo "usage: make-collector-env.sh <token-file> (the file must not be empty)" >&2; exit 1; }
umask 077
TOKEN="$(tr -d '\r\n' < "$SRC")"
if [ "${#TOKEN}" -lt 32 ]; then
  echo "the token is shorter than 32 characters; make a new one" >&2
  exit 1
fi
# printf is a shell builtin: the token is not in a process argument list.
printf 'OTLP_TOKEN=%s\n' "$TOKEN" > "$OUT.tmp"
chown root:root "$OUT.tmp"
chmod 600 "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
rm -f "$SRC"
rmdir "$(dirname "$SRC")" 2>/dev/null || true
stat -c '%a %U %n' "$OUT"
echo "COLLECTOR ENV DONE"
