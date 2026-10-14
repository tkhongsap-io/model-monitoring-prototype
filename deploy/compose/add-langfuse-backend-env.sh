#!/usr/bin/env bash
# S2-05, test host only: gives the backend the Langfuse project keys for the scores.
# Reads them from /opt/langfuse/langfuse.env (made by make-langfuse-env.sh) and sets
# LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in backend.env (600, root).
# Other lines stay. Run once:  sudo bash add-langfuse-backend-env.sh   Prints names only.
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
SRC=/opt/langfuse/langfuse.env
DST=/opt/model-monitor/backend.env
[ -f "$SRC" ] || { echo "$SRC is missing; deploy Langfuse first (S2-03)" >&2; exit 1; }
[ -f "$DST" ] || { echo "$DST is missing" >&2; exit 1; }
umask 077
python3 - "$SRC" "$DST" <<'PY'
import os, sys

src, dst = sys.argv[1:3]
values = {}
with open(src, encoding="utf-8") as handle:
    for line in handle:
        key, sep, value = line.strip().partition("=")
        if sep:
            values[key] = value
public_key = values.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY", "")
secret_key = values.get("LANGFUSE_INIT_PROJECT_SECRET_KEY", "")
if not public_key or not secret_key:
    print("langfuse.env has no project keys", file=sys.stderr)
    sys.exit(1)
updates = {"LANGFUSE_HOST": "http://langfuse-web:3000",
           "LANGFUSE_PUBLIC_KEY": public_key, "LANGFUSE_SECRET_KEY": secret_key}
with open(dst, encoding="utf-8") as handle:
    lines = [l for l in handle.read().splitlines() if l.split("=", 1)[0] not in updates]
lines += [f"{k}={v}" for k, v in updates.items()]
tmp = dst + ".tmp"
fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
os.replace(tmp, dst)
print("set: " + ", ".join(updates))
PY
chown root:root "$DST"
chmod 600 "$DST"
stat -c '%a %U %n' "$DST"
echo "BACKEND LANGFUSE ENV DONE"
