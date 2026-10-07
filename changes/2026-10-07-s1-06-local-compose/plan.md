# Local Compose stack with the OTel Collector (S1-06, local part) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One command starts the backend, PostgreSQL 18.6 and the OTel Collector 0.161.0; a smoke test proves that a batch run is stored and its `monitor.ingest` span reaches the Collector file with the same trace ID.

**Architecture:** A base `deploy/compose/compose.yaml` (backend, collector) plus `compose.local.yaml` (postgres, build, local ports and settings) and `otel-collector.yaml`. `scripts/compose-smoke.sh` runs the stack test on macOS and Linux; `.github/workflows/compose-smoke.yml` runs it in CI. A static pytest (`tests/test_compose_files.py`) checks the files where Docker is not available.

**Tech Stack:** Docker Compose v2, `postgres:18.6-bookworm`, `otel/opentelemetry-collector-contrib:0.161.0`, bash, Python 3.12 (PyYAML is already installed), GitHub Actions.

**Spec:** [spec.md](spec.md) (approved 2026-10-07). Intent: [intent.md](intent.md).

## Global Constraints

- Images: `postgres:18.6-bookworm`, `otel/opentelemetry-collector-contrib:0.161.0`. Never `latest`.
- Local test key: `local-dev-batch-key-not-a-secret`; its SHA-256 is `ca9263478834f0d9f054e84eda1a55dee86d8a6551f27aa8a2c751a4b541b200`; use case `GCP-UC-03`. Only the hash goes in a Compose file.
- Published ports: `127.0.0.1:8000:8000` (backend) and `127.0.0.1:4318:4318` (collector), only in `compose.local.yaml`. PostgreSQL is never published.
- Collector file output: `/tmp/spans.jsonl` in the container; read it with `docker compose cp`. No volume for it.
- No secret in any file. The local PostgreSQL password `monitor` is a local-only value.
- No new pip or npm package. No change to backend code.
- Run Compose commands from `deploy/compose/`: `docker compose -f compose.yaml -f compose.local.yaml ...`.
- Tests run from `backend/`: `.venv/bin/python -m pytest ...` (Windows: `.venv\Scripts\python.exe -m pytest ...`).
- Docker is not available on the Windows development computer: never claim a stack test passed there.

## Review Focus

- A published port without `127.0.0.1` would open the laptop stack to the network. (Task 1, `test_published_ports_are_loopback_only`.)
- The base file must not depend on the local file (no `build:`, no `postgres` dependency, no published port), or the test host inherits local settings. (Task 1, `test_base_file_has_no_local_settings`.)
- A smoke test that leaves volumes behind breaks the next run on the Mac. (Task 2, `test_smoke_script_cleans_up_and_fails_fast`.)
- A smoke test that prints the key or the body would leak into CI logs. (Task 2, same test checks that the key appears only in the `Authorization` header line.)
- A CI workflow that runs on every push to every branch wastes minutes; it must be limited to the stack paths. (Task 2, `test_ci_workflow_paths`.)

---

## File structure

| File | Task | Responsibility |
|---|---|---|
| `backend/tests/test_compose_files.py` | 1, 2 | Static checks of the Compose files, the script and the workflow |
| `deploy/compose/compose.yaml` | 1 | Base services |
| `deploy/compose/compose.local.yaml` | 1 | Local services and settings |
| `deploy/compose/otel-collector.yaml` | 1 | Collector configuration |
| `scripts/compose-smoke.sh` | 2 | Stack smoke test |
| `.github/workflows/compose-smoke.yml` | 2 | CI for the smoke test |
| `deploy/compose/README.md`, `TESTING.md`, `README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md` | 3 | Docs |

---

### Task 1: Compose files and the Collector configuration

**Files:**
- Create: `backend/tests/test_compose_files.py`
- Create: `deploy/compose/compose.yaml`, `deploy/compose/compose.local.yaml`, `deploy/compose/otel-collector.yaml`

