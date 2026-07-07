# Model Monitoring Prototype — AI Use Case Observability Control Tower

> **CPG Confidential & Proprietary.** Internal to True Corporation / CP Group. **Keep this repository private — do not make it public.** Contains no real True data and no PII (all telemetry is synthetic by design); confidentiality applies to the operating-model and governance context.

A **simulation-first demo web app** that shows what True's Responsible-AI **model-monitoring** tool will look like — running, not on slides. It simulates end-to-end monitoring for **two use cases at once**: an **LLM** use case (HR Policy Chatbot, RAG) and a **classical-ML** use case (Churn / Next-Best-Action) — because the RAI operating model's central finding is that no single tool natively covers both.

A presenter plays a scenario: **baseline (all Green) → drift injected → the portfolio heatmap flips to Red → a Critical action fires against a named owner with a 2-day SLA → the SLA breaches and auto-escalates → remediation turns it Green again.** It makes the operating model (five monitoring lanes, Sheet-3 Green/Amber/Red grading, an action queue with SLAs) concrete in ~10 minutes.

## Status

**Spec ready — not built.** This repo currently holds the PRD, the working reference implementation, and context. Application code follows the PRD's milestones (M0–M3). **Do not build ahead of the PRD.**

## What's here

| Path | What it is |
|---|---|
| **`docs/PRD.md`** | The **v1.0 PRD** — the self-contained, buildable spec. Everything a builder needs (requirements, the 7 views, scenario scripts, thresholds, registry schema, API, repo skeleton) is embedded. **Start here.** |
| **`reference/`** | A **verified working reference implementation** (Python/Streamlit) proving the engine logic — Sheet-3 thresholds, Evidently/NannyML/LIME/SHAP wiring, the health + action loop. **Port from it; don't depend on it** (the real build is greenfield). Synthetic data only. |
| **`docs/context/`** | The "why" — the RAI operating-model proposal (§10–§13), the registry schema, and the 7-view dashboard spec. Provenance/context, not build dependencies (the PRD embeds what's needed). |

## The build (per `docs/PRD.md`)

- **Frontend:** Next.js / React + TypeScript — the 7 dashboard views + a docked scenario player.
- **Backend:** FastAPI (Python) — registry, Sheet-3 health engine, action queue, scenario engine.
- **Store:** SQLite (demo); Postgres at pilot stage.
- **Engines (open-source, proposal Option D):** Langfuse (or a compatible stub), Evidently, NannyML, LIME + SHAP — behind three adapter interfaces so the enterprise Azure path (Option A) is a swap, not a rebuild.
- **Runs fully offline** — no API keys required for the demo (deterministic seeded simulation).
- **Milestones:** M0 scaffold → M1 engines + scenario core → M2 the 7 views → M3 polish + demo script (hard "demo-ready" gate before the team meeting).

## Read next

1. `docs/PRD.md` — the spec.
2. `reference/README.md` — how the proven reference prototype runs, and the enterprise-swap story.
3. `docs/context/` — the operating model behind it.
