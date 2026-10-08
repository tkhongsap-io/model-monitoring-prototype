# Trace check tool (S1-07) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `deploy/compose/check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]` prints found / missing / skipped for the run row, the monitor span, the GCP root span and the ancestor link of one trace, and exits `0`, `1` or `2`, on the local stack and on the test host.

**Architecture:** Pure check logic in `backend/app/trace_check.py`; I/O (arguments, span file, read-only database, output, exit code) in `backend/scripts/check_trace.py`. It runs as a one-shot Compose service `trace-check` (profile `tools`) with the backend image, the span volume mounted read-only, and `CHECK_DATABASE_URL` from the host. A bash wrapper selects the Compose files. The CI smoke test uses the wrapper.

**Tech Stack:** Python 3.12, SQLAlchemy 2 + psycopg 3 (already installed), pytest, PyYAML (already installed), Docker Compose v2, bash.

**Spec:** [spec.md](spec.md) (approved 2026-10-08). Intent: [intent.md](intent.md).

## Global Constraints

- No new pip or npm package. No new API route. No change to `backend/app/main.py`.
- The tool reads only `CHECK_DATABASE_URL`. It never reads `DATABASE_URL` and never calls `db.engine()` (that runs the migrations).
- The tool never selects `batch_runs.payload` and never prints a span attribute other than `outcome`, `use_case_id`, `run_id`, `stored_trace_id`, and the span names, IDs and times.
- The tool never prints the database URL, a password, an exception message or a traceback. A database error prints only `error: cannot read the database (<ExceptionClassName>)`.
- Exit codes: `0` all checked items found; `1` an item missing; `2` usage or setup error.
- Default span file: `/otel/spans.jsonl`. Poll interval for `--wait`: 2 seconds.
- Test-host values: Cloud SQL private IP `10.188.112.8`, database `monitor`, user `monitor_readonly`, password file `/opt/model-monitor/secrets/monitor-readonly.password`, env file `/opt/model-monitor/check.env` (mode 600, root), CA file `/etc/model-monitor/cloudsql-server-ca.pem` in the container.
- Shell scripts: start with `#!/usr/bin/env bash`, have `set -euo pipefail`, use LF line endings (`.gitattributes` already forces LF for `*.sh`).
- Tests run from `backend/`: `.venv\Scripts\python.exe -m pytest ...` on Windows, `.venv/bin/python -m pytest ...` elsewhere.
- Docker and bash are not available on the Windows development computer: never claim the stack or a shell script ran there. The CI smoke test is the stack proof.
- **Codex: do not run `git commit`** (the sandbox cannot write the git index). Leave the changes in the working tree; Claude reviews and commits each task.

## Review Focus

- A database URL with a password must never reach stdout or stderr, also when the connection fails. (Task 3, `test_password_never_printed_on_connection_error`.)
- A half-written last line in the span file (the Collector is writing) must not crash the tool or drop the spans of the good lines. (Task 3, `test_broken_lines_are_skipped_and_counted`.)
- An upper-case trace ID pasted from a log must work; a 31-character or all-zero ID must be a usage error. (Task 3, `test_trace_id_rules`.)
- A parent-link loop in bad span data must not hang the tool. (Task 2, `test_chain_loop_does_not_hang`.)
- `DATABASE_URL` set without `CHECK_DATABASE_URL` must fail with exit 2, not fall back to the write user. (Task 3, `test_database_url_is_never_used`.)

---

## File structure

| File | Task | Responsibility |
|---|---|---|
| `backend/app/db.py` | 1 | `driver_url(url)` shared by `engine()` and the tool |
| `backend/tests/test_db_driver_url.py` | 1 | Test of `driver_url` |
| `backend/app/trace_check.py` | 2 | Pure check logic and text output |
| `backend/tests/test_trace_check.py` | 2 | Tests of the check logic |
| `backend/scripts/check_trace.py` | 3 | The command: arguments, span file, database, exit code |
| `backend/tests/test_check_trace_script.py` | 3 | Tests of the command |
| `deploy/compose/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml` | 4 | The `trace-check` service |
| `deploy/compose/check-trace.sh`, `make-check-env.sh`, `check.env.example` | 4 | Wrapper, test-host setup, template |
| `scripts/compose-smoke.sh` | 4 | Smoke test uses the wrapper |
| `backend/tests/test_compose_files.py` | 4 | Static checks |
| `deploy/compose/TESTHOST.md`, `deploy/compose/README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md` | 5 | Docs |

---

### Task 1: `db.driver_url`

**Files:**
- Modify: `backend/app/db.py` (function `engine()`, about lines 336–356)
- Test: `backend/tests/test_db_driver_url.py`

**Interfaces:**
- Produces: `db.driver_url(url: str) -> str`

- [ ] **Step 1: Write the failing test** — `backend/tests/test_db_driver_url.py`:

```python
"""S1-07: the driver URL rule is shared by the backend and the trace check tool."""
from app import db


def test_postgres_urls_select_psycopg3():
    assert db.driver_url("postgres://u:p@h:5432/d") == "postgresql+psycopg://u:p@h:5432/d"
    assert db.driver_url("postgresql://u:p@h/d?sslmode=verify-ca") == \
        "postgresql+psycopg://u:p@h/d?sslmode=verify-ca"


def test_other_urls_do_not_change():
    assert db.driver_url("postgresql+psycopg://u@h/d") == "postgresql+psycopg://u@h/d"
    assert db.driver_url("sqlite:///x.db") == "sqlite:///x.db"
```