**Interfaces:**
- Produces: service names `backend`, `collector`, `postgres`; the Collector OTLP/HTTP endpoint `http://collector:4318`; the file `/tmp/spans.jsonl` in `collector`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_compose_files.py`:

```python
"""S1-06 (local part): static checks of the Compose stack.

Docker does not run on every development computer, so these checks read the files.
The stack itself is tested by scripts/compose-smoke.sh in CI and on macOS.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy" / "compose"
LOCAL_KEY = "local-dev-batch-key-not-a-secret"


def _load(name: str) -> dict:
    return yaml.safe_load((COMPOSE / name).read_text(encoding="utf-8"))


def test_images_are_pinned():
    base, local = _load("compose.yaml"), _load("compose.local.yaml")
    assert base["services"]["collector"]["image"] == \
        "otel/opentelemetry-collector-contrib:0.161.0"
    assert local["services"]["postgres"]["image"] == "postgres:18.6-bookworm"
    for doc in (base, local):
        for service in doc["services"].values():
            assert not str(service.get("image", "")).endswith(":latest")


def test_base_file_has_no_local_settings():
    base = _load("compose.yaml")["services"]
    assert set(base) == {"backend", "collector"}
    for service in base.values():
        assert "build" not in service and "ports" not in service
    backend = base["backend"]
    env = backend["environment"]
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://collector:4318"
    assert env["OTEL_SERVICE_NAME"] == "model-monitor"
    assert "DATABASE_URL" not in env and "BATCH_API_KEY_SHA256" not in env
    assert backend["depends_on"] == {"collector": {"condition": "service_started"}}
    assert "/api/health" in " ".join(backend["healthcheck"]["test"])


def test_local_file_builds_backend_and_waits_for_postgres():
    local = _load("compose.local.yaml")["services"]
    backend = local["backend"]
    assert backend["build"] == "../../backend"
    assert backend["depends_on"]["postgres"] == {"condition": "service_healthy"}
    env = backend["environment"]
    assert env["DATABASE_URL"] == "postgresql://monitor:monitor@postgres:5432/monitor"
    expected = hashlib.sha256(LOCAL_KEY.encode()).hexdigest()
    assert env["BATCH_API_KEY_SHA256"] == f"GCP-UC-03:{expected}"
    assert "ports" not in local["postgres"]
    assert local["postgres"]["volumes"] == ["pgdata:/var/lib/postgresql"]


def test_published_ports_are_loopback_only():
    local = _load("compose.local.yaml")["services"]
    published = [port for service in local.values() for port in service.get("ports", [])]
    assert sorted(published) == ["127.0.0.1:4318:4318", "127.0.0.1:8000:8000"]


def test_collector_config_writes_spans_to_tmp_without_secrets():
    text = (COMPOSE / "otel-collector.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    assert config["receivers"]["otlp"]["protocols"] == {"http": {"endpoint": "0.0.0.0:4318"}}
    assert config["exporters"]["file"]["path"] == "/tmp/spans.jsonl"
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp"], "processors": ["batch"],
                      "exporters": ["debug", "file"]}
    for word in ("password", "token", "secret", "authorization"):
        assert word not in text.lower()


def test_no_plain_key_in_compose_files():
    for path in COMPOSE.glob("*.yaml"):
        assert LOCAL_KEY not in path.read_text(encoding="utf-8"), path.name
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `.venv/bin/python -m pytest -q tests/test_compose_files.py`
Expected: FAIL with `FileNotFoundError` for `deploy/compose/compose.yaml`.

- [ ] **Step 3: Create the files**

`deploy/compose/compose.yaml`:

```yaml
# Base services of the batch MVP stack (S1-06). The same on every host.
# Use with one environment file: compose.local.yaml (laptop and CI) or, with S1-04,
# compose.testhost.yaml. Run from this folder:
#   docker compose -f compose.yaml -f compose.local.yaml up --build --wait
name: model-monitor

services:
  backend:
    environment:
      OTEL_EXPORTER_OTLP_ENDPOINT: http://collector:4318
      OTEL_SERVICE_NAME: model-monitor
      LOG_FORMAT: json
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"
      interval: 5s
      timeout: 5s
      retries: 12
      start_period: 20s
    depends_on:
      collector:
        condition: service_started
    restart: unless-stopped

  collector:
    image: otel/opentelemetry-collector-contrib:0.161.0
    command: ["--config=/etc/otelcol/config.yaml"]
    volumes:
      - ./otel-collector.yaml:/etc/otelcol/config.yaml:ro
    # No Docker health check: the image has no shell. A Collector problem never stops
    # the backend (S1-05); the smoke test checks the span file instead.
    restart: unless-stopped
```

`deploy/compose/compose.local.yaml`:

```yaml
# Laptop and CI settings (S1-06). Never use this file on the test host.
# The PostgreSQL password and the API key are local test values, not secrets:
# the key is "local-dev-batch-key-not-a-secret"; only its SHA-256 is here.
services:
  postgres:
    image: postgres:18.6-bookworm
    environment:
      POSTGRES_USER: monitor
      POSTGRES_PASSWORD: monitor
      POSTGRES_DB: monitor
    volumes:
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "monitor", "-d", "monitor"]
      interval: 2s
      timeout: 5s
      retries: 30
    restart: unless-stopped

  backend:
    build: ../../backend
    image: model-monitor-backend:local
    environment:
      DATABASE_URL: postgresql://monitor:monitor@postgres:5432/monitor
      BATCH_API_KEY_SHA256: GCP-UC-03:ca9263478834f0d9f054e84eda1a55dee86d8a6551f27aa8a2c751a4b541b200
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"

  collector:
    ports:
      - "127.0.0.1:4318:4318"

volumes:
  pgdata:
```

`deploy/compose/otel-collector.yaml`:

```yaml
# OTel Collector for the batch MVP (S1-06). Receives OTLP/HTTP and writes the spans to
# the log and to /tmp/spans.jsonl in the container (read it with `docker compose cp`).
# The file output is temporary: S2-03 adds the export to Langfuse. S3-03 adds the memory
# limit and the attribute filter. This file contains no credential.
extensions:
  health_check:
    endpoint: 0.0.0.0:13133

receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch: {}

exporters:
  debug:
    verbosity: basic
  file:
    path: /tmp/spans.jsonl

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, file]
```

- [ ] **Step 4: Run the test to make sure it passes**

Run: `.venv/bin/python -m pytest -q tests/test_compose_files.py`
Expected: 6 passed.

If Docker with Compose v2 is available on the host, also run from `deploy/compose/`:
`docker compose -f compose.yaml -f compose.local.yaml config --quiet` — expected: no output, exit 0. If Docker is not available, record "not run: no Docker".

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_compose_files.py deploy/compose/compose.yaml deploy/compose/compose.local.yaml deploy/compose/otel-collector.yaml
git commit -m "feat(s1-06): local Compose stack with the OTel Collector"
```

---

### Task 2: Smoke test script and CI workflow

**Files:**
- Modify: `backend/tests/test_compose_files.py` (append tests)
- Create: `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml`

**Interfaces:**
- Consumes: the files of Task 1.
- Produces: `bash scripts/compose-smoke.sh` (exit 0 = pass; `KEEP=1` keeps the stack).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_compose_files.py`:

```python
SMOKE = ROOT / "scripts" / "compose-smoke.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "compose-smoke.yml"


def test_smoke_script_cleans_up_and_fails_fast():
    text = SMOKE.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "trap cleanup EXIT" in text and "down -v" in text
    assert 'KEEP:-0' in text
    assert "--wait" in text and "/api/readiness" in text
    assert "monitor.ingest" in text and "docker compose" in text and " cp " in text
    assert "SMOKE PASS" in text and "SMOKE FAIL" in text
    # the key is sent only in the Authorization header, never echoed
    key_lines = [line for line in text.splitlines() if "KEY" in line and "echo" in line]
    assert key_lines == []
    assert "\r\n" not in text                       # LF line endings for bash


def test_ci_workflow_paths():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow[True]                       # PyYAML reads the key `on` as True
    paths = {"deploy/compose/**", "backend/**", "scripts/compose-smoke.sh",
             ".github/workflows/compose-smoke.yml"}
    assert set(triggers["pull_request"]["paths"]) == paths
    assert set(triggers["push"]["paths"]) == paths
    assert triggers["push"]["branches"] == ["dev"]
    job = workflow["jobs"]["smoke"]
    assert job["runs-on"] == "ubuntu-latest" and job["timeout-minutes"] == 15
    assert workflow["permissions"] == {"contents": "read"}
    assert any(step.get("run") == "bash scripts/compose-smoke.sh" for step in job["steps"])
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `.venv/bin/python -m pytest -q tests/test_compose_files.py`
Expected: 2 failed (`FileNotFoundError` for the script and the workflow), 6 passed.

- [ ] **Step 3: Create the script and the workflow**

`scripts/compose-smoke.sh` (LF line endings):

```bash
#!/usr/bin/env bash
# Smoke test of the local Compose stack (S1-06). macOS and Linux.
# Starts backend + PostgreSQL + OTel Collector, stores one batch run with a known
# traceparent, and checks the row and the monitor.ingest span in the Collector file.
# KEEP=1 keeps the stack running afterwards. Needs: docker (Compose v2), curl, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/deploy/compose"
COMPOSE=(docker compose -f compose.yaml -f compose.local.yaml)
BASE_URL="http://127.0.0.1:8000"
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
EXAMPLE="$ROOT/changes/2026-10-02-batch-monitoring-mvp/schema/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "SMOKE FAIL: $STEP"
    "${COMPOSE[@]}" logs --no-color --tail 200 backend collector || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

STEP="compose up"
"${COMPOSE[@]}" up --build --wait --wait-timeout 300

STEP="readiness"
curl -fsS "$BASE_URL/api/readiness" >/dev/null

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

STEP="POST /api/batch/runs"
STATUS="$(curl -sS -o "$WORK/response.json" -w '%{http_code}' -X POST "$BASE_URL/api/batch/runs" \
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

STEP="monitor.ingest span in the Collector file"
for _ in $(seq 1 15); do
  if "${COMPOSE[@]}" cp collector:/tmp/spans.jsonl "$WORK/spans.jsonl" >/dev/null 2>&1 &&
     python3 - "$WORK/spans.jsonl" "$TRACE_ID" <<'PY'
import json, sys
found = False
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    for resource in json.loads(line).get("resourceSpans", []):
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                if span.get("name") == "monitor.ingest" and \
                        span.get("traceId", "").lower() == sys.argv[2]:
                    found = True
sys.exit(0 if found else 1)
PY
  then
    echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
    exit 0
  fi
  sleep 2
done
exit 1
```

Make it executable in git: `git update-index --chmod=+x scripts/compose-smoke.sh` (after `git add`).

`.github/workflows/compose-smoke.yml`:

```yaml
name: Compose smoke test

on:
  pull_request:
    paths:
      - "deploy/compose/**"
      - "backend/**"
      - "scripts/compose-smoke.sh"
      - ".github/workflows/compose-smoke.yml"
  push:
    branches: [dev]
    paths:
      - "deploy/compose/**"
      - "backend/**"
      - "scripts/compose-smoke.sh"
      - ".github/workflows/compose-smoke.yml"

permissions:
  contents: read

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - run: bash scripts/compose-smoke.sh
```

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `.venv/bin/python -m pytest -q tests/test_compose_files.py`
Expected: 8 passed.

If `bash` is available on the host, run `bash -n scripts/compose-smoke.sh` — expected: no output (TESTING.md: deployment scripts get `bash -n`). If Docker with Compose v2 is available, run `bash scripts/compose-smoke.sh` — expected: `SMOKE PASS`. Otherwise record "not run: no Docker" and "not run: no bash" as they apply.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_compose_files.py scripts/compose-smoke.sh .github/workflows/compose-smoke.yml
git update-index --chmod=+x scripts/compose-smoke.sh
git commit -m "test(s1-06): Compose smoke test script and CI workflow"
```

---

### Task 3: Docs and plan text

**Files:**
- Create: `deploy/compose/README.md`
- Modify: `TESTING.md`, `README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md`

- [ ] **Step 1: Write `deploy/compose/README.md`**

```markdown
# Local stack: backend, PostgreSQL and OTel Collector

The batch MVP stack on a laptop (S1-06): the backend (`backend/Dockerfile`), PostgreSQL
18.6 and the OTel Collector 0.161.0. It runs on macOS (Apple Silicon or Intel) and Linux.

## Prerequisites

- Docker Desktop 4.x (macOS) or Docker Engine with Compose v2 (Linux):
  `docker compose version` must work.
- `curl` and `python3` (macOS has both).
- Ports 8000 and 4318 free on `127.0.0.1`.

## Run the smoke test

From the repository root:

```bash
bash scripts/compose-smoke.sh
```

Expected last line: `SMOKE PASS: run smoke-..., trace <32 hex>`. The script starts the
stack, stores one batch run with a known `traceparent`, checks the `batch_runs` row and the
`monitor.ingest` span in the Collector file, then removes the stack and its volume.

To keep the stack running after the test:

```bash
KEEP=1 bash scripts/compose-smoke.sh
```

## Use the stack by hand

Start it, from `deploy/compose/`:

```bash
docker compose -f compose.yaml -f compose.local.yaml up --build --wait
```

Check it:

```bash
curl -s http://127.0.0.1:8000/api/readiness
```

Send one run (the local test key is `local-dev-batch-key-not-a-secret`, use case
`GCP-UC-03`; it is not a secret):

```bash
curl -s -X POST http://127.0.0.1:8000/api/batch/runs -H "Authorization: Bearer local-dev-batch-key-not-a-secret" -H "Content-Type: application/json" -H "traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" --data-binary @../../changes/2026-10-02-batch-monitoring-mvp/schema/examples/valid/04-identity-only.json
```

Send test spans to the Collector (needs `telemetrygen`):

```bash
telemetrygen traces --otlp-http --otlp-insecure --otlp-endpoint 127.0.0.1:4318 --traces 3
```

Read the spans:

```bash
docker compose -f compose.yaml -f compose.local.yaml cp collector:/tmp/spans.jsonl ./spans.jsonl
```

Read the database:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec postgres psql -U monitor -d monitor -c "select run_id, trace_id, trace_id_source from batch_runs"
```

Stop it and remove the data:

```bash
docker compose -f compose.yaml -f compose.local.yaml down -v
```

## If a port is in use

If port 8000 or 4318 is in use, stop the other program, or change the left side of the
port in `compose.local.yaml` (for example `127.0.0.1:18000:8000`) for your own run only.
Do not commit that change: the smoke test uses port 8000.

## What this stack is not

- Not the test host: the front door on port 443, the OTLP token, Cloud SQL and the
  Artifact Registry image come with S1-04 (`compose.testhost.yaml`).
- The span file in `/tmp` is lost when the Collector container is removed. S2-03 sends the
  spans to Langfuse.
```

(Inside the Markdown file the code fences are normal three-backtick fences.)

- [ ] **Step 2: Change the other docs**

`TESTING.md`:
- In "Required checks", after the backend code block, add:

```markdown
Local stack (S1-06), run from the repository root on macOS or Linux with Docker:

```bash
bash scripts/compose-smoke.sh   # expected last line: SMOKE PASS
```

`.github/workflows/compose-smoke.yml` runs it in CI. On a Windows host without Docker,
report it as unavailable; `backend/tests/test_compose_files.py` checks the files statically.
```

- Replace the sentence "CI runs the full backend suite, slow tests included, against PostgreSQL 16 in `.github/workflows/backend-live.yml` and also validates the strict-live configuration with CI placeholder URLs and tokens." with: "CI runs the full backend suite, slow tests included, against PostgreSQL 18.6 in `.github/workflows/backend-live.yml` and validates the batch MVP configuration (`config.batch_configuration_errors()`)."

`README.md`: in the "Development" table, add a row after "Integration tests":

```markdown
| Local stack | `bash scripts/compose-smoke.sh` (repo root; macOS/Linux with Docker; see [deploy/compose/README.md](../../deploy/compose/README.md)) | `SMOKE PASS`; CI: `compose-smoke.yml` |
```

`changes/2026-10-02-batch-monitoring-mvp/issues.md`, section `### S1-06`:
- After the paragraph that ends "The Langfuse export comes in S2-03.", add:

```markdown
**Local part (done in `changes/2026-10-07-s1-06-local-compose/`):** `deploy/compose/compose.yaml`
(base), `compose.local.yaml`, `otel-collector.yaml`, `scripts/compose-smoke.sh` and
`.github/workflows/compose-smoke.yml`. The file output is `/tmp/spans.jsonl` in the
Collector container (the Collector runs as uid 10001 and cannot write to a new volume);
read it with `docker compose cp`. The test host adds `compose.testhost.yaml` (S1-04).
```

`CHANGELOG.md`, under `## [Unreleased]`, add an `### Added` section above `### Changed` if none exists, with:

```markdown
- A local Docker Compose stack (`deploy/compose/`): the backend, PostgreSQL 18.6 and the
  OTel Collector 0.161.0, with a smoke test (`scripts/compose-smoke.sh`) that runs in CI
  (`compose-smoke.yml`) and on macOS (S1-06).
```

`DEVLOG.md`: add at the top of `## Work log`:

```markdown
### 2026-10-07 — S1-06 local part: Docker Compose stack and smoke test

- Changed: `deploy/compose/` (base and local Compose files, Collector configuration,
  README), `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml`,
  `backend/tests/test_compose_files.py`. Decisions with the project owner: CI smoke test
  plus a hand test on a Mac; base file plus one file for each environment; the Collector
  file in `/tmp`; loopback-only ports. Change package `changes/2026-10-07-s1-06-local-compose/`.
- Evidence: <test_compose_files result>; <fast suite result>; `tests/test_docs.py`
  <result>. Not run here (no Docker on the Windows host): the stack, `docker compose
  config`, the smoke test. CI runs the smoke test on the pull request; the project owner
  runs it on a Mac.
- Remaining: the test-host part of S1-06 (front door, OTLP token,
  `compose.testhost.yaml`) with S1-04. S1-07 can now read the Collector file.
```

- [ ] **Step 3: Run every check that the host allows**

Run: `.venv/bin/python -m pytest -q tests/test_compose_files.py tests/test_docs.py` — expected: 13 passed.
Run: `.venv/bin/python -m pytest -q -m "not slow"` — expected: all passed, 9 deselected.
Put the results in the DEVLOG entry instead of the `<...>` text.

- [ ] **Step 4: Commit**

```bash
git add deploy/compose/README.md TESTING.md README.md changes/2026-10-02-batch-monitoring-mvp/issues.md CHANGELOG.md DEVLOG.md
git commit -m "docs(s1-06): run the local stack on a Mac; S1-06 plan text"
```

Do not push and do not open a pull request; the reviewer does that.
