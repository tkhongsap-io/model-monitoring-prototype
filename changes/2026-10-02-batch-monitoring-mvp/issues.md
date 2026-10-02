# Batch Monitoring MVP — GitHub-ready issue drafts

These are proposed issue bodies, not issues posted to GitHub. Assign an owner and split an issue further if its implementation cannot be independently reviewed. Use the [monthly scaffold](plan.md) and [GCP → AWS flow](flow.html). A use case counts as live only with a verified real completed batch. Preserve the existing three-source v1.1 contract.

> **Out of date (2026-10-02):** the [plan](plan.md) now uses push ingestion: each GCP job sends a JSON summary to the monitor API after publishing. The Sprint 1 drafts below (S1-01 to S1-05) still describe read-only pull and are superseded by plan tasks 1.1–1.7. Later drafts that mention pull adapters or manifests need the same update before they are posted.

## Sprint 1 — Oct 5–9: discovery and first proof

### S1-01 — Map the ten production use cases

Owner: Source owners + backend

What to do: Obtain the authoritative ten-ID list and map each ID to its actual GCP deployment, owner, schedule, output location/retention, publication-based completion signal, run identifiers, data class, and label availability. Reconcile the six inspected logical pipelines against that list.

Acceptance criteria:
- [ ] Inventory contains exactly ten distinct production IDs with named owners, not assumed config-to-use-case mappings.
- [ ] Every entry distinguishes submission, harvest and business publication, and records an output/access path or an explicit blocker.
- [ ] Source owners confirm deployed cadence, retention and which results can be accessed from AWS.

### S1-02 — Decide secure cross-cloud handoff and cluster ownership

Owner: Platform + security

What to do: For each source, select approved read-only pull or minimal authenticated post-publication manifest; document egress, identity, data minimization, network path and secrets ownership. Identify target AWS Kubernetes operator and access date without assuming EKS.

Acceptance criteria:
- [ ] Per-source transport and data-permission decision is documented and approved or flagged as blocked with owner/date.
- [ ] AWS cluster owner, access date, ingress/TLS and secret-management decision are recorded.
- [ ] No proposed raw-data transfer or public OTLP/database endpoint bypasses security review.

### S1-03 — Define the completed-run contract and prove one parser

Owner: Monitoring backend

What to do: Specify a batch-run record separate from the existing v1.1 closed-window contract. Include stable use-case/run IDs, artifact identity/version, completion/freshness, status, allowlisted model/usage, source references, missing-value reasons and optional evaluation evidence. Parse a sanitized fixture from one approved source.

Acceptance criteria:
- [ ] Contract explicitly says which signal proves completed business publication; output-object existence alone is insufficient.
- [ ] Parser tests cover a valid fixture, absent timing/labels and malformed or sensitive fields without logging raw contents.
- [ ] Existing three-source contract tests continue to pass; no inferred latency, cost or accuracy is populated.

### S1-04 — Approve the first batch evaluation policy

Owner: RAI reviewers + backend

What to do: Select one use case with permitted evaluation inputs. Specify a versioned task-specific rubric, sample rule, reference-label coverage if any, judge provider/privacy and budget; map results into existing backend score/health machinery without applying the chatbot rubric unchanged.

Acceptance criteria:
- [ ] RAI/use-case owner signs off rubric, policy version, judge identity, sample size and supported metrics.
- [ ] Policy states when an outcome is Unknown (no labels, missing inputs or judge failure) rather than silently Green.
- [ ] Sensitive evaluation inputs and outputs have explicit redaction/retention approval.

### S1-05 — Demonstrate one authorized completed batch

Owner: Source owner + backend + frontend

What to do: Import one real published run using the approved handoff, store run/evidence identity and apply the reviewed evaluation policy where evidence permits. Show run status, supported usage, evaluation provenance or Unknown reason in the monitor API/dashboard.

Acceptance criteria:
- [ ] Source owner confirms completion after business publication and the monitor retains the run/artifact reference.
- [ ] API/dashboard show the actual run ID and metric provenance without raw customer content.
- [ ] A contract/integration test covers the ingest; any unavailable evaluation is explicitly Unknown. A fixture-only demo does not pass.

## Sprint 2 — Oct 12–16: repeatable local system

### S2-01 — Build a registry and idempotent batch ingestion

Owner: Monitoring backend

What to do: Add a configurable batch source registry, reusable pull/manifest adapter boundary, normalized-run store and durable checkpoints. Key by `(use_case_id, run_id)` and retain artifact digest/version; do not wait on a batch within an HTTP request.

