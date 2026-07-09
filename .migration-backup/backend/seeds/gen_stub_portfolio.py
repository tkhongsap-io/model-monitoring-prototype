"""Deterministic stub-portfolio generator — PRD Appendix B §B.8.

Emits AICT-P16…AICT-P130 (115 rows) in ID order with EXACT remainders:
production 30 · in-development 32 (PoV+UAT) · requirements 39 · paused 2 · retired 12;
exactly 2 high-risk production rows carry a missing approval; exactly 11 stub rows
get risk_tier = Unknown. Statuses/tiers/gaps come from fixed quota schedules — the
seed only shuffles names and group assignment, never the asserted counters.
"""
from __future__ import annotations

import zlib

import numpy as np

GROUPS = ["Network AI", "CVM", "Finance", "HR", "Call Center", "CX", "Enterprise",
          "Consumer", "Retail", "AI Council", "Supply Chain", "Legal Ops"]
NOUNS = ["Forecasting", "Classifier", "Assistant", "Recommender", "Scoring", "Summarizer",
         "Anomaly Detector", "Router", "Triage Bot", "Optimizer", "Extractor", "Planner"]
DOMAINS = ["Billing", "Roaming", "Device Upgrade", "Network Ticket", "Store Ops", "Field Force",
           "Contract", "Campaign", "Care Chat", "Invoice", "Coverage", "Loyalty", "Onboarding",
           "Fraud Signal", "Complaint", "Usage Pattern", "Retention", "Knowledge Search",
           "Capacity", "Churn Signal", "Quality Audit", "Sales Lead", "Backhaul"]

# Fixed quota schedules (order is deterministic; the rng only shuffles cosmetic fields)
STATUS_QUOTA = (["production"] * 30 + ["PoV"] * 16 + ["UAT"] * 16
                + ["requirements"] * 39 + ["paused"] * 2 + ["retired"] * 12)
TIER_QUOTA = ["High"] * 18 + ["Medium"] * 46 + ["Low"] * 40 + ["Unknown"] * 11


def generate(seed: int = 42) -> list[dict]:
    g = np.random.default_rng(np.random.SeedSequence([seed, zlib.crc32(b"stub-portfolio")]))
    n = 115
    statuses = list(STATUS_QUOTA)
    tiers = list(TIER_QUOTA)
    assert len(statuses) == n and len(tiers) == n
    # deterministic interleave of quotas across IDs (positions fixed given the seed)
    order = g.permutation(n)
    statuses = [statuses[i] for i in order]
    order2 = g.permutation(n)
    tiers = [tiers[i] for i in order2]

    # exactly 2 high-risk production rows carry a missing approval: pick the first
    # two indices that are (production, High) after interleave; force-create if scarce
    hi_prod = [i for i in range(n) if statuses[i] == "production" and tiers[i] == "High"]
    while len(hi_prod) < 2:  # force enough High production rows (deterministic swap)
        j = next(i for i in range(n) if statuses[i] == "production" and tiers[i] != "High"
                 and tiers[i] != "Unknown")
        k = next(i for i in range(n) if tiers[i] == "High" and i not in hi_prod
                 and statuses[i] != "production")
        tiers[j], tiers[k] = tiers[k], tiers[j]
        hi_prod = [i for i in range(n) if statuses[i] == "production" and tiers[i] == "High"]
    gap_rows = set(hi_prod[:2])

    rows = []
    used_names: set[str] = set()
    for i in range(n):
        rid = f"AICT-P{16 + i}"
        group = GROUPS[int(g.integers(0, len(GROUPS)))]
        for _ in range(50):
            name = f"{DOMAINS[int(g.integers(0, len(DOMAINS)))]} {NOUNS[int(g.integers(0, len(NOUNS)))]}"
            if name not in used_names:
                used_names.add(name)
                break
        status, tier = statuses[i], tiers[i]
        row = {
            "registry_id": rid, "use_case_name": name, "use_case_group": group,
            "status": status, "risk_tier": tier,
            "privacy_status": "Unknown", "security_status": "Unknown",
            "rai_status": "Unknown", "ai_readiness_status": "Unknown",
            "telemetry_status": "Unknown", "current_health": "Unknown",
            "monitoring_owner": "Unknown", "stub": True,
        }
        if status == "production" and tier in ("High", "Medium", "Low"):
            # give production rows plausible evidence so the 4-gap counter stays exact
            row.update({"privacy_status": "Approved", "security_status": "Approved",
                        "rai_status": "Complete", "ai_readiness_status": "Complete",
                        "current_health": "Green"})
        if i in gap_rows:  # the 2 scripted high-risk production approval gaps
            row.update({"rai_status": "Missing", "current_health": "Red"})
        rows.append(row)
    return rows


if __name__ == "__main__":
    import collections
    rows = generate(42)
    print(len(rows), collections.Counter(r["status"] for r in rows))
    print("unknown tier:", sum(1 for r in rows if r["risk_tier"] == "Unknown"))
    print("hi-prod gaps:", sum(1 for r in rows if r["status"] == "production"
                               and r["risk_tier"] == "High"
                               and r["rai_status"] == "Missing"))
