# Intent: October batch monitoring MVP

- **Status:** Accepted
- **Owner:** project owner (ta.khongsap)
- **Date:** 2026-10-07 (the plan started on 2026-10-02)
- **Risk tier:** **R2 — material workflow** (accepted by the project owner on 2026-10-07)
- **Review date:** the release sign-off, S4-06 (week of 26 October 2026), or earlier when
  the data, the senders or the judge change
- **Plan:** [plan.md](plan.md), [issues.md](issues.md). Decision record:
  [ADR 0002](../../docs/adr/0002-batch-push-ingest.md).

## Problem

The RAI team must know if the LLM output of 10 GCP batch use cases is good enough. The
prototype monitor pulls telemetry from three demo models and cannot see the GCP jobs.

## Outcome

Each GCP batch run sends one run summary to the monitor. The monitor grades the run
Green, Amber, Red or Unknown with the five LLM metrics, and shows the grade to the RAI
team. Engineers see one trace for each run in Langfuse. The monitor advises; the RAI team
decides. The monitor never acts on a model or a job.

## Risk tier measurement

Measured with `handbook/risk-tiers.md` of `tkhongsap-ai-engineering-playbook@5ba9dc8`.

1. Base tier: **R1**. Internal users (the RAI team and engineers), the output is advice,
   and a human decides.
2. Escalation rules ("escalate at least one tier when the system…"):

| Rule | Batch MVP | Applies |
|---|---|---|
| Uses personal, confidential, regulated or security-sensitive data | Real customer records from 10 production use cases. Phones, emails and national IDs become placeholders; names are hard to remove (S1-08). | Yes |
| Can call tools that write, send, publish, delete, buy, deploy or change access | The judge only scores; the monitor writes only its own database | No |
| Influences a consequential decision about a person | It grades models, not people | No |
| Is exposed to untrusted content that can influence instructions or tools | The LLM judge reads customer text (prompt injection can change a score) | Yes |
| Works without timely human review | The RAI team reviews the dashboard | No |
| One failure can affect many users or systems | One monitor grades 10 use cases, but only advises | Partly |
| Has no reliable rollback or correction path | Stored runs never change; code rolls back | No |

Result: **R2**. The prototype (three demo models, synthetic data) stays R1.

## R2 evidence and where it is

| Evidence (R2) | Level | Where |
|---|---|---|
| Outcome, scope, assumptions | MUST | This file, `plan.md` |
| Data and model provenance | MUST | S1-01 schema, S1-09 inventory, the judge model in S1-12 |
| Versioned evaluation dataset, predeclared thresholds | MUST | S2-10 reference set and limits, `llm-metrics-standard.md` |
| Threat model and abuse cases | MUST | **New: S2-11** (not in the plan before 2026-10-07) |
| Privacy and retention review | MUST | S1-08, S3-05 |
| Human authority boundary | MUST | The dashboard advises; the RAI team decides (ADR 0001 for alerts) |
| Staged release and rollback | MUST | Test host → test AWS cluster → production (S3-06, S4-01) |
| Production monitoring | MUST | S3-02 delivery alerts, S4-05 runbooks |
| Independent or domain review | SHOULD | RAI accepts the judge (S2-10) |
| Formal incident exercise | SHOULD | S3-04 drills |

## Open uncertainty

- Names and other free-text PII in the records: security decides the list (S1-08).
- Prompt injection into the judge: S2-11 describes it and its controls.
- The AI system card (`templates/ai-system-card.md` of the playbook) is not written yet.
  The project owner decided to write it later, before S4-06.
