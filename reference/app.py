"""AI Use Case Observability Control Tower — Pilot (Streamlit).

Live view of the proposal's operating model: portfolio health (Green/Amber/Red per the
five §10 lanes), the Sheet-3 signal grades, the §11 action queue, and the open-stack tool
outputs (Evidently drift, NannyML label-free performance, LIME/SHAP explanations, Langfuse
eval scores). Reads artifacts/dashboard.json produced by run_all.py; the sidebar button
runs a fresh cycle in-process.

    streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from common import read_json
from config import load_config

RED, DARK = "#e60012", "#b9000e"
COLORS = {"Green": "#00a66c", "Amber": "#ffb000", "Red": "#e60012", "Unknown": "#8a8f98"}
LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation", "Feedback"]

st.set_page_config(page_title="RAI Control Tower — Pilot", layout="wide", page_icon="🛡️")

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.4rem; max-width: 1400px; }}
  .tt-bar {{ background: linear-gradient(135deg,#111 0%,#1a1a1a 45%,{RED} 100%);
             color:#fff; padding: 14px 20px; border-radius: 10px; margin-bottom: 14px;
             display:flex; align-items:center; gap:14px; }}
  .tt-mark {{ background:#fff; color:{RED}; font-weight:800; border-radius:999px;
              padding:3px 12px; font-size:15px; letter-spacing:-.02em; }}
  .tt-conf {{ margin-left:auto; background:{RED}; border:1px solid #fff3; border-radius:999px;
              padding:3px 10px; font-size:11px; font-weight:800; letter-spacing:.05em; }}
  .hl {{ display:inline-block; color:#fff; border-radius:6px; padding:2px 9px; font-weight:700;
         font-size:12px; text-align:center; min-width:64px; }}
  .cell {{ border-radius:6px; padding:6px 4px; color:#fff; font-weight:700; text-align:center;
           font-size:12px; }}
  table.heat {{ border-collapse:separate; border-spacing:5px; width:100%; }}
  table.heat td, table.heat th {{ font-size:12.5px; }}
  table.heat th {{ text-align:center; color:#5c6370; font-weight:700; padding:4px; }}
  table.heat td.name {{ text-align:left; font-weight:600; color:#141414; white-space:nowrap; }}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="tt-bar"><span class="tt-mark">true</span>'
    '<b>AI Use Case Observability Control Tower</b> — Pilot &nbsp;·&nbsp; Responsible AI, COE'
    '<span class="tt-conf">CPG CONFIDENTIAL · SYNTHETIC DEMO DATA</span></div>',
    unsafe_allow_html=True)

cfg = load_config()
ART = cfg.artifacts_dir


def badge(health: str, text: str | None = None) -> str:
    return f'<span class="hl" style="background:{COLORS.get(health, "#888")}">{text or health}</span>'


# ---- sidebar: run a cycle -----------------------------------------------------------
with st.sidebar:
    st.subheader("Monitoring cycle")
    st.caption(f"LLM lane: **{'ONLINE (OpenAI)' if cfg.llm_enabled else 'OFFLINE (simulated)'}**  \n"
               f"Langfuse: **{'configured' if cfg.langfuse_enabled else 'not set'}**")
    if st.button("▶ Run monitoring cycle now", type="primary", use_container_width=True):
        with st.spinner("Training model, running Evidently / NannyML / LIME + LLM evals…"):
            from health import build_dashboard
            from llm_lane import run_llm_lane
            from ml_lane import run_ml_lane
            from common import write_json
            d = build_dashboard([run_ml_lane(cfg), run_llm_lane(cfg)])
            write_json(ART / "dashboard.json", d)
        st.success("Cycle complete.")
        st.rerun()
    st.caption("Or from a terminal: `python run_all.py` (schedule it for the §10 cadence).")
    st.divider()
    st.caption("Maps to the proposal: registry → 5 lanes (§10) → Sheet-3 Green/Amber/Red "
               "(§10) → action queue with SLAs (§11).")

dashboard = read_json(ART / "dashboard.json")
if not dashboard:
    st.info("No monitoring data yet — click **▶ Run monitoring cycle now** in the sidebar "
            "(or run `python run_all.py`).")
    st.stop()

use_cases = dashboard["use_cases"]
summary = dashboard["summary"]

# ---- portfolio summary --------------------------------------------------------------
c = st.columns(4)
c[0].metric("Use cases", summary["use_case_count"])
c[1].metric("Red / Amber", f'{summary["overall_counts"]["Red"]} / {summary["overall_counts"]["Amber"]}')
c[2].metric("Open actions", summary["open_actions"])
c[3].metric("Critical actions", summary["critical_actions"])

# ---- monitoring lane heatmap --------------------------------------------------------
st.subheader("Monitoring lane heatmap")
rows = ['<table class="heat"><tr><th style="text-align:left">Use case</th><th>Risk</th>'
        + "".join(f"<th>{l}</th>" for l in LANES) + "<th>Overall</th></tr>"]
for uc in use_cases:
    cells = [f'<td class="name">{uc["name"]}</td>',
             f'<td style="text-align:center;color:#5c6370">{uc["risk_tier"]}</td>']
    for lane in LANES:
        h = uc["lanes"].get(lane)
        cells.append(f'<td class="cell" style="background:{COLORS[h]}">{h}</td>' if h
                     else '<td class="cell" style="background:#eceef1;color:#9aa0a6">—</td>')
    cells.append(f'<td class="cell" style="background:{COLORS[uc["overall"]]}">{uc["overall"]}</td>')
    rows.append("<tr>" + "".join(cells) + "</tr>")
st.markdown("".join(rows) + "</table>", unsafe_allow_html=True)
st.caption("Green = Sheet-3 'continue in production' · Red = 'issue/escalate' · "
           "Amber = trending/behavioural · — = lane not monitored for this type · "
           "Unknown = missing telemetry (itself a finding).")

# ---- action queue -------------------------------------------------------------------
st.subheader(f"Action queue ({len(dashboard['action_queue'])})")
if dashboard["action_queue"]:
    for a in dashboard["action_queue"]:
        st.markdown(
            f'{badge("Red", a["severity"])} &nbsp; **{a["use_case"]}** — {a["signal"]} = '
            f'`{a["value"]}` &nbsp;·&nbsp; close within **{a["sla"]}** &nbsp;·&nbsp; '
            f'owner: {a["owner"]}  \n&nbsp;&nbsp;↳ {a["recommended_action"]}',
            unsafe_allow_html=True)
else:
    st.success("No open actions — nothing Red this cycle.")

# ---- use-case drill-down ------------------------------------------------------------
st.divider()
st.subheader("Use-case detail")
names = {uc["name"]: uc for uc in use_cases}
pick = st.selectbox("Select a use case", list(names))
uc = names[pick]

top = st.columns([1, 1, 1, 1])
top[0].markdown(f"**Overall**  \n{badge(uc['overall'])}", unsafe_allow_html=True)
top[1].markdown(f"**Risk tier**  \n{uc['risk_tier']}")
top[2].markdown(f"**Cadence**  \n{uc['cadence']}")
top[3].markdown(f"**Monitoring owner**  \n{uc['owners'].get('monitoring', '—')}")

st.markdown("**Signals (value vs Sheet-3 band)**")
sig_rows = ['<table class="heat"><tr><th style="text-align:left">Signal</th><th style="text-align:left">Lane</th><th>Value</th><th>Health</th></tr>']
for key, g in uc["signals"].items():
    val = "—" if g["value"] is None else (f'{g["value"]:.3f}' if isinstance(g["value"], float) else g["value"])
    sig_rows.append(
        f'<tr><td class="name">{g["label"]}</td><td class="name" style="color:#5c6370">{g["lane"]}</td>'
        f'<td style="text-align:center">{val}</td>'
        f'<td class="cell" style="background:{COLORS[g["health"]]}">{g["health"]}</td></tr>')
st.markdown("".join(sig_rows) + "</table>", unsafe_allow_html=True)

if uc.get("errors"):
    st.warning("Some tools degraded this run: " + ", ".join(f"{k}: {v}" for k, v in uc["errors"].items()))

ctx = uc.get("context", {})
art = uc.get("artifacts", {})

if uc["use_case_id"] == "UC-CHURN-01":
    tabs = st.tabs(["Drift (Evidently)", "Performance (NannyML)", "Explainability (LIME / SHAP)"])
    with tabs[0]:
        st.caption("Drifted features: " + (", ".join(ctx.get("drifted_features", [])) or "none reported"))
        p = art.get("evidently_html")
        if p and Path(p).exists():
            components.html(Path(p).read_text(encoding="utf-8"), height=620, scrolling=True)
        else:
            st.info("Evidently report not available.")
    with tabs[1]:
        sig = uc["signals"]
        st.write({"estimated_roc_auc (label-free, NannyML)": sig["estimated_roc_auc"]["value"],
                  "realized_roc_auc (once labels arrive)": sig["realized_roc_auc"]["value"],
                  "reference_roc_auc (training window)": ctx.get("reference_roc_auc")})
        st.caption("NannyML estimates production performance **before** ground-truth labels "
                   "arrive — the early-warning the proposal's Drift/Quality lanes rely on.")
    with tabs[2]:
        inst = ctx.get("lime_instance", {})
        cp = inst.get("churn_proba")
        if cp is not None:
            st.caption(f"LIME explanation for the highest-risk customer "
                       f"(row {inst.get('index')}, churn prob {cp:.2f}).")
        p = art.get("lime_html")
        if p and Path(p).exists():
            components.html(Path(p).read_text(encoding="utf-8"), height=380, scrolling=True)
        if ctx.get("lime_top"):
            st.write("Top contributing factors:", ctx["lime_top"])
        sp = art.get("shap_png")
        if sp and Path(sp).exists():
            st.image(sp, caption="SHAP global feature importance (the consistent, "
                                 "enterprise-path counterpart to LIME).")
        st.caption("⚠ LIME explanations are local and can be unstable (fidelity-vs-simplicity). "
                   "SHAP is the more consistent, game-theoretic counterpart — and what the "
                   "enterprise path (Azure ML Responsible AI dashboard) uses.")
else:
    st.caption(f"Mode: **{ctx.get('mode', '?')}** · {ctx.get('interactions', 0)} interactions"
               + (f" · pushed to Langfuse ({ctx.get('langfuse_host')})" if ctx.get("langfuse_pushed")
                  else " · Langfuse not configured (set LANGFUSE_* to push traces/scores)"))
    if ctx.get("sample"):
        st.markdown("**Sample evaluated interactions**")
        st.dataframe([{"question": s["question"], "answer": s["answer"][:80],
                       "groundedness": round(s["groundedness"], 2),
                       "relevance": round(s["relevance"], 2),
                       "hallucination": s["hallucination"]} for s in ctx["sample"]],
                     use_container_width=True, hide_index=True)