- [ ] **Step 2: Run it and make sure it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_db_driver_url.py -q`
Expected: FAIL, `AttributeError: module 'app.db' has no attribute 'driver_url'`

- [ ] **Step 3: Implement** — in `backend/app/db.py`, add above `def engine():`

```python
def driver_url(url: str) -> str:
    """Select psycopg v3 for postgres:// and postgresql:// URLs.

    Replit/managed providers commonly emit postgres:// or postgresql://; deployments must
    not depend on legacy psycopg2. Used by engine() and by scripts/check_trace.py (S1-07).
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url
```

and in `engine()` replace the comment and the `if url.startswith("postgres://") ... elif ...` block with:

```python
        url = driver_url(url)
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_db_driver_url.py -q -m "not slow"` then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: PASS (no behaviour change for the backend)

- [ ] **Step 5: Stop for review** (Claude commits `refactor(db): share driver_url with the trace check tool (S1-07)`)

---

### Task 2: the check logic (`app/trace_check.py`)

**Files:**
- Create: `backend/app/trace_check.py`
- Test: `backend/tests/test_trace_check.py`

**Interfaces:**
- Produces (used by Task 3):
  - `FOUND = "found"`, `MISSING = "missing"`, `SKIPPED = "skipped"`
  - `Span(trace_id: str, span_id: str, parent_span_id: str, name: str, start_ns: int, attributes: dict[str, Any])` (frozen dataclass)
  - `RunRow(use_case_id: str, run_id: str, status: str, completed_at: str, received_at: float, trace_id_source: str)` (frozen dataclass)
  - `Item(name: str, state: str, detail: str = "")`, `Result(trace_id: str, items: tuple[Item, ...], skipped_lines: int = 0)` with properties `checked: list[Item]` and `ok: bool`
  - `stored_trace_ids(spans: list[Span]) -> list[str]`
  - `check(trace_id: str, rows: list[RunRow], spans: list[Span], *, backend_only: bool, stored_rows: dict[str, list[RunRow]] | None = None, skipped_lines: int = 0) -> Result`
  - `render(result: Result) -> str`

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_trace_check.py`:

```python
"""S1-07: the pure check logic of the trace check tool."""
from __future__ import annotations

from app.trace_check import (FOUND, MISSING, SKIPPED, RunRow, Span, check, render,
                             stored_trace_ids)

T = "4bf92f3577b34da6a3ce929d0e0e4736"
OTHER = "0af7651916cd43dd8448eb211c80319c"
NS = 1_791_442_803_000_000_000          # 2026-10-08T07:00:03Z


def span(name, span_id, parent="", **attributes):
    return Span(trace_id=T, span_id=span_id, parent_span_id=parent, name=name,
                start_ns=NS, attributes=attributes)


def row(trace_source="traceparent"):
    return RunRow(use_case_id="rtr-fraud-validation", run_id="run-20261008-01",
                  status="succeeded", completed_at="2026-10-08T06:59:00Z",
                  received_at=NS / 1e9, trace_id_source=trace_source)


def full_trace():
    return [
        span("batch.run", "a1", "", use_case_id="rtr-fraud-validation", run_id="run-20261008-01"),
        span("batch.send", "a2", "a1"),
        span("POST", "a3", "a2"),
        span("POST /api/batch/runs", "b1", "a3"),
        span("monitor.ingest", "b2", "b1", outcome="stored"),
    ]


def states(result):
    return {item.name: item.state for item in result.items}


def detail(result, name):
    return next(item.detail for item in result.items if item.name == name)


def test_all_four_found_with_the_path():
    result = check(T, [row()], full_trace(), backend_only=False)
    assert states(result) == {"run row": FOUND, "monitor span": FOUND,
                              "gcp root span": FOUND, "ancestor link": FOUND}
    assert result.ok
    assert detail(result, "ancestor link") == \
        "monitor.ingest → POST /api/batch/runs → POST → batch.send"
    assert "rtr-fraud-validation / run-20261008-01" in detail(result, "run row")
    assert "received 2026-10-08T07:00:03Z" in detail(result, "run row")


def test_each_item_missing_alone():
    spans = full_trace()
    no_root = [s for s in spans if s.name != "batch.run"]
    assert states(check(T, [row()], no_root, backend_only=False))["gcp root span"] == MISSING
    no_row = check(T, [], spans, backend_only=False)
    assert states(no_row)["run row"] == MISSING
    assert detail(no_row, "run row") == \
        "monitor.ingest says stored, but no run row has this trace ID"
    no_ingest = [s for s in spans if s.name != "monitor.ingest"]
    result = check(T, [row()], no_ingest, backend_only=False)
    assert states(result)["monitor span"] == MISSING
    assert detail(result, "ancestor link") == "no monitor.ingest span"
    assert not result.ok


def test_duplicate_found_only_when_the_stored_row_exists():
    spans = [span("monitor.ingest", "b2", "b1", outcome="duplicate", stored_trace_id=OTHER)]
    assert stored_trace_ids(spans) == [OTHER]
    found = check(T, [], spans, backend_only=True, stored_rows={OTHER: [row()]})
    assert states(found)["run row"] == FOUND
    assert detail(found, "run row") == f"duplicate delivery; the run is stored under trace {OTHER}"
    missing = check(T, [], spans, backend_only=True, stored_rows={})
    assert states(missing)["run row"] == MISSING
    assert detail(missing, "run row") == f"duplicate delivery, but trace {OTHER} has no run row"


def test_conflict_is_missing_with_and_without_stored_trace_id():
    with_id = [span("monitor.ingest", "b2", "", outcome="conflict", stored_trace_id=OTHER)]
    result = check(T, [], with_id, backend_only=True)
    assert states(result)["run row"] == MISSING
    assert detail(result, "run row") == \
        f"rejected: another body is stored for this run_id under trace {OTHER}"
    without = [span("monitor.ingest", "b2", "", outcome="conflict")]
    assert detail(check(T, [], without, backend_only=True), "run row") == \
        "rejected: another body is stored for this run_id"


def test_other_outcome_is_missing_with_the_outcome():
    spans = [span("monitor.ingest", "b2", "", outcome="invalid")]
    result = check(T, [], spans, backend_only=True)
    assert detail(result, "run row") == "the backend did not store the run (outcome invalid)"


def test_chain_stops_at_a_missing_parent_or_a_root():
    spans = [span("POST /api/batch/runs", "b1", "ffffffffffffffff"),
             span("monitor.ingest", "b2", "b1", outcome="stored")]
    result = check(T, [row()], spans, backend_only=False)
    assert detail(result, "ancestor link") == \
        "the chain stops at POST /api/batch/runs: parent ffffffffffffffff is not in the file"
    rootless = [span("monitor.ingest", "b2", "", outcome="stored")]
    assert detail(check(T, [row()], rootless, backend_only=False), "ancestor link") == \
        "the chain stops at monitor.ingest: it has no parent"


def test_chain_loop_does_not_hang():
    spans = [span("x", "c1", "c2"), span("y", "c2", "c1"),
             span("monitor.ingest", "b2", "c1", outcome="stored")]
    result = check(T, [row()], spans, backend_only=False)
    assert states(result)["ancestor link"] == MISSING
    assert detail(result, "ancestor link").startswith("the chain stops at ")


def test_retry_two_ingest_spans_one_chain_reaches_batch_send():
    spans = full_trace() + [span("monitor.ingest", "b9", "zz", outcome="duplicate",
                                 stored_trace_id=T)]
    result = check(T, [row()], spans, backend_only=False)
    assert states(result)["ancestor link"] == FOUND
    assert detail(result, "monitor span").count("outcome ") == 2


def test_backend_only_skips_the_gcp_items():
    result = check(T, [row()], full_trace(), backend_only=True)
    assert states(result)["gcp root span"] == SKIPPED
    assert states(result)["ancestor link"] == SKIPPED
    assert len(result.checked) == 2 and result.ok


def test_render_result_line_note_and_no_other_attributes():
    spans = full_trace()
    spans[-1] = span("monitor.ingest", "b2", "b1", outcome="stored",
                     **{"http.request.header.authorization": "Bearer SECRET"})
    text = render(check(T, [row()], spans, backend_only=True, skipped_lines=3))
    lines = text.splitlines()
    assert lines[0] == f"trace {T}"
    assert lines[-2] == "note: 3 span file line(s) could not be read"
    assert lines[-1] == "RESULT: OK (2 of 2 found)"
    assert "SECRET" not in text
    missing = render(check(T, [], [], backend_only=False))
    assert missing.splitlines()[-1] == "RESULT: MISSING (0 of 4 found)"
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trace_check.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.trace_check'`

- [ ] **Step 3: Implement** — `backend/app/trace_check.py`:

```python
"""S1-07: the check logic of the trace check tool. Pure: no I/O, no database, no files.

