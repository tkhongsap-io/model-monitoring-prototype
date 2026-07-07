---
title: "Working Operating Playbook: RAI Operating Model"
created: 2026-07-06
updated: 2026-07-07
status: working-draft
version: v0.5 — four web-verified ecosystem options (Azure/AWS/Google/open); ecosystem-aligned tooling recommendation (Azure front-runner); prior v0.4 — first-meeting tone, 1-month evaluation, BU-owned gap closure, minimal resourcing ask
tags: [work/true, responsible-ai, ai-architecture, ai-monitoring, intelligence-layer]
---

# Working Operating Playbook: RAI Operating Model

> Internal working draft (v0.5). This is an operating playbook — how True runs AI governance day-to-day after the Accenture-supported phase — not a presentation. It **operates the existing RAI Council gate at portfolio scale**; it does not create a parallel framework. Where it requests new authority, the item is tagged *proposed — for CDAO confirmation*.

## Discussion — The Short Version (read this first)

> For the meeting. This page is the plain-language summary; every statement is backed by detail, evidence, and dates in §0–§17 below.

**Where we are.** Accenture set up True's Responsible AI (RAI) framework and assessed the first three AI use cases with it. That engagement is complete, and Accenture is off-boarded at the end of July. From now on, **True runs Responsible AI ourselves** — for the **131 AI use cases** already registered and for every new one to come. This document is the proposal requested on 6 July, covering the two actions: **(1) monitoring of deployed AI models**, and **(2) AI Architecture as part of the RAI Council** — aligned with our Mity / AI Intelligence Layer work so it applies to both existing and new use cases.

**1) Model monitoring — "how do we know our AI is still behaving?"** Today, once an AI use case goes live, there is no systematic check that it keeps working well. We propose: every live AI system gets a **named owner** and a simple **health status — Green / Amber / Red / Unknown** — reviewed on a schedule set by its risk level (high-risk weekly, medium monthly, low quarterly). Health is judged on five plain questions: *is it giving right answers · is it safe (no data leaks, no harmful outputs) · is it up and responding · is it getting worse over time · are user complaints acted on.* When something goes wrong there is a clear escalation path with deadlines — and, new, a **defined way to pause a misbehaving AI system**, which no one clearly holds today. For tools, the honest reality (web-checked against every vendor's own docs) is that **no cloud sells one product that monitors both chatbot-style AI and classic prediction models** — each gives you a drift monitor for classic models *plus* a separate quality/safety capability for GenAI, tied together by its own telemetry backbone. So the real decision is **which cloud we already run production on**, and we present **four options**: the native monitoring of **Microsoft/Azure**, **AWS**, or **Google** — whichever hosts our estate — or a **specialist open-source stack** (deepest AI-specific features, data stays fully in-house, but more systems for IT to maintain). A **~1-month hands-on evaluation** — first *confirming our production cloud*, then sourcing, setup, and testing on real use cases — decides with evidence. Our front-runner going in is **Azure**, because we already use it (Azure AI Foundry, existing Azure security/audit), but we confirm the ecosystem before committing.

**2) AI Architecture as part of the RAI Council — "design it right before we build."** Exactly as framed in the ask: the Council should table **governance, architecture, and implementation** together. We propose that as the RAI Council's standing agenda — **governance** (risk classification and approvals), **architecture** (is each new AI use case designed safely, on the right data and foundations — reviewed *before* build against a fixed checklist), and **implementation** (is what's live healthy — the monitoring above). Architecture reviews are prepared with the existing Architecture Forum — **no new committee** — and high-risk cases come to the Council for decision.

**3) Existing and new use cases — one journey.** Every **new** use case follows one 8-step path from idea to retirement — register → risk check → privacy review → architecture review → build → launch decision → monitoring → periodic re-review — **reusing the Council's existing forms** (risk questionnaire, privacy checklist, deployment checklist), not new paperwork. For **existing** use cases, the known gaps — **4 high-risk live systems** without complete approvals, **3 live systems** never risk-screened, **19 live systems** missing privacy checklists — are **owned by the responsible business units**, with owners and dates the Council has already set; we provide the visibility, templates, and follow-up so they close, with a status report ready for the **4 August board update**. We do not gate anyone's delivery on this — governance here is enablement, not a blocker.

**What we ask from this discussion — five directions:**

> This meeting seeks agreement on direction (endorsement at most) — not formal approvals. Those follow through the RAI Council and the 4 August board path once the direction is agreed.

1. **Endorse the operating-model direction** — including that someone must be able to pause a live AI system.
2. **Agree a ~1-month tooling evaluation** — first confirm which cloud already runs our production estate, then align monitoring to that cloud's native tools (Azure / AWS / Google) vs. a specialist open stack; front-runner: **Azure** (we already use it).
3. **Endorse starting monitoring + architecture review, production-first** — monitor the live use cases first, architecture-review the in-development ones; support business units to close known gaps in parallel, not block them.
4. **Resourcing** — one additional person to help with coordination; expert input (architecture, security, privacy) from existing teams.
5. **Make Architecture a standing RAI Council agenda item** — governance + architecture + implementation, every session.

*Details, evidence, owners, and dates follow: §0 is the dense one-page version of this discussion; §1–§17 are the playbook.*

## 0. Executive Summary & Direction Sought

