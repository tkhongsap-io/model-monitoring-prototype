# Dashboard for the GCP Use Cases (S2-07) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **In this project Codex implements ONE task per run (`codex exec`, reasoning effort medium) and does not commit; Claude reviews, runs the tests and commits after each task.**

**Goal:** The existing dashboard, unchanged, shows the registered GCP use cases with their latest run, freshness, grade, lanes and "Unknown" reasons, served on front-door port 8082 of the test host.

**Architecture:** A pure view (`dashboard_view.py`) turns registry entries, stored runs and evaluations into the JSON the UI already reads; three read-only routes (`dashboard_routes.py`) serve it. A `dashboard` image (Node build stage → dashboard file server on port 8090) holds the built files. The front door gets port 8082: `/` to the dashboard, four GET API paths to the backend.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy Core, pytest; nginx-unprivileged 1.28.0; Node 24 + pnpm 10.15.1 (build stage only); Docker Compose; GitHub Actions.

**Spec:** `changes/2026-10-14-s2-07-dashboard/spec.md` (intent: `intent.md` in the same folder). Read both, and the spec's "Names" table, before you start.

## Global Constraints

- `artifacts/control-tower/src/**` does not change. No file under `artifacts/` changes.
- Use the names of the spec's "Names" table: **front door** (the existing nginx), **dashboard** (the Compose service and image), **dashboard file server** (the web server inside the dashboard image; never "the nginx"), **dashboard API** (`/api/live/*`), **job API** (`POST /api/batch/runs`).
- Ports: front door 8082 (host and container) for the dashboard; dashboard file server 8090 (inside Docker only, never published); backend 8000.
- No new Python or npm package. No change to `pnpm-lock.yaml` or `pnpm-workspace.yaml`.
- Pinned images: `node:24.21.0-bookworm-slim` (build stage; **not** Alpine: the workspace keeps only the glibc Linux binaries of rollup, lightningcss and tailwind oxide) and `nginxinc/nginx-unprivileged:1.28.0-alpine` (the same pin as the front door).
- No response of the dashboard API contains `payload`, a record, a key or a token.
- The view is pure: no I/O, no clock (`now` is a parameter), never raises for stored data.
- LF line endings. No `git add`, no `git commit` (Claude commits).
- Run the tests from `backend/` with `.venv\Scripts\python.exe -m pytest ...`. If the sandbox blocks the pytest temp folder, add `-p no:cacheprovider --basetemp=.pytest-tmp`. Do not patch `os.mkdir` or any other global in `conftest.py`.
- Do not run Docker, Compose, the smoke scripts or pnpm; CI runs them.

## Review Focus

1. **A run whose `completed_at` cannot be read, or a corrupt `metrics` JSON in an evaluation:** the row still renders (state `stale`, lanes Unknown), no 500. Test in Task 1 (`test_bad_stored_data_never_raises`).
2. **A use case with a run but no evaluation yet (the first 30 s):** all lanes Unknown with "not graded yet", `signals` empty. Test in Task 1 (`test_run_not_graded_yet`).
3. **Freshness exactly at the limit** (`now − completed_at == expected_every_s + grace_s`): `at_tail`; one second more: `stale`. Test in Task 1 (`test_freshness_limit`).
4. **The S1-01 example record texts** (question, answer, retrieval text) must never appear in any dashboard response, also after the run is graded. Test in Task 2 (`test_no_record_text_in_any_response`).
5. **A non-GET method or an unlisted `/api/` path on port 8082** (for example `POST /api/batch/runs`, `GET /api/readiness`): refused by the front door. Test in Task 4 (static config checks) and Task 5 (smoke).

---

### Task 1: Read functions and the pure view

**Files:**
- Modify: `backend/app/db.py` (after `evaluator_counts`)
- Create: `backend/app/dashboard_view.py`
- Test: `backend/tests/test_dashboard_view.py`, `backend/tests/test_dashboard_store.py`

**Interfaces:**
- Consumes: `app.engines.batch_grading.parse_utc(text) -> datetime | None`; `app.registry.UseCase` (fields `use_case_id`, `name`, `owner`, `developer`, `mode`, `schedule.expected_every_s`, `schedule.grace_s`, `turnaround_limit_s`, `data_classification`); tables `batch_runs`, `batch_evaluations`.
- Produces:
  - `db.latest_batch_run(use_case_id: str) -> dict | None`
  - `db.latest_evaluation(batch_run_id: str, bands_version: str) -> dict | None`
  - `db.evaluation_history(use_case_id: str, bands_version: str, limit: int = 20) -> list[dict]` (newest first)
  - `dashboard_view.UI_LANES: list[str]`, `dashboard_view.LANE_OF: dict[str, str]`, `dashboard_view.REASON_TEXT: dict[str, str]`
  - `dashboard_view.portfolio_row(use_case, run: dict | None, evaluation: dict | None, now: float) -> dict`
  - `dashboard_view.detail(use_case, run, evaluation, history: list[dict], now: float) -> dict`
  - `dashboard_view.summary(rows: list[dict], now: float, build_sha: str) -> dict`

- [ ] **Step 1: Write the failing store tests** in `backend/tests/test_dashboard_store.py`:

```python
"""Dashboard read functions (S2-07)."""
from __future__ import annotations

import json

from app import db, ids
from tests.test_batch_runs_store import row as run_row

BANDS = "core-2026-10-12"


def evaluation(stored: dict, at: float, grade: str = "Green") -> dict:
    return {"evaluation_id": ids.new_id(at), "batch_run_id": stored["batch_run_id"],
            "use_case_id": stored["use_case_id"], "run_id": stored["run_id"],
            "trace_id": stored["trace_id"], "bands_version": BANDS, "metrics": json.dumps([]),
            "delivery_grade": "Green", "grade": grade, "baseline_run_ids": "[]",
            "evaluated_at": at, "langfuse_status": "skipped", "langfuse_attempts": 0,
            "langfuse_error": None}


def test_latest_run_is_the_newest_received(isolated_db):
    db.put_batch_run(run_row(run_id="a"))
    second, _ = db.put_batch_run(run_row(run_id="b"))
    db.put_batch_run(run_row(run_id="c", use_case_id="GCP-UC-07"))
    assert db.latest_batch_run("GCP-UC-03")["run_id"] == second["run_id"]
    assert db.latest_batch_run("GCP-UC-99") is None


def test_latest_evaluation_and_history(isolated_db):
    a, _ = db.put_batch_run(run_row(run_id="a"))
    b, _ = db.put_batch_run(run_row(run_id="b"))
    db.put_batch_evaluation(evaluation(a, 10.0, "Amber"))
    db.put_batch_evaluation(evaluation(b, 20.0, "Green"))
    assert db.latest_evaluation(b["batch_run_id"], BANDS)["grade"] == "Green"
    assert db.latest_evaluation(b["batch_run_id"], "other") is None
    assert [e["grade"] for e in db.evaluation_history("GCP-UC-03", BANDS)] == ["Green", "Amber"]
    assert len(db.evaluation_history("GCP-UC-03", BANDS, limit=1)) == 1
```

