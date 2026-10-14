# Batch Evaluator (S2-05) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **In this project Codex implements and does not commit; Claude reviews and commits each task.**

**Goal:** Each stored batch run is graded one time with the core metrics by a background worker; the result is stored in `batch_evaluations` and sent as scores to the run's trace in self-hosted Langfuse.

**Architecture:** A pure engine (`engines/batch_grading.py`) calculates the metrics and grades. A runner (`batch_evaluator.py`) runs as an asyncio task in the backend lifespan, holds the DB lease `batch-evaluator`, stores one evaluation row for each run and sends scores through an adapter (`adapters/langfuse_scores.py`). IDs of MVP tables become uuid7 (`ids.py`, package `uuid-utils`).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core, pytest, Langfuse SDK 4.17 (`client.api.scores.create`), `uuid-utils` 1.0.

**Spec:** `changes/2026-10-14-s2-05-batch-evaluator/spec.md` (intent: `intent.md` in the same folder). Read both before you start.

## Global Constraints

- Bands version string: `core-2026-10-12`. Bands exactly as in the spec table "Grading engine".
- New package: `uuid-utils>=1.0,<2` only. No other new package.
- The engine is pure: no I/O, no clock, no logging, and it never raises for a stored run.
- The stored `batch_runs` row never changes after the insert, except the one-time migration 10 of `batch_run_id`.
- In `batch_evaluations`, only `langfuse_status`, `langfuse_attempts` and `langfuse_error` change after the insert.
- Scores go only to the host in the raw `LANGFUSE_HOST` setting. Never fall back to `config.LANGFUSE_HOST` (default `https://cloud.langfuse.com`).
- Use `client.api.scores.create(...)` (synchronous). Never use `client.create_score(...)`.
- Logs and readiness never contain a key, a password or a body. An error is reported by its class name.
- Prototype tables and prototype code do not change.
- LF line endings. No `git add` and no `git commit` (Claude commits).
- Run the tests from `backend/` with `.venv\Scripts\python.exe -m pytest ...` (Windows) or `.venv/bin/python -m pytest ...`. If the sandbox blocks the pytest temp folder, add `-p no:cacheprovider --basetemp=.pytest-tmp`.

### Corrections to the spec (found while writing this plan; they win over the spec)

1. **Baseline selection is in Python, not in SQL.** `completed_at` may have fractional seconds (`…:30Z` and `…:30.5Z`), so a string comparison in SQL sorts wrongly. The store returns the history of the use case (`db.batch_run_history`), and the pure function `batch_grading.select_baseline` selects the 5 earlier runs by parsed time. This replaces the spec's `earlier_runs(...)`.
2. **The engine has one more Unknown reason, `invalid_counts`**, for a `request_count` or `failed_count` that is not a non-negative integer. The schema prevents this, but the engine must never raise.
3. **The CI reads scores with `GET /api/public/v3/scores?traceId=…&name=grade`.** Langfuse v4 removed the old read path. Writes still use `POST /api/public/scores` through the SDK.

## Review Focus

1. **`completed_at` with and without fractional seconds in the same use case:** the baseline must use the real time order. Test in Task 2 (`test_select_baseline_uses_time_not_text`).
2. **A use case removed from the registry after its run was stored:** the run is still graded, with `turnaround_s` Unknown (`not_reported`). Test in Task 5 (`test_run_of_removed_use_case_is_still_graded`).
3. **The current run itself, or a later run, in the history:** it is never in its own baseline. Test in Task 2 (`test_select_baseline_excludes_same_and_later_runs`).
4. **Langfuse fails 20 times:** the row becomes `failed` and is not sent again; the grade does not change. Test in Task 5 (`test_twenty_failures_mark_failed`).
5. **The DB is down when readiness is called:** readiness still answers, with `unevaluated: null` and `langfuse_pending: null`. Test in Task 5 (`test_readiness_evaluator_counts_when_database_fails`).

---

### Task 1: uuid7 IDs

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/ids.py`
- Modify: `backend/app/db.py` (`put_batch_run`, around line 1162)
- Test: `backend/tests/test_ids.py`, `backend/tests/test_batch_runs_store.py`

**Interfaces:**
- Produces: `ids.new_id(at: float | None = None) -> str` (uuid7 string); `ids.is_uuid7(value: str) -> bool`.

- [ ] **Step 1: Add the package.** In `backend/requirements.txt`, add one line after the OpenTelemetry lines:

```
uuid-utils>=1.0,<2
```

Install it in the local venv: `uv pip install --python .venv\Scripts\python.exe "uuid-utils>=1.0,<2"` (it may already be installed).

- [ ] **Step 2: Write the failing tests** in `backend/tests/test_ids.py`:

```python
"""uuid7 IDs of the MVP tables (S2-05)."""
from __future__ import annotations

import uuid

from app import ids


def test_new_id_is_version_7():
    value = ids.new_id()
    parsed = uuid.UUID(value)
    assert parsed.version == 7 and parsed.variant == uuid.RFC_4122
    assert ids.is_uuid7(value)


def test_time_part_is_the_given_time():
    at = 1_760_000_000.123
    value = uuid.UUID(ids.new_id(at))
    millis = value.int >> 80
    assert millis == int(at * 1000)


def test_later_ids_sort_later():
    first, second = ids.new_id(1_760_000_000.0), ids.new_id(1_760_000_001.0)
    assert first < second
    made = [ids.new_id() for _ in range(50)]
    assert made == sorted(made)


def test_is_uuid7_rejects_other_values():
    assert not ids.is_uuid7(str(uuid.uuid5(uuid.NAMESPACE_URL, "x")))
    assert not ids.is_uuid7("not-a-uuid")
    assert not ids.is_uuid7("")
```

Add to `backend/tests/test_batch_runs_store.py`:

```python
def test_put_makes_a_uuid7_from_the_receive_time(isolated_db):
    from app import ids
    import uuid
    stored, _ = db.put_batch_run(row())
    assert ids.is_uuid7(stored["batch_run_id"])
    assert uuid.UUID(stored["batch_run_id"]).int >> 80 == int(stored["received_at"] * 1000)
```

- [ ] **Step 3: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_ids.py tests/test_batch_runs_store.py -q`
Expected: FAIL (`ModuleNotFoundError: app.ids`).

- [ ] **Step 4: Write `backend/app/ids.py`:**

```python
"""Time-ordered IDs (uuid7, RFC 9562) for the rows of the batch MVP tables (S2-05).

The time part is the creation time in milliseconds, so the IDs sort by time. Prototype
tables keep their own IDs (S4-07 deletes them).
"""
from __future__ import annotations

import uuid

import uuid_utils


def new_id(at: float | None = None) -> str:
    """A uuid7 string. `at` (Unix seconds) sets the time part; default: now."""
    if at is None:
        return str(uuid_utils.uuid7())
    return str(uuid_utils.uuid7(nanoseconds=int(at * 1_000_000_000)))


def is_uuid7(value: str) -> bool:
    try:
        return uuid.UUID(value).version == 7
    except (ValueError, TypeError, AttributeError):
        return False
```

- [ ] **Step 5: Change `put_batch_run` in `backend/app/db.py`.** Add `from . import config, ids` (replace `from . import config`). Replace:

```python
    new = {**row, "received_at": time.time(), "batch_run_id": str(uuid.uuid5(
        uuid.NAMESPACE_URL, f"batch-run/{use_case_id}/{run_id}"))}
```

with:

```python
    received_at = time.time()
    new = {**row, "received_at": received_at, "batch_run_id": ids.new_id(received_at)}
```

Keep `import uuid` in `db.py` (other code uses it).

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_ids.py tests/test_batch_runs_store.py tests/test_batch_runs_api.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `feat(s2-05): uuid7 IDs for batch runs (uuid-utils)`

---

### Task 2: Grading engine (pure)

**Files:**
- Create: `backend/app/engines/batch_grading.py`
- Test: `backend/tests/test_batch_grading.py`

**Interfaces:**
- Consumes: `engines.health.worst(healths: list[str]) -> str`.
- Produces:
  - `BANDS_VERSION: str = "core-2026-10-12"`
  - `@dataclass(frozen=True) class Metric(name: str, lane: str, value: float | None, health: str, reason: str | None, in_rollup: bool)`
  - `@dataclass(frozen=True) class Grade(bands_version: str, metrics: tuple[Metric, ...], delivery_grade: str, grade: str)`
  - `grade_run(body: dict, earlier_request_counts: list[int], turnaround_limit_s: int | None) -> Grade`
  - `select_baseline(history: list[dict], batch_run_id: str, completed_at: str, size: int = 5) -> list[dict]` (each history dict has `batch_run_id`, `completed_at`, `request_count`; returns newest first)
  - `parse_utc(text: object) -> datetime | None`

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_batch_grading.py`:

```python
"""Core-metric grading (S2-05): bands, Unknown reasons, rollup, baseline selection."""
from __future__ import annotations

