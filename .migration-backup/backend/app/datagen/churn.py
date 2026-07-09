"""Synthetic telco-churn generator — PRD Appendix A §A.3.1, with the M1 calibration
applied per §A.7 ("recalibrate the generator, never the bands").

M1 CALIBRATION RECORD (seed 42, measured — see backend/tests/test_calibration.py):
The PRD's §A.3.1 recipe (weak z, rounded 0.45 compression, RandomForest) could not
reach its own §A.7 assertions out-of-sample (baseline OOS AUC ≈ 0.66; v2 recovery
≈ 0.70; CBPE barely responsive). Three generator-level recalibrations, all sanctioned
by §A.7 / simulation.yaml tunability:
  1. Signal strength: z deviations scaled by C_SCALE=2.4 around M_CENTER=-1.9
     -> baseline OOS AUC ≈ 0.85 (C1 [0.82, 0.86]).
  2. Concept drift added to the drifted world (the promo cohort behaves differently:
     support calls stop predicting, auto-pay stops protecting, fiber flips) ->
     the v1 model genuinely loses ranking skill on drifted rows: realized AUC falls
     to ≈ 0.70 at full drift (C4) while a v2 retrained on the drifted world recovers
     to ≈ 0.83 (C8) because...
  3. ...compression is INVERTIBLE (linear shrink, no rounding): information is
     preserved for the retrained model but the old model's baseline-scale geometry
     misreads it.
Engine-reality note (C3 recalibration): NannyML CBPE is calibration-based and
structurally conservative under covariate shift — its estimate dips measurably below
baseline (label-free early warning) but does NOT reach the illustrative Amber band of
the original A.5.2 table. The recalibrated C3 asserts the dip + never-Red + monotone
sag; the demo narrative states the honest lesson: "estimated is early but
conservative; realized confirms worse."
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

FEATURES = [
    "tenure_months", "monthly_charges", "total_charges", "num_support_calls",
    "contract_type", "has_fiber", "is_senior", "auto_pay",
]
CATEGORICAL = ["contract_type", "has_fiber", "is_senior", "auto_pay"]
TARGET = "churn"

C_SCALE = 2.4    # z signal-strength scale (M1 calibration #1)
M_CENTER = -1.9  # centre for the affine z scaling (keeps churn prevalence ~0.13)
SHRINK = 0.45    # invertible compression factor (M1 calibration #3)


def rng(seed: int, stream: str, tick: int = 0) -> np.random.Generator:
    """Keyed generator: seed-sequence over [seed, hash(stream), tick] (§A.6).

    Ticks are offset by +1000 because SeedSequence requires non-negative entropy
    and pre-history windows use negative ticks (t = -3..-1).
    """
    stream_id = zlib.crc32(stream.encode("utf-8"))
    return np.random.default_rng(np.random.SeedSequence([seed, stream_id, tick + 1000]))


def _rows(g: np.random.Generator, n: int, drifted: bool) -> pd.DataFrame:
    # 1. tenure
    tenure = g.integers(1, 48 if drifted else 72, n).astype(float)
    # 2. contract type (month-to-month share jumps in the drifted world)
    p = [0.80, 0.12, 0.08] if drifted else [0.55, 0.25, 0.20]
    contract = g.choice([0, 1, 2], size=n, p=p).astype(float)
    # 3. monthly charges
    monthly = np.clip(g.normal(70, 22, n), 20, 140)
    if drifted:
        monthly = np.clip(monthly * 1.30, 20, 190)
    monthly = np.round(monthly, 2)
    # 4. total charges (pre-compression values; not compressed — per §A.3.1 step 4)
    total = np.round(monthly * tenure * g.uniform(0.8, 1.0, n), 1)
    # 5. remaining features
    support = g.poisson(3.6 if drifted else 1.2, n).astype(float)
    fiber = g.binomial(1, 0.66 if drifted else 0.45, n).astype(float)
    senior = g.binomial(1, 0.16, n).astype(float)
    autopay = g.binomial(1, 0.55, n).astype(float)
    # 6. label from CURRENT (pre-compression) values; drifted world carries CONCEPT
    #    drift (M1 calibration #2): support dampened 0.35->0.15, fiber flips
    #    +0.25->-0.25, auto-pay stops protecting -0.40->+0.40.
    if drifted:
        z = (-2.4 + 0.9 * (contract == 0) - 0.02 * tenure + 0.012 * (monthly - 70)
             + 0.15 * support - 0.25 * fiber + 0.30 * senior + 0.40 * autopay)
    else:
        z = (-2.4 + 0.9 * (contract == 0) - 0.02 * tenure + 0.012 * (monthly - 70)
             + 0.35 * support + 0.25 * fiber + 0.30 * senior - 0.40 * autopay)
    z = M_CENTER + C_SCALE * (z - M_CENTER)
    churn = g.binomial(1, 1.0 / (1.0 + np.exp(-z))).astype(int)
    # 7. drifted only — post-label INVERTIBLE signal compression (no rounding;
    #    M1 calibration #3): the CBPE/realized trick of §A.3.1, information-preserving.
    if drifted:
        monthly = 70 + SHRINK * (monthly - 70)
        support = SHRINK * support
        tenure = 36 + SHRINK * (tenure - 36)
    return pd.DataFrame({
        "tenure_months": np.round(tenure, 2), "monthly_charges": np.round(monthly, 2),
        "total_charges": total, "num_support_calls": np.round(support, 2),
        "contract_type": contract, "has_fiber": fiber, "is_senior": senior,
        "auto_pay": autopay, TARGET: churn,
    })


def reference_window(seed: int, n_rows: int = 4000) -> pd.DataFrame:
    """Baseline reference window, rng key (seed, 'churn-ref')."""
    return _rows(rng(seed, "churn-ref"), n_rows, drifted=False)


def drifted_reference_window(seed: int, n_rows: int = 4000) -> pd.DataFrame:
    """Fully-drifted reference window (S5 re-baseline), rng key (seed, 'churn-ref-v2')."""
    return _rows(rng(seed, "churn-ref-v2"), n_rows, drifted=True)


def analysis_window(seed: int, tick: int, alpha: float, n_rows: int = 500) -> pd.DataFrame:
    """Per-tick analysis window: round(alpha*n) drifted rows + rest baseline, shuffled.

    rng key (seed, 'churn', tick).
    """
    g = rng(seed, "churn", tick)
    n_drift = int(round(max(0.0, min(1.0, alpha)) * n_rows))
    parts = []
    if n_drift:
        parts.append(_rows(g, n_drift, drifted=True))
    if n_rows - n_drift:
        parts.append(_rows(g, n_rows - n_drift, drifted=False))
    df = pd.concat(parts, ignore_index=True)
    return df.iloc[g.permutation(len(df))].reset_index(drop=True)
