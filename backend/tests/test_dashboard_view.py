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


def test_malformed_metric_fields_never_raise():
    for bad_metric in (
        {"name": "failure_rate", "value": 0.002},
        metric("failure_rate", "Reliability", "bad", "Green"),
        metric("failure_rate", "Reliability", None, "Unknown", ["invalid_counts"]),
    ):
        evaluation = {**EVAL, "metrics": json.dumps([bad_metric])}
        row = v.portfolio_row(UC, RUN, evaluation, NOW)
        assert isinstance(row["tooltips"]["Reliability"]["metric"], str)
        assert len(v.detail(UC, RUN, evaluation, [], NOW)["signals"]) == 6


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