Acceptance criteria:
- [ ] Tests show an identical replay creates no duplicate observation and a changed artifact under the same ID raises an integrity error.
- [ ] Restart resumes from a durable checkpoint after an observation is stored; an ingest failure does not advance it.
- [ ] Existing v1.1 sources remain functional and batch reads are asynchronous to the reverse-proxy response.

### S2-02 — Onboard four real sources through the common path

Owner: Source owners + backend

What to do: Configure and validate at least four distinct production IDs, including a second output or completion pattern. Add source-specific parser fixtures and minimal post-publication manifest exporters only where read-only access is not viable.

Acceptance criteria:
- [ ] Four unique IDs each show a source-owner-verified completed run and artifact/version provenance.
- [ ] Parser tests cover the observed source variants; submission-only or unpublished results are excluded.
- [ ] Source-specific blocked metrics appear as Unknown instead of fabricated values.

### S2-03 — Adapt backend evaluator for approved batch rubrics

Owner: RAI reviewers + backend

What to do: Reuse the existing judge, score persistence and health grading while adding task-specific policy selection, versioned rubric metadata, sample counts and reasoned Unknown outcomes. Avoid an automatic English-only heuristic for Thai or mixed-language material.

Acceptance criteria:
- [ ] Tests cover missing labels, insufficient samples, judge failure and policy-specific threshold boundaries.
- [ ] Scores retain judge identity, policy version, evidence/run IDs and sample size; quality failures do not masquerade as ingest failures.
- [ ] At least one approved real run has a durable evaluation score; unsupported accuracy remains Unknown.

### S2-04 — Verify Collector → Langfuse trace and score correlation

Owner: Platform + backend

What to do: Integrate monitor, PostgreSQL, OTel Collector and self-hosted Langfuse in local Compose. Emit allowlisted importer/evaluator spans per completed run, link monitor-owned scores through a tested Langfuse score-write path and store stable trace IDs. Check version/auth compatibility rather than assuming OTLP writes scores.

Acceptance criteria:
- [ ] A real completed run's trace is read back in Langfuse with matching use-case/run ID; its score is attached to that trace and read back by ID.
- [ ] Retrying trace or score export does not duplicate the run, generation or score; transport failure is recorded for retry.
- [ ] No importer duration is labeled original Gemini latency; secrets and raw customer content are absent from spans.

### S2-05 — Show evidence and authorized trace links in the RAI dashboard

Owner: Frontend + backend

What to do: Expose latest completed run, freshness, operational state, signal provenance, score/Unknown reason and trace reference via the monitor API. Keep database and Langfuse credentials server-side.

Acceptance criteria:
- [ ] Four real sources are visible with run identity and correct freshness; missing measurements say Unknown.
- [ ] Browser uses only read APIs and authorized links, not direct PostgreSQL access or Langfuse project keys.
- [ ] API/UI tests cover unavailable score and trace, redacted payload and a stale source.

## Sprint 3 — Oct 19–23: broaden and harden

### S3-01 — Onboard eight sources with nontrivial completion paths

Owner: Source owners + backend

What to do: Reach at least eight distinct production IDs. Handle submit/harvest across different executions, short-lived raw outputs, post-tasks and partial publication with source-specific completion checks; create a sanitized manifest where needed.

Acceptance criteria:
- [ ] Eight source-owner-confirmed real published batches are visible, not eight configs or fixture rows.
- [ ] Tests exclude a submitted-but-unharvested job and an artifact present before business publication.
- [ ] One disappearing-output path survives via an approved, idempotent post-publication manifest.

### S3-02 — Make evaluation coverage and provenance inspectable

Owner: Backend + RAI reviewers

What to do: Separate label/judge coverage and quality results from ingestion failures; show policy version, sample count, lag and reasoned Unknown per run. Preserve stable model/prompt and approved sample references for a possible later explanation artifact.

Acceptance criteria:
- [ ] Tests cover missing timing, malformed rows, insufficient labels, unsupported rubrics and a changed artifact digest.
- [ ] API reports coverage, judge identity and evaluated-versus-Unknown reason without inventing ground truth or money cost.
- [ ] Batch policies are reviewed for each newly scored task; LIME is not executed in this MVP.

### S3-03 — Prove failure and recovery behavior

Owner: Backend + platform

What to do: Add bounded retries, bad-record quarantine, staleness/error alerts and durable trace/score export retry. Exercise restarts, Collector outage and Langfuse score-write failure without losing completed-run evidence.

Acceptance criteria:
- [ ] Automated tests prove failed import does not advance the checkpoint and one bad record does not stop other sources.
- [ ] Outage/restart drill preserves normalized runs; recovery produces one observation and one linked score per run.
- [ ] Stale/failed ingestion is surfaced separately from model quality and does not generate a false Green.

