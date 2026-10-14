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
