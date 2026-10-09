# Spec: trace check tool (S1-07)

Intent and decisions: `intent.md` in this folder.

## Files

| File | Change |
|---|---|
| `backend/app/trace_check.py` | New. The pure check logic: no I/O, no database, no file access |
| `backend/scripts/check_trace.py` | New. Arguments, span file, database, output, exit code |
| `backend/app/db.py` | Small refactor: a public `driver_url(url)` that `engine()` and the tool both use (the `postgres://` and `postgresql://` → `postgresql+psycopg://` rule). No behaviour change. |
| `deploy/compose/compose.yaml` | New service `trace-check` |
| `deploy/compose/compose.local.yaml` | `trace-check`: local image and local `CHECK_DATABASE_URL` |
| `deploy/compose/compose.testhost.yaml` | `trace-check`: `BACKEND_IMAGE`, `check.env`, CA file |
| `deploy/compose/check-trace.sh` | New wrapper |
| `deploy/compose/make-check-env.sh` | New. Test host only: writes `/opt/model-monitor/check.env` |
| `deploy/compose/check.env.example` | New. Names only |
| `scripts/compose-smoke.sh` | Uses the wrapper instead of the inline span check |
| `deploy/compose/TESTHOST.md`, `deploy/compose/README.md` | How to run the tool |
| `backend/tests/test_trace_check.py`, `backend/tests/test_check_trace_script.py`, `backend/tests/test_compose_files.py` | Tests |
| `changes/2026-10-02-batch-monitoring-mvp/issues.md` (S1-07), `DEVLOG.md`, `CHANGELOG.md` | Documentation |

No new package. The tool uses SQLAlchemy and psycopg, which the backend already has.

## Command line

```
check_trace.py <trace_id> [--backend-only] [--wait SECONDS] [--spans-file PATH]
```

| Argument | Rule |
|---|---|
| `trace_id` | Exactly 32 hex characters, not all zeros. Upper case is accepted and changed to lower case. Anything else: exit `2`. |
| `--backend-only` | Check only the run row and the monitor span. The GCP root span and the ancestor link show `skipped`. |
| `--wait SECONDS` | Integer, `0` or more, default `0`. If an item is missing, read the database and the file again every 2 seconds until all checked items are found or the time is over. Print only the final result. |
| `--spans-file PATH` | Default `/otel/spans.jsonl` (the mount in the `trace-check` service). For tests. |

Environment: `CHECK_DATABASE_URL` only. The tool never reads `DATABASE_URL` and never
calls `db.engine()` (that function runs the migrations).

## Database access (in the script)

- `create_engine(db.driver_url(CHECK_DATABASE_URL), future=True)`. For PostgreSQL, add
  `connect_args={"options": "-c default_transaction_read_only=on"}`.
- One query, through the `db.batch_runs` table object:
  `SELECT use_case_id, run_id, status, completed_at, received_at, trace_id_source FROM batch_runs WHERE trace_id = :t`.
  It never selects `payload`.
- For a duplicate (see below) a second query with the same columns for the stored trace ID.
- Any SQLAlchemy error: print `error: cannot read the database (<ExceptionClassName>)` to
  stderr and exit `2`. Never print the URL, the exception message, or a traceback.

## Span file (in the script)

The Collector file exporter writes one OTLP JSON object per line:
`resourceSpans[].scopeSpans[].spans[]`. Each span has `traceId`, `spanId`,
`parentSpanId` (empty or missing for a root span), `name`, `startTimeUnixNano` (a string),
and `attributes: [{"key": ..., "value": {"stringValue" | "intValue" | ...: ...}}]`.

- If the file does not exist or cannot be read: `error: span file <path> not found` on
  stderr, exit `2`.
- Read the file line by line. Keep only the spans whose `traceId` (lower case) is the
  trace ID. Do not keep other spans in memory.
- A line that is not valid JSON, or that has the wrong shape, is skipped and counted.
- The script gives the check logic a list of `Span` values:
  `trace_id, span_id, parent_span_id, name, start_ns, attributes` (a dict of the simple
  attribute values: string, int, bool, double).

## Check logic (`app/trace_check.py`)

