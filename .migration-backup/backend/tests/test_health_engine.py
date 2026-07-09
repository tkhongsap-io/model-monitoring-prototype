"""Health-engine table tests — PRD Appendix C.2 (grading) + §A.1.4 (rollup)."""
from app.engines.health import evaluate, rollup, worst


def test_hallucination_band_sheet3():
    # Coincident bars: Red checked first — exactly 2% grades Red (C.2 note 1)
    assert evaluate("hallucination_rate", 0.02) == "Red"
    assert evaluate("hallucination_rate", 0.035) == "Red"
    assert evaluate("hallucination_rate", 0.015) == "Green"
    assert evaluate("hallucination_rate", 0.010) == "Green"


def test_pii_band():
    # Green only at exactly 0; (0, 1%) Amber; >=1% Red (C.2 note 2)
    assert evaluate("pii_exposure_rate", 0.0) == "Green"
    assert evaluate("pii_exposure_rate", 0.005) == "Amber"
    assert evaluate("pii_exposure_rate", 0.01) == "Red"


def test_higher_is_better_bands():
    assert evaluate("groundedness", 0.90) == "Green"
    assert evaluate("groundedness", 0.75) == "Amber"   # numeric guard band
    assert evaluate("groundedness", 0.69) == "Red"
    assert evaluate("estimated_roc_auc", 0.80) == "Green"
    assert evaluate("estimated_roc_auc", 0.79) == "Amber"
    assert evaluate("estimated_roc_auc", 0.7199) == "Red"


def test_lower_is_better_bands():
    assert evaluate("data_drift_share", 0.30) == "Green"
    assert evaluate("data_drift_share", 0.375) == "Amber"
    assert evaluate("data_drift_share", 0.50) == "Red"
    assert evaluate("p95_latency_s", 3.4) == "Green"
    assert evaluate("p95_latency_s", 5.0) == "Amber"
    assert evaluate("p95_latency_s", 8.0) == "Red"


def test_missing_value_unknown():
    assert evaluate("data_drift_share", None) == "Unknown"
    assert evaluate("not_a_signal", 1.0) == "Unknown"


def test_worst_order():
    assert worst(["Green", "Unknown"]) == "Unknown"
    assert worst(["Green", "Amber", "Unknown"]) == "Amber"
    assert worst(["Amber", "Red"]) == "Red"
    assert worst([]) == "Unknown"


def test_rollup_reasoned_exclusion():
    healths = {"data_drift_share": "Red", "estimated_roc_auc": "Amber", "realized_roc_auc": "Unknown"}
    lanes, overall = rollup(
        healths, excluded_keys={"realized_roc_auc"},
        hand_set_lanes={"Feedback & action loop": "Unknown", "Safety & security": "Green",
                        "Reliability": "Green"},
        excluded_lanes={"Feedback & action loop"})
    assert lanes["Drift & degradation"] == "Red"
    assert lanes["Quality"] == "Amber"          # realized excluded, estimated Amber remains
    assert lanes["Feedback & action loop"] == "Unknown"  # visible in lanes...
    assert overall == "Red"                      # ...but excluded from the overall rollup


def test_rollup_unreasoned_unknown_degrades():
    lanes, overall = rollup({"data_drift_share": "Green"},
                            hand_set_lanes={"Feedback & action loop": "Unknown"})
    assert overall == "Unknown"  # unreasoned Unknown still degrades
