# Self-hosted Langfuse and the Collector export (S2-03) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Langfuse 4.50.0 runs as its own Compose project with private dependencies, the Collector exports every span to it, nginx serves its UI on port 3000, the trace check tool gets a 5th item read from Langfuse, and a new CI test proves a fake-job trace in Langfuse also after a restart.

**Architecture:** `deploy/langfuse/` (project `langfuse`): web, worker, PostgreSQL, ClickHouse, Redis, MinIO on the project network; only `langfuse-web` joins `edge`. Settings that are the same on every host are in the base `environment`; secrets and host settings come from one env file per host. The Collector gets an `otlphttp/langfuse` exporter. `check_trace.py` reads Langfuse with `urllib`.

**Tech Stack:** Docker Compose v2, Langfuse 4.50.0, ClickHouse 25.12.11.4, Redis 7.4.11, PostgreSQL 17.11, Chainguard MinIO (by digest), nginx, OTel Collector contrib 0.161.0, Python 3.12 standard library, pytest, PyYAML.

**Spec:** [spec.md](spec.md) (approved 2026-10-12). Intent: [intent.md](intent.md).

## Global Constraints

- Images: `langfuse/langfuse:4.50.0`, `langfuse/langfuse-worker:4.50.0`, `postgres:17.11-bookworm`, `clickhouse/clickhouse-server:25.12.11.4`, `redis:7.4.11`, `cgr.dev/chainguard/minio@sha256:dc455cdd4db6e390b1b26514f15ff37681a777bf8dab41aac445a0259f751e56`. Never `latest`.
- No Langfuse service publishes a port. Only `langfuse-web` joins `edge` (alias `langfuse-web`).
- No secret in git. `deploy/langfuse/local.env` holds local test values only and says so in its first line.
- Local Langfuse project keys: `pk-lf-local-00000000-0000-0000-0000-000000000000` / `sk-lf-local-00000000-0000-0000-0000-000000000000`; their Basic value: `cGstbGYtbG9jYWwtMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwOnNrLWxmLWxvY2FsLTAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMA==`.
- Use the Langfuse setting names exactly as in the spec. Do not rename them without evidence; the CI test `langfuse-smoke` proves them.
- `check_trace.py`: standard library only for Langfuse (`urllib`, `base64`, `json`); never prints a key or a URL with credentials.
- Shell scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, LF endings. YAML, nginx and env files: LF.
- Tests run from `backend/`: `.venv\Scripts\python.exe -m pytest ...`. If pytest cannot open its temp or cache folder in the sandbox, add `-p no:cacheprovider --basetemp=.pytest-tmp` and delete `backend/.pytest-tmp` afterwards.
- Docker and bash are not available on the Windows computer: never claim a stack, a script or a CI test ran.
- **Codex: do not run `git commit` or `git add`.** Leave changes in the working tree; Claude reviews and commits each task.

## Review Focus

- A second run of `make-langfuse-env.sh` must refuse, or it would change the database passwords and the project keys. (Task 1: `test_make_langfuse_env_script`.)
- The Google client secret must never be a process argument or an output line. (Task 1: same test: the secret is read by Python from the file path, and no `echo` prints a value.)
- When the Langfuse settings are absent (laptop without Langfuse, old `check.env`), the trace check must show `skipped`, not `missing`. (Task 4: `test_langfuse_item_skipped_without_settings`.)
- A Langfuse `401`, a timeout or bad JSON must give one safe line, no key. (Task 4: `test_langfuse_errors_are_one_safe_line`.)
- After the span file rotates, the trace check must still find older spans. (Task 4: `test_rotated_span_files_are_read`.)

---

## File structure

| File | Task | Responsibility |
|---|---|---|
| `deploy/langfuse/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml`, `local.env`, `langfuse.env.example`, `google-oauth.env.example`, `make-langfuse-env.sh`, `README.md` | 1 | The Langfuse project |
| `backend/tests/test_langfuse_files.py` | 1, 5 | Static tests of the Langfuse project and its CI |
| `deploy/nginx/conf.d/langfuse.conf`, `deploy/nginx/compose.local.yaml`, `deploy/nginx/compose.testhost.yaml`, `backend/tests/test_nginx_files.py` | 2 | UI on port 3000 |
| `deploy/compose/otel-collector.yaml`, `compose.yaml`, `compose.local.yaml`, `backend/tests/test_compose_files.py` | 3 | Exporter, rotation, trace-check on `edge` |
| `backend/app/trace_check.py`, `backend/scripts/check_trace.py`, `backend/tests/test_trace_check.py`, `backend/tests/test_check_trace_script.py` | 4 | 5th item, rotated files |
| `scripts/langfuse-smoke.sh`, `.github/workflows/langfuse-smoke.yml` | 5 | CI test |
| `deploy/compose/TESTHOST.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md` | 6 | Docs |

---

### Task 1: the Langfuse Compose project

**Files:**
- Create: `deploy/langfuse/compose.yaml`, `deploy/langfuse/compose.local.yaml`, `deploy/langfuse/compose.testhost.yaml`, `deploy/langfuse/local.env`, `deploy/langfuse/langfuse.env.example`, `deploy/langfuse/google-oauth.env.example`, `deploy/langfuse/make-langfuse-env.sh`, `deploy/langfuse/README.md`
- Test: `backend/tests/test_langfuse_files.py`

