# AGENTS.md — build context for AI coding tools

Orientation for any AI agent (Claude Code, Cursor, etc.) working in this repository.

## What this project is

A **simulation-first demo web app** that simulates AI model monitoring (one LLM + one classical-ML use case) for True Corporation's Responsible-AI COE. It is a **demo/prototype**, not production — it proves the monitoring operating model by running it against synthetic, scenario-driven telemetry.

## The single source of truth

**`docs/PRD.md` is authoritative.** It is a self-contained v1.0 PRD (canon thin-contract style): §1–§12 are the contract, Appendices A–G carry the detail (A simulation & scenarios · B registry data model & seeds · C thresholds & SLA · D the 7 views · E architecture/API/repo skeleton · F demo script · G enterprise-swap). Build to it. If something seems missing, it is almost certainly in an appendix — check before inventing.

**Do not build ahead of the PRD.** Follow its milestones **M0 → M3** and its P0/P1/P2 requirement priorities. When a decision isn't in the PRD, ask rather than guess; `[TBC]` markers are unresolved on purpose — don't silently resolve them.

## The reference implementation

`reference/` is a **verified working prototype** (Python / Streamlit) that proves the engine logic:
- `common.py` — the **Sheet-3 threshold model** (Green/Amber/Red bands) — port this almost verbatim.
- `ml_lane.py` — Evidently (drift) + NannyML (label-free performance) + LIME/SHAP wiring.
- `llm_lane.py` — LLM-eval signals + trace/score handling (deterministic offline mode).
- `health.py` — registry → lanes → action queue with SLAs.
- `data_gen.py` — synthetic churn generator (with drift injection) + HR corpus/Q&A.

**Port the logic; do not depend on `reference/`.** The real build is greenfield: Next.js/React + TypeScript frontend, FastAPI backend, SQLite. `reference/` is Streamlit and exists only as proof + a porting source.

## Stack & conventions (from the PRD)

- **Frontend:** Next.js (app router) + TypeScript + Tailwind + a chart lib; the 7 views + a docked scenario player; all API calls same-origin via Next rewrites to the backend (dev ports 3000/8000).
- **Backend:** FastAPI; one API contract (PRD Appendix E §E.3, `/api` prefix); three engine adapter protocols (`LLMEvalAdapter`, `MLMonitorAdapter`, `ExplainAdapter`) + a non-engine `ScenarioSource`.
- **Determinism:** the demo must run **offline with zero API keys**, seeded (seed 42), bake-mode default (precompute the scenario; advancing a tick is a DB read). Reset restores baked tick 0.
- **Pins/gotchas:** Python 3.12 · `nannyml>=0.13,<0.14` · `numpy<2` · `evidently>=0.4.20,<0.5` · `langfuse>=2.53,<3` (or the stub). Pass `random_state=seed` to LIME; SHAP background `random_state=0`.

## Guardrails

- **Confidential + private.** This repo is CPG Confidential — keep it private, never publish externally.
- **No real data, ever.** All telemetry is synthetic; no PII; no real True customer or employee data.
- **No secrets in git.** `.env` is gitignored; only `reference/.env.example` (placeholders) is tracked.