**Where we are.** Per the RAI Council register (Council #3, 22 Jun 2026): **131 AI use cases** — 37 live, 36 in development, 13 cancelled, 3 on hold, 42 not started. Known gaps on systems **already serving users**: **4 high-risk live** cases operating without completed DPA review / control implementation / RAI checklist approval (incl. **AI Speaker** and **AI Pet**, both vendor-delivered by T3); **3 live** never risk-screened (Smart Accounting Ph.1, Jaidee Borrow credit score, AIS competitor churn score); **19 live** without a completed DPO checklist; **10 in-development** unscreened. *(The board narrative cites 130/38 — reconcile both to the Council register as the single count before Aug 4.)*

**The forcing events.** Accenture — who stood up the RAI framework and runs the gate today — **exits at the end of July**. The **board update on RAI/governance is Aug 4**. And the Council minutes show a structural gap: **there is no defined mechanism for pausing a live AI system** — when a vendor SoW slipped, the strongest available response was to *"escalate and recommend the use case to be blocked"* (Council #3, Action 7). §3 proposes that mechanism.

**First workload.** The visibility pilot starts now, and **in parallel** we support the responsible BUs in closing exactly these gaps (§14 — they own the fixes; the Council already set owners and dates); status board-ready by Thu 30 Jul. The four high-risk live cases: **AI Speaker**, **AI Pet**, **Proactive Fiber Cut Impact Prediction** (CNO — per the Council #2 register), and a fourth to be confirmed by name from the register in the wave-1 tracker (by Fri 10 Jul).

**What this playbook is.** How True operationalizes Responsible AI internally: **pre-deployment** (intake → risk classification → DPO review → architecture review → launch readiness) and **post-deployment** (monitoring → action queue → escalation → incident response → re-review), reusing the Council's existing instruments, with the Intelligence Layer (Mity) and the chosen monitoring platform as the technical backbone, and the **AI Use Case Observability Control Tower** as the portfolio view.

**Direction sought in this meeting** *(alignment / endorsement — formal approvals follow via the RAI Council and the board path once direction is agreed)*:

| # | Direction | Proposed | Detail |
|---|---|---|---|
| 1 | **Operating mandate & decision rights** — incl. that someone must be able to pause a live AI system, and a standard vendor suspension ("kill-switch") clause | Agree the direction of the §3 decision-rights table; formal confirmation follows via the RAI Council | §3 |
| 2 | **Tooling direction** — align to our production cloud's native monitoring (Azure / AWS / Google) or a specialist open stack | Run a **~1-month tooling evaluation** (confirm production ecosystem → source → setup → hands-on test); front-runner **Azure** unless the evaluation or the confirmed ecosystem says otherwise | §13 |
| 3 | **Start monitoring + architecture review (production-first)** | Endorse standing up both capabilities now — **monitor the live (production) use cases first** (risk-ranked; the ~10–15 pilot set is the first batch), **architecture-review in-development cases** before launch; support the **BU-owned** closure of the known backlog in parallel — enablement, not a blocker | §14 |
| 4 | **Resourcing** | **One additional coordination person** (no new team); expert input from existing teams per case; tooling budget estimated by the evaluation | §15 |
| 5 | **Architecture as part of the RAI Council** | Architecture as a **standing pillar of the RAI Council agenda** — reviews prepared via the existing Architecture Forum, tabled at the Council for High-risk cases | §8 |

## 1. Objective & Scope

Operationalize True's Responsible AI framework after the Accenture-supported phase, per the CDAO's ask: (a) **AI model monitoring** for deployed use cases, and (b) **AI architecture review** as part of the RAI Council process — moving from consultant-led assessment to an internal operating model for existing and new AI use cases.

> Every AI use case has an owner, a risk tier, an architecture-review path, a launch-readiness decision, a monitoring plan, an escalation path, and an action loop — and missing evidence is visible as **Unknown**, never hidden.

**In scope:** the operating loop above, for all AI at True — GenAI/LLM, classic ML (prediction, recommendation, CVM/next-best-action, scoring), vendor-supplied AI, and workflow AI — on any platform (Mity, Microsoft, internal, vendor).
**Out of scope:** the legal/policy layer — owned by Legal (K.Kounmoudri); this playbook *requests* legal deliverables (the vendor clause set, §16) but does not own policy — and business-value tracking (owned by VRO; §2 boundary).

## 2. Fit With True's Existing Governance

This playbook **reuses the instruments True already runs** — it changes who operates them (internal, post-Accenture) and adds the missing pieces (decision rights, monitoring, incident response). Naming: the governance forum is the **RAI Council** (Responsible AI Council). Some meeting artifacts abbreviate it as "AI Council" — same forum.

| Lifecycle stage | Existing instrument (reused as-is) | What this playbook adds |
|---|---|---|
| Registration | **AI Reporting Tool / VRO / TPM record** = source of truth | Assurance overlay keyed on the source record ID (`registry-schema.md`) — never a second registry |
| Risk classification | **7-question Risk Screening Questionnaire** + its scoring rubric | Enforcement hooks (§7) and `Unknown` as a visible operating status |
| Privacy | **DPO Data Privacy Checklist** — completed **before design** (existing rule) | Tracked as an explicit lifecycle stage with an SLA (§6) |
| Controls & evidence | DPA-review recommended controls; security assessment | **Validation** tracking — controls confirmed implemented, not just claimed (the AI Speaker A3 SIEM / R3 data-access lesson) |
| Launch gate | **RAI Deployment Checklist v2.0** + Sheet-3 Performance & Risk Criteria | Decision protocol + hard gates incl. signed SoW/DPA (§9) |
| Architecture | **Architecture Forum** (existing) | AI-specific review checklist + vendor variant, hosted there (§8) |
| Value | **VRO** | Boundary: the control tower tracks *assurance*, never value — value stays linked, not duplicated |
| Budget | **>5M THB business case → CFO gate** | Unchanged; referenced at intake |

**External anchoring (defensibility):** the lifecycle maps onto **NIST AI RMF** (Govern = §3; Map = §7; Measure = §10; Manage = §11) and the management-system pattern of **ISO/IEC 42001**; privacy obligations follow **Thai PDPA** (DPO checklist before design; breach notification to the regulator within 72 hours of awareness; cross-border transfer safeguards). A clause-level mapping is a §16 output, not a blocker.

## 3. Decision Rights & Operating Roles *(proposed — for CDAO confirmation)*

The single biggest operating gap today: the Council can *recommend* blocking, but no role is empowered to **act**. Proposed decision rights:

| Decision | Proposed holder | Mechanism | Today |
|---|---|---|---|
| Confirm risk tier | COE RAI coordinator proposes (rubric result); **RAI Council confirms High** | Questionnaire score + Council minute | Rubric exists; confirmation implicit |
| Approve **Low/Medium** to production | Business owner + technical owner + COE sign-off | Launch-readiness protocol (§9) | Unclear |
| Approve **High** to production | **RAI Council** | Deployment Checklist complete + evidence in the record | Council reviews; authority implicit |
| Conditional go | As above + named condition owner + due date | Auto-escalation on breach (§11 SLAs) | Conditions drift (e.g. SoW due dates passed without consequence) |
| **Pause / restrict a live system** | **COE coordinator proposes → CDAO (or standing RAI Council-chair delegate, §17) approves within the S1 clock (§11) → IT executes** (internal) / **vendor suspension clause invoked** (vendor) | Incident runbook (§11) | No defined mechanism — Council can only "escalate and recommend… blocked" (Council #3, Action 7) |
| Kill / retire | RAI Council recommendation → CDAO decision | Re-review stage (§6, stage 8) | n/a |
| Budget >5M THB | CFO gate | Existing | Exists |

**Run roles (RACI-lite):**

| Role | Responsibility |
|---|---|
| **RAI Council** (chair: TBC) | Confirms High risk tiers; approves High-risk launches; receives escalations; reviews portfolio KPIs |
| **COE RAI coordinator** (Ta) — performs the checklist's **"AI Transformation Lead"** duties | Runs the gate + register; reviews checklist completeness and presents to the Council; chases evidence; operates the control tower; proposes pauses; reports KPIs |
| **Architecture Forum** | Hosts AI architecture reviews (§8) |
| **Security / DPO** | Security assessment; privacy checklist; control validation; incident roles (§11) |
| **Business owner** (per use case) | Workflow fit, acceptance, value; first escalation point |
| **Technical owner** (per use case) | Implementation, support, fallback, telemetry |
| **Monitoring owner** (per use case) | Cadence reviews, action follow-up — may equal technical owner for Low risk |
| **IT platform** | Capture layer (gateway / endpoints / SIEM), tooling operation (§13) |
| **Vendor** (where applicable) | Contractual evidence, telemetry export, suspension obligation (§13.1) |

**RAI Council operating mechanics** *(proposed — chartered together with the decision-rights confirmation)*:
- **Chair** — the Deployment Checklist already names a **Council Chair** who signs off deployment approvals; confirm the holder (recommend: CDAO or a named delegate).
- **Cadence** — biweekly sessions (the 5 Jun / 22 Jun pattern), plus an **async e-vote path** so 48-hour Critical escalations (§11) and the ≤10-working-day turnaround KPI (§15) are serviceable between sessions.
- **Quorum** — Chair + Security + DPO + the affected BU's business owner.
- **Escalation above the Council** — to the **AGC**, per the checklist's existing escalation log.
- **Role mapping** — this playbook adds no new roles: the COE RAI coordinator performs the checklist's "AI Transformation Lead" duties; Use Case Owners complete evidence exactly as the checklist prescribes.

## 4. Accenture Handover — complete by Fri 24 July

Accenture currently facilitates the Council, keeps the register, and chases the gate. Their operationalization support is framed as complete for the first three assessed use cases — **but as of 6 Jul the pack shows AI Speaker checklist items still awaiting True-side confirmation** (risk-screening / DPO-review confirmation; controls partial), and the Council's accept-or-block **reconvene (week of 29 Jun) has no recorded outcome in the pack** — confirm and record both as the first wave-1 item (§14). **The operating knowledge must land inside True before exit** (and all Accenture documents linked into the COE doc — standing requirement).

| Artifact / role | Current keeper | True custodian (proposed) | Done when |
|---|---|---|---|
| Use-case register (131) | Facilitator (Akash) | COE RAI coordinator | Register exported to the governance library + linked in COE doc |
| Risk Screening Questionnaire template + **scoring logic** | Accenture | COE RAI coordinator | Template + rubric stored and documented (§7) |
| DPO Data Privacy Checklist template + tracker | DPO office | DPO office (confirm) | Confirmed + linked |
| RAI Assessment workbook pattern (e.g. AI Speaker v2.0) | Accenture / vendor | COE RAI coordinator | Blank template extracted + stored |
| RAI Deployment Checklist v2.0 + **Sheet-3 thresholds** | Accenture | COE RAI coordinator | Template + thresholds table stored (§10) |
| Evidence store (today: OneDrive zip drops) | Ad-hoc | Governance SharePoint library (§11) | Evidence migrated; links resolve |
| Gate-driver / chase role (the "Action: K.Nakhun…" pattern) | K.Nakhun *(confirm side)* | COE RAI coordinator | Open actions transferred with owners/dates |
| Council facilitation | Akash | COE RAI coordinator | Ta facilitates the next Council with Accenture shadowing |

Plus: **2–3 shadowing sessions** on live gate cases before exit; a final KT sign-off noting anything not handed over.

## 5. Operating Principles

| Principle | What it means in practice |
|---|---|
| Reuse existing gates | Extend the RAI Council instruments; never build a parallel bureaucracy or second registry. |
| Start with the AI lifecycle | Manage each use case from intake to re-review (§6) — the stages are the operating system. |
| Make ownership explicit | Every use case: business owner, technical owner, monitoring owner. No orphans. |
| Make missing evidence visible | `Unknown` is a first-class status — never blank, never hidden. |
| Use risk-based depth | Low-risk moves fast; High-risk gets stronger review, monitoring, and Council visibility. |
| Governance enables delivery | Architecture review helps teams ship safely — it is not only a blocking gate. |
| Monitoring must create action | Every **Red and critical-`Unknown`** produces an owner-assigned action with a due date and SLA; **Amber is watch-listed** and converts to an action if it persists two consecutive reviews (§10). |
| Evidence lives in a system of record | Decisions and evidence go to the governance library (§11) — not inboxes or zip files. |

## 6. End-to-End AI Lifecycle

Eight stages. Each row names its **existing instrument** — nothing here is a new form for its own sake. Vendor-supplied AI follows the same stages with the vendor variants noted in §8/§9/§13.

| # | Stage | Owner | Instrument | Output | Decision / next |
|---|---|---|---|---|---|
| 1 | Intake / registration | Business owner | AI Reporting Tool / VRO / TPM record + assurance overlay (§7) | Registered use case with source ID | To risk classification |
| 2 | Risk classification | COE RAI coordinator (proposes) | 7-question Risk Screening Questionnaire + rubric | Risk tier (High confirmed by RAI Council) | Route by tier |
| 3 | **DPO / privacy review** | DPO + business owner | DPO Data Privacy Checklist — **before design** | Privacy status (incl. "not required" ruling) — **SLA: ruling ≤ 10 working days from complete submission** *(proposed)* | Proceed / conditions / stop |
| 4 | Architecture review | Architecture Forum | AI architecture checklist (§8) | Review decision + conditions | Approved / conditions / blocked / escalate |
| 5 | Build / configure | Technical owner | Approved design + DPA-recommended controls | Working solution + **validated** controls | To launch readiness |
| 6 | Launch readiness | Business + technical owner + COE (+ RAI Council for High) | RAI Deployment Checklist v2.0 + hard gates (§9) | Launch decision | Go / conditional / no-go / escalate |
| 7 | Post-deployment monitoring | Monitoring owner + COE | Five lanes + thresholds + cadence (§10) | Health status + action queue | Continue / remediate / escalate / pause |
| 8 | Re-review / change control | COE → Architecture Forum / RAI Council | Change triggers (§11) | Updated approvals | Continue / rework / restrict / retire |

## 7. Intake & Risk Classification

**Intake is a thin overlay, not a second registry.** Each use case is keyed on its **source-of-truth record ID** (AI Reporting Tool / VRO / TPM) per `registry-schema.md`; business-context fields (initiative, value, owner) are *already captured in the Value Realization framework* — the overlay adds only assurance fields (owners triple, platform/model path, data sensitivity flag, lifecycle status).

**Classification uses the existing rubric verbatim** — the 7-question Risk Screening Questionnaire (function; users; autonomy; prohibited-use patterns; worst credible failure impact; risk surface; data sensitivity), where each answer maps to High=3 / Medium=2 / Low=1 and:

> **Count(High) ≥ 2 → High** · else **Count(High)=1 and Count(Medium) ≥ 3 → Medium** · else **Low** · **Override: any PII → High.**

`Unknown` is an **operating status**, not a fifth tier: a use case missing classification or evidence is treated at Medium-or-higher scrutiny and chased until classified (registry cadence, §10).

**Enforcement (fixing voluntary intake).** Today registration is voluntary and demonstrably leaks (3 live cases never screened; the 3 Jul 2026 security review found True Connect had operated **without any security assessment**). Proposed hooks:
- **No TPM record / PO / production access without a use-case ID and risk tier** — wired into the existing IT demand-management and procurement checkpoints.
- **Quarterly shadow-AI discovery sweep**: procurement contracts, SSO/app inventory, security scans, expense lines → unregistered AI lands in the register as `Unknown` and gets chased.

## 8. Pre-Deployment AI Architecture Review — Architecture as Part of the RAI Council

Per the CDAO's ask — *"AI Architecture and how it could become part of RAI Council… this way we table in this council both governance, architecture and implementation"* — **Architecture becomes a standing agenda item at every RAI Council session**, alongside governance and implementation/monitoring. Reviews are prepared at the **existing Architecture Forum** — extended with the AI-specific checklist below — and tabled at the Council; the Council's decision is **required for High-risk cases**. No new body is created.

| Review area | Required questions | Output |
|---|---|---|
| Business fit | What workflow does this improve? Success measure? Who signs off? | Business fit confirmed |
| Data & knowledge | Sources? Owners? Current, complete, permissioned? | Data / KB readiness view |
| Model choice | Which model/vendor/route, why suitable, what fallback? | Model decision note |
| Architecture pattern | RAG, agent, workflow, API/MCP, embedded, prediction, hybrid? | Pattern decision |
| Access control | Who can use it? Role-based data visibility? Source-permission inheritance? | Access approach |
| Guardrails | What must the AI refuse, restrict, escalate, or require approval for? | Guardrail requirements |
| Human-in-the-loop | Where is approval, review, or override required? | Human-review design |
| Integration | Systems, APIs, tools, MCP servers, workflows connected? | Integration map |
| Logging & monitoring | What telemetry exists after launch (§12 contract)? | Monitoring plan |
| Fallback & rollback | Behavior on failure, low confidence, or detected risk? | Fallback / rollback plan |
| Ownership | Who supports, fixes, improves, monitors? | Owner model |

**Vendor variant** (when internals are not inspectable — the AI Speaker / AI Pet pattern): review **attested vendor evidence** instead — architecture documentation, algorithm/content and bias test reports, security white papers, SLA, O&M access-control and audit-log evidence — plus the **contractual monitoring obligations** in §13.1. Vendor evidence gaps are review findings, not waivers.

**Outcomes:** Approved · Approved with conditions (tracked, §11 SLAs) · Blocked pending remediation · Escalate (RAI Council / Security / DPO / CDAO).

## 9. Launch Readiness

**The instrument is the existing RAI Deployment Checklist v2.0** (controls & evidence attestation + Sheet-3 Performance & Risk Criteria). This section defines the **decision protocol** around it, plus hard gates that recent cases proved necessary:

**Hard gates — no Go while any is open:**
1. **Signed SoW / DPA with any vendor** (both current High-risk live cases ran with unsigned SoWs).
2. **DPO checklist complete** (or a documented "not required" ruling).
3. **DPA-recommended controls validated as implemented** — confirmed by Security/Architecture, not self-attested (the A3 SIEM / R3 data-access lesson).
4. **Monitoring owner named + monitoring plan active from day one** (§10).
5. **Vendor telemetry + suspension clause in contract** for vendor-supplied AI (§13.1).

**Decisions:** **Go** (all controls green or formally risk-accepted at the right level) · **Conditional go** (gaps documented with owner, due date, auto-escalation on breach) · **No-go** (material risk / missing owner / failed critical test) · **Escalate** (business wants to proceed against High or unresolved risk → RAI Council, CDAO if needed).

## 10. Post-Deployment Monitoring

### Monitoring dimensions (what we watch)

| Dimension | What to monitor | Example signals |
|---|---|---|
| Quality | Correct, useful, grounded outputs | Accuracy, task success, hallucination rate, citation correctness, SME pass rate |
| Safety / security | Privacy, access, policy, security risk | PII exposure, prompt-injection attempts, unauthorized access, unsafe output, policy violations |
| Reliability | Consistent operation in the real workflow | Latency, uptime, timeout rate, fallback rate, failed tool/API calls |
| Drift / degradation | Getting worse over time | Quality trend, stale KB, model/prompt regression, data/behavior shift |
| Feedback / action loop | Signals turning into improvements | User feedback, SME corrections, tickets, incident reviews, content backlog |

**Minimum monitoring focus by use-case type** (the registry's lane fields implement this):

| Use case type | Minimum focus |
|---|---|
| RAG / knowledge chatbot | Answer accuracy, citation correctness, retrieval quality, unsupported-answer handling, stale content, feedback |
| Agent / tool-using AI | Tool-call success, unsafe-action attempts, approval flow, execution trace, rollback path, incident count |
| Recommendation / decision support | Recommendation quality, business acceptance, bias/fairness checks, override rate, outcome tracking |
| Prediction model | Model performance, data drift, false positives/negatives, retraining need, business impact |
| Workflow automation | Task completion, exception rate, manual intervention, error rate, audit trail |
| Customer-facing AI | Safety, privacy, service quality, escalation, complaint signals, brand/reputation risk |

### Starter thresholds *(inherited, not invented)*

Adopt the **Deployment Checklist Sheet-3 "Performance & Risk Criteria"** — its actual bands are **Go-Live Threshold · Continue in Production · Issue/Escalate** — as portfolio defaults, tuned per use case at onboarding. Worked example — hallucination rate (Sheet-3 SL#2.1), by risk tier:

| Signal | Go-live bar (§9 launch gate) | **Green** — continue in production | **Red** — issue / escalate |
|---|---|---|---|
| Hallucination rate — High-risk case | < 1% | < 2% | ≥ 2% |
| Hallucination rate — Medium | < 2% | < 3% | ≥ 3% |
| Hallucination rate — Low | < 3% | < 5% | ≥ 5% |

**Amber is behavioral, not a threshold band**: a signal trending toward Red across two consecutive reviews, missing/stale monitoring data, or an owner/action gap. (This keeps Sheet-3's "Continue in Production" band Green — e.g. a High-risk case at 1.5% hallucination operates normally, exactly as the Council cleared A2BI — instead of flooding the action queue.)

**Color → action-severity map (drives §11 SLAs):**

| Signal state | Action severity |
|---|---|
| Red on a High-risk case | **Critical** (48 h) |
| Red on Medium / Low | **High** (5 wd) |
| Amber persisting 2 consecutive reviews | **Medium** (15 wd) |
| Critical `Unknown` (High-risk case lacking owner, classification, or telemetry) | **High** (5 wd) |

Measurement per Sheet-3 (human eval, ≥200 outputs/period); for weekly High-risk cadence this runs sample-based with a monthly full evaluation *(proposed — evaluation-validated)*. Reliability defaults (latency, uptime, fallback) are **provisional pending the pilot** and set per use case at onboarding.

### One cadence table *(supersedes earlier drafts in the pack)*

| Risk tier | Minimum cadence | Review |
|---|---|---|
| High | **Weekly**, near-real-time alerts for critical signals where telemetry allows | Owner + COE; Security/DPO/RAI Council where relevant |
| Medium | **Monthly** with sampled quality checks | Owner + COE |
| Low | **Quarterly** (minimum six-month confirmation) | Owner attestation + COE spot check |
| Unknown | Reviewed **monthly until classified** | COE chases the classification owner |
| *Pilot (all rows)* | *Weekly from now — **manual, registry-driven** until telemetry lands post-evaluation (§14) — through Aug 4, then risk-based* | Per board-pack decision |

## 11. Action Queue, Escalation & AI Incident Response

### Action queue with SLAs *(new — closes the "due date passed, nothing happened" hole)*

Every **Red and critical-`Unknown`** produces an action; Amber is watch-listed and converts on persistence (per the §10 color→severity map; fields per `registry-schema.md`). **Closure SLAs:**

| Severity | Close within | On SLA breach |
|---|---|---|
| Critical | 48 h | Auto-escalate to RAI Council + CDAO notification |
| High | 5 working days | Auto-escalate one level (owner → business owner → Council) |
| Medium | 15 working days | COE chases; flagged in weekly review |
| Low | 30 working days | Batch-reviewed monthly |

An action whose due date passes **escalates automatically** — it cannot silently slip (as the vendor-SoW deadlines did).

### Escalation triggers

| Trigger | Response |
|---|---|
| PII leakage or unauthorized access | Incident runbook S1 — Security + DPO immediately |
| High-risk case missing owner or monitoring | RAI Council / COE |
| Hallucination / wrong-answer threshold breached (§10) | SME review + remediation |
| Citation / retrieval quality drop | KB owner + technical owner |
| Latency / API failures affecting workflow | Technical owner |
| Repeated unsafe tool-call attempts | Disable tool, tighten guardrails, or require human approval |
| Major model / vendor / data / prompt / workflow change | Re-review (stage 8): architecture + RAI |

### AI incident runbook *(one page, proposed)*

| Severity | Definition | Clock & mandatory steps |
|---|---|---|
| **S1** | PII breach, safety harm, unsafe autonomous action, security compromise | Containment **proposed by the COE coordinator, approved per §3 within the clock, executed by IT (internal) or vendor suspension (§13.1)**. Security + DPO engaged at once. **PDPA: notify the regulator within 72 h of awareness** where personal-data breach criteria are met. CDAO informed same day. |
| **S2** | Sustained wrong answers on a High-risk case, material reliability outage, policy-violation pattern | Pause or restrict per §3; vendor RCA within 5 working days (the AI Speaker 2h12m outage of 29 Apr set the precedent — vendor delivered a formal fault report); fix-forward plan owner-assigned |
| **S3** | Degradation trends, recurring Amber items | Action queue with SLAs; monthly review |

Vendor systems: pausing means **invoking the contractual suspension clause** (§13.1) — this is why the clause is a launch hard-gate. **Interim containment (until the clause set lands in a vendor's contract):** blocking the service's integration points at True's network/API edge plus a named vendor commercial escalation contact — defined per case in the wave-1 tracker, because today an S1 on a vendor case whose SoW is unsigned has no contractual pause lever at all. Every S1/S2 ends with a post-incident review that feeds stage-8 re-review. AI incidents follow the **existing IT security-incident process** with these AI-specific severities layered on — one process, not two.

### Evidence system of record

All gate decisions, checklists, test reports, and incident reviews live in a **versioned governance library** (SharePoint) with an immutable decision log and retention ≥ 5 years *(proposed — confirm with Legal/DPO)*. Today's OneDrive zip-drop pattern ends with the §4 handover; action-queue `evidence_link`s must resolve to the library.

## 12. Intelligence Layer (Mity) as Technical Backbone

| Capability | Operating role |
|---|---|
| AI Knowledge Base | Grounded answers, source traceability, citation monitoring, content ownership |
| AI Orchestrator | Routing visibility, workflow control, agent decision tracking |
| AI Agents Hub | Agent lifecycle, ownership, reuse, versioning, governance |
| AI Services Layer | Reusable APIs, tools, MCP interfaces |
| Guardrails & Policy Engine | Safety, compliance, refusal, approval enforcement |
| Observability & Logging | Usage, latency, errors, model route, safety flags, audit logs |
| Feedback Loop | User feedback, SME correction, improvement backlog |
| Cost & Latency Optimizer | Model routing, token cost, service-level performance |

**Plane arbitration** *(new)*: for use cases running **on Mity**, Mity's policy engine **enforces** runtime guardrails; the monitoring platform (§13) **observes and independently verifies**. One policy source of truth — guardrail configurations are versioned in the registry, so enforcement and monitoring can't diverge silently.

**Minimum telemetry contract** (unchanged from v0.1 — use-case ID + owner; model/vendor/route + version; prompt/workflow version; volume + users; latency/timeout/error/fallback; quality or sampled-review result; citation/retrieval quality; safety filter results + violations; escalation/override/correction events; feedback; cost; incident/action status). **It applies to every use case regardless of platform**: Mity emits it natively where available; non-Mity internal systems emit it via OpenTelemetry; **vendor systems meet it contractually** — telemetry export or SIEM log forwarding (§13.1). A use case that cannot meet the contract is `Unknown` health, and that is a finding.

## 13. Monitoring Platform & Tooling — Ecosystem Options *(decision for management)*

**Honest market premise (web-verified 2026-07-07 against each vendor's own documentation):** **no cloud — Azure, AWS, or Google — and no single open-source tool covers the full monitoring lifecycle across *both* GenAI and classic ML in one native pane.** On every platform, "monitor both model classes" means a **classical-ML drift monitor** *plus* a **separate GenAI evaluation / guardrail / logging capability**, tied together by that platform's **telemetry spine** (Azure Monitor, AWS CloudWatch, or Google Cloud Monitoring). So the real decision is not "which tool is best" but **which ecosystem already hosts our production estate** — then, within it, an integrated cloud suite vs. a composed open stack. Because Ta joined the team this month, **confirming that production ecosystem is step 1 of the evaluation (§13.7)**, not an assumption. Four options follow; each capability below is drawn from vendor docs, and where a capability is Preview / not-yet-GA or a common misconception, it is flagged as such rather than asserted.

### 13.1 Where monitoring plugs in — three capture patterns

| Pattern | Capture point | Applies to |
|---|---|---|
| **GenAI / LLM** | AI gateway + app instrumentation (OpenTelemetry GenAI conventions) | Chatbots, RAG, agents — Mity and non-Mity |
| **Classic ML** | Model-serving endpoint / inference logs | Prediction, recommendation, CVM/NBO, scoring |
| **Vendor / external AI** | **Contractual**: telemetry export *or* SIEM log forwarding; model-change notification; attested evidence on a cadence (test reports, accuracy method); audit rights; **suspension/kill-switch obligation** | AI Speaker, AI Pet, future vendor AI — regardless of ecosystem choice |

The vendor pattern is a **contracting standard** (Legal + procurement adopt the clause set) — it exists because our two flagship High-risk cases run on vendor infrastructure that **no monitoring platform, cloud or open, can instrument directly**. (The un-started A3 SIEM integration on AI Speaker is exactly this pattern's first live application.)

### 13.2 Option A — Microsoft / Azure *(enterprise default; current front-runner)*

| Need | Service (verified capabilities) |
|---|---|
| GenAI tracing / performance | **Azure AI Foundry Observability** — OpenTelemetry distributed tracing (LLM calls, tool calls, agent decisions) into Azure Monitor Application Insights; latency, token/cost, error rates |
| GenAI quality / eval | **Azure AI Foundry evaluators** (groundedness, relevance, coherence, fluency, tool-call accuracy, task completion + custom) — run as **continuous sampled evaluation of live traffic** *and* **scheduled evaluation to detect drift over time** |
| GenAI safety / red-teaming | **Azure AI Content Safety** (harmful content, prompt-attack, PII) + **scheduled AI red-teaming** (built on Microsoft's PyRIT) |
| Classic ML drift / quality | **Azure ML model monitoring** — data drift + prediction drift (Jensen-Shannon, PSI, Wasserstein, KS, Chi-squared), data quality (null-rate, type-error, out-of-bounds), **feature-attribution drift** *(preview)* |
| Classic ML performance | **Azure ML model performance** *(preview)* — accuracy/precision/recall (or MAE/MSE/RMSE); **requires ground-truth ("actuals") joined by ID** |
| Classic ML fairness / explainability | **Azure ML Responsible AI dashboard** |
| Telemetry spine + alerts | **Azure Monitor + Application Insights** — dashboards + threshold alerts for both model classes |
| Feedback / retraining loop | **Azure Event Grid** — a threshold breach can trigger a retraining job / CI-CD |
| LLM gateway (optional) | **Azure API Management** GenAI policies |

**For:** one governance plane inherited from True's existing Azure RBAC/audit/retention; nothing to self-host; covers **both** model classes; fastest integration on an Azure/Eko estate; vendor support and SLAs; the retrain loop is a native Event Grid pattern.
**Against:** it is honestly **two products sharing Azure Monitor** (Azure ML for classic, Foundry for GenAI), not one unified pane; performance + attribution monitoring are **Preview**; performance monitoring **needs ground-truth data**; shallower LLM-native ergonomics (prompt management, dataset curation) than specialist tools; consumption cost at portfolio scale; **Thai-language quality of built-in evaluators unproven** (evaluation item); residency depends on Azure region; lock-in (mitigated by OpenTelemetry).
**"Deployed-elsewhere" caveat:** out-of-box, auto-collected monitoring applies **only to Azure ML online endpoints**. For a model served anywhere else, monitoring is still possible but **you must pipe its production data in yourself** — register it as an Azure ML data asset, keep it refreshed, and supply a custom preprocessing component. There is **no auto-discovery** of externally hosted models (a common misconception).

### 13.3 Option B — AWS *(if production runs on AWS)*

> **Time-sensitive caveat, verified 2026-07-07:** Amazon **SageMaker Model Monitor** (the managed classic-ML monitor) is **closing to new customers on 2026-07-30**. AWS's own stated replacement is the **open-source SageMaker monitoring pattern (Evidently + MLflow) + CloudWatch + QuickSight**. So the AWS option is **not** "plug into Model Monitor" — it is **CloudWatch as the spine** with SageMaker Clarify, the OSS monitoring pattern, and Bedrock around it. (If True is already a Model Monitor customer, it may continue using it.)

| Need | Service (verified capabilities) |
|---|---|
| Telemetry spine + alarms + dashboards | **Amazon CloudWatch** — the model-agnostic metrics/alarms/dashboards layer any model can publish to; **Amazon QuickSight** for governance/exec dashboards |
| Classic ML drift / quality | Historically **SageMaker Model Monitor** (data quality, model quality, bias drift, feature-attribution drift — **tabular only**, SageMaker-endpoint-centric); **for new build, AWS's recommended pattern is open-source SageMaker monitoring (Evidently/MLflow) → CloudWatch** *(see the sunset caveat above)* |
| Classic ML bias / explainability | **Amazon SageMaker Clarify** (bias detection + SHAP feature attribution) |
| GenAI safety / guardrails | **Amazon Bedrock Guardrails** — content filters, denied topics, PII redaction, and a **contextual-grounding (hallucination) check** with confidence thresholds |
| GenAI eval | **Amazon Bedrock Evaluations** — **offline / on-demand** (LLM-as-a-judge, programmatic metrics, and **RAG evaluation** for Knowledge Bases); *not* a continuous production monitor |
| GenAI logging | **Bedrock model-invocation logging** → CloudWatch Logs / S3 (off by default) |
| Feedback / retraining loop | **Amazon EventBridge + Lambda + SageMaker Pipelines** (scheduled drift job → alert → retrain) |

**For:** CloudWatch is a genuinely model-agnostic spine (any model, anywhere, can publish to it); mature classic-ML tooling via Clarify + the OSS pattern; Bedrock covers GenAI guardrails + evaluation + logging; strong retrain automation.
**Against:** the flagship managed monitor (**Model Monitor**) is **sunsetting for new customers** — the go-forward path is more assembly (CloudWatch + OSS Evidently/MLflow) than a turnkey suite; **no native continuous "LLM-quality drift" monitor** (GenAI = guardrails + offline eval + logging, stitched together); more moving parts than Option A on an Azure estate.
**"Deployed-elsewhere" caveat:** Model Monitor's automatic data capture is a feature of **SageMaker real-time endpoints only**. A model served anywhere else must have its inference records **emitted to S3 by you**, then scheduled monitoring/processing jobs (often bring-your-own-container) run over them. "Point Model Monitor at any endpoint" is **false** — CloudWatch + a custom drift job is the model-agnostic route.

### 13.4 Option C — Google Cloud / Vertex AI *(if production runs on GCP)*

| Need | Service (verified capabilities) |
|---|---|
| Classic ML drift / skew | **Vertex AI Model Monitoring** — training-serving skew, feature/prediction drift, and (with Explainable AI) feature-attribution drift (Jensen-Shannon divergence / L-infinity distance) |
| Classic ML — models **outside** Vertex | **Vertex AI Model Monitoring v2** monitors models on **any serving infra, including outside Vertex** (GKE, Cloud Run, multi-cloud/hybrid) via a **referenced model** in Vertex Model Registry — **the strongest "deployed-elsewhere" story of the three clouds**, *but* **verify current GA status before business-critical / PII use** (it was Preview at announcement — GA as of mid-2026 unconfirmed) |
| GenAI eval | **Gen AI evaluation service** — **offline** eval (LLM-as-a-judge PointwiseMetric/PairwiseMetric; ROUGE/BLEU; agent eval); *not* continuous production monitoring |
| GenAI safety / guardrails | Configurable **safety / content filters** (harm categories with tunable blocking thresholds; probability/severity scores) |
| GenAI ops metrics | **Model Observability** dashboard + Cloud Monitoring — request rate, token throughput, latency (incl. first-token p50/p95/p99), error rates — **operational, not content-quality/drift** |
| Telemetry spine + alerts | **Cloud Monitoring** alerting policies + custom dashboards |

**For:** **v2 model monitoring genuinely covers externally/anywhere-deployed models** (directly answers "the model is deployed elsewhere"); clean drift statistics; unified Cloud Monitoring alerting.
**Against:** **v2 GA status unconfirmed** — Preview at launch, so don't yet rely on it for PII/business-critical without checking; GenAI side is **evaluation (offline) + safety filters + operational metrics**, with **no native GenAI output-quality drift monitor**; smallest overlap with True's current (Azure-leaning) skills/estate.

### 13.5 Option D — Open / best-of-breed *(innovation-first / residency-first; also composes with any cloud above)*

Composed because no single tool — cloud or open — covers the lifecycle. Notably, this stack **is AWS's own recommended replacement** for the sunsetting Model Monitor, so it is an **overlay on any ecosystem**, not only an Azure alternative.

| Need | Tool (verified license/scope) |
|---|---|
| GenAI tracing, eval, prompt mgmt, feedback | **Langfuse** — **open-source, self-hostable**; LLM/GenAI observability (OpenTelemetry-based) — *variant: **LangSmith** only if agent dev standardizes on LangChain/LangGraph; note **LangSmith is commercial / closed-source**, self-host only under an enterprise licence → residency caveat* |
| GenAI evals in CI | **Ragas + DeepEval** (OSS) |
| GenAI safety / guardrails | **NeMo Guardrails** (OSS) — or keep the serving cloud's content-safety service (pragmatic hybrid) |
| Classic ML drift + data quality (+ LLM evals) | **Evidently** (OSS, **Apache-2.0**; covers **both** classic-ML drift/quality **and** LLM evals — the closest single OSS tool to spanning both) |
| Classic ML performance when labels lag | **NannyML** (OSS — estimates performance **before ground truth arrives** via CBPE/DLE; **tabular only**) |
| LLM gateway | **LiteLLM** (OSS) or the cloud's API gateway |
| Telemetry spine | Reuse the serving cloud's Monitor/CloudWatch, or an OSS stack (Prometheus/Grafana) |

**For:** deepest LLM-native tooling and iteration speed; full in-country data control (prompts/outputs never leave True infrastructure — strongest PDPA posture); minimal licence cost and lock-in; portable across clouds.
**Against:** genuinely **multi-tool** — even Evidently doesn't do NannyML-style label-free performance, so expect **2–4 self-hosted services** to deploy, patch, secure, back up (needs platform-engineering capacity that must be resourced); fragmented governance — RBAC/audit/retention built per tool; no single-vendor support. *(Note: Arize **Phoenix** is OSS but **LLM-only** — its classic-ML monitoring lives in the commercial Arize AX; don't assume the free tier covers ML.)*

### 13.6 Trade-off comparison

| Dimension | A — Azure | B — AWS | C — Google | D — Open |
|---|---|---|---|---|
| Classic-ML drift/quality | **Native** (Azure ML) | Clarify + OSS pattern *(Model Monitor sunsetting)* | **Native** (Vertex, incl. v2 external) | Evidently / NannyML (assembled) |
| Classic-ML perf without labels | Preview; needs ground truth | Needs ground truth | Needs ground truth | **NannyML** (label-free estimate) |
| GenAI observability/eval | Foundry: continuous + scheduled eval | Guardrails + **offline** eval + logging | **Offline** eval + safety + ops metrics | **Best-in-class** (Langfuse) |
| Native GenAI quality-drift monitor | Closest (scheduled eval) | **No** | **No** | Via Langfuse/Evidently |
| "Deployed-elsewhere" models | Pipe data in (data asset) | Pipe to S3 + custom job | **v2 supports external** *(verify GA)* | Instrument anywhere (OTel) |
| Ops burden | Low (managed) | Medium (assembled) | Low–medium (managed) | **High** (2–4 self-hosted) |
| Governance plane | **Inherited** Azure RBAC | Inherited AWS IAM | Inherited GCP IAM | Built per tool |
| PDPA / residency | Region-dependent (eval item) | Region-dependent | Region-dependent | **Full in-country control** |
| Fit with current estate | **Best** (Foundry in use) | If AWS-hosted | If GCP-hosted | Overlay on any |
| Lock-in | Higher (OTel-mitigated) | Higher (OTel-mitigated) | Higher (OTel-mitigated) | **Low** |

### 13.7 Recommendation & decision protocol

**Recommendation: align monitoring to the cloud that already runs True's production estate — its native tools (Azure / AWS / Google), with the open stack (Option D) as a selective overlay** where LLM-native depth or in-country residency demands it (OpenTelemetry keeps that additive, not rework). Because the RAI coordinator is new to the team, **confirming that production ecosystem is the first step, not an assumption.** On current signals the front-runner is **Azure** — True already uses Azure AI Foundry, and Azure ML + Foundry cover both model classes under existing Azure RBAC/audit/retention — so **Azure is the working default pending ecosystem confirmation.** This is a management decision; to make it on evidence, run a **~1-month tooling evaluation** — confirm ecosystem → sourcing → environment setup → hands-on testing → dated decision:

| Evaluation output (dated) | Question it answers |
|---|---|
| **Confirmed production ecosystem** — which cloud(s) actually host our live models (with IT) | Which native option (A/B/C) is even in scope |
| One GenAI use case traced end-to-end on the front-runner (Azure) + an open (Langfuse) sandbox on the same case | Real capture quality + effort, side by side |
| One classic-ML use case on the front-runner's native monitor | Drift/perf signals land in the dashboard? |
| DPO residency ruling | Does our region satisfy PDPA for prompts/outputs (in-country availability vs Singapore + safeguards)? |
| Thai-language evaluator sample test | Are the native GenAI evaluators usable for Thai content? |
| IT ownership decision | Who runs the capture layer (see §17) |
| Cost estimate | Order-of-magnitude run cost per option at pilot + portfolio scale |

### 13.8 Working with IT — integration steps

1. **Confirm the production ecosystem + inventory** — which cloud(s) host our live models (the decision input for §13.7), then split use cases **GenAI / classic ML / vendor** and confirm each serving path (Mity, cloud endpoint, vendor, on-prem) → assigns each its capture pattern (§13.1).
2. **Confirm the telemetry contract** (§12) as the required signal set; map each signal to a capture point.
3. **Run the tooling evaluation** (§13.7) → management picks the **ecosystem-native suite / open / hybrid** on evidence.
4. **Adopt the vendor clause set** with Legal/procurement as a **standing requirement for all new and renewing AI vendor contracts**. Where a vendor's SoW is **still unsigned, insert the core clauses at signature** — an unsigned SoW is a one-time leverage moment; signing without them leaves §11's vendor-pause mechanics fictional until renewal. Retrofit already-signed vendor contracts at renewal.
5. **Instrument the pilot** (§14) per the chosen option; verify signals + alerts land in one dashboard and the action queue.
6. **Security / DPO review of the monitoring stack itself** — it processes prompts, outputs, and features, so it is in scope for the same controls it enforces.

## 14. Rollout — Wave 1 Remediation, Pilot, 30/60/90

**Wave 1 = visibility + BU support, running in parallel with the pilot — not a gate on anyone's delivery.** The gaps below are **owned by the responsible business units**, with owners and dates the Council itself set; the COE tracks them, provides templates and follow-up, and escalates only per the Council's own decisions ("governance enables delivery", §5). The board will ask about them on Aug 4, so their status is part of the board pack:

| Wave-1 item (from Council #2/#3) | Owner (per minutes) | Target |
|---|---|---|
| **Confirm + record the outcome of the accept-or-block reconvene** (week of 29 Jun) for AI Speaker & AI Pet — the pack holds no outcome | COE + K.Nakhun | Wed 8 Jul |
| Close the 2 unsigned vendor SoWs — **with the §13.1 clause set inserted at signature (Legal)** — or execute the Council's block recommendation | K.Pat / K.Jirayu / K.Pasit + Legal | Immediate (past due 26 Jun) |
| **Name + gate-check the remaining high-risk live cases**: Proactive Fiber Cut Impact Prediction (CNO — Chalermpon W., per Council #2) and the fourth from the register | COE | Fri 10 Jul |
| Validate AI Speaker & AI Pet DPO controls (A3 SIEM integration, R3 data-access; AI Pet SIEM per Actions 8–9) + close the accuracy/hallucination/bias evidence asks (Actions 14–17) | Security / Architecture + K.Pasit + T3 | Fri 31 Jul |
| Risk-screen the 3 live unscreened cases (Smart Accounting Ph.1, Jaidee Borrow, AIS churn) | K.Nakhun → COE + use-case owners | Fri 24 Jul |
| Complete the **first tranche (9, ranked by tier)** of the 19 live DPO-checklist gaps; all 19 owner-assigned | COE + DPO + owners (escalation per Action 4) | Tue 4 Aug (remainder by end-Q3) |
| Screen the 10 in-development cases — build does not pass architecture review without screening | COE + owners | Tue 4 Aug |

**Standing up the two capabilities — production first.** Both start now, manual and registry-driven (implementation-plan Phases 0–2: registry rows, scorecard, prototype dashboard), upgrading to telemetry after the tooling evaluation (~late Aug):

- **Monitoring → live (production) use cases first.** Ingest the ~37 live cases into the control tower, high-risk-live first; the **10–15 risk-balanced pilot set** (per the board pack + 15-row scorecard — HR chatbot, Call Center KB, Mity platform, AI Speaker/AI Pet, A2BI, agents' unintended-action controls, CX sentiment, NBA/NBO, network AI incl. Nomiso/Digital Twin/GENIE, Finance, B2B, TrueID TV) is the manageable first batch. Weekly reviews from week one.
- **Architecture review → in-development use cases.** Every in-development case gets architecture review before it launches; the 10 in-dev unscreened cases (wave-1 table above) are first.

Both run **in parallel** with the BU-owned gap closure above — enablement, not a gate.

**30 / 60 / 90 (day 0 = Tue 7 Jul 2026):**

| By | Milestones |
|---|---|
| **Fri 24 Jul** | Accenture handover complete (§4) · wave-1 items owner-assigned with dates · manual pilot reviews running · tooling evaluation started · decision-rights table (§3) circulated for CDAO confirmation |
| **Thu 30 Jul** | Wave-1 status board-ready · §0 asks packaged for the board |
| **Tue 4 Aug** | **Board update** — operating model, wave-1 status, pilot scope, tooling direction, resourcing ask |
| **Fri 4 Sep (60d)** | Evaluation decision ratified (production ecosystem confirmed → ecosystem-native / open / hybrid) · pilot telemetry-instrumented, weekly cadence running · wave-1 closed or escalated · KPI baseline published |
| **Mon 5 Oct (90d)** | Risk-based cadence business-as-usual across the live portfolio · first monthly KPI report to the RAI Council · scale decision beyond the pilot |

## 15. Resourcing & Function KPIs

**Resourcing (ask #4 — deliberately minimal).** Today the operating capacity is effectively one person, and resources are tight — so the ask is **one additional person to help with coordination**, who also covers for the coordinator (removing the single-point-of-failure that §4 is the lesson of). Architecture, security, and privacy input is drawn from **existing teams per case**, not new formal allocations. For transparency, what running the model consumes:

| Role | Load |
|---|---|
| COE RAI coordinator (Ta) | 1.0 FTE — gate, register, control tower, KPIs, facilitation |
| AI architect (Architecture Forum) | ~0.3 FTE — reviews + evaluation |
| Security | ~0.2 FTE — assessments, control validation, incidents |
| DPO / privacy | ~0.2 FTE — checklists, rulings, incidents |
| BU monitoring owners | 2–4 h/week per High-risk case (named, federated) |
| IT platform | ~0.5 FTE during setup (capture layer, tooling), ~0.1 run |

**Peak-load check (Jul–Aug) — the honest version:** the DPO tranche implies **~2 checklist completions per week** through Aug 4 — confirm DPO capacity or the tier-ranked order in §14 stands and the tail moves to Q3. The coordinator's 1.0 FTE assumes **RAI coordination is the primary assignment**; the same person currently also carries Mity, the HR POV, and the COE weekly doc — if those stay, timelines stretch and the board should hear that explicitly.

**Tooling cost:** drivers are Foundry evaluator tokens, Content Safety calls, App Insights ingestion (A) or 1–2 VMs + platform-engineering time (B). **No number is quoted here by design — the evaluation produces the estimate** (§13.5).

**Function KPIs (baseline = Council #3 register, 22 Jun).** These are **portfolio-health targets the COE tracks and facilitates** — the closures themselves are owned by the responsible BUs (§14):

| KPI | Baseline | Aug 4 target | End-Q3 target |
|---|---|---|---|
| High-risk live without completed gate | **4** | **All 4 named** (only 2 were, pre-playbook), owner-assigned; each closed **or formally escalated to a block decision** | 0 |
| Live cases never risk-screened | **3** | 0 | 0 |
| Live cases without DPO checklist | **19** | **First 9 closed (tier-ranked)**; all 19 owner-assigned | 0 (or formally risk-accepted) |
| In-development unscreened | **10** | 0 | 0 |
| Pilot rows with all three owners named | n/a | 100% | 100% (portfolio-wide for High) |
| Median intake → decision turnaround | not measured | baseline it | ≤ 10 working days |
| Actions closed within SLA | not measured | baseline it | ≥ 90% |
| `Unknown` statuses on live cases | baseline at pilot start | — | –50% |

*(Count reconciliation — one number set, from the Council register, before Aug 4: register 131 / 37 live vs board narrative 130 / 38; the narrative's "12 not risk-assessed" vs the register's 13 (3 live + 10 in-dev); "40 not started" vs the register's 42.)*

## 16. Working Outputs to Produce Next

| Output | Owner | Target |
|---|---|---|
| Wave-1 remediation tracker (per-case owner/date, incl. the 4th high-risk case named) | COE | Fri 10 Jul |
| Intake overlay form (final, keyed on source ID) | COE | Fri 17 Jul |
| Accenture handover checklist executed (§4) | COE + Accenture | Fri 24 Jul |
| Decision-rights table + Council charter confirmed (§3) | CDAO | Thu 30 Jul |
| **Core vendor clauses inserted in AI vendor SoWs at signature** (telemetry/SIEM forwarding, evidence cadence, suspension) — any still-unsigned SoW first | Legal + COE | Standing; unsigned SoWs now (wave 1) |
| Full vendor AI clause-set template (for all future contracts) | Legal + COE | Fri 14 Aug |
| AI incident runbook v1 (§11) wired to IT incident process, incl. interim vendor containment per case | COE + Security | Fri 14 Aug |
| Thresholds & SLA table adopted (Sheet-3 defaults + §10 severity map + §11 SLAs) | RAI Council | Aug session |
| Tooling evaluation report + platform decision (§13.5) | COE + IT | Fri 21 Aug |
| **Intake enforcement hooks live** (no TPM record / PO / prod access without use-case ID) + first quarterly shadow-AI sweep | IT demand mgmt + Procurement + COE | Hooks: Sep · first sweep: Q3 |
| KPI dashboard v1 (control tower) | COE | Sep |
| Pack-doc sync — align **all four sibling docs** (control-tower README incl. Medium cadence weekly→monthly, implementation plan, board narrative counts, registry schema) to this playbook | COE | Fri 17 Jul |
| NIST AI RMF / ISO 42001 clause mapping (defensibility annex) | COE | Q3 |

## 17. Open Decisions (beyond the §0 asks)

- **Capture-layer ownership:** who runs the gateway/endpoints/SIEM plumbing — recommend **IT owns the platform, COE owns the policy and thresholds**; confirm with IT leadership.
- **Where this function sits after the Sep 1 restructure** — the new data-governance box's scope (data-governance only vs + RAI) and placement (Data vs AI/Transformation pillar) is still TBD with HR; this playbook transfers intact either way.
- **Evidence retention duration** — ≥ 5 years proposed; confirm with Legal/DPO.
- **Delegation of pause approval** — §3's model is: coordinator proposes → CDAO **or a standing RAI Council-chair delegate** approves within the S1 clock → IT/vendor executes. The open question is only the middle step: standing delegation to the Chair (recommended — with same-day CDAO notification) or per-incident CDAO approval.