**Interfaces:**
- Produces: service `langfuse-web` on `edge` as `langfuse-web:3000`; local keys (Global Constraints); test-host files `/opt/langfuse/langfuse.env`, and `LANGFUSE_OTLP_AUTH` in `/opt/model-monitor/collector.env`, `CHECK_LANGFUSE_URL` / `CHECK_LANGFUSE_PUBLIC_KEY` / `CHECK_LANGFUSE_SECRET_KEY` in `/opt/model-monitor/check.env`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_langfuse_files.py`:

```python
"""S2-03: static checks of the self-hosted Langfuse project (deploy/langfuse)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LANGFUSE = ROOT / "deploy" / "langfuse"
SERVICES = {"langfuse-web", "langfuse-worker", "postgres", "clickhouse", "redis", "minio"}
IMAGES = {
    "langfuse-web": "langfuse/langfuse:4.50.0",
    "langfuse-worker": "langfuse/langfuse-worker:4.50.0",
    "postgres": "postgres:17.11-bookworm",
    "clickhouse": "clickhouse/clickhouse-server:25.12.11.4",
    "redis": "redis:7.4.11",
    "minio": "cgr.dev/chainguard/minio@sha256:"
             "dc455cdd4db6e390b1b26514f15ff37681a777bf8dab41aac445a0259f751e56",
}


def _load(name: str) -> dict:
    return yaml.safe_load((LANGFUSE / name).read_text(encoding="utf-8"))


def _env_lines(name: str) -> dict[str, str]:
    text = (LANGFUSE / name).read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines()
                if line and not line.startswith("#"))


def test_images_are_pinned():
    base = _load("compose.yaml")
    assert base["name"] == "langfuse"
    assert set(base["services"]) == SERVICES
    for name, image in IMAGES.items():
        assert base["services"][name]["image"] == image, name


def test_no_published_port_and_only_web_on_edge():
    base = _load("compose.yaml")
    for name in ("compose.yaml", "compose.local.yaml", "compose.testhost.yaml"):
        for service in _load(name)["services"].values():
            assert "ports" not in service, name
    services = base["services"]
    assert services["langfuse-web"]["networks"] == {
        "default": {}, "edge": {"aliases": ["langfuse-web"]}}
    for name in SERVICES - {"langfuse-web"}:
        assert "edge" not in str(services[name].get("networks", "")), name
    assert base["networks"] == {"edge": {"external": True}}
    for service in services.values():
        assert service["restart"] == "unless-stopped"
        assert "healthcheck" in service


def test_base_settings_turn_off_signup_and_telemetry():
    services = _load("compose.yaml")["services"]
    for name in ("langfuse-web", "langfuse-worker"):
        env = services[name]["environment"]
        assert env["TELEMETRY_ENABLED"] == "false"
        assert env["AUTH_DISABLE_SIGNUP"] == "true"
        assert env["LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES"] == "false"
        assert env["LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT"] == "http://minio:9000"
        for dep in ("postgres", "clickhouse", "redis", "minio"):
            assert services[name]["depends_on"][dep] == {"condition": "service_healthy"}
    assert services["langfuse-web"]["environment"]["LANGFUSE_INIT_PROJECT_NAME"] == "model-monitor"
    assert "noeviction" in " ".join(services["redis"]["command"])
    for name in ("compose.yaml", "compose.local.yaml", "compose.testhost.yaml"):
        text = (LANGFUSE / name).read_text(encoding="utf-8")
        assert not re.search(r"(PASSWORD|SECRET|_KEY|_AUTH)\s*:\s*\S", text), name


def test_every_service_reads_the_host_env_file():
    local = _load("compose.local.yaml")["services"]
    host = _load("compose.testhost.yaml")["services"]
    assert set(local) == set(host) == SERVICES
    for name in SERVICES:
        assert local[name]["env_file"] == ["./local.env"]
        assert host[name]["env_file"] == [{"path": "/opt/langfuse/langfuse.env", "required": True}]


def test_local_env_is_marked_and_uses_password_login():
    text = (LANGFUSE / "local.env").read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("# Local test values, not secrets")
    env = _env_lines("local.env")
    assert env["AUTH_DISABLE_USERNAME_PASSWORD"] == "false"
    assert env["LANGFUSE_INIT_PROJECT_PUBLIC_KEY"] == "pk-lf-local-00000000-0000-0000-0000-000000000000"
    assert env["LANGFUSE_INIT_PROJECT_SECRET_KEY"] == "sk-lf-local-00000000-0000-0000-0000-000000000000"
    assert "AUTH_GOOGLE_CLIENT_ID" not in env
    assert len(env["ENCRYPTION_KEY"]) == 64


def test_examples_have_names_only():
    for name in ("langfuse.env.example", "google-oauth.env.example"):
        values = _env_lines(name)
        assert values and all(v == "" for v in values.values()), name
    assert set(_env_lines("google-oauth.env.example")) == {
        "AUTH_GOOGLE_CLIENT_ID", "AUTH_GOOGLE_CLIENT_SECRET"}


def test_make_langfuse_env_script():
    text = (LANGFUSE / "make-langfuse-env.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "\r\n" not in text
    assert "umask 077" in text and "chmod 600" in text
    assert "/opt/langfuse/langfuse.env" in text and "exists" in text   # refuses a second run
    assert "AUTH_DISABLE_USERNAME_PASSWORD" in text and '"true"' in text
    assert "LANGFUSE_OTLP_AUTH" in text and "CHECK_LANGFUSE_SECRET_KEY" in text
    assert "os.remove(google_file)" in text
    # the Google secret is read by Python from the file, never passed as an argument
    assert "GOOGLE_SECRET" not in text
    for line in text.splitlines():
        if line.lstrip().startswith("echo"):
            assert "$" not in line.replace('"$OUT"', "").replace("$0", ""), line
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py -q`
Expected: FAIL (`FileNotFoundError` for `deploy/langfuse/compose.yaml`)

- [ ] **Step 3: Implement**

`deploy/langfuse/compose.yaml`:

```yaml
# Self-hosted Langfuse (S2-03), its own Compose project. No service publishes a port: the
# databases are Langfuse's own. Only langfuse-web joins the external network `edge`, for
# nginx (UI, port 3000) and the Collector (OTLP export).
# Run from this folder: docker compose -f compose.yaml -f compose.<local|testhost>.yaml up -d --wait
name: langfuse

x-langfuse-env: &langfuse-env
  TELEMETRY_ENABLED: "false"
  LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES: "false"
  AUTH_DISABLE_SIGNUP: "true"
  CLICKHOUSE_MIGRATION_URL: clickhouse://clickhouse:9000
  CLICKHOUSE_URL: http://clickhouse:8123
  CLICKHOUSE_USER: clickhouse
  CLICKHOUSE_CLUSTER_ENABLED: "false"
  REDIS_HOST: redis
  REDIS_PORT: "6379"
  LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse
  LANGFUSE_S3_EVENT_UPLOAD_REGION: auto
  LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://minio:9000
  LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE: "true"
  LANGFUSE_S3_EVENT_UPLOAD_PREFIX: events/

x-depends: &depends
  postgres: {condition: service_healthy}
  clickhouse: {condition: service_healthy}
  redis: {condition: service_healthy}
  minio: {condition: service_healthy}

services:
  langfuse-worker:
    image: langfuse/langfuse-worker:4.50.0
    environment: *langfuse-env
    depends_on: *depends
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O /dev/null http://localhost:3030/api/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 60s
    restart: unless-stopped

  langfuse-web:
    image: langfuse/langfuse:4.50.0
    environment:
      <<: *langfuse-env
      LANGFUSE_INIT_ORG_ID: model-monitor
      LANGFUSE_INIT_ORG_NAME: Model monitor
      LANGFUSE_INIT_PROJECT_ID: model-monitor
      LANGFUSE_INIT_PROJECT_NAME: model-monitor
    depends_on: *depends
    networks:
      default: {}
      edge:
        aliases: [langfuse-web]
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O /dev/null http://localhost:3000/api/public/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 60s
    restart: unless-stopped

  postgres:
    image: postgres:17.11-bookworm
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_DB: langfuse
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse -d langfuse"]
      interval: 5s
      timeout: 5s
      retries: 30
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:25.12.11.4
    user: "101:101"
    environment:
      CLICKHOUSE_DB: default
      CLICKHOUSE_USER: clickhouse
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - clickhouse-logs:/var/log/clickhouse-server
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8123/ping || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 30
      start_period: 20s
    restart: unless-stopped

  redis:
    image: redis:7.4.11
    # Langfuse's job queue: noeviction, no persistence. Not shared with other apps.
    command: ["sh", "-c", "exec redis-server --requirepass \"$$REDIS_AUTH\" --maxmemory-policy noeviction --save '' --appendonly no"]
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a \"$$REDIS_AUTH\" --no-auth-warning ping | grep -q PONG"]
      interval: 5s
      timeout: 5s
      retries: 30
    restart: unless-stopped

  minio:
    image: cgr.dev/chainguard/minio@sha256:dc455cdd4db6e390b1b26514f15ff37681a777bf8dab41aac445a0259f751e56
    entrypoint: ["sh", "-c"]
    command: ["mkdir -p /data/langfuse && minio server --address :9000 --console-address :9001 /data"]
    environment:
      MINIO_ROOT_USER: langfuse
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 30
    restart: unless-stopped

volumes:
  postgres-data:
  clickhouse-data:
  clickhouse-logs:
  minio-data:

networks:
  edge:
    external: true
```

`deploy/langfuse/compose.local.yaml`:

```yaml
# Laptop and CI (S2-03): local test values from ./local.env. Never use on the test host.
services:
  langfuse-web: {env_file: [./local.env]}
  langfuse-worker: {env_file: [./local.env]}
  postgres: {env_file: [./local.env]}
  clickhouse: {env_file: [./local.env]}
  redis: {env_file: [./local.env]}
  minio: {env_file: [./local.env]}
```

`deploy/langfuse/compose.testhost.yaml`:

```yaml
# GCP test host (S2-03): secrets from /opt/langfuse/langfuse.env (600, made by
# make-langfuse-env.sh). The Langfuse UI is reached through nginx port 3000 and the IAP tunnel.
x-env: &env
  env_file:
    - path: /opt/langfuse/langfuse.env
      required: true
services:
  langfuse-web: *env
  langfuse-worker: *env
  postgres: *env
  clickhouse: *env
  redis: *env
  minio: *env
```

`deploy/langfuse/local.env`:

```
# Local test values, not secrets (S2-03). Laptop and CI only; the test host uses /opt/langfuse/langfuse.env.
DATABASE_URL=postgresql://langfuse:local-postgres-password@postgres:5432/langfuse
POSTGRES_PASSWORD=local-postgres-password
CLICKHOUSE_PASSWORD=local-clickhouse-password
REDIS_AUTH=local-redis-password
MINIO_ROOT_PASSWORD=local-minio-password
LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID=langfuse
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=local-minio-password
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=local-nextauth-secret-not-a-secret
SALT=local-salt-not-a-secret
ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-local-00000000-0000-0000-0000-000000000000
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-local-00000000-0000-0000-0000-000000000000
LANGFUSE_INIT_USER_EMAIL=local@example.com
LANGFUSE_INIT_USER_NAME=local
LANGFUSE_INIT_USER_PASSWORD=local-dev-password-not-a-secret
AUTH_DISABLE_USERNAME_PASSWORD=false
```

`deploy/langfuse/langfuse.env.example` (names only; `make-langfuse-env.sh` writes the real file):

```
# Template for /opt/langfuse/langfuse.env on the test host (S2-03). Names only.
DATABASE_URL=
POSTGRES_PASSWORD=
CLICKHOUSE_PASSWORD=
REDIS_AUTH=
MINIO_ROOT_PASSWORD=
LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID=
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=
NEXTAUTH_URL=
NEXTAUTH_SECRET=
SALT=
ENCRYPTION_KEY=
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=
LANGFUSE_INIT_PROJECT_SECRET_KEY=
LANGFUSE_INIT_USER_EMAIL=
LANGFUSE_INIT_USER_NAME=
LANGFUSE_INIT_USER_PASSWORD=
AUTH_DISABLE_USERNAME_PASSWORD=
AUTH_GOOGLE_CLIENT_ID=
AUTH_GOOGLE_CLIENT_SECRET=
AUTH_GOOGLE_ALLOWED_DOMAINS=
AUTH_GOOGLE_ALLOW_ACCOUNT_LINKING=
```

`deploy/langfuse/google-oauth.env.example`:

```
# Template for the Google OAuth client file (S2-03). Fill in on the laptop as google-oauth.tmp,
# copy it to the VM, never commit it. make-langfuse-env.sh reads and deletes it.
AUTH_GOOGLE_CLIENT_ID=
AUTH_GOOGLE_CLIENT_SECRET=
```

`deploy/langfuse/make-langfuse-env.sh`:

```bash
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
```

`deploy/langfuse/README.md`: what the project is (six services, no published port, only `langfuse-web` on `edge`), the licenses line from `intent.md`, how to start it locally (`docker network create edge` once, then `docker compose -f compose.yaml -f compose.local.yaml up -d --wait`, UI through nginx `http://127.0.0.1:3000`, local login `local@example.com` / the value in `local.env`), and that the test-host steps are in `deploy/compose/TESTHOST.md`, "Langfuse (S2-03)". Its own Redis is not shared: another app that needs Redis deploys its own.

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py -q`
Expected: PASS (7 tests)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-03): self-hosted Langfuse Compose project`)

---

### Task 2: nginx serves the Langfuse UI on port 3000

**Files:**
- Create: `deploy/nginx/conf.d/langfuse.conf`
- Modify: `deploy/nginx/compose.local.yaml`, `deploy/nginx/compose.testhost.yaml`
- Test: `backend/tests/test_nginx_files.py`

- [ ] **Step 1: Update and add the tests** in `backend/tests/test_nginx_files.py`

Replace `test_nginx_ports_per_host` with:

```python
def test_nginx_ports_per_host():
    assert _load("compose.local.yaml")["services"]["nginx"]["ports"] == [
        "127.0.0.1:8080:8080", "127.0.0.1:3000:3000"]
    assert _load("compose.testhost.yaml")["services"]["nginx"]["ports"] == [
        "80:8080", "3000:3000"]
```

Append:

```python
def test_langfuse_conf_proxies_the_ui():
    text = (CONF / "langfuse.conf").read_text(encoding="utf-8")
    assert re.search(r"^\s*listen 3000;", text, flags=re.MULTILINE)
    assert "set $langfuse http://langfuse-web:3000;" in text
    assert _locations(text) == ["/"]
    passes = re.findall(r"proxy_pass\s+([^;]+);", text)
    assert passes == ["$langfuse"]
    assert "proxy_set_header Host $http_host;" in text
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py -q`
Expected: FAIL (ports, missing file)

- [ ] **Step 3: Implement**

`deploy/nginx/conf.d/langfuse.conf`:

```nginx
# Langfuse UI (S2-03). Engineers only, through the IAP tunnel to host port 3000.
server {
    listen 3000;
    client_max_body_size 10m;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    set $langfuse http://langfuse-web:3000;
    location / {
        proxy_pass $langfuse;
    }
}
```

`deploy/nginx/compose.local.yaml`: ports `["127.0.0.1:8080:8080", "127.0.0.1:3000:3000"]`.
`deploy/nginx/compose.testhost.yaml`: ports `["80:8080", "3000:3000"]`, and add to its header
comment: "Port 3000 (Langfuse UI) is open only to the IAP range 35.235.240.0/20 (rule
langfuse-testhost-allow-iap)."

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py -q`
Expected: PASS

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-03): nginx serves the Langfuse UI on port 3000`)

---

### Task 3: Collector export, rotation and trace-check settings

**Files:**
- Modify: `deploy/compose/otel-collector.yaml`, `deploy/compose/compose.yaml`, `deploy/compose/compose.local.yaml`
- Test: `backend/tests/test_compose_files.py`

- [ ] **Step 1: Update the tests** in `backend/tests/test_compose_files.py`

In `test_collector_config_has_internal_and_token_receivers`, replace

```python
    assert config["exporters"]["file"]["path"] == "/data/spans.jsonl"
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp", "otlp/external"], "processors": ["batch"],
                      "exporters": ["debug", "file"]}
```

with

```python
    assert config["exporters"]["file"] == {
        "path": "/data/spans.jsonl",
        "rotation": {"max_megabytes": 100, "max_days": 14, "max_backups": 5}}
    assert config["exporters"]["otlphttp/langfuse"] == {
        "endpoint": "http://langfuse-web:3000/api/public/otel",
        "headers": {"Authorization": "Basic ${env:LANGFUSE_OTLP_AUTH}",
                    "x-langfuse-ingestion-version": "4"}}
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp", "otlp/external"], "processors": ["batch"],
                      "exporters": ["debug", "file", "otlphttp/langfuse"]}
```

In `test_trace_check_service_is_a_read_only_tool`, after `assert base["restart"] == "no"` add

```python
    assert base["networks"] == ["default", "edge"]          # reaches langfuse-web (S2-03)
```

and replace the local environment assertion with

```python
    assert local["environment"] == {
        "CHECK_DATABASE_URL": "postgresql://monitor:monitor@postgres:5432/monitor",
        "CHECK_LANGFUSE_URL": "http://langfuse-web:3000",
        "CHECK_LANGFUSE_PUBLIC_KEY": "pk-lf-local-00000000-0000-0000-0000-000000000000",
        "CHECK_LANGFUSE_SECRET_KEY": "sk-lf-local-00000000-0000-0000-0000-000000000000"}
```

In `test_backend_and_collector_join_edge_with_aliases`, replace

```python
    for name in ("collector-init", "trace-check"):
        assert "networks" not in services[name]
```

with

```python
    assert "networks" not in services["collector-init"]
```

In `test_local_collector_uses_the_local_test_token`, replace the assertion with

```python
    assert local["environment"] == {
        "OTLP_TOKEN": "local-dev-otlp-token-not-a-secret",
        "LANGFUSE_OTLP_AUTH": "cGstbGYtbG9jYWwtMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwOnNrLWxmLWxvY2FsLTAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMA=="}
```

In `test_collector_config_has_internal_and_token_receivers`, the loop that forbids words must not forbid `authorization` any more (the exporter header is named `Authorization`); replace it with

```python
    for word in ("password", "secret", "local-dev-otlp-token", "pk-lf-", "sk-lf-"):
        assert word not in text.lower()
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL in the changed tests

- [ ] **Step 3: Implement**

`deploy/compose/otel-collector.yaml`: replace the `exporters:` block with

```yaml
exporters:
  debug:
    verbosity: basic
  file:
    path: /data/spans.jsonl
    # The trace check tool reads this file and its rotated copies (S2-03: kept, size-limited).
    rotation:
      max_megabytes: 100
      max_days: 14
      max_backups: 5
  # Langfuse OTLP endpoint (S2-03); the project keys come from the environment.
  otlphttp/langfuse:
    endpoint: http://langfuse-web:3000/api/public/otel
    headers:
      Authorization: "Basic ${env:LANGFUSE_OTLP_AUTH}"
      x-langfuse-ingestion-version: "4"
```

and the pipeline `exporters: [debug, file, otlphttp/langfuse]`. Update the header comment:
"Writes the spans to the log, to /data/spans.jsonl (rotated) and to Langfuse (S2-03)."

`deploy/compose/compose.yaml`, service `trace-check`: add

```yaml
    networks: [default, edge]   # reaches langfuse-web for the 5th item (S2-03)
```

`deploy/compose/compose.local.yaml`: in `collector.environment` add
`LANGFUSE_OTLP_AUTH: cGstbGYtbG9jYWwtMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwOnNrLWxmLWxvY2FsLTAwMDAwMDAwLTAwMDAtMDAwMC0wMDAwLTAwMDAwMDAwMDAwMA==   # local test keys`;
in `trace-check.environment` add
`CHECK_LANGFUSE_URL: http://langfuse-web:3000`, `CHECK_LANGFUSE_PUBLIC_KEY: pk-lf-local-00000000-0000-0000-0000-000000000000`,
`CHECK_LANGFUSE_SECRET_KEY: sk-lf-local-00000000-0000-0000-0000-000000000000   # local test value`.

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_nginx_files.py tests/test_langfuse_files.py -q`
Expected: PASS

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-03): Collector exports to Langfuse; rotated span file`)

---

### Task 4: trace check, 5th item and rotated files

**Files:**
- Modify: `backend/app/trace_check.py`, `backend/scripts/check_trace.py`
- Test: `backend/tests/test_trace_check.py`, `backend/tests/test_check_trace_script.py`

**Interfaces:**
- Produces: `check(trace_id, rows, spans, *, backend_only, stored_rows=None, skipped_lines=0, langfuse_names: list[str] | None = None, langfuse_error: str | None = None) -> Result` (5 items; the 5th is `"langfuse trace"`); `check_trace.span_files(path: str) -> list[Path]`; `check_trace.read_langfuse(trace_id: str) -> tuple[list[str] | None, str | None]`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_trace_check.py`, change the expected dict of `test_all_four_found_with_the_path` to include `"langfuse trace": SKIPPED`, and append:

```python
def test_langfuse_item_skipped_without_settings():
    result = check(T, [row()], full_trace(), backend_only=False)
    assert states(result)["langfuse trace"] == SKIPPED and len(result.checked) == 4


def test_langfuse_item_found_and_missing():
    names = ["batch.run", "batch.send", "POST", "monitor.ingest"]
    found = check(T, [row()], full_trace(), backend_only=False, langfuse_names=names)
    assert states(found)["langfuse trace"] == FOUND
    assert detail(found, "langfuse trace") == "4 observations in Langfuse"
    assert render(found).splitlines()[-1] == "RESULT: OK (5 of 5 found)"
    backend_only = check(T, [row()], full_trace(), backend_only=True,
                         langfuse_names=["monitor.ingest"])
    assert states(backend_only)["langfuse trace"] == FOUND
    missing = check(T, [row()], full_trace(), backend_only=False,
                    langfuse_names=["monitor.ingest"])
    assert states(missing)["langfuse trace"] == MISSING
    assert detail(missing, "langfuse trace") == "not in Langfuse: batch.run"
    error = check(T, [row()], full_trace(), backend_only=False, langfuse_names=[],
                  langfuse_error="Langfuse answered 401")
    assert detail(error, "langfuse trace") == "Langfuse answered 401"
```

In `backend/tests/test_check_trace_script.py`, in the `database` fixture add after the
`monkeypatch.setenv("CHECK_DATABASE_URL", url)` line:

```python
    for name in ("CHECK_LANGFUSE_URL", "CHECK_LANGFUSE_PUBLIC_KEY", "CHECK_LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
```

and append:

```python
import http.server
import threading


class FakeLangfuse:
    """A local HTTP server that answers the Observations API with a scripted reply."""

    def __init__(self, status=200, body=None):
        outer = self
        self.status, self.body, self.auth = status, body, None

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                outer.auth = self.headers.get("Authorization")
                outer.path = self.path
                payload = outer.body if isinstance(outer.body, bytes) else json.dumps(
                    outer.body).encode()
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


def langfuse_env(monkeypatch, url):
    monkeypatch.setenv("CHECK_LANGFUSE_URL", url)
    monkeypatch.setenv("CHECK_LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("CHECK_LANGFUSE_SECRET_KEY", "sk-lf-secret-value")


def test_langfuse_item_found_through_the_api(database, tmp_path, monkeypatch, capsys):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    fake = FakeLangfuse(body={"data": [{"name": "monitor.ingest"}]})
    try:
        langfuse_env(monkeypatch, fake.url)
        assert run([T, "--backend-only", "--spans-file", path]) == 0
    finally:
        fake.close()
    assert fake.path == f"/api/public/v2/observations?traceId={T}&limit=100"
    assert fake.auth == "Basic " + __import__("base64").b64encode(
        b"pk-lf-test:sk-lf-secret-value").decode()
    out = capsys.readouterr().out
    assert "langfuse trace found" in " ".join(out.split())
    assert out.splitlines()[-1] == "RESULT: OK (3 of 3 found)"


def test_langfuse_errors_are_one_safe_line(database, tmp_path, monkeypatch, capsys):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    for status, body, expected in [(401, {"message": "no"}, "Langfuse answered 401"),
                                   (200, b"not json", "Langfuse answered with bad JSON")]:
        fake = FakeLangfuse(status=status, body=body)
        try:
            langfuse_env(monkeypatch, fake.url)
            assert run([T, "--backend-only", "--spans-file", path]) == 1
        finally:
            fake.close()
        out = capsys.readouterr()
        assert expected in out.out
        assert "sk-lf-secret-value" not in out.out + out.err
    langfuse_env(monkeypatch, "http://127.0.0.1:1")
    assert run([T, "--backend-only", "--spans-file", path]) == 1
    out = capsys.readouterr()
    assert "Langfuse is not reachable (" in out.out
    assert "sk-lf-secret-value" not in out.out + out.err


def test_rotated_span_files_are_read(database, tmp_path, capsys):
    add_row(database)
    current = spans_file(tmp_path, otlp_line(raw_span("other", "c1", trace="1" * 32)))
    (tmp_path / "spans-2026-10-12T00-00-00.000.jsonl").write_text(
        otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")) + "\n", encoding="utf-8")
    assert run([T, "--backend-only", "--spans-file", current]) == 0
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trace_check.py tests/test_check_trace_script.py -q`
Expected: FAIL in the new tests

- [ ] **Step 3: Implement**

`backend/app/trace_check.py`: add after `_ancestor_link`:

```python
def _langfuse(names: list[str] | None, error: str | None, backend_only: bool) -> Item:
    name = "langfuse trace"
    if names is None and error is None:
        return Item(name, SKIPPED)
    if error:
        return Item(name, MISSING, error)
    needed = [INGEST] if backend_only else [ROOT, INGEST]
    absent = [n for n in needed if n not in (names or [])]
    if absent:
        return Item(name, MISSING, "not in Langfuse: " + ", ".join(absent))
    return Item(name, FOUND, f"{len(names or [])} observations in Langfuse")
```

and change `check` to:

```python
def check(trace_id: str, rows: list[RunRow], spans: list[Span], *, backend_only: bool,
          stored_rows: dict[str, list[RunRow]] | None = None, skipped_lines: int = 0,
          langfuse_names: list[str] | None = None,
          langfuse_error: str | None = None) -> Result:
    items = [_run_row(rows, spans, stored_rows or {}), _monitor_span(spans)]
    if backend_only:
        items += [Item("gcp root span", SKIPPED), Item("ancestor link", SKIPPED)]
    else:
        items += [_root_span(spans), _ancestor_link(spans)]
    items.append(_langfuse(langfuse_names, langfuse_error, backend_only))
    return Result(trace_id=trace_id, items=tuple(items), skipped_lines=skipped_lines)
```

`backend/scripts/check_trace.py`:
- imports: add `import base64`, `import urllib.error`, `import urllib.request`.
- add above `read_spans`:

```python
def span_files(path: str) -> list[Path]:
    """The span file and its rotated copies (same folder, same stem prefix), oldest first."""
    main = Path(path)
    rotated = sorted(p for p in main.parent.glob(f"{main.stem}*{main.suffix}") if p != main)
    return rotated + ([main] if main.exists() else [])
```

- change `read_spans` so it reads every file of `span_files(path)` in order (same per-line
  logic, the skipped count summed); if the list is empty, raise
  `SetupError(f"span file {path} not found")` as today.
- add:

```python
def read_langfuse(trace_id: str) -> tuple[list[str] | None, str | None]:
    """Observation names of the trace in Langfuse (S2-03), or (None, None) when not set up."""
    url = os.environ.get("CHECK_LANGFUSE_URL", "").strip().rstrip("/")
    public_key = os.environ.get("CHECK_LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("CHECK_LANGFUSE_SECRET_KEY", "").strip()
    if not (url and public_key and secret_key):
        return None, None
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"{url}/api/public/v2/observations?traceId={trace_id}&limit=100",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            document = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return [], f"Langfuse answered {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], f"Langfuse is not reachable ({type(exc).__name__})"
    except ValueError:
        return [], "Langfuse answered with bad JSON"
    data = document.get("data") if isinstance(document, dict) else None
    if not isinstance(data, list):
        return [], "Langfuse answered with bad JSON"
    return [str(item.get("name", "")) for item in data if isinstance(item, dict)], None
```

- in `run_once`, before `return check(...)`: `names, error = read_langfuse(args.trace_id)`, and pass
  `langfuse_names=names, langfuse_error=error` to `check`.
- update the module docstring: "5 items: … and the Langfuse trace (S2-03, skipped when the
  CHECK_LANGFUSE_* settings are absent). Reads the span file and its rotated copies."

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trace_check.py tests/test_check_trace_script.py -q`, then the fast suite `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: PASS

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-03): trace check reads Langfuse and the rotated span files`)

---

### Task 5: the `langfuse-smoke` CI test

**Files:**
- Create: `scripts/langfuse-smoke.sh`, `.github/workflows/langfuse-smoke.yml`
- Test: `backend/tests/test_langfuse_files.py` (append)

- [ ] **Step 1: Write the failing tests** — append to `backend/tests/test_langfuse_files.py`:

```python
SMOKE = ROOT / "scripts" / "langfuse-smoke.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "langfuse-smoke.yml"


def test_langfuse_smoke_script():
    text = SMOKE.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "trap cleanup EXIT" in text and "\r\n" not in text
    assert "deploy/langfuse/compose.yaml" in text and "deploy/langfuse/compose.local.yaml" in text
    assert "RESULT: OK (5 of 5 found)" in text
    assert text.count("check-trace.sh") >= 2 and "restart" in text
    assert "http://127.0.0.1:3000/api/public/health" in text
    assert "down -v" in text and "docker network rm edge" in text
    for line in text.splitlines():
        if "echo" in line:
            assert "KEY" not in line and "OTLP_TOKEN" not in line, line


def test_langfuse_smoke_workflow():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    paths = {"deploy/langfuse/**", "deploy/nginx/**", "deploy/compose/otel-collector.yaml",
             "scripts/langfuse-smoke.sh", ".github/workflows/langfuse-smoke.yml",
             "backend/app/trace_check.py", "backend/scripts/check_trace.py"}
    triggers = workflow[True]
    assert set(triggers["pull_request"]["paths"]) == paths
    assert set(triggers["push"]["paths"]) == paths and triggers["push"]["branches"] == ["dev"]
    job = workflow["jobs"]["langfuse-smoke"]
    assert job["runs-on"] == "ubuntu-latest" and job["timeout-minutes"] == 30
    assert workflow["permissions"] == {"contents": "read"}
    assert any(step.get("run") == "bash scripts/langfuse-smoke.sh" for step in job["steps"])
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py -q`
Expected: FAIL (files missing)

- [ ] **Step 3: Implement**

`.github/workflows/langfuse-smoke.yml`:

```yaml
name: Langfuse smoke test

on:
  pull_request:
    paths:
      - "deploy/langfuse/**"
      - "deploy/nginx/**"
      - "deploy/compose/otel-collector.yaml"
      - "scripts/langfuse-smoke.sh"
      - ".github/workflows/langfuse-smoke.yml"
      - "backend/app/trace_check.py"
      - "backend/scripts/check_trace.py"
  push:
    branches: [dev]
    paths:
      - "deploy/langfuse/**"
      - "deploy/nginx/**"
      - "deploy/compose/otel-collector.yaml"
      - "scripts/langfuse-smoke.sh"
      - ".github/workflows/langfuse-smoke.yml"
      - "backend/app/trace_check.py"
      - "backend/scripts/check_trace.py"

permissions:
  contents: read

jobs:
  langfuse-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - run: bash scripts/langfuse-smoke.sh
```

(The list is written twice on purpose: YAML anchors are not used in workflows.)

`scripts/langfuse-smoke.sh`:

```bash
#!/usr/bin/env bash
# Langfuse smoke test (S2-03). Linux CI and macOS.
# Starts edge, Langfuse, the monitor stack and nginx with local test values; sends one batch
# run and fake GCP job spans through nginx; the trace check must find 5 of 5 (also the
# Langfuse trace), also after a Langfuse restart. KEEP=1 keeps the stacks running.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/deploy/compose/compose.yaml" -f "$ROOT/deploy/compose/compose.local.yaml")
NGINX=(docker compose -f "$ROOT/deploy/nginx/compose.yaml" -f "$ROOT/deploy/nginx/compose.local.yaml")
LANGFUSE=(docker compose -f "$ROOT/deploy/langfuse/compose.yaml" -f "$ROOT/deploy/langfuse/compose.local.yaml")
FRONT="http://127.0.0.1:8080"
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
OTLP_TOKEN="local-dev-otlp-token-not-a-secret"    # local test value, not a secret
EXAMPLE="$ROOT/backend/schemas/batch-run/1/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"
MADE_EDGE=0

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "LANGFUSE SMOKE FAIL: $STEP"
    "${LANGFUSE[@]}" logs --no-color --tail 100 langfuse-web langfuse-worker || true
    "${COMPOSE[@]}" logs --no-color --tail 100 collector || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${NGINX[@]}" down --remove-orphans >/dev/null 2>&1 || true
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    "${LANGFUSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    if [ "$MADE_EDGE" = "1" ]; then
      docker network rm edge >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

STEP="edge network"
if ! docker network inspect edge >/dev/null 2>&1; then
  docker network create edge >/dev/null
  MADE_EDGE=1
fi

STEP="langfuse up"
"${LANGFUSE[@]}" up -d --wait --wait-timeout 600
STEP="monitor up"
"${COMPOSE[@]}" up --build -d --wait --wait-timeout 300
STEP="nginx up"
"${NGINX[@]}" up -d --wait --wait-timeout 120

STEP="langfuse health through nginx"
[ "$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/public/health)" = "200" ]

STEP="batch run and fake job spans"
TRACE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PARENT_ID="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
RUN_ID="lf-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
python3 - "$EXAMPLE" "$RUN_ID" > "$WORK/body.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1], encoding="utf-8"))
body["run_id"] = sys.argv[2]
body["use_case_id"] = "rtr-fraud-validation"
print(json.dumps(body))
PY
[ "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$FRONT/api/batch/runs" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -H "traceparent: 00-$TRACE_ID-$PARENT_ID-01" --data-binary "@$WORK/body.json")" = "201" ]
python3 - "$TRACE_ID" "$PARENT_ID" > "$WORK/spans.json" <<'PY'
import json, secrets, sys, time
trace_id, client_id = sys.argv[1], sys.argv[2]
run_id, send_id = secrets.token_hex(8), secrets.token_hex(8)
now = time.time_ns()

def span(name, span_id, parent, kind):
    return {"traceId": trace_id, "spanId": span_id, "parentSpanId": parent, "name": name,
            "kind": kind, "startTimeUnixNano": str(now), "endTimeUnixNano": str(now + 1000000)}

print(json.dumps({"resourceSpans": [{
    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "smoke-fake-job"}}]},
    "scopeSpans": [{"scope": {"name": "langfuse-smoke"}, "spans": [
        span("batch.run", run_id, "", 1),
        span("batch.send", send_id, run_id, 1),
        span("POST", client_id, send_id, 3),
    ]}]}]}))
PY
[ "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$FRONT/otlp/v1/traces" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $OTLP_TOKEN" \
  --data-binary "@$WORK/spans.json")" = "200" ]

STEP="trace check with Langfuse"
OUT="$(bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 90 || true)"
echo "$OUT"
grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"

STEP="langfuse restart"
"${LANGFUSE[@]}" restart
"${LANGFUSE[@]}" up -d --wait --wait-timeout 300
OUT="$(bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 60 || true)"
echo "$OUT"
grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"
echo "LANGFUSE SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py -q`
Expected: PASS. (The CI test runs on the pull request; do not claim it ran.)

- [ ] **Step 5: Stop for review** (Claude commits `test(s2-03): langfuse-smoke CI test`)

---

### Task 6: documentation

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md`

- [ ] **Step 1: `deploy/compose/TESTHOST.md`** — add `## Langfuse (S2-03)` before `## Check a trace (S1-07)`, numbered steps, each command in its own block:
  1. VM check: `nproc; free -g; df -h /` (expect 4 CPUs, 32 GB; if less than 50 GB is free on `/`, grow the disk first: `gcloud compute disks resize ai-ml-monitoring-dev-env --size 200 --zone asia-southeast3-c`, then on the VM `sudo growpart /dev/nvme0n1 1 && sudo resize2fs /dev/nvme0n1p1`; check the device name with `lsblk` first).
  2. Google OAuth client (console: APIs & Services → Credentials → OAuth client ID, type Web application, consent screen Internal), redirect URI `http://localhost:3000/api/auth/callback/google`. On the laptop, copy `deploy/langfuse/google-oauth.env.example` to `google-oauth.tmp` and fill in the two values in an editor (never in chat).
  3. Firewall: `gcloud compute firewall-rules create langfuse-testhost-allow-iap --network test-true-corp-ai --direction INGRESS --action ALLOW --rules tcp:3000 --source-ranges 35.235.240.0/20 --target-tags monitor-frontdoor`.
  4. Copy: `gcloud compute ssh ... --command "mkdir -m 700 /tmp/s2-03"`; `gcloud compute scp --recurse google-oauth.tmp deploy/langfuse deploy/nginx/conf.d/langfuse.conf deploy/nginx/compose.testhost.yaml deploy/compose/otel-collector.yaml deploy/compose/compose.yaml ai-ml-monitoring-dev-env:/tmp/s2-03/ --zone asia-southeast3-c --tunnel-through-iap`; then `Remove-Item google-oauth.tmp`.
  5. VM: `sudo mv /tmp/s2-03/langfuse /opt/langfuse`, `sudo mv /tmp/s2-03/langfuse.conf /opt/nginx/conf.d/`, `sudo mv /tmp/s2-03/compose.testhost.yaml /opt/nginx/`, `sudo mv /tmp/s2-03/otel-collector.yaml /tmp/s2-03/compose.yaml /opt/model-monitor/compose/`.
  6. VM: `sudo bash /opt/langfuse/make-langfuse-env.sh --admin-email <your company email> --google-file /tmp/s2-03/google-oauth.tmp` (expect three `600 root` lines and `LANGFUSE ENV DONE`).
  7. VM: in `/opt/langfuse`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait`.
  8. VM: in `/opt/model-monitor/compose`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait` (the Collector gets the exporter).
  9. VM: in `/opt/nginx`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait` (port 3000).
  10. Laptop: `gcloud compute start-iap-tunnel ai-ml-monitoring-dev-env 3000 --local-host-port=localhost:3000 --zone asia-southeast3-c`; open `http://localhost:3000`, sign in with Google; open project `model-monitor`.
  11. Add engineers: Settings → Members, by company email; they sign in with Google.
  12. Check: `sudo docker ps --format '{{.Names}} {{.Ports}}' | grep langfuse` shows no published port; `sudo bash /opt/model-monitor/compose/check-trace.sh <trace_id>` shows the `langfuse trace` item.

- [ ] **Step 2: `issues.md`** — S2-03: a dated note `**Changed 2026-10-12 (design: changes/2026-10-12-s2-03-langfuse/):**` own Compose project, private dependencies, Google sign-in through the IAP tunnel, the span file kept with rotation (the cleanup rule moves to when the trace check reads every item from Langfuse). S2-02: `**2026-10-12:** the packages stay approved (2026-10-05); the SDK use (scores) comes with S2-05.` S3-07: `**2026-10-12:** the Langfuse Google sign-in is done in S2-03; S3-07 keeps the dashboard.`

- [ ] **Step 3: `CHANGELOG.md`** — under `## [Unreleased]` / `### Added`, first item:

```markdown
- Self-hosted Langfuse (S2-03): `deploy/langfuse/` (web, worker, PostgreSQL, ClickHouse,
  Redis, MinIO; no published port). The Collector exports every span to it; nginx serves
  the UI on port 3000 (IAP tunnel on the test host, Google sign-in). The trace check tool
  shows the Langfuse trace as a 5th item and reads the rotated span files. New CI test
  `langfuse-smoke`.
```

- [ ] **Step 4: `DEVLOG.md`** — at the top of `## Work log`: `### 2026-10-12 — S2-03: self-hosted Langfuse` with what was built, the decisions from `intent.md`, the exact pytest results, and "Not yet run: the `langfuse-smoke` CI test (on the pull request; it proves the Langfuse setting names) and the test-host deploy (TESTHOST.md, Langfuse)".

- [ ] **Step 5: Run** `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py tests/test_nginx_files.py tests/test_langfuse_files.py -q`, then the fast suite `.venv\Scripts\python.exe -m pytest -q -m "not slow"`. Expected: PASS.

- [ ] **Step 6: Stop for review** (Claude commits `docs(s2-03): Langfuse runbook, changelog and devlog`)
