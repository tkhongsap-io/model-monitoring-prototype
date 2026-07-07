"""LLM monitoring lane (HR policy chatbot stand-in).

A tiny RAG chatbot over the HR corpus, evaluated with LLM-as-judge signals
(groundedness / relevance / hallucination / PII / latency) that map to the proposal's
Quality / Safety / Reliability lanes and its Sheet-3 hallucination band.

Two modes, chosen automatically:
  * ONLINE  (OPENAI_API_KEY present): real OpenAI answers + real LLM-as-judge, and — if
    LANGFUSE_* are set — traces + scores pushed to Langfuse Cloud.
  * OFFLINE (no key): a deterministic, seeded simulation so the control tower still runs
    and demos end-to-end with no network and no cost.
"""
from __future__ import annotations

import json
import time

import numpy as np

from common import write_json
from config import Config
from data_gen import HR_CORPUS, HR_QA

USE_CASE_ID = "UC-HRBOT-01"
USE_CASE_NAME = "HR Policy Chatbot (RAG)"

REFUSAL = "I don't have that in the HR policy documents — please check with HR."


def _retrieve(question: str, k: int = 1) -> list[tuple[str, str]]:
    """Keyword-overlap retrieval over the HR corpus (no embeddings needed)."""
    q = set(question.lower().replace("?", " ").replace("/", " ").split())
    scored = []
    for key, text in HR_CORPUS.items():
        words = set(text.lower().split()) | set(key.split("_"))
        scored.append((len(q & words), key, text))
    scored.sort(reverse=True)
    return [(key, text) for _, key, text in scored[:k]]


# --------------------------------------------------------------------------------------
# ONLINE mode (OpenAI + optional Langfuse)
# --------------------------------------------------------------------------------------

def _answer_online(cfg: Config, question: str, context: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.chat.completions.create(
        model=cfg.chat_model, temperature=0,
        messages=[
            {"role": "system", "content": (
                "You are an HR assistant. Answer ONLY from the provided HR policy context. "
                "If the answer is not in the context, reply exactly: " + REFUSAL)},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    return resp.choices[0].message.content.strip()


def _judge_online(cfg: Config, question: str, context: str, answer: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    resp = client.chat.completions.create(
        model=cfg.judge_model, temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "You grade an HR chatbot answer against its retrieved context. Return JSON "
                "with keys: groundedness (0-1, is the answer supported by the context), "
                "relevance (0-1, does it address the question), hallucination (true if it "
                "states facts not in the context), pii (true if it leaks personal data). "
                "A correct 'I don't know' refusal is fully grounded and not a hallucination.")},
            {"role": "user", "content": json.dumps(
                {"question": question, "context": context, "answer": answer})},
        ],
    )
    d = json.loads(resp.choices[0].message.content)
    return {
        "groundedness": float(d.get("groundedness", 0.0)),
        "relevance": float(d.get("relevance", 0.0)),
        "hallucination": bool(d.get("hallucination", False)),
        "pii": bool(d.get("pii", False)),
    }


def _push_langfuse(cfg: Config, records: list[dict]) -> bool:
    """Best-effort push of traces + scores to Langfuse Cloud (v2 low-level API)."""
    if not cfg.langfuse_enabled:
        return False
    try:
        from langfuse import Langfuse
        lf = Langfuse(public_key=cfg.langfuse_public_key,
                      secret_key=cfg.langfuse_secret_key, host=cfg.langfuse_host)
        for r in records:
            trace = lf.trace(name="hr_chatbot", input=r["question"], output=r["answer"],
                             metadata={"topic": r.get("topic"), "latency_s": r["latency_s"]})
            for name in ("groundedness", "relevance"):
                trace.score(name=name, value=r[name])
            trace.score(name="hallucination", value=1 if r["hallucination"] else 0)
        lf.flush()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  (Langfuse push skipped: {e})")
        return False


# --------------------------------------------------------------------------------------
# OFFLINE mode (deterministic simulation)
# --------------------------------------------------------------------------------------

def _simulate(cfg: Config, reps: int = 20) -> list[dict]:
    rng = np.random.default_rng(cfg.seed)
    records = []
    for item in HR_QA:
        ctx = _retrieve(item["q"])[0][1]
        for _ in range(reps):
            latency = float(np.clip(rng.normal(2.4, 0.6), 0.6, 12.0))
            if item["answerable"]:
                answer = item["ref"]
                rec = {"groundedness": float(np.clip(rng.normal(0.92, 0.04), 0, 1)),
                       "relevance": float(np.clip(rng.normal(0.92, 0.04), 0, 1)),
                       "hallucination": False, "pii": False}
            else:
                # mostly refuses; occasionally invents an unsupported answer (~5%)
                if rng.random() < 0.05:
                    answer = "Yes — the policy grants that; see the staff handbook."  # unsupported
                    rec = {"groundedness": float(np.clip(rng.normal(0.30, 0.08), 0, 1)),
                           "relevance": float(np.clip(rng.normal(0.80, 0.06), 0, 1)),
                           "hallucination": True, "pii": False}
                else:
                    answer = REFUSAL
                    rec = {"groundedness": float(np.clip(rng.normal(0.90, 0.05), 0, 1)),
                           "relevance": float(np.clip(rng.normal(0.85, 0.05), 0, 1)),
                           "hallucination": False, "pii": False}
            rec.update({"question": item["q"], "answer": answer,
                        "topic": item.get("topic"), "latency_s": latency})
            records.append(rec)
    return records


def _run_online(cfg: Config) -> list[dict]:
    records = []
    for item in HR_QA:
        ctx = _retrieve(item["q"])[0][1]
        t0 = time.time()
        answer = _answer_online(cfg, item["q"], ctx)
        latency = time.time() - t0
        scores = _judge_online(cfg, item["q"], ctx, answer)
        scores.update({"question": item["q"], "answer": answer,
                       "topic": item.get("topic"), "latency_s": float(latency)})
        records.append(scores)
    return records


def run_llm_lane(cfg: Config) -> dict:
    cfg.ensure_dirs()
    mode = "online" if cfg.llm_enabled else "offline"
    if mode == "online":
        try:
            records = _run_online(cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  (OpenAI call failed, falling back to offline mode: {e})")
            mode, records = "offline", _simulate(cfg)
    else:
        records = _simulate(cfg)

    langfuse_pushed = _push_langfuse(cfg, records) if mode == "online" else False

    n = len(records)
    signals = {
        "hallucination_rate": float(np.mean([r["hallucination"] for r in records])) if n else None,
        "groundedness": float(np.mean([r["groundedness"] for r in records])) if n else None,
        "relevance": float(np.mean([r["relevance"] for r in records])) if n else None,
        "pii_exposure_rate": float(np.mean([r["pii"] for r in records])) if n else None,
        "p95_latency_s": float(np.percentile([r["latency_s"] for r in records], 95)) if n else None,
    }
    result = {
        "use_case_id": USE_CASE_ID,
        "name": USE_CASE_NAME,
        "type": "RAG / knowledge chatbot",
        "risk_tier": "High",
        "signals": signals,
        "context": {
            "mode": mode, "interactions": n, "langfuse_pushed": langfuse_pushed,
            "langfuse_host": cfg.langfuse_host if langfuse_pushed else None,
            "sample": records[:3],
        },
        "errors": {},
    }
    write_json(cfg.artifacts_dir / "signals_hrbot.json", result)
    return result


if __name__ == "__main__":
    from config import load_config
    r = run_llm_lane(load_config())
    print(f"LLM lane ({r['context']['mode']}) signals:", r["signals"])
