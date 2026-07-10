"""Live runner — the monitor's LIVE observation of an external model app.

On each tick() it advances its read position, pulls the current telemetry window
through the LIVE adapters (which reach OUT to the model app over HTTP), grades the
signals with the SAME health engine the baker uses (Green/Amber/Red rollup), and stores
the graded payload. Cursor sync (contract v1.0): before pulling, each runner checks the
app's /telemetry/meta latest_tick best-effort — if the monitor is ahead it reports
{"waiting": true} WITHOUT advancing, so it never burns ticks against 404s. It is kept
ENTIRELY SEPARATE from the baked scenario player/baker — those stay byte-deterministic
and untouched. tick() does sync HTTP + heavy engine work, so callers run it in a worker
thread (never the event loop).
"""
from __future__ import annotations

import threading

from .. import config
from ..adapters.base import TickContext
from ..adapters.explain.lime_shap import make_explain
from ..adapters.explain.live_http import LiveHttpExplainAdapter
from ..adapters.llm_eval.judge import make_llm_eval
from ..adapters.ml_monitor.evidently_nannyml import make_ml_monitor
from ..adapters.ml_monitor.nba_live_http import LiveHttpNBAAdapter
from ..adapters.telemetry_http import pull_meta
from ..engines import health
from .baker import _artifact_writer_factory

LIVE_UC = "AICT-L01"      # the live churn use case (ML lane)
LIVE_LLM_UC = "AICT-L02"  # the live chatbot use case (LLM lane)
LIVE_NBA_UC = "AICT-L03"  # the live NBA recommender use case (ML + feedback lanes)

# non-ML lanes hand-set for an ML use case (mirrors the baker's P02 rollup, §A.1.4)
_HAND_SET = {"Feedback & action loop": "Unknown", "Safety & security": "Green", "Reliability": "Green"}
_EXCLUDED_LANES = {"Feedback & action loop"}

# lanes an LLM use case doesn't produce signals for (its Quality/Safety/Reliability lanes
# come from the 5 LLM signals); Drift is assumed clean, Feedback is declared-Unknown.
_HAND_SET_LLM = {"Drift & degradation": "Green", "Feedback & action loop": "Unknown"}
_EXCLUDED_LANES_LLM = {"Feedback & action loop"}

# NBA hand-sets only Safety/Reliability — Feedback is a REAL lane (acceptance_rate);
# while rewards lag it is reasoned-Unknown and excluded, once arrived it COUNTS.
_HAND_SET_NBA = {"Safety & security": "Green", "Reliability": "Green"}


def _commit_tick(runner, payload: dict, telemetry_err: str | None) -> dict:
    """Store a graded tick. On a telemetry failure (the model app is unreachable) HOLD the
    last good state (annotated stale) instead of clobbering it with an all-Unknown payload,
    and do NOT advance the read cursor — the dashboard keeps showing the last observed
    window rather than flashing every lane grey. On success, store and advance."""
    if telemetry_err:
        if runner._current is not None:
            held = dict(runner._current)
            held["cursor_held"] = True
            held["errors"] = {**held.get("errors", {}), "telemetry": telemetry_err}
            runner._current = held
            return held
        payload["cursor_held"] = True   # never observed yet — surface the degraded payload
        runner._current = payload
        return payload
    runner._current = payload
    runner._read_tick += 1
    return payload


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


def _ahead_of_app(base_url: str, read_tick: int, uc: str) -> dict | None:
    """Cursor sync: best-effort /telemetry/meta; the monitor reads only CLOSED windows
    (tick < latest_tick — the latest window is still open: /chat appends to it, contract
    §6). If the cursor has caught up, return a waiting payload (caller must NOT advance
    the cursor)."""
    latest = pull_meta(base_url).get("latest_tick")
    if latest is not None and read_tick >= latest:
        return {"use_case_id": uc, "tick": None, "mode": "live",
                "waiting": True, "latest_app_tick": latest}
    return None


