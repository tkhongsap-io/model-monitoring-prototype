"""Classical-ML monitoring lane (churn / next-best-action stand-in).

Trains a scikit-learn churn model on the reference window, then monitors the drifted
analysis window with the proposal's open-stack tools:
  - Evidently  -> data drift + quality  (Drift & degradation lane)
  - NannyML    -> label-free performance estimation (Quality lane, before labels arrive)
  - LIME       -> per-prediction explanation (explainability; SHAP added if available)

Produces artifacts (HTML/PNG) + a signals dict the control tower grades against Sheet-3.
Every heavy import is wrapped so a missing/incompatible library degrades that signal to
`Unknown` instead of crashing the whole lane.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

from common import write_json
from config import Config
from data_gen import CATEGORICAL, FEATURES, TARGET, generate_churn

USE_CASE_ID = "UC-CHURN-01"
USE_CASE_NAME = "Churn / Next-Best-Action model"


def _train(reference: pd.DataFrame, seed: int) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=20, random_state=seed, n_jobs=-1
    )
    model.fit(reference[FEATURES].to_numpy(float), reference[TARGET].to_numpy(int))
    return model


def _score(model: RandomForestClassifier, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    proba = model.predict_proba(df[FEATURES].to_numpy(float))[:, 1]
    pred = (proba >= 0.5).astype(int)
    return proba, pred


def _run_evidently(reference: pd.DataFrame, analysis: pd.DataFrame, out_html: Path) -> dict:
    try:
        from evidently import ColumnMapping
        from evidently.metric_preset import DataDriftPreset, DataQualityPreset
        from evidently.report import Report
    except Exception as e:  # noqa: BLE001
        return {"share": None, "drifted_features": [], "error": f"evidently unavailable: {e}"}

    numeric = [c for c in FEATURES if c not in CATEGORICAL]
    cm = ColumnMapping(numerical_features=numeric, categorical_features=CATEGORICAL, target=None)
    report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    report.run(reference_data=reference[FEATURES], current_data=analysis[FEATURES], column_mapping=cm)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(out_html))

    share, drifted = None, []
    for m in report.as_dict().get("metrics", []):
        res = m.get("result", {})
        if "share_of_drifted_columns" in res:
            share = res.get("share_of_drifted_columns")
        cols = res.get("drift_by_columns")
        if isinstance(cols, dict):
            drifted = [c for c, v in cols.items() if v.get("drift_detected")]
    return {"share": share, "drifted_features": drifted, "html": str(out_html)}


def _run_nannyml(reference: pd.DataFrame, analysis: pd.DataFrame,
                 ref_proba, ref_pred, ana_proba, ana_pred) -> dict:
    try:
        import nannyml as nml
    except Exception as e:  # noqa: BLE001
        return {"estimated_roc_auc": None, "error": f"nannyml unavailable: {e}"}

    ref = reference[FEATURES].copy()
    ref["y_pred_proba"], ref["y_pred"], ref["y_true"] = ref_proba, ref_pred, reference[TARGET].to_numpy(int)
    ana = analysis[FEATURES].copy()
    ana["y_pred_proba"], ana["y_pred"], ana["y_true"] = ana_proba, ana_pred, analysis[TARGET].to_numpy(int)

    estimator = nml.CBPE(
        problem_type="classification_binary",
        y_pred_proba="y_pred_proba", y_pred="y_pred", y_true="y_true",
        metrics=["roc_auc"], chunk_size=1000,
    )
    estimator.fit(ref)
    result = estimator.estimate(ana)
    df = result.to_df()
    # extract the estimated roc_auc value column across chunks, averaged
    est_vals = None
    try:
        est_vals = df[("roc_auc", "value")]
    except Exception:  # noqa: BLE001
        for col in df.columns:
            if isinstance(col, tuple) and col[0] == "roc_auc" and col[-1] == "value":
                est_vals = df[col]
                break
    estimated = float(np.mean(est_vals)) if est_vals is not None else None
    return {"estimated_roc_auc": estimated}


def _run_lime(model, reference: pd.DataFrame, analysis: pd.DataFrame,
              ana_proba, out_html: Path) -> dict:
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except Exception as e:  # noqa: BLE001
        return {"top": [], "error": f"lime unavailable: {e}"}

    cat_idx = [FEATURES.index(c) for c in CATEGORICAL]
    explainer = LimeTabularExplainer(
        training_data=reference[FEATURES].to_numpy(float),
        feature_names=FEATURES, class_names=["stay", "churn"],
        categorical_features=cat_idx, discretize_continuous=True, mode="classification",
    )
    idx = int(np.argmax(ana_proba))  # explain the highest-risk customer
    exp = explainer.explain_instance(
        analysis[FEATURES].to_numpy(float)[idx], model.predict_proba, num_features=6
    )
    out_html.parent.mkdir(parents=True, exist_ok=True)
    exp.save_to_file(str(out_html))
    return {"top": exp.as_list(), "instance_index": idx,
            "instance_churn_proba": float(ana_proba[idx]), "html": str(out_html)}


def _run_shap(model, reference: pd.DataFrame, out_png: Path) -> dict:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import shap
    except Exception as e:  # noqa: BLE001
        return {"error": f"shap unavailable: {e}"}
    try:
        sample = reference[FEATURES].sample(min(500, len(reference)), random_state=0).to_numpy(float)
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_values(sample)
        vals = values[1] if isinstance(values, list) else values
        shap.summary_plot(vals, sample, feature_names=FEATURES, show=False, plot_type="bar")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(out_png, dpi=110, bbox_inches="tight")
        plt.close()
        return {"png": str(out_png)}
    except Exception as e:  # noqa: BLE001
        return {"error": f"shap failed: {e}"}


def run_ml_lane(cfg: Config) -> dict:
    cfg.ensure_dirs()
    art = cfg.artifacts_dir
    reference, analysis = generate_churn(seed=cfg.seed)

    model = _train(reference, cfg.seed)
    ref_proba, ref_pred = _score(model, reference)
    ana_proba, ana_pred = _score(model, analysis)

    realized_auc = float(roc_auc_score(analysis[TARGET], ana_proba))
    reference_auc = float(roc_auc_score(reference[TARGET], ref_proba))

    ev = _run_evidently(reference, analysis, art / "churn_evidently.html")
    nm = _run_nannyml(reference, analysis, ref_proba, ref_pred, ana_proba, ana_pred)
    lime = _run_lime(model, reference, analysis, ana_proba, art / "churn_lime.html")
    shap_res = _run_shap(model, reference, art / "churn_shap.png")

    result = {
        "use_case_id": USE_CASE_ID,
        "name": USE_CASE_NAME,
        "type": "Prediction model",
        "risk_tier": "High",
        "signals": {
            "data_drift_share": ev.get("share"),
            "estimated_roc_auc": nm.get("estimated_roc_auc"),
            "realized_roc_auc": realized_auc,
        },
        "context": {
            "reference_roc_auc": reference_auc,
            "drifted_features": ev.get("drifted_features", []),
            "lime_top": lime.get("top", []),
            "lime_instance": {
                "index": lime.get("instance_index"),
                "churn_proba": lime.get("instance_churn_proba"),
            },
        },
        "artifacts": {
            "evidently_html": ev.get("html"),
            "lime_html": lime.get("html"),
            "shap_png": shap_res.get("png"),
        },
        "errors": {k: v for k, v in {
            "evidently": ev.get("error"), "nannyml": nm.get("error"),
            "lime": lime.get("error"), "shap": shap_res.get("error"),
        }.items() if v},
    }
    write_json(art / "signals_churn.json", result)
    return result


if __name__ == "__main__":
    from config import load_config
    r = run_ml_lane(load_config())
    print("ML lane signals:", r["signals"])
    if r["errors"]:
        print("ML lane degraded:", r["errors"])
