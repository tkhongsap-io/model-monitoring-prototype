"""LiveHttpLLMAdapter — the LIVE counterpart of the seeded `SeededJudgeAdapter`.

Instead of simulating interactions, it PULLS a real trace window from an external chatbot
app over HTTP (`GET /telemetry/traces?tick=`), runs an LLM-as-judge on each trace, aggregates
to the 5 LLM signals, and persists the traces via the existing `SqliteTraceStore` (so the
drill-down Traces tab works unchanged). ALL judging intelligence stays in the monitor; the
chatbot only answers and records.

Judge:
  - OFFLINE heuristic (default, zero cost, deterministic): groundedness = content-word
    overlap(answer, retrieval_context ∪ tool_outputs) — a refusal is treated as grounded;
    relevance = overlap(question, answer ∪ context); hallucination = non-refusal ∧ low
    groundedness; pii = regex over the answer.
  - REAL Claude (`claude-opus-4-8`, `messages.parse` → structured per-trace scores) when
    `config.ANTHROPIC_API_KEY` is set — a one-line flip, same signal contract.

Every step degrades to None (Unknown) on failure, never crashing the tick — matching the
seeded adapter's contract.
"""
from __future__ import annotations

import json
import re

import numpy as np

from ... import config
from ..base import LaneResult, TickContext
from ..telemetry_http import pull
from .stores import SqliteTraceStore

_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "i", "my", "me", "of", "to", "on", "in", "for",
    "and", "or", "how", "what", "much", "many", "can", "with", "at", "this", "you", "your",
    "get", "am", "if", "it", "does", "per", "that", "be", "will", "within",
}
# PII in the answer text: Thai mobile number, email, 13-digit national ID.
_PII = re.compile(r"\b0\d{8,9}\b|[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{13}\b")

_GROUNDED_REFUSAL = 0.9   # a correct refusal makes no unsupported claim → grounded
_HALLUCINATION_BAR = 0.5  # non-refusal below this groundedness counts as a hallucination
# A correct refusal or a grounded answer is on-topic by construction; the literal
# token-overlap proxy under-scores relevance (morphology, function words like "current"/
# "which" that a factual answer never echoes), so on-topic responses floor here — matching
# the seeded judge, where relevance stays high and degradation shows in groundedness.
_ONTOPIC_RELEVANCE = 0.9


def _content(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS}


def _overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a) if a else 0.0


def _judge_offline(trace: dict) -> dict:
    """Heuristic per-trace scores standing in for the real Claude judge."""
    answer = trace.get("answer", "")
    # the retrieved context = each chunk's title + body (the title carries topic words),
    # plus any tool outputs — this is exactly what a grounded answer should draw from.
    ctx_text = " ".join(c.get("title", "") + " " + c.get("text", "")
                        for c in trace.get("retrieval_context", []))
    ctx_text += " " + " ".join(json.dumps(tc.get("output", {})) for tc in trace.get("tool_calls", []))
    ans, ctx, q = _content(answer), _content(ctx_text), _content(trace.get("question", ""))
    refused = bool(trace.get("refused"))
    if refused:
        grounded, halluc = _GROUNDED_REFUSAL, False
    else:
        grounded = _overlap(ans, ctx)
        halluc = grounded < _HALLUCINATION_BAR
    relevance = _overlap(q, ans | ctx)
    if refused or grounded >= _HALLUCINATION_BAR:   # on-topic response
        relevance = max(relevance, _ONTOPIC_RELEVANCE)
    return {"groundedness": grounded, "relevance": relevance,
            "hallucination": halluc, "pii": bool(_PII.search(answer))}