```python
@dataclass(frozen=True)
class Span: trace_id: str; span_id: str; parent_span_id: str; name: str; start_ns: int; attributes: dict

@dataclass(frozen=True)
class RunRow: use_case_id: str; run_id: str; status: str; completed_at: str; received_at: float; trace_id_source: str

@dataclass(frozen=True)
class Item: name: str; state: str; detail: str      # state: "found" | "missing" | "skipped"

@dataclass(frozen=True)
class Result: trace_id: str; items: list[Item]; skipped_lines: int
    # ok: no item is "missing"

def check(trace_id, rows, spans, *, backend_only, stored_rows=None, skipped_lines=0) -> Result
def stored_trace_ids(spans) -> list[str]          # the stored_trace_id of duplicate monitor.ingest spans
def render(result) -> str                          # the text below
```

The items, always in this order:

1. **run row**
   - At least one row has this trace ID → `found`. The detail is
     `<use_case_id> / <run_id>, status <status>, received <ISO UTC>, trace_id_source <source>`.
     If there are more rows, show each one.
   - No row, and a `monitor.ingest` span in this trace has `outcome=duplicate` and a
     `stored_trace_id`, and `stored_rows` has a row for that trace ID → `found`,
     detail `duplicate delivery; the run is stored under trace <id>`.
   - The same, but `stored_rows` has no row → `missing`,
     detail `duplicate delivery, but trace <id> has no run row`.
   - No row, and a `monitor.ingest` span has `outcome=conflict` → `missing`,
     detail `rejected: another body is stored for this run_id under trace <stored_trace_id>`
     (without the `under trace` part if the attribute is absent).
   - No row, and a `monitor.ingest` span has `outcome=stored` → `missing`,
     detail `monitor.ingest says stored, but no run row has this trace ID` (for example,
     the tool reads another database).
   - No row, and a `monitor.ingest` span has another outcome → `missing`,
     detail `the backend did not store the run (outcome <outcome>)`.
   - Else → `missing`, no detail.
2. **monitor span** — at least one span `monitor.ingest` → `found`. The detail lists, for
   each one in time order, `outcome <outcome>, <ISO UTC start>`. Else `missing`.
3. **gcp root span** — `skipped` with `--backend-only`. Else: at least one span `batch.run`
   → `found`, detail its `use_case_id` and `run_id` attributes when present and the start
   time. Else `missing`.
4. **ancestor link** — `skipped` with `--backend-only`. Else, for each `monitor.ingest`
   span: follow `parent_span_id` through the spans of this trace. If a span named
   `batch.send` is reached → `found`, detail the path of span names, for example
   `monitor.ingest → POST /api/batch/runs → POST → batch.send`. Stop on a loop. If no chain
   reaches `batch.send` → `missing`, detail of the first `monitor.ingest` chain:
   `the chain stops at <name>: parent <id> is not in the file`, or
   `the chain stops at <name>: it has no parent`. If there is no `monitor.ingest` span →
   `missing`, detail `no monitor.ingest span`.

Times: `received_at` (seconds) and `start_ns` (nanoseconds) are shown as
`YYYY-MM-DDTHH:MM:SSZ` in UTC.

The tool prints only IDs, names, outcomes, status values and times. It never prints other
span attributes or any body content.

## Output and exit codes

```
trace 4bf92f3577b34da6a3ce929d0e0e4736
run row        found    rtr-fraud-validation / run-20261008-01, status succeeded, received 2026-10-08T07:00:03Z, trace_id_source traceparent
monitor span   found    outcome stored, 2026-10-08T07:00:03Z
gcp root span  skipped
ancestor link  skipped
RESULT: OK (2 of 2 found)
```

- The last line is `RESULT: OK (<n> of <m> found)` or `RESULT: MISSING (<n> of <m> found)`;
  `m` counts the checked items, not the skipped ones.
- If lines were skipped, print `note: <k> span file line(s) could not be read` before the
  result line.
- Exit `0`: no checked item is missing. Exit `1`: an item is missing. Exit `2`: a usage or
  setup error (argparse errors, a bad trace ID, no `CHECK_DATABASE_URL`, a database error,
  no span file). An exit-`2` error prints one line on stderr and no result.

## Compose

`compose.yaml` (base):

```yaml
  trace-check:
    profiles: ["tools"]
    entrypoint: ["python", "scripts/check_trace.py"]
    volumes:
      - collector-data:/otel:ro
    restart: "no"
```

No `ports`, no `depends_on`, no `environment` in the base. The working folder of the image
is `/srv/backend`; the user is `appuser` (uid 10001), the same uid as the Collector that
writes the file.

`compose.local.yaml`:

```yaml
  trace-check:
    image: model-monitor-backend:local
    environment:
      CHECK_DATABASE_URL: postgresql://monitor:monitor@postgres:5432/monitor   # local test value
```