- [ ] **Step 2: Write the failing view tests** in `backend/tests/test_dashboard_view.py`:

```python
"""Dashboard view (S2-07): pure mapping to the shapes the unchanged UI reads."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import dashboard_view as v
from app.registry import Schedule, UseCase

UC = UseCase(use_case_id="rtr-fraud-validation", name="RTR fraud validation",
             owner="RTR fraud team", developer="Prakasit Issanapong", mode="identity_only",
             schedule=Schedule(expected_every_s=86400, grace_s=21600), turnaround_limit_s=None,
             data_classification="confidential")
DONE = "2026-10-14T02:00:00Z"
T_DONE = datetime(2026, 10, 14, 2, 0, 0, tzinfo=timezone.utc).timestamp()
NOW = T_DONE + 3600
RUN = {"batch_run_id": "0199e2c1-7a10-7c3e-9b1a-3f6d2a4e8b01", "run_id": "rtr-1",
       "status": "completed", "completed_at": DONE, "model": "gemini-2.5-flash",
       "record_count": 0, "content_sha256": "b" * 64, "trace_id": "09d9f92ba1b231744a1a36bdf0e78db3",
       "payload": '{"records":[]}'}


def metric(name, lane, value, health, reason=None, in_rollup=True):
    return {"name": name, "lane": lane, "value": value, "health": health, "reason": reason,
            "in_rollup": in_rollup}


METRICS = [
    metric("run_status", "Delivery", None, "Green"),
    metric("turnaround_s", "Delivery", None, "Unknown", "not_reported"),
    metric("failure_rate", "Reliability", 0.002, "Green"),
    metric("volume_change", "Reliability", None, "Unknown", "no_baseline"),
    metric("valid_output_rate", "Output", None, "Unknown", "records_not_approved", False),
    metric("block_rate", "Output", None, "Unknown", "records_not_approved", False),
]
EVAL = {"grade": "Unknown", "delivery_grade": "Unknown", "bands_version": "core-2026-10-12",
        "metrics": json.dumps(METRICS), "evaluated_at": T_DONE + 30}


def test_graded_row():
    row = v.portfolio_row(UC, RUN, EVAL, NOW)
    assert row["registry_id"] == "rtr-fraud-validation" and row["use_case_name"] == "RTR fraud validation"
    assert row["business_unit"] == "RTR fraud team" and row["platform_or_app"] == "GCP batch job"
    assert row["risk_tier"] is None and row["lane_kind"] == "llm" and row["status"] == "completed"
    assert row["overall"] == row["current_health"] == row["grade"] == "Unknown"
    assert list(row["lanes"]) == v.UI_LANES
    assert row["lanes"] == {"Quality": "Unknown", "Safety & security": "Unknown",
                            "Reliability": "Green", "Drift & degradation": "Unknown",
                            "Feedback & action loop": "Unknown"}
    assert row["tooltips"]["Reliability"] == {"metric": "failure_rate 0.2% (Green)"}
    assert row["tooltips"]["Drift & degradation"] == {
        "metric": "volume_change Unknown: no baseline: needs 5 earlier runs"}
    assert row["tooltips"]["Quality"] == {"metric": "Unknown: records not approved"}
    assert row["tooltips"]["Feedback & action loop"] == {
        "metric": "Unknown: no feedback source in October"}
    assert row["feedback_unknown_reason"] == "no feedback source in October"
    assert row["state"] == "at_tail"
    assert (row["window_id"], row["observation_id"], row["trace_id"], row["batch_id"]) == (
        "rtr-1", RUN["trace_id"], RUN["trace_id"], RUN["batch_run_id"])
    assert row["model_version"] == "gemini-2.5-flash" and row["record_count"] == 0
    assert row["last_success_at"] == DONE and row["delivery_grade"] == "Unknown"
    assert row["bands_version"] == "core-2026-10-12"
    assert "payload" not in row


def test_volume_tooltip_with_value():
    metrics = [m if m["name"] != "volume_change" else metric("volume_change", "Reliability",
                                                              1.25, "Green") for m in METRICS]
    row = v.portfolio_row(UC, RUN, {**EVAL, "metrics": json.dumps(metrics)}, NOW)
    assert row["lanes"]["Drift & degradation"] == "Green"
    assert row["tooltips"]["Drift & degradation"] == {"metric": "volume_change 1.25 (Green)"}


def test_no_run_yet():
    row = v.portfolio_row(UC, None, None, NOW)
    assert row["state"] == "idle" and row["status"] == "no run yet" and row["overall"] == "Unknown"
    assert set(row["lanes"].values()) == {"Unknown"}
    assert {t["metric"] for t in row["tooltips"].values()} == {"Unknown: no run yet"}
    assert row["trace_id"] is None and row["window_id"] is None


def test_run_not_graded_yet():
    row = v.portfolio_row(UC, RUN, None, NOW)
    assert row["state"] == "at_tail" and row["overall"] == "Unknown"
    assert {t["metric"] for t in row["tooltips"].values()} == {"Unknown: not graded yet"}
    d = v.detail(UC, RUN, None, [], NOW)
    assert d["signals"] == [] and d["evidence_note"] == "not graded yet"


def test_freshness_limit():
    limit = 86400 + 21600
    assert v.portfolio_row(UC, RUN, EVAL, T_DONE + limit)["state"] == "at_tail"
    assert v.portfolio_row(UC, RUN, EVAL, T_DONE + limit + 1)["state"] == "stale"


def test_bad_stored_data_never_raises():
    row = v.portfolio_row(UC, {**RUN, "completed_at": "not a time"},
                          {**EVAL, "metrics": "{broken"}, NOW)
    assert row["state"] == "stale" and set(row["lanes"].values()) == {"Unknown"}
    d = v.detail(UC, RUN, {**EVAL, "metrics": "{broken"}, [], NOW)
    assert isinstance(d["signals"], list)


def test_detail_header_and_signals():
    d = v.detail(UC, RUN, EVAL, [EVAL], NOW)
    assert d["source_record_id"] == "registry: batch-use-cases.yaml"
    assert d["business_owner"] == d["system_owner"] == "RTR fraud team"
    assert d["technical_owner"] == "Prakasit Issanapong" and d["monitoring_owner"] == "RAI team"
    assert d["model_or_route"] == "gemini-2.5-flash"
    assert d["data_sources"] == "confidential (identity-only: no records)"
    assert d["judge"] is None and d["judge_sample"] == []
    assert d["evidence_note"] == "graded with bands core-2026-10-12"
    sig = {s["key"]: s for s in d["signals"]}
    assert list(sig) == ["run_status", "turnaround_s", "failure_rate", "volume_change",
                         "valid_output_rate", "block_rate"]
    assert {k: s["lane"] for k, s in sig.items()} == v.LANE_OF
    assert (sig["run_status"]["green_bar"], sig["run_status"]["red_bar"]) == ("completed", "failed")
    assert (sig["turnaround_s"]["unit"], sig["turnaround_s"]["green_bar"],
            sig["turnaround_s"]["red_bar"]) == ("s", "limit", "2 × limit")
    assert sig["turnaround_s"]["pending_reason"] == v.REASON_TEXT["not_reported"]
    assert (sig["failure_rate"]["value"], sig["failure_rate"]["health"],
            sig["failure_rate"]["pending_reason"]) == (0.002, "Green", None)
    assert sig["volume_change"]["label"] == "Volume change (Green 0.7–1.3)"
    assert (sig["volume_change"]["green_bar"], sig["volume_change"]["red_bar"]) == (0.7, 0.4)
    assert sig["block_rate"]["pending_reason"] == "records not approved"


def test_turnaround_band_with_limit():
    uc = UC.model_copy(update={"turnaround_limit_s": 3600, "mode": "records"})
    d = v.detail(uc, RUN, EVAL, [], NOW)
    sig = {s["key"]: s for s in d["signals"]}
    assert (sig["turnaround_s"]["unit"], sig["turnaround_s"]["green_bar"],
            sig["turnaround_s"]["red_bar"]) == ("seconds", 3600, 7200)
    assert d["data_sources"] == "confidential"


def test_history_is_oldest_first_values_only():
    older = {**EVAL, "metrics": json.dumps([metric("failure_rate", "Reliability", 0.004, "Green")])}
    d = v.detail(UC, RUN, EVAL, [EVAL, older], NOW)            # newest first in
    hist = next(s for s in d["signals"] if s["key"] == "failure_rate")["history"]
    assert hist == [{"tick": 0, "value": 0.004, "health": "Green"},
                    {"tick": 1, "value": 0.002, "health": "Green"}]
    vol = next(s for s in d["signals"] if s["key"] == "volume_change")["history"]
    assert vol == []


def test_summary():
    rows = [v.portfolio_row(UC, RUN, EVAL, NOW),
            v.portfolio_row(UC.model_copy(update={"use_case_id": "b"}), None, None, NOW)]
    s = v.summary(rows, NOW, "abc123")
    assert s["use_case_count"] == 2 and s["as_of"] == {"rtr-fraud-validation": None, "b": None}
    assert s["overall_counts"] == {"Unknown": 2}
    assert s["lane_counts"]["Reliability"] == {"Green": 1, "Unknown": 1}
    assert s["open_alerts"] == {} and s["sync_state"] == "idle"
    assert s["build"] == {"git_sha": "abc123"}
    assert s["generated_at"].endswith("Z")
    assert v.summary([], NOW, "x")["sync_state"] == "idle"
    stale = v.portfolio_row(UC, RUN, EVAL, T_DONE + 10**7)
    assert v.summary(rows + [stale], NOW, "x")["sync_state"] == "stale"
```

