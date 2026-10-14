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
