"""HR policy corpus + Q&A eval set — PRD Appendix A §A.3.2 (copy verbatim) —
and the per-tick interaction simulator (deterministic seeded judge; count-based
hallucination injection). No live LLM exists in demo scope.
"""
from __future__ import annotations

import numpy as np

from .churn import rng

CORPUS: dict[str, str] = {
    "annual_leave": (
        "Annual leave: full-time employees accrue 15 working days of paid annual leave per "
        "calendar year. Unused leave of up to 5 days may be carried over to the next year and "
        "must be used by 31 March, after which it is forfeited."
    ),
    "sick_leave": (
        "Sick leave: employees are entitled to 30 days of paid sick leave per year. A medical "
        "certificate is required for any absence of 3 or more consecutive days."
    ),
    "wfh": (
        "Work from home: employees may work from home up to 2 days per week with manager "
        "approval. Fully remote arrangements require director-level approval and a signed "
        "remote-work agreement."
    ),
    "probation": (
        "Probation: new employees serve a probation period of 119 days. During probation "
        "either party may terminate with 7 days' notice."
    ),
    "expense_claim": (
        "Expense claims: submit claims within 30 days of the expense via the HR portal, "
        "attaching original receipts. Claims over 5,000 THB require line-manager approval."
    ),
    "parental_leave": (
        "Maternity leave: 98 days of leave, of which 45 days are paid at full salary. "
        "Paternity leave is 15 days, paid, to be taken within 90 days of the birth."
    ),
}

QA: list[dict] = [
    {"q": "How many days of annual leave do I get per year?",
     "ref": "15 working days of paid annual leave per year.", "answerable": True, "topic": "annual_leave"},
    {"q": "Can I carry over unused annual leave?",
     "ref": "Up to 5 days, and it must be used by 31 March.", "answerable": True, "topic": "annual_leave"},
    {"q": "How long is the probation period?",
     "ref": "119 days.", "answerable": True, "topic": "probation"},
    {"q": "How many days of paid sick leave am I entitled to?",
     "ref": "30 days per year.", "answerable": True, "topic": "sick_leave"},
    {"q": "How many days can I work from home each week?",
     "ref": "Up to 2 days per week with manager approval.", "answerable": True, "topic": "wfh"},
    {"q": "What is the deadline to submit an expense claim?",
     "ref": "Within 30 days of the expense.", "answerable": True, "topic": "expense_claim"},
    {"q": "How much paid maternity leave is there?",
     "ref": "98 days total, 45 of them paid at full salary.", "answerable": True, "topic": "parental_leave"},
    {"q": "What is the company's stock option / ESOP vesting schedule?",
     "ref": "Not covered by the HR policy corpus.", "answerable": False, "topic": None},
    {"q": "How many days of paid study / education leave do I get?",
     "ref": "Not covered by the HR policy corpus.", "answerable": False, "topic": None},
    {"q": "What is the retirement gratuity formula?",
     "ref": "Not covered by the HR policy corpus.", "answerable": False, "topic": None},
]

REFUSAL = "I don't have that in the HR policy documents — please check with HR."
INVENTED = "Yes — the policy grants that; see the staff handbook."

REPS_PER_QUESTION = 20  # 10 questions x 20 reps = 200 interactions/tick (Sheet-3 ">=200")


def retrieve_topic(question: str) -> str | None:
    """Keyword-overlap top-1 retrieval over the corpus (no embeddings)."""
    q = set(question.lower().replace("?", " ").replace("/", " ").split())
    best, best_score = None, -1
    for key, text in CORPUS.items():
        words = set(text.lower().split()) | set(key.split("_"))
        score = len(q & words)
        if score > best_score:
            best, best_score = key, score
    return best


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def simulate_tick(seed: int, tick: int, n_halluc: int) -> list[dict]:
    """200 evaluated interactions for tick `tick`; exactly `n_halluc` of the 60
    unanswerable interactions are invented answers (count-based, placement seeded).
    rng key (seed, 'llm', tick)."""
    g = rng(seed, "llm", tick)
    records: list[dict] = []
    # index the unanswerable slots (3 questions x 20 reps = 60) for injection placement
    unanswerable_slots = [(qi, rep) for qi, item in enumerate(QA) if not item["answerable"]
                          for rep in range(REPS_PER_QUESTION)]
    n_halluc = max(0, min(n_halluc, len(unanswerable_slots)))
    inject = set(map(tuple, np.array(unanswerable_slots)[
        g.choice(len(unanswerable_slots), size=n_halluc, replace=False)].tolist())) if n_halluc else set()

    for qi, item in enumerate(QA):
        for rep in range(REPS_PER_QUESTION):
            latency = float(np.clip(g.normal(2.4, 0.6), 0.6, 12.0))
            if item["answerable"]:
                answer = item["ref"]
                grounded = _clip01(g.normal(0.92, 0.04))
                relevance = _clip01(g.normal(0.92, 0.04))
                halluc = False
            elif (qi, rep) in inject:
                answer = INVENTED
                grounded = _clip01(g.normal(0.30, 0.08))
                relevance = _clip01(g.normal(0.80, 0.06))
                halluc = True
            else:
                answer = REFUSAL
                grounded = _clip01(g.normal(0.90, 0.05))
                relevance = _clip01(g.normal(0.85, 0.05))
                halluc = False
            records.append({
                "question": item["q"], "answer": answer, "topic": item.get("topic"),
                "groundedness": grounded, "relevance": relevance,
                "hallucination": halluc, "pii": False, "latency_s": latency,
            })
    return records


def aggregate(records: list[dict]) -> dict[str, float]:
    n = len(records)
    return {
        "hallucination_rate": float(np.mean([r["hallucination"] for r in records])) if n else None,
        "groundedness": float(np.mean([r["groundedness"] for r in records])) if n else None,
        "relevance": float(np.mean([r["relevance"] for r in records])) if n else None,
        "pii_exposure_rate": float(np.mean([r["pii"] for r in records])) if n else None,
        "p95_latency_s": float(np.percentile([r["latency_s"] for r in records], 95)) if n else None,
    }