- [ ] **Step 3: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_store.py tests/test_dashboard_view.py -q`
Expected: FAIL (`AttributeError` / `ModuleNotFoundError: app.dashboard_view`).

- [ ] **Step 4: Add the read functions** to `backend/app/db.py`, after `evaluator_counts`:

```python
# ---------------------------------------------------------------- dashboard reads (S2-07)

def latest_batch_run(use_case_id: str) -> dict | None:
    q = (select(batch_runs).where(batch_runs.c.use_case_id == use_case_id)
         .order_by(batch_runs.c.received_at.desc()).limit(1))
    with engine().begin() as cx:
        found = cx.execute(q).mappings().fetchone()
    return dict(found) if found else None


def latest_evaluation(batch_run_id: str, bands_version: str) -> dict | None:
    q = select(batch_evaluations).where(
        (batch_evaluations.c.batch_run_id == batch_run_id)
        & (batch_evaluations.c.bands_version == bands_version))
    with engine().begin() as cx:
        found = cx.execute(q).mappings().fetchone()
    return dict(found) if found else None


def evaluation_history(use_case_id: str, bands_version: str, limit: int = 20) -> list[dict]:
    q = (select(batch_evaluations)
         .where((batch_evaluations.c.use_case_id == use_case_id)
                & (batch_evaluations.c.bands_version == bands_version))
         .order_by(batch_evaluations.c.evaluated_at.desc()).limit(max(1, min(limit, 200))))
    with engine().begin() as cx:
        return [dict(r) for r in cx.execute(q).mappings().all()]