import pytest

from app.engines import batch_grading as g


def body(**overrides) -> dict:
    base = {"status": "completed", "completed_at": "2026-10-06T02:12:30Z",
            "request_count": 1000, "failed_count": 0, "records": []}
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not _DROP}


_DROP = object()
FIVE = [1000, 1000, 1000, 1000, 1000]


def metric(grade: g.Grade, name: str) -> g.Metric:
    return next(m for m in grade.metrics if m.name == name)


def test_bands_version():
    assert g.grade_run(body(), FIVE, None).bands_version == "core-2026-10-12"


@pytest.mark.parametrize("failed, health", [
    (0, "Green"), (9, "Green"),          # 0.009
    (10, "Amber"), (49, "Amber"),        # exactly 0.01 is Amber; 0.049
    (50, "Red"), (1000, "Red"),          # exactly 0.05 is Red
])
def test_failure_rate_bands(failed, health):
    m = metric(g.grade_run(body(failed_count=failed), FIVE, None), "failure_rate")
    assert m.health == health and m.value == failed / 1000 and m.lane == "Reliability"


def test_failure_rate_unknown_without_requests():
    m = metric(g.grade_run(body(request_count=0, failed_count=0), FIVE, None), "failure_rate")
    assert (m.health, m.reason, m.value) == ("Unknown", "no_requests", None)


@pytest.mark.parametrize("count, health", [
    (39, "Red"), (40, "Amber"), (69, "Amber"), (70, "Green"), (100, "Green"),
    (130, "Green"), (131, "Amber"), (200, "Amber"), (201, "Red"),
])
def test_volume_change_bands(count, health):
    m = metric(g.grade_run(body(request_count=count), [100] * 5, None), "volume_change")
    assert m.health == health and m.value == count / 100


@pytest.mark.parametrize("earlier", [[], [100] * 4, [0] * 5])
def test_volume_change_no_baseline(earlier):
    m = metric(g.grade_run(body(), earlier, None), "volume_change")
    assert (m.health, m.reason) == ("Unknown", "no_baseline")


def test_volume_change_uses_the_median_of_five():
    m = metric(g.grade_run(body(request_count=100), [10, 100, 100, 100, 1000, 5], None),
               "volume_change")
    assert m.value == 1.0                 # only the first 5 count; median 100


