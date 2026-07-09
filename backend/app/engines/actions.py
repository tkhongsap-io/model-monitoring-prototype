"""Action queue — severity map (C.3), SLAs + per-severity auto-escalation (C.4), dedupe.

State is evolved tick-by-tick during bake; each tick's complete action list is
persisted in the baked tick payload (bake-mode semantics).
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

from .health import SIGNAL_SPECS

SLA_TICKS = {"Critical": 2, "High": 5, "Medium": 15, "Low": 30}
SLA_LABEL = {"Critical": "48 h", "High": "5 working days",
             "Medium": "15 working days", "Low": "30 working days"}

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

ESCALATION_BASE = {
    "hallucination_rate": "SME review", "groundedness": "KB owner + technical owner",
    "relevance": "KB owner + technical owner", "pii_exposure_rate": "Security + DPO (S1)",
    "p95_latency_s": "Technical owner", "data_drift_share": "Technical owner",
    "estimated_roc_auc": "Data Science", "realized_roc_auc": "Data Science",
}

BREACH_ESCALATION = {
    "Critical": "RAI Council + CDAO notification",
    "High": "one level (owner → business owner → Council)",
    "Medium": "COE chases; flagged in weekly review",
    "Low": "batch-reviewed monthly",
}

EPOCH = date(2026, 7, 13)  # tick 0 (B.5 demo-clock convention)


def tick_date(tick: int) -> str:
    return (EPOCH + timedelta(days=tick)).isoformat()


def severity_for(health: str, risk_tier: str, *, amber_persist: bool = False,
                 critical_unknown: bool = False) -> str | None:
    """C.3 colour -> action-severity map."""
    if health == "Red":
        return "Critical" if risk_tier == "High" else "High"
    if amber_persist:
        return "Medium"
    if critical_unknown and risk_tier == "High":
        return "High"
    return None


class ActionEngine:
    """Evolves the action/alert/event state across ticks during a bake."""

    def __init__(self) -> None:
        self.actions: list[dict] = []
        self.alerts: list[dict] = []
        self._seq = 0
        self.suppressed: dict[tuple[str, str], int] = {}  # (registry_id, key) -> until_tick

    def _next_id(self) -> str:
        self._seq += 1
        return f"ACT-{self._seq:03d}"

    def open_action(self, registry_id: str, key: str) -> dict | None:
        for a in self.actions:
            if (a["registry_id"] == registry_id and a["signal_key"] == key
                    and a["status"] in ("Open", "In progress")):
                return a
        return None

    def observe(self, tick: int, registry_id: str, key: str, value, health: str,
                risk_tier: str, owner: str, events: list[dict]) -> None:
        """Fire/attach an action for a Red observation (dedupe + suppression rules)."""
        if health != "Red":
            return
        if self.suppressed.get((registry_id, key), -1) >= tick:
            return
        existing = self.open_action(registry_id, key)
        spec = SIGNAL_SPECS.get(key)
        issue = f"{spec.label if spec else key} = {_fmt(value, key)} (Red)"
        if existing:
            existing["issue"] = issue  # re-observed Red attaches, no duplicate
            return
        severity = severity_for("Red", risk_tier)
        action = {
            "action_id": self._next_id(), "registry_id": registry_id, "signal_key": key,
            "issue": issue, "recommended_action": RECOMMENDED.get(key, "Review with the technical owner."),
            "owner": owner, "severity": severity, "sla": SLA_LABEL[severity],
            "opened_at_tick": tick, "due_tick": tick + SLA_TICKS[severity],
            "due_date": tick_date(tick + SLA_TICKS[severity]),
            "escalation_path": ESCALATION_BASE.get(key, "technical owner"),
            "status": "Open", "evidence_link": "", "escalated": False,
            "history": [{"tick": tick, "event": f"created ({severity}, due t{tick + SLA_TICKS[severity]})"}],
        }
        self.actions.append(action)
        self.alerts.append({
            "alert_id": f"AL-{len(self.alerts) + 1:03d}", "tick": tick,
            "registry_id": registry_id, "signal_key": key, "value": value,
            "health": health, "severity": severity, "sla": SLA_LABEL[severity],
            "owner": owner, "recommended_action": action["recommended_action"],
        })
        events.append({"type": "action_opened", "action_id": action["action_id"],
                       "registry_id": registry_id, "signal_key": key,
                       "severity": severity, "due_tick": action["due_tick"]})

    def amber_persistence(self, tick: int, registry_id: str, key: str, risk_tier: str,
                          owner: str, events: list[dict]) -> None:
        """Amber across 2 consecutive weekly reviews -> Medium action (C.3)."""
        if self.open_action(registry_id, key):
            return
        spec = SIGNAL_SPECS.get(key)
        action = {
            "action_id": self._next_id(), "registry_id": registry_id, "signal_key": key,
            "issue": f"{spec.label if spec else key} Amber across 2 consecutive weekly reviews",
            "recommended_action": RECOMMENDED.get(key, "Review with the technical owner."),
            "owner": owner, "severity": "Medium", "sla": SLA_LABEL["Medium"],
            "opened_at_tick": tick, "due_tick": tick + SLA_TICKS["Medium"],
            "due_date": tick_date(tick + SLA_TICKS["Medium"]),
            "escalation_path": ESCALATION_BASE.get(key, "technical owner"),
            "status": "Open", "evidence_link": "", "escalated": False,
            "history": [{"tick": tick, "event": "created (Medium — Amber persistence at weekly review)"}],
        }
        self.actions.append(action)
        events.append({"type": "action_opened", "action_id": action["action_id"],
                       "registry_id": registry_id, "signal_key": key, "severity": "Medium",
                       "due_tick": action["due_tick"]})

    def sla_breach_check(self, tick: int, events: list[dict]) -> None:
        """Per tick after grading: due-tick passed -> per-severity escalation (C.4).
        The action stays open — escalation is added visibility, not closure."""
        for a in self.actions:
            if a["status"] in ("Open", "In progress") and not a["escalated"] and tick > a["due_tick"]:
                a["escalated"] = True
                a["escalation_path"] = f'{a["escalation_path"]} → {BREACH_ESCALATION[a["severity"]]}'
                a["history"].append({"tick": tick, "event": f'SLA breached → auto-escalated: {BREACH_ESCALATION[a["severity"]]}'})
                self.alerts.append({
                    "alert_id": f"AL-{len(self.alerts) + 1:03d}", "tick": tick,
                    "registry_id": a["registry_id"], "signal_key": a["signal_key"],
                    "value": None, "health": "Red", "severity": a["severity"], "sla": a["sla"],
                    "owner": a["owner"],
                    "recommended_action": f'ESCALATED: {BREACH_ESCALATION[a["severity"]]}',
                })
                events.append({"type": "action_escalated", "action_id": a["action_id"],
                               "registry_id": a["registry_id"],
                               "escalation": BREACH_ESCALATION[a["severity"]]})

    def close(self, tick: int, action_ids: list[str], evidence_link: str,
              events: list[dict], suppress_ticks: int = 0) -> None:
        """Scripted CLOSE_ACTION: close with evidence; optionally suppress re-fire
        (post-remediation label-lag rule, §A.5.5)."""
        for a in self.actions:
            if a["action_id"] in action_ids and a["status"] != "Closed":
                a["status"] = "Closed"
                a["evidence_link"] = evidence_link
                a["history"].append({"tick": tick, "event": "closed (Close with evidence)"})
                if suppress_ticks:
                    self.suppressed[(a["registry_id"], a["signal_key"])] = tick + suppress_ticks
                events.append({"type": "action_closed", "action_id": a["action_id"],
                               "registry_id": a["registry_id"]})

    def snapshot(self) -> tuple[list[dict], list[dict]]:
        return copy.deepcopy(self.actions), copy.deepcopy(self.alerts)


def _fmt(value, key: str) -> str:
    if value is None:
        return "—"
    if key in ("hallucination_rate", "pii_exposure_rate", "data_drift_share"):
        return f"{value:.3f}" if key == "data_drift_share" else f"{value * 100:.1f}%"
    if key == "p95_latency_s":
        return f"{value:.1f}s"
    return f"{value:.3f}" if isinstance(value, float) else str(value)
