# Spec: batch evaluator with the core metrics (S2-05)

Intent: [intent.md](intent.md). Issue: S2-05 (#19). Bands:
[core-metrics.md](../2026-10-08-batch-metric-profiles/core-metrics.md), section 1 (RAI
approved, bands version `core-2026-10-12`).

## Files

| File | Change |
|---|---|
| `backend/requirements.txt` | Add `uuid-utils>=1.0,<2` (approved 2026-10-14) |
| `backend/app/ids.py` | New. `new_id(at: float \| None = None) -> str`: a uuid7 string. |
| `backend/app/engines/batch_grading.py` | New, pure. Metrics, bands, reasons, grades. |
| `backend/app/adapters/langfuse_scores.py` | New. Sends the scores of one evaluation. |
| `backend/app/batch_evaluator.py` | New runner. The loop with the lease. |
| `backend/app/db.py` | Table `batch_evaluations`; migrations 9 and 10; store functions; `put_batch_run` uses `ids.new_id()` |
| `backend/app/registry.py` | A non-empty `band_overrides` is a load error |
| `backend/app/config.py` | Evaluator settings |
| `backend/app/main.py` | The lifespan starts and stops the loop |
| `backend/app/api/ops_routes.py` | Readiness gets `batch_evaluator` |
| `deploy/compose/compose.local.yaml` | Backend Langfuse settings, set only by `langfuse-smoke` |
| `deploy/compose/add-langfuse-backend-env.sh` | New. Test host: copies the Langfuse keys into `backend.env` |
| `scripts/compose-smoke.sh`, `scripts/langfuse-smoke.sh` | New checks |
| `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md` | Docs |
| `backend/tests/…` | Tests (section "Tests") |

## IDs: uuid7 (`backend/app/ids.py`)

```python
import uuid_utils

def new_id(at: float | None = None) -> str:
    """A uuid7 string. `at` (Unix seconds) sets the time part; default: now."""
    if at is None:
        return str(uuid_utils.uuid7())
    return str(uuid_utils.uuid7(nanoseconds=int(at * 1_000_000_000)))
```

- `put_batch_run` sets `batch_run_id = ids.new_id(received_at)` (was uuid5). The duplicate
  and conflict check (`use_case_id`, `run_id`, `content_sha256`) does not change.
- **Migration 10** "uuid7 batch run IDs": for each `batch_runs` row whose `batch_run_id` is
  not a version-7 UUID, set `batch_run_id = new_id(received_at)`. Nothing else in the row
  changes. A second run of the migration changes nothing. It runs after migration 9, and
  `batch_evaluations` is empty at that time (no foreign key to update).
- Prototype tables do not change.

## Grading engine (`backend/app/engines/batch_grading.py`)

Pure functions. No I/O, no clock, no logging. It never raises for a stored run: bad data
gives Unknown.

```python
BANDS_VERSION = "core-2026-10-12"

@dataclass(frozen=True)
class Metric:
    name: str
    lane: str               # "Delivery" | "Reliability" | "Output"
    value: float | None
    health: str             # "Green" | "Amber" | "Red" | "Unknown"
    reason: str | None      # set only when health is "Unknown"
    in_rollup: bool

@dataclass(frozen=True)
class Grade:
    bands_version: str
    metrics: tuple[Metric, ...]
    delivery_grade: str
    grade: str

def grade_run(body: dict, earlier_request_counts: list[int],
              turnaround_limit_s: int | None) -> Grade: ...
```

`body` is the stored `payload` (JSON). `earlier_request_counts` is newest first, at most 5.

| Metric | Lane | Value | Green | Amber | Red | Unknown (reason) |
|---|---|---|---|---|---|---|
| `run_status` | Delivery | none (`value` = None) | `completed` | `partial` | `failed` | other status → `invalid_status` |
| `turnaround_s` | Delivery | `completed_at − submitted_at` in seconds | ≤ L | L < v ≤ 2L | > 2L | no `submitted_at` or L is None → `not_reported`; a time cannot be read, or v < 0 → `invalid_times` |
| `failure_rate` | Reliability | `failed_count / request_count` | < 0.01 | 0.01 ≤ v < 0.05 | ≥ 0.05 | `request_count` = 0 → `no_requests` |
| `volume_change` | Reliability | `request_count / median(earlier 5)` | 0.7 ≤ v ≤ 1.3 | 0.4 ≤ v < 0.7 or 1.3 < v ≤ 2.0 | < 0.4 or > 2.0 | fewer than 5 earlier runs, or median 0 → `no_baseline` |
| `valid_output_rate` | Output | — | — | — | — | always `records_not_approved`; `in_rollup` False |
| `block_rate` | Output | — | — | — | — | always `records_not_approved`; `in_rollup` False |

- L = `turnaround_limit_s` of the use case in the registry.
- Red is examined first. Unknown is never Green.
- `delivery_grade` = worst of the Delivery metrics. `grade` = worst of the metrics with
  `in_rollup` in the lanes Reliability and Output. Worst order: Red > Amber > Unknown > Green
  (`engines/health.py` `HEALTH_RANK`).
- Times are ISO 8601 UTC strings as the schema accepts them (`Z` or `+00:00`).

## Table `batch_evaluations` (migration 9 "batch evaluations")

| Column | Type | Note |
|---|---|---|
| `evaluation_id` | String, primary key | uuid7 (`ids.new_id()`) |
| `batch_run_id` | String, not null | |
| `use_case_id`, `run_id`, `trace_id` | String, not null | Copied from the run |
| `bands_version` | String, not null | |
| `metrics` | Text, not null | JSON list of the `Metric` fields |
| `delivery_grade`, `grade` | String, not null | |
| `baseline_run_ids` | Text, not null | JSON list of the earlier `batch_run_id`s (empty if fewer than 5) |
| `evaluated_at` | Float, not null | |
| `langfuse_status` | String, not null | `pending` \| `sent` \| `skipped` \| `failed` |
| `langfuse_attempts` | Integer, not null, default 0 | |
| `langfuse_error` | String, null | The exception class name only |

- Unique (`batch_run_id`, `bands_version`).
- After the insert, only the three `langfuse_*` columns change.
- Store functions in `db.py`:
  - `runs_without_evaluation(bands_version, limit) -> list[dict]`: the oldest by `received_at` first.
  - `earlier_runs(use_case_id, completed_at, limit=5) -> list[dict]`: the same use case, `completed_at` < the given value, newest first.
  - `put_batch_evaluation(row) -> bool`: False if the unique key exists (no error).
  - `evaluations_for_langfuse(limit) -> list[dict]`: status `pending`.
  - `set_langfuse_result(evaluation_id, status, error)`: also adds 1 to `langfuse_attempts`.
  - `evaluator_counts() -> dict`: `unevaluated` and `langfuse_pending`.

## Langfuse scores (`backend/app/adapters/langfuse_scores.py`)

```python
class ScoreSender(Protocol):
    def send(self, evaluation: dict) -> None: ...   # raises on failure

def make_sender() -> ScoreSender | None: ...   # None when not configured
```

- Configured only when `EVALUATOR_LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY` and
  `LANGFUSE_SECRET_KEY` are all set. `EVALUATOR_LANGFUSE_HOST` reads the raw
  `LANGFUSE_HOST` environment value. It never falls back to `config.LANGFUSE_HOST`, whose
  default is `https://cloud.langfuse.com`. Scores go only to the self-hosted Langfuse.
- Client: `Langfuse(public_key=…, secret_key=…, host=…, tracing_enabled=False, timeout=10)`.
  `tracing_enabled=False` keeps the SDK away from the app's OpenTelemetry setup.
- Calls: the synchronous `client.api.scores.create(name=…, value=…, id=score_id,
  trace_id=…, data_type=…, comment=…)`. Do not use `client.create_score`: it queues and never
  raises.
- `score_id` = `str(uuid.uuid5(SCORE_NAMESPACE, f"{evaluation_id}:{name}"))`, with a fixed
  `SCORE_NAMESPACE` UUID constant in the module.

| Score name | `data_type` | Value | Comment |
|---|---|---|---|
| `grade` | `CATEGORICAL` | the grade | `bands core-2026-10-12; unknown: volume_change=no_baseline, …` |
| `delivery_grade` | `CATEGORICAL` | the delivery grade | the same form |
| `failure_rate`, `volume_change`, `turnaround_s` | `NUMERIC` | the value | `Green` (the band) |

- A numeric score is sent only when the metric has a value. Record metrics are not sent.

## Worker (`backend/app/batch_evaluator.py`)

- An `asyncio` task started by the lifespan when `BATCH_EVALUATOR_ENABLED` is true. Each
  cycle runs in a thread (`asyncio.to_thread`), because the store is synchronous.
- **Lease:** name `batch-evaluator` in `live_worker_leases`, with an owner ID
  `<hostname>:<pid>:<random>`. Lease time = 3 × interval. Take or renew the lease at the start of
  each cycle; without the lease, do nothing in that cycle.
- **Cycle:**
  1. For each run of `runs_without_evaluation(BANDS_VERSION, 50)`:
     - read `earlier_runs`
     - read `turnaround_limit_s` from the current registry
     - `grade_run(...)`
     - `put_batch_evaluation(...)` with `langfuse_status` = `pending`, or `skipped` when no sender
  2. For each row of `evaluations_for_langfuse(50)`, call `sender.send(row)`:
     - success → `sent`
     - an exception → `pending` with the error class
     - when `langfuse_attempts` reaches 20 → `failed`
  3. Record `last_cycle_at`.
- **Errors:** an exception in a cycle is logged (class and message, no body, no keys), and
  the next cycle runs normally. A grading problem of one run never stops the other runs.
- **Use case not in the registry** (removed after the run was stored): grade with L = None.
- **Shutdown:** cancel the task and wait for the current cycle to end, at most 10 s.
- Log one line for each new evaluation: `use_case_id`, `run_id`, `trace_id`, `grade`,
  `delivery_grade`.

## Settings (`backend/app/config.py`)

| Setting | Default |
|---|---|
| `BATCH_EVALUATOR_ENABLED` | `true` |
| `BATCH_EVALUATOR_INTERVAL_S` | `30` |
| `EVALUATOR_LANGFUSE_HOST` | raw `LANGFUSE_HOST`, empty if not set |

Tests set `BATCH_EVALUATOR_ENABLED=false` in `conftest.py` and call the cycle function
directly.

## Registry

`load()` rejects a use case with a non-empty `band_overrides`. The message is:
`<use_case_id>: band_overrides is not supported yet (S2-05); remove it or wait for support`.

## Readiness

`/api/readiness` adds this object. It does not change `status`, because readiness answers
whether a run can be stored.

```json
"batch_evaluator": {"enabled": true, "last_cycle_at": "2026-10-14T03:00:00Z",
                    "unevaluated": 0, "langfuse_pending": 0}
```

`last_cycle_at` is `null` before the first cycle.

## Local stack and CI

- `deploy/compose/compose.local.yaml`, the backend service:
  - `LANGFUSE_HOST: ${BACKEND_LANGFUSE_HOST:-}`
  - `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`: the local test keys of
    `deploy/langfuse/local.env`
  - `BATCH_EVALUATOR_INTERVAL_S: "5"`
- `scripts/compose-smoke.sh`: after the `POST`, poll readiness for up to 60 s until
  `batch_evaluator.unevaluated` is 0. `langfuse_pending` is 0, because the status is `skipped`.
- `scripts/langfuse-smoke.sh`:
  - export `BACKEND_LANGFUSE_HOST=http://langfuse-web:3000`
  - after the trace check, poll `GET /api/public/scores?traceId=<id>&name=grade` on
    `http://127.0.0.1:3000` with the local keys (Basic auth), for up to 90 s, until 1 score
    is found
  - then make sure that readiness shows `langfuse_pending` 0

## Test host

- `deploy/compose/add-langfuse-backend-env.sh` (run once with sudo):
  - reads `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` and `LANGFUSE_INIT_PROJECT_SECRET_KEY` from `/opt/langfuse/langfuse.env`
  - sets `LANGFUSE_HOST=http://langfuse-web:3000`, `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `/opt/model-monitor/backend.env` (mode 600, root; the other lines stay)
  - prints names only
- TESTHOST "Batch evaluator (S2-05)":
  1. Run the script.
  2. Set `BACKEND_IMAGE` to the new build, then `pull` and `up -d --wait`.
  3. Readiness must show `batch_evaluator.unevaluated` 0 and `langfuse_pending` 0.
  4. In Langfuse, the RTR trace must show the `grade` score.
- The TESTHOST S2-03 section also gets:
  - the `backend:14` image step
  - the VS Code port-forward option
  - the "?" arrows fixed

## Tests

| File | Covers |
|---|---|
| `test_ids.py` | Version 7; the time part equals `at` (ms); IDs made later sort later |
| `test_batch_grading.py` | Every band edge: failure 0.0099/0.01/0.0499/0.05; volume 0.39/0.4/0.69/0.7/1.3/1.31/2.0/2.01; turnaround L, L+1, 2L, 2L+1. Every Unknown reason. Unknown never Green. Output metrics are never in the rollup. `delivery_grade` does not change `grade`. |
| `test_batch_evaluations_store.py` | Migrations 9 and 10 (the old uuid5 rows become uuid7 from `received_at`; a second run changes nothing; the other columns do not change); the unique key; `earlier_runs` order by `completed_at`; `put_batch_run` makes uuid7 |
| `test_batch_evaluator.py` | One cycle grades each run one time; two cycles with two owners at the same time make one row; the lease blocks a second owner; the stored run's `payload` and `content_sha256` do not change; the `POST` returns 201 before any evaluation exists; an engine or store error in one cycle does not stop the next |
| `test_langfuse_scores.py` | A fake client: the score names, types and values; stable `score_id` for the same evaluation; a failure → `pending`, then a retry → `sent`; 20 failures → `failed`; no host → `make_sender()` is None and the status is `skipped`; `LANGFUSE_HOST` not set never uses cloud.langfuse.com |
| `test_registry.py` | A non-empty `band_overrides` fails the load with the message |
| `test_app_surface.py` (the existing readiness test) | The `batch_evaluator` object and that `status` does not change |

All the existing tests pass, also the chatbot (`AICT-L02`) tests.

## Docs

- CHANGELOG.
- DEVLOG.
- `issues.md` S2-05: a note with the decisions and the link to this folder.
- TESTHOST, as in the section "Test host".

## Not in scope

The missing-run timer (S3-02), records and the record metrics, the judge, the quality
profiles, band overrides, the dashboard (S2-07), the `monitor.evaluate` span, and uuid7 for
the prototype tables.