`scripts/check_trace.py` reads the run rows and the spans of one trace and prints
`render(check(...))`. The output contains only IDs, span names, outcomes, status values and
times, never other span attributes or body content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

FOUND, MISSING, SKIPPED = "found", "missing", "skipped"
INGEST, SEND, ROOT = "monitor.ingest", "batch.send", "batch.run"


@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    start_ns: int
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunRow:
    use_case_id: str
    run_id: str
    status: str
    completed_at: str
    received_at: float
    trace_id_source: str


@dataclass(frozen=True)
class Item:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True)
class Result:
    trace_id: str
    items: tuple[Item, ...]
    skipped_lines: int = 0

    @property
    def checked(self) -> list[Item]:
        return [item for item in self.items if item.state != SKIPPED]

    @property
    def ok(self) -> bool:
        return all(item.state == FOUND for item in self.checked)


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ingests(spans: list[Span]) -> list[Span]:
    return sorted((s for s in spans if s.name == INGEST), key=lambda s: s.start_ns)


def stored_trace_ids(spans: list[Span]) -> list[str]:
    """The stored trace IDs of duplicate deliveries, in time order, without repeats."""
    ids: list[str] = []
    for s in _ingests(spans):
        stored = s.attributes.get("stored_trace_id")
        if s.attributes.get("outcome") == "duplicate" and stored and str(stored) not in ids:
            ids.append(str(stored))
    return ids


