---
name: prd-control-tower-simulation-demo
description: PRD v1.0 for the AI Use Case Observability Control Tower — Simulation Demo. A self-contained, buildable contract for a demo prototype web app that simulates model monitoring for one LLM and one classical-ML use case, driven by a deterministic scenario player over synthetic telemetry.
type: prd
status: draft
version: 1.0
owner: RAI COE (Ta)
last_reviewed: 2026-07-07
source_docs:
  - rai-operating-model-proposal.md (§10–§13) — RAI operating-model playbook v0.5
  - registry-schema.md — assurance registry field definitions (2026-07-06)
  - control-tower-dashboard-prototype.md — the 7 dashboard views (2026-07-06)
  - tools/rai-monitoring-prototype/ — verified reference implementation (Sheet-3 bands, synthetic data generators, lane engines, health/action logic)
supersedes: v0.1 (git history, same path)
---

# PRD — AI Use Case Observability Control Tower: Simulation Demo (v1.0)

> **CPG Confidential & Proprietary.** Internal working document for the AI Transformation / RAI COE team, True Corporation / CP Group. Do not distribute externally. Contains no real True data and no PII by design (see NG2) — confidentiality applies to the operating model and governance content, not to any telemetry, which is entirely synthetic.

**How to read this document.** This is a thin contract: the core (§1–§12) is everything a builder needs to commit to; detail lives in Appendices A–G and is referenced, never restated. §5 (Requirements) is the row-level build checklist; §4 gives the user stories those rows serve; Appendices A–G carry the simulation spine and scenario scripts, the registry data model & seeds, thresholds & SLA, the 7-view UX spec, architecture/API & repo, the demo script, and the enterprise-swap map. **The demo is built in its own repository and this PRD is self-contained** — every threshold, field name, scenario tick, and version pin a builder needs is embedded here or in an appendix. Paths into the `life-os` repository appear only in §12's provenance row and are never a build dependency. `[TBC]` marks an unverified number or date; do not resolve one silently.

**Reframe from v0.1.** v0.1 specified a pilot monitoring tool fed by real telemetry. v1.0 narrows the product to a **simulation demo**: a prototype web app that *simulates* end-to-end model monitoring for two synthetic use cases so the RAI COE team can *see* the target tool before deciding to build it for real. The engines are real (open-source, proposal Option D); the telemetry is synthetic and scenario-driven; the pilot-scale concerns (RBAC, real ingestion, retention, HA) are explicitly deferred (§9) and return at pilot stage.

---

## 1. Problem Statement