### S3-04 — Complete security and data-retention review

Owner: Security + platform + source owners

What to do: Audit GCP↔AWS identity, allowlisted metadata, TLS/auth, secrets, judge payloads, logs/spans and retention for all onboarded sources; record exceptions and remediation ownership.

Acceptance criteria:
- [ ] Unauthorized access is rejected in an integration test; no browser or public endpoint receives a service credential.
- [ ] Sample traces, logs and dashboard responses show no raw customer identifiers, invoice text or credentials.
- [ ] Transfer/retention approvals and remaining exceptions are documented per source.

### S3-05 — Prepare target-cluster deployment and connectivity

Owner: Platform

What to do: Package monitor, Collector, Langfuse and backing services for target AWS Kubernetes with persistent storage, secrets, TLS ingress, health probes, resource bounds and a rollback path. Exercise locally if possible and test target-cluster access/networking once granted.

Acceptance criteria:
- [ ] Deployment configuration passes validation and a disposable-cluster smoke test if available; unavailable tooling is reported, not counted as passing.
- [ ] GCP artifact and judge network paths, Langfuse persistence, and AWS cluster credentials/owner have an explicit tested or blocked result.
- [ ] Backup/restore and rollback procedures are written before release week.

## Sprint 4 — Oct 26–30: AWS release and handoff

### S4-01 — Complete all ten real source integrations

Owner: Source owners + backend

What to do: Finish the remaining production IDs and obtain a real scheduled published batch for each; if cadence does not permit one, arrange an approved controlled real rerun. Reconcile the dashboard list to the authoritative ten-ID inventory.

Acceptance criteria:
- [ ] Exactly ten named sources have source-owner-verified real completed batches, artifact identity and freshness.
- [ ] No synthetic run, configured-only entry, submitted job or raw result before publication is counted as live.
- [ ] Missing evidence or access is reported as a blocked source, not hidden by a fixture.

### S4-02 — Deploy and smoke-test the target AWS Kubernetes stack

Owner: Platform

What to do: Deploy the monitor, Collector, self-hosted Langfuse and backing services to the actual target AWS cluster. Verify network path to approved GCP outputs and judge, secret delivery, ingress/TLS, storage and health.

Acceptance criteria:
- [ ] Actual cluster smoke test reads one authorized real GCP run and shows its imported trace in Langfuse with linked score where evidence permits.
- [ ] Authenticated endpoints, storage survival after pod restart and non-public backing services/OTLP are verified.
- [ ] Cluster identity, deployment version and any unmet infrastructure prerequisites are recorded.

### S4-03 — Reconcile per-source dashboard, evaluation and trace evidence

Owner: Backend + frontend + RAI reviewers

What to do: For each of the ten IDs, compare source completion, stored normalized run, monitor API/dashboard state, OTel/Langfuse trace and score attachment. Explain gaps explicitly rather than making Langfuse the browser's business-status source.

Acceptance criteria:
- [ ] A ten-row checklist records run ID, completion evidence, last-run freshness, policy/coverage or Unknown reason, and trace ID.
- [ ] Each approved scored run's trace/score IDs match; unsupported scores have an explicit reason and no invented Green.
- [ ] RAI reviewers accept the displayed provenance, including any unavailable latency, cost or accuracy.

### S4-04 — Exercise operations and document ownership

Owner: Platform + operations

What to do: Run target-cluster restart, backup/restore, rollback, alert and score-export recovery drills. Publish runbooks for stuck sources, failed egress, Langfuse outage, permissions and on-call escalation.

Acceptance criteria:
- [ ] Recorded drill shows recovery without duplicate runs/scores or data loss after restart/restore.
- [ ] Alerts distinguish source staleness from evaluation quality; rollback and restore have an owner and tested steps.
- [ ] Runbook names service owners, source owners, credential rotation and incident escalation.

### S4-05 — Sign off release against evidence, not configuration

Owner: RAI + platform owners

What to do: Review the ten-source checklist and cluster drill record. Approve release only if both real source coverage and target-cluster verification pass; otherwise publish the completed pilot and its blockers.

Acceptance criteria:
- [ ] RAI and platform owners sign off 10/10 real completed sources and the target AWS Kubernetes operational result.
- [ ] Any missing source, data-egress approval, trace correlation or cluster access is recorded as an unmet gate with owner and next action.
- [ ] Handoff distinguishes production release from local Compose or fixture-only validation.

**Out of scope:** Mandatory LiteLLM migration, producer-side OTel SDK in all ten jobs, fabricated latency/accuracy/cost, and LIME execution. Langfuse and the Collector are mandatory AWS components; batch evaluation policy stays in the monitoring backend.
