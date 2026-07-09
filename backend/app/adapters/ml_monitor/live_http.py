"""LiveHttpMLAdapter — the LIVE counterpart of `EvidentlyNannyMLAdapter`.

Instead of generating synthetic data internally, it PULLS raw telemetry from an
external model app (churn/NBA) over HTTP and runs the monitor's OWN engines on it:
  - reference + current FEATURE windows  -> Evidently drift  -> data_drift_share
  - reference scored by the pulled model -> NannyML CBPE fit  -> estimated_roc_auc
  - current proba + lagged labels         -> roc_auc_score    -> realized_roc_auc

ALL monitoring intelligence stays in the monitor; the model app only emits raw data +
its serialized model. Every engine call degrades to None (Unknown) on failure, never
crashing the tick — matching the seeded adapter's contract.
"""
from __future__ import annotations

import pandas as pd
from sklearn.metrics import roc_auc_score

from ...datagen import churn
from ..base import LaneResult, TickContext
from ..telemetry_http import pull, pull_model
from . import engines


class LiveHttpMLAdapter:
    name = "live_http"

    def __init__(self, base_url: str, artifact_writer, chunk_size: int = 500,
                 model_name: str = "telco-churn") -> None:
        self.base_url = base_url.rstrip("/")
        self.write_artifact = artifact_writer
        self.chunk_size = chunk_size
        self.model_name = model_name
        self._version: int | None = None
        self._cbpe = None                       # fitted estimator or remembered Exception
        self._reference_features: pd.DataFrame | None = None
        self._reference_auc: float | None = None

    # -- refit the CBPE baseline whenever the app's served model version changes --
    def _ensure_baseline(self) -> None:
        model, version = pull_model(self.base_url)
        if version == self._version and self._cbpe is not None:
            return
        self._version = version
        ref = pull(self.base_url, "/telemetry/reference")["records"]
        ref_feat = pd.DataFrame([r["features"] for r in ref])[churn.FEATURES]
        ref_labels = [int(r["label"]) for r in ref]
        proba = model.predict_proba(ref_feat.to_numpy(float))[:, 1]
        self._reference_features = ref_feat
        self._reference_auc = float(roc_auc_score(ref_labels, proba))
        try:
            self._cbpe = engines.cbpe_fit(
                engines.build_scored_frame(ref_feat, proba, ref_labels), self.chunk_size)
        except Exception as e:  # noqa: BLE001 — remember; degrade estimated signal
            self._cbpe = e

    def monitor(self, use_case_id: str, tick: TickContext) -> LaneResult:
        res = LaneResult()
        t = tick.tick
        try:
            self._ensure_baseline()
        except Exception as e:  # noqa: BLE001 — model/reference unreachable
            for k in ("data_drift_share", "estimated_roc_auc", "realized_roc_auc"):
                res.signals[k] = None
            res.errors["telemetry"] = f"{type(e).__name__}: {e}"
            return res

        inf = pull(self.base_url, "/telemetry/inferences", {"tick": t})["records"]
        cur_feat = pd.DataFrame([r["features"] for r in inf])[churn.FEATURES]
        cur_proba = [float(r["churn_proba"]) for r in inf]

        # --- Evidently drift ---
        drifted: list[str] = []
        try:
            share, drifted, html = engines.evidently_drift(self._reference_features, cur_feat)
            res.signals["data_drift_share"] = share
            res.artifacts["evidently_html"] = self.write_artifact("evidently_html", t, html, "html")
        except Exception as e:  # noqa: BLE001
            res.signals["data_drift_share"] = None
            res.errors["evidently"] = f"{type(e).__name__}: {e}"

        # --- NannyML CBPE estimated ROC-AUC (label-free) ---
        try:
            if isinstance(self._cbpe, Exception):
                raise self._cbpe
            res.signals["estimated_roc_auc"] = engines.cbpe_estimate(
                self._cbpe, engines.build_scored_frame(cur_feat, cur_proba))
        except Exception as e:  # noqa: BLE001
            res.signals["estimated_roc_auc"] = None
            res.errors["nannyml"] = f"{type(e).__name__}: {e}"

        # --- realized ROC-AUC once the lagged labels arrive ---
        labels = pull(self.base_url, "/telemetry/labels", {"tick": t})["records"]
        realized, pending = None, None
        if labels:
            lab = {l["inference_id"]: int(l["label"]) for l in labels}
            y_true = [lab.get(r["inference_id"]) for r in inf]
            if all(v is not None for v in y_true):
                realized = float(roc_auc_score(y_true, cur_proba))
        else:
            pending = "label lag"
        res.signals["realized_roc_auc"] = realized
        if pending:
            res.errors["realized_pending"] = pending

        res.records = {"drifted_features": drifted, "reference_auc": self._reference_auc,
                       "model_version": self._version, "realized_pending_reason": pending,
                       "realized_window_tick": t}
        return res
