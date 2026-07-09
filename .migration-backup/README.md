# Model Monitoring Prototype — AI Use Case Observability Control Tower

> **CPG Confidential & Proprietary.** Internal to True Corporation / CP Group. **Keep this repository private — do not make it public.** Contains no real True data and no PII (all telemetry is synthetic by design); confidentiality applies to the operating-model and governance context.

A **simulation-first demo web app** that shows what True's Responsible-AI **model-monitoring** tool will look like — running, not on slides. It simulates end-to-end monitoring for **two use cases at once**: an **LLM** use case (HR Policy Chatbot, RAG) and a **classical-ML** use case (Churn / Next-Best-Action) — because the RAI operating model's central finding is that no single tool natively covers both.

A presenter plays a scenario: **baseline (all Green) → drift injected → the portfolio heatmap flips to Red → a Critical action fires against a named owner with a 2-day SLA → the SLA breaches and auto-escalates → remediation turns it Green again.** It makes the operating model (five monitoring lanes, Sheet-3 Green/Amber/Red grading, an action queue with SLAs) concrete in ~10 minutes.

## Status

**✅ BUILT & VERIFIED** — the prototype is implemented per `docs/PRD.md` and passes its full test suite (20/20, including the C1–C9 golden calibration on the 20-tick DEMO-FULL scenario at seed 42, with a double-bake determinism check). All 7 dashboard views + drill-downs + the scenario player run end-to-end.

## Quick start (two commands + one bake)

```bash
# 0) one-time setup
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cd ../frontend && npm install

# 1) bake the demo scenario (precomputes all 20 ticks through the real engines, ~90s)
cd ../backend && .venv/Scripts/python ../scripts/demo_reset.py

# 2) run (two terminals)
cd backend  && .venv/Scripts/python -m uvicorn app.main:app --port 8000   # API
cd frontend && npm run dev                                                # UI on :3000
```

Open **http://localhost:3000** → use the scenario player bar (bottom): pick **DEMO-FULL**, press **▶ Play** (or `Space`; `←`/`→` step, `R` reset). Runs **fully offline with an empty `.env`** — the Langfuse stub is the default. With `LANGFUSE_*` keys + `LLM_EVAL_ADAPTER=langfuse_cloud` in `.env`, chatbot traces/scores also push to Langfuse Cloud (synthetic Q&A only).

**Tests:** `cd backend && .venv/Scripts/python -m pytest tests` (add `-m "not slow"` to skip the ~90s golden bake).

## What's here

| Path | What it is |
|---|---|
| **`docs/PRD.md`** | The **v1.0 PRD** — the build contract (requirements, the 7 views, scenario scripts, thresholds, registry schema, API). |
| **`backend/`** | FastAPI app: 130-row assurance registry, Sheet-3 health engine, action queue + SLA auto-escalation, scenario engine (bake mode), the three engine adapters, seeds, tests. |
| **`frontend/`** | Next.js app: the 7 dashboard views, use-case drill-downs (Evidently/LIME/SHAP embeds, NannyML chart, judge scores, traces), scenario player bar. |
| **`scripts/demo_reset.py`** | One-shot: reseed the registry + bake DEMO-FULL at seed 42 (the R-34 demo-day reset). |
| **`reference/`** | The original working reference prototype (Streamlit) the build ported from. Provenance only. |
| **`docs/context/`** | The RAI operating-model proposal (§10–§13), registry schema, and 7-view dashboard spec. |

## Architecture (per the PRD)

- **Frontend:** Next.js 14 / React / TypeScript / Tailwind + recharts; same-origin `/api/*` rewrites → FastAPI (ports 3000/8000).
- **Backend:** FastAPI (Python 3.12) · SQLite (ADR-1: Postgres at pilot) · **bake mode** — the whole scenario is precomputed through the real engines; every demo tick is a DB read (<1s step, <2s reset, measured ~35ms).
- **Engines (open-source, proposal Option D)** behind exactly three adapter protocols (the Azure Option-A swap seam): `LLMEvalAdapter` (Langfuse stub → SQLite | Langfuse Cloud; deterministic seeded judge) · `MLMonitorAdapter` (Evidently 0.4.x drift + NannyML CBPE) · `ExplainAdapter` (LIME + SHAP).
- **Deterministic:** seed 42; two bakes are byte-identical (CI-asserted).

## Calibration notes (M1 — honest engineering record)

The PRD's illustrative trajectories were calibrated against the **real** engines at seed 42 (see the record in `backend/app/datagen/churn.py` and `backend/scenarios/simulation.yaml`):
- Generator z-signal scaled (C_SCALE 2.4) so out-of-sample baseline AUC ≈ 0.85; **concept drift** added to the drifted world so the old model genuinely loses skill (realized AUC → **0.71 Red** at t13) while a retrained model recovers (**0.82 Green** at t18); compression made **invertible** so recovery is learnable.
- **NannyML CBPE finding:** the label-free estimate dips measurably under drift but stays conservative (it never reaches the illustrative Amber band) — a real property of CBPE under covariate shift, kept and told honestly in the demo: *"the estimate warns early but conservatively; the labels confirm worse."* The Sheet-3 bands were never moved.
- `churn_alpha` ramps recalibrated to the real Evidently trip points (Amber 0.375 at t8, Red 0.75 at t9), exactly as §A.7 prescribes.