True Corporation runs a large registered AI portfolio — on the order of 125–131 use cases depending on the source snapshot (three un-reconciled counts: the RAI Council #3 register 131 · the 6-Jul COE count 125 · the board narrative 130; reconciling them is itself an open wave-1 item due before the Aug-4 board update [TBC] — this PRD deliberately does not depend on any one number; the demo's seeded counters are a synthetic echo of the board-narrative set, per NG1 and Appendix B). Roughly a third of those are already live in production. **Once a use case goes live, there is no systematic check that it keeps working**: no drift detection, no quality trend, no owner-bound action loop when something degrades.

Three forcing events make this acute:

1. **Accenture — who stood up the RAI framework and runs the gate today — exits at end of July 2026.** Post-deployment monitoring passes to True's own RAI COE.
2. **The RAI Council assigned model-degradation monitoring to the COE + IT.** The operating model for it exists on paper (proposal §10–§13): five monitoring lanes, Sheet-3-format Green/Amber/Red grading, an action queue with SLAs, risk-based cadence. Nobody on the team has seen it *running*.
3. **A board update on RAI/governance lands 4 August 2026**, and a ~1-month tooling evaluation (proposal §13.7) must decide between cloud-native monitoring suites and an open stack.

The immediate problem this PRD solves is narrower than "build the monitoring platform": **the COE team and CDAO need to see what the target tool is before they can align on building it.** Another slide deck will not do that — the team has had decks. What is missing is a working artifact: a web app where a presenter plays drift into a model, the portfolio heatmap flips to Red, a Critical action with a two-working-day SLA fires against a named owner, and remediation turns it Green again — for both an LLM use case and a classical-ML use case, because the proposal's central honest finding (§13) is that no single tool natively covers both.

## 2. Hypothesis

**A working simulation demo aligns the team and CDAO on the monitoring operating model faster and more durably than documents can** — because seeing the loop run (drift → Red → action → SLA → recovery) makes the §10–§11 rules concrete in ten minutes, where the playbook takes hours to absorb and still leaves the tool imagined differently by each reader.

Secondary hypotheses, each testable by the §7 metrics:

- **The demo skeleton is the pilot's skeleton.** Because the registry schema, health engine, action queue, and 7 views are implemented for real (not mocked pixels), the same codebase grows into the pilot tool by swapping the synthetic `ScenarioSource` for real telemetry per the proposal's §12 contract — no rebuild.
- **The demo de-risks tooling-evaluation direction-ask #2.** By running the proposal's §13.5 Option D stack (Langfuse, Evidently, NannyML) plus LIME+SHAP explainability (from the verified reference implementation; SHAP is also the Azure Responsible-AI-dashboard path) behind adapter protocols, the demo *shows* Option D working and *proves* the operating model is engine-agnostic — so the Azure (Option A) front-runner decision stays a swap, not a rebuild, and the evaluation argues from evidence.

## 3. Goals / Non-Goals

### Goals

| # | Goal |
|---|---|
| **G1** | Simulate end-to-end monitoring for **exactly two deep use cases**: an LLM use case (**HR Policy Chatbot, RAG** — registry `AICT-P01`) and a classical-ML use case (**Churn / Next-Best-Action** — registry `AICT-P02`), both status production, both risk tier High, both fully synthetic. |
| **G2** | Ship **all 7 dashboard views** (Appendix D) live in a web app — At A Glance, Portfolio Health, Pilot Health Table, Monitoring Lane Heatmap, Risk & Evidence Gaps, Action Queue, Board Narrative Panel — plus per-use-case drill-downs with embedded engine artifacts (Evidently report, NannyML estimate, LIME/SHAP explanations, trace/score views). |
| **G3** | Drive the demo with a **scenario player**: deterministic, versioned scenario scripts **S1–S5** plus the 20-tick **DEMO-FULL** master (Appendix A, normative), advancing in **ticks** (1 tick = 1 simulated working day; the monitoring cycle runs every tick; a WEEKLY_REVIEW event every 7 ticks handles Amber-persistence and review stamps; tick 0 = 2026-07-13), replayable to identical results (fixed seed 42). |
| **G4** | Implement the **Sheet-3-format health logic and the §11 action queue for real, in code** — signal grading to Green/Amber/Red per band (Amber = the gap between the Green bar and the Red bar, plus the trend/staleness rules — Appendix C), worst-of lane and use-case rollup, color→severity map, SLA clocks (**Critical 2 · High 5 · Medium 15 · Low 30 ticks**; 1 tick = 1 simulated working day), and the §11 per-severity SLA-breach ladder (Critical → auto-escalate to RAI Council + CDAO notification; High → auto-escalate one level, owner → business owner → Council; Medium → COE chases, flagged in weekly review; Low → monthly batch review) — running on the simulated tick clock so an SLA breach is demonstrable in minutes (Appendix C). Not mocked pixels. |
| **G5** | Use **real open-source engines** behind exactly three adapter protocols — **`LLMEvalAdapter`** (judge + tracing; `TraceStore` is a sub-interface inside its implementations: `LangfuseStub`, persisting to SQLite, or `LangfuseCloud`, an env-var flip), **`MLMonitorAdapter`** (Evidently 0.4.x `Report` + `DataDriftPreset` drift and NannyML CBPE performance), and **`ExplainAdapter`** (LIME + SHAP) — running the proposal's §13.5 Option D stack (Langfuse, Evidently, NannyML) plus LIME+SHAP explainability (from the verified reference implementation; SHAP is also the Azure Responsible-AI-dashboard path), with the **enterprise-swap seam visible**: each of the three adapters is replaceable by its Azure Option-A counterpart per Appendix G without touching registry, health engine, action queue, or frontend. |
| **G6** | Keep the demo **fully self-contained and deterministic**: synthetic data generated in-repo, no network required for the core path (Langfuse Cloud optional), one-command setup, and **bake mode as the demo default** — the full scenario precomputed dev-time (`POST /api/sim/bake`), tick advance a DB read (**< 1 s**), reset a pointer swap to baked tick 0 (**< 2 s**); live engine compute is a dev-only mode. |

### Non-Goals

| # | Non-Goal |
|---|---|
| **NG1** | **Not production or HA.** No load-bearing deployment, no multi-region, no backup/DR. Demo scale is the seeded registry: 2 deep rows + 13 shallow pilot rows + a deterministic seeded stub portfolio (130 rows total), all synthetic. |
| **NG2** | **No real telemetry, no real True data, no PII — ever.** All telemetry is synthetic and scenario-generated. If Langfuse Cloud is used, only synthetic HR Q&A content may reach it. |
| **NG3** | **No VRO value tracking.** The registry links a `source_record_id` and stops there (§6); no revenue/cost/productivity fields. |
| **NG4** | **No SSO/RBAC.** A single **presenter-mode toggle** is the entire access model: presenter = scenario controls + action edits; viewer = read-only and sees **all 7 views**. There is no board-only role anywhere — View 7 is merely screenshot-ready. Real RBAC returns at pilot (§9). |
| **NG5** | **No portfolio-scale ingestion or real-time streaming.** The scenario player advances discrete ticks (1 simulated working day each); no event streams, no live ingestion — the 130-row seeded portfolio is generated in-repo. |
| **NG6** | **No automated remediation.** Remediation/recovery is a scripted scenario event (Appendix A); the tool recommends and tracks actions, humans (in the story) act — the presenter's "Close with evidence" click at t15 is the trigger for the scripted CLOSE_ACTION event, not an automated fix. |

## 4. Users & User Stories

Three users. The Presenter runs the meeting; Viewers watch and ask; the Builder stands the thing up and evolves it.

| Persona | Who | Mode |
|---|---|---|
| **Presenter** | Ta (RAI COE coordinator) | Presenter mode: scenario controls + action edits, reset, all views |
| **Viewer** | COE team members, CDAO/leadership when reused | Viewer rendering: all 7 views, read-only, no scenario controls |
| **Builder** | The engineer(s) building and extending the demo | Repo, config, APIs, scenario scripts |

**U1 — Presenter: start clean.** As the Presenter, I start the demo in a known-good baseline state with a single click.
*Acceptance:* From a machine with the repo installed and the scenario baked, a single documented command (or one click on a "Reset to baseline" control) restores baked tick 0 (2026-07-13) for the loaded scenario: every lane on the heatmap Green (or the scripted baseline Amber where the scenario says so), zero open Critical/High actions, tick indicator showing t0. Reset is a pointer swap to the baked tick-0 state, idempotent, completing in **under 2 seconds**; it also discards any session-local overlay edits, so running it twice in a row yields byte-identical dashboard state (same seed, same values). No terminal work is needed during the meeting itself.

**U2 — Presenter: drive the story.** As the Presenter, I advance the demo through its scripted ticks from the UI, without typing anything.
*Acceptance:* A scenario-player control (visible only in presenter mode) shows the loaded scenario, the current tick, and Play/Pause/Step/Jump/Speed controls (playback 2.0 s per tick at 1x; multipliers 1x/2x/4x). The demo default is **bake mode**: the full scenario is precomputed dev-time, so advancing a tick is a DB read (**< 1 s**) that updates all views — and because scripts are versioned and the seed fixed (42), the same tick always produces the same signal values, the same colors, and the same actions, in every rehearsal and in the meeting. Interactive mutations during a demo (ad-hoc action edits, what-if threshold edits) live in a session-local overlay discarded on jump/reset, so determinism holds. All scenarios (**S1–S5** and the 20-tick **DEMO-FULL** master) are selectable; tick semantics per Appendix A.

**U3 — Presenter: play the drift, watch the heatmap flip.** As the Presenter, I play the churn drift scenario (**S2**, or the same ticks inside DEMO-FULL) and show the Monitoring Lane Heatmap flip — the demo's signature moment.
*Acceptance:* At t0 the churn row's Drift & degradation and Quality lanes read Green. The scripted covariate + concept drift ramps in the analysis window (per Appendix A: shifted charges, support-call, and contract-mix distributions plus discriminative-signal compression, so the model genuinely loses skill); Evidently's drifted-feature share crosses its Red bar (≥ 0.50, demo-default band, Appendix C) at t9, and the heatmap cell renders Red within one tick refresh — visibly, on the same screen, without a page reload the audience would notice. NannyML's label-free estimated ROC-AUC sags into the Amber guard band [0.72, 0.80) and never crosses Red; the realized ROC-AUC (labels lag 3 ticks) crosses Red (< 0.72) at t13, confirming the estimate. The Presenter can narrate *which* features drifted from the same view or one click deeper.

**U4 — Presenter: show the action fire and the SLA clock.** As the Presenter, I open the Action Queue after the Red tick and show that Red did not just change a color — it created an obligation.
*Acceptance:* In S2, **`ACT-001`** (severity **Critical**, SLA **2 ticks**) fires at t9 on the churn case's `data_drift_share` Red — deduped to one OPEN action per (registry_id, signal key) — carrying issue, recommended action (per the §11 trigger map embedded in Appendix C), owner, due tick (t11), escalation path, and evidence link, all fields from the action-queue schema (Appendix B). The SLA countdown is visible and runs on the tick clock; at t12 the breached action **auto-escalates to RAI Council + CDAO notification** (escalation state and target rendered, event logged) per the §11 ladder. **`ACT-002`** (Critical) fires at t13 on the realized ROC-AUC Red, due t15; S2's final tick shows **exactly two open Critical actions**. Nothing about this flow is hard-coded UI copy: playing S1 (no breach) from reset produces zero actions, and a health-engine unit test fed the same tick with `data_drift_share` inside the Green bar (≤ 0.30) produces no action row.

**U5 — Presenter: drill into the "why".** As the Presenter, I drill into the churn use case and explain the degradation with the engines' own artifacts.
*Acceptance:* The churn drill-down page shows, from artifacts generated by the real engines at bake time (not mocked screenshots): the embedded Evidently drift report (which features drifted, how), the NannyML estimated-vs-realized ROC-AUC comparison ("we knew before labels arrived": the estimate sags into the Amber guard band at serving time; the realized value, with its 3-tick label lag, confirms Red at t13), a **LIME** explanation for the highest-churn-risk synthetic customer with the top contributing features (seeded, deterministic), and a **SHAP** global-importance chart. The UI states the LIME caveat (local, can be unstable; SHAP is the consistent counterpart and the enterprise path). A Viewer who asks "how do you know it's the contract mix?" can be answered from this page in one click.

**U6 — Presenter: the LLM lane is monitored the same way.** As the Presenter, I run the chatbot scenario and show that GenAI quality is governed by the same registry, bands, and queue.
*Acceptance:* At t0 the HR chatbot answers its synthetic Q&A set well (grounded answers on answerable questions, refusals on the three unanswerable ones) and all lanes read Green. Playing **S3** ramps the scripted count-based hallucination injection until the aggregated hallucination rate crosses the High-tier Red bar (≥ 2 % — the one band inherited verbatim from the Deployment Checklist Sheet-3, Appendix C) at t13; the Quality lane flips, **`ACT-003`** (Critical, due t15) fires exactly as in U4, and the drill-down's Traces tab shows per-interaction traces and judge scores (groundedness, relevance, hallucination flag, PII flag, latency) read via the API from the Langfuse stub's SQLite store (or Langfuse Cloud when enabled — same `TraceStore` sub-interface). The judge is a deterministic seeded simulation; no live LLM is called in demo scope. The Presenter can show one hallucinated answer verbatim next to its low groundedness score.

**U7 — Presenter: close the loop.** As the Presenter, I remediate and show recovery — the operating model ends in Green, not in an alert.
*Acceptance:* In DEMO-FULL the scripted remediation lands (retrained-model window for churn; corrected grounding/refusal behavior for the chatbot), subsequent ticks re-grade signals back inside Green bars, and the heatmap recovers. The Presenter's **"Close with evidence"** click at t15 is the trigger for the scripted CLOSE_ACTION event — actions are closed from the UI with a closure note, and each action's status history (opened → escalated if breached → closed) remains visible in the log. The full 20-tick DEMO-FULL run, including talking time, fits the < 10-minute target (§7).

**U8 — Viewer: understand it in one pass.** As a Viewer, after one walkthrough I understand the operating model well enough to critique it.
*Acceptance:* Every view labels the five lanes by name (Quality · Safety & security · Reliability · Drift & degradation · Feedback/action loop) and renders Green/Amber/Red/Unknown with a persistent legend that states the semantics in one line each: Green = within the Green (continue) bar; **Amber = trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap; Sheet-3 itself defines no Amber band**; Red = issue/escalate; Unknown = insufficient evidence, itself a finding. The engine grades gap values Amber mechanically, and the legend says so. The Board Narrative Panel (View 7) reads as a self-explanatory one-screen summary a CDAO could screenshot. Success is measured by the §7 comprehension check, not by feature count.

**U9 — Builder: stand it up and swap an engine.** As the Builder, I can go from clean clone to running demo quickly, and I can see the enterprise seam.
*Acceptance:* Following only the repo README (content per Appendix E): clean clone → one documented setup command → both servers up → bake (`POST /api/sim/bake`) → a full DEMO-FULL run passes, on Python 3.12 and a current Node LTS, with the pinned dependency set (notably `nannyml>=0.13,<0.14` for Python 3.12, `numpy<2` for Evidently 0.4.x/LIME compatibility, `evidently>=0.4.20,<0.5`, `langfuse>=2.53,<3` when the cloud adapter is enabled), in **< 30 minutes** [TBC]. The engine seams are exactly three adapter protocols — **`LLMEvalAdapter`** (judge + tracing; `TraceStore` is a sub-interface inside its implementations: `LangfuseStub`, persisting traces/scores to SQLite, or `LangfuseCloud`), **`MLMonitorAdapter`** (Evidently drift + NannyML performance), and **`ExplainAdapter`** (LIME + SHAP) — each visible as an interface with exactly one demo implementation (Appendix E), and Appendix G names each one's Azure counterpart. Switching the trace store between stub and Langfuse Cloud is a config change, not a code change (env vars: the optional `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` — `.env.example` carries nothing else, and there is no `OPENAI_API_KEY` anywhere). **`ScenarioSource`** is a separate non-engine input interface — the future real-ingestion seam — and is excluded from the Azure-swap claim.

## 5. Requirements

The buildable contract. Each row is one requirement with a one-line, testable acceptance. **P0** = the demo cannot be shown without it (including everything the demo script depends on). **P1** = the demo is materially better with it (target for the team meeting). **P2** = stretch / after the meeting.

**Acceptance test context (applies to every row):** fresh clone of the demo repo · Python 3.12 + Node 20 · **zero API keys / zero network** unless the row says otherwise · default seed **42** · SQLite database created on first boot (ADR: Postgres at pilot stage) · FastAPI backend + Next.js/React frontend (Next.js rewrites proxy `/api/*` to FastAPI; dev ports 3000/8000; everything same-origin from the browser — single API contract: Appendix E §E.3) · **bake mode is the demo default** — the full scenario is precomputed (`POST /api/sim/bake`, dev-time) and advancing a tick is a DB read; live engine compute is a dev-only mode. Performance numbers, stated identically everywhere: **scenario reset < 2 s · tick advance < 1 s (baked) · cold start < 2 min · full demo < 10 min · setup < 30 min [TBC]**.

**Simulated-time conventions used below:** 1 tick = 1 simulated day (every tick a working day) · tick 0 = 2026-07-13 · seed 42. One monitoring cycle runs **every tick**; a **WEEKLY_REVIEW** event fires every 7 ticks (Amber-persistence evaluation + review stamps). SLA clocks run in ticks: **Critical 2 · High 5 · Medium 15 · Low 30.** Scenario references use tick notation against **S1–S5 and the 20-tick DEMO-FULL master** (Appendix A is normative) — "S2 t9" = tick 9 of scenario S2. Scripted beats cited below: **ACT-001** Critical fires S2 t9 (`data_drift_share` Red; due t11; breaches t12 → auto-escalated) · **ACT-002** Critical fires S2 t13 (`realized_roc_auc` Red; due t15) · **ACT-003** Critical fires S3 t13 (hallucination Red; due t15).

### 5.1 Requirements table

| ID | Pri | Requirement | Acceptance (one line, testable) |
|---|---|---|---|
| R-01 | P0 | Registry service (SQLite) implements the assurance-registry schema **field-exactly** (Appendix B): all 25 required fields, the 11 monitoring-lane fields (`quality_metric/threshold/status`, `safety_controls/safety_status`, `reliability_metric/reliability_status`, `degradation_signal/degradation_status`, `feedback_source/feedback_status`), and the 9 action-queue fields. | `GET /api/registry` returns rows carrying every schema field under its exact name, with absent values serialised as the string `Unknown`, never `null` or empty. |
| R-02 | P0 | **Unknown is visible everywhere**: every enum-valued field (`current_health`, `telemetry_status`, `risk_tier`, all lane `*_status`, evidence statuses) renders as an explicit grey `Unknown` chip in every view — never a blank cell, dash-for-missing, or hidden row. | Seeding one registry row with every status set to `Unknown` shows a grey `Unknown` chip for it in Views 1–5 and the drill-down with zero blank cells, and an action seeded with `due_date = Unknown` renders in View 6 with a grey `Unknown` chip in Due plus the "no due date" warning icon per the D.6 empty-state spec. |
| R-03 | P0 | Seed dataset ships in-repo: **2 deep simulated use cases** (`AICT-P01` HR Policy Chatbot / RAG, High risk; `AICT-P02` Churn / Next-Best-Action model, High risk) + **13 shallow pilot rows** (`AICT-P03…AICT-P15`) + a deterministic seeded stub portfolio totalling **130 rows** with exact marginals: production 38 · in-development 36 · requirements/not-started 40 · paused 3 · retired/cancelled 13; 4 high-risk production rows with missing approvals; 12 rows `risk_tier = Unknown`. These counters are a **synthetic echo** of the board-narrative/dashboard-prototype set — one of three un-reconciled portfolio counts (register 131/37 · 6-Jul COE 125/35 · board 130/38), reconciliation due pre-Aug-4 **[TBC]**. | First boot with an empty DB auto-seeds and the views show exactly **the seeded counter set** (130 total · 38 production · 36 in-development · 40 requirements/not-started · 3 paused · 13 retired/cancelled · 4 high-risk-missing-approval · 12 `risk_tier = Unknown`) plus a 15-row pilot set — tests assert the seeded counter set, never the COE count. |
| R-04 | P0 | **Scenario engine**: scenarios are data files (JSON/YAML, in-repo) that mutate synthetic telemetry per tick; ships **S1 Steady state**, **S2 ML drift**, **S3 LLM degradation**, plus S4/S5 (R-29) and the **20-tick DEMO-FULL master** (Appendix A is normative); fully deterministic from `(scenario, seed)`. | Playing S2 to its final tick always yields `degradation_status = Red` on AICT-P02 **and exactly two open Critical actions** (ACT-001, data-drift, fired t9; ACT-002, realized-AUC, fired t13), and two runs with seed 42 produce hash-identical signal series. |
| R-05 | P0 | **Scenario player UI**: bar docked at the bottom of every view with scenario selector (S1–S5 + DEMO-FULL), **load / play / pause / step ±1 / jump / reset**, speed control (1× / 2× / 4×; 1× = 2.0 s per tick), tick counter, and simulated date. | During playback, pause freezes all views mid-scenario, step advances exactly one tick in < 1 s (baked read), and reset returns every view to the baked tick-0 state in **< 2 s** (pointer swap) without a page reload. |
| R-06 | P0 | **Time-lapse tick model**: each tick advances the simulated clock one working day, applies that tick's telemetry, runs **one monitoring cycle for every use case**, re-grades health, and updates SLA clocks; every 7th tick emits a **WEEKLY_REVIEW** event (Amber-persistence evaluation + review stamps). | Advancing one tick updates the simulated date by one day, runs one monitoring cycle, and re-renders affected views via `GET /api/events` (SSE; poll fallback `GET /api/scenario/state`) with no manual refresh, and ticks 7 and 14 emit WEEKLY_REVIEW events. |
| R-07 | P0 | **ML lane synthetic data**: in-repo churn generator (8 features: `tenure_months`, `monthly_charges`, `total_charges`, `num_support_calls`, `contract_type`, `has_fiber`, `is_senior`, `auto_pay`; labelled reference + analysis windows — analysis 500 rows/tick against a 4,000-row reference window) with **parameterised covariate-drift + signal-compression injection** driven by the scenario tick script. | In S2, baseline ticks grade `data_drift_share` Green (≤ 0.30) and tick 9 grades Red (≥ 0.50) on every seeded run. |
| R-08 | P0 | **Evidently (real engine)** computes data drift every tick using the 0.4.x API (`Report` + `DataDriftPreset` [+ `DataQualityPreset`]), extracting `share_of_drifted_columns` and per-feature drift flags, and persists the full HTML report as a per-tick artifact. | The AICT-P02 drill-down "Drift" tab embeds the actual Evidently HTML for the current tick and lists ≥ 3 drifted features at S2 t9. |
| R-09 | P0 | **NannyML CBPE (real engine)** estimates ROC-AUC **label-free** every tick; `realized_roc_auc` is populated from tick 0 via 3 pre-history windows and trails the serving window by `label_lag_ticks: 3`. In S2 the estimated AUC sags into the **Amber guard band [0.72, 0.80)** (~0.762–0.79) and **never crosses Red** — the early warning — while the realized value crosses **< 0.72 (Red) at t13**, confirming the estimate 3 ticks after the serving window. | In S2, `estimated_roc_auc` grades Amber (never Red) once it enters the guard band, and `realized_roc_auc` grades Red (< 0.72) at t13 — exactly 3 ticks after the corresponding serving window — firing ACT-002. |
| R-10 | P0 | **LIME + SHAP (real engines)**: each tick's cycle produces a LIME HTML explanation for the highest-churn-probability instance (top-6 weighted factors) and a SHAP global-importance PNG (TreeExplainer bar plot), seeded for determinism (Appendix A data spec; Appendix E gotchas). | The Explainability tab renders both artifacts for the current tick, with the LIME view naming the explained instance and its churn probability. |
| R-11 | P0 | **LLM lane**: embedded HR-policy RAG bot (6-topic corpus + 10-question eval set, 3 deliberately unanswerable) evaluated by a **deterministic seeded judge simulation** (count-based hallucination injection + seeded score draws) producing per-interaction groundedness / relevance / hallucination / PII / latency, aggregated to 5 signals (`hallucination_rate`, `groundedness`, `relevance`, `pii_exposure_rate`, `p95_latency_s`). **No live-LLM judge ships in demo scope** (moved to Deferred Capabilities; returns at pilot behind `LLMEvalAdapter`); no `OPENAI_API_KEY` appears anywhere in the repo. | With no environment keys, every scenario and every view runs end-to-end with zero outbound network calls, all 5 LLM signals graded every tick, and a repo scan finding no `OPENAI_API_KEY` reference. |
| R-12 | P0 | **Tracing seam**: `TraceStore` is a sub-interface inside `LLMEvalAdapter` implementations — **LangfuseStub** (default; persists traces + scores to **SQLite**) \| **LangfuseCloud** (env-var flip, wired at P2, R-30); the drill-down "Traces" tab reads the SQLite-backed traces via the API. | LLM interactions appear as inspectable traces (input, output, scores, latency) in the drill-down "Traces" tab, read from SQLite via the API using only the stub, and switching LangfuseStub → LangfuseCloud requires env-var changes only. |
| R-13 | P0 | **Sheet-3-format health engine**: grades each signal Green/Red against its band (Appendix C; direction-aware `green_max`/`red_at` or `green_min`/`red_below`), applies the **Amber doctrine** — *Amber = trending toward Red: a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap; Sheet-3 itself defines no Amber band, and the engine grades gap values Amber mechanically* — and rolls up signal → lane → overall by **worst-of** with rank Red > Amber > Unknown > Green. | A unit suite covers all four grades for both directions, the Unknown-beats-Green rollup, the mechanical gap-value Amber, and the two-weekly-review trend rule, and passes in CI. |
| R-14 | P0 | **Action generation (§11)**: every Red and every critical-`Unknown` (High-tier row lacking owner, classification, or telemetry) creates an action row with the schema-exact fields (`action_id`, `registry_id`, `issue`, `recommended_action`, `owner`, `due_date`, `escalation_path`, `status`, `evidence_link`) using the colour→severity map (Red-High→Critical 2 ticks · Red-Med/Low→High 5 · Amber×2→Medium 15 · critical-Unknown-High→High 5); action IDs are sequential **ACT-001 / ACT-002 / …**; dedupe rule: **at most one OPEN action per (registry_id, signal key)**. | Forcing `hallucination_rate` Red on AICT-P01 creates exactly one open Critical action (repeat Reds on the same signal do not duplicate it) with owner, due tick T+2, a signal-specific `recommended_action`, and an `escalation_path`, and increments the row's `open_actions`. |
| R-15 | P0 | **SLA-breach behaviour per proposal §11, per severity — no blanket escalation**: **Critical** → auto-escalate to RAI Council + CDAO notification; **High** → auto-escalate one level (owner → business owner → Council); **Medium** → COE chases, flagged in the weekly review; **Low** → monthly batch review. Every breach event is written to the alert/audit log — nothing silently slips. | In S2, ACT-001 (Critical, due t11) still open at t12 flips to `OVERDUE` and auto-escalates with the banner "Escalated to RAI Council + CDAO" and a tick-stamped log event, while a past-due Medium action is flagged for COE chase at the next WEEKLY_REVIEW instead of escalating. |
| R-16 | P0 | **Views 1 + 3** (At A Glance counters; Pilot Health Table) implemented per Appendix D.1 / D.3, computed live from the registry at the current tick. | Every counter and every pilot row matches a direct `GET /api/registry` query at the same tick, and clicking a pilot row opens its drill-down. |
| R-17 | P0 | **View 4 — Monitoring Lane Heatmap (the signature view)** per Appendix D.4: pilot use cases × the five lanes + Overall, cells bound to the lane `*_status` fields and `current_health`, with animated cell transitions on tick changes. | During S2 the AICT-P02 *Drift/degradation* cell visibly flips Green→Amber→Red (Red at t9) with a transition animation and no page reload, and the Overall cell recomputes worst-of in the same tick. |
| R-18 | P0 | **View 6 — Action Queue** per Appendix D.6: severity-sorted queue with P0–P3 display mapping (Critical→P0 · High→P1 · Medium→P2 · Low→P3), live SLA countdown in ticks, editable `status`, and `evidence_link` per row; **ad-hoc action edits during a demo live in the session-local overlay and are discarded on jump/reset** — the presenter's "Close with evidence" click at t15 is the trigger for the scripted CLOSE_ACTION event. | The queue lists actions Critical-first with a per-row countdown that decrements each tick; marking an action `Closed` decrements `open_actions` on its registry row, a jump/reset discards the ad-hoc edit (overlay), and the scripted t15 close persists. |
| R-19 | P0 | **Use-case drill-down pages** per Appendix D.8: header + owners, signals table (current value vs band vs health + sparkline), artifact tabs (Evidently HTML iframe, LIME HTML, SHAP image, NannyML chart for ML; simulated-judge scores table + SQLite-backed traces + corpus for LLM), and per-case action history. | Both deep use cases drill down with all tabs populated at any tick ≥ 1, and every embedded artifact matches the current tick's cycle output. |
| R-20 | P0 | **Engine adapters behind exactly three protocols** (the swap seam): **`LLMEvalAdapter`** (subsumes judge + tracing; `TraceStore` is a sub-interface inside its implementations), **`MLMonitorAdapter`** (subsumes Evidently drift + NannyML performance), **`ExplainAdapter`** (LIME + SHAP). `ScenarioSource` is a separate **non-engine input interface, excluded from the Azure-swap claim**; Appendix G swaps only the three. | Each of the **three** protocols has a stub implementation passing the same contract-test suite as the real engine — the suite counts exactly three protocols — and no view or health-engine module imports an engine package directly. |
| R-21 | P0 | **Data-hygiene guard + confidential chrome**: all data is generated in-repo (synthetic churn, fictional HR corpus/Q&A); no real True data or PII anywhere; every route shows the masthead badge **"CPG Confidential · Simulated data"** (Appendix D.9), and exports carry the same mark. | A repo scan finds no real personal or True-operational data, and the masthead badge is visible on every route including drill-downs and on every export. |
| R-22 | P0 | **Pinned build environment** (Appendix E): Python 3.12 with `numpy<2.0`, `evidently>=0.4.20,<0.5`, `nannyml>=0.13,<0.14`, `lime>=0.2,<0.3`, `shap>=0.44`, `langfuse>=2.53,<3`; engines that fail to import degrade that lane to `Unknown` with a visible degraded-banner instead of crashing. | Clean `pip install -r requirements.txt` on Python 3.12 imports all engines and completes one full monitoring cycle; deleting one engine package still boots the app with that lane shown `Unknown` + degraded banner. |
| R-23 | P1 | **Views 2 + 5** (Portfolio Health slices; Risk & Evidence Gaps rule table) per Appendix D.2 / D.5, with click-through filtering into the registry/pilot table. | All five slice dimensions and all five gap rules render with live counts, and clicking any segment or gap count opens the matching filtered case list. |
| R-24 | P0 | **View 7 — Board Narrative Panel** per Appendix D.7: read-only board summary pairing the five narrative statements with live proof-stats (registry size, % rows with all three owners named, open actions, on-time closure %); screenshot-ready — there is **no board-only role**. | View 7 renders with all five statements, its proof-stats match the current tick, and it exposes no edit controls. |
| R-25 | P0 | **Escalation badges + alert toasts**: a new Critical/High action or an auto-escalation raises a toast (use case, signal, value, health, severity, SLA, owner, recommended action) anchored above the player bar, and escalated rows carry the escalation badge/banner per §11; the persistent, filterable **alert log** portion is P1. | Playing S2 raises exactly one Critical toast within one tick of the t9 breach, and the t12 auto-escalation renders the escalation badge + "Escalated to RAI Council + CDAO" banner (P1: both events appear in the filterable alert log with tick stamps). |
| R-26 | P1 | **Cadence badge per risk tier** on View 3 rows, heatmap rows, and drill-down headers: High "Weekly review + near-real-time alerts" · Medium "Monthly" · Low "Quarterly" · Unknown "Monthly until classified", plus the next WEEKLY_REVIEW tick — the badge reflects the §10 review cadence; monitoring itself runs every tick. | Every pilot row displays the cadence badge matching its `risk_tier`, and the badge shows the next WEEKLY_REVIEW tick ≤ 7 ticks away. |
| R-27 | P1 | **LIME-vs-SHAP explainability tab** in the ML drill-down showing both artifacts side-by-side with the mandated caveat copy: *"LIME explanations are local and can be unstable (fidelity-vs-simplicity trade-off). SHAP is the more consistent, game-theoretic counterpart — and what the enterprise path (Azure ML Responsible AI dashboard) uses."* | The tab renders LIME and SHAP side-by-side with the caveat text verbatim and visible without scrolling at 1280 px width. |
| R-28 | P1 | **Guided-script overlay** (naming per D.9 — distinct from *presenter mode*, which is the presenter/viewer access toggle only): a toggleable overlay that walks the guided demo script (one talking point per scripted beat, "next" via hotkey), dims non-focus chrome, and highlights the view the script is discussing. | Toggling the guided-script overlay during S2 shows the t9-breach talking point synchronised to the breach tick, and arrow-key advances to the next scripted point. |
| R-29 | P0 | **Scenarios S4 + S5 + DEMO-FULL**: **S4 SLA breach** (S2 continues unremediated → ACT-001's due tick t11 passes → auto-escalation fires at t12, Council + CDAO flagged) and **S5 Remediate & recover** (remediation event → metrics recover → lanes return Green → action closed), each self-contained (includes its own preamble ticks); **DEMO-FULL** is the 20-tick master script for the full demo. | Playing S4 cold shows the OVERDUE flip + escalation toast at t12; playing S5 cold ends with AICT-P02 all-Green, its actions `Closed`, and `open_actions` back to 0; DEMO-FULL plays end-to-end within the < 10 min demo budget at 1× (2.0 s/tick). |
| R-30 | P2 | **LangfuseCloud TraceStore**: with `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` set (the only optional keys in `.env.example`; stub is default), LLM traces + scores push to Langfuse Cloud (SDK v2) each tick via the env-var flip and the Traces tab deep-links to the hosted trace (synthetic Q&A only leaves the machine). | With keys set, one tick's traces are visible in Langfuse Cloud and the drill-down link opens the matching trace; with keys unset, behaviour is identical to R-12. |
| R-31 | — | **R-31 — withdrawn to Deferred (registry CSV import).** ID retained for stability; see Deferred Capabilities. | — |
| R-32 | P2 | **Board export**: one-click export of View 7 to PDF and PNG (headless render) with simulated as-of date and the "CPG Confidential · Simulated data" mark baked in. | The exported file reproduces View 7's current proof-stats and carries the confidentiality mark and simulated date. |
| R-33 | P2 | **What-if threshold editor**: in the drill-down, edit a signal's Green/Red bars, re-grade instantly across heatmap/health/actions, with a "Reset to default bands" control (Appendix C); **edits live in the session-local overlay — never persisted to the registry — and are discarded on jump/reset**. | Tightening the hallucination Red bar below the current value flips the Quality lane Red within one render, and reset (or any jump/reset) restores the Appendix-C defaults with the original grades. |
| R-34 | P1 | **Demo-day fallback**: baked per-tick static snapshots of Views 4, 6, 7 + the NannyML chart, served via `GET /api/export/demo-snapshots`, plus a `scripts/demo_reset` one-shot task that restores the baked demo-ready state. | `GET /api/export/demo-snapshots` returns snapshots of Views 4, 6, 7 and the NannyML chart for every DEMO-FULL tick, and running `scripts/demo_reset` yields a demo-ready state in one command. |

### 5.2 Requirement → view / scenario coverage (orientation)

| Cluster | Rows | Demonstrated by |
|---|---|---|
| Registry & data honesty | R-01–R-03, R-21 | Views 1–5; every view |
| Scenario & time machine | R-04–R-06, R-29 | Player bar (D.9); all views on tick |
| ML lane (real engines) | R-07–R-10, R-22 | Drill-down D.8 (AICT-P02); heatmap D.4 |
| LLM lane (zero-key) | R-11–R-12, R-30 | Drill-down D.8 (AICT-P01) |
| Health & action loop | R-13–R-15, R-25–R-26 | Heatmap D.4; queue D.6; alerts |
| The seven views | R-16–R-19, R-23–R-24, R-32 | Appendix D.1–D.8 |
| Swap seam & explainability honesty | R-20, R-27, R-33 | D.8 tabs; Appendices E & G |
| Demo-day resilience | R-34 | Snapshots + `scripts/demo_reset`; D.7 |

## 6. Ownership Boundaries

| Boundary | Rule |
|---|---|
| **Assurance vs value** | The Control Tower — demo and any successor — is an **assurance overlay**. Business value (revenue, cost saving, productivity) is owned by **VRO / TPM / AI Reporting Tool**; the registry stores a `source_record_id` link and never duplicates value fields. In the demo, the deep-seeded rows carry `source_record_id: Unknown` (synthetic), demonstrating the link discipline without inventing fake VRO records. |
| **Registry source of truth** | The official use-case record lives outside the tool (AI Reporting Tool / VRO / TPM). The registry adds assurance fields only (risk, evidence status, lane health, actions) per the schema in Appendix B — exact field names, `Unknown` never blank. |
| **Demo repository** | Owned by the **RAI COE team** (maintainer: Ta). New repository, separate from any personal or life-os repository; this PRD plus its appendices is the complete build input. |
| **Governance content** | The demo *implements* proposal §10–§13 rules; it does not define governance. Any change to bands, SLAs, cadence, or the severity map is a proposal change first, a code change second. |
| **Engines** | Open-source engines are consumed as pinned dependencies; the COE owns the adapter code, not the engines. The Azure swap (Appendix G) is IT-facing future work, out of demo scope. |
| **Build provenance (BUILT/EXTEND/NEW)** | Greenfield. **BUILT: none — greenfield.** All components are **NEW**. The proven logic from the reference implementation (Sheet-3 bands, generators, lane wiring, health/action rules) is *embedded in this PRD's appendices* and re-implemented in the demo repo — provenance in §12, never a code dependency. |

## 7. Success Metrics

### Leading (measured at/around the demo)

| # | Metric | Target |
|---|---|---|
| L1 | Full scripted demo (the 20-tick DEMO-FULL master, per the Appendix F script) runs end-to-end | **< 10 minutes**, zero dev intervention, zero live coding |
| L2 | Deterministic replay | Two consecutive full runs from reset produce identical signal values, colors, and actions |
| L3 | Viewer comprehension after one walkthrough | A viewer can name the **5 lanes** and explain **Green/Amber/Red** (incl. that Amber = trending toward Red, not a Sheet-3 band) unprompted |
| L4 | Signature moment lands | Heatmap flip (U3) and action-with-SLA (U4) each demonstrated live, from the running app, in the meeting |
| L5 | Builder setup from clean clone to running demo | **< 30 minutes** on a standard laptop [TBC — validate at M3] |
| L6 | Health/action logic is real | Golden test: driving the 20-tick DEMO-FULL master in CI reproduces the **DEMO-FULL per-beat health matrix** and action set (Appendix A) |

### Lagging (weeks after the demo)

| # | Metric | Target |
|---|---|---|
| T1 | Team decision | COE team greenlights the **pilot build** on the demo's skeleton (or records a reasoned redirect) |
| T2 | Tooling evaluation input | The demo is cited as the **Option D evidence** in the §13.7 tooling-evaluation write-up (side-by-side with the Azure sandbox) |
| T3 | Upward reuse | CDAO/board materials (incl. the Aug-4 update pack) reuse demo screenshots or the Board Narrative Panel |
| T4 | Skeleton survives | The pilot build starts from this codebase (registry, health engine, action queue, views retained; the `ScenarioSource` swapped for real §12-contract ingestion) rather than restarting |

## 8. Open Questions

Confidence = how settled the leaning answer is (1 = wide open, 10 = effectively decided).

| # | Question | Leaning | Confidence |
|---|---|---|---|
| Q1 | **Demo hosting** — presenter's localhost vs a shared internal dev URL the team can click after the meeting? | Localhost for demo day (zero infra dependency, NG1); shared URL revisited post-demo | 7 |
| Q2 | **Langfuse Cloud vs in-repo stub on day 1?** | Stub first (deterministic, offline, zero account setup); Cloud adapter behind the same `TraceStore` sub-interface, enabled by env vars for a "and here it is in real Langfuse" flourish | 6 |
| Q3 | **First real model to onboard after the demo** (pilot phase, post-DPO)? | HR chatbot PoV — closest live analogue to `AICT-P01` | 5 |
| Q4 | **Thai-language evaluator quality** — do LLM-as-judge signals hold up on Thai content? [TBC] | Unknown; out of demo scope (synthetic English corpus) but a named §13.7 evaluation item the demo must not overclaim on | 3 |
| Q5 | **Demo date** [TBC] | A COE team meeting before the Aug-4 board update; exact slot unset | 4 |

## 9. Deferred Capabilities

Each deferred deliberately; each returns at the **pilot phase** unless noted.

| Capability | Why deferred | Returns |
|---|---|---|
| Real §12 telemetry feeds (Langfuse/OTel adapters on live use cases) | Requires DPO sign-off per feed; the demo's point is the loop, not the plumbing | Pilot, first feed post-DPO (Q3 candidate) |
| RBAC / SSO (Entra ID) | Access control adds nothing to a meeting-room demo; presenter-mode toggle suffices (NG4) | Pilot, before any non-synthetic data |
| 5-year audit retention + governance-library evidence links | Retention is a legal/records obligation of the real tool, meaningless for synthetic events | Pilot, with the §11 evidence system of record |
| Langfuse self-host (Docker, in-country) | PDPA residency matters only when real prompts/outputs flow; demo data is synthetic | Pilot, as the PDPA-posture config flip |
| **Live-OpenAI LLM judge (real model calls)** | The demo's judge is a deterministic seeded simulation (count-based hallucination injection + seeded score draws); a live model adds nondeterminism and an API key (no `OPENAI_API_KEY` in demo scope) with no narrative gain | Pilot, behind the `LLMEvalAdapter` |
| Real alert channels (email/Slack/webhook) | The demo shows alerts in-app + logged; wiring channels is integration effort with no narrative gain | Pilot, alongside on-call ownership |
| CSV/registry import at portfolio scale (**R-31, withdrawn from the requirements table to here**) | The demo seeds 2 deep rows + 13 shallow pilot rows + a deterministic seeded stub portfolio (130 rows); bulk import is a pilot data-migration task | Pilot onboarding |
| Postgres | SQLite is sufficient and zero-setup at demo scale; **ADR (recorded in Appendix E): SQLite for the demo, Postgres at pilot** — schema written to port cleanly | Pilot |
| Scheduler-driven cadence (real weekly/monthly cycles) | The scenario player *is* the demo's clock (monitoring runs every tick; a WEEKLY_REVIEW event every 7 ticks); wall-clock scheduling only matters with real feeds | Pilot |

## 10. Connection to Strategy

- **Implements proposal §10–§13.** The demo is the running form of the playbook's post-deployment monitoring chapter: §10 lanes/bands/cadence, §11 action queue/SLAs/escalation, §12 telemetry contract (as the future ingestion seam), §13 tooling options. It adds no governance of its own (§6).
- **De-risks direction-ask #2 (tooling evaluation).** The proposal recommends **ecosystem-aligned** tooling with **Azure as front-runner**, decided by a ~1-month hands-on evaluation (§13.7). The demo showcases **Option D as the innovation path** — the open stack running for real — and, because every engine sits behind one of the three adapter protocols, each with a named Azure counterpart (Appendix G), it **proves the operating model is engine-agnostic**: the registry, Sheet-3-format health logic, action queue, and 7 views survive the ecosystem decision unchanged, whichever way it goes. The evaluation then compares engines on evidence, not on which one the tool was welded to.
- **Feeds the Aug-4 board update.** The Board Narrative Panel (View 7) is written to be screenshot-ready for the board pack, and the demo gives the COE a concrete "here is what monitoring will look like" exhibit alongside the wave-1 gap-closure status.
- **Seeds the production-first pilot (proposal §14).** T4 (§7) is the strategic payoff: the pilot monitors live production use cases first, on this skeleton, with the `ScenarioSource` swapped for real feeds.

## 11. Timeline

Milestones, not week estimates. Each milestone exits only on its criterion; **M3's exit is the hard demo-ready gate.**

| Milestone | Scope | Exit criterion |
|---|---|---|
| **M0 — Scaffold** | New repo; Next.js/React + TypeScript app and FastAPI service boot together (Next.js rewrites proxy `/api/*` to FastAPI, same-origin); SQLite schema implementing the Appendix B registry/action/signal model; the seeded portfolio (2 deep rows + 13 shallow pilot rows + a deterministic seeded stub portfolio, 130 rows total) | Both servers start with the documented commands; `GET /api/registry` returns `AICT-P01` and `AICT-P02` with every required field populated (`Unknown` where synthetic), rendered in a stub view |
| **M1 — Engines + scenario core** | Synthetic generators (churn windows with drift injection; HR corpus + Q&A); `MLMonitorAdapter` (Evidently drift, NannyML CBPE) + `ExplainAdapter` (LIME+SHAP) artifacts; `LLMEvalAdapter` (`LangfuseStub` persisting traces/scores to SQLite or `LangfuseCloud`; deterministic seeded judge scores); Sheet-3-format health engine; §11 action queue with per-severity SLA (ticks) + the SLA-breach escalation ladder on the tick clock; scenario player + bake pipeline (`POST /api/sim/bake`) executing versioned scenarios **S1–S5** (S4+S5 are P0, R-29) and the 20-tick **DEMO-FULL** master | **Golden test green in CI**: driving the DEMO-FULL master via the API reproduces the **DEMO-FULL per-beat health matrix** and action set (Appendix A), twice, identically |
| **M2 — Views** | All 7 views (Appendix D) live on real backend data — including the **P0 View 7 (Board Narrative Panel, R-24)** and the **P0 escalation-badge / alert-banner (R-25)**; use-case drill-downs with embedded Evidently/LIME/SHAP artifacts and trace/score tables; scenario-player UI; presenter-mode toggle | All 7 views render from the API with no mocked data; advancing a tick from the UI flips the heatmap, raises the alert banner, and populates the Action Queue in the browser (U3/U4 pass end-to-end) |
| **M3 — Polish + demo script** | Reset control (pointer swap to baked tick 0, **< 2 s**); tick-clock SLA-breach demonstration; legend/lane labeling for U8; baked per-tick static snapshots of Views 4/6/7 + the NannyML chart served via `GET /api/export/demo-snapshots`, plus a `scripts/demo_reset` one-shot as the demo-day fallback (R-34); README per Appendix E; demo script written and rehearsed (Appendix F) | **Demo-ready gate:** from a clean clone on a fresh machine, setup per README (**< 30 minutes** [TBC], cold start **< 2 min**), then the full Appendix F script — the 20-tick DEMO-FULL master, reset included — runs in **< 10 minutes with zero dev intervention**, twice, with identical results (L1/L2), and the U8 comprehension check passes with one non-builder viewer |

## 12. References

| Go-deeper question | Where |
|---|---|
| What happens at each tick of `S1`–`S5` and the 20-tick `DEMO-FULL` master, with expected signal values and health per tick (the normative per-beat health matrix)? How is drift injected, and what are the seed/determinism specs (seed 42; `LimeTabularExplainer` `random_state=seed`; SHAP background `random_state=0`)? | **Appendix A — Simulation & scenarios** |
| What are the exact registry, monitoring-lane, and action-queue field names, allowed values, health-status rules, and the deep-seed + shallow + stub-portfolio rows? | **Appendix B — Registry data model & seeds** |
| What are the Sheet-3 signal bands (per signal, per direction; hallucination inherited verbatim, all others demo defaults), the Amber rules, the color→severity map, the SLA table (ticks), and the escalation/recommended-action mapping? | **Appendix C — Thresholds & SLA** |
| What does each of the 7 views show, with layout, states, legend, drill-down, and presenter-mode behavior? | **Appendix D — The 7 views UX spec** |
| What is the architecture, the single API contract (§E.3, `/api` prefix), the repo layout, the setup commands, the dependency pins, and the SQLite→Postgres ADR? | **Appendix E — Architecture, API & repo** |
| What does the Presenter say and click, minute by minute? | **Appendix F — Demo script** |
| How does each of the three engine adapters swap for its Azure Option-A counterpart, and what stays identical? | **Appendix G — Enterprise swap** |
| *Provenance (not a build dependency):* which source documents does this PRD adhere to? | RAI operating-model proposal §10–§13, `registry-schema.md`, `control-tower-dashboard-prototype.md`, and the verified reference implementation `tools/rai-monitoring-prototype/` (Sheet-3 `SignalSpec` bands, `data_gen.py` drift mechanics, lane/health/action logic) — all in the owner's `life-os` repository, `work-work/projects/responsible-ai-operating-model/` and `tools/`. Their load-bearing content is embedded in Appendices A–G. |

## Appendix A — Simulation & Scenario Specification

### A.0 Purpose & reading guide

This appendix is the soul of the demo. It specifies (1) the discrete-time simulation model and scenario player, (2) the synthetic sample data for both lanes — copy the corpus and Q&A verbatim, (3) the signal bands (§A.2 — the hallucination band inherited verbatim from Sheet-3; the other seven are demo defaults in the same band format), (4) scenario scripts S1–S5 with per-tick trajectory tables and the business story the presenter tells, and (5) determinism/replay/reset rules plus the CI calibration assertions that make the whole thing testable. It is **self-contained**: everything a builder needs to implement the simulation is embedded here; external file paths appear only in the §12 references row (provenance) and are never build dependencies.

**Design rule (binding):** the scenario player scripts *generator parameters* (drift blend, hallucination counts), **not** signal values. The real engines — Evidently (drift), NannyML CBPE (label-free performance), LIME/SHAP (explainability), Langfuse-or-stub (LLM traces/scores) — compute the signals from the generated data, so Evidently and NannyML fire **for real**. The per-tick tables below give *expected* engine outputs with tolerances; §A.7 turns them into CI assertions.

**Every number in this appendix is a demo default**, tunable in one config file (`simulation.yaml`, §A.4). Provenance is scoped precisely: **only the hallucination tier table is inherited verbatim** from the RAI Deployment Checklist v2.0 Sheet-3 (SL#2.1); every other band is a **demo default expressed in the Sheet-3 band format** (proposal §10: thresholds are set per use case at onboarding; reliability defaults are provisional pending the pilot).

### A.1 Simulation model

#### A.1.1 Clock & ticks

| Rule | Spec |
|---|---|
| Tick | 1 tick = **1 simulated day**. Tick 0 date = **2026-07-13** (a Monday) so dates render sensibly. |
| Weekly review | Every **7 ticks** (t7, t14, t21 …) a `WEEKLY_REVIEW` event fires — the High-risk cadence. It evaluates Amber-persistence (Amber across 2 consecutive reviews → Medium action) and stamps `last_reviewed` / `next_review` on the registry rows. |
| Working days | Demo simplification: **every tick is a working day** — SLA "48 h" = 2 ticks, "5 wd" = 5 ticks, "15 wd" = 15 ticks, "30 wd" = 30 ticks. Stated in the UI footnote. |
| Monitoring cycle | One monitoring cycle runs **per tick**: generate window → run engines → grade signals → roll up lanes/health → fire/dedupe actions → SLA-breach check → emit events. This order of operations is normative. |
| Player controls | ▶ Play (2.0 s wall-clock per tick at 1×; speed multipliers 1× / 2× / 4×) · ⏸ Pause · ⏭ Next tick · ⏮ Jump to tick *n* · 🔄 **RESET** (§A.6; < 2 s) · scenario picker (S1–S5, DEMO-FULL) · snapshot loader (§A.5.0). |

#### A.1.2 Bake mode (demo safety — default ON)

At app start (or `POST /api/sim/bake`, dev-only — this and all endpoints named in this appendix are defined in Appendix E §E.3), the backend runs the **entire selected scenario** tick-by-tick through the real engines and persists every tick's signals, grades, artifacts (Evidently HTML, LIME HTML, SHAP PNG), actions, and events to SQLite. The scenario player then only *reveals* precomputed ticks — advancing a tick is a DB read (< 1 s), never a live engine run. Guarantees: no live-compute risk mid-meeting, instant tick advance, instant RESET. A `live` mode (compute on advance) exists for development; the demo **must** run baked. The UI shows a status chip: `BAKED ✓ · seed 42 · DEMO-FULL`.

**Bake-mode interaction rules (normative):** the presenter's **Close with evidence** click at t15 does not mutate baked state ad hoc — the click **is the trigger** for the scripted t15 `CLOSE_ACTION` event (the baked timeline expects it; demo script F.2 step 12 performs it). Any other interactive mutation during a demo — ad-hoc action edits, what-if threshold edits — lives in a **session-local overlay** that is discarded on jump or reset; the baked timeline itself is immutable. RESET restores pure baked tick 0 in < 2 s (typically < 1 s; a state-pointer swap, §A.6).

#### A.1.3 Scenario = script of per-tick parameters + events

A scenario is a declarative script with, per tick: **churn drift blend α** (§A.3.1), **LLM hallucination injection count** (§A.3.2), and an optional **event list** (`RETRAIN_REBASELINE`, `KB_UPDATE`, `CLOSE_ACTION`, `INJECT_OVERDUE_ACTION`). Scenarios are loadable standalone (each declares a starting snapshot) or chained as **DEMO-FULL**, the 20-tick master timeline used by the demo script (Appendix F).

#### A.1.4 Health, rollup & severity (the grading spine)

Mechanical grading per signal (mirrors the proven reference logic — evaluate Red first, then Green, else Amber):

```
lower_is_better:  value >= red_at   -> Red;  value <= green_max -> Green;  else Amber
higher_is_better: value <  red_below-> Red;  value >= green_min -> Green;  else Amber
value missing / signal not computable -> Unknown
```

- **Amber doctrine (one phrasing, legend + engine):** *"Amber = trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap. Sheet-3 itself defines no Amber band."* The engine grades band-gap values Amber mechanically; the UI legend must state this doctrine verbatim.
- **Rollup:** signal → lane → overall use-case health = **worst-of**, ranked `Red(3) > Amber(2) > Unknown(1) > Green(0)`.
- **Reasoned exclusion (one rule, used twice):** a signal in state `Pending`/`Unknown` with a declared reason is rendered grey-striped and **excluded** from lane rollup. The demo uses exactly two: *"post-remediation label lag"* (Pending, §A.5.5) and the AICT-P02 feedback lane's *"no feedback loop instrumented — itself a finding"* (Unknown, hand-set in Appendix B — surfaced in View 5 as an evidence gap, not a health degradation). An *unreasoned* Unknown still degrades the rollup and, on a High-risk case, fires a High action (critical-Unknown rule).
- **Colour → action severity → SLA (verbatim from the operating model, proposal §11):**

| Signal state | Severity | Close within (demo ticks) | On SLA breach |
|---|---|---|---|
| Red on a High-risk case | **Critical** | 48 h (2 ticks) | **Auto-escalate to RAI Council + CDAO notification** |
| Red on Medium / Low | High | 5 wd (5 ticks) | Auto-escalate one level (owner → business owner → Council) |
| Amber persisting 2 consecutive weekly reviews | Medium | 15 wd (15 ticks) | COE chases; flagged in weekly review |
| Critical `Unknown` on a High-risk case | High | 5 wd (5 ticks) | as High |

- **Action lifecycle:** `Open → In progress → Closed`; independent boolean flag `escalated`. Fired actions carry `action_id`, `registry_id`, `issue`, `recommended_action`, `owner`, `due_date` (= fire tick + SLA ticks), `escalation_path`, `status`, `evidence_link` — the exact action-queue field names of the registry schema (Appendix B). Action IDs are sequential: `ACT-001`, `ACT-002`, `ACT-003` … **Dedupe:** at most one *open* action per (`registry_id`, signal key); a re-observed Red attaches to the open action rather than duplicating. A **closed** action re-fires on a new Red observation *unless* suppressed by the post-remediation rule (§A.5.5).
- **SLA breach check (per tick, after grading):** any `Open`/`In progress` action whose `due_date` tick has passed → set `escalated = true`, extend `escalation_path` per the table above, emit `SLA_BREACH_ESCALATION` event (alert-log entry + UI toast + View 6 badge `AUTO-ESCALATED`). The action **stays open** — escalation is added visibility, not closure. Nothing silently slips.
- **Recommended-action text per signal (verbatim demo defaults):**

| Signal | `recommended_action` |
|---|---|
| hallucination_rate | SME review + fix unsupported-answer handling (grounding/refusal). |
| groundedness / relevance | KB / retrieval-quality review with the content owner. |
| pii_exposure_rate | Incident runbook S1 — engage Security + DPO immediately. |
| p95_latency_s | Technical owner — investigate latency / API failures. |
| data_drift_share | Investigate input drift; schedule retraining review (stage-8 re-review). |
| estimated_roc_auc | Model degradation — retrain / regression-test; confirm with labels. |
| realized_roc_auc | Confirmed model degradation — retrain and re-validate before continuing. |

### A.2 Signal bands — High-risk demo configuration

Both demo use cases are **High-risk tier**; these are the High-risk bands. **Provenance (binding):** only the `hallucination_rate` tier table is inherited **verbatim** from the RAI Deployment Checklist v2.0 Sheet-3 (SL#2.1). The other seven bands are **demo defaults expressed in the Sheet-3 band format** — per proposal §10, thresholds are set per use case at onboarding, and the reliability defaults are provisional pending the pilot. Bands are per-use-case-configurable; the config file (§A.4) ships exactly these values.

| Signal | Lane | Direction | Green | Red | Notes |
|---|---|---|---|---|---|
| `hallucination_rate` | Quality | lower better | ≤ 2% (`green_max 0.02`) | ≥ 2% (`red_at 0.02`) | **Inherited verbatim from Sheet-3 (SL#2.1).** Go-live bar < 1%. Green/Red bars touch → **no band-gap Amber**; exactly 2.0% grades **Red** (Red checked first). Tier variants: Medium < 2% go-live / < 3% Green / ≥ 3% Red · Low < 3% / < 5% / ≥ 5%. |
| `groundedness` | Quality | higher better | ≥ 0.85 (`green_min`) | < 0.70 (`red_below`) | Demo default (Sheet-3 format). LLM-judge (or stub) mean score 0–1. |
| `relevance` | Quality | higher better | ≥ 0.85 | < 0.70 | Demo default (Sheet-3 format). LLM-judge (or stub) mean score 0–1. |
| `pii_exposure_rate` | Safety & security | lower better | 0 (`green_max 0.0`) | ≥ 1% (`red_at 0.01`) | Demo default (Sheet-3 format). Any non-zero value is at least Amber; PII stays 0 in every scripted scenario. |
| `p95_latency_s` | Reliability | lower better | ≤ 4 s (`green_max 4.0`) | ≥ 8 s (`red_at 8.0`) | Demo default (Sheet-3 format); reliability defaults provisional pending pilot. |
| `data_drift_share` | Drift & degradation | lower better | ≤ 0.30 (`green_max`) | ≥ 0.50 (`red_at`) | Demo default (Sheet-3 format). Evidently share of drifted features (of 8). |
| `estimated_roc_auc` | Quality | higher better | ≥ 0.80 (`green_min`) | < 0.72 (`red_below`) | Demo default (Sheet-3 format). NannyML CBPE, label-free. |
| `realized_roc_auc` | Quality | higher better | ≥ 0.80 | < 0.72 | Demo default (Sheet-3 format). Once labels arrive (lag = 3 ticks). |

**Lane map:** LLM use case (AICT-P01) → Quality (hallucination, groundedness, relevance) · Safety & security (PII) · Reliability (p95 latency). ML use case (AICT-P02) → Drift & degradation (drift share) · Quality (estimated + realized AUC). The **Feedback/action-loop lane is not tick-simulated**: its status is hand-set in the Appendix B seeds — AICT-P01 **Green** (user thumbs + SME sampling, simulated), AICT-P02 **Unknown** (*"no feedback loop instrumented — itself a finding"* — a declared gap surfaced in View 5, excluded from health rollup per §A.1.4). Any other un-instrumented lane renders `—` (an honest gap, not an error).

### A.3 Sample-data spec

#### A.3.1 Synthetic telco-churn tabular data (ML lane)

**Feature list (exact column names):** `tenure_months`, `monthly_charges`, `total_charges`, `num_support_calls`, `contract_type`, `has_fiber`, `is_senior`, `auto_pay`; target `churn`. Categorical (for Evidently ColumnMapping and LIME): `contract_type` (0 = month-to-month, 1 = one-year, 2 = two-year), `has_fiber`, `is_senior`, `auto_pay`.

**Two row generators** share one labelling formula. Order of operations is **normative** — it is what makes both engines fire for real:

1. Draw `tenure_months` ~ DiscreteUniform[1, 71] *(drifted: [1, 47])*, int.
2. Draw `contract_type` ~ Categorical p = [0.55, 0.25, 0.20] *(drifted: [0.80, 0.12, 0.08] — month-to-month share jumps)*.
3. Draw `monthly_charges` ~ Normal(70, 22) clipped [20, 140] *(drifted: ×1.30, re-clipped [20, 190])*, round 2 dp.
4. Compute `total_charges` = round(`monthly_charges` × `tenure_months` × Uniform(0.8, 1.0), 1). *(Computed from the pre-compression values — so it drifts upward and is NOT compressed in step 7.)*
5. Draw `num_support_calls` ~ Poisson(1.2) *(drifted: Poisson(3.6))*; `has_fiber` ~ Bernoulli(0.45) *(drifted: 0.66)*; `is_senior` ~ Bernoulli(0.16); `auto_pay` ~ Bernoulli(0.55) *(both undrifted)*.
6. **Label** from the *current* (pre-compression) values:
   `z = −2.4 + 0.9·1[contract_type=0] − 0.02·tenure_months + 0.012·(monthly_charges−70) + 0.35·num_support_calls + 0.25·has_fiber + 0.30·is_senior − 0.40·auto_pay`;
   `churn ~ Bernoulli(sigmoid(z))`. Baseline churn prevalence ≈ 0.15 [TBC — measure at seed 42 during M1 calibration].
7. **Drifted only — post-label signal compression** (the CBPE trick): `monthly_charges ← 70 + 0.45·(monthly_charges − 70)`; `num_support_calls ← max(0, round(0.45·num_support_calls))`; `tenure_months ← round(36 + 0.45·(tenure_months − 36))`.

**Why this works (three engines, one trick):** (i) steps 1–5 shift distributions → **Evidently** flags covariate drift feature-by-feature; (ii) labels are drawn from the *pre-compression* signal, then the discriminative features are regressed toward the mean → a model trained on the reference window **genuinely loses skill** on drifted rows, so **realized ROC-AUC really drops**; (iii) the model's predicted-probability spread compresses on drifted rows → **NannyML CBPE estimates the drop label-free**, before any labels arrive. Nothing is faked downstream of the generator.

**Windows & per-tick mechanics:**

| Item | Spec (demo default) |
|---|---|
| Reference window | **4,000 rows**, baseline generator, generated once at bake, rng key `(seed, "churn-ref")`. Model (RandomForest: `n_estimators 200, max_depth 8, min_samples_leaf 20, random_state = seed`) is trained on it. Reference AUC target **0.84 ± 0.02** [TBC — verify at seed 42; if outside tolerance adjust the `z` coefficients, not the bands]. |
| Analysis window (per tick) | **500 rows** at tick *t*: `round(α_t·500)` rows from the drifted generator + the rest from the baseline generator, shuffled; rng key `(seed, "churn", t)`. α is the scenario's per-tick **drift blend** ∈ [0, 1]. |
| Pre-history | 3 baseline windows at t = −3…−1 (generated at bake) so `realized_roc_auc` is populated from tick 0. |
| Label lag | Ground-truth labels for window *t* "arrive" at tick **t + 3** (`label_lag_ticks: 3`). `realized_roc_auc(t)` = AUC over window *t−3*, scored by the model version that served that window. |
| Evidently | 0.4.x API: `Report(metrics=[DataDriftPreset(), DataQualityPreset()])`, `ColumnMapping(numerical, categorical, target=None)`; run reference vs current tick window; read `share_of_drifted_columns` and per-column `drift_detected`; persist HTML per tick. |
| NannyML | `nml.CBPE(problem_type="classification_binary", metrics=["roc_auc"], chunk_size=500)` — one chunk per tick window → one estimate per tick; fit on the reference window (with `y_pred_proba`, `y_pred`, `y_true`). |
| LIME / SHAP | LIME `LimeTabularExplainer` (categorical indices set, `discretize_continuous=True`, **pass `random_state = seed`** for deterministic explanations), explain the **highest-predicted-churn-probability row** of the current window, `num_features=6`, persist HTML. SHAP `TreeExplainer` global bar plot over a 500-row reference sample (**background sample uses `random_state=0`**), persist PNG. Refresh both each tick during bake. |

**Expected drift-share quantization:** with 8 features, `data_drift_share` steps through k/8 = 0.125 · 0.25 · 0.375 · 0.50 · 0.625 · 0.75. Expected feature trip order as α rises (strongest effect first): `num_support_calls` (Poisson 1.2→3.6) → `contract_type` → `monthly_charges` → `total_charges` → `tenure_months` → `has_fiber`. Ceiling = **0.75** (6 of 8 features drift; `is_senior` and `auto_pay` never move — a deliberate credibility detail). Trip ticks are calibration-asserted at seed 42 (§A.7); if an engine-version change moves them, recalibrate the α ramp, never the bands.

#### A.3.2 HR policy corpus + Q&A eval set (LLM lane) — copy verbatim

**Corpus — 6 topics.** This is the entire knowledge base; embed as data, no retrieval infra needed beyond keyword overlap.

| Topic key | Corpus text (verbatim) |
|---|---|
| `annual_leave` | Annual leave: full-time employees accrue 15 working days of paid annual leave per calendar year. Unused leave of up to 5 days may be carried over to the next year and must be used by 31 March, after which it is forfeited. |
| `sick_leave` | Sick leave: employees are entitled to 30 days of paid sick leave per year. A medical certificate is required for any absence of 3 or more consecutive days. |
| `wfh` | Work from home: employees may work from home up to 2 days per week with manager approval. Fully remote arrangements require director-level approval and a signed remote-work agreement. |
| `probation` | Probation: new employees serve a probation period of 119 days. During probation either party may terminate with 7 days' notice. |
| `expense_claim` | Expense claims: submit claims within 30 days of the expense via the HR portal, attaching original receipts. Claims over 5,000 THB require line-manager approval. |
| `parental_leave` | Maternity leave: 98 days of leave, of which 45 days are paid at full salary. Paternity leave is 15 days, paid, to be taken within 90 days of the birth. |

**Q&A eval set — 10 questions, 3 deliberately unanswerable** (the grounding/refusal test). A correct "I don't know" refusal is fully grounded and **not** a hallucination.

| # | Question (verbatim) | Reference answer (verbatim) | Answerable | Topic |
|---|---|---|---|---|
| 1 | How many days of annual leave do I get per year? | 15 working days of paid annual leave per year. | Yes | annual_leave |
| 2 | Can I carry over unused annual leave? | Up to 5 days, and it must be used by 31 March. | Yes | annual_leave |
| 3 | How long is the probation period? | 119 days. | Yes | probation |
| 4 | How many days of paid sick leave am I entitled to? | 30 days per year. | Yes | sick_leave |
| 5 | How many days can I work from home each week? | Up to 2 days per week with manager approval. | Yes | wfh |
| 6 | What is the deadline to submit an expense claim? | Within 30 days of the expense. | Yes | expense_claim |
| 7 | How much paid maternity leave is there? | 98 days total, 45 of them paid at full salary. | Yes | parental_leave |
| 8 | What is the company's stock option / ESOP vesting schedule? | Not covered by the HR policy corpus. | **No** | — |
| 9 | How many days of paid study / education leave do I get? | Not covered by the HR policy corpus. | **No** | — |
| 10 | What is the retirement gratuity formula? | Not covered by the HR policy corpus. | **No** | — |

**Canonical refusal string (verbatim):** `I don't have that in the HR policy documents — please check with HR.`
**Canonical invented-answer string (verbatim, used for injected hallucinations):** `Yes — the policy grants that; see the staff handbook.`

**Interaction simulator (per tick):** 10 questions × 20 reps = **200 evaluated interactions per tick** — deliberately matching Sheet-3's measurement rule (evaluation over ≥ 200 outputs per period). Retrieval = keyword-overlap top-1 over the corpus (no embeddings). Per interaction, rng key `(seed, "llm", t)`:

| Interaction type | Answer | Judge scores drawn (Normal(μ, σ), clipped [0,1]) | hallucination | pii |
|---|---|---|---|---|
| Answerable (questions 1–7; 140/tick) | reference answer | groundedness (0.92, 0.04) · relevance (0.92, 0.04) | false | false |
| Unanswerable, refused | refusal string | groundedness (0.90, 0.05) · relevance (0.85, 0.05) | false | false |
| Unanswerable, **invented** (injected) | invented-answer string | groundedness (0.30, 0.08) · relevance (0.80, 0.06) | **true** | false |
| Latency (all) | — | latency ~ Normal(2.4 s, 0.6 s) clipped [0.6, 12.0] → p95 ≈ 3.4 s | — | — |

**Hallucination injection is count-based, not sampled** (determinism + exact targets): the scenario scripts `n_halluc(t)` — exactly that many of the 60 unanswerable interactions per tick are invented answers (placement chosen by the seeded rng); the rest refuse. Baseline `n_halluc = 2` → `hallucination_rate = 2/200 = 0.010`. Expected aggregates at baseline: groundedness ≈ **0.908**, relevance ≈ **0.90**, p95 latency ≈ **3.4 s**, PII = **0** — all Green. The judge is a **deterministic seeded simulation only** (count-based injection + seeded score draws); there is no live LLM-judge mode in demo scope.

**Langfuse or stub:** each interaction is emitted as a trace (name `hr_chatbot`, input = question, output = answer, metadata topic/latency) with scores `groundedness`, `relevance`, `hallucination` (0/1) — Langfuse SDK **v2** `trace()/score()` API against Langfuse Cloud free tier *if* `LANGFUSE_*` keys are set, else an **in-repo stub implementing the identical interface** (same method signatures; **persists traces and scores to SQLite** — the drill-down Traces tab reads them via the API). The demo (Appendix F) runs on the **stub — offline, no keys, no network**. Only synthetic HR Q&A may ever reach Langfuse Cloud.

#### A.3.3 Registry seed rows

The normative seed rows live in **Appendix B**; the simulation computes the `*_status` and `current_health` fields; hand-set evidence fields come from Appendix B. (`current_health`, `last_reviewed` / `next_review`, and `open_actions` are **computed** by the tick engine — never hand-set; the `WEEKLY_REVIEW` event stamps the review fields.)

#### A.3.4 Engine binding notes (build gotchas — binding)

- **Python 3.12** requires `nannyml>=0.13,<0.14`.
- **Pin `numpy<2.0`** — required for `evidently>=0.4.20,<0.5` and `lime` compatibility. Also pin `scipy<1.13`, `pandas>=2.0,<2.3`, `scikit-learn>=1.3,<1.6`.
- **Evidently 0.4.x API** (not 0.5+): `from evidently.report import Report`, `from evidently.metric_preset import DataDriftPreset, DataQualityPreset`, `from evidently import ColumnMapping`.
- **Langfuse SDK v2** (`langfuse>=2.53,<3`) `trace()/score()` API — or the in-repo stub with the identical interface (§A.3.2). The demo path requires **zero** external keys.
- Every engine call is wrapped: an unavailable/incompatible engine degrades that signal to `Unknown` (surfaced in the UI as a finding) instead of crashing the cycle.

### A.4 Simulation config file (ship verbatim as `simulation.yaml`)

```yaml
# simulation.yaml — every number is a demo default; tune here, never in code.
sim:
  seed: 42                     # determinism root (§A.6)
  tick_days: 1                 # 1 tick = 1 simulated day
  start_date: 2026-07-13       # tick 0 (Monday -> weekly reviews land on Mondays)
  weekly_review_every: 7       # ticks (High-risk cadence)
  label_lag_ticks: 3           # labels for window t arrive at t+3
  bake_on_start: true          # precompute all ticks (demo safety, §A.1.2)
  play_seconds_per_tick: 2.0   # 1x speed; UI multipliers 1x / 2x / 4x

churn:
  reference_rows: 4000
  rows_per_tick: 500
  prehistory_ticks: 3
  nannyml_chunk_size: 500
  model: {kind: random_forest, n_estimators: 200, max_depth: 8, min_samples_leaf: 20}

llm:
  interactions_per_tick: 200   # 10 questions x 20 reps (Sheet-3 ">=200 outputs/period")
  latency: {mean_s: 2.4, sd_s: 0.6, clip_s: [0.6, 12.0]}
  baseline_hallucination_count: 2          # per 200 -> 0.010
  scores:
    answerable: {groundedness: [0.92, 0.04], relevance: [0.92, 0.04]}
    refusal:    {groundedness: [0.90, 0.05], relevance: [0.85, 0.05]}
    invented:   {groundedness: [0.30, 0.08], relevance: [0.80, 0.06]}

# High-risk demo bands (SS A.2). hallucination_rate is inherited verbatim from Sheet-3 SL#2.1;
# the other seven are demo defaults in the Sheet-3 band format (proposal SS10; reliability provisional).
bands:
  hallucination_rate: {direction: lower,  green_max: 0.02, red_at: 0.02}
  groundedness:       {direction: higher, green_min: 0.85, red_below: 0.70}
  relevance:          {direction: higher, green_min: 0.85, red_below: 0.70}
  pii_exposure_rate:  {direction: lower,  green_max: 0.0,  red_at: 0.01}
  p95_latency_s:      {direction: lower,  green_max: 4.0,  red_at: 8.0}
  data_drift_share:   {direction: lower,  green_max: 0.30, red_at: 0.50}
  estimated_roc_auc:  {direction: higher, green_min: 0.80, red_below: 0.72}
  realized_roc_auc:   {direction: higher, green_min: 0.80, red_below: 0.72}

sla_ticks: {Critical: 2, High: 5, Medium: 15, Low: 30}   # 48h / 5wd / 15wd / 30wd

scenarios:
  S1: {name: Healthy baseline, ticks: 5, start_snapshot: null,
       churn_alpha:  [0.05, 0.05, 0.05, 0.05, 0.05],
       llm_halluc:   [2, 2, 2, 2, 2]}
  S2: {name: Gradual churn-model drift, ticks: 10, start_snapshot: SNAP-BASELINE,
       churn_alpha:  [0.10, 0.25, 0.40, 0.55, 0.75, 1.00, 1.00, 1.00, 1.00, 1.00],
       llm_halluc:   [2, 2, 2, 2, 2, 2, 2, 2, 2, 2]}
  S3: {name: Chatbot hallucination spike, ticks: 5, start_snapshot: SNAP-BASELINE,
       churn_alpha:  [0.05, 0.05, 0.05, 0.05, 0.05],
       llm_halluc:   [2, 3, 7, 7, 7]}
  S4: {name: SLA breach + auto-escalation, ticks: 2, start_snapshot: SNAP-OVERDUE,
       churn_alpha:  [1.00, 1.00], llm_halluc: [2, 2]}
  S5:
    name: Remediate & recover
    ticks: 5
    start_snapshot: SNAP-RED
    churn_alpha: [1.00, 1.00, 1.00, 1.00, 1.00]
    llm_halluc:  [2, 2, 2, 2, 2]
    events:
      - {tick: 0, type: CLOSE_ACTION, targets: [ACT-001, ACT-002, ACT-003],
         evidence_link: "evidence://retrain-and-rebaseline-2026-07-28"}
      - {tick: 0, type: RETRAIN_REBASELINE, lane: churn}
      - {tick: 0, type: KB_UPDATE, lane: llm}
  DEMO-FULL:                       # 20-tick master timeline (S1+S2 with S3 overlay; S4 auto; S5)
    name: Full demo run
    ticks: 20
    start_snapshot: null
    churn_alpha: [0.05,0.05,0.05,0.05,0.05,          # t0-t4   S1
                  0.10,0.25,0.40,0.55,0.75,          # t5-t9   S2 ramp
                  1.00,1.00,1.00,1.00,1.00,          # t10-t14 S2 hold
                  1.00,1.00,1.00,1.00,1.00]          # t15-t19 S5 (world stays drifted; baseline moves)
    llm_halluc:  [2,2,2,2,2, 2,2,2,2,2, 2,2,3,7,7,   # t12=3 (trending), t13-14 spike (S3)
                  2,2,2,2,2]                         # t15+ recovered
    events:
      - {tick: 15, type: CLOSE_ACTION, targets: [ACT-001, ACT-002, ACT-003],
         evidence_link: "evidence://retrain-and-rebaseline-2026-07-28"}
      - {tick: 15, type: RETRAIN_REBASELINE, lane: churn}
      - {tick: 15, type: KB_UPDATE, lane: llm}
```

### A.5 Scenario scripts S1–S5

#### A.5.0 Snapshots (instant scene-setting)

| Snapshot | Definition | Used by |
|---|---|---|
| `SNAP-BASELINE` | State at end of S1 (DEMO-FULL tick 4): all Green, no actions. | S2, S3 standalone |
| `SNAP-OVERDUE` | `SNAP-RED` variant with one injected **open Critical action** whose `due_date` = load tick (breach imminent). | S4 standalone |
| `SNAP-RED` | State at DEMO-FULL tick 14: churn Red (drift + realized AUC), chatbot Red (hallucination), ACT-001 escalated, ACT-002/ACT-003 open. | S5 standalone |

Snapshots are materialized during bake; loading one is a DB pointer swap (< 1 s).

*(In the trajectory tables: expected engine outputs carry tolerance ±0.02 for AUC values, exact step-set membership for drift share, exact values for count-based hallucination rate. G/A/R/U = Green/Amber/Red/Unknown.)*

#### A.5.1 S1 — Healthy baseline (5 ticks)

**Business story (what the presenter says):** *"A normal week. The churn model is targeting retention campaigns; the HR chatbot is answering leave-policy questions. Everything is inside its band — this is what 'boring and healthy' looks like, and boring is the goal."*

| Tick | churn α | drift_share | est AUC | realized AUC | halluc rate | ground. | p95 lat | Expected health | Expected UI |
|---|---|---|---|---|---|---|---|---|---|
| 0–4 | 0.05 | 0.000 (G) | 0.840 (G) | 0.840 (G) | 0.010 (G) | 0.908 (G) | 3.4 s (G) | Both use cases **Green**, all monitored lanes Green | Heatmap all Green; action queue empty ("No open actions — nothing Red this cycle"); View 1 counters steady |

Exit state = `SNAP-BASELINE`. (Tolerance: drift_share may tick to 0.125 on one feature at seed variance — still Green; CI asserts ≤ 0.125.)

#### A.5.2 S2 — Gradual churn-model drift (10 ticks; DEMO-FULL t5–t14)

**Business story:** *"Marketing launched an aggressive prepaid promotion. The customer mix feeding the churn model is shifting — more month-to-month contracts, more support calls, higher charges. The model was trained on last quarter's world. Watch the tower catch it in three stages: drift first, estimated performance second, confirmed performance last — before the business feels it."*

Signal mechanics: α ramps 0.10 → 1.00; drift share ramps **0.125 → 0.75**; CBPE-estimated AUC sags **0.84 → 0.79 (Amber early-warning) → ~0.76** — into the Amber guard band [0.72, 0.80), never crossing Red; true window AUC falls faster (compression breaks calibration — CBPE is early but conservative); realized AUC follows with the 3-tick label lag to **0.70 (Red)** — **the NannyML-before-labels story**: the estimate warned at t10; labels confirmed — worse — at t13.

| Tick | α | drift_share | est AUC | realized AUC *(window t−3)* | Churn lanes (Drift / Quality) | Overall | Expected UI change |
|---|---|---|---|---|---|---|---|
| 5 | 0.10 | 0.125 (G) | 0.838 (G) | 0.840 (G) | G / G | **G** | First feature flagged in Evidently detail (support calls) |
| 6 | 0.25 | 0.250 (G) | 0.832 (G) | 0.840 (G) | G / G | G | Drifted-feature list grows (+ contract_type) |
| 7 | 0.40 | 0.250 (G) | 0.828 (G) | 0.840 (G) | G / G | G | `WEEKLY_REVIEW` #1 event; review stamp on registry rows |
| 8 | 0.55 | **0.375 (A)** | 0.818 (G) | 0.840 (G) | **A** / G | **Amber** | Heatmap Drift cell flips Amber; watch-list entry created |
| 9 | 0.75 | **0.500 (R)** | 0.805 (G) | 0.835 (G) | **R** / G | **Red** | **Action ACT-001 fires: Critical, 48 h SLA (due t11), owner RAI COE (demo)** — toast + View 6 row; View 1 Critical counter = 1 |
| 10 | 1.00 | 0.625 (R) | **0.790 (A)** | 0.825 (G) | R / **A** | Red | Quality cell Amber — **estimated** AUC early-warning, labels not yet in |
| 11 | 1.00 | 0.750 (R) | 0.778 (A) | 0.810 (G) | R / A | Red | ACT-001 due tick reached (end of t11) |
| 12 | 1.00 | 0.750 (R) | 0.770 (A) | 0.780 (A) | R / A | Red | **ACT-001 SLA breaches → S4 auto-escalation fires here (§A.5.4)** |
| 13 | 1.00 | 0.750 (R) | 0.765 (A) | **0.700 (R)** | R / **R** | Red | **Labels confirm: realized crosses Red → Action ACT-002 (Critical, due t15)**; est-vs-realized chart shows the 3-tick lead |
| 14 | 1.00 | 0.750 (R) | 0.762 (A) | 0.690 (R) | R / R | Red | `WEEKLY_REVIEW` #2. Standalone S2 ends here with **exactly two open Critical actions** (ACT-001 — escalated — and ACT-002); in DEMO-FULL the chatbot's ACT-003 (§A.5.3) is also open |

#### A.5.3 S3 — Chatbot hallucination spike (5 ticks; overlaid on DEMO-FULL t11–t15)

**Business story:** *"HR just announced a new flexible-benefits policy — but nobody updated the chatbot's knowledge base. Employees are asking; the bot should say 'I don't know', but under pressure of unanswerable questions it starts inventing policy. For an HR bot that's the nightmare scenario — a confident wrong answer about someone's leave entitlement."*

Mechanics: injected invented-answer count steps 2 → 3 → 7 per 200 interactions (`hallucination_rate` 0.010 → 0.015 → **0.035**); groundedness dips 0.908 → **0.893** (visible dip, still Green — the talking point: *the aggregate hides what the rate exposes*).

| Local tick (DEMO-FULL) | n_halluc | halluc rate | ground. | relevance | Chatbot Quality lane | Overall | Expected UI change |
|---|---|---|---|---|---|---|---|
| t0 (11) | 2 | 0.010 (G) | 0.908 (G) | 0.900 (G) | G | **G** | — |
| t1 (12) | 3 | 0.015 (G) | 0.906 (G) | 0.899 (G) | G | G | Sparkline visibly trending up — presenter can point at it |
| t2 (13) | 7 | **0.035 (R)** | 0.893 (G) | 0.897 (G) | **R** | **Red** | Heatmap chatbot Quality flips Red vs the **2% High-risk band**; **Action ACT-003 fires (Critical, 48 h, due t15)**: "SME review + fix unsupported-answer handling (grounding/refusal)"; drill-down shows a sample invented answer next to a correct refusal |
| t3 (14) | 7 | 0.035 (R) | 0.893 (G) | 0.897 (G) | R | Red | ACT-003 open, clock running |
| t4 (15) | 2 | 0.010 (G) | 0.908 (G) | 0.900 (G) | G | G | *(recovery — in DEMO-FULL this is the S5 `KB_UPDATE` tick; ACT-003 closed **within** SLA)* |

Safety lane stays Green throughout (PII = 0); Reliability Green (p95 ≈ 3.4 s).

#### A.5.4 S4 — SLA breach + auto-escalation (event, DEMO-FULL t12; standalone 2 ticks)

**Business story:** *"The Critical action on the churn model was due in 48 hours. Nobody acted — the owner was busy, the email got buried. In the old world this is where it dies in a spreadsheet. In the tower, a passed due date cannot silently slip: it escalates itself."* *(This encodes the real lesson of the unsigned vendor-SoW deadlines.)*

| Trigger | Behaviour (normative) |
|---|---|
| Tick opens with an `Open`/`In progress` action whose `due_date` tick has passed (ACT-001: fired t9, Critical, due t11 → breach detected at t12) | 1. `escalated = true`; action **stays open**. 2. `escalation_path` extended: **→ RAI Council + CDAO notification**. 3. `SLA_BREACH_ESCALATION` event appended to the immutable alert log: `ACT-001 · AICT-P02 (Churn/NBA) · data_drift_share Red · SLA 48h BREACHED at t12 · escalated to RAI Council · CDAO notified`. 4. UI: red **AUTO-ESCALATED** badge on the View 6 row, toast, View 1 "SLA breaches" counter increments, View 7 board narrative picks it up. |

Standalone S4 loads `SNAP-OVERDUE` (breach on the first tick advance) so the moment can be demoed in isolation. Deliberate contrast in DEMO-FULL: **ACT-001 breaches and escalates; ACT-003 is closed within SLA at t15** — the queue shows both behaviours side by side.

#### A.5.5 S5 — Remediate & recover (5 ticks; DEMO-FULL t15–t19)

**Business story:** *"Data Science retrained the churn model on the new customer mix and re-baselined the monitor; HR published the missing policy into the chatbot's knowledge base. The owners close their actions — with evidence links, not verbal assurances. Watch the tower go quiet again, and note that the estimate turns Green three days before the labels can confirm it — the same early-warning asymmetry, on the way up."*

Events at t15: `CLOSE_ACTION` ACT-001 (escalated) + ACT-002 + ACT-003 with `evidence_link: evidence://retrain-and-rebaseline-2026-07-28` (synthetic link — resolves to a demo evidence page) · `RETRAIN_REBASELINE` (churn: model v2 trained on the last 3 label-arrived drifted windows, ~1,500 rows; **reference window reset** to the current distribution — retraining alone does not clear drift, re-baselining does) · `KB_UPDATE` (LLM: the three unanswerable questions' invent-injection returns to baseline; narratively, the missing policy was published). In a live run, the presenter's **Close with evidence** click at t15 **is the trigger** for this scripted event bundle (§A.1.2; F.2 step 12).

**Post-remediation label-lag rule (one rule, used once):** after `RETRAIN_REBASELINE`, realized-AUC observations for windows served by the *old* model are shown grey ("legacy cohort — pre-retrain") and set `Pending` with reason *"post-remediation label lag"* — excluded from grading and from action re-fire for `label_lag_ticks` (3) ticks. First post-retrain realized value lands at t18.

| Tick | drift_share *(vs new ref)* | est AUC *(model v2)* | realized AUC | halluc rate | Overall (churn / chatbot) | Expected UI change |
|---|---|---|---|---|---|---|
| 15 | 0.000 (G) | 0.815 (G) | Pending (grey) | 0.010 (G) | **G / G** | Actions ACT-001/002/003 → Closed with evidence link; heatmap flips Green; queue empties |
| 16 | 0.000 (G) | 0.815 (G) | Pending (grey) | 0.010 (G) | G / G | Est-vs-realized chart shows grey legacy dots + green estimate line |
| 17 | 0.000 (G) | 0.815 (G) | Pending (grey) | 0.010 (G) | G / G | — |
| 18 | 0.000 (G) | 0.815 (G) | **0.815 (G)** | 0.010 (G) | G / G | **Labels confirm recovery** — realized line rejoins in green |
| 19 | 0.000 (G) | 0.815 (G) | 0.815 (G) | 0.010 (G) | G / G | View 7 stats: churn Red t9 → Green t15 (6 ticks); chatbot Red t13 → Green t15 (2 ticks, within SLA); 1 escalation; 3 actions closed with evidence |

Honesty note (also a talking point): recovered AUC ≈ **0.815, not 0.84** — the drifted world genuinely carries less signal; the retrained model recovers to a new, slightly lower — but Green — baseline. CI asserts ≥ 0.805.

#### A.5.6 DEMO-FULL — master timeline recap (20 ticks)

| Ticks | Segment | Headline |
|---|---|---|
| 0–4 | S1 | All Green |
| 5–8 | S2 ramp | Drift 0.125 → 0.375; Amber at t8 |
| 9 | S2 | Drift **Red 0.50** → **ACT-001 Critical (48 h, due t11)** |
| 10 | S2 | Estimated AUC **0.79 Amber** — label-free early warning |
| 12 | S4 | ACT-001 breach → **auto-escalation: RAI Council + CDAO** |
| 13 | S2 + S3 | Realized AUC **0.70 Red** (ACT-002) · chatbot hallucination **3.5 % Red** (ACT-003) |
| 14 | — | Weekly review #2: 2 use cases Red, 3 Critical actions, 1 escalation |
| 15 | S5 | Remediate: close with evidence · retrain + re-baseline · KB update → Green |
| 18 | S5 | Labels confirm recovery (0.815) |
| 19 | — | Steady Green; board wrap |

### A.6 Determinism, replay & reset (demo safety — binding)

1. **Same seed + same scenario + same config = identical run**, bit-for-bit: every random draw uses a keyed generator `rng(seed, stream, tick)` (NumPy `default_rng` with a seed-sequence over `[seed, stream_id, tick]`) — never a shared global RNG, so tick *n* is reproducible in isolation and independent of execution order.
2. Default **seed = 42**. The seed is displayed in the UI status chip and stamped into every baked artifact and exported JSON.
3. **RESET restores baked tick 0 in < 2 s** (typically < 1 s): bake mode (§A.1.2) keeps all tick states in SQLite; RESET (`POST /api/scenario/reset`, Appendix E §E.3) is a state-pointer swap plus cache-served artifacts — no recompute, no engine call — and discards any session-local overlay (§A.1.2). RESET is always available, from any tick, mid-playback.
4. **Replay:** jump-to-tick *n* loads the baked state for *n*; play/pause simply walks the baked sequence. Snapshots (§A.5.0) are named jump targets.
5. **Count-based injection** (hallucinations) and **blend-based generation** (churn α) keep scripted quantities exact while leaving engine outputs genuinely computed.
6. Re-baking with an unchanged (seed, scenario, config, engine-versions) tuple must reproduce the previous bake; the bake writes a manifest (config hash + package versions) so CI can detect engine-version drift that would move calibration targets.

### A.7 Calibration assertions (CI — run on every build, seed 42, DEMO-FULL)

| # | Assertion | Guards |
|---|---|---|
| C1 | Reference-window model AUC ∈ [0.82, 0.86] *(target 0.84 [TBC — first verified in M1 calibration])* | Generator/label formula sanity |
| C2 | `data_drift_share`: t0–t7 ≤ 0.30 (Green); t8 ∈ (0.30, 0.50) (Amber); t9 ≥ 0.50 (Red); t11–t14 = 0.75 | S2 drift ramp + Evidently trip order |
| C3 | `estimated_roc_auc`: t9 ≥ 0.80; t10 ∈ [0.72, 0.80) (Amber); never < 0.72 at any tick; monotonic non-increasing t5–t14 (±0.005 noise) | NannyML early warning stays in the Amber guard band |
| C4 | `realized_roc_auc`: t12 ∈ [0.72, 0.80); **t13 < 0.72 (Red)** | Label-lag confirmation, 3 ticks after C3's Amber |
| C5 | `hallucination_rate`: t0–t12 ≤ 0.015; **t13 = 0.035 exactly**; t15 = 0.010 | Count-based injection is exact |
| C6 | Groundedness t13 ∈ [0.88, 0.91] (dips, stays Green); p95 latency all ticks ≤ 4.0; PII = 0 all ticks | No accidental extra Reds |
| C7 | ACT-001 fires at t9 (Critical, `due` = t11); `SLA_BREACH_ESCALATION` for ACT-001 at t12 with path "RAI Council + CDAO"; ACT-002 fires t13; ACT-003 fires t13 with `due` = t15; standalone S2 final tick has exactly two open Critical actions | Action queue + §11 SLA mechanics |
| C8 | Post-S5: drift t16 ≤ 0.30; est AUC t16 ≥ 0.805; realized t18 ≥ 0.80; zero open actions t15–t19; ACT-003 closed ≤ its due tick | Recovery + within-SLA contrast |
| C9 | Two full bakes at seed 42 produce byte-identical signal JSON; RESET completes < 2 s (typically < 1 s) | Determinism + demo safety |

If an engine-version bump moves C2–C4 outside tolerance: recalibrate `churn_alpha` ramps (and only them) until the assertions pass again. **Never move the signal bands to fit the data** — the hallucination band is Sheet-3-inherited and the rest are declared demo defaults; either way, recalibrate the generator, not the bands.

## Appendix B — Registry Data Model & Seed Data

The registry is an **assurance overlay**, not a value tracker. Source of truth for the use case itself stays outside (AI Reporting Tool / VRO / TPM); the registry links to it via `source_record_id` and owns only risk, evidence, monitoring health, telemetry, and action status. The registry answers: *for each AI use case — what is running, who owns it, what evidence exists, what is monitored, what is degrading, and who must act?*

**Data principles (normative):**

1. Source of truth stays outside this tool — store the external identifier, never re-own value data.
2. Assurance fields live here — risk, evidence, monitoring health, telemetry, action status.
3. Missing information is **visible**: use `Unknown`, never blank.
4. Value (revenue / cost saving / productivity) is linked, not duplicated — VRO remains the owner.
5. Platform-neutral by default: LLM apps, classical ML, vendor tools, and workflow AI use the same minimum schema.

### B.1 Required registry fields

| Field | Required | Definition | Allowed values / example |
|---|---|---|---|
| `registry_id` | Yes | Stable control-tower ID | `AICT-P01` |
| `source_record_id` | Yes if known | AI Reporting Tool / VRO / TPM ID | `TPM-...`, `VRO-...`, `Unknown` |
| `use_case_name` | Yes | Plain-language use-case name | `HR Policy Chatbot (RAG)` |
| `use_case_group` | Yes | Portfolio grouping | `Mity PoV`, `Network AI`, `AI Council`, `Finance`, `Demo` |
| `business_unit` | Yes or `Unknown` | BU or domain sponsor | `HR`, `Call Center`, `Network`, `Finance`, `CVM` |
| `business_owner` | Yes or `Unknown` | Accountable for workflow fit and acceptance | Named person/team (demo: role names) |
| `technical_owner` | Yes or `Unknown` | Accountable for implementation and support | Named person/team |
| `monitoring_owner` | Yes or `Unknown` | Accountable for ongoing monitoring and action follow-up | Named person/team |
| `system_owner` | Yes for platform/system rows | Owner of the application/system boundary | `HR Portal System Owner`, `Unknown` |
| `platform_or_app` | Yes | Where the AI is embedded | `True Connect`, `Mity`, `Microsoft`, vendor app |
| `model_provider` | Yes or `Unknown` | Model, vendor, or provider path | `Mity`, `Microsoft`, `Internal`, `Vendor`, `Unknown` |
| `model_or_route` | If available | Model name, route, agent, or gateway decision | `GPT via Mity`, `Internal + Microsoft`, `Unknown` |
| `workflow_location` | Yes or `Unknown` | Where users encounter it | `HR portal chat`, `call center workflow`, `network ops` |
| `data_sources` | Yes or `Unknown` | Major source systems or knowledge bases | `SharePoint`, `SAP SuccessFactors`, `network tickets` |
| `status` | Yes | Lifecycle status | `requirements` · `PoV` · `UAT` · `production` · `paused` · `retired` |
| `risk_tier` | Yes or `Unknown` | AI Council risk classification | `High` · `Medium` · `Low` · `Unknown` |
| `privacy_status` | Yes | DPO/privacy evidence status | `Not required` · `Required` · `In review` · `Approved` · `Unknown` |
| `security_status` | Yes | Security assessment status | `Not started` · `In review` · `Approved` · `Exception` · `Unknown` |
| `rai_status` | Yes | RAI / AI Council evidence status | `Complete` · `Partial` · `Missing` · `Unknown` |
| `ai_readiness_status` | Yes | Readiness checklist status | `Complete` · `Partial` · `Missing` · `Unknown` |
| `telemetry_status` | Yes | Whether monitoring signals are available | `Live` · `Manual` · `Partial` · `Missing` · `Unknown` |
| `current_health` | Yes | Current assurance health | `Green` · `Amber` · `Red` · `Unknown` |
| `last_reviewed` | Yes or `Unknown` | Date of latest assurance review | `2026-07-13` |
| `next_review` | Yes or `Unknown` | Next required assurance review | `2026-07-20` |
| `open_actions` | Yes | Count or linked action list | `3`, `None`, link to action queue |

### B.2 Monitoring-lane fields

One set per registry row; these score whether each of the five monitoring lanes has evidence.

| Lane | Field | Expected content |
|---|---|---|
| Quality | `quality_metric` | Accuracy, task success, citation correctness, SME pass/fail, recommendation precision |
| Quality | `quality_threshold` | Pass threshold or review rule (Sheet-3 band format, Appendix C) |
| Quality | `quality_status` | `Green` · `Amber` · `Red` · `Unknown` |
| Safety/security | `safety_controls` | PII, prompt-injection, unauthorized-access, unsafe-action controls |
| Safety/security | `safety_status` | `Green` · `Amber` · `Red` · `Unknown` |
| Reliability | `reliability_metric` | Latency, uptime, fallback rate, timeout rate, incident count |
| Reliability | `reliability_status` | `Green` · `Amber` · `Red` · `Unknown` |
| Drift/degradation | `degradation_signal` | Quality trend, stale knowledge, changed data pattern, model/prompt regression |
| Drift/degradation | `degradation_status` | `Green` · `Amber` · `Red` · `Unknown` |
| Feedback/action loop | `feedback_source` | User feedback, SME correction, support tickets, incident review |
| Feedback/action loop | `feedback_status` | `Green` · `Amber` · `Red` · `Unknown` |

### B.3 Action-queue fields

Every Red and critical-`Unknown` produces an action row; Amber is watch-listed and converts on persistence (rules in Appendix C).

| Field | Definition |
|---|---|
| `action_id` | Stable action ID (demo format: `ACT-001`, `ACT-002`, `ACT-003`, …) |
| `registry_id` | Linked use case |
| `issue` | What is wrong or missing |
| `recommended_action` | What should happen next |
| `owner` | Person/team accountable |
| `due_date` | Target date (opened-at + SLA) or `Unknown` |
| `escalation_path` | `Security` · `DPO` · `AI Council` · `CDAO` · `business owner` · `technical owner` |
| `status` | `Open` · `In progress` · `Blocked` · `Closed` |
| `evidence_link` | Link to document, checklist, risk register, or meeting note |

**Dedupe rule (normative):** at most one **Open** action per `(registry_id, signal key)` — a persisting or repeating breach updates the existing action rather than spawning a duplicate.

Demo extensions (additive, do not rename the fields above): `severity` (`Critical`/`High`/`Medium`/`Low`), `sla` (display string), `opened_at_tick`, `escalated` (bool — set on SLA breach per the per-severity rules in Appendix C.4).

### B.4 Health-status rules

| Status | Meaning |
|---|---|
| **Green** | Evidence exists, monitoring is defined, no active breach or material missing owner. |
| **Amber** | Trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap. Sheet-3 itself defines no Amber band (Appendix C.1–C.3). |
| **Red** | Material risk, missing required control, missing owner for a high-risk case, production issue, or security/privacy gap — or a signal at/past its Red bar. |
| **Unknown** | Use case exists but evidence is insufficient to assess. `Unknown` is a visible state and, on a High-risk case lacking owner, classification, or telemetry, itself generates an action (Appendix C.3). |

Rollup (normative, mirrors the health engine): signal health → lane health → overall use-case health is **worst-of**, with severity order `Red > Amber > Unknown > Green`.

### B.5 Risk-based cadence

| Risk tier | Minimum cadence | Required review body |
|---|---|---|
| High | Weekly, near-real-time alerts for critical signals where telemetry allows | Use-case owner + COE; Security/DPO/AI Council where relevant |
| Medium | Monthly with sampled quality checks | Use-case owner + COE review |
| Low | Quarterly (minimum six-month confirmation) | Owner attestation + COE spot check |
| Unknown | Reviewed monthly until classified | COE chases the risk-classification owner |

**Demo-clock convention (normative):** 1 tick = **1 simulated day** (every tick a working day); **tick 0 = 2026-07-13**. The monitoring cycle runs **every tick** regardless of tier — there are no cadence-gated cycles. A `WEEKLY_REVIEW` event fires every 7 ticks and handles Amber-persistence conversion (Appendix C.3) and the `last_reviewed` / `next_review` stamps. Action due dates are expressed in SLA ticks per Appendix C.4 (Critical 2 · High 5 · Medium 15 · Low 30). The cadence table above states the operating-model review expectation per tier; within the 20-tick demo window the High-tier weekly cadence is what the `WEEKLY_REVIEW` event enacts. Dates are computed from the tick counter against the fixed demo epoch, so the demo is deterministic and date-stable.

### B.6 Minimum row-completion criteria

A registry row counts as "monitored" when it has: (1) a linked source-of-truth record or explicit `Unknown`; (2) named business, technical, and monitoring owners or explicit `Unknown`; (3) a risk tier or explicit `Unknown`; (4) privacy/security/readiness evidence status; (5) at least one monitoring metric per relevant lane, or a stated reason the lane is not applicable; (6) a current health status; (7) an open action for every Amber/Red/Unknown critical gap. Both deep seed rows below satisfy all seven (AICT-P02's feedback lane is an explicit `Unknown` with a stated reason — visible, never blank).

### B.7 Seeded deep registry rows (the single normative deep-row table)

The deep seed rows ship in `backend/seeds/registry_seed.json` together with the 13 shallow pilot rows of B.8; the stub portfolio is generated (B.8). All owners are **roles, not real names**; all statuses are simulated. Values shown are the **baseline (tick 0 = 2026-07-13)** state; the scenario player mutates `current_health`, lane statuses, `open_actions`, and review dates as the script runs. **This section is the single normative deep-row table** — every other section (core PRD, Appendices A/D/F) cites these rows and duplicates none of them.

#### Row 1 — AICT-P01 · HR Policy Chatbot (RAG) — LLM lane

| Field | Value |
|---|---|
| `registry_id` | `AICT-P01` |
| `source_record_id` | `Unknown` *(synthetic demo — no AI Reporting Tool / VRO / TPM record)* |
| `use_case_name` | `HR Policy Chatbot (RAG)` |
| `use_case_group` | `Demo — Employee GenAI` |
| `business_unit` | `HR` |
| `business_owner` | `HR Operations Lead (role)` |
| `technical_owner` | `Intelligence-Layer Platform Team (role)` |
| `monitoring_owner` | `RAI COE Coordinator (role)` |
| `system_owner` | `HR Portal System Owner (role)` |
| `platform_or_app` | `True Connect chat (simulated)` |
| `model_provider` | `Vendor LLM via internal gateway (simulated)` |
| `model_or_route` | `GPT-family via platform gateway (simulated)` |
| `workflow_location` | `True Connect chat widget` |
| `data_sources` | `Synthetic HR policy corpus (6 topics: annual leave, sick leave, WFH, probation, expense claims, parental leave)` |
| `status` | `production` *(simulated)* |
| `risk_tier` | `High` |
| `privacy_status` | `Approved` *(simulated — synthetic data only)* |
| `security_status` | `Approved` *(simulated)* |
| `rai_status` | `Complete` *(simulated)* |
| `ai_readiness_status` | `Complete` *(simulated)* |
| `telemetry_status` | `Live` *(simulated traces + eval scores, 200 interactions/tick)* |
| `current_health` | `Green` *(baseline)* |
| `last_reviewed` | `2026-07-13` *(demo epoch, tick 0)* |
| `next_review` | `2026-07-20` *(tick 7 — `WEEKLY_REVIEW`)* |
| `open_actions` | `0` *(baseline)* |
| `quality_metric` | `hallucination_rate · groundedness · relevance (LLM-as-judge over sampled interactions — deterministic seeded simulation, Appendix A)` |
| `quality_threshold` | `hallucination <2% Green / ≥2% Red; groundedness ≥0.85 Green / <0.70 Red; relevance ≥0.85 Green / <0.70 Red` (Appendix C.2) |
| `quality_status` | `Green` |
| `safety_controls` | `PII-exposure detection on outputs; grounded-refusal policy for unanswerable questions` |
| `safety_status` | `Green` |
| `reliability_metric` | `p95 latency (s): ≤4.0 Green / ≥8.0 Red` |
| `reliability_status` | `Green` |
| `degradation_signal` | `Rolling hallucination/groundedness trend across weekly reviews; stale-KB flag` |
| `degradation_status` | `Green` |
| `feedback_source` | `User thumbs + SME sampling (simulated)` |
| `feedback_status` | `Green` |

#### Row 2 — AICT-P02 · Churn / Next-Best-Action Model — classical-ML lane

| Field | Value |
|---|---|
| `registry_id` | `AICT-P02` |
| `source_record_id` | `Unknown` *(synthetic demo — no AI Reporting Tool / VRO / TPM record)* |
| `use_case_name` | `Churn / Next-Best-Action Model` |
| `use_case_group` | `Demo — CVM Classical ML` |
| `business_unit` | `CVM / Marketing` |
| `business_owner` | `CVM Campaign Lead (role)` |
| `technical_owner` | `Data Science Team (role)` |
| `monitoring_owner` | `RAI COE Coordinator (role)` |
| `system_owner` | `Campaign Decisioning System Owner (role)` |
| `platform_or_app` | `Campaign decisioning engine (simulated)` |
| `model_provider` | `Internal` |
| `model_or_route` | `scikit-learn RandomForestClassifier, batch scoring` |
| `workflow_location` | `Outbound campaign targeting workflow` |
| `data_sources` | `Synthetic telco billing + usage features (8 features: tenure, monthly/total charges, support calls, contract type, fiber, senior, auto-pay)` |
| `status` | `production` *(simulated)* |
| `risk_tier` | `High` |
| `privacy_status` | `Approved` *(simulated — no PII features, synthetic data)* |
| `security_status` | `Approved` *(simulated)* |
| `rai_status` | `Complete` *(simulated)* |
| `ai_readiness_status` | `Complete` *(simulated)* |
| `telemetry_status` | `Live` *(simulated batch scoring: 4,000-row reference window, 500-row analysis window per tick — NannyML `chunk_size` 500)* |
| `current_health` | `Green` *(baseline — the uninstrumented feedback lane is a reasoned exclusion, surfaced in View 5, not a health degradation; Appendix A §A.1.4)* |
| `last_reviewed` | `2026-07-13` *(demo epoch, tick 0)* |
| `next_review` | `2026-07-20` *(tick 7 — `WEEKLY_REVIEW`)* |
| `open_actions` | `0` *(baseline)* |
| `quality_metric` | `estimated_roc_auc (NannyML CBPE, label-free) · realized_roc_auc (labels arrive with label_lag_ticks = 3; realized series populated from tick 0 via 3 pre-history windows — Appendix A)` |
| `quality_threshold` | `ROC-AUC ≥0.80 Green / <0.72 Red` (Appendix C.2) |
| `quality_status` | `Green` |
| `safety_controls` | `No PII features in model inputs; least-privilege access to scoring outputs (simulated)` |
| `safety_status` | `Green` |
| `reliability_metric` | `Batch scoring job completion + data freshness (simulated)` |
| `reliability_status` | `Green` |
| `degradation_signal` | `data_drift_share (share of drifted features, Evidently DataDriftPreset)` |
| `degradation_status` | `Green` |
| `feedback_source` | `Unknown` *(no feedback loop instrumented — itself a finding)* |
| `feedback_status` | `Unknown` |

> **Note (AICT-P02 baseline):** the uninstrumented feedback lane is a **reasoned exclusion** (Appendix A §A.1.4): a declared-reason `Unknown` is rendered grey-striped and **excluded from the health rollup**, so it does **not** degrade the row. Baseline overall health is therefore **Green** — all tick-simulated lanes are Green, and Appendix A's S1 shows both demo use cases Green at tick 0. The missing loop is made **visible** as an evidence gap in View 5, not hidden. It is **not** a critical `Unknown` under Appendix C.3 (owner / classification / telemetry), so it opens no action at baseline. Outcome labels for `realized_roc_auc` do arrive through the data pipeline (`label_lag_ticks = 3`, Appendix A) — label arrival is a pipeline fact, not a user/business feedback loop.

### B.8 Shallow pilot rows + stub portfolio seed spec

Beyond the two deep rows, the seed registry carries **13 shallow pilot rows** (`AICT-P03`…`AICT-P15`) — plausible synthetic echoes of the dashboard-prototype's pilot examples — plus a **deterministic stub portfolio** (`AICT-P16`…`AICT-P130`) that brings the registry to exactly **130 rows**. Shallow rows populate only the summary fields shown below; all unlisted evidence and lane fields default to `Unknown`. Stub rows are summary-only.

| `registry_id` | `use_case_name` | `use_case_group` | `status` | `risk_tier` | Evidence-status note (one line) | `current_health` |
|---|---|---|---|---|---|---|
| `AICT-P03` | True Connect × Mity Platform Assessment | Mity PoV | `PoV` | `Unknown` | Platform assessment underway; risk classification pending AI Council | `Unknown` |
| `AICT-P04` | Call Center Knowledge Assistant (KB RAG) | Call Center | `UAT` | `High` | Security Approved; RAI evidence Partial — hallucination eval pending | `Amber` |
| `AICT-P05` | A2BI Hallucination Monitor | AI Council | `PoV` | `Medium` | Monitoring-tooling pilot; telemetry Live on test traffic | `Green` |
| `AICT-P06` | Agents-AI Unintended-Action Controls | AI Council | `requirements` | `High` | Control design stage; all evidence statuses Unknown | `Unknown` |
| `AICT-P07` | NBA/NBO Recommendation Engine | CVM | `production` | `High` | RAI status Missing in production — flagged (one of the 4 high-risk production approval gaps) | `Red` |
| `AICT-P08` | Network Fault-Prediction AI | Network AI | `production` | `Medium` | Telemetry Manual; monthly sampled quality checks | `Green` |
| `AICT-P09` | Finance Revenue Forecasting | Finance | `production` | `Medium` | Readiness Complete; drift lane not instrumented | `Amber` |
| `AICT-P10` | B2B Lead Scoring | Enterprise | `UAT` | `Low` | Privacy In review; readiness Partial | `Amber` |
| `AICT-P11` | TrueID TV Recommender | Consumer | `production` | `Low` | Owner attestation current; quarterly cadence | `Green` |
| `AICT-P12` | CX Sentiment Analytics | CX | `production` | `Medium` | Feedback lane Green; quality sampling manual | `Green` |
| `AICT-P13` | HR CV-Screening Assistant | HR | `paused` | `High` | Paused pending DPO review — privacy In review | `Amber` |
| `AICT-P14` | Retail Store-Traffic Forecasting | Retail | `retired` | `Low` | Retired Q2-2026; row retained for audit trail | `Unknown` |
| `AICT-P15` | Payments Fraud-Detection Scoring | Finance | `production` | `High` | Privacy Approved; security assessment status Unknown — flagged (one of the 4 high-risk production approval gaps) | `Red` |

**Portfolio marginals (normative — CI asserts exactly these):** across all 130 rows, `status` counts are **production 38 · in-development 36 · requirements/not-started 40 · paused 3 · retired/cancelled 13** (= 130), where in-development = `PoV` + `UAT`, requirements/not-started = `requirements`, retired/cancelled = `retired`. Cross-cutting: exactly **4** high-risk `production` rows carry a missing approval (privacy / security / RAI) and exactly **12** rows have `risk_tier = Unknown`.

Named-row contributions (P01–P15): production 8 (P01, P02, P07, P08, P09, P11, P12, P15) · in-development 4 (P03, P05 PoV; P04, P10 UAT) · requirements 1 (P06) · paused 1 (P13) · retired 1 (P14) · high-risk production approval gaps 2 (P07, P15) · `risk_tier = Unknown` 1 (P03).

**Stub generation rule (deterministic):** `backend/seeds/gen_stub_portfolio.py`, seeded with `DEMO_SEED` (default **42**), emits rows `AICT-P16`…`AICT-P130` in ID order and fills the exact remainders: production **30** · in-development **32** · requirements **39** · paused **2** · retired **12** (= 115 stub rows); among its high-risk production rows exactly **2** carry a missing approval, and exactly **11** stub rows get `risk_tier = Unknown`. Statuses, tiers, and approval gaps are assigned from fixed quota schedules (the seed only shuffles names and group assignment — never the asserted counters), so the same seed always yields the same registry. A CI test (`backend/tests/test_seed_marginals.py`) asserts **the seeded counter set** above.

**Provenance of the counters (synthetic echo):** these totals are a synthetic echo of the board-narrative / dashboard-prototype portfolio set. They are **one of three un-reconciled portfolio counts** in circulation (register 131/37 · 6-Jul COE 125/35 · board 130/38); reconciliation is due pre-Aug-4 [TBC]. Acceptance tests therefore assert "the seeded counter set", never "the COE count".

## Appendix C — Thresholds, Severity & SLA

This appendix is the static thresholds-and-SLA reference the health engine implements; the engine, scenario spine, and calibration assertions that consume these values are normative in **Appendix A**.

**Provenance is scoped precisely (proposal §10).** Only the **hallucination-rate tier table (C.1)** is inherited **verbatim** from the RAI Deployment Checklist **Sheet-3 "Performance & Risk Criteria"** (SL#2.1). **Every other band in this appendix is a demo default** — expressed in the Sheet-3 band format (Go-Live Threshold · Continue in Production · Issue/Escalate) but *set for this demo*, not inherited: thresholds are tuned per use case at onboarding, and the reliability/quality defaults are provisional pending the pilot. Any "inherited, not invented" claim in this PRD (including the demo-script Q&A answer) is scoped to hallucination only.

### C.1 Worked example — hallucination rate (Sheet-3 SL#2.1), by risk tier

Inherited **verbatim** from Sheet-3 SL#2.1:

| Signal | Go-live bar (launch gate) | **Green** — continue in production | **Red** — issue / escalate |
|---|---|---|---|
| Hallucination rate — **High**-risk case | < 1% | < 2% | ≥ 2% |
| Hallucination rate — **Medium** | < 2% | < 3% | ≥ 3% |
| Hallucination rate — **Low** | < 3% | < 5% | ≥ 5% |

**Amber doctrine (one phrasing, legend + engine):** *Amber = trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap. **Sheet-3 itself defines no Amber band.*** The engine grades band-gap values Amber mechanically; the UI legend states this doctrine verbatim. This keeps Sheet-3's "Continue in Production" band Green — e.g. a High-risk case at 1.5% hallucination operates normally — instead of flooding the action queue.

Measurement per Sheet-3: human/LLM-judge evaluation over **≥ 200 outputs per period**. The demo honors this — the LLM lane simulates 10 Q&A items × 20 repetitions = **200 interactions per tick** (Appendix A §A.3.2).

### C.2 Demo SignalSpec table (the exact bands the health engine ships with)

Both demo rows are High-tier, so the bands below are the High-risk configuration. `direction` says which way is good. For `lower_is_better`: Green while value ≤ Green bar, Red once value ≥ Red bar. For `higher_is_better`: Green while value ≥ Green bar, Red once value < Red bar. Values between the bars grade **Amber** (numeric guard band). A missing value grades **Unknown**. **Provenance:** only `hallucination_rate`'s High band (Green < 2%, Red ≥ 2%) is the inherited Sheet-3 value (C.1); every other row is a demo default in the Sheet-3 band format (intro).

| Signal key | Label | Lane | Direction | Green bar | Red bar | Unit | Provenance |
|---|---|---|---|---|---|---|---|
| `hallucination_rate` | Hallucination rate | Quality | lower_is_better | ≤ 0.02 | ≥ 0.02 | fraction (% displayed) | **Sheet-3 (inherited)** |
| `groundedness` | Groundedness | Quality | higher_is_better | ≥ 0.85 | < 0.70 | score 0–1 | demo default |
| `relevance` | Answer relevance | Quality | higher_is_better | ≥ 0.85 | < 0.70 | score 0–1 | demo default |
| `pii_exposure_rate` | PII exposure rate | Safety & security | lower_is_better | ≤ 0.00 | ≥ 0.01 | fraction (% displayed) | demo default |
| `p95_latency_s` | p95 latency | Reliability | lower_is_better | ≤ 4.0 | ≥ 8.0 | seconds | demo default |
| `data_drift_share` | Share of drifted features | Drift & degradation | lower_is_better | ≤ 0.30 | ≥ 0.50 | fraction of features | demo default |
| `estimated_roc_auc` | Estimated ROC-AUC (NannyML, label-free) | Quality | higher_is_better | ≥ 0.80 | < 0.72 | AUC | demo default |
| `realized_roc_auc` | Realized ROC-AUC (once labels arrive) | Quality | higher_is_better | ≥ 0.80 | < 0.72 | AUC | demo default |

Notes: (1) `hallucination_rate` has coincident bars (Green ≤ 0.02, Red ≥ 0.02) — the Red check runs **first**, so exactly 2% grades Red and there is no numeric Amber gap for this signal, matching the Sheet-3 High band (Green < 2%, Red ≥ 2%). (2) `pii_exposure_rate` is Green only at exactly 0; any exposure between 0 and 1% is Amber, ≥ 1% is Red.

**Grading rule (normative pseudocode, mirrors Appendix A §A.1.4):**

```
evaluate(signal, value):
    if value is missing            -> Unknown
    if direction == lower_is_better:
        if value >= red_bar        -> Red        # Red checked first
        if value <= green_bar      -> Green
        else                       -> Amber      # numeric guard band
    if direction == higher_is_better:
        if value <  red_bar        -> Red
        if value >= green_bar      -> Green
        else                       -> Amber
rollup: lane = worst(signals in lane); overall = worst(lanes)
worst order: Red > Amber > Unknown > Green
```

A declared-reason `Unknown` (Appendix A §A.1.4 reasoned exclusion — e.g. AICT-P02's un-instrumented feedback lane) is grey-striped and **excluded** from the rollup, so it does not degrade the row; an *unreasoned* `Unknown` still degrades it.

### C.3 Colour → action-severity map

| Signal state | Action severity |
|---|---|
| **Red** on a **High**-risk case | **Critical** |
| **Red** on Medium / Low | **High** |
| **Amber persisting 2 consecutive weekly reviews** | **Medium** |
| **Critical `Unknown`** (High-risk case lacking owner, classification, or telemetry) | **High** |

The scenario engine tracks per-signal consecutive-Amber counts across `WEEKLY_REVIEW` events (every 7 ticks) to implement the Amber×2 → Medium conversion; single-review Amber is watch-listed only, no action. **Dedupe rule:** at most one **Open** action per `(registry_id, signal key)` — a re-observed Red attaches to the existing open action rather than creating a duplicate; a Closed action re-fires on a new Red unless suppressed by the post-remediation label-lag rule (Appendix A §A.5.5).

### C.4 Closure SLAs

In the demo, 1 tick = 1 simulated day and every tick is a working day, so the working-day SLAs map directly to ticks. `due_date` = fire tick + SLA ticks.

| Severity | Close within | SLA ticks | On SLA breach (due date passes) |
|---|---|---|---|
| **Critical** | **48 h** | **2 ticks** | Auto-escalate to RAI Council + CDAO notification |
| **High** | **5 working days** | **5 ticks** | Auto-escalate one level (owner → business owner → Council) |
| **Medium** | **15 working days** | **15 ticks** | COE chases; flagged in weekly review |
| **Low** | **30 working days** | **30 ticks** | Batch-reviewed monthly |

An action whose due date passes **escalates automatically** per its own severity row above — it cannot silently slip, and there is **no blanket "everything escalates"**. On breach the engine sets `escalated = true`, extends `escalation_path`, and emits an `SLA_BREACH_ESCALATION` event (alert-log entry + UI toast + View 6 `AUTO-ESCALATED` badge); the action **stays open** — escalation is added visibility, not closure. The scenario deliberately lets one Critical action breach on stage — **ACT-001** fires at t9 (`data_drift_share` Red), is due t11 (opened + 2 ticks), and breaches at t12 → auto-escalates to RAI Council + CDAO. In deliberate contrast, **ACT-003** (chatbot hallucination, fires t13, due t15) is closed *within* SLA at t15, so the queue shows both behaviours side by side (Appendix A §A.5.4).

### C.5 Escalation targets per signal type

| Trigger (signal / condition) | Escalation target & response |
|---|---|
| `pii_exposure_rate` Red — PII leakage / unauthorized access | **Incident runbook S1 — Security + DPO immediately**; PDPA 72-h regulator clock where personal-data breach criteria are met; CDAO informed same day |
| `hallucination_rate` Red — wrong-answer threshold breached | SME review + remediation (fix grounding / unsupported-answer refusal handling) |
| `groundedness` / `relevance` Red — citation / retrieval quality drop | KB owner + technical owner (retrieval-quality review with the content owner) |
| `p95_latency_s` Red — latency / API failures affecting workflow | Technical owner |
| `data_drift_share` Red — input data drift | Technical owner; schedule retraining review (stage-8 re-review) |
| `estimated_roc_auc` Red — label-free performance-drop estimate | Data Science: retrain / regression-test; confirm with labels when they arrive |
| `realized_roc_auc` Red — confirmed degradation | Data Science: retrain and re-validate before continuing in production |
| High-risk case missing owner or monitoring (critical `Unknown`) | RAI Council / COE |
| Repeated unsafe tool-call attempts *(not in the two demo seeds; kept for generality)* | Disable tool, tighten guardrails, or require human approval |
| Major model / vendor / data / prompt / workflow change | Re-review (stage 8): architecture + RAI |

## Appendix D — The 7 Views (UX Specification)

This appendix is the build spec for the frontend. Field names in `code` are the **exact** assurance-registry field names (Appendix B). Everything here renders from the FastAPI JSON API — the single API contract in **Appendix E §E.3** — and no view computes governance logic client-side beyond display formatting.

### D.0 Conventions (apply to every view)

**Health chips.** Solid, labelled chips — colour is never the only signal (the label is always printed):

| State | Fill | Text | Notes |
|---|---|---|---|
| Green | `#00A66C` | white | Sheet-3 "continue in production" |
| Amber | `#FFB000` | `#1A1A1A` | trending toward Red (doctrine below) — not a Sheet-3 value band |
| Red | `#E60012` | white | Sheet-3 "issue / escalate"; matches True brand red |
| Unknown | `#8A8F98` | white | **always rendered — never blank**; "missing telemetry is itself a finding" |
| Not applicable | `#ECEEF1` outline | `#9AA0A6` | em-dash "—"; lane not relevant to this use-case type — visually distinct from Unknown |

**Amber doctrine (one phrasing — legend and engine).** *Amber = trending toward Red — a value in the gap between the Green bar and the Red bar (trending by definition), a Red-ward trend across two weekly reviews, or a missing/stale data-or-owner gap. Sheet-3 itself defines no Amber band.* The engine grades gap values Amber mechanically; every legend that explains Amber uses this phrasing.

**Responsive rule.** Design target 1280 px (meeting-room projector); minimum 1024 px. Any table or heatmap wider than its container scrolls horizontally **inside its own `overflow-x: auto` wrapper**; the page body itself never scrolls horizontally.

**Tick reactivity.** All views subscribe to the scenario event stream (`GET /api/events`, SSE; poll fallback = `GET /api/scenario/state` at 2 s). State changes animate with a 300 ms ease crossfade; cells/rows changed in the current tick carry a small corner dot for one tick.

**Simulated clock.** Rendered everywhere as `Day N · YYYY-MM-DD (simulated)` — the word *simulated* is never dropped. Tick 0 = 2026-07-13; every tick is a working day.

**Scenario reference notation** (used in the "Simulation behaviour" sections below). **Appendix A is normative** for all scenario content; views reference scenario moments by tick — "S2 t9" = tick 9 of scenario S2 — never by named stages. Shipped scenarios: **S1** Steady state · **S2** ML drift (`data_drift_share` Red at t9 → ACT-001; `realized_roc_auc` Red at t13 → ACT-002) · **S3** LLM degradation (hallucination Red at t13 → ACT-003) · **S4** SLA breach (ACT-001 due t11 passes; auto-escalation at t12) · **S5** Remediate & recover (metrics recover; scripted CLOSE_ACTION at t15) · **DEMO-FULL** — the 20-tick master script.

**API surface.** The single API contract lives in **Appendix E §E.3**; no endpoint is re-specified here. Endpoints consumed per view: View 1 `GET /api/summary` · Views 2/3/5 `GET /api/registry` (filter params) · View 4 `GET /api/heatmap` · View 6 `GET /api/actions` + `PATCH /api/actions/{action_id}` · View 7 `GET /api/board-narrative` · drill-down `GET /api/use-cases/{registry_id}` + `GET /api/artifacts/{artifact_id}` · alerts `GET /api/alerts` · player bar `GET /api/scenario/state` + `POST /api/scenario/load` / `/play` / `/pause` / `/step` / `/speed` / `/jump` / `/reset` · all views `GET /api/events` (SSE; poll fallback `GET /api/scenario/state`) · demo fallback `GET /api/export/demo-snapshots`.

---

### D.1 View 1 — At A Glance

**Purpose.** Answer "how big, how risky, how healthy is the AI portfolio?" in five seconds — the meeting-opening screen.

**Layout.** Two rows of four stat cards, then a full-width pilot health strip.

```
┌──────────┬──────────┬──────────┬──────────┐
│ 130      │ 38       │ 36       │ 40       │
│ Total AI │ Product- │ In dev-  │ Require- │
│ use cases│ ion      │ elopment │ ments    │
├──────────┼──────────┼──────────┼──────────┤
│ 4        │ 12       │ 15       │ 1/2/3    │
│ Hi-risk  │ Missing  │ Pilot    │ Pilot    │
│ missing  │ risk     │ assurance│ Red/Amb/ │
│ approval │ assessmnt│ set      │ Unknown  │
├──────────┴──────────┴──────────┴──────────┤
│ Pilot strip: ●●●●●●●●●●●●●●●  (15 chips)  │
└────────────────────────────────────────────┘
```

**Components.** Stat card (big number, label, small delta-since-last-tick chip); pilot strip of 15 mini health chips (one per `AICT-P*` row, hover = `use_case_name`).

**Data binding.** `GET /api/summary`, computed server-side from the registry: totals and lifecycle counts over `status` (production 38 · in-development 36 · requirements/not-started 40 · paused 3 · retired/cancelled 13 = 130); "High-risk missing approval" = `risk_tier = High` AND any of `privacy_status`/`security_status`/`rai_status` not in its approved/complete state; "Missing risk assessment" = `risk_tier = Unknown`; pilot set = rows with `registry_id` prefix `AICT-P`; Red/Amber/Unknown counts over pilot rows' `current_health`. Seed values are a **synthetic echo** of the board-narrative/dashboard-prototype counter set — one of three un-reconciled portfolio counts (register 131/37 · 6-Jul COE 125/35 · board 130/38), reconciliation due pre-Aug-4 **[TBC]**; acceptance tests assert the seeded counter set, never the COE count (provenance in the References section — not live True numbers).

**Interactions.** Card click navigates pre-filtered: lifecycle cards → View 2 with the matching `status` filter; risk/evidence cards → View 5; pilot cards and strip chips → View 3 (chip click → that case's drill-down).

**Empty/Unknown states.** Counters render `0`, never blank. The Red/Amber/Unknown card always shows all three numbers with their chip colours (grey for Unknown). If the DB is empty (seed skipped), the view shows a single "Seed data not loaded — Load demo data" panel.

**Simulation behaviour.** Health-derived numbers move: the pilot Red/Amber/Unknown card ticks 0→1 Amber as S2's drift enters the guard band, →1 Red at t9, and back to Green over S5, each with a delta chip animation. Portfolio-size and evidence counters stay static in the shipped scenarios (scenario files *may* mutate evidence fields).

---

### D.2 View 2 — Portfolio Health *(P1)*

**Purpose.** Slice the portfolio five ways to expose concentrations and blind spots (where monitoring can be designed-in vs retrofitted; where Council/DPO attention is needed).

**Layout.** Five horizontal 100 %-stacked bars (one per slice), a shared legend, and a filtered registry table below.

```
Lifecycle   [ req 40 | in-dev 36 | production 38 | paused 3 | retired 13 ]
Risk tier   [ High | Medium | Low | Unknown(grey) ]
Platform    [ True platform (sim) | Microsoft | Internal | Vendor | Unknown ]
BU/domain   [ HR | CallCtr | Network | Finance | CVM | … ]
Health      [ Green | Amber | Red | Unknown ]
────────────────────────────────────────────────
Active filters: [production ×] [High ×]   Clear all
┌ filtered registry table (scrolls in container) ┐
```

**Components.** Stacked slice bar (segment = count + %, min-width so small segments stay clickable); filter chips; registry table (same columns as View 3 plus `business_unit`, `platform_or_app`).

**Data binding.** `GET /api/registry` aggregated over `status` (lifecycle), `risk_tier`, `platform_or_app`, `business_unit`, `current_health`. Table rows bind the same fields.

**Interactions.** Segment click adds a filter (AND across slices); active filters render as removable chips; row click → drill-down (deep cases) or a read-only stub-row panel (background rows).

**Empty/Unknown states.** `Unknown` is always a legend entry and always grey, shown even at count 0 (rendered as `Unknown · 0`). An empty filter result shows "No use cases match — clear a filter", never a bare table.

**Simulation behaviour.** Only the Health bar re-proportions during scenarios (one row's `current_health` moving Amber→Red→Green shifts segment widths with an animated tween). Other slices are static portfolio structure.

---

### D.3 View 3 — Pilot Health Table

**Purpose.** The working table for the 15-row pilot assurance set — one row per case: what's wrong, who acts, by when.

**Layout.** Full-width table in a horizontal-scroll container; sticky header; sticky first column (`registry_id`).

| Column | Binding | Render |
|---|---|---|
| ID | `registry_id` | monospace link |
| Use case | `use_case_name` | + `use_case_group` subtext |
| Lifecycle | `status` | text |
| Risk | `risk_tier` | tier badge + cadence badge (P1, R-26) |
| Health | `current_health` | health chip |
| Missing evidence | derived: any of `privacy_status`, `security_status`, `rai_status`, `ai_readiness_status`, `telemetry_status` not in its complete/approved/live state → list those field labels | comma list, `Unknown` items in grey |
| Next action | most severe open action's `recommended_action` for this `registry_id` | truncated, tooltip full |
| Owner | `monitoring_owner` | text (grey `Unknown` chip if unset) |
| Due | that action's `due_date` | simulated date + `T-n` countdown; red `OVERDUE +n` past due |

**Data binding.** `GET /api/registry?group=pilot` joined server-side with `GET /api/actions?status=Open`.

**Interactions.** Row click → drill-down (D.8). Column sort (default: health severity desc — Red, Amber, Unknown, Green). Header filter chips for Health and Risk. Hover on "Missing evidence" lists the exact status values.

**Empty/Unknown states.** Any `Unknown` field renders the grey chip (per R-02). A case with no open action shows "—" in Next action/Due (em-dash = "nothing pending", distinct from Unknown). No pilot rows → seed prompt panel.

**Simulation behaviour.** During S2: AICT-P02's Health chip flips Green→Amber (drift in the guard band; trend confirmed at the t7 WEEKLY_REVIEW)→Red at t9; "Next action" populates at t9 with ACT-001's retraining recommendation and a live `T-2` countdown; in S4 the Due cell turns red `OVERDUE +1` at t12; in S5 Health returns to Green and Next action/Due clear after the t15 close. Changed cells pulse once.

---

### D.4 View 4 — Monitoring Lane Heatmap *(the signature view)*

**Purpose.** One matrix showing which of the five §10 monitoring lanes is healthy, degrading, or simply **unmeasured** across the pilot portfolio — the single image the whole operating model reduces to.

**Layout.**

```
                      Risk  Quality  Safety/  Reliab-  Drift/   Feedback/  Overall
Use case                             security ility    degrad.  action
──────────────────────────────────────────────────────────────────────────────────
HR Policy Chatbot     High  [Green]  [Green]  [Green]  [Amber]  [Green]    [Amber]
Churn / NBA model     High  [Amber]  [ — ]    [Green]  [RED]    [Unkn]     [RED]
Call Center KB        Unk   [Unkn]   [Amber]  [Unkn]   [Unkn]   [Unkn]     [Unkn]
… (15 pilot rows)
──────────────────────────────────────────────────────────────────────────────────
Legend: Green = Sheet-3 "continue" · Red = "issue/escalate" · Amber = trending
toward Red (gap value, Red-ward trend across two weekly reviews, or missing/stale
gap — Sheet-3 defines no Amber band; D.0) · Unknown(grey) = missing telemetry —
itself a finding · — = lane N/A
```

Matrix in a horizontal-scroll container; row height 40 px; cells are solid chips with the state label printed (colour-blind safe).

**Components.** Heatmap grid; legend (always visible, exact wording above); per-row cadence badge (P1); "changed this tick" corner dot.

**Data binding.** `GET /api/heatmap` → per pilot row: `registry_id`, `use_case_name`, `risk_tier`, `quality_status`, `safety_status`, `reliability_status`, `degradation_status`, `feedback_status`, `current_health` (Overall column), plus per-cell tooltip payload (the lane's `*_metric` and `*_threshold`, e.g. `quality_metric`, `quality_threshold`, and the driving signal's latest value).

**Interactions.** Cell click → drill-down anchored to that lane's signals section. Row-name click → drill-down top. Column-header click sorts rows by that lane's severity. Tooltip shows metric, threshold, current value, and "driven by: <signal label>".

**Empty/Unknown states.** `Unknown` = solid grey chip labelled *Unknown* (a finding — AICT-P02's Feedback lane ships `Unknown`: "no feedback loop instrumented — itself a finding"); lane N/A = light outline "—" (deliberate, not missing). A use case with zero computed lanes still renders — a full row of grey Unknowns is exactly the message.

**Simulation behaviour.** The core demo moment: during S2 the AICT-P02 *Drift & degradation* cell flips **Green → Amber → Red** (Red at t9) with a 300 ms crossfade and a brief pulse ring on each change; the Quality cell follows the NannyML story — the estimated AUC sags into the Amber guard band and never crosses Red, while the realized AUC crosses Red at t13 — and Overall recomputes worst-of within the same tick. During S3 the AICT-P01 Quality cell flips Red at t13 on the hallucination spike. S5 reverses cells to Green one lane at a time (recovery reads as a wave, not a jump-cut).

---

### D.5 View 5 — Risk & Evidence Gaps *(P1)*

**Purpose.** Turn missing governance evidence into typed, countable, actionable gaps — the "what the registry doesn't know" view.

**Layout.** One rule-card per gap type (5 shipped), each with live count, detection rule, action rule, and affected cases; a detail list expands inline.

| Gap type | Detection rule (field predicates) | Action rule (displayed) |
|---|---|---|
| Risk tier unknown | `risk_tier = Unknown` AND `status = production` | Assign owner + due date for risk screening |
| DPO / privacy status unclear | `privacy_status` ∈ {`Unknown`, `Required`, `In review`} | Escalate to DPO if personal data is likely |
| Security assessment incomplete | `security_status` ∈ {`Not started`, `In review`, `Unknown`} | Track in shared risk register |
| Readiness checklist missing | `ai_readiness_status` ∈ {`Missing`, `Unknown`} | Block production sign-off until evidence exists |
| Monitoring plan absent | `telemetry_status` ∈ {`Missing`, `Unknown`} | Mark health `Unknown` until cadence + metrics exist |

**Components.** Gap card (count badge, rule text, expand chevron); affected-case list (ID, name, the offending field value as a grey/amber chip, owner).

**Data binding.** `GET /api/registry` filtered server-side per predicate; each card returns `count` + `cases[]` with the predicate's driving fields.

**Interactions.** Count click expands the affected list; case click → drill-down; "Create action" button per case (demo: opens a pre-filled action form; shipped scenarios pre-create these where scripted).

**Empty/Unknown states.** A gap with count 0 renders greyed with "0 — no cases" (rules stay visible; absence of gaps is information). Field values driving a gap always display as chips, `Unknown` in grey.

**Simulation behaviour.** Static by default — shipped scenarios do not mutate evidence fields, so this view demonstrates the *standing* gaps in the seeded portfolio (4 high-risk-missing-approval, 12 missing-risk-assessment — the seeded counter set). Scenario files may mutate evidence fields; if one does, counts re-badge with a pulse.

---

### D.6 View 6 — Action Queue

**Purpose.** The closed-loop half of the operating model: every Red / critical-Unknown becomes an owned, dated action with §11 per-severity breach behaviour — nothing silently slips.

**Layout.** Filter bar + queue table (horizontal-scroll container), Critical-first.

```
[Severity ▾] [Status ▾] [Owner ▾] [☐ Overdue only]          n open · n escalated
┌────┬─────────┬───────────────┬──────────────────┬────────┬─────────┬──────────┬────────┐
│Pri │ Action  │ Use case      │ Issue            │ Owner  │ Due     │ Escalate │ Status │
├────┼─────────┼───────────────┼──────────────────┼────────┼─────────┼──────────┼────────┤
│ P0 │ ACT-001 │ Churn / NBA   │ data_drift_share │ RAI COE│ Day 11  │ Council +│ Open   │
│    │Critical │ AICT-P02      │ = 0.55 (Red)     │        │ T-2     │ CDAO     │        │
└────┴─────────┴───────────────┴──────────────────┴────────┴─────────┴──────────┴────────┘
```

**Components.** Priority chip (display map: Critical→**P0**, High→**P1**, Medium→**P2**, Low→**P3**, severity word beneath) — **P0–P3 in the UI display the §11 severity**; the dashboard-prototype's trigger classes are subsumed by the §10/§11 severity map. SLA countdown chip (`T-n` neutral, amber at `T-1`, red `OVERDUE +n` past due); escalated rows get a red left border + a per-severity §11 banner (Critical: "Escalated to RAI Council + CDAO" · High: "Escalated one level" · Medium: "COE chase — weekly review" flag · Low: "monthly batch review" tag); status dropdown; row-expand history.

**Data binding.** `GET /api/actions` → schema-exact action fields: `action_id` (format `ACT-001` / `ACT-002` / …), `registry_id` (+ joined `use_case_name`, `risk_tier`), `issue` (signal label + value + health), `recommended_action`, `owner`, `due_date` (simulated date + tick), `escalation_path`, `status`, `evidence_link` (resolves to the artifact that triggered it — e.g. the Evidently report for a drift action). Severity/SLA derive from the §10 colour→severity map (R-14); dedupe: at most one open action per (`registry_id`, signal key).

**Interactions.** Filters; status edit (`Open` / `In progress` / `Blocked` / `Closed`) via `PATCH /api/actions/{action_id}` — closing decrements the registry row's `open_actions`; **ad-hoc status edits during a demo live in the session-local overlay and are discarded on jump/reset** — the presenter's "Close with evidence" click at t15 is the trigger for the scripted CLOSE_ACTION event, which persists; row expand shows the event history (created → escalated → closed, tick-stamped); `evidence_link` opens the artifact in a viewer panel.

**Empty/Unknown states.** Empty queue renders the success panel *"No open actions — nothing Red this cycle."* An action with `due_date = Unknown` shows a grey Unknown chip in Due and is flagged by a "no due date" warning icon (a dated queue is the point).

**Simulation behaviour.** S2 t9: ACT-001 (Critical) slides in at the top with a toast (R-25). Each tick decrements the countdown. S4 t12: the countdown flips to red `OVERDUE +1`, the row auto-escalates per §11 (banner "Escalated to RAI Council + CDAO"), and the alert log records it — with no user input. S2 t13: ACT-002 (realized-AUC Red) joins the queue — S2's final tick holds **exactly two open Critical actions**. S5 t15: the presenter's "Close with evidence" click fires the scripted CLOSE_ACTION; the action animates out of the Open filter and `open_actions` on AICT-P02 returns to 0.

---

### D.7 View 7 — Board Narrative Panel

**Purpose.** The board-ready, read-only one-pager: five governance claims, each paired with live proof from the running registry.

**Layout.** Title block ("AI Use Case Observability — Board View", simulated as-of date, "CPG Confidential · Simulated data" mark), then five statement rows, each: narrative sentence (left) + live proof-stat card (right).

| Narrative statement (fixed copy) | Live proof-stat binding |
|---|---|
| One registry links AI Reporting Tool / VRO / TPM records to assurance evidence. | total rows; % with `source_record_id` ≠ `Unknown` |
| Risk-based monitoring separates high, medium, low, and unknown cases. | counts by `risk_tier` with cadence labels |
| Named owners make validation and post-production action accountable. | % pilot rows with `business_owner`, `technical_owner`, `monitoring_owner` all named (≠ `Unknown`) |
| Red/amber/unknown items become action queues, not hidden spreadsheet gaps. | open actions; % closed within SLA (on-time closure) |
| The intelligence layer can become the operating backbone as platform telemetry matures. | `telemetry_status` distribution (`Live`/`Manual`/`Partial`/`Missing`/`Unknown`) |

**Data binding.** `GET /api/board-narrative` (statements + computed stats in one payload).

**Interactions.** None for board consumption — deliberately static; no edit controls. There is **no board-only role**: every viewer sees all seven views, and View 7 is simply **screenshot-ready** for board decks. P2: "Export PDF/PNG" button (R-32); baked per-tick snapshots of this view are also served via `GET /api/export/demo-snapshots` (R-34). The guided-script overlay (P1, R-28) can highlight one statement at a time.

**Empty/Unknown states.** Proof-stats degrade gracefully: a stat over zero rows renders "no data yet" in grey; `Unknown`-heavy distributions show the grey share explicitly (the honesty is the message to the board).

**Simulation behaviour.** Proof-stats update at each tick (open actions rises at t9 and t13, on-time closure % moves at t12 and t15); the narrative copy never changes. Played over S4→S5 this view tells the whole story in numbers: breach → escalation → recovery.

---

### D.8 Use-case drill-down page

**Purpose.** The evidence room for one use case: every signal against its threshold band (Appendix C), the real engine artifacts behind each grade, and the action history.

**Route.** `/use-case/{registry_id}` (from any view's row/cell click).

**Layout.**

```
┌ Header ──────────────────────────────────────────────────────────────┐
│ HR Policy Chatbot (RAG)   AICT-P01 · source: Unknown                 │
│ [production] [High risk] [Amber] [telemetry: Live (simulated)]       │
│ [Weekly cadence]                                                     │
│ Owners (roles): business — HR process owner · technical — platform  │
│ engineering · monitoring — RAI COE                                   │
│ Platform: True Connect chat (simulated)                              │
│ Model: GPT-family via platform gateway (simulated)                   │
│ Data: HR policy corpus (synthetic) · reviewed t7 · next review t14   │
├ Signals (value vs threshold band) ───────────────────────────────────┤
│ Signal            Lane        Value   Band (Green / Red)  Health  ▁▂▃│
│ Hallucination rt  Quality     2.6%    <1% / ≥2%           [RED]   ▁▁▆│
│ Groundedness      Quality     0.81    ≥0.85 / <0.70       [Amber] ▆▅▃│
│ …                                                                    │
├ Tabs ────────────────────────────────────────────────────────────────┤
│ ML case:  Drift (Evidently) · Performance (NannyML) · Explainability │
│ LLM case: Judge scores · Traces · Corpus & eval set                  │
├ Action history ──────────────────────────────────────────────────────┤
│ t13  ACT-003 created (Critical, due t15) → t15 closed                │
│ (Close with evidence)                                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Header binding.** `use_case_name`, `registry_id`, `source_record_id` (both deep rows ship `Unknown`), chips for `status`, `risk_tier`, `current_health`, `telemetry_status` (`Live (simulated)` on both deep rows), cadence badge (from `risk_tier`, P1); owners strip = `business_owner`, `technical_owner`, `monitoring_owner`, `system_owner` — **owners are roles, not names**; meta = `platform_or_app`, `model_provider`, `model_or_route`, `workflow_location`, `data_sources`, `last_reviewed`, `next_review`. Example values above match the Appendix B seed rows (the single normative deep-row table).

**Signals table.** One row per signal from `GET /api/use-cases/{registry_id}`: label · lane · current value (formatted per unit; `—` if none) · **band rendered as "Green ≤/≥ x · Red ≥/< y" with direction (Appendix C)** · health chip · 15-tick sparkline with the Red bar drawn as a reference line. Demo default bands (High-risk; full spec Appendix C):

| Signal | Lane | Green | Red |
|---|---|---|---|
| `hallucination_rate` | Quality | < 1 % | ≥ 2 % |
| `groundedness` | Quality | ≥ 0.85 | < 0.70 |
| `relevance` | Quality | ≥ 0.85 | < 0.70 |
| `pii_exposure_rate` | Safety & security | = 0 % | ≥ 1 % |
| `p95_latency_s` | Reliability | ≤ 4.0 s | ≥ 8.0 s |
| `data_drift_share` | Drift & degradation | ≤ 0.30 | ≥ 0.50 |
| `estimated_roc_auc` | Quality | ≥ 0.80 | < 0.72 |
| `realized_roc_auc` | Quality | ≥ 0.80 | < 0.72 |

**Band provenance (§10).** Only the hallucination tier table (High < 1 % / < 2 % / ≥ 2 %; Medium < 2 % / < 3 % / ≥ 3 %; Low < 3 % / < 5 % / ≥ 5 %) is inherited **verbatim** from the Deployment Checklist Sheet-3 (SL#2.1). All other bands above are **demo defaults expressed in the Sheet-3 band format** — per proposal §10, thresholds are set per use case at onboarding, and the reliability defaults are provisional pending pilot. Any "inherited, not invented" claim is scoped to hallucination only.

**Artifact tabs — ML case (AICT-P02).**
- **Drift (Evidently):** drifted-features list (names + count), then the full Evidently HTML report for the current tick in a sandboxed same-origin iframe (min-height 620 px, internal scroll); at S2 t9 it lists ≥ 3 drifted features.
- **Performance (NannyML):** line chart of `estimated_roc_auc` (solid) vs `realized_roc_auc` (dashed — populated from tick 0 via 3 pre-history windows, trailing the serving window by `label_lag_ticks: 3`) vs the reference-window AUC (dotted), Red bar as a reference line; analysis chunk 500 rows/tick against a 4,000-row reference window; caption: *"NannyML estimates production performance before ground-truth labels arrive — the early warning the Drift/Quality lanes rely on."*
- **Explainability (LIME / SHAP):** LIME HTML embed for the highest-risk instance (caption: row index + churn probability) above the SHAP global-importance PNG; P1 (R-27) upgrades to side-by-side with the verbatim caveat copy: *"LIME explanations are local and can be unstable (fidelity-vs-simplicity trade-off). SHAP is the more consistent, game-theoretic counterpart — and what the enterprise path (Azure ML Responsible AI dashboard) uses."*

**Artifact tabs — LLM case (AICT-P01).**
- **Judge scores:** per-question table (question · answer excerpt ≤ 80 chars · groundedness · relevance · hallucination flag · PII flag · latency s) for the current tick's evaluated interactions, with the permanent banner *SIMULATED JUDGE — deterministic seeded simulation (count-based hallucination injection + seeded score draws)*. **Offline/simulated only** — no live-LLM mode ships in demo scope (Deferred; returns at pilot behind `LLMEvalAdapter`).
- **Traces:** trace list read from the **SQLite-backed trace store** (LangfuseStub) **via the API** (input/output/scores/latency per trace); with LangfuseCloud wired (P2, R-30), deep-link per trace.
- **Corpus & eval set:** the 6 policy topics and the 10-question eval set with `answerable` flags — makes the unanswerable-question (refusal/grounding) mechanic legible to the audience.

**Action history.** Tick-stamped timeline of all actions for this `registry_id` (created → escalated → closed), each linking to View 6.

**Interactions.** Tab switching; sparkline hover (tick + value); artifact download; lane anchor links (heatmap cell click lands here scrolled to that lane's signals); P2 what-if threshold editor (R-33) attaches to each signal row (session-local overlay; discarded on jump/reset).

**Empty/Unknown states.** Signal without data → value `—`, grey Unknown health chip, flat sparkline. A degraded engine (import/runtime failure) shows an amber banner *"Engine degraded this run: <engine>: <error> — lane graded Unknown"* (per R-22); its tab shows the error panel instead of the artifact — never a blank tab.

**Simulation behaviour.** Sparklines extend one point per tick (monitoring runs every tick); band lines are static so the crossing moment is visible. Artifacts (Evidently/LIME/SHAP/judge table) refresh each tick with a "refreshed Day N" stamp. In S2 the NannyML chart is the narrative centrepiece: the estimated line sags into the Amber guard band [0.72, 0.80) and **never crosses Red** — the early warning — while the realized line, trailing 3 ticks behind the serving window, crosses the Red bar at t13 and confirms the estimate, firing ACT-002.

---

### D.9 Global chrome & scenario player bar

**Masthead (all views).** Dark gradient bar (near-black → True red `#E60012` accent): product name **"AI Use Case Observability Control Tower"**, a **SIMULATION** tag, and — pinned right — the permanent masthead badge **"CPG Confidential · Simulated data"** (R-21). The badge appears on every route including drill-downs, and exports carry the same mark.

**Navigation.** Top tab bar with the seven views in order: *At A Glance · Portfolio · Pilot Table · Heatmap · Gaps · Actions · Board*. Drill-downs open with a breadcrumb (`Heatmap › Churn / NBA model`). P1 views (Portfolio, Gaps) render as disabled tabs with a "P1" marker until built. There is **no board-only role**: viewers see all seven views; View 7 is simply screenshot-ready.

**Scenario player bar (docked bottom, always visible, above the fold at 1024 px).**

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ Scenario: [DEMO-FULL — 20-tick master ▾]  ⏮ Reset  ▶ Play / ⏸ Pause  ⏪ −1  ⏩ +1  │
│ ⏭ Jump…  [1×|2×|4×]                                                              │
│ Day 9 / 20 · 2026-07-24 (simulated) · ACT-001 open (Critical) ●                  │
│ [Presenter/Viewer ▾]  [Guided script]                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

- **Scenario selector:** S1 Steady state · S2 ML drift · S3 LLM degradation · S4 SLA breach · S5 Remediate & recover · DEMO-FULL (20-tick master). Each scenario is self-contained (includes its own preamble ticks) so any can be loaded cold; loading resets to its baked tick 0.
- **Transport:** play (auto-advance at the selected speed — **1× = 2.0 s per tick**; 2×/4× multipliers), pause (freezes everything mid-state), step ±1 (< 1 s, baked DB read), jump to tick (`POST /api/scenario/jump`), reset (**restores baked tick 0 in < 2 s** via pointer swap; discards the session-local overlay). Keyboard: `Space` play/pause · `←`/`→` step · `R` reset.
- **Tick counter + simulated date + open-action indicator** (count and top severity of open actions at the current tick).
- **Alert toast anchor (R-25):** toasts stack immediately above the bar so they never cover the heatmap.
- **Presenter mode (access toggle only):** *presenter* = scenario controls + action edits; *viewer* = read-only, sees **all seven views**. Interactive mutations made as presenter (ad-hoc action edits, what-if threshold edits) live in a **session-local overlay discarded on jump/reset**; the presenter's "Close with evidence" click at t15 is the trigger for the scripted CLOSE_ACTION event.
- **Guided-script overlay (P1, R-28):** overlays the guided demo script — one talking point per scripted beat (e.g., S2 t9: *"The drift crossed its Red bar — a Critical action just fired with a two-tick (48-hour) SLA and a named owner. Nothing silently slips."*), dims non-focus chrome, highlights the view under discussion; arrow keys advance points.

**State behaviour.** Player state (`scenario`, `tick`, `playing`, `speed`, `seed`) lives server-side and is synced to every client via `GET /api/scenario/state` + `GET /api/events`, so every open browser tab shows the same simulated moment — a projector and a laptop stay in sync. Determinism per R-04: same scenario + seed ⇒ identical playback, every run, offline.

**Responsive.** Chrome follows D.0: the bar compresses to icon-only controls below 1200 px; the page body never scrolls horizontally.

## Appendix E — Architecture, API & Repository Skeleton

Greenfield build. A proven reference implementation exists in the author's workspace (provenance only — see the note at the end of Appendix G, never a build dependency). The demo runs **offline, deterministic, baked** (Appendix A §A.1.2).

### E.1 Architecture diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FRONTEND — Next.js (app router) / React / TypeScript / Tailwind           │
│  7 dashboard views · use-case drill-downs · ScenarioPlayerBar              │
│  (play / pause / step / speed / jump / reset) · GuidedScriptOverlay        │
│  MASTHEAD BADGE "CPG Confidential · Simulated data" on every route         │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ /api/*  (Next.js rewrites → FastAPI; same-origin)
┌───────────────────────────────▼──────────────────────────────────────────┐
│  BACKEND — FastAPI (Python 3.12)   ·   dev ports 3000 (web) / 8000 (api)   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │ SCENARIO ENGINE  │  │ HEALTH ENGINE    │  │ ACTION QUEUE            │  │
│  │ bake → SQLite ·  │─▶│ Sheet-3 grading  │─▶│ severity map · SLAs ·   │  │
│  │ tick = DB read · │  │ (App. C) · lane/ │  │ auto-escalation · dedupe│  │
│  │ play/step/jump   │  │ overall rollup   │  │ · alerts                │  │
│  └───────▲──────────┘  └──────────────────┘  └─────────────────────────┘  │
│          │ loads scripts  (NON-engine input — excluded from the swap)      │
│  ┌───────┴────── ScenarioSource (simulation.yaml, App. A §A.4) ────────┐   │
│  └────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────── ENGINE ADAPTERS — the swap seam (App. G) ───────────┐    │
│  │ LLMEvalAdapter          MLMonitorAdapter        ExplainAdapter      │    │
│  │ (judge + tracing)       (Evidently drift +      (LIME + SHAP)       │    │
│  │ ├ langfuse_stub → SQLite│  NannyML performance)  ├ lime_shap (def.) │    │
│  │ │  └ TraceStore sub-i/f ├ evidently_nannyml     └ <azure_rai_       │    │
│  │ ├ langfuse_cloud (opt.) │  (default)               dashboard>(fut.) │    │
│  │ └ <azure_foundry>(fut.) └ <azure_ml>(fut.)                          │    │
│  └────────────────────────────────────────────────────────────────────┘   │
└───────────────┬───────────────────────────────────────┬──────────────────┘
        ┌───────▼────────────┐                  ┌────────▼─────────┐
        │ SQLite (file)      │                  │ artifacts/ dir   │
        │ registry · signals │                  │ Evidently HTML · │
        │ actions · alerts · │                  │ LIME HTML ·      │
        │ scenario_state ·   │                  │ SHAP PNG         │
        │ baked_ticks ·      │                  │ (id→filename map │
        │ traces · scores ·  │                  │  lives in SQLite)│
        │ artifact_map       │                  └──────────────────┘
        └────────────────────┘
```

**Adapter interfaces (normative — exactly three engine protocols; names are fixed; other sections and Appendix G depend on them):**

```python
# backend/app/adapters/llm_eval/base.py — subsumes LLM-as-judge + tracing
class LLMEvalAdapter(Protocol):
    name: str
    def evaluate(self, use_case_id: str, tick: TickContext) -> LaneResult: ...

# TraceStore is a SUB-interface used INSIDE LLMEvalAdapter implementations — not a
# fourth engine. langfuse_stub persists traces/scores to SQLite; langfuse_cloud posts
# to Langfuse. An env-var flip (LLM_EVAL_ADAPTER) selects; calling code is identical.
class TraceStore(Protocol):
    def trace(self, name, input, output, metadata) -> "TraceRef": ...
    def score(self, trace, name, value) -> None: ...
    def flush(self) -> None: ...

# backend/app/adapters/ml_monitor/base.py — subsumes Evidently drift + NannyML performance
class MLMonitorAdapter(Protocol):
    name: str
    def monitor(self, use_case_id: str, tick: TickContext) -> LaneResult: ...

# backend/app/adapters/explain/base.py — LIME + SHAP
class ExplainAdapter(Protocol):
    name: str
    def explain(self, use_case_id: str, tick: TickContext) -> ExplainResult: ...

# backend/app/scenario/source.py — SEPARATE, NON-engine input interface.
# Loads the simulation.yaml scripts (Appendix A §A.4), feeds the scenario engine, and is
# EXCLUDED from the Azure-swap claim of Appendix G — only the three adapters above swap.
class ScenarioSource(Protocol):
    def load(self, scenario_id: str) -> "ScenarioScript": ...
```

- `TickContext` = `{tick: int, seed: int, scenario_id: str|None, inject: dict}` — carries the scenario script's per-tick generator knobs into the adapter (e.g. `inject.churn_alpha`, `inject.n_halluc`).
- `LaneResult` = `{signals: dict[str, float|None], records: list, artifacts: dict[str, str], errors: dict[str, str]}` — `signals` keys are exactly the SignalSpec keys of Appendix C.2; a failed engine degrades its signals to `None` (→ `Unknown`), never crashes the tick.
- `ExplainResult` = `{lime_top: list[tuple[str, float]], instance: dict, artifacts: {lime_html, shap_png}, errors: dict}`.
- **Registered implementations** (selected via env, E.5): `LLMEvalAdapter` → `langfuse_stub` (default) | `langfuse_cloud`; `MLMonitorAdapter` → `evidently_nannyml` (default); `ExplainAdapter` → `lime_shap` (default). Future Azure implementations plug into the same three protocols (Appendix G).
- The **Langfuse stub** implements the same call surface the Langfuse SDK v2 exposes (`Langfuse(...)`, `.trace(name=, input=, output=, metadata=)`, `trace.score(name=, value=)`, `.flush()`) and **persists traces/scores to SQLite** (`traces` + `scores` tables) — the drill-down Traces tab reads them back via `GET /api/use-cases/{id}` — so switching stub ↔ cloud changes configuration, not calling code.

### E.2 BUILT / EXTEND / NEW (greenfield)

| Component | Tag | Notes |
|---|---|---|
| — | **BUILT** | **none — greenfield** (a proven reference implementation exists in the author's workspace; provenance only, not a dependency) |
| Frontend SPA (7 views + drill-downs + ScenarioPlayerBar + GuidedScriptOverlay) | NEW | Next.js app router, TypeScript, Tailwind; chart lib bundled (recharts or similar); no CDN-only deps; masthead confidentiality badge on every route |
| FastAPI backend + REST API (E.3) | NEW | Python 3.12; serves SPA-consumable JSON + static artifacts under `/api` |
| Scenario engine (bake + tick pointer over baked ticks) | NEW | Bake mode is the demo default (precompute → SQLite; tick advance = DB read); live compute is a dev-only mode (ADR-4, Appendix A §A.1.2) |
| `ScenarioSource` (loads `simulation.yaml`, Appendix A §A.4) | NEW | Non-engine input interface; excluded from the swap seam |
| Scenario baker (`POST /api/sim/bake`, dev-only) + per-tick snapshot exporter (R-34) | NEW | Precomputes every tick, action, alert, artifact-id map, and trace to SQLite; snapshots served via `GET /api/export/demo-snapshots` |
| Health engine (Sheet-3 grading + rollup, Appendix C) | NEW | Pure functions; unit-tested against the C.2 table |
| Action queue + SLA + auto-escalation + alerts + dedupe | NEW | Rules per C.3–C.4 |
| `LLMEvalAdapter`: `langfuse_stub`, `langfuse_cloud` | NEW | Stub is the default and persists to SQLite; the judge is a **deterministic seeded simulation** (count-based hallucination injection + seeded score draws) — there is no live-OpenAI mode in demo scope (Deferred; returns at pilot behind this adapter) |
| `MLMonitorAdapter`: `evidently_nannyml` | NEW | evidently 0.4.x `Report` + `DataDriftPreset`; NannyML CBPE label-free ROC-AUC |
| `ExplainAdapter`: `lime_shap` | NEW | LIME per-instance HTML (`random_state=seed`) + SHAP global-importance PNG (background `random_state=0`); LIME-instability caveat shown in UI |
| Synthetic data generators (churn windows + HR corpus/Q&A) | NEW | Seeded; drift/hallucination injection parameterized by the scenario script (Appendix A §A.3) |
| SQLite schema + seed loader + stub-portfolio generator (Appendix B rows) | NEW | SQLAlchemy, portable SQL only (no SQLite-specific features) — ADR-1 |
| `scripts/demo_reset` one-shot task | NEW | Reseed DB + re-point to baked tick 0 — the demo-day fallback (R-34) |
| docker-compose.dev.yml + .env.example + README | NEW | Optional compose; two-command dev path must also work |

### E.3 REST API (the one and only contract)

All responses JSON unless noted. Registry field names are exactly Appendix B; health values are `Green|Amber|Red|Unknown`. Errors: `4xx/5xx` with `{detail}`. **Same-origin:** the browser only ever calls `/api/*`; Next.js rewrites proxy `/api/*` to the FastAPI backend, so there is no CORS surface and no separate API host. Dev ports: Next.js **3000**, FastAPI **8000** (the rewrite target). **This is the single API contract — every other section of this PRD cites these rows; there is no second API table anywhere.**

**Read endpoints**

| Method · path | Request | Response (shape) |
|---|---|---|
| `GET /api/summary` | — | `{as_of_tick, use_case_count, overall_counts{Green,Amber,Red,Unknown}, status_counts{production, in_development, requirements_not_started, paused, retired_cancelled}, open_actions, critical_actions}` (View 1 tiles) |
| `GET /api/registry` | query: `status?`, `risk_tier?`, `health?`, `use_case_group?`, `business_unit?`, `q?` | `{rows: [{registry_id, use_case_name, use_case_group, business_unit, status, risk_tier, current_health, telemetry_status, monitoring_owner, last_reviewed, next_review, open_actions}]}` (Views 2/3) |
| `GET /api/use-cases/{registry_id}` | — | Full Appendix-B row (B.1 + B.2) `+ cadence + lanes{Quality, Safety & security, Reliability, Drift & degradation, Feedback & action loop} + signals:[{key,label,lane,value,health,green_bar,red_bar,unit,direction,history:[{tick,value,health}]}] + artifacts:{evidently_html?, lime_html?, shap_png?, traces?} + actions:[…]` (drill-down; `traces` resolve to the SQLite trace store via artifact ids) |
| `GET /api/heatmap` | — | `{rows:[{registry_id, use_case_name, risk_tier, overall, lanes{Quality, Safety & security, Reliability, Drift & degradation, Feedback & action loop}}]}` (View 4) |
| `GET /api/actions` | query: `status?`, `severity?`, `registry_id?` | `{actions:[{action_id, registry_id, issue, recommended_action, owner, severity, sla, due_date, escalation_path, status, evidence_link, opened_at_tick, escalated}]}` sorted Critical→Low (View 6) |
| `GET /api/alerts` | query: `since_tick?` | `{alerts:[{alert_id, tick, registry_id, signal_key, value, health, severity, sla, owner, recommended_action}]}` — one alert per new Critical/High action or escalation event (View 1 banner / View 5) |
| `GET /api/board-narrative` | — | `{as_of_tick, statements:[s1,s2,s3,s4,s5], proof_stats:{use_cases_monitored, red_open, critical_open, actions_closed_with_evidence, mean_ticks_to_action, amber_watchlisted}}` — the **five board statements + computed proof-stats** that View 7 binds (read-only, screenshot-ready) |
| `GET /api/artifacts/{artifact_id}` | — | The artifact file (Evidently/LIME HTML, SHAP PNG) with its content-type; `artifact_id`→filename is resolved from the **per-tick map in SQLite**; `404` on unknown id |

**Action mutation**

| Method · path | Request | Response (shape) |
|---|---|---|
| `PATCH /api/actions/{action_id}` | body: `{status?, owner?, due_date?, evidence_link?}` | Updated action row. Rule: `status:"Closed"` without a non-empty `evidence_link` → `422` (evidence-before-closure, B.3). In a demo run the edit lands in the session-local overlay (discarded on jump/reset); the presenter's **"Close with evidence"** click at t15 is the trigger for the scripted `CLOSE_ACTION` event (Appendix A §A.1.2) |

**Scenario control** *(presenter mode only)*

| Method · path | Request | Response (shape) |
|---|---|---|
| `GET /api/events` | — (SSE) | Server-Sent Events stream: `tick`, `action_opened`, `action_escalated`, `alert`, `scenario_state`. **Poll fallback:** `GET /api/scenario/state` |
| `GET /api/scenario/state` | — | `{scenario_id, tick, total_ticks, playing, speed, mode:"baked"|"live", events_this_tick:[]}` (poll fallback; no `phase` field — scenarios are event-driven, Appendix A) |
| `POST /api/scenario/load` | body: `{scenario_id}` | `{scenario_id, tick:0, total_ticks, mode}`; loads a baked scenario (S1–S5 or DEMO-FULL) and points at tick 0 |
| `POST /api/scenario/play` | — | `{playing:true, speed}` — advances at `2.0 s / tick ÷ multiplier` |
| `POST /api/scenario/pause` | — | `{playing:false, tick}` |
| `POST /api/scenario/step` | — | Advance one tick — a DB read of the baked tick (< 1 s) → `{tick, events_this_tick:[…], summary:{overall_counts, open_actions, critical_actions}}` |
| `POST /api/scenario/speed` | body: `{multiplier: 1|2|4}` | `{speed, multiplier}` |
| `POST /api/scenario/jump` | body: `{tick}` | Pointer-swap to a baked tick (discards the session-local overlay) → `{tick, …}` |
| `POST /api/scenario/reset` | — | Restore baked tick 0 by pointer swap (< 2 s); discards the session overlay → `{scenario_id, tick:0}` |

**Dev-only / export**

| Method · path | Request | Response (shape) |
|---|---|---|
| `POST /api/sim/bake` | body: `{scenario_id}` | **Dev-only** (disabled in the demo/presenter runtime). Runs the whole scenario tick-by-tick through the real engines once and persists every tick, action, alert, artifact-id map, and trace to SQLite → `{scenario_id, total_ticks, baked:true}`. At demo time every tick is a DB read of this bake |
| `GET /api/export/demo-snapshots` | query: `scenario_id?` | Baked per-tick static snapshots of Views 4/6/7 + the NannyML chart (R-34) — a manifest of static files (each carrying the "CPG Confidential · Simulated data" mark) for the demo-day fallback; pairs with `scripts/demo_reset` |

**Access & roles (rule of record).** The scenario-control endpoints and `PATCH /api/actions` are exposed only in **presenter mode** (scenario controls + action edits). **Viewer mode** is read-only and still sees **all 7 views**. The **guided-script overlay** is a separate presenter aid. There is **no board-only role** — View 7 is merely screenshot-ready.

### E.4 Repository skeleton (new repo, monorepo)

```
rai-control-tower-demo/
├── README.md                      # quick start: compose path + 2-command dev path (ports 3000/8000)
├── docker-compose.dev.yml         # optional: backend + frontend, one command
├── .env.example                   # ALL optional — demo runs with ZERO keys (stub is default):
│                                  #   LANGFUSE_PUBLIC_KEY=     (optional — cloud trace store)
│                                  #   LANGFUSE_SECRET_KEY=     (optional)
│                                  #   LANGFUSE_HOST=           (optional)
│                                  #   LLM_EVAL_ADAPTER=langfuse_stub       (default; stub → SQLite)
│                                  #   ML_MONITOR_ADAPTER=evidently_nannyml
│                                  #   EXPLAIN_ADAPTER=lime_shap
│                                  #   DEMO_SEED=42
├── scripts/
│   └── demo_reset                 # one-shot: reseed DB + re-point to baked tick 0 (R-34 fallback)
├── docs/
│   └── prd-v1.0.md                # this PRD (the build contract)
├── frontend/                      # Next.js app router + TypeScript + Tailwind
│   ├── package.json
│   ├── next.config.js             # rewrites: /api/* -> http://localhost:8000/api/*  (same-origin)
│   ├── src/app/                   # routes for Views 1–7 + use-cases/[id] drill-down
│   ├── src/components/            # HealthPill · LaneHeatmap · ScenarioPlayerBar
│   │                              #   (play/pause/step/speed/jump/reset) · ActionTable ·
│   │                              #   SignalTrendChart · GuidedScriptOverlay · MastheadBadge
│   └── src/lib/api.ts             # typed client for the E.3 endpoints (+ SSE)
└── backend/
    ├── requirements.txt           # pins per E.5
    ├── app/
    │   ├── main.py                # FastAPI app + /api routers + static artifact route
    │   ├── api/                   # routers: summary · registry · use_cases · heatmap · actions ·
    │   │                          #   alerts · board · artifacts · scenario · events · sim · export
    │   ├── engines/
    │   │   ├── health.py          # SignalSpec table (C.2) + grading + rollup
    │   │   └── actions.py         # severity map (C.3) + SLAs (C.4) + auto-escalation + dedupe
    │   ├── scenario/
    │   │   ├── source.py          # ScenarioSource (loads simulation.yaml, App. A §A.4) — NON-engine
    │   │   ├── baker.py           # POST /api/sim/bake: precompute every tick → SQLite (dev-only)
    │   │   └── player.py          # tick pointer; play/step/jump/reset over baked ticks
    │   ├── adapters/
    │   │   ├── llm_eval/          # base.py (LLMEvalAdapter + TraceStore) · langfuse_stub.py
    │   │   │                      #   (→ SQLite) · langfuse_cloud.py
    │   │   ├── ml_monitor/        # base.py (MLMonitorAdapter) · evidently_nannyml.py
    │   │   └── explain/           # base.py (ExplainAdapter) · lime_shap.py
    │   ├── datagen/               # churn.py (windows + parameterized drift) ·
    │   │                          #   hr_corpus.py (6-topic corpus + 10-item Q&A set)
    │   └── db/                    # SQLAlchemy models (portable SQL): registry · signals · actions ·
    │                              #   alerts · scenario_state · baked_ticks · traces · scores ·
    │                              #   artifact_map + seed loader
    ├── scenarios/                 # S1–S5 + demo-full master — simulation.yaml schema (App. A §A.4)
    ├── seeds/
    │   ├── registry_seed.json     # the 2 deep + 13 shallow rows (Appendix B)
    │   └── gen_stub_portfolio.py  # deterministic seeded stub generator → 130 rows (B.8)
    ├── artifacts/                 # generated Evidently/LIME HTML + SHAP PNG (gitignored)
    └── tests/                     # health-engine table tests · scenario `expect`/calibration asserts ·
                                   #   portfolio-marginals asserts (B.8)
```

**Scenario scripts follow the `simulation.yaml` schema defined in Appendix A §A.4 (normative).** Bake mode is the demo default — the full scenario is precomputed to SQLite (`POST /api/sim/bake`, dev-time) and every demo tick is a DB read; live engine compute is a dev-only mode (ADR-4).

### E.5 Dependency pins & known gotchas (carry these into the repo verbatim)

**Backend (`backend/requirements.txt`), Python 3.12:**

```
numpy<2.0                    # HARD PIN: evidently 0.4.x + lime break on numpy 2
pandas>=2.0,<2.3
scipy<1.13
scikit-learn>=1.3,<1.6
evidently>=0.4.20,<0.5       # 0.4.x API: Report + DataDriftPreset (0.5+ changed the API)
nannyml>=0.13,<0.14          # <0.13 does not support Python 3.12
lime>=0.2,<0.3
shap>=0.44
matplotlib>=3.7              # SHAP plots (Agg backend, headless)
fastapi>=0.111
uvicorn[standard]>=0.30
sqlalchemy>=2.0
pyyaml>=6.0
python-dotenv>=1.0
langfuse>=2.53,<3            # v2 trace/score API — cloud trace store, OPTIONAL; the in-repo
                             #   stub mirrors the v2 surface and persists to SQLite (E.1)
# NOTE: no `openai` dependency. The LLM judge is a deterministic seeded simulation
#   (count-based hallucination injection + seeded score draws); a live-OpenAI judge is
#   Deferred (returns at pilot behind LLMEvalAdapter) and is out of demo scope.
```

**Frontend:** `next` (14+, app router) · `react` 18 · `typescript` 5 · `tailwindcss` · one bundled chart lib (`recharts` or similar). **No CDN-only dependencies** — everything installs from the lockfile and bundles locally, so the demo runs with no internet.

**Gotchas checklist (each one has bitten before):**

1. Python 3.12 requires `nannyml>=0.13`.
2. `numpy<2` or evidently 0.4.x / lime import errors at runtime.
3. Evidently must be used through the **0.4.x** API: `from evidently.report import Report`, `from evidently.metric_preset import DataDriftPreset` — do not code against the 0.5+ API.
4. Langfuse SDK must be **v2** (`>=2.53,<3`) if the cloud adapter is used; the stub mirrors v2's `trace()`/`score()`/`flush()` so calling code is identical, and persists to SQLite (not JSON).
5. NannyML CBPE result columns are a MultiIndex — extract `("roc_auc", "value")` defensively.
6. SHAP `TreeExplainer.shap_values()` returns a list for binary classifiers on some versions — handle `list` vs `ndarray`.
7. matplotlib must use the `Agg` backend (headless server).
8. Every engine call is wrapped: an engine failure degrades its signals to `Unknown` and records `errors[engine]` — a broken library never kills a tick.
9. **Explainer determinism:** pass `random_state=seed` to `LimeTabularExplainer`, and use `random_state=0` for the SHAP background sample — without these, LIME/SHAP output varies run-to-run and breaks determinism (also fixed in the Appendix A §A.3.1 data spec).

### E.6 Non-functional requirements (demo-grade)

| # | Requirement | Acceptance |
|---|---|---|
| NF1 | **Fully offline** | Fresh clone + install runs the entire demo with an empty `.env` — zero API keys (no `OPENAI_API_KEY` exists), zero network calls at runtime (stub adapter default) |
| NF2 | **Two ways to run** | `docker compose -f docker-compose.dev.yml up` **or** two commands (`uvicorn app.main:app` on :8000 + `npm run dev` on :3000) |
| NF3 | **Cold start < 2 min** | From `up` to View 1 rendering the seeded baseline, on a normal laptop |
| NF4 | **Tick advance < 1 s (baked)** | `POST /api/scenario/step` returns a baked-tick DB read in under 1 s |
| NF5 | **Scenario reset < 2 s** | `POST /api/scenario/reset` pointer-swaps to baked tick 0 in under 2 s |
| NF6 | **Deterministic** | Same `DEMO_SEED` (default 42) + same scenario ⇒ identical signal values, healths, actions, board narrative every run |
| NF7 | **Demo timings** | Scripted DEMO-FULL run plays end-to-end in **under 10 min**; first-time setup **under 30 min [TBC]** |
| NF8 | **Confidentiality marking** | Every route renders the masthead badge **"CPG Confidential · Simulated data"**; exports carry the same mark (no separate footer requirement) |
| NF9 | **No real data** | Repo contains no True data, no PII, no real names (owners are roles); CI grep-gate for obvious PII patterns [TBC — pattern list] |

**ADR notes (the big decisions):**

- **ADR-1 — SQLite, not Postgres (for the demo).** One file, zero setup, trivially resettable. All schema via SQLAlchemy with portable SQL only. **At pilot stage swap to Postgres** — a connection-string change plus a migration, because nothing SQLite-specific is allowed in.
- **ADR-2 — Langfuse stub by default, cloud optional.** The stub keeps the demo offline, deterministic, and guarantees no data (even synthetic) leaves the machine; it persists traces/scores to SQLite and mirrors the Langfuse v2 SDK surface, so `LLM_EVAL_ADAPTER=langfuse_cloud` + keys is a config flip, not a code change. The judge itself is a deterministic seeded simulation — no live-OpenAI path in demo scope.
- **ADR-3 — Monorepo.** One clone, one compose file, one version = one demo; frontend and backend are versioned atomically so the scenario narration and the API can't drift apart. Next.js rewrites keep the browser same-origin (`/api/*` → FastAPI).
- **ADR-4 — Bake mode by default.** The full scenario is precomputed once (`POST /api/sim/bake`, dev-time) and persisted to SQLite; at demo time advancing / jumping / resetting a tick is a DB pointer read, not a live engine run. This is what makes tick advance < 1 s and reset < 2 s (NF4/NF5) and guarantees the on-stage run is byte-identical to the baked, tested run. Live compute remains a dev-only mode for regenerating a bake.

## Appendix F — Demo Script (~10 minutes)

Purpose: Ta walks the team through what he envisions the monitoring tool to be, using the DEMO-FULL scenario (Appendix A). Views 1–7 are the seven dashboard views specified in Appendix D (At-A-Glance · Portfolio Health · Pilot Health Table · Lane Heatmap · Risk & Evidence Gaps · Action Queue · Board Narrative).

### F.1 Pre-demo checklist (run 10 minutes before the meeting)

| ✓ | Check |
|---|---|
| ☐ | Run `scripts/demo_reset` — the **R-34** one-shot task (loads DEMO-FULL at seed 42 and bakes; wraps `POST /api/scenario/load` + `POST /api/sim/bake`, Appendix E §E.3) → status chip shows **BAKED ✓ · seed 42 · DEMO-FULL · tick 0**. |
| ☐ | **Offline mode verified**: `LANGFUSE_*` keys unset (the default — the Langfuse stub is active; there is no `OPENAI_API_KEY` anywhere in scope). Banner shows **OFFLINE / SIMULATED — Langfuse stub active**. Toggle Wi-Fi off once and click through two views — everything must still work (no external keys, no network). |
| ☐ | Masthead badge visible on every route: **CPG Confidential · Simulated data** (exports carry the same mark). |
| ☐ | Browser full-screen (F11), zoom 100 % at 1080p (125 % if presenting on a 4K room screen); light theme; Tab 1 = View 1, Tab 2 = View 4. |
| ☐ | Scenario player docked bottom-right; rehearse twice: *jump to tick 9* and *RESET* (both < 2 s). |
| ☐ | Fallback ready: the **R-34** baked static snapshots (`GET /api/export/demo-snapshots`, Appendix E §E.3 — per-tick Views 4/6/7 + the NannyML chart) saved to local disk — if the app dies mid-demo, present from the export. |

### F.2 Walkthrough (numbered; ~10:00 total)

| # | Time | Presenter does (view · click · tick) | Audience sees | Talking point (one line) |
|---|---|---|---|---|
| 1 | 0:00 | Open **View 1** at tick 0 | Portfolio counters, 2 pilot use cases, 0 open actions, all Green | "One registry for every AI use case — this is the assurance view, not the value dashboard." |
| 2 | 0:40 | Switch to **View 4** (lane heatmap) | 2 use cases × 5 monitoring lanes, all Green; `—` where a lane isn't instrumented | "Five lanes from the operating model — quality, safety, reliability, drift, feedback — live, not a slide." |
| 3 | 1:10 | Start scenario player → **advance to tick 8** | Drift cell on the churn row flips **Amber**; watch-list entry appears | "Marketing's new promo is shifting the customer mix — Amber means *trending*, nobody's escalated yet." |
| 4 | 1:50 | **Advance to tick 9** | Drift cell flips **Red** (share 0.50); toast fires | "Half the model's input features no longer look like its training data." |
| 5 | 2:20 | Open **View 6** (action queue) | **ACT-001 · Critical · close within 48 h** — owner, recommended action, due date auto-filled | "Every Red becomes an action with an owner and a clock — never a note in someone's spreadsheet." |
| 6 | 3:00 | Drill into churn use case → **Evidently tab** | Drifted-feature list: support calls, contract mix, charges; distribution plots | "The tool tells us *which* features moved — support calls tripled; month-to-month contracts jumped." |
| 7 | 4:00 | **NannyML tab**, advance to **tick 10** | Estimated AUC **0.79 (Amber)** while realized still ~0.82 — two lines diverging | "No ground-truth labels yet — NannyML estimates the damage *before* the labels arrive." |
| 8 | 5:00 | **Advance to tick 13**, same chart | Realized AUC drops to **0.70 (Red)** — labels confirm, 3 ticks later | "The labels confirm it three days later — meaning we started acting three days early." |
| 9 | 5:30 | **Explainability tab** | LIME breakdown of the highest-risk customer + SHAP global bar chart | "LIME explains one customer but can be unstable — SHAP is the consistent counterpart, and it's what the Azure enterprise path uses; we show both on purpose." |
| 10 | 6:30 | Back to **View 4** (tick 13) → drill into chatbot | Chatbot Quality **Red**: hallucination **3.5 %** vs the 2 % High-risk band; sample invented answer beside a correct refusal | "A new HR policy nobody loaded into the KB — the bot started inventing answers; our eval set includes 3 deliberately unanswerable questions to catch exactly this." |
| 11 | 7:15 | **View 6** — point at ACT-001's badge | **AUTO-ESCALATED at t12**: SLA breached → RAI Council + CDAO notified (alert-log entry) | "The 48-hour clock ran out with no action — so it escalated itself; nothing silently slips." |
| 12 | 7:45 | At **t15**, click **Close with evidence** — this click **is** the trigger for the scripted t15 `CLOSE_ACTION` event (ACT-001/ACT-002/ACT-003) plus the retrain + KB-update events; **advance t15 → t18** | Heatmap flips Green; ACT-001/ACT-002/ACT-003 Closed with evidence links; realized AUC rejoins in green at t18; chatbot action closed **within** SLA | "Remediation closes with an evidence link, not a verbal 'we fixed it' — and one action escalated while the other closed on time: the queue shows both." |
| 13 | 8:45 | Open **View 7** (board narrative) | Board-ready summary: 2 Red episodes, 1 auto-escalation, 3 actions closed with evidence, mean-time-to-green | "This exact panel is what the board sees — red/amber items become action queues, not hidden spreadsheet gaps." |
| 14 | 9:30 | Press **RESET** live → tick 0, all Green | Instant return to baseline (< 2 s) | "Open-source today, Azure tomorrow — same registry, same thresholds, same views; only the engines swap. And everything you saw is synthetic and replayable, seed 42." |

### F.3 Likely audience questions (with suggested answers)

**Q1 — "Can we trust LIME? Why show two explainability tools?"**
LIME is local and can be unstable — the fidelity-vs-simplicity trade-off — and the UI says so on the tab itself. SHAP is the consistent, game-theoretic counterpart, and it is what the enterprise path uses (Azure ML Responsible AI dashboard). We show both deliberately: LIME for the per-customer story, SHAP for the defensible global view — so the team learns the difference before a regulator or the Council asks.

**Q2 — "When do we get real data / our real use cases in here?"**
Never in this demo — by design: no real True data, no PII, PDPA-clean (that's why it runs offline with no keys). Real telemetry is a deferred capability in the PRD core (§9 Deferred capabilities): each real feed onboards through the telemetry-contract adapter only after DPO sign-off, with the HR chatbot the likely first candidate. The point of today: the registry, thresholds, action queue, and views you just saw carry over **unchanged** — only the data source swaps from simulator to live feed.

**Q3 — "Are these thresholds and SLAs made up for the demo?"**
Partly inherited, partly demo defaults — and the UI is honest about which. **Only the hallucination band is inherited verbatim**: it's Sheet-3 SL#2.1 of our deployed RAI Deployment Checklist v2.0 (High-risk: < 1 % go-live / < 2 % continue / ≥ 2 % escalate). **Every other band** (groundedness, relevance, PII, latency, drift share, AUC) is a **demo default expressed in the same Sheet-3 band format** — proposal §10 sets thresholds per use case at onboarding, and the reliability defaults in particular are provisional pending the pilot. The SLAs (48 h / 5 wd / 15 wd / 30 wd with auto-escalation) come from the operating-model proposal §10–§11. So: one band is canon, the rest are sensible placeholders you tune per use case — in the config, never in code.

### F.4 If something breaks

1. **Any weirdness → RESET** (baked, < 2 s) and jump straight to the relevant snapshot (`SNAP-RED` recovers the second half of the demo in one click).
2. **App down → static export**: present from the **R-34** baked static snapshots (`GET /api/export/demo-snapshots` — per-tick Views 4/6/7 and the NannyML chart, saved to disk by `scripts/demo_reset` before the meeting).
3. **Never** debug live in the meeting; the closing line still works from the export: *"same registry, same thresholds, same views."*
## Appendix G — Enterprise-Swap Mapping (Option D -> Option A)

The demo runs the proposal's **§13.5 Option D** stack — **Langfuse, Evidently, NannyML** — plus **LIME + SHAP** explainability (from the verified reference implementation; SHAP is also the Azure Responsible-AI-dashboard path). The enterprise path is **Option A** (Azure — the working default pending ecosystem confirmation). Because every engine sits behind exactly one of the **three** adapter protocols (`LLMEvalAdapter`, `MLMonitorAdapter`, `ExplainAdapter` — Appendix E.1), the swap replaces adapter implementations, not the product. `ScenarioSource` is a separate, **non-engine** input interface and is **not** part of the swap.

| Layer | Demo (Option D — open) | Enterprise (Option A — Azure) | Swap mechanism |
|---|---|---|---|
| `LLMEvalAdapter` — LLM tracing + evaluation (judge + tracing; `TraceStore` sub-interface) | Langfuse stub (→ SQLite) / Langfuse cloud (traces + scores) + deterministic seeded LLM-as-judge | **Azure AI Foundry** observability (OpenTelemetry tracing into Application Insights) + **Foundry evaluators** (groundedness, relevance, coherence + custom; continuous sampled + scheduled eval) | New `LLMEvalAdapter` implementation (`azure_foundry`) returning the same `LaneResult` signal keys |
| `MLMonitorAdapter` — classical-ML drift + performance (Evidently drift + NannyML performance) | **Evidently** (data drift/quality) + **NannyML** (label-free performance via CBPE) | **Azure ML model monitoring** — data drift + prediction drift (JS, PSI, Wasserstein, KS, Chi-squared), data quality; model performance *(preview; requires ground-truth joined by ID — NannyML's label-free estimate has no direct Azure equivalent, note at swap time)* | New `MLMonitorAdapter` implementation (`azure_ml`) |
| `ExplainAdapter` — explainability (LIME + SHAP) | **LIME** (per-prediction, with instability caveat) + **SHAP** (global) | **SHAP / Azure ML Responsible AI dashboard** (SHAP is already the demo's global method — the swap drops LIME, keeps SHAP semantics) | New `ExplainAdapter` implementation (`azure_rai_dashboard`) |
| Storage *(infrastructure — not an adapter seam)* | SQLite + local `artifacts/` dir | **Azure Database for PostgreSQL** + **Azure Blob Storage** | Connection-string + storage-client change (ADR-1 kept the SQL portable) |
| **INVARIANT — does not change** | **Registry (Appendix B, exact fields + seed) · Sheet-3 thresholds + grading + rollup (Appendix C) · colour→severity map + SLA/auto-escalation action queue (C.3–C.4) · the 7 dashboard views + drill-downs · the scenario engine + `ScenarioSource` + scripts (Appendix A)** | *Same* | None needed — these sit **above** the three adapter interfaces and never import an engine directly |

**Why this makes the demo an honest preview of both options.** The proposal's tooling section is deliberately a two-option decision (ecosystem-native suite vs. open stack), and the honest market finding behind it is that *every* path is really "a classical-ML monitor plus a GenAI evaluation capability tied together by a telemetry spine" — no single pane exists. This demo embodies exactly that shape: two engine families, one control tower. Everything the team sees in the meeting — the registry, the Sheet-3 grading, the heatmap, the action firing with a 48-hour SLA, the recovery — lives *above* the adapter seam and is identical under Option D or Option A. What the demo proves is therefore not "we chose Langfuse/Evidently"; it is "the operating model runs, and the engine decision (§13) stays a genuinely open management choice — a swap behind three interfaces, not a rebuild." The open engines make the demo runnable today, offline, at zero cost and zero data risk; the same click-path is what an Azure-backed pilot would show.

---

*Provenance (non-normative — not a build dependency):* the threshold values, signal set, drift-injection mechanics, and engine wiring in these appendices were validated in a working reference implementation in the author's workspace (`life-os` repo, `tools/rai-monitoring-prototype/` — Streamlit, Python), and the registry/threshold/view definitions derive from the RAI operating-model proposal (§10–§13), `registry-schema.md`, and `control-tower-dashboard-prototype.md` in `work-work/projects/responsible-ai-operating-model/`. The build repo must not reference these paths.

