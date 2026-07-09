"""Run one monitoring cycle — the proposal's 'scheduled evaluation' + alerting.

Runs both lanes, grades everything through the control-tower logic, writes the dashboard
JSON the Streamlit app reads, and emits alerts for Critical/High actions (console + a
JSON alert log). Run it on a schedule (Task Scheduler / cron) to embody the risk-based
cadence in §10; the Streamlit app just visualises whatever this last produced.

    python run_all.py
"""
from __future__ import annotations

from common import write_json
from config import load_config
from health import build_dashboard
from llm_lane import run_llm_lane
from ml_lane import run_ml_lane

BAR = "─" * 72


def emit_alerts(cfg, dashboard: dict) -> None:
    alerts = [a for a in dashboard["action_queue"] if a["severity"] in ("Critical", "High")]
    write_json(cfg.artifacts_dir / "alerts.json", alerts)
    if not alerts:
        print("\nALERTS: none — no Red on any use case this cycle.")
        return
    print(f"\nALERTS ({len(alerts)}):")
    for a in alerts:
        print(f"  [{a['severity']}] {a['use_case']} · {a['signal']} = {a['value']} "
              f"({a['health']}) → close within {a['sla']} · {a['recommended_action']}")


def main() -> None:
    cfg = load_config()
    cfg.ensure_dirs()
    print(BAR)
    print("RAI Control Tower — monitoring cycle")
    print(f"LLM lane: {'ONLINE (OpenAI)' if cfg.llm_enabled else 'OFFLINE (simulated)'}"
          f" · Langfuse: {'configured' if cfg.langfuse_enabled else 'not set'}")
    print(BAR)

    print("Running classical-ML lane (churn: Evidently + NannyML + LIME)…")
    ml = run_ml_lane(cfg)
    if ml["errors"]:
        print("  degraded:", ml["errors"])
    print("  signals:", ml["signals"])

    print("Running LLM lane (HR chatbot: Langfuse + LLM-as-judge)…")
    llm = run_llm_lane(cfg)
    print(f"  mode={llm['context']['mode']} interactions={llm['context']['interactions']} "
          f"signals={llm['signals']}")

    dashboard = build_dashboard([ml, llm])
    write_json(cfg.artifacts_dir / "dashboard.json", dashboard)

    print(BAR)
    s = dashboard["summary"]
    print(f"Portfolio: {s['use_case_count']} use cases · "
          f"health {s['overall_counts']} · {s['open_actions']} open actions "
          f"({s['critical_actions']} critical)")
    for uc in dashboard["use_cases"]:
        lanes = " ".join(f"{k}:{v}" for k, v in uc["lanes"].items())
        print(f"  {uc['overall']:7} {uc['name']:32} [{uc['risk_tier']}] {lanes}")
    emit_alerts(cfg, dashboard)
    print(BAR)
    print(f"Wrote {cfg.artifacts_dir / 'dashboard.json'} — run `streamlit run app.py` to view.")


if __name__ == "__main__":
    main()
