"""Shared ML engine helpers — Evidently 0.4.x drift + NannyML CBPE — extracted so the
LIVE adapter (`live_http.py`) runs the SAME engines as the seeded `EvidentlyNannyMLAdapter`
WITHOUT touching that determinism-critical class (its golden bake stays byte-identical).

These operate on plain DataFrames: reference/current FEATURE frames for drift, and
`{FEATURES + y_pred_proba + y_pred [+ y_true]}` scored frames for CBPE.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from ...datagen import churn


def evidently_drift(reference_features: pd.DataFrame, current_features: pd.DataFrame,
                    features: list[str] | None = None,
                    categorical: list[str] | None = None) -> tuple[float | None, list[str], str]:
    """Evidently DataDrift + DataQuality; returns (share_of_drifted, drifted_cols, html).

    `features`/`categorical` default to the churn lists so existing callers are unchanged;
    live adapters pass the model-service-owned lists (contract v1.0)."""
    from evidently import ColumnMapping
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    from evidently.report import Report

    features = features if features is not None else churn.FEATURES
    categorical = categorical if categorical is not None else churn.CATEGORICAL
    numeric = [c for c in features if c not in categorical]
    cm = ColumnMapping(numerical_features=numeric,
                       categorical_features=categorical, target=None)
    report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    report.run(reference_data=reference_features[features],
               current_data=current_features[features], column_mapping=cm)
    share, drifted = None, []
    for m in report.as_dict().get("metrics", []):
        r = m.get("result", {})
        if "share_of_drifted_columns" in r:
            share = float(r["share_of_drifted_columns"])
        cols = r.get("drift_by_columns")
        if isinstance(cols, dict):
            drifted = [c for c, v in cols.items() if v.get("drift_detected")]
    buf = io.StringIO()
    report.save_html(buf)  # evidently 0.4.x accepts a file object
    return share, drifted, buf.getvalue()


def build_scored_frame(features: pd.DataFrame, proba, y_true=None,
                       feature_order: list[str] | None = None) -> pd.DataFrame:
    """CBPE input frame: FEATURES + y_pred_proba + y_pred [+ y_true].

    `feature_order` defaults to the churn list (existing callers unchanged)."""
    out = features[feature_order if feature_order is not None else churn.FEATURES].copy()
    p = np.asarray(proba, dtype=float)
    out["y_pred_proba"] = p
    out["y_pred"] = (p >= 0.5).astype(int)
    if y_true is not None:
        out["y_true"] = np.asarray(y_true, dtype=int)
    return out


def cbpe_fit(scored_reference: pd.DataFrame, chunk_size: int = 500):
    """Fit NannyML CBPE on a scored+labelled reference (raises on failure — caller degrades)."""
    import nannyml as nml
    est = nml.CBPE(problem_type="classification_binary",
                   y_pred_proba="y_pred_proba", y_pred="y_pred", y_true="y_true",
                   metrics=["roc_auc"], chunk_size=chunk_size)
    est.fit(scored_reference)
    return est


def cbpe_estimate(estimator, scored_current: pd.DataFrame) -> float | None:
    """Label-free estimated ROC-AUC over the current window (mean of per-chunk values)."""
    result = estimator.estimate(scored_current)
    df = result.to_df()
    vals = None
    try:
        vals = df[("roc_auc", "value")]
    except Exception:  # MultiIndex defensive extraction
        for col in df.columns:
            if isinstance(col, tuple) and col[0] == "roc_auc" and col[-1] == "value":
                vals = df[col]
                break
    return float(np.mean(vals)) if vals is not None else None
