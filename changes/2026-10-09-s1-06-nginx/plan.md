# nginx front door and OTLP token (S1-06, test-host part) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A standalone nginx Compose project serves only `/api/batch/runs`, `/api/health` (backend) and `/otlp/*` (Collector, which checks an OTLP token) on port 80 of the test host, and the CI smoke test proves the routes, the token and a full fake-job trace.

**Architecture:** `deploy/nginx/` is its own Compose project `nginx` with one file for each app in `conf.d/`. The apps join the external Docker network `edge` with app-specific aliases. The Collector gets a second receiver `otlp/external` (port 4319) with the `bearertokenauth` extension; nginx only routes paths. The smoke test starts `edge`, nginx and the monitor stack and tests everything through `127.0.0.1:8080`.

**Tech Stack:** nginx (`nginxinc/nginx-unprivileged:1.28.0-alpine`), OTel Collector contrib 0.161.0 (`bearertokenauth`), Docker Compose v2, bash, Python 3.12 + pytest + PyYAML (installed).

**Spec:** [spec.md](spec.md) (approved 2026-10-09). Intent: [intent.md](intent.md).

## Global Constraints

- nginx image: `nginxinc/nginx-unprivileged:1.28.0-alpine`. Never `latest`.
- Network `edge` is external in every Compose file that uses it. Aliases: `model-monitor-backend`, `model-monitor-collector`.
- Ports: nginx local `127.0.0.1:8080:8080`; test host `80:8080`; the nginx base file has no ports. Collector port `4319` is never published.
- Collector: `otlp` on `0.0.0.0:4318` (no auth, unchanged); `otlp/external` on `0.0.0.0:4319` with `auth.authenticator: bearertokenauth`; `bearertokenauth.token` is exactly `${env:OTLP_TOKEN}`, `scheme: Bearer`.
- Local test token: `local-dev-otlp-token-not-a-secret` (not a secret). Never put a real token in a file, test or log.
- Test-host token file: `/opt/model-monitor/collector.env`, mode 600, root, `OTLP_TOKEN=<token>`, made by `deploy/compose/make-collector-env.sh`.
- `client_max_body_size 10m` (= backend `BATCH_MAX_BODY_BYTES`).
- No backend code change. No new pip or npm package.
- Shell scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, LF line endings.
- Tests run from `backend/`: `.venv\Scripts\python.exe -m pytest ...` (Windows). If pytest cannot open its temp or cache folder in the sandbox, add `-p no:cacheprovider --basetemp=.pytest-tmp` and delete `backend/.pytest-tmp` afterwards.
- Docker and bash are not available on the Windows computer: never claim nginx, the Collector, a shell script or the smoke test ran. The CI smoke test on the pull request is the proof.
- **Codex: do not run `git commit` or `git add`.** Leave changes in the working tree; Claude reviews and commits each task.

## Review Focus

- An empty or missing test-host token must fail closed, not open. (Task 2: `test_make_collector_env_refuses_short_tokens` checks the length check; `test_testhost_collector_requires_the_env_file` checks `required: true`.)
- A path that is not on the allowlist, also with a prefix trick like `/api/batch/runs/../live/portfolio` or `/api/healthx`, must give 404. (Task 1: `test_model_monitor_conf_allows_only_three_routes` checks exact-match locations; Task 3 smoke checks `/api/healthx` → 404.)
- The token or the API key must never reach a log. (Task 1: `test_nginx_files_log_no_headers`; Task 3: the smoke test check of echo lines.)
- An nginx config change must trigger the CI smoke test. (Task 3: `test_ci_workflow_paths` includes `deploy/nginx/**`.)
- When the monitor stack is down, nginx must still start (resolver plus variables). (Task 1: `test_model_monitor_conf_resolves_at_request_time`.)

---

## File structure

