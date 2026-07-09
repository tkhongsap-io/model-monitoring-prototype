"""ExplainAdapter `lime_shap` — LIME per-instance HTML + SHAP global-importance PNG.

Determinism (gotcha #9): LimeTabularExplainer gets random_state=seed; the SHAP
background sample uses random_state=0. SHAP global importance is recomputed per
model version (identical within one) and re-registered per tick.
"""
from __future__ import annotations

import numpy as np

from ...datagen import churn
from ..base import ExplainResult, TickContext


class LimeShapAdapter:
    name = "lime_shap"

    def __init__(self, seed: int, ml_world, artifact_writer) -> None:
        self.seed = seed
        self.world = ml_world               # the EvidentlyNannyMLAdapter (model + windows)
        self.write_artifact = artifact_writer
        self._shap_png_by_version: dict[int, bytes] = {}

    def _shap_png(self, version: int) -> bytes | None:
        if version in self._shap_png_by_version:
            return self._shap_png_by_version[version]
        try:
            import matplotlib
            matplotlib.use("Agg")  # headless (gotcha #7)
            import matplotlib.pyplot as plt
            import shap
            model = self.world.models[version]
            sample = self.world.reference[churn.FEATURES].sample(
                min(500, len(self.world.reference)), random_state=0).to_numpy(float)
            if hasattr(model, "named_steps"):  # StandardScaler + LogisticRegression pipeline
                scaler = model.named_steps.get("standardscaler")
                lr = model.named_steps.get("logisticregression")
                scaled = scaler.transform(sample)
                explainer = shap.LinearExplainer(lr, scaled)
                vals = explainer.shap_values(scaled)
                sample = scaled  # plot in scaled space; importance ranking unchanged
            else:  # tree model
                explainer = shap.TreeExplainer(model)
                values = explainer.shap_values(sample)
                vals = values[1] if isinstance(values, list) else values  # list on some versions (gotcha #6)
                if getattr(vals, "ndim", 2) == 3:  # (n, features, classes) on newer shap
                    vals = vals[:, :, 1]
            shap.summary_plot(vals, sample, feature_names=churn.FEATURES,
                              show=False, plot_type="bar")
            import io
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
        window = self.world.windows.get(t)
        if window is None:
            res.errors["explain"] = "no analysis window for tick"
            return res
        model = self.world.models[self.world.model_version]

        # --- LIME: highest-predicted-churn-probability row, num_features=6 ---
        try:
            from lime.lime_tabular import LimeTabularExplainer
            proba = model.predict_proba(window[churn.FEATURES].to_numpy(float))[:, 1]
            idx = int(np.argmax(proba))
            cat_idx = [churn.FEATURES.index(c) for c in churn.CATEGORICAL]
            explainer = LimeTabularExplainer(
                training_data=self.world.reference[churn.FEATURES].to_numpy(float),
                feature_names=churn.FEATURES, class_names=["stay", "churn"],
                categorical_features=cat_idx, discretize_continuous=True,
                mode="classification", random_state=self.seed)
            exp = explainer.explain_instance(
                window[churn.FEATURES].to_numpy(float)[idx], model.predict_proba, num_features=6)
            res.lime_top = [[name, float(w)] for name, w in exp.as_list()]
            res.instance = {"index": idx, "churn_probability": float(proba[idx])}
            res.artifacts["lime_html"] = self.write_artifact("lime_html", t, exp.as_html(), "html")
        except Exception as e:  # noqa: BLE001
            res.errors["lime"] = f"{type(e).__name__}: {e}"

        # --- SHAP global importance (per model version; re-registered per tick) ---
        png = self._shap_png(self.world.model_version)
        if png is not None:
            res.artifacts["shap_png"] = self.write_artifact("shap_png", t, png, "png")
        else:
            res.errors.setdefault("shap", "shap unavailable or failed")
        return res


def make_explain(seed: int, ml_world, artifact_writer, impl: str | None = None):
    """Factory for the ExplainAdapter (mirrors make_llm_eval, judge.py).

    The baker PINS impl="lime_shap" so the golden bake is byte-identical regardless
    of env; only the live runner passes impl=config.EXPLAIN_ADAPTER.
    """
    from ... import config
    impl = (impl or config.EXPLAIN_ADAPTER or "lime_shap").strip()
    if impl == "lime_shap":
        return LimeShapAdapter(seed, ml_world, artifact_writer)
    if impl == "live_http":
        # live: the ml_world slot carries {base_url, model_name} (built by the live runner)
        from .live_http import LiveHttpExplainAdapter
        cfg = ml_world
        return LiveHttpExplainAdapter(cfg["base_url"], artifact_writer,
                                      model_name=cfg.get("model_name", "telco-churn"), seed=seed)
    raise ValueError(f"unknown EXPLAIN_ADAPTER: {impl!r}")
