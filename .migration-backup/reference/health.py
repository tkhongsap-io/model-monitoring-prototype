"""Control-tower logic — the proposal's operating model in code.

Takes the raw signals from each lane and produces the registry view the playbook
describes: per-signal Green/Amber/Red/Unknown (Sheet-3, §10), a per-lane rollup, an
overall use-case health, the risk-based cadence (§10), and the action queue with SLAs
(§11). This is the single place the proposal's §10-§11 rules are encoded.
"""
from __future__ import annotations

from common import SIGNAL_SPECS, Health, evaluate_signal, worst

# risk tier -> minimum monitoring cadence (proposal §10 cadence table)
CADENCE = {"High": "Weekly + near-real-time alerts", "Medium": "Monthly + sampled checks",
           "Low": "Quarterly", "Unknown": "Monthly until classified"}

# action severity -> closure SLA (proposal §11 action-queue table)
SLA = {"Critical": "48 hours", "High": "5 working days",
       "Medium": "15 working days", "Low": "30 working days"}

# demo owners (registry-schema.md: business / technical / monitoring owners)
OWNERS = {
    "UC-HRBOT-01": {"business": "HR Ops", "technical": "MITY / IL team", "monitoring": "RAI COE"},
    "UC-CHURN-01": {"business": "CVM / Marketing", "technical": "Data Science", "monitoring": "RAI COE"},
}

# signal -> recommended action (proposal §11 escalation triggers)
RECOMMENDED = {
    "hallucination_rate": "SME review + fix unsupported-answer handling (grounding/refusal).",
    "groundedness": "KB / retrieval-quality review with the content owner.",
    "relevance": "KB / retrieval-quality review with the content owner.",
    "pii_exposure_rate": "Incident runbook S1 — engage Security + DPO immediately.",
    "p95_latency_s": "Technical owner — investigate latency / API failures.",
    "data_drift_share": "Investigate input drift; schedule retraining review (stage-8 re-review).",
    "estimated_roc_auc": "Model degradation — retrain / regression-test; confirm with labels.",
    "realized_roc_auc": "Confirmed model degradation — retrain and re-validate before continuing.",
}


def _action_severity(risk_tier: str, health: Health) -> str | None:
    if health == "Red":
        return "Critical" if risk_tier == "High" else "High"
    if health == "Unknown" and risk_tier == "High":
        return "High"  # critical-Unknown on a High-risk case (§10 map)
    return None


def assess_use_case(lane_result: dict) -> dict:
    """Grade one lane result into the registry view + its action items."""
    tier = lane_result.get("risk_tier", "Unknown")
    graded, lane_health = {}, {}
    for key, value in lane_result.get("signals", {}).items():
        spec = SIGNAL_SPECS.get(key)
        h = evaluate_signal(key, value)
        graded[key] = {
            "value": value, "health": h,
            "label": spec.label if spec else key,
            "lane": spec.lane if spec else "Other",
        }
        lane_health.setdefault(spec.lane if spec else "Other", []).append(h)

    lanes = {lane: worst(hs) for lane, hs in lane_health.items()}
    overall = worst(list(lanes.values()))

    actions = []
    for key, g in graded.items():
        sev = _action_severity(tier, g["health"])
        if sev:
            actions.append({
                "use_case_id": lane_result["use_case_id"],
                "use_case": lane_result["name"],
                "signal": g["label"], "signal_key": key,
                "value": g["value"], "health": g["health"],
                "severity": sev, "sla": SLA[sev],
                "recommended_action": RECOMMENDED.get(key, "Review with the technical owner."),
                "owner": OWNERS.get(lane_result["use_case_id"], {}).get("monitoring", "RAI COE"),
            })

    return {
        "use_case_id": lane_result["use_case_id"],
        "name": lane_result["name"],
        "type": lane_result.get("type", ""),
        "risk_tier": tier,
        "cadence": CADENCE.get(tier, CADENCE["Unknown"]),
        "owners": OWNERS.get(lane_result["use_case_id"], {}),
        "overall": overall,
        "lanes": lanes,
        "signals": graded,
        "actions": actions,
        "context": lane_result.get("context", {}),
        "artifacts": lane_result.get("artifacts", {}),
        "errors": lane_result.get("errors", {}),
    }


def build_dashboard(lane_results: list[dict]) -> dict:
    """Roll up all use cases into the portfolio view + a single action queue."""
    assessed = [assess_use_case(r) for r in lane_results]
    actions = [a for uc in assessed for a in uc["actions"]]
    sev_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    actions.sort(key=lambda a: sev_rank.get(a["severity"], 9))

    counts = {"Green": 0, "Amber": 0, "Red": 0, "Unknown": 0}
    for uc in assessed:
        counts[uc["overall"]] += 1

    return {
        "use_cases": assessed,
        "action_queue": actions,
        "summary": {
            "use_case_count": len(assessed),
            "overall_counts": counts,
            "open_actions": len(actions),
            "critical_actions": sum(1 for a in actions if a["severity"] == "Critical"),
        },
    }