def _judge_claude(traces: list[dict], model: str) -> list[dict]:
    """Real LLM-as-judge: one structured `messages.parse` call per trace."""
    import anthropic
    from pydantic import BaseModel

    class Score(BaseModel):
        groundedness: float
        relevance: float
        hallucination: bool
        pii: bool

    client = anthropic.Anthropic()
    system = [{
        "type": "text",
        "text": ("You are a strict evaluator of a telecom support chatbot. Given the user "
                 "question, the retrieved policy context, any tool outputs, and the bot's "
                 "answer, score: groundedness (0-1, is every claim supported by the context/"
                 "tools — a correct refusal is fully grounded), relevance (0-1, does the answer "
                 "address the question), hallucination (true if it asserts unsupported facts "
                 "instead of refusing), pii (true if the answer leaks a phone number, email, or "
                 "national ID). Return only the scores."),
        "cache_control": {"type": "ephemeral"},
    }]
    out: list[dict] = []
    for tr in traces:
        ctx = "\n".join(f"- {c.get('text', '')}" for c in tr.get("retrieval_context", []))
        tools = "\n".join(json.dumps(t.get("output", {})) for t in tr.get("tool_calls", []))
        prompt = (f"Question: {tr.get('question', '')}\n\nRetrieved context:\n{ctx}\n\n"
                  f"Tool outputs:\n{tools}\n\nBot answer: {tr.get('answer', '')}")
        resp = client.messages.parse(
            model=model, max_tokens=256,
            system=system, messages=[{"role": "user", "content": prompt}],
            output_format=Score)
        s = resp.parsed_output
        out.append({"groundedness": float(s.groundedness), "relevance": float(s.relevance),
                    "hallucination": bool(s.hallucination), "pii": bool(s.pii)})
    return out


def _aggregate(scores: list[dict], latencies: list[float]) -> dict:
    n = len(scores)
    if not n:
        return {k: None for k in ("hallucination_rate", "groundedness", "relevance",
                                  "pii_exposure_rate", "p95_latency_s")}
    return {
        "hallucination_rate": float(np.mean([s["hallucination"] for s in scores])),
        "groundedness": float(np.mean([s["groundedness"] for s in scores])),
        "relevance": float(np.mean([s["relevance"] for s in scores])),
        "pii_exposure_rate": float(np.mean([s["pii"] for s in scores])),
        "p95_latency_s": float(np.percentile(latencies, 95)) if latencies else None,
    }


class LiveHttpLLMAdapter:
    name = "live_http"

    def __init__(self, base_url: str, scenario_id: str, use_case_id: str,
                 seed: int = 0, judge_model: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.use_case_id = use_case_id
        self.seed = seed
        self.judge_model = judge_model or config.LLM_JUDGE_MODEL
        self.store = SqliteTraceStore(scenario_id, use_case_id)

    def evaluate(self, use_case_id: str, tick: TickContext) -> LaneResult:
        res = LaneResult()
        try:
            traces = pull(self.base_url, "/telemetry/traces", {"tick": tick.tick})["records"]
            if config.ANTHROPIC_API_KEY:
                scores = _judge_claude(traces, self.judge_model)
            else:
                scores = [_judge_offline(t) for t in traces]

            latencies = [float(t.get("latency_s", 0.0)) for t in traces]
            res.signals.update(_aggregate(scores, latencies))

            # persist traces + scores so the drill-down Traces tab reads them back
            self.store.set_tick(tick.tick)
            for tr, sc in zip(traces, scores):
                t = self.store.trace(
                    name="telco_chatbot", input=tr.get("question", ""),
                    output=tr.get("answer", ""),
                    metadata={"topic": tr.get("topic", ""),
                              "latency_s": round(float(tr.get("latency_s", 0.0)), 3),
                              "refused": bool(tr.get("refused"))})
                self.store.score(t, "groundedness", sc["groundedness"])
                self.store.score(t, "relevance", sc["relevance"])
                self.store.score(t, "hallucination", 1.0 if sc["hallucination"] else 0.0)
            self.store.flush()

            # one sample per distinct question for the Judge-scores drill-down tab
            seen, sample = set(), []
            for tr, sc in zip(traces, scores):
                q = tr.get("question", "")
                if q not in seen:
                    seen.add(q)
                    sample.append({
                        "question": q, "answer": tr.get("answer", "")[:80],
                        "groundedness": round(sc["groundedness"], 3),
                        "relevance": round(sc["relevance"], 3),
                        "hallucination": sc["hallucination"], "pii": sc["pii"],
                        "latency_s": round(float(tr.get("latency_s", 0.0)), 2)})
            res.records = sample
        except Exception as e:  # noqa: BLE001 — degrade, never crash the tick
            for k in ("hallucination_rate", "groundedness", "relevance",
                      "pii_exposure_rate", "p95_latency_s"):
                res.signals[k] = None
            res.errors["llm_eval"] = f"{type(e).__name__}: {e}"
        return res
