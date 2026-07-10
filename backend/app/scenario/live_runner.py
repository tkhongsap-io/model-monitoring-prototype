"""Live runner — the monitor's LIVE observation of an external model app.

On each tick() it advances its read position, pulls the current telemetry window
through the LIVE adapters (which reach OUT to the model app over HTTP), grades the
signals with the SAME health engine the baker uses (Green/Amber/Red rollup), and stores
the graded payload. It is kept ENTIRELY SEPARATE from the baked scenario player/baker
— those stay byte-deterministic and untouched. tick() does sync HTTP + heavy engine
work, so callers run it in a worker thread (never the event loop).
"""
from __future__ import annotations

import threading

from .. import config
from ..adapters.base import TickContext
from ..adapters.explain.lime_shap import make_explain
from ..adapters.llm_eval.judge import make_llm_eval
from ..adapters.ml_monitor.evidently_nannyml import make_ml_monitor
from ..engines import health
from .baker import _artifact_writer_factory

LIVE_UC = "AICT-L01"      # the live churn use case (ML lane)
LIVE_LLM_UC = "AICT-L02"  # the live chatbot use case (LLM lane)

# non-ML lanes hand-set for an ML use case (mirrors the baker's P02 rollup, §A.1.4)
_HAND_SET = {"Feedback & action loop": "Unknown", "Safety & security": "Green", "Reliability": "Green"}
_EXCLUDED_LANES = {"Feedback & action loop"}

# lanes an LLM use case doesn't produce signals for (its Quality/Safety/Reliability lanes
# come from the 5 LLM signals); Drift is assumed clean, Feedback is declared-Unknown.
_HAND_SET_LLM = {"Drift & degradation": "Green", "Feedback & action loop": "Unknown"}
_EXCLUDED_LANES_LLM = {"Feedback & action loop"}


def _signal_view(sig: dict, s_health: dict, extra: dict | None = None) -> dict:
    """Shape a signals dict {key -> {value, health, label, lane, ...}} for the UI."""
    specs = health.SIGNAL_SPECS
    out = {}
    for k, v in sig.items():
        sp = specs.get(k)
        out[k] = {
            "value": None if v is None else round(float(v), 4), "health": s_health[k],
            "label": sp.label if sp else k, "lane": sp.lane if sp else "Quality",
            "unit": sp.unit if sp else "", "direction": sp.direction if sp else "",
            "green_bar": sp.green_bar if sp else None, "red_bar": sp.red_bar if sp else None,
            **((extra or {}).get(k, {}))}
    return out


