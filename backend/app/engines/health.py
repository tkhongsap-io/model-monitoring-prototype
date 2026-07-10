"""Health engine — Sheet-3 grading + rollup (PRD Appendix C.2, normative pseudocode).

Pure functions, unit-tested against the C.2 table. Provenance: only hallucination_rate's
High band is inherited verbatim from Sheet-3 SL#2.1; the other seven bands are demo
defaults in the Sheet-3 band format.
"""
from __future__ import annotations

from dataclasses import dataclass

Health = str  # "Green" | "Amber" | "Red" | "Unknown"

HEALTH_RANK = {"Red": 3, "Amber": 2, "Unknown": 1, "Green": 0}

LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation", "Feedback & action loop"]


@dataclass(frozen=True)
class SignalSpec:
    key: str
    label: str
    lane: str
    direction: str          # lower_is_better | higher_is_better
    green_bar: float
    red_bar: float
    unit: str
    provenance: str


SIGNAL_SPECS: dict[str, SignalSpec] = {s.key: s for s in [
    SignalSpec("hallucination_rate", "Hallucination rate", "Quality",
               "lower_is_better", 0.02, 0.02, "fraction", "Sheet-3 (inherited)"),
    SignalSpec("groundedness", "Groundedness", "Quality",
               "higher_is_better", 0.85, 0.70, "score", "demo default"),
    SignalSpec("relevance", "Answer relevance", "Quality",
               "higher_is_better", 0.85, 0.70, "score", "demo default"),
    SignalSpec("pii_exposure_rate", "PII exposure rate", "Safety & security",
               "lower_is_better", 0.0, 0.01, "fraction", "demo default"),
    SignalSpec("p95_latency_s", "p95 latency", "Reliability",
               "lower_is_better", 4.0, 8.0, "seconds", "demo default"),
    SignalSpec("data_drift_share", "Share of drifted features", "Drift & degradation",
               "lower_is_better", 0.30, 0.50, "fraction of features", "demo default"),
    SignalSpec("estimated_roc_auc", "Estimated ROC-AUC (NannyML, label-free)", "Quality",
               "higher_is_better", 0.80, 0.72, "AUC", "demo default"),
    SignalSpec("realized_roc_auc", "Realized ROC-AUC (once labels arrive)", "Quality",
               "higher_is_better", 0.80, 0.72, "AUC", "demo default"),
    SignalSpec("acceptance_rate", "Offer acceptance rate", "Feedback & action loop",
               "higher_is_better", 0.15, 0.05, "fraction", "demo default"),
    SignalSpec("recommendation_drift", "Recommendation mix drift (TV distance)", "Drift & degradation",
               "lower_is_better", 0.30, 0.50, "TV distance", "demo default"),
]}


def evaluate(key: str, value: float | None) -> Health:
    """C.2 normative pseudocode: Red checked first; missing value -> Unknown."""
    spec = SIGNAL_SPECS.get(key)
    if spec is None or value is None:
        return "Unknown"
    if spec.direction == "lower_is_better":
        if value >= spec.red_bar:
            return "Red"
        if value <= spec.green_bar:
            return "Green"
        return "Amber"
    # higher_is_better
    if value < spec.red_bar:
        return "Red"
    if value >= spec.green_bar:
        return "Green"
    return "Amber"


def worst(healths: list[Health]) -> Health:
    if not healths:
        return "Unknown"
    return max(healths, key=lambda h: HEALTH_RANK.get(h, 1))


def rollup(signal_healths: dict[str, Health],
           excluded_keys: set[str] | None = None,
           hand_set_lanes: dict[str, Health] | None = None,
           excluded_lanes: set[str] | None = None) -> tuple[dict[str, Health], Health]:
    """Signal -> lane -> overall (worst-of). Reasoned exclusions (§A.1.4) are
    excluded from the rollup; hand-set lanes (e.g. Feedback) merge in; a hand-set
    lane in `excluded_lanes` (declared-reason Unknown) doesn't degrade overall."""
    excluded_keys = excluded_keys or set()
    lanes: dict[str, list[Health]] = {}
    for key, h in signal_healths.items():
        if key in excluded_keys:
            continue
        spec = SIGNAL_SPECS.get(key)
        lane = spec.lane if spec else "Quality"
        lanes.setdefault(lane, []).append(h)
    lane_health: dict[str, Health] = {lane: worst(hs) for lane, hs in lanes.items()}
    for lane, h in (hand_set_lanes or {}).items():
        lane_health.setdefault(lane, h)
    rollup_lanes = [h for lane, h in lane_health.items()
                    if lane not in (excluded_lanes or set())]
    return lane_health, worst(rollup_lanes)
