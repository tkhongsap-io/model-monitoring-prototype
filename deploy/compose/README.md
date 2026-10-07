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
