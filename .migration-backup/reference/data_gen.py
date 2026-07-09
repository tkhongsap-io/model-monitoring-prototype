"""Synthetic, self-contained demo data — no real True data, no network.

- `generate_churn()` builds a telco-churn-like tabular dataset in two windows:
    * reference : the "training / last quarter" distribution (labelled)
    * analysis  : the "current production window" with INJECTED covariate drift
                  (higher charges, more support calls, more month-to-month contracts)
                  AND mild concept drift + label noise, so a model trained on the
                  reference window genuinely degrades — Evidently flags the drift and
                  NannyML estimates the performance drop before labels arrive.
- `generate_hr_corpus()` builds a tiny HR-policy corpus + a Q&A eval set (some questions
  deliberately unanswerable) for the LLM lane.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "tenure_months", "monthly_charges", "total_charges", "num_support_calls",
    "contract_type", "has_fiber", "is_senior", "auto_pay",
]
CATEGORICAL = ["contract_type", "has_fiber", "is_senior", "auto_pay"]
TARGET = "churn"


def _make_window(rng: np.random.Generator, n: int, drift: bool) -> pd.DataFrame:
    tenure = rng.integers(1, 48 if drift else 72, n)
    contract = rng.choice([0, 1, 2], n, p=([0.80, 0.12, 0.08] if drift else [0.55, 0.25, 0.20]))
    monthly = rng.normal(70, 22, n).clip(20, 140)
    if drift:
        monthly = (monthly * 1.30).clip(20, 190)
    total = (monthly * tenure * rng.uniform(0.8, 1.0, n)).round(1)
    support = rng.poisson(3.6 if drift else 1.2, n)
    fiber = rng.binomial(1, 0.66 if drift else 0.45, n)
    senior = rng.binomial(1, 0.16, n)
    autopay = rng.binomial(1, 0.55, n)

    # base data-generating relationship (same in both windows)
    z = (
        -2.4
        + 0.9 * (contract == 0)
        - 0.02 * tenure
        + 0.012 * (monthly - 70)
        + 0.35 * support
        + 0.25 * fiber
        + 0.30 * senior
        - 0.40 * autopay
    )
    p = 1.0 / (1.0 + np.exp(-z))
    churn = rng.binomial(1, p)

    # production signal degradation: the discriminative features regress toward the
    # population mean, so the model can no longer separate customers as well — ROC-AUC
    # drops. Because the model's predicted-probability spread compresses too, NannyML CBPE
    # estimates the drop LABEL-FREE, and realized labels then confirm it. (churn was already
    # drawn from the pre-compression signal, so the model genuinely loses skill here.)
    if drift:
        monthly = 70.0 + 0.45 * (monthly - 70.0)
        support = np.clip(np.round(0.45 * support), 0, None)
        tenure = np.round(36.0 + 0.45 * (tenure.astype(float) - 36.0))

    return pd.DataFrame({
        "tenure_months": tenure.astype(int),
        "monthly_charges": monthly.round(2),
        "total_charges": total,
        "num_support_calls": support.astype(int),
        "contract_type": contract.astype(int),
        "has_fiber": fiber.astype(int),
        "is_senior": senior.astype(int),
        "auto_pay": autopay.astype(int),
        TARGET: churn.astype(int),
    })


def generate_churn(seed: int = 42, n_reference: int = 4000, n_analysis: int = 2000):
    """Return (reference_df, analysis_df) — both labelled; analysis carries injected drift."""
    rng = np.random.default_rng(seed)
    reference = _make_window(rng, n_reference, drift=False)
    analysis = _make_window(rng, n_analysis, drift=True)
    return reference, analysis


# --------------------------------------------------------------------------------------
# HR knowledge base (LLM lane)
# --------------------------------------------------------------------------------------

HR_CORPUS: dict[str, str] = {
    "annual_leave": (
        "Annual leave: full-time employees accrue 15 working days of paid annual leave "
        "per calendar year. Unused leave of up to 5 days may be carried over to the next "
        "year and must be used by 31 March, after which it is forfeited."
    ),
    "sick_leave": (
        "Sick leave: employees are entitled to 30 days of paid sick leave per year. A "
        "medical certificate is required for any absence of 3 or more consecutive days."
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

# Q&A eval set. `answerable=False` means the corpus does NOT contain the answer — a good
# chatbot should say it doesn't know rather than invent one (grounding / refusal test).
HR_QA: list[dict] = [
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
