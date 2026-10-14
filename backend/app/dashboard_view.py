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
    return REASON_TEXT.get(reason, reason or "unknown") if isinstance(reason, str) else "unknown"


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
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return f"{name} Unknown: unknown"
    shown = f"{value * 100:.1f}%" if name == "failure_rate" else f"{value:.2f}"
    return f"{name} {shown} ({metric.get('health', 'Unknown')})"


def portfolio_row(use_case, run: dict | None, evaluation: dict | None, now: float) -> dict:
    metrics = _metrics(evaluation)
    lanes = {lane: "Unknown" for lane in UI_LANES}
    if run is None or evaluation is None:
        blank = "Unknown: no run yet" if run is None else "Unknown: not graded yet"
        tooltips = {lane: {"metric": blank} for lane in UI_LANES}
    else:
        failure, volume = metrics.get("failure_rate"), metrics.get("volume_change")
        lanes["Reliability"] = failure.get("health", "Unknown") if failure else "Unknown"
        lanes["Drift & degradation"] = volume.get("health", "Unknown") if volume else "Unknown"
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
