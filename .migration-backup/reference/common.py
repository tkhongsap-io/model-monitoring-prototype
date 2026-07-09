"""Small shared helpers: JSON IO and the proposal's Sheet-3 threshold model.

`SIGNAL_SPECS` and `evaluate_signal()` encode §10 of the RAI proposal — the Sheet-3
Green / Amber / Red bands and the colour->action-severity map — so both the ML lane
and the LLM lane grade their signals through the exact same logic the playbook describes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Health = Literal["Green", "Amber", "Red", "Unknown"]
Direction = Literal["lower_is_better", "higher_is_better"]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class SignalSpec:
    """One monitored signal and its Sheet-3 Green/Red bar (Amber is behavioural, §10)."""
    key: str
    label: str
    lane: str            # one of the five monitoring lanes (§10)
    direction: Direction
    green_max: float | None = None   # lower_is_better: Green while <= green_max
    red_at: float | None = None      # lower_is_better: Red once >= red_at
    green_min: float | None = None   # higher_is_better: Green while >= green_min
    red_below: float | None = None   # higher_is_better: Red once < red_below
    unit: str = ""


# Thresholds tuned for a *High-risk* use case (proposal §10 worked example: hallucination
# <1% go-live / <2% continue / >=2% escalate). These are the demo defaults; in production
# they are set per use case at onboarding from Sheet-3.
SIGNAL_SPECS: dict[str, SignalSpec] = {
    # --- LLM lane (HR chatbot) ---
    "hallucination_rate": SignalSpec(
        "hallucination_rate", "Hallucination rate", "Quality",
        "lower_is_better", green_max=0.02, red_at=0.02, unit="%"),
    "groundedness": SignalSpec(
        "groundedness", "Groundedness", "Quality",
        "higher_is_better", green_min=0.85, red_below=0.70),
    "relevance": SignalSpec(
        "relevance", "Answer relevance", "Quality",
        "higher_is_better", green_min=0.85, red_below=0.70),
    "pii_exposure_rate": SignalSpec(
        "pii_exposure_rate", "PII exposure rate", "Safety & security",
        "lower_is_better", green_max=0.0, red_at=0.01, unit="%"),
    "p95_latency_s": SignalSpec(
        "p95_latency_s", "p95 latency", "Reliability",
        "lower_is_better", green_max=4.0, red_at=8.0, unit="s"),
    # --- classical ML lane (churn) ---
    "data_drift_share": SignalSpec(
        "data_drift_share", "Share of drifted features", "Drift & degradation",
        "lower_is_better", green_max=0.30, red_at=0.50, unit="frac"),
    "estimated_roc_auc": SignalSpec(
        "estimated_roc_auc", "Estimated ROC-AUC (NannyML, label-free)", "Quality",
        "higher_is_better", green_min=0.80, red_below=0.72),
    "realized_roc_auc": SignalSpec(
        "realized_roc_auc", "Realised ROC-AUC (once labels arrive)", "Quality",
        "higher_is_better", green_min=0.80, red_below=0.72),
}


def evaluate_signal(key: str, value: float | None) -> Health:
    """Grade one signal value to Green/Red per its Sheet-3 bars, or Unknown if missing.
    (Amber is assigned at the lane/registry level from trend + data-gap rules, §10.)"""
    spec = SIGNAL_SPECS.get(key)
    if spec is None or value is None:
        return "Unknown"
    if spec.direction == "lower_is_better":
        if spec.red_at is not None and value >= spec.red_at:
            return "Red"
        if spec.green_max is not None and value <= spec.green_max:
            return "Green"
        return "Amber"
    else:  # higher_is_better
        if spec.red_below is not None and value < spec.red_below:
            return "Red"
        if spec.green_min is not None and value >= spec.green_min:
            return "Green"
        return "Amber"


HEALTH_RANK: dict[Health, int] = {"Red": 3, "Amber": 2, "Unknown": 1, "Green": 0}


def worst(healths: list[Health]) -> Health:
    if not healths:
        return "Unknown"
    return max(healths, key=lambda h: HEALTH_RANK[h])