`compose.testhost.yaml`:

```yaml
  trace-check:
    image: ${BACKEND_IMAGE:?BACKEND_IMAGE is not set}
    env_file:
      - /opt/model-monitor/check.env
    volumes:
      - /opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro
```

## Wrapper: `deploy/compose/check-trace.sh`

```
check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]
```

- `#!/usr/bin/env bash`, `set -euo pipefail`, `cd "$(dirname "$0")"`.
- If `/opt/model-monitor/check.env` exists: the files are `compose.yaml` and
  `compose.testhost.yaml`. Else: `compose.yaml` and `compose.local.yaml`.
- Runs `docker compose -f ... -f ... --profile tools run --rm -T --no-deps trace-check "$@"`
  and exits with its exit code.
- On the test host it runs with `sudo` (Docker needs root there). The documented SSH line:
  `gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "sudo /opt/model-monitor/compose/check-trace.sh <trace_id> --backend-only"`.

## Test host setup: `deploy/compose/make-check-env.sh`

- `#!/usr/bin/env bash`, `set -euo pipefail`; must run as root (else exit `1` with a message).
- Reads `/opt/model-monitor/secrets/monitor-readonly.password` (S1-11). If it is missing
  or empty: exit `1` with a message.
- Writes `/opt/model-monitor/check.env` with `umask 077`, then `chmod 600` and owner root:
  `CHECK_DATABASE_URL=postgresql://monitor_readonly:<pw>@10.188.112.8:5432/monitor?sslmode=verify-ca&sslrootcert=/etc/model-monitor/cloudsql-server-ca.pem`.
  The password is URL-safe (S1-11 makes it with `token_urlsafe` plus `Kq7-`), so it needs
  no encoding.
- Prints only `stat -c '%a %U %n'` of the file and `CHECK ENV DONE`. Never prints or
  echoes the password.

`check.env.example` contains the line with `<password>` and a comment; no value.

## CI smoke test

In `scripts/compose-smoke.sh`, replace the step "monitor.ingest span in the Collector
file" (the `docker compose cp` loop and the inline Python) with:

```bash
STEP="check-trace"
bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --backend-only --wait 30
echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
```

The step "batch_runs row" (with `psql`) stays as an independent check.

## Tests

1. `tests/test_trace_check.py` (pure logic, fixture spans):
   - all four found, with the path of names in the ancestor detail;
   - each item missing alone;
   - duplicate: found when `stored_rows` has the row, missing when it has not;
   - conflict: missing, with and without `stored_trace_id`;
   - another outcome (for example `invalid`): missing with the outcome;
   - chain stops at a missing parent, chain stops at a span with no parent, a loop does not hang;
   - two `monitor.ingest` spans (a retry), one chain reaches `batch.send` → found;
   - `--backend-only`: two items `skipped`, `m` is 2;
   - `render`: the result line, the skipped-lines note, no attribute other than the allowed ones.
2. `tests/test_check_trace_script.py` (the script with a temporary span file and a SQLite
   database made with `db.metadata`, `CHECK_DATABASE_URL` set with `monkeypatch`):
   - exit `0`, `1` and `2` cases; bad trace IDs (31 characters, not hex, all zeros);
   - no `CHECK_DATABASE_URL` → `2`; `DATABASE_URL` set but no `CHECK_DATABASE_URL` → `2`;
   - no span file → `2`; broken lines are skipped and counted;
   - a database URL with a password: the password does not appear in stdout or stderr,
     also when the connection fails;
   - `--wait`: a span that is added to the file during the wait is found (use a short wait
     and a patched sleep, or a thread that appends the line).
3. `tests/test_compose_files.py`:
   - `trace-check` has the profile `tools`, mounts `collector-data` at `/otel` read-only,
     and has no `ports`;
   - the local file gives it `model-monitor-backend:local`; the test-host file gives it
     `BACKEND_IMAGE`, `check.env` and the CA file read-only;
   - `check.env.example` contains no password value;
   - the shell scripts start with `#!/usr/bin/env bash` and have `set -euo pipefail`;
     `make-check-env.sh` never echoes the password.
4. CI: `compose-smoke.yml` passes with the new step.
5. By hand on the test host after the merge and the next image: run `make-check-env.sh`
   once; send one request with a known `traceparent`; the tool with `--backend-only`
   exits `0`; a random trace ID exits `1`.

## Not in scope

Langfuse (S2-03), a JSON output mode, the full four-item test with a real GCP job (S1-10),
and the test-host front door (S1-06).