```

- [ ] **Step 5: Write `backend/app/dashboard_view.py`:**

```python
"""Dashboard view (S2-07): registry + latest run + evaluations → the JSON the UI reads.

Pure: no I/O, no clock (`now` is a parameter), never raises for stored data. The frontend
does not change, so the five fixed UI lanes are filled from the S2-05 metrics:
Reliability ← failure_rate, Drift & degradation ← volume_change, Quality and Safety ←
records not approved, Feedback ← no source in October. The Delivery metrics show only in
the detail signals. No row or detail contains `payload`, a record, a key or a token.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .engines.batch_grading import parse_utc

UI_LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation",
            "Feedback & action loop"]
LANE_OF = {"run_status": "Delivery", "turnaround_s": "Delivery",
           "failure_rate": "Reliability", "volume_change": "Drift & degradation",
           "valid_output_rate": "Quality", "block_rate": "Safety & security"}
REASON_TEXT = {
    "no_requests": "no requests in the run",
    "no_baseline": "no baseline: needs 5 earlier runs",
    "not_reported": "not reported: no limit in the registry or no submitted_at",
    "invalid_times": "the run times cannot be read",
    "invalid_counts": "the run counts cannot be read",
    "invalid_status": "unknown run status",
    "records_not_approved": "records not approved",
}
NO_FEEDBACK = "no feedback source in October"
NO_RECORDS = "Unknown: records not approved"
_STATE_RANK = {"at_tail": 0, "idle": 1, "stale": 2}
_SIGNALS = [  # key, label, unit, direction, green_bar, red_bar
    ("run_status", "Run status", "status", "lower_is_better", "completed", "failed"),
    ("turnaround_s", "Turnaround", "seconds", "lower_is_better", None, None),
    ("failure_rate", "Failure rate", "fraction", "lower_is_better", 0.01, 0.05),
    ("volume_change", "Volume change (Green 0.7–1.3)", "ratio", "higher_is_better", 0.7, 0.4),
    ("valid_output_rate", "Valid output rate", "fraction", "higher_is_better", 0.99, 0.95),
    ("block_rate", "Block rate", "fraction", "lower_is_better", 0.01, 0.05),
]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _metrics(evaluation: dict | None) -> dict[str, dict]:
    if not evaluation:
        return {}
    try:
        items = json.loads(evaluation.get("metrics") or "[]")
    except (TypeError, ValueError):
        return {}
    if not isinstance(items, list):
        return {}
    return {m["name"]: m for m in items if isinstance(m, dict) and isinstance(m.get("name"), str)}


def _reason(reason: object) -> str:
    return REASON_TEXT.get(reason, str(reason) if reason else "unknown")  # type: ignore[arg-type]


def _state(use_case, run: dict | None, now: float) -> str:
    if run is None:
        return "idle"
    done = parse_utc(run.get("completed_at"))
    if done is None:
        return "stale"
    limit = use_case.schedule.expected_every_s + use_case.schedule.grace_s
    return "at_tail" if now - done.timestamp() <= limit else "stale"


def _tooltip(metric: dict | None, name: str) -> str:
    if metric is None:
        return f"{name} Unknown: not graded yet"
    if metric.get("health") == "Unknown" or metric.get("value") is None:
        return f"{name} Unknown: {_reason(metric.get('reason'))}"
    value = metric["value"]
    shown = f"{value * 100:.1f}%" if name == "failure_rate" else f"{value:.2f}"
    return f"{name} {shown} ({metric['health']})"


def portfolio_row(use_case, run: dict | None, evaluation: dict | None, now: float) -> dict:
    metrics = _metrics(evaluation)
    lanes = {lane: "Unknown" for lane in UI_LANES}
    if run is None or evaluation is None:
        blank = "Unknown: no run yet" if run is None else "Unknown: not graded yet"
        tooltips = {lane: {"metric": blank} for lane in UI_LANES}
    else:
        failure, volume = metrics.get("failure_rate"), metrics.get("volume_change")
        lanes["Reliability"] = failure["health"] if failure else "Unknown"
        lanes["Drift & degradation"] = volume["health"] if volume else "Unknown"
        tooltips = {
            "Quality": {"metric": NO_RECORDS},
            "Safety & security": {"metric": NO_RECORDS},
            "Reliability": {"metric": _tooltip(failure, "failure_rate")},
            "Drift & degradation": {"metric": _tooltip(volume, "volume_change")},
            "Feedback & action loop": {"metric": f"Unknown: {NO_FEEDBACK}"},
        }
    grade = (evaluation or {}).get("grade") or "Unknown"
    r = run or {}
    return {
        "registry_id": use_case.use_case_id, "use_case_name": use_case.name,
        "business_unit": use_case.owner, "platform_or_app": "GCP batch job",
        "risk_tier": None, "lane_kind": "llm",
        "status": r.get("status") or "no run yet",
        "overall": grade, "current_health": grade, "lanes": lanes, "tooltips": tooltips,
        "feedback_unknown_reason": NO_FEEDBACK,
        "state": _state(use_case, run, now),
        "window_id": r.get("run_id"), "observation_id": r.get("trace_id"),
        "trace_id": r.get("trace_id"), "batch_id": r.get("batch_run_id"),
        "content_sha256": r.get("content_sha256"), "model_version": r.get("model"),
        "record_count": r.get("record_count"), "last_success_at": r.get("completed_at"),
        "grade": (evaluation or {}).get("grade"),
        "delivery_grade": (evaluation or {}).get("delivery_grade"),
        "bands_version": (evaluation or {}).get("bands_version"),
        "backlog": None, "source_lag_ms": None, "source_tick": None, "observed_tick": None,
    }


def _signal(key, label, unit, direction, green, red, metric, limit, history):
    if key == "turnaround_s":
        if limit:
            green, red = limit, 2 * limit
        else:
            unit, green, red = "s", "limit", "2 × limit"
    points = []
    for tick, past in enumerate(reversed(history)):
        m = _metrics(past).get(key)
        if m and isinstance(m.get("value"), (int, float)):
            points.append({"tick": tick, "value": m["value"], "health": m.get("health")})
    health = metric.get("health", "Unknown") if metric else "Unknown"
    pending = None
    if metric is None:
        pending = "not graded yet"
    elif health == "Unknown":
        pending = _reason(metric.get("reason"))
    return {"key": key, "label": label, "lane": LANE_OF[key],
            "value": metric.get("value") if metric else None, "unit": unit,
            "direction": direction, "green_bar": green, "red_bar": red, "health": health,
            "pending_reason": pending, "history": points}


def detail(use_case, run: dict | None, evaluation: dict | None, history: list[dict],
           now: float) -> dict:
    out = portfolio_row(use_case, run, evaluation, now)
    metrics = _metrics(evaluation)
    if run is None:
        note = "no run yet"
    elif evaluation is None:
        note = "not graded yet"
    else:
        note = f"graded with bands {evaluation.get('bands_version')}"
    classification = use_case.data_classification
    out.update({
        "source_record_id": "registry: batch-use-cases.yaml",
        "business_owner": use_case.owner, "system_owner": use_case.owner,
        "technical_owner": use_case.developer, "monitoring_owner": "RAI team",
        "model_or_route": (run or {}).get("model"),
        "data_sources": (f"{classification} (identity-only: no records)"
                         if use_case.mode == "identity_only" else classification),
        "last_reviewed": None, "next_review": None,
        "judge": None, "judge_sample": [], "evidence_note": note,
        "signals": [] if evaluation is None else [
            _signal(*spec, metrics.get(spec[0]), use_case.turnaround_limit_s, history)
            for spec in _SIGNALS],
    })
    return out


def summary(rows: list[dict], now: float, build_sha: str) -> dict:
    overall: dict[str, int] = {}
    lane_counts: dict[str, dict[str, int]] = {lane: {} for lane in UI_LANES}
    for row in rows:
        overall[row["overall"]] = overall.get(row["overall"], 0) + 1
        for lane in UI_LANES:
            health = row["lanes"].get(lane, "Unknown")
            lane_counts[lane][health] = lane_counts[lane].get(health, 0) + 1
    states = [row["state"] for row in rows] or ["idle"]
    return {
        "use_case_count": len(rows), "as_of": {row["registry_id"]: None for row in rows},
        "overall_counts": overall, "lane_counts": lane_counts, "open_alerts": {},
        "sync_state": max(states, key=lambda s: _STATE_RANK.get(s, 2)),
        "generated_at": _iso(now), "build": {"git_sha": build_sha},
    }
```

Note on `test_summary`: rows `[at_tail, idle]` → the worst is `idle` (rank 1 > 0). That is what the test expects.

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_store.py tests/test_dashboard_view.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `feat(s2-07): dashboard read functions and pure view`

---

### Task 2: The dashboard API routes

**Files:**
- Create: `backend/app/api/dashboard_routes.py`
- Modify: `backend/app/main.py` (import and `include_router`; docstring)
- Modify: `backend/tests/test_app_surface.py` (`ALLOWLIST`; the parametrize list of `test_prototype_paths_are_404_in_any_mode`)
- Test: `backend/tests/test_dashboard_routes.py`

**Interfaces:**
- Consumes: Task 1 (`db.latest_batch_run`, `db.latest_evaluation`, `db.evaluation_history`, `dashboard_view.portfolio_row`, `detail`, `summary`); `batch_grading.BANDS_VERSION`; `registry.current() -> dict[str, UseCase]`; `config.BUILD_SHA`.
- Produces: `GET /api/live/portfolio`, `GET /api/live/use-case/{use_case_id}`, `GET /api/live/alerts`.

- [ ] **Step 1: Change `backend/tests/test_app_surface.py`.** Add to `ALLOWLIST`:

```python
    ("/api/live/portfolio", "get"),
    ("/api/live/use-case/{use_case_id}", "get"),
    ("/api/live/alerts", "get"),
```

and remove `("GET", "/api/live/portfolio"),` from the parametrize list of `test_prototype_paths_are_404_in_any_mode` (the path is now served). Keep the other entries, also `("POST", "/api/live/poll")`.

- [ ] **Step 2: Write the failing route tests** in `backend/tests/test_dashboard_routes.py`:

```python
"""Dashboard API (S2-07): read-only, registry use cases, no record text."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import batch_evaluator, db, main
from tests.test_batch_runs_api import AUTH, URL, client, example  # noqa: F401 (fixture)

