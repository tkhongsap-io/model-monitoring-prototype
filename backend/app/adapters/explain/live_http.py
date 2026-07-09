"""LiveHttpExplainAdapter — the LIVE counterpart of `LimeShapAdapter`.

Pulls the external model app's serialized model + reference/current windows and runs
LIME (per-instance, highest-churn-risk row) + SHAP (global importance) on the REAL
fitted model. Self-contained on purpose: it does NOT touch the determinism-critical
seeded LimeShapAdapter (that class's golden bake stays byte-identical). SHAP importance
is cached per pulled model version; every engine call degrades gracefully.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from ...datagen import churn
from ..base import ExplainResult, TickContext
from ..telemetry_http import pull, pull_model


class LiveHttpExplainAdapter:
    name = "live_http"

    def __init__(self, base_url: str, artifact_writer, model_name: str = "telco-churn",
                 seed: int = 42) -> None:
        self.base_url = base_url.rstrip("/")
        self.write_artifact = artifact_writer
        self.model_name = model_name
        self.seed = seed
        self._model = None
        self._version: int | None = None
        self._reference: pd.DataFrame | None = None    # reference FEATURE frame
        self._shap_png_by_version: dict[int, bytes] = {}

    def _ensure_model(self) -> None:
        model, version = pull_model(self.base_url)
        if version == self._version and self._model is not None:
            return
        self._model, self._version = model, version
        ref = pull(self.base_url, "/telemetry/reference")["records"]
        self._reference = pd.DataFrame([r["features"] for r in ref])[churn.FEATURES]

    def _shap_png(self, version: int) -> bytes | None:
        if version in self._shap_png_by_version:
            return self._shap_png_by_version[version]
        try:
            import matplotlib
            matplotlib.use("Agg")  # headless
            import matplotlib.pyplot as plt
            import shap
            sample = self._reference.sample(
                min(500, len(self._reference)), random_state=0).to_numpy(float)
            explainer = shap.TreeExplainer(self._model)  # churn app serves a RandomForest
            values = explainer.shap_values(sample)
            vals = values[1] if isinstance(values, list) else values
            if getattr(vals, "ndim", 2) == 3:            # (n, features, classes) on newer shap
                vals = vals[:, :, 1]
            shap.summary_plot(vals, sample, feature_names=churn.FEATURES,
                              show=False, plot_type="bar")
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format="png", dpi=110, bbox_inches="tight")
            plt.close("all")
            png = buf.getvalue()
            self._shap_png_by_version[version] = png
            return png
        except Exception:  # noqa: BLE001
            return None

    def explain(self, use_case_id: str, tick: TickContext) -> ExplainResult:
        res = ExplainResult()
        t = tick.tick
        try:
            self._ensure_model()
        except Exception as e:  # noqa: BLE001
            res.errors["explain"] = f"{type(e).__name__}: {e}"
            return res

        inf = pull(self.base_url, "/telemetry/inferences", {"tick": t})["records"]
        if not inf:
            res.errors["explain"] = "no inferences for tick"
            return res
        cur_feat = pd.DataFrame([r["features"] for r in inf])[churn.FEATURES]
        proba = np.asarray([float(r["churn_proba"]) for r in inf])

        # --- LIME: highest-predicted-churn-probability row, num_features=6 ---
        try:
            from lime.lime_tabular import LimeTabularExplainer
            idx = int(np.argmax(proba))
            cat_idx = [churn.FEATURES.index(c) for c in churn.CATEGORICAL]
            explainer = LimeTabularExplainer(
                training_data=self._reference.to_numpy(float),
                feature_names=churn.FEATURES, class_names=["stay", "churn"],
                categorical_features=cat_idx, discretize_continuous=True,
                mode="classification", random_state=self.seed)
            exp = explainer.explain_instance(
                cur_feat.to_numpy(float)[idx], self._model.predict_proba, num_features=6)
            res.lime_top = [[name, float(w)] for name, w in exp.as_list()]
            res.instance = {"index": idx, "churn_probability": float(proba[idx])}
            res.artifacts["lime_html"] = self.write_artifact("lime_html", t, exp.as_html(), "html")
        except Exception as e:  # noqa: BLE001
            res.errors["lime"] = f"{type(e).__name__}: {e}"

        # --- SHAP global importance (per model version) ---
        png = self._shap_png(self._version)
        if png is not None:
            res.artifacts["shap_png"] = self.write_artifact("shap_png", t, png, "png")
        else:
            res.errors.setdefault("shap", "shap unavailable or failed")
        return res
