# Local stack: backend, PostgreSQL and OTel Collector

The batch MVP stack on a laptop (S1-06): the backend (`backend/Dockerfile`), PostgreSQL
17.11 and the OTel Collector 0.161.0. It runs on macOS (Apple Silicon or Intel) and Linux.

## Prerequisites

- Docker Desktop 4.x (macOS) or Docker Engine with Compose v2 (Linux):
  `docker compose version` must work.
- `curl` and `python3` (macOS has both).
- Ports 8000, 8080 and 4318 free on `127.0.0.1`.

## Run the smoke test

From the repository root:

```bash
bash scripts/compose-smoke.sh
```

Expected last line: `SMOKE PASS: run smoke-..., trace <32 hex>`. The script starts the
monitor and nginx stacks, checks routes and the OTLP token, stores one batch run with a
known `traceparent`, sends fake-job spans and checks all four trace items, then removes
the stacks, the monitor volume and the edge network if this run created it.

To keep the stack running after the test:

```bash
KEEP=1 bash scripts/compose-smoke.sh
```

## nginx front door (S1-06)

The smoke test starts the external network `edge` and nginx itself. To run them by hand,
see [deploy/nginx/README.md](../nginx/README.md); create `edge` before starting the monitor.
Through nginx the local URL is `http://127.0.0.1:8080`. The local OTLP token is
`local-dev-otlp-token-not-a-secret` (a local test value).

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
docker compose -f compose.yaml -f compose.local.yaml cp collector:/data/spans.jsonl ./spans.jsonl
```

Read the database:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec postgres psql -U monitor -d monitor -c "select run_id, trace_id, trace_id_source from batch_runs"
```

Stop it and remove the data:

```bash
docker compose -f compose.yaml -f compose.local.yaml down -v
```

## Check a trace (S1-07)

After starting the stack with `up`, run from the repository root:

```bash
bash deploy/compose/check-trace.sh <trace_id> --backend-only
```

Use `--wait SECONDS` to wait for spans to arrive. Without `--backend-only`, the tool
also checks the GCP `batch.run` span and the ancestor link to `batch.send`.
Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
The smoke test uses this tool with `--wait 30`, checking the full fake-job trace.

## After the change from PostgreSQL 18 to 17 (2026-10-08)

If you kept a stack running with `KEEP=1` before this change, remove its volume one time,
because PostgreSQL 17 cannot read PostgreSQL 18 data:

```bash
docker compose -f compose.yaml -f compose.local.yaml down -v
```

The smoke test always removes its volume, so a normal smoke test run needs no step.

## If a port is in use

If port 8000 or 4318 is in use, stop the other program, or change the left side of the
port in `compose.local.yaml` (for example `127.0.0.1:18000:8000`) for your own run only.
Do not commit that change: the smoke test uses port 8000.

## What this stack is not

- The test host uses nginx on port 80, a secret OTLP token, Cloud SQL and the
  Artifact Registry image (`compose.testhost.yaml`); see `TESTHOST.md`.
- The span file `/data/spans.jsonl` is in the named volume `collector-data`. It stays when
  the Collector restarts, and `down -v` removes it. The span file grows without a limit; it
  is temporary until S2-03 sends the spans to Langfuse.