| File | Task | Responsibility |
|---|---|---|
| `deploy/nginx/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml` | 1 | The nginx project |
| `deploy/nginx/conf.d/00-common.conf`, `conf.d/model-monitor.conf` | 1 | Shared settings; model-monitor routes |
| `deploy/nginx/README.md` | 1 | How to run nginx and add an app |
| `backend/tests/test_nginx_files.py` | 1 | Static tests of the nginx project |
| `deploy/compose/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml`, `otel-collector.yaml` | 2 | `edge` network, Collector token receiver |
| `deploy/compose/collector.env.example`, `deploy/compose/make-collector-env.sh` | 2 | Token template; test-host setup script |
| `backend/tests/test_compose_files.py` | 2, 3 | Static tests of the monitor stack and the smoke script |
| `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml` | 3 | The smoke test through nginx |
| `deploy/compose/TESTHOST.md`, `deploy/compose/README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md` | 4 | Docs |

---

### Task 1: the nginx project

**Files:**
- Create: `deploy/nginx/compose.yaml`, `deploy/nginx/compose.local.yaml`, `deploy/nginx/compose.testhost.yaml`, `deploy/nginx/conf.d/00-common.conf`, `deploy/nginx/conf.d/model-monitor.conf`, `deploy/nginx/README.md`
- Test: `backend/tests/test_nginx_files.py`