class LiveRunner:
    def __init__(self, churn_url: str | None = None, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else config.DEMO_SEED
        base = churn_url or config.LIVE_CHURN_URL
        writer = _artifact_writer_factory("LIVE")
        cfg = {"base_url": base, "chunk_size": 500, "model_name": "telco-churn"}
        self.ml = make_ml_monitor(self.seed, cfg, writer, impl="live_http")
        self.explain = make_explain(self.seed, cfg, writer, impl="live_http")
        self._read_tick = 0
        self._current: dict | None = None
        self._lock = threading.Lock()

    def _grade(self, ml_res, ex_res, t: int) -> dict:
        sig = dict(ml_res.signals)
        s_health = {k: health.evaluate(k, v) for k, v in sig.items()}
        records = ml_res.records if isinstance(ml_res.records, dict) else {}
        pending = records.get("realized_pending_reason")
        excluded = {"realized_roc_auc"} if pending else set()
        if pending:
            s_health["realized_roc_auc"] = "Unknown"  # reasoned-Unknown, excluded from rollup
        lanes, overall = health.rollup(
            s_health, excluded_keys=excluded,
            hand_set_lanes=_HAND_SET, excluded_lanes=_EXCLUDED_LANES)
        specs = health.SIGNAL_SPECS
        signals = {}
        for k, v in sig.items():
            sp = specs.get(k)
            signals[k] = {
                "value": None if v is None else round(float(v), 4), "health": s_health[k],
                "label": sp.label if sp else k, "lane": sp.lane if sp else "Quality",
                "unit": sp.unit if sp else "", "direction": sp.direction if sp else "",
                "green_bar": sp.green_bar if sp else None, "red_bar": sp.red_bar if sp else None,
                **({"pending_reason": pending} if k == "realized_roc_auc" and pending else {})}
        return {
            "use_case_id": LIVE_UC, "tick": t, "mode": "live",
            "signals": signals, "lanes": lanes, "overall": overall,
            "drifted_features": records.get("drifted_features", []),
            "reference_auc": records.get("reference_auc"),
            "model_version": records.get("model_version"),
            "realized_pending_reason": pending,
            "lime_top": ex_res.lime_top, "lime_instance": ex_res.instance,
            "artifacts": {**ml_res.artifacts, **ex_res.artifacts},
            "errors": {**ml_res.errors, **ex_res.errors},
        }

    def tick(self) -> dict:
        """Observe the next telemetry window, grade it, store + return the payload."""
        with self._lock:
            t = self._read_tick
            ctx = TickContext(tick=t, seed=self.seed, scenario_id="LIVE")
            ml_res = self.ml.monitor(LIVE_UC, ctx)
            ex_res = self.explain.explain(LIVE_UC, ctx)
            payload = self._grade(ml_res, ex_res, t)
            self._current = payload
            self._read_tick += 1
            return payload

    def state(self) -> dict | None:
        return self._current


class LiveLLMRunner:
    """LIVE observation of an external chatbot: pull traces -> LLM-as-judge -> grade the
    LLM lanes with the SAME health engine. Separate from the baked player (byte-deterministic
    and untouched). tick() does sync HTTP + judging, so callers run it in a worker thread."""

    def __init__(self, chatbot_url: str | None = None, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else config.DEMO_SEED
        base = chatbot_url or config.LIVE_CHATBOT_URL
        cfg = {"base_url": base, "judge_model": config.LLM_JUDGE_MODEL}
        self.llm = make_llm_eval(self.seed, "LIVE", LIVE_LLM_UC, cfg=cfg, impl="live_http")
        self._read_tick = 0
        self._current: dict | None = None
        self._lock = threading.Lock()

    def _grade(self, res, t: int) -> dict:
        sig = dict(res.signals)  # the 5 LLM signals
        s_health = {k: health.evaluate(k, v) for k, v in sig.items()}
        lanes, overall = health.rollup(
            s_health, hand_set_lanes=_HAND_SET_LLM, excluded_lanes=_EXCLUDED_LANES_LLM)
        return {
            "use_case_id": LIVE_LLM_UC, "tick": t, "mode": "live",
            "signals": _signal_view(sig, s_health), "lanes": lanes, "overall": overall,
            "judge_sample": res.records if isinstance(res.records, list) else [],
            "errors": res.errors,
        }

    def tick(self) -> dict:
        with self._lock:
            t = self._read_tick
            ctx = TickContext(tick=t, seed=self.seed, scenario_id="LIVE")
            res = self.llm.evaluate(LIVE_LLM_UC, ctx)
            payload = self._grade(res, t)
            self._current = payload
            self._read_tick += 1
            return payload

    def state(self) -> dict | None:
        return self._current


_ml_runner: LiveRunner | None = None
_llm_runner: LiveLLMRunner | None = None


def live_runner(uc: str = LIVE_UC):
    """Return the live runner for a use case (churn ML by default, chatbot LLM for L02)."""
    global _ml_runner, _llm_runner
    if uc == LIVE_LLM_UC:
        if _llm_runner is None:
            _llm_runner = LiveLLMRunner()
        return _llm_runner
    if _ml_runner is None:
        _ml_runner = LiveRunner()
    return _ml_runner


def reset_live_runner(uc: str | None = None) -> None:
    global _ml_runner, _llm_runner
    if uc in (None, LIVE_UC):
        _ml_runner = None
    if uc in (None, LIVE_LLM_UC):
        _llm_runner = None