@pytest.mark.parametrize("seconds, health", [
    (3600, "Green"), (3601, "Amber"), (7200, "Amber"), (7201, "Red"),
])
def test_turnaround_bands(seconds, health):
    from datetime import datetime, timedelta, timezone
    done = datetime(2026, 10, 6, 2, 12, 30, tzinfo=timezone.utc)
    sub = (done - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = metric(g.grade_run(body(submitted_at=sub), FIVE, 3600), "turnaround_s")
    assert m.health == health and m.value == seconds and m.lane == "Delivery"


@pytest.mark.parametrize("extra, limit, reason", [
    ({}, 3600, "not_reported"),                                         # no submitted_at
    ({"submitted_at": "2026-10-06T01:00:00Z"}, None, "not_reported"),   # no limit
    ({"submitted_at": "2026-10-06T03:00:00Z"}, 3600, "invalid_times"),  # after completed_at
    ({"submitted_at": "yesterday"}, 3600, "invalid_times"),
])
def test_turnaround_unknown(extra, limit, reason):
    m = metric(g.grade_run(body(**extra), FIVE, limit), "turnaround_s")
    assert (m.health, m.reason) == ("Unknown", reason)


@pytest.mark.parametrize("status, health", [
    ("completed", "Green"), ("partial", "Amber"), ("failed", "Red")])
def test_run_status(status, health):
    m = metric(g.grade_run(body(status=status), FIVE, None), "run_status")
    assert m.health == health and m.lane == "Delivery" and m.value is None


def test_run_status_unknown_value():
    m = metric(g.grade_run(body(status="weird"), FIVE, None), "run_status")
    assert (m.health, m.reason) == ("Unknown", "invalid_status")


@pytest.mark.parametrize("field, value", [
    ("request_count", "10"), ("request_count", -1), ("failed_count", None),
    ("request_count", True)])
def test_bad_counts_are_unknown_never_an_error(field, value):
    grade = g.grade_run(body(**{field: value}), FIVE, None)
    assert metric(grade, "failure_rate").reason == "invalid_counts"


def test_output_metrics_are_unknown_and_not_in_rollup():
    grade = g.grade_run(body(), FIVE, None)
    for name in ("valid_output_rate", "block_rate"):
        m = metric(grade, name)
        assert (m.health, m.reason, m.in_rollup, m.lane) == (
            "Unknown", "records_not_approved", False, "Output")


def test_grade_is_green_only_when_all_rollup_metrics_are_green():
    grade = g.grade_run(body(), FIVE, None)
    assert grade.grade == "Green"


def test_unknown_is_never_green():
    grade = g.grade_run(body(), [], None)          # volume_change no_baseline
    assert grade.grade == "Unknown"


def test_red_wins_over_unknown():
    grade = g.grade_run(body(failed_count=500), [], None)
    assert grade.grade == "Red"


def test_delivery_does_not_change_grade():
    grade = g.grade_run(body(status="failed"), FIVE, None)
    assert grade.delivery_grade == "Red" and grade.grade == "Green"


def test_delivery_grade_is_worst_of_delivery():
    grade = g.grade_run(body(status="partial"), FIVE, None)   # turnaround not_reported
    assert grade.delivery_grade == "Amber"


def h(run_id: str, completed_at: str, count: int = 100) -> dict:
    return {"batch_run_id": run_id, "completed_at": completed_at, "request_count": count}


def test_select_baseline_newest_first_max_five():
    history = [h(f"r{i}", f"2026-10-0{i}T00:00:00Z") for i in range(1, 9)]
    chosen = g.select_baseline(history, "r9", "2026-10-09T00:00:00Z")
    assert [x["batch_run_id"] for x in chosen] == ["r8", "r7", "r6", "r5", "r4"]


def test_select_baseline_uses_time_not_text():
    history = [h("a", "2026-10-06T02:12:30.5Z"), h("b", "2026-10-06T02:12:30Z")]
    chosen = g.select_baseline(history, "now", "2026-10-06T02:12:30.2Z")
    assert [x["batch_run_id"] for x in chosen] == ["b"]


def test_select_baseline_excludes_same_and_later_runs():
    history = [h("self", "2026-10-05T00:00:00Z"), h("later", "2026-10-06T00:00:00Z"),
               h("same-time", "2026-10-05T00:00:00Z"), h("bad", "not a time"),
               h("earlier", "2026-10-04T00:00:00Z")]
    chosen = g.select_baseline(history, "self", "2026-10-05T00:00:00Z")
    assert [x["batch_run_id"] for x in chosen] == ["earlier"]


def test_select_baseline_with_unreadable_own_time_is_empty():
    assert g.select_baseline([h("a", "2026-10-04T00:00:00Z")], "x", "nope") == []
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_grading.py -q`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Write `backend/app/engines/batch_grading.py`:**

```python
"""Core-metric grading of one batch run (S2-05). Pure: no I/O, no clock, no logging.

Bands: changes/2026-10-08-batch-metric-profiles/core-metrics.md, section 1 (RAI approved;
version below). Red is examined first; Unknown is never Green. The delivery lane has its
own grade and never changes `grade`. The record metrics are Unknown (`records_not_approved`)
and are not in the rollup while the MVP is identity-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import median

from .health import worst

BANDS_VERSION = "core-2026-10-12"
DELIVERY, RELIABILITY, OUTPUT = "Delivery", "Reliability", "Output"
BASELINE_SIZE = 5


@dataclass(frozen=True)
class Metric:
    name: str
    lane: str
    value: float | None
    health: str
    reason: str | None
    in_rollup: bool


@dataclass(frozen=True)
class Grade:
    bands_version: str
    metrics: tuple[Metric, ...]
    delivery_grade: str
    grade: str


def parse_utc(text: object) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _unknown(name: str, lane: str, reason: str, in_rollup: bool = True) -> Metric:
    return Metric(name, lane, None, "Unknown", reason, in_rollup)


def _run_status(body: dict) -> Metric:
    health = {"completed": "Green", "partial": "Amber", "failed": "Red"}.get(body.get("status"))
    if health is None:
        return _unknown("run_status", DELIVERY, "invalid_status")
    return Metric("run_status", DELIVERY, None, health, None, True)


def _turnaround(body: dict, limit: int | None) -> Metric:
    name = "turnaround_s"
    if body.get("submitted_at") is None or limit is None:
        return _unknown(name, DELIVERY, "not_reported")
    completed, submitted = parse_utc(body.get("completed_at")), parse_utc(body.get("submitted_at"))
    if completed is None or submitted is None:
        return _unknown(name, DELIVERY, "invalid_times")
    seconds = (completed - submitted).total_seconds()
    if seconds < 0:
        return _unknown(name, DELIVERY, "invalid_times")
    if seconds > 2 * limit:
        health = "Red"
    elif seconds <= limit:
        health = "Green"
    else:
        health = "Amber"
    return Metric(name, DELIVERY, seconds, health, None, True)


def _failure_rate(body: dict) -> Metric:
    name = "failure_rate"
    requests, failed = _count(body.get("request_count")), _count(body.get("failed_count"))
    if requests is None or failed is None:
        return _unknown(name, RELIABILITY, "invalid_counts")
    if requests == 0:
        return _unknown(name, RELIABILITY, "no_requests")
    value = failed / requests
    if value >= 0.05:
        health = "Red"
    elif value < 0.01:
        health = "Green"
    else:
        health = "Amber"
    return Metric(name, RELIABILITY, value, health, None, True)


def _volume_change(body: dict, earlier: list[int]) -> Metric:
    name = "volume_change"
    requests = _count(body.get("request_count"))
    if requests is None:
        return _unknown(name, RELIABILITY, "invalid_counts")
    window = [c for c in (_count(x) for x in earlier[:BASELINE_SIZE]) if c is not None]
    if len(window) < BASELINE_SIZE or median(window) <= 0:
        return _unknown(name, RELIABILITY, "no_baseline")
    value = requests / median(window)
    if value < 0.4 or value > 2.0:
        health = "Red"
    elif 0.7 <= value <= 1.3:
        health = "Green"
    else:
        health = "Amber"
    return Metric(name, RELIABILITY, value, health, None, True)


def grade_run(body: dict, earlier_request_counts: list[int],
              turnaround_limit_s: int | None) -> Grade:
    metrics = (
        _run_status(body),
        _turnaround(body, turnaround_limit_s),
        _failure_rate(body),
        _volume_change(body, earlier_request_counts),
        _unknown("valid_output_rate", OUTPUT, "records_not_approved", in_rollup=False),
        _unknown("block_rate", OUTPUT, "records_not_approved", in_rollup=False),
    )
    delivery = worst([m.health for m in metrics if m.lane == DELIVERY])
    grade = worst([m.health for m in metrics if m.lane != DELIVERY and m.in_rollup])
    return Grade(BANDS_VERSION, metrics, delivery, grade)


def select_baseline(history: list[dict], batch_run_id: str, completed_at: str,
                    size: int = BASELINE_SIZE) -> list[dict]:
    """The `size` runs that completed before `completed_at`, newest first.

    Times are compared as parsed datetimes (fractional seconds are allowed, so text order
    is wrong). The run itself, runs at the same time or later, and unreadable times are out.
    """
    own = parse_utc(completed_at)
    if own is None:
        return []
    earlier = []
    for item in history:
        at = parse_utc(item.get("completed_at"))
        if item.get("batch_run_id") == batch_run_id or at is None or at >= own:
            continue
        earlier.append((at, item))
    earlier.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in earlier[:size]]
```

- [ ] **Step 4: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_grading.py -q`
Expected: PASS.

- [ ] **Step 5: Commit** (Claude): `feat(s2-05): core-metric grading engine`

---

### Task 3: Table `batch_evaluations` and the store

**Files:**
- Modify: `backend/app/db.py` (tables near line 268; migrations list near line 314; store functions after `list_batch_runs`)
- Create: `backend/tests/test_batch_evaluations_store.py`
- Modify: `backend/tests/test_batch_runs_store.py` (`test_migration_eight_is_recorded_and_idempotent`)

**Interfaces:**
- Consumes: `ids.new_id`, `ids.is_uuid7` (Task 1).
- Produces (all in `app.db`):
  - `batch_evaluations` (Table)
  - `runs_without_evaluation(bands_version: str, limit: int = 50) -> list[dict]`
  - `batch_run_history(use_case_id: str, limit: int = 1000) -> list[dict]` (keys `batch_run_id`, `completed_at`, `request_count`)
  - `put_batch_evaluation(row: dict) -> bool`
  - `evaluations_for_langfuse(limit: int = 50) -> list[dict]`
  - `set_langfuse_result(evaluation_id: str, status: str, error: str | None) -> None`
  - `evaluator_counts(bands_version: str) -> dict` (`{"unevaluated": int, "langfuse_pending": int}`)

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_batch_evaluations_store.py`:

```python
"""`batch_evaluations` (S2-05): migrations 9 and 10, store functions."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app import db, ids
from tests.test_batch_runs_store import row as run_row

BANDS = "core-2026-10-12"


def evaluation(stored: dict, **overrides) -> dict:
    base = {
        "evaluation_id": ids.new_id(), "batch_run_id": stored["batch_run_id"],
        "use_case_id": stored["use_case_id"], "run_id": stored["run_id"],
        "trace_id": stored["trace_id"], "bands_version": BANDS,
        "metrics": json.dumps([]), "delivery_grade": "Green", "grade": "Unknown",
        "baseline_run_ids": json.dumps([]), "evaluated_at": 1.0,
        "langfuse_status": "pending", "langfuse_attempts": 0, "langfuse_error": None,
    }
    return {**base, **overrides}


def test_migrations_nine_and_ten_are_recorded(isolated_db):
    bind = db.engine()
    with bind.begin() as cx:
        names = dict(cx.execute(db.select(db.schema_migrations.c.version,
                                          db.schema_migrations.c.name)).all())
    assert names[9] == "batch evaluations"
    assert names[10] == "uuid7 batch run IDs"


def test_migration_ten_rewrites_old_ids_once(isolated_db):
    bind = db.engine()
    old = str(uuid.uuid5(uuid.NAMESPACE_URL, "batch-run/GCP-UC-03/r1"))
    with bind.begin() as cx:
        cx.execute(db.insert(db.batch_runs), {**run_row(run_id="r1"), "batch_run_id": old,
                                              "received_at": 1_760_000_000.5})
        cx.exec_driver_sql("DELETE FROM schema_migrations WHERE version = 10")
    before = db.get_batch_run("GCP-UC-03", "r1")
    assert db.migrate_engine(bind) == [10]
    after = db.get_batch_run("GCP-UC-03", "r1")
    assert ids.is_uuid7(after["batch_run_id"])
    assert uuid.UUID(after["batch_run_id"]).int >> 80 == 1_760_000_000_500
    assert {k: v for k, v in after.items() if k != "batch_run_id"} == {
        k: v for k, v in before.items() if k != "batch_run_id"}
    with bind.begin() as cx:                         # a second run changes nothing
        cx.exec_driver_sql("DELETE FROM schema_migrations WHERE version = 10")
    assert db.migrate_engine(bind) == [10]
    assert db.get_batch_run("GCP-UC-03", "r1") == after


def test_put_evaluation_once_per_run_and_bands(isolated_db):
    stored, _ = db.put_batch_run(run_row())
    assert db.put_batch_evaluation(evaluation(stored)) is True
    assert db.put_batch_evaluation(evaluation(stored)) is False      # same run, same bands
    assert db.put_batch_evaluation(evaluation(stored, bands_version="other")) is True


def test_unique_key_is_enforced_by_the_database(isolated_db):
    stored, _ = db.put_batch_run(run_row())
    db.put_batch_evaluation(evaluation(stored))
    with pytest.raises(IntegrityError):
        with db.engine().begin() as cx:
            cx.execute(db.insert(db.batch_evaluations), evaluation(stored))


def test_runs_without_evaluation_oldest_first(isolated_db):
    first, _ = db.put_batch_run(run_row(run_id="a"))
    second, _ = db.put_batch_run(run_row(run_id="b"))
    assert [r["run_id"] for r in db.runs_without_evaluation(BANDS)] == ["a", "b"]
    db.put_batch_evaluation(evaluation(first))
    assert [r["run_id"] for r in db.runs_without_evaluation(BANDS)] == ["b"]
    assert [r["run_id"] for r in db.runs_without_evaluation("other")] == ["a", "b"]


def test_batch_run_history_is_the_use_case_only(isolated_db):
    db.put_batch_run(run_row(run_id="a"))
    db.put_batch_run(run_row(run_id="b", use_case_id="GCP-UC-07"))
    history = db.batch_run_history("GCP-UC-03")
    assert len(history) == 1
    assert set(history[0]) == {"batch_run_id", "completed_at", "request_count"}


def test_langfuse_result_and_counts(isolated_db):
    a, _ = db.put_batch_run(run_row(run_id="a"))
    db.put_batch_run(run_row(run_id="b"))
    ev = evaluation(a)
    db.put_batch_evaluation(ev)
    assert db.evaluator_counts(BANDS) == {"unevaluated": 1, "langfuse_pending": 1}
    assert [e["evaluation_id"] for e in db.evaluations_for_langfuse()] == [ev["evaluation_id"]]
    db.set_langfuse_result(ev["evaluation_id"], "pending", "ConnectError")
    pending = db.evaluations_for_langfuse()[0]
    assert pending["langfuse_attempts"] == 1 and pending["langfuse_error"] == "ConnectError"
    db.set_langfuse_result(ev["evaluation_id"], "sent", None)
    assert db.evaluations_for_langfuse() == []
    assert db.evaluator_counts(BANDS) == {"unevaluated": 1, "langfuse_pending": 0}
```

In `backend/tests/test_batch_runs_store.py`, change the expected list in
`test_migration_eight_is_recorded_and_idempotent` to `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`.

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_evaluations_store.py tests/test_batch_runs_store.py -q`
Expected: FAIL (`AttributeError: module 'app.db' has no attribute 'batch_evaluations'`).

- [ ] **Step 3: Add the table** in `backend/app/db.py`, after the `batch_runs` table:

```python
# One evaluation of a stored batch run (S2-05). The grade fields never change after the
# insert; only the three langfuse_* fields do. `evaluation_id` is a uuid7.
batch_evaluations = Table(
    "batch_evaluations", metadata,
    Column("evaluation_id", String, primary_key=True),
    Column("batch_run_id", String, nullable=False, index=True),
    Column("use_case_id", String, nullable=False, index=True),
    Column("run_id", String, nullable=False),
    Column("trace_id", String, nullable=False),
    Column("bands_version", String, nullable=False),
    Column("metrics", Text, nullable=False),
    Column("delivery_grade", String, nullable=False),
    Column("grade", String, nullable=False),
    Column("baseline_run_ids", Text, nullable=False),
    Column("evaluated_at", Float, nullable=False),
    Column("langfuse_status", String, nullable=False),     # pending | sent | skipped | failed
    Column("langfuse_attempts", Integer, nullable=False, default=0),
    Column("langfuse_error", String),
    UniqueConstraint("batch_run_id", "bands_version", name="uq_batch_evaluation"),
)
```

- [ ] **Step 4: Add migrations 9 and 10.** Inside `migrate_engine`, before `migrations = [`:

```python
    def uuid7_batch_run_ids(cx) -> None:
        rows = cx.execute(select(batch_runs.c.batch_run_id, batch_runs.c.received_at)).all()
        for old_id, received_at in rows:
            if ids.is_uuid7(old_id):
                continue
            cx.execute(update(batch_runs).where(batch_runs.c.batch_run_id == old_id).values(
                batch_run_id=ids.new_id(received_at)))
```

Append to the `migrations` list:

```python
        (9, "batch evaluations",
         lambda cx: batch_evaluations.create(bind=cx, checkfirst=True)),
        (10, "uuid7 batch run IDs", uuid7_batch_run_ids),
```

- [ ] **Step 5: Add the store functions** after `list_batch_runs`:

```python
# ---------------------------------------------------------------- batch evaluations (S2-05)

def runs_without_evaluation(bands_version: str, limit: int = 50) -> list[dict]:
    """Stored runs with no evaluation for `bands_version`, oldest received first."""
    done = select(batch_evaluations.c.batch_run_id).where(
        batch_evaluations.c.bands_version == bands_version)
    q = (select(batch_runs).where(batch_runs.c.batch_run_id.not_in(done))
         .order_by(batch_runs.c.received_at).limit(max(1, min(limit, 500))))
    with engine().begin() as cx:
        return [dict(r) for r in cx.execute(q).mappings().all()]


def batch_run_history(use_case_id: str, limit: int = 1000) -> list[dict]:
    """ID, completion time and request count of the newest runs of one use case.

    The caller selects the baseline by parsed time (`batch_grading.select_baseline`):
    `completed_at` may have fractional seconds, so SQL text order is not time order."""
    q = (select(batch_runs.c.batch_run_id, batch_runs.c.completed_at,
                batch_runs.c.request_count)
         .where(batch_runs.c.use_case_id == use_case_id)
         .order_by(batch_runs.c.received_at.desc()).limit(max(1, min(limit, 5000))))
    with engine().begin() as cx:
        return [dict(r) for r in cx.execute(q).mappings().all()]


def put_batch_evaluation(row: dict) -> bool:
    """Insert one evaluation. False when the run already has one for these bands."""
    with engine().begin() as cx:
        try:
            with cx.begin_nested():
                cx.execute(insert(batch_evaluations), row)
        except IntegrityError:
            return False
    return True


def evaluations_for_langfuse(limit: int = 50) -> list[dict]:
    q = (select(batch_evaluations).where(batch_evaluations.c.langfuse_status == "pending")
         .order_by(batch_evaluations.c.evaluated_at).limit(max(1, min(limit, 500))))
    with engine().begin() as cx:
        return [dict(r) for r in cx.execute(q).mappings().all()]


def set_langfuse_result(evaluation_id: str, status: str, error: str | None) -> None:
    with engine().begin() as cx:
        cx.execute(update(batch_evaluations).where(
            batch_evaluations.c.evaluation_id == evaluation_id).values(
                langfuse_status=status, langfuse_error=error,
                langfuse_attempts=batch_evaluations.c.langfuse_attempts + 1))


def evaluator_counts(bands_version: str) -> dict:
    done = select(batch_evaluations.c.batch_run_id).where(
        batch_evaluations.c.bands_version == bands_version)
    with engine().begin() as cx:
        unevaluated = cx.execute(select(func.count()).select_from(batch_runs).where(
            batch_runs.c.batch_run_id.not_in(done))).scalar_one()
        pending = cx.execute(select(func.count()).select_from(batch_evaluations).where(
            batch_evaluations.c.langfuse_status == "pending")).scalar_one()
    return {"unevaluated": int(unevaluated), "langfuse_pending": int(pending)}
```

Add `func` to the `from sqlalchemy import (...)` list.

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_evaluations_store.py tests/test_batch_runs_store.py tests/test_batch_runs_api.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `feat(s2-05): batch_evaluations table, uuid7 migration and store`

---

### Task 4: Langfuse score adapter and settings

**Files:**
- Modify: `backend/app/config.py` (after `BATCH_REGISTRY_PATH`)
- Create: `backend/app/adapters/langfuse_scores.py`
- Test: `backend/tests/test_langfuse_scores.py`

**Interfaces:**
- Produces:
  - `config.BATCH_EVALUATOR_ENABLED: bool`, `config.BATCH_EVALUATOR_INTERVAL_S: float`, `config.EVALUATOR_LANGFUSE_HOST: str`
  - `langfuse_scores.SCORE_NAMESPACE: uuid.UUID`
  - `langfuse_scores.score_id(evaluation_id: str, name: str) -> str`
  - `langfuse_scores.scores_for(evaluation: dict) -> list[dict]` (keys `id`, `name`, `value`, `data_type`, `comment`)
  - `class LangfuseScoreSender(client)` with `send(evaluation: dict) -> None` (raises on failure)
  - `langfuse_scores.make_sender() -> LangfuseScoreSender | None`

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_langfuse_scores.py`:

```python
"""Langfuse scores of one evaluation (S2-05)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app import config
from app.adapters import langfuse_scores as ls


def metrics(**health) -> str:
    base = [
        {"name": "run_status", "lane": "Delivery", "value": None, "health": "Green",
         "reason": None, "in_rollup": True},
        {"name": "turnaround_s", "lane": "Delivery", "value": None, "health": "Unknown",
         "reason": "not_reported", "in_rollup": True},
        {"name": "failure_rate", "lane": "Reliability", "value": 0.002, "health": "Green",
         "reason": None, "in_rollup": True},
        {"name": "volume_change", "lane": "Reliability", "value": None, "health": "Unknown",
         "reason": "no_baseline", "in_rollup": True},
        {"name": "valid_output_rate", "lane": "Output", "value": None, "health": "Unknown",
         "reason": "records_not_approved", "in_rollup": False},
    ]
    return json.dumps(base)


EVALUATION = {"evaluation_id": "0199e0a0-0000-7000-8000-000000000001",
              "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "bands_version": "core-2026-10-12",
              "metrics": metrics(), "grade": "Unknown", "delivery_grade": "Unknown"}


class FakeScores:
    def __init__(self, fail_times: int = 0) -> None:
        self.calls: list[dict] = []
        self.fail_times = fail_times

    def create(self, **kwargs):
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("down")
        self.calls.append(kwargs)


def fake_client(scores: FakeScores):
    return SimpleNamespace(api=SimpleNamespace(scores=scores))


def test_score_list():
    scores = {s["name"]: s for s in ls.scores_for(EVALUATION)}
    assert set(scores) == {"grade", "delivery_grade", "failure_rate"}
    assert scores["grade"]["value"] == "Unknown" and scores["grade"]["data_type"] == "CATEGORICAL"
    assert scores["grade"]["comment"] == "bands core-2026-10-12; unknown: volume_change=no_baseline"
    assert scores["delivery_grade"]["comment"] == (
        "bands core-2026-10-12; unknown: turnaround_s=not_reported")
    assert scores["failure_rate"] == {
        "id": ls.score_id(EVALUATION["evaluation_id"], "failure_rate"), "name": "failure_rate",
        "value": 0.002, "data_type": "NUMERIC", "comment": "Green"}


def test_comment_without_unknown():
    clean = json.dumps([{"name": "failure_rate", "lane": "Reliability", "value": 0.0,
                         "health": "Green", "reason": None, "in_rollup": True}])
    grade = next(s for s in ls.scores_for({**EVALUATION, "metrics": clean})
                 if s["name"] == "grade")
    assert grade["comment"] == "bands core-2026-10-12; unknown: none"


def test_score_ids_are_stable_and_distinct():
    first = [s["id"] for s in ls.scores_for(EVALUATION)]
    again = [s["id"] for s in ls.scores_for(EVALUATION)]
    assert first == again and len(set(first)) == len(first)
    other = ls.score_id("0199e0a0-0000-7000-8000-000000000002", "grade")
    assert other not in first


def test_send_calls_the_sync_api_with_the_trace():
    scores = FakeScores()
    ls.LangfuseScoreSender(fake_client(scores)).send(EVALUATION)
    assert {c["name"] for c in scores.calls} == {"grade", "delivery_grade", "failure_rate"}
    for call in scores.calls:
        assert call["trace_id"] == EVALUATION["trace_id"]
        assert call["id"] == ls.score_id(EVALUATION["evaluation_id"], call["name"])
        assert str(call["data_type"]) in ("CATEGORICAL", "NUMERIC")


def test_send_raises_on_failure():
    with pytest.raises(ConnectionError):
        ls.LangfuseScoreSender(fake_client(FakeScores(fail_times=1))).send(EVALUATION)


def test_make_sender_needs_host_and_keys(monkeypatch):
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "")
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-lf-x")
    assert ls.make_sender() is None
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "")
    assert ls.make_sender() is None


def test_make_sender_never_uses_the_cloud_default():
    # a fresh process without LANGFUSE_HOST: the prototype default is the cloud, but the
    # evaluator host stays empty, so no sender is made
    import os
    import subprocess
    import sys
    from pathlib import Path
    env = {k: v for k, v in os.environ.items() if k != "LANGFUSE_HOST"}
    env.update(LANGFUSE_PUBLIC_KEY="pk-lf-x", LANGFUSE_SECRET_KEY="sk-lf-x")
    code = ("from app import config; from app.adapters import langfuse_scores as ls; "
            "print(repr(config.EVALUATOR_LANGFUSE_HOST), config.LANGFUSE_HOST, ls.make_sender())")
    out = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                         env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["''", "https://cloud.langfuse.com", "None"]


def test_make_sender_builds_a_client_without_tracing(monkeypatch):
    seen = {}

    class FakeLangfuse:
        def __init__(self, **kwargs):
            seen.update(kwargs)

    import langfuse
    monkeypatch.setattr(langfuse, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-lf-x")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-lf-x")
    assert ls.make_sender() is not None
    assert seen == {"public_key": "pk-lf-x", "secret_key": "sk-lf-x",
                    "host": "http://langfuse-web:3000", "tracing_enabled": False, "timeout": 10}
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_scores.py -q`
Expected: FAIL (`ImportError`).

- [ ] **Step 3: Add the settings** in `backend/app/config.py`, after `BATCH_REGISTRY_PATH`:

```python
# Batch evaluator (S2-05). Scores go only to the self-hosted Langfuse in the raw
# LANGFUSE_HOST setting; never to the prototype default (cloud.langfuse.com).
BATCH_EVALUATOR_ENABLED = _env("BATCH_EVALUATOR_ENABLED", "true").lower() in ("1", "true", "yes")
BATCH_EVALUATOR_INTERVAL_S = float(_env("BATCH_EVALUATOR_INTERVAL_S", "30"))
EVALUATOR_LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "").strip().rstrip("/")
```

- [ ] **Step 4: Write `backend/app/adapters/langfuse_scores.py`:**

```python
"""Scores of one batch evaluation on the run's trace in self-hosted Langfuse (S2-05).

`score_id` is stable (uuid5 of the evaluation ID and the score name), so a retry makes no
duplicate. The synchronous API call raises on failure; the SDK's `create_score` queues and
never raises, so it is not used. No record text and no key is sent or logged.
"""
from __future__ import annotations

import json
import uuid

from .. import config

SCORE_NAMESPACE = uuid.UUID("6f1d3f5e-2b8a-4c1e-9d3a-5b7c2e4f8a10")
NUMERIC_SCORES = ("failure_rate", "volume_change", "turnaround_s")


def score_id(evaluation_id: str, name: str) -> str:
    return str(uuid.uuid5(SCORE_NAMESPACE, f"{evaluation_id}:{name}"))


def _comment(bands_version: str, metrics: list[dict]) -> str:
    unknown = [f"{m['name']}={m['reason']}" for m in metrics if m["health"] == "Unknown"]
    return f"bands {bands_version}; unknown: {', '.join(unknown) or 'none'}"


def scores_for(evaluation: dict) -> list[dict]:
    metrics = json.loads(evaluation["metrics"])
    bands = evaluation["bands_version"]
    delivery = [m for m in metrics if m["lane"] == "Delivery"]
    rollup = [m for m in metrics if m["lane"] != "Delivery" and m["in_rollup"]]
    out = [
        {"name": "grade", "value": evaluation["grade"], "data_type": "CATEGORICAL",
         "comment": _comment(bands, rollup)},
        {"name": "delivery_grade", "value": evaluation["delivery_grade"],
         "data_type": "CATEGORICAL", "comment": _comment(bands, delivery)},
    ]
    for m in metrics:
        if m["name"] in NUMERIC_SCORES and m["value"] is not None:
            out.append({"name": m["name"], "value": m["value"], "data_type": "NUMERIC",
                        "comment": m["health"]})
    return [{"id": score_id(evaluation["evaluation_id"], s["name"]), **s} for s in out]


class LangfuseScoreSender:
    def __init__(self, client) -> None:
        self._client = client

    def send(self, evaluation: dict) -> None:
        from langfuse.api import ScoreDataType
        for score in scores_for(evaluation):
            self._client.api.scores.create(
                name=score["name"], value=score["value"], id=score["id"],
                trace_id=evaluation["trace_id"], data_type=ScoreDataType(score["data_type"]),
                comment=score["comment"])


def make_sender() -> LangfuseScoreSender | None:
    host = config.EVALUATOR_LANGFUSE_HOST
    public_key, secret_key = config.LANGFUSE_PUBLIC_KEY, config.LANGFUSE_SECRET_KEY
    if not (host and public_key and secret_key):
        return None
    import langfuse
    client = langfuse.Langfuse(public_key=public_key, secret_key=secret_key, host=host,
                               tracing_enabled=False, timeout=10)
    return LangfuseScoreSender(client)
```

Note: the test `test_score_list` expects `scores_for` dict keys in this order: `id`, `name`, `value`, `data_type`, `comment` (dict equality ignores order, so any order passes).

- [ ] **Step 5: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_scores.py -q`
Expected: PASS.

- [ ] **Step 6: Commit** (Claude): `feat(s2-05): Langfuse score adapter and evaluator settings`

---

### Task 5: Worker, lifespan, registry rule and readiness

**Files:**
- Create: `backend/app/batch_evaluator.py`
- Modify: `backend/app/main.py`, `backend/app/registry.py` (`load`), `backend/app/api/ops_routes.py` (`readiness`)
- Modify: `backend/tests/conftest.py`, `backend/tests/test_app_surface.py` (`test_readiness_ready`), `backend/tests/test_registry.py`
- Create: `backend/tests/test_batch_evaluator.py`

**Interfaces:**
- Consumes: `batch_grading.grade_run`, `batch_grading.select_baseline`, `batch_grading.BANDS_VERSION` (Task 2); the store functions (Task 3); `langfuse_scores.make_sender`, `config.BATCH_EVALUATOR_*` (Task 4); `db.acquire_live_lease(lease_name, owner_id, ttl_seconds) -> bool`, `db.release_live_lease(lease_name, owner_id)` (existing).
- Produces:
  - `batch_evaluator.LEASE_NAME = "batch-evaluator"`, `MAX_LANGFUSE_ATTEMPTS = 20`, `BATCH = 50`
  - `class Evaluator(sender=..., now=time.time)` with `run_cycle() -> dict` (`{"lease": bool, "graded": int, "sent": int}`), `last_cycle_at: float | None`, `start()`, `async stop()`
  - `batch_evaluator.start() -> Evaluator`, `batch_evaluator.current() -> Evaluator | None`
  - `batch_evaluator.status() -> dict` (the readiness object)

- [ ] **Step 1: Turn the loop off in tests.** In `backend/tests/conftest.py`, inside the autouse fixture `batch_registry`, before `yield`, add:

```python
    monkeypatch.setattr(config, "BATCH_EVALUATOR_ENABLED", False)   # tests call run_cycle()
```

- [ ] **Step 2: Write the failing tests** in `backend/tests/test_batch_evaluator.py`:

```python
"""Batch evaluator worker (S2-05)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import batch_evaluator as be
from app import db, main, registry
from app.engines import batch_grading
from tests.test_batch_runs_api import AUTH, URL, client, example  # noqa: F401 (fixture)
from tests.test_batch_runs_store import row as run_row


def store(run_id: str, use_case_id: str = "GCP-UC-03", **body) -> dict:
    payload = {"status": "completed", "completed_at": "2026-10-06T02:12:30Z",
               "request_count": 1000, "failed_count": 0, "records": [], **body}
    stored, _ = db.put_batch_run(run_row(
        run_id=run_id, use_case_id=use_case_id, payload=json.dumps(payload),
        completed_at=payload["completed_at"], content_sha256=run_id.ljust(64, "0")[:64]))
    return stored


class FakeSender:
    def __init__(self, fail_times: int = 0) -> None:
        self.sent: list[str] = []
        self.fail_times = fail_times

    def send(self, evaluation: dict) -> None:
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("down")
        self.sent.append(evaluation["evaluation_id"])


def evaluations() -> list[dict]:
    with db.engine().begin() as cx:
        return [dict(r) for r in cx.execute(db.select(db.batch_evaluations)).mappings().all()]


def test_cycle_grades_each_run_once(isolated_db):
    store("a")
    store("b")
    worker = be.Evaluator(sender=None)
    assert worker.run_cycle() == {"lease": True, "graded": 2, "sent": 0}
    assert worker.run_cycle()["graded"] == 0
    rows = evaluations()
    assert len(rows) == 2
    assert {r["langfuse_status"] for r in rows} == {"skipped"}
    assert all(r["bands_version"] == batch_grading.BANDS_VERSION for r in rows)
    assert worker.last_cycle_at is not None


def test_evaluation_row_content(isolated_db):
    for i in range(1, 7):
        store(f"r{i}", completed_at=f"2026-10-0{i}T00:00:00Z",
              submitted_at=f"2026-10-0{i}T00:00:00Z")
    be.Evaluator(sender=None).run_cycle()
    row = next(r for r in evaluations() if r["run_id"] == "r6")
    metrics = {m["name"]: m for m in json.loads(row["metrics"])}
    assert metrics["volume_change"]["value"] == 1.0                   # 5 earlier runs
    assert metrics["turnaround_s"]["health"] == "Green"               # GCP-UC-03 limit 3600
    assert len(json.loads(row["baseline_run_ids"])) == 5
    assert row["grade"] == "Green" and row["delivery_grade"] == "Green"
    first = next(r for r in evaluations() if r["run_id"] == "r1")
    assert first["grade"] == "Unknown"                                # no_baseline


def test_stored_run_does_not_change(isolated_db):
    stored = store("a")
    be.Evaluator(sender=None).run_cycle()
    assert db.get_batch_run("GCP-UC-03", "a") == stored


def test_second_owner_waits_for_the_lease(isolated_db):
    store("a")
    first, second = be.Evaluator(sender=None), be.Evaluator(sender=None)
    assert first.run_cycle()["lease"] is True
    store("b")
    assert second.run_cycle() == {"lease": False, "graded": 0, "sent": 0}
    assert len(evaluations()) == 1


def test_same_run_twice_makes_one_row(isolated_db, monkeypatch):
    stored = store("a")
    monkeypatch.setattr(db, "runs_without_evaluation", lambda *a, **k: [stored, stored])
    assert be.Evaluator(sender=None).run_cycle()["graded"] == 1
    assert len(evaluations()) == 1


def test_one_bad_run_does_not_stop_the_others(isolated_db, monkeypatch):
    store("bad")
    store("good")
    real = batch_grading.grade_run

    def flaky(body, earlier, limit):
        if body.get("request_count") == 13:
            raise RuntimeError("boom")
        return real(body, earlier, limit)

    db_payload = json.dumps({"status": "completed", "completed_at": "2026-10-06T02:12:30Z",
                             "request_count": 13, "failed_count": 0, "records": []})
    with db.engine().begin() as cx:
        cx.execute(db.update(db.batch_runs).where(db.batch_runs.c.run_id == "bad").values(
            payload=db_payload))
    monkeypatch.setattr(be, "grade_run", flaky)
    assert be.Evaluator(sender=None).run_cycle()["graded"] == 1
    assert [r["run_id"] for r in evaluations()] == ["good"]


def test_run_of_removed_use_case_is_still_graded(isolated_db, monkeypatch):
    store("a", use_case_id="GCP-UC-99", submitted_at="2026-10-06T02:00:00Z")
    be.Evaluator(sender=None).run_cycle()
    metrics = {m["name"]: m for m in json.loads(evaluations()[0]["metrics"])}
    assert metrics["turnaround_s"]["reason"] == "not_reported"


def test_scores_are_sent_and_retried(isolated_db):
    store("a")
    sender = FakeSender(fail_times=1)
    worker = be.Evaluator(sender=sender)
    assert worker.run_cycle()["sent"] == 0
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"], row["langfuse_error"]) == (
        "pending", 1, "ConnectionError")
    assert row["grade"] == "Unknown"
    assert worker.run_cycle()["sent"] == 1
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"]) == ("sent", 2)
    assert row["grade"] == "Unknown"                                  # never changed
    assert sender.sent == [row["evaluation_id"]]


