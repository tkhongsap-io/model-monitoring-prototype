#!/usr/bin/env bash
# S2-03, test host only: makes /opt/langfuse/langfuse.env (600, root) with random secrets,
# Google sign-in and the project keys; adds LANGFUSE_OTLP_AUTH to collector.env and the
# CHECK_LANGFUSE_* settings to check.env. Run once:
#   sudo bash make-langfuse-env.sh --admin-email <company email> --google-file <path>
# Refuses a second run (it would change the passwords and the keys). Prints names only.
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
ADMIN_EMAIL=""
GOOGLE_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --admin-email) ADMIN_EMAIL="${2:-}"; shift 2 ;;
    --google-file) GOOGLE_FILE="${2:-}"; shift 2 ;;
    *) echo "usage: make-langfuse-env.sh --admin-email <email> --google-file <path>" >&2; exit 2 ;;
  esac
done
OUT=/opt/langfuse/langfuse.env
COLLECTOR=/opt/model-monitor/collector.env
CHECK=/opt/model-monitor/check.env
[[ "$ADMIN_EMAIL" == *@*.* ]] || { echo "--admin-email must be an email address" >&2; exit 2; }
[ -s "$GOOGLE_FILE" ] || { echo "the Google file is missing or empty" >&2; exit 1; }
[ ! -e "$OUT" ] || { echo "$OUT exists; a second run would change the passwords and keys" >&2; exit 1; }
[ -f "$COLLECTOR" ] && [ -f "$CHECK" ] || { echo "collector.env and check.env must exist first (S1-06, S1-07)" >&2; exit 1; }
umask 077
mkdir -p /opt/langfuse
# Python reads the Google file itself: the client secret is never a process argument.
python3 - "$OUT" "$ADMIN_EMAIL" "$GOOGLE_FILE" "$COLLECTOR" "$CHECK" <<'PY'
import base64, os, secrets, sys, uuid

out, email, google_file, collector, check = sys.argv[1:6]
google = {}
with open(google_file, encoding="utf-8") as handle:
    for line in handle:
        key, sep, value = line.strip().partition("=")
        if sep:
            google[key] = value.strip()
client_id = google.get("AUTH_GOOGLE_CLIENT_ID", "")
client_secret = google.get("AUTH_GOOGLE_CLIENT_SECRET", "")
if not client_id or not client_secret:
    print("the Google file needs AUTH_GOOGLE_CLIENT_ID and AUTH_GOOGLE_CLIENT_SECRET", file=sys.stderr)
    sys.exit(1)


def pw() -> str:
    return secrets.token_urlsafe(32)


postgres, clickhouse, redis, minio = pw(), pw(), pw(), pw()
public_key, secret_key = f"pk-lf-{uuid.uuid4()}", f"sk-lf-{uuid.uuid4()}"
values = {
    "DATABASE_URL": f"postgresql://langfuse:{postgres}@postgres:5432/langfuse",
    "POSTGRES_PASSWORD": postgres,
    "CLICKHOUSE_PASSWORD": clickhouse,
    "REDIS_AUTH": redis,
    "MINIO_ROOT_PASSWORD": minio,
    "LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID": "langfuse",
    "LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY": minio,
    "NEXTAUTH_URL": "http://localhost:3000",
    "NEXTAUTH_SECRET": pw(),
    "SALT": pw(),
    "ENCRYPTION_KEY": secrets.token_hex(32),
    "LANGFUSE_INIT_PROJECT_PUBLIC_KEY": public_key,
    "LANGFUSE_INIT_PROJECT_SECRET_KEY": secret_key,
    "LANGFUSE_INIT_USER_EMAIL": email,
    "LANGFUSE_INIT_USER_NAME": email.split("@", 1)[0],
    "LANGFUSE_INIT_USER_PASSWORD": pw(),
    "AUTH_DISABLE_USERNAME_PASSWORD": "true",
    "AUTH_GOOGLE_CLIENT_ID": client_id,
    "AUTH_GOOGLE_CLIENT_SECRET": client_secret,
    "AUTH_GOOGLE_ALLOWED_DOMAINS": email.split("@", 1)[1],
    "AUTH_GOOGLE_ALLOW_ACCOUNT_LINKING": "true",
}
fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    handle.write("".join(f"{k}={v}\n" for k, v in values.items()))


def set_keys(path: str, updates: dict[str, str]) -> None:
    with open(path, encoding="utf-8") as handle:
        lines = [l for l in handle.read().splitlines() if l.split("=", 1)[0] not in updates]
    lines += [f"{k}={v}" for k, v in updates.items()]
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
set_keys(collector, {"LANGFUSE_OTLP_AUTH": auth})
set_keys(check, {"CHECK_LANGFUSE_URL": "http://langfuse-web:3000",
                 "CHECK_LANGFUSE_PUBLIC_KEY": public_key,
                 "CHECK_LANGFUSE_SECRET_KEY": secret_key})
os.remove(google_file)
PY
chown root:root "$OUT" "$COLLECTOR" "$CHECK"
chmod 600 "$OUT" "$COLLECTOR" "$CHECK"
stat -c '%a %U %n' "$OUT" "$COLLECTOR" "$CHECK"
echo "LANGFUSE ENV DONE"