def _run_row(rows: list[RunRow], spans: list[Span],
             stored_rows: dict[str, list[RunRow]]) -> Item:
    name = "run row"
    if rows:
        return Item(name, FOUND, "; ".join(
            f"{r.use_case_id} / {r.run_id}, status {r.status}, received {_iso(r.received_at)}, "
            f"trace_id_source {r.trace_id_source}" for r in rows))
    ingests = _ingests(spans)
    for s in ingests:
        stored = s.attributes.get("stored_trace_id")
        if s.attributes.get("outcome") == "duplicate" and stored:
            if stored_rows.get(str(stored)):
                return Item(name, FOUND,
                            f"duplicate delivery; the run is stored under trace {stored}")
            return Item(name, MISSING, f"duplicate delivery, but trace {stored} has no run row")
    for s in ingests:
        if s.attributes.get("outcome") == "conflict":
            stored = s.attributes.get("stored_trace_id")
            suffix = f" under trace {stored}" if stored else ""
            return Item(name, MISSING,
                        f"rejected: another body is stored for this run_id{suffix}")
    for s in ingests:
        outcome = s.attributes.get("outcome")
        if outcome == "stored":
            return Item(name, MISSING,
                        "monitor.ingest says stored, but no run row has this trace ID")
        if outcome:
            return Item(name, MISSING, f"the backend did not store the run (outcome {outcome})")
    return Item(name, MISSING)


def _monitor_span(spans: list[Span]) -> Item:
    ingests = _ingests(spans)
    if not ingests:
        return Item("monitor span", MISSING)
    return Item("monitor span", FOUND, "; ".join(
        f"outcome {s.attributes.get('outcome', 'unknown')}, {_iso(s.start_ns / 1e9)}"
        for s in ingests))


def _root_span(spans: list[Span]) -> Item:
    roots = sorted((s for s in spans if s.name == ROOT), key=lambda s: s.start_ns)
    if not roots:
        return Item("gcp root span", MISSING)
    parts = []
    for s in roots:
        ident = " / ".join(str(s.attributes[k]) for k in ("use_case_id", "run_id")
                           if s.attributes.get(k))
        parts.append(f"{ident + ', ' if ident else ''}{_iso(s.start_ns / 1e9)}")
    return Item("gcp root span", FOUND, "; ".join(parts))


def _chain(start: Span, by_id: dict[str, Span]) -> tuple[bool, str]:
    names, seen, current = [start.name], {start.span_id}, start
    while True:
        parent = current.parent_span_id
        if not parent:
            return False, f"the chain stops at {current.name}: it has no parent"
        if parent in seen:
            return False, f"the chain stops at {current.name}: the parent links make a loop"
        nxt = by_id.get(parent)
        if nxt is None:
            return False, f"the chain stops at {current.name}: parent {parent} is not in the file"
        names.append(nxt.name)
        seen.add(parent)
        current = nxt
        if nxt.name == SEND:
            return True, " → ".join(names)


def _ancestor_link(spans: list[Span]) -> Item:
    ingests = _ingests(spans)
    if not ingests:
        return Item("ancestor link", MISSING, "no monitor.ingest span")
    by_id = {s.span_id: s for s in spans}
    first_failure = ""
    for s in ingests:
        reached, text = _chain(s, by_id)
        if reached:
            return Item("ancestor link", FOUND, text)
        first_failure = first_failure or text
    return Item("ancestor link", MISSING, first_failure)


def check(trace_id: str, rows: list[RunRow], spans: list[Span], *, backend_only: bool,
          stored_rows: dict[str, list[RunRow]] | None = None, skipped_lines: int = 0) -> Result:
    items = [_run_row(rows, spans, stored_rows or {}), _monitor_span(spans)]
    if backend_only:
        items += [Item("gcp root span", SKIPPED), Item("ancestor link", SKIPPED)]
    else:
        items += [_root_span(spans), _ancestor_link(spans)]
    return Result(trace_id=trace_id, items=tuple(items), skipped_lines=skipped_lines)


def render(result: Result) -> str:
    lines = [f"trace {result.trace_id}"]
    lines += [f"{item.name:<15}{item.state:<9}{item.detail}".rstrip() for item in result.items]
    if result.skipped_lines:
        lines.append(f"note: {result.skipped_lines} span file line(s) could not be read")
    found = sum(1 for item in result.checked if item.state == FOUND)
    word = "OK" if result.ok else "MISSING"
    lines.append(f"RESULT: {word} ({found} of {len(result.checked)} found)")
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trace_check.py -q`
Expected: PASS (10 tests)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s1-07): trace check logic`)

---

### Task 3: the command (`scripts/check_trace.py`)

**Files:**
- Create: `backend/scripts/check_trace.py`
- Test: `backend/tests/test_check_trace_script.py`

