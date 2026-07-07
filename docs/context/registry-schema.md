# Assurance Registry Schema

> Internal True / CP Group working draft.
> Created: 2026-07-06.

## Purpose

The control tower registry is an **assurance overlay**. It should link to the official AI Reporting Tool / VRO / TPM record rather than becoming a duplicate value-realization tracker.

The registry answers:

> For each AI use case, what is running, who owns it, what evidence exists, what is monitored, what is degrading, and who must act?

## Data Principles

- **Source of truth stays outside this project.** Use the AI Reporting Tool / VRO / TPM identifier wherever available.
- **Assurance fields live here.** Risk, evidence, monitoring health, telemetry, and action status are the control-tower layer.
- **Missing information is visible.** Use `Unknown`, not blank.
- **Value is linked, not duplicated.** Revenue, cost saving, and productivity value can be referenced, but VRO remains the owner.
- **Platform-neutral by default.** Mity, Microsoft, vendor tools, internal ML, LLM apps, and workflow AI use the same minimum schema.

## Required Registry Fields

| Field | Required | Definition | Example / allowed values |
|---|---|---|---|
| `registry_id` | Yes | Stable control-tower ID | `AICT-P01` |
| `source_record_id` | Yes if known | AI Reporting Tool / VRO / TPM ID | `TPM-...`, `VRO-...`, `Unknown` |
| `use_case_name` | Yes | Plain-language use-case name | `HR leave-policy chatbot` |
| `use_case_group` | Yes | Portfolio grouping | `Mity PoV`, `Network AI`, `AI Council`, `Finance` |
| `business_unit` | Yes or `Unknown` | BU or domain sponsor | `HR`, `Call Center`, `Network`, `Finance` |
| `business_owner` | Yes or `Unknown` | Accountable for workflow fit and acceptance | Named person/team |
| `technical_owner` | Yes or `Unknown` | Accountable for implementation and support | Named person/team |
| `monitoring_owner` | Yes or `Unknown` | Accountable for ongoing monitoring and action follow-up | Named person/team |
| `system_owner` | Yes for platform/system rows | Owner of the application/system boundary | `True Connect owner`, `Unknown` |
| `platform_or_app` | Yes | Where the AI is embedded | `True Connect`, `Mity`, `Microsoft`, `Nomiso` |
| `model_provider` | Yes or `Unknown` | Model, vendor, or provider path | `Mity`, `Microsoft`, `Internal`, `Vendor`, `Unknown` |
| `model_or_route` | If available | Model name, route, agent, or gateway decision | `GPT via Mity`, `Internal + Microsoft`, `Unknown` |
| `workflow_location` | Yes or `Unknown` | Where users encounter it | `True Connect chat`, `call center workflow`, `network ops` |
| `data_sources` | Yes or `Unknown` | Major source systems or knowledge bases | `SharePoint`, `SAP SuccessFactors`, `network tickets` |
| `status` | Yes | Lifecycle status | `requirements`, `PoV`, `UAT`, `production`, `paused`, `retired` |
| `risk_tier` | Yes or `Unknown` | AI Council risk classification | `High`, `Medium`, `Low`, `Unknown` |
| `privacy_status` | Yes | DPO/privacy evidence status | `Not required`, `Required`, `In review`, `Approved`, `Unknown` |
| `security_status` | Yes | Security assessment status | `Not started`, `In review`, `Approved`, `Exception`, `Unknown` |
| `rai_status` | Yes | RAI / AI Council evidence status | `Complete`, `Partial`, `Missing`, `Unknown` |
| `ai_readiness_status` | Yes | Readiness checklist status | `Complete`, `Partial`, `Missing`, `Unknown` |
| `telemetry_status` | Yes | Whether monitoring signals are available | `Live`, `Manual`, `Partial`, `Missing`, `Unknown` |
| `current_health` | Yes | Current assurance health | `Green`, `Amber`, `Red`, `Unknown` |
| `last_reviewed` | Yes or `Unknown` | Date of latest assurance review | `2026-07-06` |
| `next_review` | Yes or `Unknown` | Next required assurance review | `2026-07-13` |
| `open_actions` | Yes | Count or linked action list | `3`, `None`, link to action queue |

## Monitoring Lane Fields

Use these fields to score whether each monitoring lane has evidence.

| Lane | Field | Expected content |
|---|---|---|
| Quality | `quality_metric` | Accuracy, task success, citation correctness, SME pass/fail, recommendation precision |
| Quality | `quality_threshold` | Pass threshold or review rule |
| Quality | `quality_status` | `Green`, `Amber`, `Red`, `Unknown` |
| Safety/security | `safety_controls` | PII, prompt injection, unauthorized access, unsafe-action controls |
| Safety/security | `safety_status` | `Green`, `Amber`, `Red`, `Unknown` |
| Reliability | `reliability_metric` | Latency, uptime, fallback rate, timeout rate, incident count |
| Reliability | `reliability_status` | `Green`, `Amber`, `Red`, `Unknown` |
| Drift/degradation | `degradation_signal` | Quality trend, stale knowledge, changed data pattern, model/prompt regression |
| Drift/degradation | `degradation_status` | `Green`, `Amber`, `Red`, `Unknown` |
| Feedback/action loop | `feedback_source` | User feedback, SME correction, support tickets, incident review |
| Feedback/action loop | `feedback_status` | `Green`, `Amber`, `Red`, `Unknown` |

## Action Queue Fields

Every amber or red item should produce an action row.

| Field | Definition |
|---|---|
| `action_id` | Stable action ID |
| `registry_id` | Linked use case |
| `issue` | What is wrong or missing |
| `recommended_action` | What should happen next |
| `owner` | Person/team accountable |
| `due_date` | Target date or `Unknown` |
| `escalation_path` | Security, DPO, AI Council, CDAO, business owner, technical owner |
| `status` | `Open`, `In progress`, `Blocked`, `Closed` |
| `evidence_link` | Link to document, checklist, risk register, or meeting note |

## Health Status Rules

| Status | Meaning |
|---|---|
| Green | Evidence exists, monitoring is defined, no active breach or material missing owner. |
| Amber | Some evidence exists but a monitoring signal, owner, threshold, or action is missing. |
| Red | Material risk, missing required control, missing owner for high-risk case, production issue, or security/privacy gap. |
| Unknown | Use case exists but evidence is insufficient to assess. |

## Risk-Based Cadence

| Risk tier | Minimum cadence | Required review body |
|---|---|---|
| High | Weekly or near-real-time for critical signals | Use-case owner plus Security/DPO/AI Council where relevant |
| Medium | Monthly with sampled quality checks | Use-case owner plus COE review |
| Low | Quarterly or minimum six-month confirmation | Owner confirmation plus COE spot check |
| Unknown | Review until classified | COE to chase risk classification owner |

## Minimum Pilot Completion Criteria

A pilot row is usable when it has:

- one linked source-of-truth record or explicit `Unknown`
- named business, technical, and monitoring owners or explicit `Unknown`
- risk tier or explicit `Unknown`
- privacy/security/readiness evidence status
- at least one monitoring metric per relevant lane, or a stated reason the lane is not applicable
- current health status
- open actions for every amber/red/unknown critical gap