def test_twenty_failures_mark_failed(isolated_db):
    store("a")
    worker = be.Evaluator(sender=FakeSender(fail_times=1000))
    for _ in range(25):
        worker.run_cycle()
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"]) == ("failed", 20)


def test_post_does_not_grade(client):
    # `client` is the fixture of test_batch_runs_api.py (imported at the top of this file)
    body = example("01-completed-online.json")
    response = client.post(URL, json=body, headers=AUTH)
    assert response.status_code == 201, response.text
    assert evaluations() == []                       # the POST never grades inline


def test_status_without_worker(isolated_db):
    store("a")
    assert be.status() == {"enabled": False, "last_cycle_at": None,
                           "unevaluated": 1, "langfuse_pending": 0}


def test_readiness_evaluator_counts_when_database_fails(isolated_db, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(db, "evaluator_counts", broken)
    assert be.status()["unevaluated"] is None and be.status()["langfuse_pending"] is None


def test_lifespan_starts_and_stops_the_worker(isolated_db, monkeypatch):
    monkeypatch.setattr(be.config, "BATCH_EVALUATOR_ENABLED", True)
    monkeypatch.setattr(be.config, "BATCH_EVALUATOR_INTERVAL_S", 0.05)
    monkeypatch.setattr(be.langfuse_scores, "make_sender", lambda: None)
    store("a")
    import time
    with TestClient(main.app):
        deadline = time.time() + 5
        while time.time() < deadline and not evaluations():
            time.sleep(0.05)
        assert be.current() is not None
    assert len(evaluations()) == 1
    assert be.current() is None
```

Add to `backend/tests/test_registry.py`:

```python
def test_band_overrides_stop_the_load(tmp_path):
    text = GOOD + "    band_overrides: {failure_rate: {red: 0.1}}\n"
    with pytest.raises(registry.RegistryError) as exc:
        registry.load(write(tmp_path, text))
    assert "use case UC-A: band_overrides is not supported yet (S2-05)" in str(exc.value)
```

In `backend/tests/test_app_surface.py`, `test_readiness_ready`: change the expected body to:

```python
    assert response.json() == {"status": "ready", "database": {"ok": True, "error": None},
                               "batch_api_keys": 1, "use_cases": 2, "errors": [],
                               "batch_evaluator": {"enabled": False, "last_cycle_at": None,
                                                   "unevaluated": 0, "langfuse_pending": 0}}
```

- [ ] **Step 3: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_evaluator.py tests/test_registry.py tests/test_app_surface.py -q`
Expected: FAIL (`ImportError: app.batch_evaluator`).

- [ ] **Step 4: Write `backend/app/batch_evaluator.py`:**

```python
"""Batch evaluator (S2-05): grades each stored run one time, then sends the scores.

An asyncio task of the backend lifespan. Each cycle runs in a thread and needs the DB lease
`batch-evaluator`, so one instance grades also when more instances run. A cycle error is
logged by class and message and the next cycle runs normally; the API never stops. The
POST request never waits for this worker.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable

from . import config, db, ids, registry
from .adapters import langfuse_scores
from .engines.batch_grading import BANDS_VERSION, grade_run, select_baseline

log = logging.getLogger(__name__)

LEASE_NAME = "batch-evaluator"
MAX_LANGFUSE_ATTEMPTS = 20
BATCH = 50
_DEFAULT = object()
_current: "Evaluator | None" = None


class Evaluator:
    def __init__(self, sender=_DEFAULT, now: Callable[[], float] = time.time) -> None:
        self.sender = langfuse_scores.make_sender() if sender is _DEFAULT else sender
        self.now = now
        self.owner_id = f"{socket.gethostname()}:{os.getpid()}:{ids.new_id()[-12:]}"
        self.last_cycle_at: float | None = None
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    # ---------------------------------------------------------------- one cycle
    def run_cycle(self) -> dict:
        ttl = 3 * config.BATCH_EVALUATOR_INTERVAL_S
        if not db.acquire_live_lease(LEASE_NAME, self.owner_id, ttl):
            return {"lease": False, "graded": 0, "sent": 0}
        graded = 0
        for run in db.runs_without_evaluation(BANDS_VERSION, BATCH):
            try:
                graded += self._grade(run)
            except Exception as exc:  # noqa: BLE001 — one run never stops the others
                log.warning("batch evaluation failed", extra={
                    "use_case_id": run.get("use_case_id"), "run_id": run.get("run_id"),
                    "error": type(exc).__name__})
        sent = self._send_scores()
        self.last_cycle_at = self.now()
        return {"lease": True, "graded": graded, "sent": sent}

    def _grade(self, run: dict) -> int:
        body = json.loads(run["payload"])
        history = db.batch_run_history(run["use_case_id"])
        baseline = select_baseline(history, run["batch_run_id"], run["completed_at"])
        use_case = registry.current().get(run["use_case_id"])
        limit = use_case.turnaround_limit_s if use_case else None
        grade = grade_run(body, [b["request_count"] for b in baseline], limit)
        row = {
            "evaluation_id": ids.new_id(), "batch_run_id": run["batch_run_id"],
            "use_case_id": run["use_case_id"], "run_id": run["run_id"],
            "trace_id": run["trace_id"], "bands_version": grade.bands_version,
            "metrics": json.dumps([asdict(m) for m in grade.metrics]),
            "delivery_grade": grade.delivery_grade, "grade": grade.grade,
            "baseline_run_ids": json.dumps([b["batch_run_id"] for b in baseline]),
            "evaluated_at": self.now(),
            "langfuse_status": "pending" if self.sender is not None else "skipped",
            "langfuse_attempts": 0, "langfuse_error": None,
        }
        if not db.put_batch_evaluation(row):
            return 0
        log.info("batch run graded", extra={
            "use_case_id": run["use_case_id"], "run_id": run["run_id"],
            "trace_id": run["trace_id"], "grade": grade.grade,
            "delivery_grade": grade.delivery_grade})
        return 1

    def _send_scores(self) -> int:
        if self.sender is None:
            return 0
        sent = 0
        for evaluation in db.evaluations_for_langfuse(BATCH):
            try:
                self.sender.send(evaluation)
            except Exception as exc:  # noqa: BLE001 — the grade is stored; retry later
                attempts = int(evaluation["langfuse_attempts"]) + 1
                status = "failed" if attempts >= MAX_LANGFUSE_ATTEMPTS else "pending"
                db.set_langfuse_result(evaluation["evaluation_id"], status, type(exc).__name__)
                continue
            db.set_langfuse_result(evaluation["evaluation_id"], "sent", None)
            sent += 1
        return sent

    # ---------------------------------------------------------------- the loop
    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.run_cycle)
            except Exception as exc:  # noqa: BLE001 — log and try again next cycle
                log.warning("batch evaluator cycle failed", extra={"error": type(exc).__name__})
            try:
                await asyncio.wait_for(self._stop.wait(), config.BATCH_EVALUATOR_INTERVAL_S)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        self._stop = asyncio.Event()
        self._task = asyncio.get_running_loop().create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, 10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        try:
            await asyncio.to_thread(db.release_live_lease, LEASE_NAME, self.owner_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("batch evaluator lease release failed",
                        extra={"error": type(exc).__name__})


def start() -> Evaluator:
    global _current
    _current = Evaluator()
    _current.start()
    return _current


async def stop() -> None:
    global _current
    if _current is not None:
        await _current.stop()
    _current = None


def current() -> Evaluator | None:
    return _current


def status() -> dict:
    """The readiness object. No key, no body; counts are None when the DB fails."""
    worker = _current
    last = worker.last_cycle_at if worker else None
    try:
        counts = db.evaluator_counts(BANDS_VERSION)
    except Exception:  # noqa: BLE001 — readiness reports the database separately
        counts = {"unevaluated": None, "langfuse_pending": None}
    return {
        "enabled": bool(config.BATCH_EVALUATOR_ENABLED),
        "last_cycle_at": (datetime.fromtimestamp(last, timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ") if last else None),
        **counts,
    }
```

- [ ] **Step 5: Start and stop it in `backend/app/main.py`.** Add `batch_evaluator` to the import (`from . import batch_evaluator, config, db, logging_setup, registry, tracing`) and change the lifespan to:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.set_current(registry.load(config.BATCH_REGISTRY_PATH))   # error: no start
    db.engine()
    if config.BATCH_EVALUATOR_ENABLED:
        batch_evaluator.start()                                       # S2-05
    try:
        yield
    finally:
        await batch_evaluator.stop()
        tracing.shutdown()
```

Add one sentence to the module docstring: "When `BATCH_EVALUATOR_ENABLED` is true, the lifespan also runs the batch evaluator (S2-05)."

- [ ] **Step 6: Reject `band_overrides` in `backend/app/registry.py`.** In `load()`, inside the loop over `parsed.use_cases`, after the duplicate check:

```python
        if use_case.band_overrides:
            raise RegistryError(
                f"batch registry {path}: use case {use_case.use_case_id}: band_overrides is "
                "not supported yet (S2-05); remove it or wait for support")
```

- [ ] **Step 7: Add the readiness object** in `backend/app/api/ops_routes.py`: import `batch_evaluator` (`from .. import batch_evaluator, config, db, registry`) and change the body to:

```python
    body = {"status": "ready" if not errors else "not_ready", "database": database,
            "batch_api_keys": len(config.batch_api_key_hashes()),
            "use_cases": len(use_cases), "errors": errors,
            "batch_evaluator": batch_evaluator.status()}
```

- [ ] **Step 8: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_evaluator.py tests/test_registry.py tests/test_app_surface.py -q`
Expected: PASS.

- [ ] **Step 9: Run the full fast suite.**
Run: `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: all pass (the chatbot `AICT-L02` tests included). If a readiness test elsewhere compares the full body, add the `batch_evaluator` object to its expected value.

- [ ] **Step 10: Commit** (Claude): `feat(s2-05): batch evaluator worker, readiness and registry rule`

---

### Task 6: Local stack, CI checks and the test-host script

**Files:**
- Modify: `deploy/compose/compose.local.yaml` (backend service)
- Create: `deploy/compose/add-langfuse-backend-env.sh`
- Modify: `scripts/compose-smoke.sh`, `scripts/langfuse-smoke.sh`
- Modify: `.github/workflows/langfuse-smoke.yml` (paths)
- Test: `backend/tests/test_compose_files.py`, `backend/tests/test_langfuse_files.py`

**Interfaces:**
- Consumes: readiness `batch_evaluator` (Task 5); score names `grade` (Task 4).

- [ ] **Step 1: Write the failing tests.** Add to `backend/tests/test_compose_files.py`:

```python
def test_local_backend_langfuse_is_opt_in():
    env = _load("compose.local.yaml")["services"]["backend"]["environment"]
    assert env["LANGFUSE_HOST"] == "${BACKEND_LANGFUSE_HOST:-}"      # only langfuse-smoke sets it
    assert env["LANGFUSE_PUBLIC_KEY"] == "pk-lf-local-00000000-0000-0000-0000-000000000000"
    assert env["LANGFUSE_SECRET_KEY"] == "sk-lf-local-00000000-0000-0000-0000-000000000000"
    assert env["BATCH_EVALUATOR_INTERVAL_S"] == "5"


def test_add_langfuse_backend_env_script():
    text = (COMPOSE / "add-langfuse-backend-env.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n") and "\r\n" not in text
    assert "set -euo pipefail" in text
    for word in ("/opt/langfuse/langfuse.env", "/opt/model-monitor/backend.env",
                 "LANGFUSE_INIT_PROJECT_PUBLIC_KEY", "LANGFUSE_INIT_PROJECT_SECRET_KEY",
                 "LANGFUSE_HOST=http://langfuse-web:3000", "chmod 600"):
        assert word in text
    for line in text.splitlines():
        if line.lstrip().startswith(("echo", "print")):
            assert "SECRET_KEY}" not in line and "$SECRET" not in line


def test_compose_smoke_waits_for_the_evaluation():
    text = (ROOT / "scripts" / "compose-smoke.sh").read_text(encoding="utf-8")
    assert "batch_evaluator" in text and "unevaluated" in text
    assert "Unknown|Unknown|skipped" in text
```

If `ROOT` is not defined in `test_compose_files.py`, define it as `ROOT = Path(__file__).resolve().parents[2]`.

Add to `backend/tests/test_langfuse_files.py`, in `test_langfuse_smoke_script`:

```python
    assert 'export BACKEND_LANGFUSE_HOST="http://langfuse-web:3000"' in text
    assert "/api/public/v3/scores" in text and "name=grade" in text
```

and in the workflow test, assert the new paths are in the `paths` lists:

```python
    for path in ("backend/app/batch_evaluator.py", "backend/app/adapters/langfuse_scores.py"):
        assert text.count(path) == 2
```

(Put that inside the existing test that reads `WORKFLOW`.)

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_langfuse_files.py -q`
Expected: FAIL.

- [ ] **Step 3: Change `deploy/compose/compose.local.yaml`**, the backend `environment`:

```yaml
    environment:
      DATABASE_URL: postgresql://monitor:monitor@postgres:5432/monitor
      BATCH_API_KEY_SHA256: rtr-fraud-validation:ca9263478834f0d9f054e84eda1a55dee86d8a6551f27aa8a2c751a4b541b200
      BATCH_EVALUATOR_INTERVAL_S: "5"
      # Empty unless langfuse-smoke sets it: the plain smoke test has no Langfuse (skipped).
      LANGFUSE_HOST: ${BACKEND_LANGFUSE_HOST:-}
      LANGFUSE_PUBLIC_KEY: pk-lf-local-00000000-0000-0000-0000-000000000000
      LANGFUSE_SECRET_KEY: sk-lf-local-00000000-0000-0000-0000-000000000000   # local test value
```

- [ ] **Step 4: Write `deploy/compose/add-langfuse-backend-env.sh`:**

```bash
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
```

- [ ] **Step 5: Add the check to `scripts/compose-smoke.sh`**, after the `check-trace` step and before the `SMOKE PASS` line:

```bash
STEP="batch evaluation"
# S2-05: the worker grades the run within a few cycles (interval 5 s locally). No Langfuse
# here, so the score status is "skipped". The example body has no baseline and no
# submitted_at, so both grades are Unknown.
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/api/readiness" | python3 -c '
import json, sys
e = json.load(sys.stdin)["batch_evaluator"]
sys.exit(0 if e["unevaluated"] == 0 and e["last_cycle_at"] else 1)'; then
    break
  fi
  [ "$i" = "30" ] && { echo "the run was not graded in 60 s"; exit 1; }
  sleep 2
done
GRADE="$("${COMPOSE[@]}" exec -T postgres psql -U monitor -d monitor -tAc \
  "select grade, delivery_grade, langfuse_status from batch_evaluations where run_id = '$RUN_ID'")"
[ "$GRADE" = "Unknown|Unknown|skipped" ] || { echo "unexpected evaluation: $GRADE"; exit 1; }
```

Update the header comment of the script: "…then the trace check tool finds all the items, and the worker grades the run (S2-05)."

- [ ] **Step 6: Add the checks to `scripts/langfuse-smoke.sh`.**

After the `export CHECK_LANGFUSE_URL=...` line, add:

```bash
# The backend sends its scores to Langfuse only when this is set (compose.local.yaml, S2-05).
export BACKEND_LANGFUSE_HOST="http://langfuse-web:3000"
```

After the first `grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"` (before the restart step), add:

```bash
STEP="grade score in Langfuse"
AUTH="$(python3 -c 'import base64; print(base64.b64encode(b"pk-lf-local-00000000-0000-0000-0000-000000000000:sk-lf-local-00000000-0000-0000-0000-000000000000").decode())')"
for i in $(seq 1 45); do
  FOUND="$(curl -sS -H "Authorization: Basic $AUTH" \
    "http://127.0.0.1:3000/api/public/v3/scores?traceId=$TRACE_ID&name=grade" \
    | python3 -c 'import json, sys
try:
    print(len(json.load(sys.stdin).get("data", [])))
except Exception:
    print(0)')"
  [ "$FOUND" = "1" ] && break
  [ "$i" = "45" ] && { echo "no grade score on the trace after 90 s"; exit 1; }
  sleep 2
done
PENDING="$(curl -fsS http://127.0.0.1:8000/api/readiness | python3 -c 'import json, sys; print(json.load(sys.stdin)["batch_evaluator"]["langfuse_pending"])')"
[ "$PENDING" = "0" ] || { echo "langfuse_pending is $PENDING"; exit 1; }
```

- [ ] **Step 7: Add the new paths to `.github/workflows/langfuse-smoke.yml`**, to both `paths` lists (pull_request and push), after `"backend/scripts/check_trace.py"`:

```yaml
      - "backend/app/batch_evaluator.py"
      - "backend/app/adapters/langfuse_scores.py"
      - "backend/app/engines/batch_grading.py"
```

- [ ] **Step 8: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_langfuse_files.py -q`
Expected: PASS. (Do not run the scripts or Docker; CI runs them.)

- [ ] **Step 9: Commit** (Claude): `test(s2-05): smoke checks for the evaluator; test-host env script`

---

### Task 7: Docs

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`

- [ ] **Step 1: TESTHOST — fix the S2-03 section.**
  - In "Langfuse (S2-03)", replace the two broken arrows: `APIs & Services ? Credentials ? OAuth client ID` → `APIs & Services → Credentials → OAuth client ID`, and `Settings ? Members` → `Settings → Members`.
  - Before step 8 ("reload the Collector exporter"), add a step: "On the VM, set `BACKEND_IMAGE` in `/opt/model-monitor/compose/.env` to the build that contains S2-03 (`backend:14` or later), then run `sudo docker compose -f compose.yaml -f compose.testhost.yaml pull`." Renumber the steps after it.
  - In the tunnel step, add: "Or, when you connect to the VM with VS Code Remote-SSH, forward port 3000 in the **Ports** panel. The local port must be 3000."

- [ ] **Step 2: TESTHOST — add the section "Batch evaluator (S2-05)"** after the Langfuse section:

```markdown
## Batch evaluator (S2-05)

1. Copy `deploy/compose/add-langfuse-backend-env.sh` to `/opt/model-monitor/compose/`.
2. On the VM, give the backend the Langfuse keys. Expect `600 root` and `BACKEND LANGFUSE ENV DONE`.

   ```sh
   sudo bash /opt/model-monitor/compose/add-langfuse-backend-env.sh
   ```

3. Set `BACKEND_IMAGE` in `/opt/model-monitor/compose/.env` to the build that contains
   S2-05, then from `/opt/model-monitor/compose`:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml pull && sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

4. Check readiness. `batch_evaluator.unevaluated` and `langfuse_pending` must be `0`
   after one or two minutes.

   ```sh
   curl -s http://127.0.0.1:8000/api/readiness
   ```

5. In Langfuse, open the trace of the latest RTR run. It must show the `grade` and
   `delivery_grade` scores.
```

- [ ] **Step 3: CHANGELOG** — under "Unreleased" / "Added", first item:

```markdown
- Batch evaluator (S2-05): a worker in the backend grades each stored run one time with the
  core metrics (`run_status`, `turnaround_s`, `failure_rate`, `volume_change`; bands
  `core-2026-10-12`, RAI approved), stores the result in `batch_evaluations` and sends the
  scores to the run's trace in Langfuse. Readiness shows `batch_evaluator`. The IDs of the
  MVP tables are uuid7 (`uuid-utils`); a migration changes the existing `batch_run_id`s.
```

- [ ] **Step 4: DEVLOG** — add at the top of "Work log" (use the em dash `—`, not `?`):

```markdown
### 2026-10-14 — S2-05: batch evaluator

- Built (Codex from `changes/2026-10-14-s2-05-batch-evaluator/plan.md`, reviewed by
  Claude): `engines/batch_grading.py`, `batch_evaluator.py` (lease `batch-evaluator`),
  `adapters/langfuse_scores.py`, table `batch_evaluations` (migrations 9 and 10), uuid7 IDs
  (`ids.py`, `uuid-utils`), readiness `batch_evaluator`, smoke checks,
  `add-langfuse-backend-env.sh`.
- Decisions: run status in S2-05, missing-run check in S3-02; `no_baseline` stays in the
  rollup; two grades; `band_overrides` stops the start; uuid7 for the MVP tables.
- Evidence: (Claude fills in after the review).
```

- [ ] **Step 5: issues.md** — at the end of the S2-05 section's "Changed 2026-10-09" paragraph, add:

```markdown
**Design 2026-10-14:** `changes/2026-10-14-s2-05-batch-evaluator/` (intent, spec, plan).
RAI approved the core bands (`core-2026-10-12`). "Run on time" is split: the run status
is graded here; the missing-run check stays in S3-02.
```

- [ ] **Step 6: Run the docs tests.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `docs(s2-05): evaluator runbook, changelog and devlog`
