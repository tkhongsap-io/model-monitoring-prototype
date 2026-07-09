"""LLMEvalAdapter implementations `langfuse_stub` / `langfuse_cloud`.

The judge is a DETERMINISTIC SEEDED SIMULATION (count-based hallucination injection
+ seeded score draws, §A.3.2) — there is no live-LLM mode in demo scope. The two
implementations differ only in their TraceStore (config flip, ADR-2).
"""
from __future__ import annotations

from ... import config
from ...datagen import hr_corpus
from ..base import LaneResult, TickContext
from .stores import LangfuseCloudStore, SqliteTraceStore


class SeededJudgeAdapter:
    """Shared implementation; `name` distinguishes stub vs cloud registration."""

    def __init__(self, name: str, seed: int, scenario_id: str, use_case_id: str) -> None:
        self.name = name
        self.seed = seed
        self.use_case_id = use_case_id
        if name == "langfuse_cloud" and config.langfuse_cloud_configured():
            self.store = LangfuseCloudStore(
                scenario_id, use_case_id, config.LANGFUSE_PUBLIC_KEY,
                config.LANGFUSE_SECRET_KEY, config.LANGFUSE_HOST)
        else:
            self.store = SqliteTraceStore(scenario_id, use_case_id)

    def evaluate(self, use_case_id: str, tick: TickContext) -> LaneResult:
        res = LaneResult()
        try:
            n_halluc = int(tick.inject.get("n_halluc", 2))
            records = hr_corpus.simulate_tick(self.seed, tick.tick, n_halluc)
            self.store.set_tick(tick.tick)
            for r in records:
                tr = self.store.trace(
                    name="hr_chatbot", input=r["question"], output=r["answer"],
                    metadata={"topic": r["topic"], "latency_s": round(r["latency_s"], 3)})
                self.store.score(tr, "groundedness", r["groundedness"])
                self.store.score(tr, "relevance", r["relevance"])
                self.store.score(tr, "hallucination", 1.0 if r["hallucination"] else 0.0)
            self.store.flush()
            res.signals.update(hr_corpus.aggregate(records))
            # per-question sample for the drill-down Judge-scores tab (one per question)
            seen, sample = set(), []
            for r in records:
                if r["question"] not in seen:
                    seen.add(r["question"])
                    sample.append({
                        "question": r["question"], "answer": r["answer"][:80],
                        "groundedness": round(r["groundedness"], 3),
                        "relevance": round(r["relevance"], 3),
                        "hallucination": r["hallucination"], "pii": r["pii"],
                        "latency_s": round(r["latency_s"], 2)})
            res.records = sample
        except Exception as e:  # noqa: BLE001 — degrade, never crash the tick
            for k in ("hallucination_rate", "groundedness", "relevance",
                      "pii_exposure_rate", "p95_latency_s"):
                res.signals[k] = None
            res.errors["llm_eval"] = f"{type(e).__name__}: {e}"
        return res


def make_llm_eval(seed: int, scenario_id: str, use_case_id: str) -> SeededJudgeAdapter:
    """Factory: env-var selected implementation (E.5); stub is the default."""
    return SeededJudgeAdapter(config.LLM_EVAL_ADAPTER, seed, scenario_id, use_case_id)