**Interfaces:**
- Consumes: Task 1 `db.driver_url`, `db.batch_runs`, `db.metadata`; Task 2 `Span`, `RunRow`, `check`, `render`, `stored_trace_ids`
- Produces (used by Task 4): command line `python scripts/check_trace.py <trace_id> [--backend-only] [--wait SECONDS] [--spans-file PATH]`; `main(argv=None, *, sleep=time.sleep, clock=time.monotonic) -> int`

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_check_trace_script.py`:

```python
"""S1-07: the trace check command (span file, read-only database, exit codes)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert

from app import db

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_trace.py"
spec = importlib.util.spec_from_file_location("check_trace", SCRIPT)
check_trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_trace)

T = "4bf92f3577b34da6a3ce929d0e0e4736"
NS = "1791442803000000000"


def otlp_line(*spans):
    return json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": list(spans)}]}]})


def raw_span(name, span_id, parent="", trace=T, **attributes):
    return {"traceId": trace, "spanId": span_id, "parentSpanId": parent, "name": name,
            "startTimeUnixNano": NS,
            "attributes": [{"key": k, "value": {"stringValue": v}} for k, v in attributes.items()]}


@pytest.fixture()
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'check.db'}"
    engine = create_engine(url)
    db.batch_runs.create(engine)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CHECK_DATABASE_URL", url)
    return engine


def add_row(engine, trace_id=T, run_id="run-1"):
    with engine.begin() as cx:
        cx.execute(insert(db.batch_runs), {
            "use_case_id": "rtr-fraud-validation", "run_id": run_id, "schema_version": "1",
            "status": "succeeded", "completed_at": "2026-10-08T06:59:00Z", "request_count": 1,
            "failed_count": 0, "model": "m", "sample_method": "all", "sample_size": 1,
            "records_reason": "records_not_approved", "record_count": 0,
            "content_sha256": "0" * 64, "payload": "{}", "trace_id": trace_id,
            "trace_id_source": "traceparent", "received_at": 1791442803.0})


def spans_file(tmp_path, *lines):
    path = tmp_path / "spans.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def run(argv, **kwargs):
    return check_trace.main(argv, **kwargs)


def test_exit_0_when_backend_items_are_found(database, tmp_path, capsys):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", "b1", outcome="stored")))
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "RESULT: OK (2 of 2 found)"


def test_exit_1_when_an_item_is_missing(database, tmp_path, capsys):
    path = spans_file(tmp_path, otlp_line(raw_span("other", "c1", trace="1" * 32)))
    assert run([T, "--spans-file", path]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "RESULT: MISSING (0 of 4 found)"


def test_upper_case_trace_id_is_accepted(database, tmp_path):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    assert run([T.upper(), "--backend-only", "--spans-file", path]) == 0


@pytest.mark.parametrize("bad", [T[:-1], "g" * 32, "0" * 32, T + "0"])
def test_trace_id_rules(database, tmp_path, bad):
    path = spans_file(tmp_path, "")
    with pytest.raises(SystemExit) as exc:
        run([bad, "--spans-file", path])
    assert exc.value.code == 2


def test_no_check_database_url_is_exit_2(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("CHECK_DATABASE_URL", raising=False)
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    assert "CHECK_DATABASE_URL" in capsys.readouterr().err


def test_database_url_is_never_used(monkeypatch, tmp_path):
    monkeypatch.delenv("CHECK_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'write.db'}")
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    assert not (tmp_path / "write.db").exists()


def test_no_span_file_is_exit_2(database, tmp_path, capsys):
    assert run([T, "--spans-file", str(tmp_path / "absent.jsonl")]) == 2
    captured = capsys.readouterr()
    assert "span file" in captured.err and "RESULT" not in captured.out


def test_broken_lines_are_skipped_and_counted(database, tmp_path, capsys):
    add_row(database)
    good = otlp_line(raw_span("monitor.ingest", "b2", outcome="stored"))
    path = spans_file(tmp_path, "{not json", good, '{"resourceSpans": 5}', '{"resourceSpans": [{"scopeSp')
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    out = capsys.readouterr().out
    assert "note: 3 span file line(s) could not be read" in out


def test_duplicate_reads_the_stored_row(database, tmp_path, capsys):
    other = "0af7651916cd43dd8448eb211c80319c"
    add_row(database, trace_id=other)
    path = spans_file(tmp_path, otlp_line(raw_span(
        "monitor.ingest", "b2", outcome="duplicate", stored_trace_id=other)))
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    assert f"stored under trace {other}" in capsys.readouterr().out


def test_password_never_printed_on_connection_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CHECK_DATABASE_URL",
                       "postgresql://monitor_readonly:S3cretPw-Kq7@127.0.0.1:1/monitor?connect_timeout=2")
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    captured = capsys.readouterr()
    assert "S3cretPw" not in captured.out + captured.err
    assert "127.0.0.1" not in captured.err
    assert captured.err.startswith("error: cannot read the database (")


def test_wait_finds_a_span_written_during_the_wait(database, tmp_path):
    add_row(database)
    path = spans_file(tmp_path, "")
    now = [0.0]

    def fake_sleep(seconds):
        now[0] += seconds
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")) + "\n")

    assert run([T, "--backend-only", "--wait", "10", "--spans-file", path],
               sleep=fake_sleep, clock=lambda: now[0]) == 0


def test_wait_ends_with_exit_1(database, tmp_path):
    now = [0.0]

    def fake_sleep(seconds):
        now[0] += seconds

    path = spans_file(tmp_path, "")
    assert run([T, "--wait", "5", "--spans-file", path],
               sleep=fake_sleep, clock=lambda: now[0]) == 1
    assert now[0] >= 5
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_check_trace_script.py -q`
Expected: FAIL (`FileNotFoundError` for `scripts/check_trace.py` at import)

- [ ] **Step 3: Implement** — `backend/scripts/check_trace.py`:

```python
"""S1-07: trace check tool. Shows if one batch run arrived completely.

