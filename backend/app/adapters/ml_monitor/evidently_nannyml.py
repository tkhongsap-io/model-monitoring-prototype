"""MLMonitorAdapter `evidently_nannyml` — Evidently 0.4.x drift + NannyML CBPE performance.

Owns the "ML world" for a bake: the reference window, the model (v1; v2 after
RETRAIN_REBASELINE), the per-tick analysis windows and their scoring history —
so realized ROC-AUC can be computed with the 3-tick label lag by the model version
that served each window. Every engine call is wrapped; a failure degrades the
signal to None (-> Unknown), never crashes the tick (gotcha #8).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ...datagen import churn
from ..base import LaneResult, TickContext


class EvidentlyNannyMLAdapter:
    name = "evidently_nannyml"

    def __init__(self, seed: int, cfg: dict, artifact_writer) -> None:
        """artifact_writer(kind, tick, content_bytes_or_str, ext) -> artifact_id"""
        self.seed = seed
        self.cfg = cfg
        self.write_artifact = artifact_writer
        self.label_lag = int(cfg.get("label_lag_ticks", 3))
        self.rows_per_tick = int(cfg.get("rows_per_tick", 500))
        self.chunk_size = int(cfg.get("nannyml_chunk_size", 500))
        self.model_version = 1
        self.windows: dict[int, pd.DataFrame] = {}       # tick -> analysis window
        self.window_model: dict[int, int] = {}           # tick -> model version that served it
        self.models: dict[int, object] = {}
        self.reference: pd.DataFrame | None = None
        self.reference_auc: float | None = None
        self._cbpe = None
        self._init_world()

    # ---------------------------------------------------------------- world setup

    def _train(self, df: pd.DataFrame):
        m = self.cfg.get("model", {})
        kind = m.get("kind", "logistic_regression")
        if kind == "random_forest":
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=int(m.get("n_estimators", 200)),
                max_depth=int(m.get("max_depth", 8)),
                min_samples_leaf=int(m.get("min_samples_leaf", 20)),
                random_state=self.seed, n_jobs=-1)
        else:  # logistic_regression (M1 calibration default — see simulation.yaml)
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import StandardScaler
            model = make_pipeline(StandardScaler(),
                                  LogisticRegression(max_iter=1000, random_state=self.seed))
        model.fit(df[churn.FEATURES].to_numpy(float), df[churn.TARGET].to_numpy(int))
        return model

    def _fit_cbpe(self) -> None:
        try:
            import nannyml as nml
            ref = self._scored_frame(self.reference, self.models[self.model_version])
            est = nml.CBPE(problem_type="classification_binary",
                           y_pred_proba="y_pred_proba", y_pred="y_pred", y_true="y_true",
                           metrics=["roc_auc"], chunk_size=self.chunk_size)
            est.fit(ref)
            self._cbpe = est
        except Exception as e:  # noqa: BLE001
            self._cbpe = e  # remembered error -> degraded signal

    def _init_world(self) -> None:
        self.reference = churn.reference_window(self.seed, int(self.cfg.get("reference_rows", 4000)))
        self.models[1] = self._train(self.reference)
        self.reference_auc = self._auc(self.reference, self.models[1])
        self._fit_cbpe()
        # pre-history: 3 baseline windows at t=-3..-1 so realized is populated from tick 0
        for t in range(-int(self.cfg.get("prehistory_ticks", 3)), 0):
            w = churn.analysis_window(self.seed, t, alpha=0.0, n_rows=self.rows_per_tick)
            self.windows[t] = w
            self.window_model[t] = 1

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _auc(df: pd.DataFrame, model) -> float | None:
        try:
            from sklearn.metrics import roc_auc_score
            proba = model.predict_proba(df[churn.FEATURES].to_numpy(float))[:, 1]
            return float(roc_auc_score(df[churn.TARGET].to_numpy(int), proba))
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _scored_frame(df: pd.DataFrame, model) -> pd.DataFrame:
        proba = model.predict_proba(df[churn.FEATURES].to_numpy(float))[:, 1]
        out = df[churn.FEATURES].copy()
        out["y_pred_proba"] = proba
        out["y_pred"] = (proba >= 0.5).astype(int)
        out["y_true"] = df[churn.TARGET].to_numpy(int)
        return out

    def retrain_rebaseline(self, tick: int) -> None:
        """S5 RETRAIN_REBASELINE: model v2 on the last 3 label-arrived drifted windows;
        reference window reset to the current (drifted) distribution (§A.5.5)."""
        arrived = [t for t in sorted(self.windows) if t >= 0 and t <= tick - self.label_lag]
        train_ticks = arrived[-3:] if len(arrived) >= 3 else arrived
        frames = [self.windows[t] for t in train_ticks] or [self.reference]
        self.model_version = 2
        self.models[2] = self._train(pd.concat(frames, ignore_index=True))
        self.reference = churn.drifted_reference_window(self.seed, int(self.cfg.get("reference_rows", 4000)))
        self.reference_auc = self._auc(self.reference, self.models[2])
        self._fit_cbpe()

    # ---------------------------------------------------------------- per-tick

    def monitor(self, use_case_id: str, tick: TickContext) -> LaneResult:
        res = LaneResult()
        alpha = float(tick.inject.get("churn_alpha", 0.0))
        t = tick.tick
        window = churn.analysis_window(self.seed, t, alpha, self.rows_per_tick)
        self.windows[t] = window
        self.window_model[t] = self.model_version
        model = self.models[self.model_version]

        # --- Evidently drift (0.4.x API) ---
        try:
            from evidently import ColumnMapping
            from evidently.metric_preset import DataDriftPreset, DataQualityPreset
            from evidently.report import Report
            numeric = [c for c in churn.FEATURES if c not in churn.CATEGORICAL]
            cm = ColumnMapping(numerical_features=numeric,
                               categorical_features=churn.CATEGORICAL, target=None)
            report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
            report.run(reference_data=self.reference[churn.FEATURES],
                       current_data=window[churn.FEATURES], column_mapping=cm)
            share, drifted = None, []
            for m in report.as_dict().get("metrics", []):
                r = m.get("result", {})
                if "share_of_drifted_columns" in r:
                    share = float(r["share_of_drifted_columns"])
                cols = r.get("drift_by_columns")
                if isinstance(cols, dict):
                    drifted = [c for c, v in cols.items() if v.get("drift_detected")]
            res.signals["data_drift_share"] = share
            res.records = drifted  # drifted feature names
            import io
            buf = io.StringIO()
            report.save_html(buf)  # evidently 0.4.x accepts a filename or file object
            res.artifacts["evidently_html"] = self.write_artifact(
                "evidently_html", t, buf.getvalue(), "html")
        except Exception as e:  # noqa: BLE001
            res.signals["data_drift_share"] = None
            res.errors["evidently"] = f"{type(e).__name__}: {e}"

        # --- NannyML CBPE estimated ROC-AUC (label-free) ---
        try:
            if isinstance(self._cbpe, Exception):
                raise self._cbpe
            est_frame = self._scored_frame(window, model)
            result = self._cbpe.estimate(est_frame)
            df = result.to_df()
            vals = None
            try:
                vals = df[("roc_auc", "value")]
            except Exception:  # MultiIndex defensive extraction (gotcha #5)
                for col in df.columns:
                    if isinstance(col, tuple) and col[0] == "roc_auc" and col[-1] == "value":
                        vals = df[col]
                        break
            res.signals["estimated_roc_auc"] = float(np.mean(vals)) if vals is not None else None
        except Exception as e:  # noqa: BLE001
            res.signals["estimated_roc_auc"] = None
            res.errors["nannyml"] = f"{type(e).__name__}: {e}"

        # --- realized ROC-AUC (label lag; scored by the model version that served it) ---
        lag_t = t - self.label_lag
        realized, pending_reason = None, None
        if lag_t in self.windows:
            served_by = self.window_model.get(lag_t, 1)
            if served_by != self.model_version:
                pending_reason = "post-remediation label lag"  # legacy cohort — pre-retrain (§A.5.5)
            else:
                realized = self._auc(self.windows[lag_t], self.models[served_by])
        res.signals["realized_roc_auc"] = realized
        if pending_reason:
            res.errors["realized_pending"] = pending_reason

        res.records = {"drifted_features": res.records if isinstance(res.records, list) else [],
                       "reference_auc": self.reference_auc,
                       "model_version": self.model_version,
                       "realized_pending_reason": pending_reason,
                       "realized_window_tick": lag_t if lag_t in self.windows else None}
        return res


def make_ml_monitor(seed: int, cfg: dict, artifact_writer, impl: str | None = None):
    """Factory for the MLMonitorAdapter (mirrors make_llm_eval, judge.py).

    The baker PINS impl="evidently_nannyml" so the golden bake is byte-identical
    regardless of env; only the live runner passes impl=config.ML_MONITOR_ADAPTER.
    """
    from ... import config
    impl = (impl or config.ML_MONITOR_ADAPTER or "evidently_nannyml").strip()
    if impl == "evidently_nannyml":
        return EvidentlyNannyMLAdapter(seed, cfg, artifact_writer)
    if impl == "live_http":
        from .live_http import LiveHttpMLAdapter  # added in Stage 2 (live path)
        return LiveHttpMLAdapter(seed, cfg, artifact_writer)
    raise ValueError(f"unknown ML_MONITOR_ADAPTER: {impl!r}")
