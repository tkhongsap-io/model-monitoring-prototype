# Control-Tower Dashboard Prototype

> Internal True / CP Group working draft.
> Created: 2026-07-06.

## Purpose

This is the first low-fidelity dashboard design for the AI Use Case Observability Control Tower. It should be possible to implement manually first, then migrate into BI, TPM, AI Reporting Tool, or platform telemetry later.

The dashboard is not a value-realization report. It is an AI assurance view.

## View 1: At A Glance

| Card | Initial value / rule |
|---|---|
| Total registered AI use cases | 130 from current COE update; replace with AI Reporting Tool / VRO source once linked |
| Production AI use cases | 38 from current COE update |
| In-development AI use cases | 36 from current COE update |
| Requirements-stage / not started | 40 from current COE update |
| High-risk cases missing DPA/control/RAI approval | 4 from current COE update |
| Cases missing risk assessment | 12 from current COE update |
| Pilot assurance set | 15 recommended pilot rows |
| Red / amber / unknown pilot items | Calculated from pilot scorecard |

## View 2: Portfolio Health

| Slice | What it shows | Why it matters |
|---|---|---|
| By lifecycle | Requirements, PoV, UAT, production, paused, retired | Shows where monitoring can be designed before launch versus retrofitted after launch. |
| By risk tier | High, medium, low, unknown | Shows where AI Council, DPO, and Security attention is needed. |
| By platform | Mity, Microsoft, internal, vendor, unknown | Avoids over-focusing on one platform. |
| By BU/domain | HR, Call Center, Network, Finance, CX, CVM/NBO, B2B, other | Makes owner gaps and domain concentration visible. |
| By health | Green, amber, red, unknown | Turns the portfolio into an action queue. |

## View 3: Pilot Health Table

| ID | Use case | Lifecycle | Risk | Health | Missing evidence | Next action | Owner | Due |
|---|---|---|---|---|---|---|---|---|
| P01 | HR Knowledge Base / leave-policy chatbot | PoV | Unknown | Amber | HR Q&A sign-off, latency KPI, privacy decision | Confirm Q&A set and user count | HR / project team | Unknown |
| P03 | True Connect + Mity platform assessment | Production + integration | Unknown | Red | System owner, security assessment, shared risk register | Run parallel True Connect and Mity assessment | Project team + Security | Unknown |
| P06 | Agents AI unintended-action controls | Unknown | Unknown | Red | Vendor evidence and action-test mapping | Request POCO evidence | Use-case owner | Unknown |
| P08 | NBA / NBO marketing engine | Production / active | Unknown | Amber | Engine-level grouping, owner, evaluation metrics | Regroup campaigns under one engine | NBA owner / VRO | Unknown |

The actual dashboard should show all pilot rows from `pilot-scorecard.md`.

## View 4: Monitoring Lane Heatmap

| Use case | Quality | Safety/security | Reliability | Drift/degradation | Feedback/action loop |
|---|---|---|---|---|---|
| HR chatbot | Amber | Amber | Unknown | Unknown | Amber |
| Call Center KB | Unknown | Amber | Unknown | Unknown | Unknown |
| True Connect + Mity | Unknown | Red | Amber | Unknown | Amber |
| A2BI hallucination | Amber | Unknown | Unknown | Unknown | Unknown |
| Agents AI | Unknown | Red | Unknown | Unknown | Amber |
| Network AI cases | Unknown | Unknown | Amber | Unknown | Unknown |

Use this view to see which monitoring lane is missing across the portfolio.

## View 5: Risk And Evidence Gaps

| Gap type | Example | Action rule |
|---|---|---|
| Risk tier unknown | Production use case exists but risk classification missing | Assign owner and due date for risk screening. |
| DPO / privacy status unknown | Customer-facing or employee-data use case with unclear DPO review | Escalate to DPO if personal data is likely. |
| Security assessment incomplete | True Connect and Mity integration | Track in shared risk register. |
| Readiness checklist missing | Agentic tool or generative AI workflow | Block production sign-off until evidence exists. |
| Monitoring plan absent | Existing production use case | Mark health `Unknown` until cadence and metrics exist. |

## View 6: Action Queue

| Priority | Trigger | Owner | Escalation |
|---|---|---|---|
| P0 | Red health on high-risk or production use case | Business owner + technical owner | Security / DPO / AI Council / CDAO |
| P1 | Missing risk tier or readiness evidence | Use-case owner | COE / VRO |
| P2 | Missing monitoring metric or threshold | Monitoring owner | COE |
| P3 | Watchlist item without scope | Business sponsor | VRO |

Every action row must include: issue, recommended action, owner, due date, escalation path, and evidence link.

## View 7: Board Narrative Panel

This panel should be the board-ready summary:

- One registry links AI Reporting Tool / VRO / TPM records to assurance evidence.
- Risk-based monitoring separates high, medium, low, and unknown cases.
- Named owners make validation and post-production action accountable.
- Red/amber/unknown items become action queues, not hidden spreadsheet gaps.
- The intelligence layer can become the operating backbone when platform telemetry matures.

## MVP Build Approach

1. Start as a manually maintained tracker for the 15 pilot rows.
2. Link each row to source evidence from AI Council, COE update, VRO, TPM, security assessment, or PoV documents.
3. Review weekly until the August 4 board update.
4. Use the pilot to define telemetry requirements for Mity, Microsoft, vendors, and internal systems.
5. Only then decide whether the dashboard should live in AI Reporting Tool, TPM, BI, a governance platform, or an AI platform dashboard.