Run it through deploy/compose/check-trace.sh (the Compose service `trace-check`):
    check_trace.py <trace_id> [--backend-only] [--wait SECONDS] [--spans-file PATH]
Reads only CHECK_DATABASE_URL (the read-only user), never DATABASE_URL, and never runs the
migrations. Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app import db  # noqa: E402
from app.trace_check import Result, RunRow, Span, check, render, stored_trace_ids  # noqa: E402

TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
POLL_SECONDS = 2.0
COLUMNS = ("use_case_id", "run_id", "status", "completed_at", "received_at", "trace_id_source")


class SetupError(Exception):
    """A setup problem: the message is safe to print (no URL, no secret)."""


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_trace.py", description="Check that one batch run arrived completely (S1-07).")
    parser.add_argument("trace_id", help="32 hex characters")
    parser.add_argument("--backend-only", action="store_true",
                        help="check only the run row and the monitor span")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="check again every 2 seconds until all items are found")
    parser.add_argument("--spans-file", default="/otel/spans.jsonl", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.trace_id = args.trace_id.lower()
    if not TRACE_ID.match(args.trace_id) or set(args.trace_id) == {"0"}:
        parser.error("trace_id must be 32 hex characters and not all zeros")
    if args.wait < 0:
        parser.error("--wait must be 0 or more")
    return args


def _value(value: dict[str, Any]) -> Any:
    for key in ("stringValue", "boolValue", "doubleValue"):
        if key in value:
            return value[key]
    if "intValue" in value:
        return int(value["intValue"])          # OTLP JSON writes int64 as a string
    return None


def read_spans(path: str, trace_id: str) -> tuple[list[Span], int]:
    """The spans of one trace, and the number of lines that could not be read."""
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        raise SetupError(f"span file {path} not found") from None
    spans: list[Span] = []
    skipped = 0
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                found = []
                for resource in json.loads(line).get("resourceSpans", []):
                    for scope in resource.get("scopeSpans", []):
                        for raw in scope.get("spans", []):
                            if str(raw.get("traceId", "")).lower() != trace_id:
                                continue
                            found.append(Span(
                                trace_id=trace_id,
                                span_id=str(raw.get("spanId", "")).lower(),
                                parent_span_id=str(raw.get("parentSpanId") or "").lower(),
                                name=str(raw.get("name", "")),
                                start_ns=int(raw.get("startTimeUnixNano") or 0),
                                attributes={a["key"]: _value(a.get("value", {}))
                                            for a in raw.get("attributes", [])}))
            except (ValueError, TypeError, AttributeError, KeyError):
                skipped += 1
                continue
            spans.extend(found)
    return spans, skipped


def make_engine(url: str) -> Engine:
    url = db.driver_url(url)
    kwargs: dict[str, Any] = {"future": True}
    if url.startswith("postgresql"):
        kwargs["connect_args"] = {"options": "-c default_transaction_read_only=on"}
    return create_engine(url, **kwargs)


def read_rows(engine: Engine, trace_id: str) -> list[RunRow]:
    table = db.batch_runs
    stmt = (select(*(table.c[name] for name in COLUMNS))
            .where(table.c.trace_id == trace_id).order_by(table.c.received_at))
    with engine.connect() as cx:
        return [RunRow(**dict(row)) for row in cx.execute(stmt).mappings()]


def run_once(engine: Engine, args: argparse.Namespace) -> Result:
    spans, skipped = read_spans(args.spans_file, args.trace_id)
    rows = read_rows(engine, args.trace_id)
    stored = {} if rows else {tid: read_rows(engine, tid) for tid in stored_trace_ids(spans)}
    return check(args.trace_id, rows, spans, backend_only=args.backend_only,
                 stored_rows=stored, skipped_lines=skipped)


def main(argv: list[str] | None = None, *, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic) -> int:
    args = parse_args(argv)
    url = os.environ.get("CHECK_DATABASE_URL", "").strip()
    if not url:
        print("error: CHECK_DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        engine = make_engine(url)
        deadline = clock() + args.wait
        while True:
            result = run_once(engine, args)
            if result.ok or clock() >= deadline:
                break
            sleep(POLL_SECONDS)
    except SetupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (SQLAlchemyError, ValueError) as exc:
        # never the message: it can contain the URL
        print(f"error: cannot read the database ({type(exc).__name__})", file=sys.stderr)
        return 2
    print(render(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_check_trace_script.py tests/test_trace_check.py -q`
Expected: PASS. If `test_password_never_printed_on_connection_error` takes more than a few seconds on Windows, that is the TCP retry to port 1; it must still pass.

- [ ] **Step 5: Stop for review** (Claude commits `feat(s1-07): trace check command`)

---

### Task 4: Compose service, wrapper, test-host setup, smoke test

**Files:**
- Modify: `deploy/compose/compose.yaml`, `deploy/compose/compose.local.yaml`, `deploy/compose/compose.testhost.yaml`, `scripts/compose-smoke.sh`
- Create: `deploy/compose/check-trace.sh`, `deploy/compose/make-check-env.sh`, `deploy/compose/check.env.example`
- Test: `backend/tests/test_compose_files.py`

**Interfaces:**
- Consumes: Task 3 command line
- Produces: `deploy/compose/check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]`

- [ ] **Step 1: Update the static tests** — in `backend/tests/test_compose_files.py`:

Replace in `test_base_file_has_no_local_settings`:

```python
    assert set(base) == {"backend", "collector", "collector-init", "trace-check"}
```

Replace in `test_smoke_script_cleans_up_and_fails_fast` the two lines

```python
    assert "monitor.ingest" in text and "docker compose" in text and " cp " in text
    assert "collector:/data/spans.jsonl" in text and "/tmp/spans.jsonl" not in text
```

with

```python
    assert "docker compose" in text and "/tmp/spans.jsonl" not in text
    # the span check is the S1-07 tool, not an inline copy
    assert 'check-trace.sh" "$TRACE_ID" --backend-only --wait 30' in text
    assert " cp " not in text and "resourceSpans" not in text
```

Replace in `test_testhost_file_uses_registry_image_and_host_secrets` the first assertion with

```python
    assert set(host) == {"backend", "trace-check"}      # no database on the VM (Cloud SQL)
```

Append:

```python
def test_trace_check_service_is_a_read_only_tool():
    base = _load("compose.yaml")["services"]["trace-check"]
    assert base["profiles"] == ["tools"]
    assert base["entrypoint"] == ["python", "scripts/check_trace.py"]
    assert base["volumes"] == ["collector-data:/otel:ro"]
    assert base["restart"] == "no"
    for key in ("ports", "depends_on", "environment", "build"):
        assert key not in base
    local = _load("compose.local.yaml")["services"]["trace-check"]
    assert local["image"] == "model-monitor-backend:local"
    assert local["environment"] == {
        "CHECK_DATABASE_URL": "postgresql://monitor:monitor@postgres:5432/monitor"}
    assert "DATABASE_URL" not in local["environment"]
    host = _load("compose.testhost.yaml")["services"]["trace-check"]
    assert host["image"] == "${BACKEND_IMAGE:?BACKEND_IMAGE is not set}"
    assert host["env_file"] == ["/opt/model-monitor/check.env"]
    assert host["volumes"] == [
        "/opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro"]
    assert "environment" not in host and "ports" not in host


def test_check_env_example_has_names_only():
    text = (COMPOSE / "check.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert set(values) == {"CHECK_DATABASE_URL"}
    url = values["CHECK_DATABASE_URL"]
    assert url.startswith("postgresql://monitor_readonly:<password>@")
    assert "sslmode=verify-ca" in url


def test_trace_check_shell_scripts():
    wrapper = (COMPOSE / "check-trace.sh").read_text(encoding="utf-8")
    setup = (COMPOSE / "make-check-env.sh").read_text(encoding="utf-8")
    for text in (wrapper, setup):
        assert text.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in text and "\r\n" not in text
    assert "/opt/model-monitor/check.env" in wrapper
    assert "compose.testhost.yaml" in wrapper and "compose.local.yaml" in wrapper
    assert "--profile tools run --rm -T --no-deps trace-check" in wrapper
    assert '"$@"' in wrapper
    assert "/opt/model-monitor/secrets/monitor-readonly.password" in setup
    assert "monitor_readonly" in setup and "10.188.112.8" in setup
    assert "umask 077" in setup and "chmod 600" in setup
    for line in setup.splitlines():
        if "echo" in line:
            assert "PW" not in line and "password)" not in line, line
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL (no `trace-check` service, no scripts)

- [ ] **Step 3: Implement**

`deploy/compose/compose.yaml` — add after the `collector` service (before `volumes:`):

```yaml
  # S1-07 trace check tool: a one-shot service, never started by `up` (profile tools).
  # Run it with deploy/compose/check-trace.sh. It reads the span file read-only and the
  # database with CHECK_DATABASE_URL (the read-only user), never the backend's URL.
  trace-check:
    profiles: ["tools"]
    entrypoint: ["python", "scripts/check_trace.py"]
    volumes:
      - collector-data:/otel:ro
    restart: "no"
```

`deploy/compose/compose.local.yaml` — add after the `collector` service (before `volumes:`):

```yaml
  trace-check:
    image: model-monitor-backend:local
    environment:
      CHECK_DATABASE_URL: postgresql://monitor:monitor@postgres:5432/monitor   # local test value
```

`deploy/compose/compose.testhost.yaml` — add at the end of `services:`:

```yaml
  trace-check:
    image: ${BACKEND_IMAGE:?BACKEND_IMAGE is not set}
    env_file:
      # CHECK_DATABASE_URL with monitor_readonly (S1-11); made by make-check-env.sh, mode 600
      - /opt/model-monitor/check.env
    volumes:
      - /opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro
```

`deploy/compose/check-trace.sh`:

```bash
#!/usr/bin/env bash
# S1-07: check that one batch run arrived completely.
#   check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]
# Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
# On the test host (where /opt/model-monitor/check.env exists) run it with sudo; it uses
# compose.testhost.yaml. Elsewhere it uses the local stack (compose.local.yaml).
set -euo pipefail
cd "$(dirname "$0")"
if [ -f /opt/model-monitor/check.env ]; then
  FILES=(-f compose.yaml -f compose.testhost.yaml)
else
  FILES=(-f compose.yaml -f compose.local.yaml)
fi
exec docker compose "${FILES[@]}" --profile tools run --rm -T --no-deps trace-check "$@"
```

`deploy/compose/make-check-env.sh`:

```bash
#!/usr/bin/env bash
# S1-07, test host only: writes /opt/model-monitor/check.env (mode 600, root) for the trace
# check tool, with the read-only database user monitor_readonly (S1-11). Run once with sudo.
# Prints the file name and mode only, never the password.
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
PW_FILE=/opt/model-monitor/secrets/monitor-readonly.password
OUT=/opt/model-monitor/check.env
DB_HOST=10.188.112.8
CA=/etc/model-monitor/cloudsql-server-ca.pem
[ -s "$PW_FILE" ] || { echo "$PW_FILE is missing or empty" >&2; exit 1; }
umask 077
PW="$(tr -d '\r\n' < "$PW_FILE")"
# printf is a shell builtin: the password is not in a process argument list.
printf 'CHECK_DATABASE_URL=postgresql://monitor_readonly:%s@%s:5432/monitor?sslmode=verify-ca&sslrootcert=%s\n' \
  "$PW" "$DB_HOST" "$CA" > "$OUT.tmp"
chown root:root "$OUT.tmp"
chmod 600 "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
stat -c '%a %U %n' "$OUT"
echo "CHECK ENV DONE"
```

`deploy/compose/check.env.example`:

```
# Template for /opt/model-monitor/check.env on the test host (S1-07). Names only.
# make-check-env.sh writes the real file (mode 600, root) from the S1-11 password file.
CHECK_DATABASE_URL=postgresql://monitor_readonly:<password>@<cloud-sql-private-ip>:5432/monitor?sslmode=verify-ca&sslrootcert=/etc/model-monitor/cloudsql-server-ca.pem
```

`scripts/compose-smoke.sh`:
- In the header comment, replace "and checks the row and the monitor.ingest span in the Collector file." with "and checks the row and, with the S1-07 trace check tool, the monitor.ingest span."
- Replace everything from the line `STEP="monitor.ingest span in the Collector file"` to the end of the file with:

```bash
STEP="check-trace"
bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --backend-only --wait 30
echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q` and then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: PASS. (The stack itself is proved by the CI smoke test on the pull request; do not claim it ran.)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s1-07): trace-check Compose service, wrapper and smoke test`)

---

### Task 5: Documentation

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `deploy/compose/README.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md`

- [ ] **Step 1: `deploy/compose/TESTHOST.md`** — add to the files table:

```markdown
| `/opt/model-monitor/compose/check-trace.sh`, `make-check-env.sh` | The trace check tool (S1-07) from this folder | 755 |
| `/opt/model-monitor/check.env` | `CHECK_DATABASE_URL` with `monitor_readonly` (made by `make-check-env.sh`) | **600** |
```

and add a section before `## Roll back`:

````markdown
## Check a trace (S1-07)

One time, after the files are copied (the image must contain `scripts/check_trace.py`):

```bash
sudo bash /opt/model-monitor/compose/make-check-env.sh
```

Expected: `600 root /opt/model-monitor/check.env`, then `CHECK ENV DONE`.

From a laptop, in one line (use `--backend-only` until a GCP job sends spans):

```bash
gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "sudo bash /opt/model-monitor/compose/check-trace.sh <trace_id> --backend-only"
```

Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
````

- [ ] **Step 2: `deploy/compose/README.md`** — add a short section "Check a trace (S1-07)": after `up`, run `bash deploy/compose/check-trace.sh <trace_id> --backend-only` from the repository root; the exit codes; the smoke test uses it.

- [ ] **Step 3: `issues.md` S1-07** — under the S1-07 table, add one line:
`**Design (2026-10-08):** changes/2026-10-08-s1-07-trace-check/ (Compose service trace-check, wrapper deploy/compose/check-trace.sh, --backend-only, --wait). A conflict (409) is reported as missing with the stored trace ID.`

- [ ] **Step 4: `CHANGELOG.md`** — under `## [Unreleased]` / `### Added`, first item:

```markdown
- Trace check tool (S1-07): `deploy/compose/check-trace.sh <trace_id> [--backend-only]
  [--wait SECONDS]` shows if the run row, the `monitor.ingest` span, the GCP `batch.run`
  span and the link to `batch.send` exist for one trace. Exit 0, 1 or 2. It uses the
  read-only database user and runs on the local stack and the test host. The CI smoke test
  uses it.
```

- [ ] **Step 5: `DEVLOG.md`** — add at the top of `## Work log` an entry `### 2026-10-08 — S1-07: trace check tool` with: what was built (files), the decisions from `intent.md` (approach B, SSH line, smoke uses it, conflict rule), the test evidence (the exact pytest counts you ran), and "Not yet run: the CI smoke test (on the pull request) and the test-host check (after the next image)".

- [ ] **Step 6: Run** `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py -q`. Expected: PASS.

- [ ] **Step 7: Stop for review** (Claude commits `docs(s1-07): trace check runbook, changelog and devlog`)
