# Spec: local Docker Compose stack with the OTel Collector (S1-06, local part)

## Files

| File | Purpose |
|---|---|
| `deploy/compose/compose.yaml` | Base: `backend` and `collector`, the same on every host |
| `deploy/compose/compose.local.yaml` | Laptop and CI: `postgres`, the backend build, local ports and settings |
| `deploy/compose/otel-collector.yaml` | Collector configuration |
| `deploy/compose/README.md` | How to run the stack on a Mac (and Linux) |
| `scripts/compose-smoke.sh` | The smoke test (bash; macOS and Linux) |
| `.github/workflows/compose-smoke.yml` | Runs the smoke test in CI |

Run every command from `deploy/compose/`:
`docker compose -f compose.yaml -f compose.local.yaml <command>`.

## Base: `compose.yaml`

`backend`:
- `environment`: `OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4318`,
  `OTEL_SERVICE_NAME=model-monitor`, `LOG_FORMAT=json`. `DATABASE_URL` and
  `BATCH_API_KEY_SHA256` come from the environment file of each host (the local file sets
  them directly).
- `healthcheck`: `python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"`;
  interval 5 s, timeout 5 s, retries 12, start period 20 s.
- `depends_on: collector` with `condition: service_started`.
- `restart: unless-stopped`.

`collector`:
- `image: otel/opentelemetry-collector-contrib:0.161.0` (fixed-versions table).
- `command: ["--config=/etc/otelcol/config.yaml"]`; `volumes`:
  `./otel-collector.yaml:/etc/otelcol/config.yaml:ro` and `collector-data:/data`.
- `depends_on: collector-init` with `condition: service_completed_successfully`.
- No Docker health check (the image has no shell). `restart: unless-stopped`. No `user`
  setting: the Collector stays uid 10001.

`collector-init` (added 2026-10-07 after the first CI run; the distroless image has no
`/tmp`):
- `image: busybox:1.37.0` (fixed-versions table); `command: ["chown", "-R", "10001:10001", "/data"]`;
  `volumes: collector-data:/data`; `restart: "no"`.

Named volume `collector-data` in the base file.

## Local: `compose.local.yaml`

`postgres`:
- `image: postgres:18.6-bookworm`; `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB`
  are `monitor` (local only).
- Named volume `pgdata` at `/var/lib/postgresql` (PostgreSQL 18 images keep the data
  under a version subfolder there).
- `healthcheck`: `pg_isready -U monitor -d monitor`; interval 2 s, retries 30.
- No published port.

`backend`:
- `build: ../../backend` (the S1-13 app from `backend/Dockerfile`), `image: model-monitor-backend:local`.
- `environment`: `DATABASE_URL=postgresql://monitor:monitor@postgres:5432/monitor`;
  `BATCH_API_KEY_SHA256=GCP-UC-03:<sha256 of local-dev-batch-key-not-a-secret>`.
- `depends_on: postgres` with `condition: service_healthy` (added to the base dependency).
- `ports: ["127.0.0.1:8000:8000"]`.

`collector`:
- `ports: ["127.0.0.1:4318:4318"]` (for `telemetrygen` on the laptop).

## Collector: `otel-collector.yaml`

```yaml
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
    path: /data/spans.jsonl
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug, file]
```

No gRPC receiver. No memory limiter or attribute filter (S3-03). No secret in the file.

## Smoke test: `scripts/compose-smoke.sh`

Bash with `set -euo pipefail`. Needs `docker` (Compose v2), `curl`, `python3`.

1. `cd deploy/compose`; `docker compose -f compose.yaml -f compose.local.yaml up --build --wait --wait-timeout 300`.
2. `GET http://127.0.0.1:8000/api/readiness` must return `200`.
3. Make a random 32-hex trace ID and 16-hex parent ID; a unique `run_id`
   (`smoke-<UTC timestamp>-<random>`). Read
   `changes/2026-10-02-batch-monitoring-mvp/schema/examples/valid/04-identity-only.json`,
   set its `run_id`, and send it to `POST /api/batch/runs` with
   `Authorization: Bearer local-dev-batch-key-not-a-secret` and
   `traceparent: 00-<trace>-<parent>-01`. Expect `201` and `trace_id` = the sent trace ID.
4. `docker compose exec -T postgres psql -U monitor -d monitor -tAc "select trace_id, trace_id_source from batch_runs where run_id = '<run_id>'"`
   must return `<trace>|traceparent`.
5. For up to 30 s, every 2 s: `docker compose cp collector:/data/spans.jsonl <tmp file>`
   and look for a span named `monitor.ingest` whose trace ID is the sent trace ID (the
   file holds OTLP JSON; trace IDs are hex strings).
6. Print `SMOKE PASS` and exit `0`. On a failure: print `SMOKE FAIL: <step>`, the last
   200 lines of the `backend` and `collector` logs, and exit `1`.
7. A `trap` runs `docker compose ... down -v` on exit, unless `KEEP=1`.

The script never prints the key or the body.

## CI: `.github/workflows/compose-smoke.yml`

- `on`: `pull_request` and `push` to `dev` with `paths` `deploy/compose/**`,
  `backend/**`, `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml`.
- One job on `ubuntu-latest`, `timeout-minutes: 15`, `permissions: contents: read`.
- Steps: checkout; `bash scripts/compose-smoke.sh`. No secrets.

## Docs

- `deploy/compose/README.md`: prerequisites (Docker Desktop for Apple Silicon or Intel),
  the commands (up, smoke test, `KEEP=1`, a `curl` example with the test key, `telemetrygen`,
  read the spans with `docker compose cp`, `down -v`), and what to do when port 8000 or
  4318 is in use.
- `TESTING.md`: the smoke test command; "CI, macOS and Linux; not on a Windows host
  without Docker".
- `README.md`: one line that links `deploy/compose/README.md`.
- `issues.md`, S1-06: the local acceptance criteria name these files; record the
  `collector-data` volume decision. GitHub issue #8 gets the same text.
- `CHANGELOG.md`, `DEVLOG.md`.

## Acceptance (local part of S1-06)

- `docker compose up` starts the Collector; the backend starts after PostgreSQL is
  healthy (the Collector has no Docker health check; see the decision in `intent.md`).
- The Collector image is `0.161.0`, not `latest`.
- Spans that come in on OTLP/HTTP appear in the file output (smoke test step 5).
- The Collector configuration is in the repository and contains no secrets.

## Not tested here

The Windows development computer has no Docker engine and no Compose plugin: the stack
is tested only by CI and on the Mac. The test-host criteria of S1-06 stay open (S1-04).