UI_ROW_FIELDS = {"registry_id", "use_case_name", "business_unit", "overall", "current_health",
                 "lanes", "tooltips", "state", "window_id", "observation_id", "batch_id",
                 "content_sha256", "model_version", "record_count", "last_success_at",
                 "trace_id", "grade", "delivery_grade", "bands_version"}


def strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for value in node.values() for s in strings(value)]
    if isinstance(node, list):
        return [s for value in node for s in strings(value)]
    return []


def test_portfolio_lists_registry_use_cases_in_order(client):
    body = client.get("/api/live/portfolio").json()
    assert [r["registry_id"] for r in body["rows"]] == ["GCP-UC-03", "GCP-UC-07"]
    assert all(r["state"] == "idle" for r in body["rows"])
    for key in ("use_case_count", "overall_counts", "lane_counts", "sync_state", "rows"):
        assert key in body


def test_graded_run_shows_in_portfolio_and_detail(client):
    response = client.post(URL, json=example("01-completed-online.json"), headers=AUTH)
    assert response.status_code == 201, response.text
    batch_evaluator.Evaluator(sender=None).run_cycle()
    row = client.get("/api/live/portfolio").json()["rows"][0]
    assert UI_ROW_FIELDS <= set(row)
    assert set(row["lanes"]) == {"Quality", "Safety & security", "Reliability",
                                 "Drift & degradation", "Feedback & action loop"}
    assert row["grade"] is not None and row["window_id"] == "invoice-summary-2026-10-07"
    detail = client.get("/api/live/use-case/GCP-UC-03").json()
    assert len(detail["signals"]) == 6 and detail["trace_id"] == row["trace_id"]


def test_no_record_text_in_any_response(client):
    body = example("01-completed-online.json")
    client.post(URL, json=body, headers=AUTH)
    batch_evaluator.Evaluator(sender=None).run_cycle()
    secrets = {s for s in strings(body["records"]) if len(s) >= 8}
    assert secrets, "the example must carry record text"
    for path in ("/api/live/portfolio", "/api/live/use-case/GCP-UC-03", "/api/live/alerts"):
        text = client.get(path).text
        assert '"payload"' not in text, path
        for secret in secrets:
            assert secret not in text, (path, secret)


def test_unknown_use_case_is_404(client):
    response = client.get("/api/live/use-case/AICT-L01")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown use case"}


def test_alerts_are_empty(client):
    assert client.get("/api/live/alerts?uc=GCP-UC-03&open=true").json() == {
        "contract_version": "1.1", "redacted": True, "rows": []}


def test_database_error_is_503_with_class_only(client, monkeypatch):
    def broken(*a, **k):
        raise OperationalError("SELECT secret", {}, Exception("password=hunter2"))

    monkeypatch.setattr(db, "latest_batch_run", broken)
    for path in ("/api/live/portfolio", "/api/live/use-case/GCP-UC-03"):
        response = client.get(path)
        assert response.status_code == 503
        assert response.json() == {"detail": "database is not reachable",
                                   "error": "OperationalError"}
        assert "hunter2" not in response.text


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_routes_are_read_only(client, method):
    assert getattr(client, method)("/api/live/portfolio").status_code == 405
```

- [ ] **Step 3: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_routes.py tests/test_app_surface.py -q`
Expected: FAIL (404 for the new paths; the allowlist test fails).

- [ ] **Step 4: Write `backend/app/api/dashboard_routes.py`:**

```python
"""Dashboard API (S2-07): read-only routes for the unchanged control-tower UI.

Served on front-door port 8082 only (deploy/nginx/conf.d/dashboard.conf); port 80 keeps
only the job API. Each response is built by `dashboard_view` from the registry, the latest
stored run and its evaluation: never a whole stored row, never `payload`, a record, a key
or a token. A database error gives 503 with the error class name only.
"""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .. import config, dashboard_view, db, registry
from ..engines.batch_grading import BANDS_VERSION

router = APIRouter(prefix="/api/live")


def _db_error(exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "database is not reachable", "error": type(exc).__name__},
                        status_code=503)


def _latest(use_case_id: str) -> tuple[dict | None, dict | None]:
    run = db.latest_batch_run(use_case_id)
    evaluation = db.latest_evaluation(run["batch_run_id"], BANDS_VERSION) if run else None
    return run, evaluation


@router.get("/portfolio")
def portfolio():
    now = time.time()
    try:
        rows = [dashboard_view.portfolio_row(use_case, *_latest(use_case_id), now)
                for use_case_id, use_case in registry.current().items()]
    except SQLAlchemyError as exc:
        return _db_error(exc)
    return {**dashboard_view.summary(rows, now, config.BUILD_SHA), "rows": rows}


@router.get("/use-case/{use_case_id}")
def use_case(use_case_id: str):
    entry = registry.current().get(use_case_id)
    if entry is None:
        return JSONResponse({"detail": "unknown use case"}, status_code=404)
    now = time.time()
    try:
        run, evaluation = _latest(use_case_id)
        history = db.evaluation_history(use_case_id, BANDS_VERSION)
    except SQLAlchemyError as exc:
        return _db_error(exc)
    return dashboard_view.detail(entry, run, evaluation, history, now)


@router.get("/alerts")
def alerts():
    """No alerting in October: always an empty list (the UI badge shows 0)."""
    return {"contract_version": "1.1", "redacted": True, "rows": []}
```

- [ ] **Step 5: Mount it in `backend/app/main.py`.** Change the import to
`from .api import batch_routes, dashboard_routes, ops_routes` and add
`app.include_router(dashboard_routes.router)` after `app.include_router(ops_routes.router)`.
In the module docstring, change the first paragraph to name the dashboard API too:
"It serves the batch MVP API: `POST /api/batch/runs` (S1-02, S1-05), the service checks in
`api/ops_routes.py`, and the read-only dashboard API `/api/live/*` (S2-07,
`api/dashboard_routes.py`). Every other path returns 404."

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_routes.py tests/test_app_surface.py -q`
Expected: PASS.

- [ ] **Step 7: Run the full fast suite.**
Run: `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: all pass. If another test expects `/api/live/portfolio` to be 404 on the batch MVP app (`main.app`), change only that expectation and list it under "Deviations". Tests of `tests/prototype_app.py` do not change.

- [ ] **Step 8: Commit** (Claude): `feat(s2-07): read-only dashboard API`