**Interfaces:**
- Produces: the nginx project, reachable as `http://127.0.0.1:8080` locally; upstream names `model-monitor-backend:8000` and `model-monitor-collector:4319` (Task 2 gives these aliases).

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_nginx_files.py`:

```python
"""S1-06 (test-host part): static checks of the standalone nginx front door."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deploy" / "nginx"
CONF = NGINX / "conf.d"


def _load(name: str) -> dict:
    return yaml.safe_load((NGINX / name).read_text(encoding="utf-8"))


def _locations(text: str) -> list[str]:
    return re.findall(r"^\s*location\s+([^{]+?)\s*\{", text, flags=re.MULTILINE)


def test_nginx_project_is_pinned_non_root_and_on_edge():
    base = _load("compose.yaml")
    assert base["name"] == "nginx"
    nginx = base["services"]["nginx"]
    assert nginx["image"] == "nginxinc/nginx-unprivileged:1.28.0-alpine"
    assert nginx["volumes"] == ["./conf.d:/etc/nginx/conf.d:ro"]
    assert nginx["networks"] == ["edge"]
    assert "/healthz" in " ".join(nginx["healthcheck"]["test"])
    assert "ports" not in nginx and "user" not in nginx
    assert base["networks"] == {"edge": {"external": True}}


def test_nginx_ports_per_host():
    assert _load("compose.local.yaml")["services"]["nginx"]["ports"] == ["127.0.0.1:8080:8080"]
    assert _load("compose.testhost.yaml")["services"]["nginx"]["ports"] == ["80:8080"]


def test_model_monitor_conf_allows_only_three_routes():
    text = (CONF / "model-monitor.conf").read_text(encoding="utf-8")
    assert _locations(text) == ["= /api/batch/runs", "= /api/health", "/otlp/", "/"]
    catch_all = text.split("location / {", 1)[1].split("}", 1)[0]
    assert "return 404;" in catch_all
    assert re.search(r"^\s*listen 8080;", text, flags=re.MULTILINE)
    assert "client_max_body_size 10m;" in text
    assert "rewrite ^/otlp/(.*)$ /$1 break;" in text


def test_model_monitor_conf_resolves_at_request_time():
    text = (CONF / "model-monitor.conf").read_text(encoding="utf-8")
    assert "set $mm_backend http://model-monitor-backend:8000;" in text
    assert "set $mm_collector http://model-monitor-collector:4319;" in text
    # every proxy_pass uses a variable, so nginx starts even when the app is down
    passes = re.findall(r"proxy_pass\s+([^;]+);", text)
    assert passes and all(p.startswith("$") for p in passes)
    common = (CONF / "00-common.conf").read_text(encoding="utf-8")
    assert "resolver 127.0.0.11" in common


def test_common_conf_hides_version_and_has_internal_health():
    text = (CONF / "00-common.conf").read_text(encoding="utf-8")
    assert "server_tokens off;" in text
    assert "listen 127.0.0.1:8081;" in text
    assert "location = /healthz" in text


def test_nginx_files_log_no_headers():
    for path in NGINX.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "log_format" not in text, path.name
            assert "local-dev-otlp-token-not-a-secret" not in text, path.name
            if path.suffix == ".conf":
                assert "authorization" not in text.lower(), path.name
            assert "\r\n" not in text, path.name
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py -q`
Expected: FAIL (`FileNotFoundError` for `deploy/nginx/compose.yaml`)

- [ ] **Step 3: Implement**

`deploy/nginx/compose.yaml`:

```yaml
# Standalone front door (S1-06). One nginx for all apps on this host. Each app has its own
# file in conf.d/. The apps join the external network `edge` with their own aliases.
# Make the network once: docker network create edge
# Run from this folder: docker compose -f compose.yaml -f compose.<local|testhost>.yaml up -d --wait
name: nginx

services:
  nginx:
    image: nginxinc/nginx-unprivileged:1.28.0-alpine
    volumes:
      - ./conf.d:/etc/nginx/conf.d:ro
    networks:
      - edge
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8081/healthz"]
      interval: 5s
      timeout: 3s
      retries: 12
    restart: unless-stopped

networks:
  edge:
    external: true
```

`deploy/nginx/compose.local.yaml`:

```yaml
# Laptop and CI (S1-06): the front door only on the loopback address.
services:
  nginx:
    ports:
      - "127.0.0.1:8080:8080"
```

`deploy/nginx/compose.testhost.yaml`:

```yaml
# GCP test host (S1-06): host port 80. The VPC rule monitor-testhost-allow-http-jobs allows
# only the job subnet 10.10.0.0/24. Plain HTTP inside the VPC (decided 2026-10-08).
services:
  nginx:
    ports:
      - "80:8080"
```

`deploy/nginx/conf.d/00-common.conf`:

```nginx
# Shared settings for all apps (S1-06). This folder replaces the image's default.conf.
server_tokens off;
# Docker DNS at request time: nginx starts even when an app is down; that app gives 502.
resolver 127.0.0.11 valid=10s ipv6=off;

# Health of nginx itself, for the Compose health check. Inside the container only.
server {
    listen 127.0.0.1:8081;
    location = /healthz {
        access_log off;
        return 200 "ok\n";
    }
}
```

`deploy/nginx/conf.d/model-monitor.conf`:

```nginx
# model-monitor (S1-06): the GCP job paths only. Host port 80 on the test host.
# Every other path gives 404, so nobody reaches the dashboard API here (S3-07).
server {
    listen 8080;
    client_max_body_size 10m;          # = BATCH_MAX_BODY_BYTES of the backend
    proxy_http_version 1.1;
    proxy_set_header Host $host;

    set $mm_backend http://model-monitor-backend:8000;
    set $mm_collector http://model-monitor-collector:4319;

    location = /api/batch/runs {
        proxy_pass $mm_backend;
    }
    location = /api/health {
        proxy_pass $mm_backend;
    }
    # OTLP/HTTP: /otlp/v1/traces -> Collector /v1/traces. The Collector checks the token.
    location /otlp/ {
        rewrite ^/otlp/(.*)$ /$1 break;
        proxy_pass $mm_collector;
    }
    location / {
        return 404;
    }
}
```

`deploy/nginx/README.md`:

````markdown
# nginx front door (S1-06)

One nginx for all apps on a host. Each app has one file in `conf.d/`. The apps join the
external Docker network `edge` with their own aliases (for example `model-monitor-backend`),
so two apps with a service named `backend` cannot collide. nginx finds the apps at request
time: if an app is down, nginx still starts, and only that app gives `502`.

There is no DNS name on the test host, so each app has its own port (one `server` block for
each port): 80 = model-monitor job paths (`conf.d/model-monitor.conf`). Sprint 2 adds the
dashboard and Langfuse.

## Start

Make the network once:

```bash
docker network create edge
```

From this folder (on the test host, `/opt/nginx`, with `sudo`):

```bash
docker compose -f compose.yaml -f compose.local.yaml up -d --wait
```

Use `compose.testhost.yaml` instead of `compose.local.yaml` on the test host.

## Add an app

1. Add `conf.d/<app>.conf` with a `server` block on a new port, and publish the port in the host file.
2. Check the configuration:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec nginx nginx -t
```

3. Reload without a restart of the other apps:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec nginx nginx -s reload
```

A new published port needs `up -d` instead of a reload.
````

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s1-06): standalone nginx front door`)

---

### Task 2: the `edge` network and the Collector token

**Files:**
- Modify: `deploy/compose/compose.yaml`, `deploy/compose/compose.local.yaml`, `deploy/compose/compose.testhost.yaml`, `deploy/compose/otel-collector.yaml`
- Create: `deploy/compose/collector.env.example`, `deploy/compose/make-collector-env.sh`
- Test: `backend/tests/test_compose_files.py`

**Interfaces:**
- Consumes: Task 1 upstream names.
- Produces: aliases `model-monitor-backend`, `model-monitor-collector` on `edge`; Collector receiver `otlp/external` on 4319 with the token from `OTLP_TOKEN`.

- [ ] **Step 1: Update and add the tests** in `backend/tests/test_compose_files.py`

Replace the whole function `test_collector_config_writes_spans_to_the_volume_without_secrets` with:

```python
def test_collector_config_has_internal_and_token_receivers():
    text = (COMPOSE / "otel-collector.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    receivers = config["receivers"]
    assert receivers["otlp"]["protocols"] == {"http": {"endpoint": "0.0.0.0:4318"}}
    external = receivers["otlp/external"]["protocols"]["http"]
    assert external == {"endpoint": "0.0.0.0:4319",
                        "auth": {"authenticator": "bearertokenauth"}}
    assert config["extensions"]["bearertokenauth"] == {
        "scheme": "Bearer", "token": "${env:OTLP_TOKEN}"}
    assert config["service"]["extensions"] == ["health_check", "bearertokenauth"]
    assert config["exporters"]["file"]["path"] == "/data/spans.jsonl"
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp", "otlp/external"], "processors": ["batch"],
                      "exporters": ["debug", "file"]}
    for word in ("password", "secret", "authorization", "local-dev-otlp-token"):
        assert word not in text.lower()
```

Replace in `test_testhost_file_uses_registry_image_and_host_secrets` the first assertion and the ports assertion:

```python
    assert set(host) == {"backend", "collector", "trace-check"}   # no database on the VM
```

```python
    assert backend["ports"] == ["127.0.0.1:8000:8000"]   # for operators in the VM; jobs use nginx
```

Append:

```python
def test_backend_and_collector_join_edge_with_aliases():
    base = _load("compose.yaml")
    services = base["services"]
    assert services["backend"]["networks"] == {
        "default": {}, "edge": {"aliases": ["model-monitor-backend"]}}
    assert services["collector"]["networks"] == {
        "default": {}, "edge": {"aliases": ["model-monitor-collector"]}}
    for name in ("collector-init", "trace-check"):
        assert "networks" not in services[name]
    assert base["networks"] == {"edge": {"external": True}}


def test_port_4319_is_never_published():
    for path in COMPOSE.glob("compose*.yaml"):
        services = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]
        for service in services.values():
            assert not any("4319" in str(port) for port in service.get("ports", [])), path.name


def test_local_collector_uses_the_local_test_token():
    local = _load("compose.local.yaml")["services"]["collector"]
    assert local["environment"] == {"OTLP_TOKEN": "local-dev-otlp-token-not-a-secret"}


def test_testhost_collector_requires_the_env_file():
    host = _load("compose.testhost.yaml")["services"]["collector"]
    assert host["env_file"] == [{"path": "/opt/model-monitor/collector.env", "required": True}]
    assert "environment" not in host


def test_collector_env_example_has_names_only():
    text = (COMPOSE / "collector.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert values == {"OTLP_TOKEN": ""}


def test_make_collector_env_refuses_short_tokens():
    text = (COMPOSE / "make-collector-env.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "\r\n" not in text
    assert "umask 077" in text and "chmod 600" in text
    assert "/opt/model-monitor/collector.env" in text
    assert '${#TOKEN}' in text and "-lt 32" in text
    assert "printf 'OTLP_TOKEN=%s\\n'" in text
    for line in text.splitlines():
        if "echo" in line:
            assert "TOKEN" not in line.replace("OTLP_TOKEN", ""), line
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL (no `otlp/external`, no `edge`, no new files)

- [ ] **Step 3: Implement**

`deploy/compose/compose.yaml` — in `backend`, after `restart: unless-stopped`, add:

```yaml
    networks:
      default: {}
      edge:
        aliases: [model-monitor-backend]
```

in `collector`, after `restart: unless-stopped`, add:

```yaml
    networks:
      default: {}
      edge:
        aliases: [model-monitor-collector]
```

and at the end of the file, after `volumes:` / `collector-data:`:

```yaml

networks:
  edge:
    external: true          # made once: docker network create edge (see deploy/nginx/README.md)
```

`deploy/compose/compose.local.yaml` — replace the `collector` service with:

```yaml
  collector:
    environment:
      OTLP_TOKEN: local-dev-otlp-token-not-a-secret   # local test value, not a secret
    ports:
      - "127.0.0.1:4318:4318"
```

`deploy/compose/compose.testhost.yaml` — change the backend `ports` comment line to
`# For operators inside the VM. The GCP jobs use nginx on port 80 (deploy/nginx).` and add
before `trace-check`:

```yaml
  collector:
    env_file:
      # OTLP_TOKEN of the GCP jobs (S1-06); made by make-collector-env.sh, mode 600
      - path: /opt/model-monitor/collector.env
        required: true
```

`deploy/compose/otel-collector.yaml` — replace the header comment's last two lines with
`# limit and the attribute filter. The OTLP token comes from the environment (OTLP_TOKEN);`
`# this file contains no credential.` and replace `extensions:` and `receivers:` and the `service:` block with:

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  # The OTLP token of the GCP jobs (S1-06). Only the external receiver uses it.
  bearertokenauth:
    scheme: Bearer
    token: ${env:OTLP_TOKEN}

receivers:
  otlp:                        # internal: the backend, inside the Docker network
    protocols:
      http:
        endpoint: 0.0.0.0:4318
  otlp/external:               # GCP jobs, only through nginx (/otlp/*); never published
    protocols:
      http:
        endpoint: 0.0.0.0:4319
        auth:
          authenticator: bearertokenauth
```

```yaml
service:
  extensions: [health_check, bearertokenauth]
  pipelines:
    traces:
      receivers: [otlp, otlp/external]
      processors: [batch]
      exporters: [debug, file]
```

(`processors` and `exporters` do not change.)

`deploy/compose/collector.env.example`:

```
# Template for /opt/model-monitor/collector.env on the test host (S1-06). Names only.
# make-collector-env.sh writes the real file (mode 600, root) from the copied token file.
# The value is the Secret Manager secret otlp-token.
OTLP_TOKEN=
```

`deploy/compose/make-collector-env.sh`:

```bash
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
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_nginx_files.py -q`
Expected: PASS

- [ ] **Step 5: Stop for review** (Claude commits `feat(s1-06): edge network and the Collector OTLP token`)

---

### Task 3: the smoke test through nginx

**Files:**
- Modify: `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml`
- Test: `backend/tests/test_compose_files.py` (`test_smoke_script_cleans_up_and_fails_fast`, `test_ci_workflow_paths`)

**Interfaces:**
- Consumes: Task 1 (nginx on `127.0.0.1:8080`), Task 2 (`edge`, token receiver), S1-07 `deploy/compose/check-trace.sh`.

- [ ] **Step 1: Update the tests** in `backend/tests/test_compose_files.py`

In `test_smoke_script_cleans_up_and_fails_fast`, replace the line

```python
    assert 'check-trace.sh" "$TRACE_ID" --backend-only --wait 30' in text
```

with

```python
    # the full trace through nginx: all four trace check items (S1-06 + S1-05 + S1-07)
    assert 'check-trace.sh" "$TRACE_ID" --wait 30' in text
    assert "--backend-only" not in text
    assert "docker network create edge" in text and "docker network rm edge" in text
    assert "deploy/nginx/compose.yaml" in text and "deploy/nginx/compose.local.yaml" in text
    assert 'FRONT="http://127.0.0.1:8080"' in text
    for path in ("/api/live/portfolio", "/api/readiness", "/api/healthx", "/otlp/v1/traces"):
        assert path in text
    assert "Bearer wrong-token" in text and '"401"' in text and '"404"' in text
    assert '"$FRONT/api/batch/runs"' in text
    assert "batch.run" in text and "batch.send" in text
```

and replace the key-lines block with

```python
    # the key and the token are sent only in headers, never echoed
    secret_lines = [line for line in text.splitlines()
                    if ("KEY" in line or "OTLP_TOKEN" in line) and "echo" in line]
    assert secret_lines == []
```

In `test_ci_workflow_paths`, replace the `paths` set with:

```python
    paths = {"deploy/compose/**", "deploy/nginx/**", "backend/**", "scripts/compose-smoke.sh",
             ".github/workflows/compose-smoke.yml"}
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL in the two changed tests

- [ ] **Step 3: Implement**

`.github/workflows/compose-smoke.yml`: add `- "deploy/nginx/**"` after `- "deploy/compose/**"` in both `pull_request.paths` and `push.paths`.

`scripts/compose-smoke.sh` — the complete new file:

```bash
#!/usr/bin/env bash
# Smoke test of the local Compose stack (S1-06, S1-07). macOS and Linux.
# Starts the edge network, the monitor stack (backend + PostgreSQL + OTel Collector) and the
# nginx front door. Through nginx it checks the routes, the OTLP token, one batch run with a
# known traceparent, and fake GCP job spans; then the trace check tool finds all four items.
# KEEP=1 keeps the stacks running afterwards. Needs: docker (Compose v2), curl, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/deploy/compose"
COMPOSE=(docker compose -f compose.yaml -f compose.local.yaml)
NGINX=(docker compose -f "$ROOT/deploy/nginx/compose.yaml" -f "$ROOT/deploy/nginx/compose.local.yaml")
BASE_URL="http://127.0.0.1:8000"
FRONT="http://127.0.0.1:8080"
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
OTLP_TOKEN="local-dev-otlp-token-not-a-secret"    # local test value, not a secret
EXAMPLE="$ROOT/changes/2026-10-02-batch-monitoring-mvp/schema/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"
MADE_EDGE=0

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "SMOKE FAIL: $STEP"
    "${COMPOSE[@]}" logs --no-color --tail 200 backend collector || true
    "${NGINX[@]}" logs --no-color --tail 100 nginx || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${NGINX[@]}" down --remove-orphans >/dev/null 2>&1 || true
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    if [ "$MADE_EDGE" = "1" ]; then
      docker network rm edge >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

# code <expected> <curl arguments...>: fails the step when the HTTP status differs
code() {
  local expected="$1"
  shift
  local got
  got="$(curl -sS -o /dev/null -w '%{http_code}' "$@")"
  [ "$got" = "$expected" ] || { echo "expected $expected, got $got"; return 1; }
}

STEP="edge network"
if ! docker network inspect edge >/dev/null 2>&1; then
  docker network create edge >/dev/null
  MADE_EDGE=1
fi

STEP="compose up"
"${COMPOSE[@]}" up --build --wait --wait-timeout 300

STEP="nginx up"
"${NGINX[@]}" up -d --wait --wait-timeout 120

STEP="readiness"
curl -fsS "$BASE_URL/api/readiness" >/dev/null

STEP="nginx routes"
code "200" "$FRONT/api/health"
code "404" "$FRONT/api/live/portfolio"
code "404" "$FRONT/api/readiness"
code "404" "$FRONT/api/healthx"

STEP="OTLP token required"
code "401" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" --data '{}'
code "401" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong-token" --data '{}'

STEP="prepare request"
TRACE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PARENT_ID="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
RUN_ID="smoke-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
python3 - "$EXAMPLE" "$RUN_ID" > "$WORK/body.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1], encoding="utf-8"))
body["run_id"] = sys.argv[2]
print(json.dumps(body))
PY

STEP="POST /api/batch/runs through nginx"
STATUS="$(curl -sS -o "$WORK/response.json" -w '%{http_code}' -X POST "$FRONT/api/batch/runs" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-$TRACE_ID-$PARENT_ID-01" \
  --data-binary "@$WORK/body.json")"
[ "$STATUS" = "201" ]
python3 - "$WORK/response.json" "$TRACE_ID" <<'PY'
import json, sys
answer = json.load(open(sys.argv[1], encoding="utf-8"))
assert answer["trace_id"] == sys.argv[2], "trace_id in the answer is not the sent trace ID"
PY

STEP="batch_runs row"
ROW="$("${COMPOSE[@]}" exec -T postgres psql -U monitor -d monitor -tAc \
  "select trace_id, trace_id_source from batch_runs where run_id = '$RUN_ID'")"
[ "$ROW" = "$TRACE_ID|traceparent" ]

STEP="fake job spans through nginx"
# What a GCP job sends (S1-05 part A): batch.run -> batch.send -> HTTP client span. The client
# span ID is the parent ID of the traceparent above, so the chain reaches monitor.ingest.
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
    "scopeSpans": [{"scope": {"name": "compose-smoke"}, "spans": [
        span("batch.run", run_id, "", 1),
        span("batch.send", send_id, run_id, 1),
        span("POST", client_id, send_id, 3),
    ]}]}]}))
PY
code "200" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OTLP_TOKEN" --data-binary "@$WORK/spans.json"

STEP="check-trace"
bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 30
echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_nginx_files.py -q`
Expected: PASS. (Do not claim the smoke test ran; CI runs it on the pull request.)

- [ ] **Step 5: Stop for review** (Claude commits `test(s1-06): smoke test through nginx with a full fake-job trace`)

---

### Task 4: Documentation

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `deploy/compose/README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md`

- [ ] **Step 1: `deploy/compose/TESTHOST.md`**
  - In the intro, replace "Until the front door exists (S1-06 test-host part), the backend listens only on `127.0.0.1:8000` inside the VM." with "The GCP jobs reach the monitor through nginx on port 80 (`deploy/nginx`, on the VM `/opt/nginx`). The backend also listens on `127.0.0.1:8000` for operators inside the VM."
  - Files table: add `/opt/nginx/` (`compose.yaml`, `compose.testhost.yaml`, `conf.d/` from `deploy/nginx`, 644), `/opt/model-monitor/compose/make-collector-env.sh` (755), `/opt/model-monitor/collector.env` (`OTLP_TOKEN`, made by `make-collector-env.sh`, **600**).
  - Add a section `## Front door and OTLP token (S1-06)` before `## Check a trace (S1-07)` with these numbered steps, each command in its own block:
    1. `gcloud auth login` (if the login expired).
    2. Make the token file on the laptop (PowerShell, repository root): `backend\.venv\Scripts\python.exe -c "import secrets,pathlib; pathlib.Path('otlp-token.tmp').write_text(secrets.token_urlsafe(32), encoding='ascii')"`
    3. Check the replication of the existing secret: `gcloud secrets describe batch-api-key-rtr-fraud-validation --format="yaml(replication)"`; create the new secret with the same replication: `gcloud secrets create otlp-token --data-file otlp-token.tmp` (add `--replication-policy user-managed --locations <region>` if the existing secret uses that).
    4. `gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "mkdir -m 700 /tmp/s1-06"`
    5. `gcloud compute scp otlp-token.tmp ai-ml-monitoring-dev-env:/tmp/s1-06/ --zone asia-southeast3-c --tunnel-through-iap`, then `Remove-Item otlp-token.tmp`.
    6. Copy `deploy/nginx` to `/opt/nginx` and the changed `deploy/compose` files to `/opt/model-monitor/compose` (through `/tmp` with `gcloud compute scp`, then `sudo mv`).
    7. VM: `sudo docker network create edge` (once).
    8. VM: `sudo bash /opt/model-monitor/compose/make-collector-env.sh /tmp/s1-06/otlp-token.tmp` — expected `600 root /opt/model-monitor/collector.env`, `COLLECTOR ENV DONE`.
    9. VM: in `/opt/model-monitor/compose`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait`.
    10. VM: in `/opt/nginx`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait`.
    11. Checks on the VM: `curl -s -o /dev/null -w '%{http_code}\n' http://10.10.0.4/api/health` → `200`; the same for `/api/live/portfolio` → `404`; `curl -s -o /dev/null -w '%{http_code}\n' -X POST http://10.10.0.4/otlp/v1/traces -H 'Content-Type: application/json' --data '{}'` → `401`.
    12. The job (Prakasit): `secretAccessor` on `otlp-token` for the job service account; `OTEL_EXPORTER_OTLP_ENDPOINT=http://10.10.0.4/otlp`; `OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <token>`; from the job runtime `curl http://10.10.0.4/api/health` → `200` (closes the S1-04 test).
  - Rollback: in `/opt/nginx`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml down` closes port 80.
  - Token change: add a secret version, repeat steps 4, 5, 8 and 9, then restart the jobs.

- [ ] **Step 2: `deploy/compose/README.md`** — add a short section "nginx front door (S1-06)": the smoke test starts `edge` and nginx itself; to run them by hand, see `deploy/nginx/README.md`; through nginx the local URL is `http://127.0.0.1:8080`; the local OTLP token is `local-dev-otlp-token-not-a-secret`.

- [ ] **Step 3: `issues.md` S1-06** — after the paragraph that starts "`<host>` is the internal IP of the VM", add:
`**Design (2026-10-09):** changes/2026-10-09-s1-06-nginx/. nginx is a standalone Compose project (deploy/nginx, one conf.d file for each app, external network edge). The Collector checks the OTLP token (bearertokenauth on the receiver otlp/external, port 4319); nginx routes paths only.`

- [ ] **Step 4: `CHANGELOG.md`** — under `## [Unreleased]` / `### Added`, first item:

```markdown
- nginx front door (S1-06): a standalone Compose project (`deploy/nginx`) that serves only
  `/api/batch/runs`, `/api/health` and `/otlp/*` (port 80 on the test host). The Collector
  accepts GCP spans only with the OTLP token (`bearertokenauth`, receiver `otlp/external`).
  The CI smoke test runs through nginx and checks a full fake-job trace.
```

- [ ] **Step 5: `DEVLOG.md`** — add at the top of `## Work log` an entry `### 2026-10-09 — S1-06: nginx front door and the OTLP token` with: what was built (files), the decisions from `intent.md`, the exact pytest results you ran, and "Not yet run: the CI smoke test (on the pull request) and the test-host deploy (the project owner runs the token steps)".

- [ ] **Step 6: Run** `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py tests/test_nginx_files.py -q`, then the fast suite `.venv\Scripts\python.exe -m pytest -q -m "not slow"`. Expected: PASS.

- [ ] **Step 7: Stop for review** (Claude commits `docs(s1-06): front door runbook, changelog and devlog`)