class LiveRunner:
    def __init__(self, churn_url: str | None = None, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else config.DEMO_SEED
        self.base_url = (churn_url or config.LIVE_CHURN_URL).rstrip("/")
        # per-use-case artifact namespace: L01 and L03 write the same artifact KINDS at
        # the same ticks — a shared "LIVE" namespace makes them overwrite each other's
        # files and db rows (review finding)
        writer = _artifact_writer_factory(f"LIVE-{LIVE_UC}")
        cfg = {"base_url": self.base_url, "chunk_size": 500, "model_name": "telco-churn"}
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
        extra = {"realized_roc_auc": {"pending_reason": pending}} if pending else {}
        return {
            "use_case_id": LIVE_UC, "tick": t, "mode": "live",
            "signals": _signal_view(sig, s_health, extra), "lanes": lanes, "overall": overall,
            "drifted_features": records.get("drifted_features", []),
            "reference_auc": records.get("reference_auc"),
            "model_version": records.get("model_version"),
            "realized_pending_reason": pending,
            "realized_label_coverage": records.get("realized_label_coverage"),
            "lime_top": ex_res.lime_top, "lime_instance": ex_res.instance,
            "artifacts": {**ml_res.artifacts, **ex_res.artifacts},
            "errors": {**ml_res.errors, **ex_res.errors},
        }

    def tick(self) -> dict:
        """Observe the next telemetry window, grade it, store + return the payload."""
        with self._lock:
            t = self._read_tick
            waiting = _ahead_of_app(self.base_url, t, LIVE_UC)
            if waiting:
                return waiting  # don't advance, don't store as _current
            ctx = TickContext(tick=t, seed=self.seed, scenario_id="LIVE")
            ml_res = self.ml.monitor(LIVE_UC, ctx)
            ex_res = self.explain.explain(LIVE_UC, ctx)
            payload = self._grade(ml_res, ex_res, t)
            return _commit_tick(self, payload, ml_res.errors.get("telemetry"))

    def state(self) -> dict | None:
        return self._current


class LiveLLMRunner:
    """LIVE observation of an external chatbot: pull traces -> LLM-as-judge -> grade the
    LLM lanes with the SAME health engine. Separate from the baked player (byte-deterministic
    and untouched). tick() does sync HTTP + judging, so callers run it in a worker thread."""

    def __init__(self, chatbot_url: str | None = None, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else config.DEMO_SEED
        self.base_url = (chatbot_url or config.LIVE_CHATBOT_URL).rstrip("/")
        cfg = {"base_url": self.base_url, "judge_model": config.LLM_JUDGE_MODEL}
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
            "judge": config.LLM_JUDGE_MODEL if config.ANTHROPIC_API_KEY else "heuristic-v1",
            "judge_sample": res.records if isinstance(res.records, list) else [],
            "errors": res.errors,
        }

    def tick(self) -> dict:
        with self._lock:
            t = self._read_tick
            waiting = _ahead_of_app(self.base_url, t, LIVE_LLM_UC)
            if waiting:
                return waiting
            ctx = TickContext(tick=t, seed=self.seed, scenario_id="LIVE")
            res = self.llm.evaluate(LIVE_LLM_UC, ctx)
            payload = self._grade(res, t)
            return _commit_tick(self, payload, res.errors.get("telemetry"))

    def state(self) -> dict | None:
        return self._current


class LiveNBARunner:
    """LIVE observation of the NBA recommender. Instantiates the live adapters DIRECTLY
    (not via the seeded factories — those are part of the golden-bake swap seam and stay
    untouched): LiveHttpNBAAdapter for drift/CBPE/realized-AUC + acceptance_rate +
    recommendation_drift, and LiveHttpExplainAdapter for LIME/SHAP on the pulled model.
    Unlike the churn runner, Feedback & action loop is a REAL lane here — graded from
    acceptance_rate once rewards arrive, reasoned-Unknown (excluded from overall) while
    they lag."""

    def __init__(self, nba_url: str | None = None, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else config.DEMO_SEED
        self.base_url = (nba_url or config.LIVE_NBA_URL).rstrip("/")
        writer = _artifact_writer_factory(f"LIVE-{LIVE_NBA_UC}")   # see LiveRunner note
        self.ml = LiveHttpNBAAdapter(self.base_url, writer)
        self.explain = LiveHttpExplainAdapter(
            base_url=self.base_url, artifact_writer=writer, model_name="nba-recommender",
            seed=self.seed, class_names=["decline", "accept"],
            inferences_path="/telemetry/recommendations")
        self._read_tick = 0
        self._current: dict | None = None
        self._lock = threading.Lock()

    def _grade(self, ml_res, ex_res, t: int) -> dict:
        sig = dict(ml_res.signals)
        s_health = {k: health.evaluate(k, v) for k, v in sig.items()}
        records = ml_res.records if isinstance(ml_res.records, dict) else {}
        pending = records.get("realized_pending_reason")
        acc_pending = ml_res.errors.get("acceptance_pending")
        excluded: set[str] = set()
        excluded_lanes: set[str] = set()
        hand_set = dict(_HAND_SET_NBA)
        extra: dict = {}
        if pending:  # reasoned-Unknown, excluded from rollup (labels lag by design)
            excluded.add("realized_roc_auc")
            s_health["realized_roc_auc"] = "Unknown"
            extra["realized_roc_auc"] = {"pending_reason": pending}
        if acc_pending:  # same treatment for the Feedback lane while rewards lag
            excluded.add("acceptance_rate")
            s_health["acceptance_rate"] = "Unknown"
            extra["acceptance_rate"] = {"pending_reason": acc_pending}
            hand_set["Feedback & action loop"] = "Unknown"
            excluded_lanes.add("Feedback & action loop")
        rec_pending = ml_res.errors.get("recommendation_drift_pending")
        if rec_pending:  # awaiting a current-version window to anchor the baseline mix
            excluded.add("recommendation_drift")
            s_health["recommendation_drift"] = "Unknown"
            extra["recommendation_drift"] = {"pending_reason": rec_pending}
        lanes, overall = health.rollup(
            s_health, excluded_keys=excluded,
            hand_set_lanes=hand_set, excluded_lanes=excluded_lanes)
        return {
            "use_case_id": LIVE_NBA_UC, "tick": t, "mode": "live",
            "signals": _signal_view(sig, s_health, extra), "lanes": lanes, "overall": overall,
            "drifted_features": records.get("drifted_features", []),
            "reference_auc": records.get("reference_auc"),
            "model_version": records.get("model_version"),
            "realized_pending_reason": pending,
            "realized_label_coverage": records.get("realized_label_coverage"),
            "acceptance_pending_reason": acc_pending,
            "offer_mix": records.get("offer_mix"),
            "baseline_offer_mix": records.get("baseline_offer_mix"),
            "lime_top": ex_res.lime_top, "lime_instance": ex_res.instance,
            "artifacts": {**ml_res.artifacts, **ex_res.artifacts},
            "errors": {**ml_res.errors, **ex_res.errors},
        }

    def tick(self) -> dict:
        with self._lock:
            t = self._read_tick
            waiting = _ahead_of_app(self.base_url, t, LIVE_NBA_UC)
            if waiting:
                return waiting
            ctx = TickContext(tick=t, seed=self.seed, scenario_id="LIVE")
            ml_res = self.ml.monitor(LIVE_NBA_UC, ctx)
            ex_res = self.explain.explain(LIVE_NBA_UC, ctx)
            payload = self._grade(ml_res, ex_res, t)
            return _commit_tick(self, payload, ml_res.errors.get("telemetry"))

    def state(self) -> dict | None:
        return self._current


_ml_runner: LiveRunner | None = None
_llm_runner: LiveLLMRunner | None = None
_nba_runner: LiveNBARunner | None = None
_runner_lock = threading.Lock()   # concurrent first ticks must not build two runners


def live_runner(uc: str = LIVE_UC):
    """Return the live runner for a use case (churn ML by default, chatbot LLM for L02,
    NBA recommender for L03)."""
    global _ml_runner, _llm_runner, _nba_runner
    with _runner_lock:
        if uc == LIVE_LLM_UC:
            if _llm_runner is None:
                _llm_runner = LiveLLMRunner()
            return _llm_runner
        if uc == LIVE_NBA_UC:
            if _nba_runner is None:
                _nba_runner = LiveNBARunner()
            return _nba_runner
        if _ml_runner is None:
            _ml_runner = LiveRunner()
        return _ml_runner


def reset_live_runner(uc: str | None = None) -> None:
    global _ml_runner, _llm_runner, _nba_runner
    if uc in (None, LIVE_UC):
        _ml_runner = None
    if uc in (None, LIVE_LLM_UC):
        _llm_runner = None
    if uc in (None, LIVE_NBA_UC):
        _nba_runner = None
