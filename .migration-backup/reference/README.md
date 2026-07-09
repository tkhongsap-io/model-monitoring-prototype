# RAI Monitoring Prototype — "AI Use Case Observability Control Tower"

A **runnable** prototype of the RAI operating-model proposal's model monitoring (§10–§13,
**Option D — open stack**), for demoing to the team as *something that works*, not a slide.
It monitors **both** model classes the proposal covers, rolled into one control tower:

| Lane | Use case (synthetic) | Open-source tools | Proposal lanes (§10) |
|---|---|---|---|
| **LLM** | HR Policy Chatbot (RAG) | **Langfuse** (traces + scores) + **LLM-as-judge** | Quality · Safety · Reliability |
| **Classical ML** | Churn / Next-Best-Action | **Evidently** (drift) · **NannyML** (label-free perf) · **LIME**/**SHAP** (explainability) | Drift & degradation · Quality |

Everything the team sees maps 1:1 to the proposal: **registry → 5 monitoring lanes (§10) →
Sheet-3 Green/Amber/Red thresholds (§10) → action queue with SLAs (§11) → risk-based
cadence (§10)**. It turns the static `rai-model-monitoring-mockup.html` into a live app.

> **Prototype, not production.** Data is **synthetic** (no real True data). The churn
> "current" window has **injected drift** so the demo reliably shows monitoring catching a
> degradation. Evals are sampled/illustrative. It shows the honest §13 reality: **two tools
> (LLM + classical), one control tower.**

## Quick start

```bash
# from tools/rai-monitoring-prototype/  (dedicated venv, isolated from the repo .venv)
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt     # Windows
# ./.venv/bin/python  -m pip install -r requirements.txt       # macOS/Linux

# (optional) enable the live LLM lane — otherwise it runs OFFLINE (simulated), no keys needed
cp .env.example .env      # OPENAI_API_KEY is already in the repo-root .env; add LANGFUSE_* for tracing

./.venv/Scripts/python run_all.py          # one monitoring cycle → artifacts/dashboard.json + alerts
./.venv/Scripts/streamlit run app.py       # the live Control Tower
```

- **`run_all.py`** = one monitoring cycle (the proposal's *scheduled evaluation*): runs both
  lanes, grades against Sheet-3, writes `artifacts/dashboard.json`, and prints/logs alerts
  for Critical/High actions. Schedule it (Task Scheduler / cron) to embody the §10 cadence.
- **`app.py`** = the live dashboard: portfolio **lane heatmap**, the **action queue**, and
  per-use-case drill-downs (Evidently drift report, NannyML estimated performance, a
  pick-a-customer **LIME** explanation + **SHAP** global importance, Langfuse eval scores).
  The sidebar **▶ Run monitoring cycle now** button re-runs everything in-process.

## Demo script (≈3 min)

1. **Portfolio heatmap** — two use cases, five lanes, Green/Amber/Red. The **churn model is
   Red** on Drift & Quality; the **chatbot is Green** — "this is §10, live."
2. **Action queue** — the Red churn signals have auto-generated a **Critical (48h)** action
   with an owner and the recommended remediation (§11). "Nothing silently slips."
3. **Churn drill-down** — Evidently shows *which* features drifted; **NannyML** shows the
   estimated ROC-AUC dropped **before labels arrived**; **LIME** explains one high-risk
   customer. "This is the early warning + the 'why'."
4. **Chatbot drill-down** — Langfuse eval scores (groundedness/relevance/hallucination) vs
   the Sheet-3 band. (Live traces in Langfuse if keys are set.)
5. **The close** — "Open-source now; the enterprise path is a swap, not a rebuild" ↓

## Enterprise-swap path (the "switch later" story)

| Prototype (Option D, open) | Enterprise (Option A, Azure) |
|---|---|
| Langfuse | **Azure AI Foundry** observability + evaluators |
| Evidently / NannyML | **Azure ML model monitoring** |
| LIME | **SHAP / Azure ML Responsible AI dashboard** |
| this control tower | same registry, same Sheet-3 thresholds, same action queue |

Same lanes, same thresholds, same registry — only the engine underneath changes.

## LIME vs SHAP (what the team raised)

**LIME** explains one prediction by perturbing around it and fitting a simple local model —
model-agnostic, fast, in the Explainability tab. **Caveat, stated in the UI:** LIME can be
**unstable** (fidelity-vs-simplicity); **SHAP** is the more consistent, game-theoretic
counterpart and is what the enterprise path uses. The prototype shows **both**.

## Self-hosting Langfuse (in-country / PDPA)

v1 uses Langfuse **Cloud** (free tier) for speed. To run it on True infrastructure so data
never leaves the estate, see `docker/langfuse-selfhost.compose.yml` — it's a config flip
(`LANGFUSE_HOST` + keys), not a rebuild.

## Files

`config.py` · `common.py` (Sheet-3 threshold model) · `data_gen.py` (synthetic churn + HR
corpus) · `ml_lane.py` (Evidently/NannyML/LIME/SHAP) · `llm_lane.py` (chatbot + Langfuse +
judge) · `health.py` (registry → lanes → action queue) · `run_all.py` (cycle + alerts) ·
`app.py` (Streamlit). Artifacts (git-ignored) land in `artifacts/`.

## Notes / caveats

- **Synthetic data only** — no real True data; only synthetic HR Q&A reaches Langfuse Cloud.
- Isolated **dedicated venv** (heavy ML stack) so it can't break the repo-root `.venv`.
- `numpy<2` is pinned for compatibility with the older monitoring libs.
- Thresholds here are the §10 **High-risk** demo defaults; in production they're set per use
  case at onboarding from Sheet-3.