---

### Task 3: The dashboard image

**Files:**
- Create: `deploy/dashboard/Dockerfile`, `deploy/dashboard/file-server.conf`, `.dockerignore` (repository root)
- Test: `backend/tests/test_dashboard_files.py`

**Interfaces:**
- Produces: an image that serves the built dashboard on port 8090 (`/healthz` → 200). Build: `docker build -f deploy/dashboard/Dockerfile .` from the repository root.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_dashboard_files.py`:

```python
"""Dashboard image (S2-07): pinned stages, frozen install, dashboard file server."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "deploy" / "dashboard"


def test_dockerfile_two_pinned_stages():
    text = (DASH / "Dockerfile").read_text(encoding="utf-8")
    assert "\r\n" not in text
    froms = re.findall(r"^FROM\s+(\S+)(?:\s+AS\s+(\w+))?", text, flags=re.MULTILINE)
    assert froms == [("node:24.21.0-bookworm-slim", "build"),
                     ("nginxinc/nginx-unprivileged:1.28.0-alpine", "")]
    assert "pnpm@10.15.1" in text and "--frozen-lockfile" in text
    assert "run build:live" in text and "run check:strict-live" in text
    assert "COPY --from=build /app/artifacts/control-tower/dist/public /usr/share/nginx/html" in text
    assert "COPY deploy/dashboard/file-server.conf /etc/nginx/conf.d/default.conf" in text
    assert "EXPOSE 8090" in text
    assert "USER root" not in text


def test_file_server_conf():
    text = (DASH / "file-server.conf").read_text(encoding="utf-8")
    assert "\r\n" not in text
    assert re.search(r"^\s*listen 8090;", text, flags=re.MULTILINE)
    assert "server_tokens off;" in text
    assert "try_files $uri $uri/ /index.html;" in text            # SPA fallback
    assert re.search(r"location /assets/ \{[^}]*try_files \$uri =404;", text, flags=re.S)
    assert "max-age=31536000, immutable" in text
    assert re.search(r'location = /index.html \{[^}]*no-cache', text, flags=re.S)
    assert re.search(r"location = /healthz \{[^}]*return 200", text, flags=re.S)
    assert "proxy_pass" not in text                               # file server only


def test_dockerignore_keeps_secrets_and_bulk_out():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in ("**/node_modules", ".git", "**/.env", "**/.env.*", "backend",
                  "**/dist", ".claude"):
        assert entry in lines, entry
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_files.py -q`
Expected: FAIL (`FileNotFoundError`).

- [ ] **Step 3: Write `deploy/dashboard/Dockerfile`:**

```dockerfile
# Dashboard image (S2-07): the unchanged control-tower UI, built once, served as files.
# Build from the repository root:  docker build -f deploy/dashboard/Dockerfile .
# Stage "build" is Debian (glibc), not Alpine: the workspace keeps only the glibc Linux
# binaries of rollup, lightningcss and tailwind oxide (pnpm-workspace.yaml overrides).
FROM node:24.21.0-bookworm-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.15.1 --activate
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.base.json tsconfig.json ./
COPY artifacts/control-tower/package.json artifacts/control-tower/
COPY artifacts/api-server/package.json artifacts/api-server/
COPY scripts/package.json scripts/
RUN pnpm install --frozen-lockfile --filter @workspace/control-tower...
COPY artifacts/control-tower artifacts/control-tower
COPY scripts/check-strict-live-bundle.mjs scripts/
ENV PORT=8090 BASE_PATH=/ CONTROL_TOWER_MODE=live NODE_ENV=production
RUN pnpm run build:live && pnpm run check:strict-live

# Dashboard file server: hands out dist/ only. Non-root, port 8090, inside Docker only;
# the front door (deploy/nginx/conf.d/dashboard.conf) sends "/" here.
FROM nginxinc/nginx-unprivileged:1.28.0-alpine
COPY deploy/dashboard/file-server.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/artifacts/control-tower/dist/public /usr/share/nginx/html
EXPOSE 8090
```

Before you write the `COPY … package.json` lines, check that `artifacts/api-server/package.json` and `scripts/package.json` exist (they are the other workspace packages in `pnpm-workspace.yaml`). If one does not exist, remove its line and list it under "Deviations".

- [ ] **Step 4: Write `deploy/dashboard/file-server.conf`:**

```nginx
# Dashboard file server (S2-07), inside the dashboard image. It only hands out the built
# files. The front door sends "/" here; the dashboard API goes to the backend instead.
server {
    listen 8090;
    server_tokens off;
    root /usr/share/nginx/html;

    location = /healthz {
        access_log off;
        return 200 "ok\n";
    }
    # Hashed file names: safe to keep for a year.
    location /assets/ {
        try_files $uri =404;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
    # Always fetch the newest index.html, so a new deploy shows at once.
    location = /index.html {
        add_header Cache-Control "no-cache";
    }
    # Single-page app: unknown paths (/heatmap, /use-case/<id>) get index.html.
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
}
```

- [ ] **Step 5: Write `.dockerignore`** (repository root; it is used only by builds whose context is the root, which is the dashboard image; the backend image uses `backend/` and its own `.dockerignore`):

```
# Build context of deploy/dashboard/Dockerfile (S2-07). Keep secrets and bulk out.
.git
.claude
**/node_modules
**/dist
**/.env
**/.env.*
backend
docs
changes
attached_assets
```

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_dashboard_files.py -q`
Expected: PASS. (Do not run `docker build`; CI builds the image in Task 5.)

- [ ] **Step 7: Commit** (Claude): `feat(s2-07): dashboard image with the dashboard file server`

---

### Task 4: Front door port 8082 and the Compose service

**Files:**
- Create: `deploy/nginx/conf.d/dashboard.conf`
- Modify: `deploy/nginx/compose.local.yaml`, `deploy/nginx/compose.testhost.yaml`
- Modify: `deploy/compose/compose.yaml`, `deploy/compose/compose.local.yaml`, `deploy/compose/compose.testhost.yaml`
- Test: `backend/tests/test_nginx_files.py`, `backend/tests/test_compose_files.py`

**Interfaces:**
- Consumes: the dashboard image (Task 3) on port 8090; the backend alias `model-monitor-backend:8000`.
- Produces: front-door port 8082; Compose service `dashboard` with alias `model-monitor-dashboard`.

- [ ] **Step 1: Write the failing tests.** In `backend/tests/test_nginx_files.py`, change `test_nginx_ports_per_host` to:

```python
def test_nginx_ports_per_host():
    assert _load("compose.local.yaml")["services"]["nginx"]["ports"] == [
        "127.0.0.1:8080:8080", "127.0.0.1:3000:3000", "127.0.0.1:8082:8082"]
    assert _load("compose.testhost.yaml")["services"]["nginx"]["ports"] == [
        "80:8080", "3000:3000", "8082:8082"]
```

and add:

```python
def test_dashboard_conf_serves_only_get_and_four_api_paths():
    text = (CONF / "dashboard.conf").read_text(encoding="utf-8")
    assert "\r\n" not in text
    assert re.search(r"^\s*listen 8082;", text, flags=re.MULTILINE)
    assert "set $mm_backend http://model-monitor-backend:8000;" in text
    assert "set $mm_dashboard http://model-monitor-dashboard:8090;" in text
    locations = _locations(text)
    assert locations == ["= /api/live/portfolio", "^~ /api/live/use-case/",
                         "= /api/live/alerts", "= /api/version", "/api/", "/"]
    blocks = re.findall(r"location ([^{]+)\{(.*?)\n    \}", text, flags=re.S)
    for where, body in blocks:
        if where.strip() == "/api/":
            assert "return 404;" in body and "proxy_pass" not in body
        else:
            assert "limit_except GET { deny all; }" in body, where
            assert "proxy_pass" in body, where
    assert "batch/runs" not in text and "readiness" not in text and "otlp" not in text
```

If `CONF` is not defined in `test_nginx_files.py`, use the folder the other tests read (`deploy/nginx/conf.d`) under the name it already has.

In `backend/tests/test_compose_files.py`, add:

```python
def test_dashboard_service():
    base = _load("compose.yaml")["services"]["dashboard"]
    assert "ports" not in base and "build" not in base
    assert base["networks"] == {"edge": {"aliases": ["model-monitor-dashboard"]}}
    assert "127.0.0.1:8090/healthz" in " ".join(base["healthcheck"]["test"])
    assert base["restart"] == "unless-stopped"
    local = _load("compose.local.yaml")["services"]["dashboard"]
    assert local["build"] == {"context": "../..", "dockerfile": "deploy/dashboard/Dockerfile"}
    assert local["image"] == "model-monitor-dashboard:local"
    host = _load("compose.testhost.yaml")["services"]["dashboard"]
    assert host == {"image": "${DASHBOARD_IMAGE:?DASHBOARD_IMAGE is not set}"}
```

If an existing test asserts the exact set of services in `compose.yaml` or `compose.testhost.yaml` (for example `{"backend", "collector", "collector-init", "trace-check"}`), add `"dashboard"` to that set.

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py tests/test_compose_files.py -q`
Expected: FAIL.

- [ ] **Step 3: Write `deploy/nginx/conf.d/dashboard.conf`:**

```nginx
# Dashboard (S2-07): front-door port 8082. RAI team and engineers, through the IAP tunnel.
# GET only. "/" goes to the dashboard file server; only the four read-only API paths go to
# the backend. Every other /api/ path is 404, so the job API is never reachable here.
server {
    listen 8082;
    proxy_http_version 1.1;
    proxy_set_header Host $host;

    set $mm_backend http://model-monitor-backend:8000;
    set $mm_dashboard http://model-monitor-dashboard:8090;

    location = /api/live/portfolio {
        limit_except GET { deny all; }
        proxy_pass $mm_backend;
    }
    location ^~ /api/live/use-case/ {
        limit_except GET { deny all; }
        proxy_pass $mm_backend;
    }
    location = /api/live/alerts {
        limit_except GET { deny all; }
        proxy_pass $mm_backend;
    }
    location = /api/version {
        limit_except GET { deny all; }
        proxy_pass $mm_backend;
    }
    location /api/ {
        return 404;
    }
    location / {
        limit_except GET { deny all; }
        proxy_pass $mm_dashboard;
    }
}
```

- [ ] **Step 4: Publish port 8082.** `deploy/nginx/compose.local.yaml` ports become
`"127.0.0.1:8080:8080"`, `"127.0.0.1:3000:3000"`, `"127.0.0.1:8082:8082"`.
`deploy/nginx/compose.testhost.yaml` ports become `"80:8080"`, `"3000:3000"`, `"8082:8082"`,
and its comment block gets one line: `# Port 8082 (dashboard) is open only to the IAP range 35.235.240.0/20 (same rule).`

- [ ] **Step 5: Add the Compose service.** In `deploy/compose/compose.yaml`, after `trace-check`:

```yaml
  # Dashboard (S2-07): the built UI files, handed out by the dashboard file server on 8090.
  # No published port: the front door (deploy/nginx, port 8082) is the only way in.
  dashboard:
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8090/healthz"]
      interval: 5s
      timeout: 3s
      retries: 12
    restart: unless-stopped
    networks:
      edge:
        aliases: [model-monitor-dashboard]
```

In `deploy/compose/compose.local.yaml`:

```yaml
  dashboard:
    build:
      context: ../..
      dockerfile: deploy/dashboard/Dockerfile
    image: model-monitor-dashboard:local
```

In `deploy/compose/compose.testhost.yaml`:

```yaml
  dashboard:
    image: ${DASHBOARD_IMAGE:?DASHBOARD_IMAGE is not set}
```

and in its header comment: `# BACKEND_IMAGE and DASHBOARD_IMAGE come from the .env file in that folder (image names, not secrets); use the same run number for both.`

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_nginx_files.py tests/test_compose_files.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `feat(s2-07): front-door port 8082 and the dashboard service`

---

### Task 5: CI builds the image; the smoke test reaches the dashboard

**Files:**
- Modify: `.github/workflows/build-image.yml`, `.github/workflows/compose-smoke.yml`, `scripts/compose-smoke.sh`
- Test: `backend/tests/test_compose_files.py` (or the test file that already reads `build-image.yml` / `compose-smoke.sh`; search with `grep -rn "build-image\|compose-smoke" backend/tests`)

**Interfaces:**
- Consumes: Tasks 2 to 4.

- [ ] **Step 1: Write the failing tests** (add to `backend/tests/test_compose_files.py`; define `ROOT = Path(__file__).resolve().parents[2]` if it is not there):

```python
def test_build_image_builds_backend_and_dashboard():
    text = (ROOT / ".github" / "workflows" / "build-image.yml").read_text(encoding="utf-8")
    assert "/dev/backend" in text and "/dev/dashboard" in text
    assert "-f deploy/dashboard/Dockerfile" in text
    for path in ('"artifacts/control-tower/**"', '"deploy/dashboard/**"', '"pnpm-lock.yaml"'):
        assert path in text
    assert text.count("github.run_number") >= 1


def test_compose_smoke_reaches_the_dashboard():
    text = (ROOT / "scripts" / "compose-smoke.sh").read_text(encoding="utf-8")
    assert 'DASH="http://127.0.0.1:8082"' in text
    for check in ('"$DASH/"', '"$DASH/api/live/portfolio"',
                  '"$DASH/api/live/use-case/rtr-fraud-validation"',
                  '-X POST "$DASH/api/batch/runs"', '"$DASH/api/readiness"'):
        assert check in text, check
    workflow = (ROOT / ".github" / "workflows" / "compose-smoke.yml").read_text(encoding="utf-8")
    assert '"artifacts/control-tower/**"' in workflow and '"deploy/dashboard/**"' in workflow
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL.

- [ ] **Step 3: Change `.github/workflows/build-image.yml`.**
  - `name: Build images` and the header comment: "Pushes the backend and dashboard images (one run number for both)."
  - `on.push.paths` add: `"artifacts/control-tower/**"`, `"deploy/dashboard/**"`, `"pnpm-lock.yaml"`, `"pnpm-workspace.yaml"`.
  - `env` add: `DASHBOARD_IMAGE: ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/${{ vars.GAR_REPO }}/dev/dashboard`
  - After the backend "Smoke test the image" step, add:

```yaml
      - name: Build dashboard
        run: |
          docker build -f deploy/dashboard/Dockerfile \
            --label org.opencontainers.image.revision="${{ github.sha }}" \
            --label org.opencontainers.image.source="${{ github.server_url }}/${{ github.repository }}" \
            -t "$DASHBOARD_IMAGE:$TAG" .
      - name: Smoke test the dashboard image
        run: |
          docker run -d --name dash -p 127.0.0.1:18090:8090 "$DASHBOARD_IMAGE:$TAG"
          for i in $(seq 1 20); do curl -fsS http://127.0.0.1:18090/healthz && break; sleep 1; done
          curl -fsS http://127.0.0.1:18090/ | grep -q '<div id="root">'
          curl -fsS http://127.0.0.1:18090/heatmap | grep -q '<div id="root">'
          docker rm -f dash
```

  - Change the "Push" step to push both: `docker push "$IMAGE:$TAG"` and `docker push "$DASHBOARD_IMAGE:$TAG"`, and the summary line to name both images.

- [ ] **Step 4: Change `.github/workflows/compose-smoke.yml`.** In each `paths` list, add `"artifacts/control-tower/**"`, `"deploy/dashboard/**"` and `"pnpm-lock.yaml"`. (Open the file first; keep its structure.)

- [ ] **Step 5: Change `scripts/compose-smoke.sh`.** After `FRONT="http://127.0.0.1:8080"`, add `DASH="http://127.0.0.1:8082"   # front-door port of the dashboard (S2-07)`. After the "batch evaluation" step (S2-05) and before `SMOKE PASS`, add:

```bash
STEP="dashboard through the front door (S2-07)"
code "200" "$DASH/"
curl -fsS "$DASH/" | grep -q '<div id="root">'
code "200" "$DASH/heatmap"
curl -fsS "$DASH/api/live/portfolio" | python3 -c '
import json, sys
rows = {r["registry_id"]: r for r in json.load(sys.stdin)["rows"]}
row = rows["rtr-fraud-validation"]
assert row["grade"] is not None, "the run is not graded on the dashboard"'
curl -fsS "$DASH/api/live/use-case/rtr-fraud-validation" | python3 -c '
import json, sys
body = json.load(sys.stdin)
assert body["trace_id"] == sys.argv[1], "trace_id differs"
assert "payload" not in body' "$TRACE_ID"
# The job API is not on 8082: every unlisted /api/ path is 404 (Task 4), any method.
code "404" -X POST "$DASH/api/batch/runs" -H "Content-Type: application/json" --data '{}'
code "404" "$DASH/api/readiness"
code "403" -X POST "$DASH/api/live/portfolio"
# The dashboard API is not on the job port.
code "404" "$FRONT/api/live/portfolio"
```

Also add the dashboard logs to `cleanup()`: `"${COMPOSE[@]}" logs --no-color --tail 50 dashboard || true`.

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: PASS. (Do not run the script; CI runs it on the PR.)

- [ ] **Step 7: Commit** (Claude): `test(s2-07): CI builds the dashboard image; smoke reaches port 8082`

---

### Task 6: Docs

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `deploy/nginx/README.md` (if it lists the ports)

- [ ] **Step 1: TESTHOST — add the section "Dashboard (S2-07)"** after "Batch evaluator (S2-05)":

```markdown
## Dashboard (S2-07)

The **front door** (the nginx project) gets port 8082. The **dashboard** service holds the
built UI; its **dashboard file server** listens on 8090 inside Docker only.

1. From the laptop, open port 8082 to IAP (the same rule as Langfuse):

   ```sh
   gcloud compute firewall-rules update langfuse-testhost-allow-iap --rules tcp:3000,tcp:8082
   ```

2. Copy `deploy/nginx/conf.d/dashboard.conf` to `/opt/nginx/conf.d/`,
   `deploy/nginx/compose.testhost.yaml` to `/opt/nginx/`, and `deploy/compose/compose.yaml`
   and `deploy/compose/compose.testhost.yaml` to `/opt/model-monitor/compose/`.
3. In `/opt/model-monitor/compose/.env`, set `BACKEND_IMAGE` and `DASHBOARD_IMAGE` to the same
   run number of "Build images", then from `/opt/model-monitor/compose`:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml pull && sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

4. From `/opt/nginx`, restart the front door:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

5. On the laptop, open the tunnel, or forward port 8082 in the VS Code **Ports** panel:

   ```sh
   gcloud compute start-iap-tunnel ai-ml-monitoring-dev-env 8082 --local-host-port=localhost:8082 --zone asia-southeast3-c
   ```

   Open `http://localhost:8082`. The heatmap shows `rtr-fraud-validation` only.
```

- [ ] **Step 2: CHANGELOG** — under "Unreleased" / "Added", first item:

```markdown
- Dashboard for the GCP use cases (S2-07): the unchanged control-tower UI shows each
  registered use case with its latest run, freshness, grade, lanes and "Unknown" reasons,
  from the new read-only dashboard API (`/api/live/portfolio`, `/use-case/{id}`, `/alerts`).
  A `dashboard` image (built in CI) holds the UI; the front door serves it on port 8082.
```

- [ ] **Step 3: DEVLOG** — add at the top of "Work log" (em dash `—`, not `?`):

```markdown
### 2026-10-14 — S2-07: dashboard for the GCP use cases

- Built (Codex task by task from `changes/2026-10-14-s2-07-dashboard/plan.md`, reviewed
  by Claude after each task): `dashboard_view.py`, `api/dashboard_routes.py`,
  `deploy/dashboard/` (image and dashboard file server), front-door `dashboard.conf`
  (port 8082), Compose service `dashboard`, CI image build and smoke checks.
- Decisions: serving option A (dashboard image, front door routes); port 8082; the
  frontend does not change (lane mapping A); fixed names (front door, dashboard, dashboard
  file server, dashboard API, job API).
- Evidence: (Claude fills in after the review).
```

- [ ] **Step 4: issues.md** — at the end of the S2-07 "Changed 2026-10-09" paragraph, add:

```markdown
**Design 2026-10-14:** `changes/2026-10-14-s2-07-dashboard/` (intent, spec, plan). The
dashboard is on front-door port 8082 (IAP tunnel), not 8080. The Delivery metrics show on
the detail page only; the list pages keep the five existing lanes.
```

- [ ] **Step 5: `deploy/nginx/README.md`** — if it lists the ports of the front door, add `8082 — dashboard (S2-07)`.

- [ ] **Step 6: Run the docs tests.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py tests/test_nginx_files.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `docs(s2-07): dashboard runbook, changelog and devlog`
