# October Batch Monitoring MVP Implementation Plan (team scaffold)

> For implementers: use the [20 GitHub-ready issue drafts](2026-10-02-batch-monitoring-mvp-issues.md) for the detailed "What to do" and acceptance criteria behind the weekly tasks below. Review the [GCP → AWS flow](2026-10-02-batch-monitoring-flow.html) before assigning work. Preserve the existing three-source contract; the batch path is additive.

**Goal:** By Friday, 2026-10-30, all 10 named GCP use cases have a real completed run visible in the RAI dashboard, with honest status/evaluation evidence and a correlated OpenTelemetry/Langfuse trace (plus linked scores where evaluation evidence permits), on a service verified in the target AWS Kubernetes cluster.

**Architecture:** GCP jobs keep running asynchronously and publish their existing results. The AWS monitoring backend imports authorized completed-run evidence, applies centrally owned, task-specific evaluation policy, stores graded status, emits OTel spans through an AWS Collector to self-hosted Langfuse, and links scores there. Its API feeds the dashboard; instrumented GCP/LiteLLM call spans may add timing but are not a substitute for completed batch evidence.

**Tech stack:** Existing FastAPI/React/PostgreSQL prototype; GCP batch artifacts; Docker Compose for integration; OpenTelemetry Collector and self-hosted Langfuse; AWS Kubernetes (distribution not yet confirmed).

**Status:** Planning scaffold; producer access, AWS cluster access and the mapping to ten production use cases remain to be verified.

## Working rules and ownership

- Source owners: identify the ten production use-case IDs, output and completion signal, cadence, retention, label access and data classification. Six logical pipelines in four repositories have been inspected; their mapping to ten use cases remains unverified. Prefer read-only pull; add a small post-publication manifest only where outputs are ephemeral or inaccessible.
- Monitoring/backend team: own the registry, normalized run/cursor schema, source adapters, central evaluation policy, API and test fixtures. Keep batch IDs, submit/harvest execution IDs and business row keys separate; use idempotent artifact versions. Existing v1.1 closed-window sources must continue to work.
- Platform/observability team: own Compose and AWS manifests, Collector → Langfuse integration, secure GCP↔AWS access, secrets, persistence, backup/restore and alerts. Test trace and score attachment, not just container readiness. No public database, object store or unauthenticated OTLP receiver.
- RAI/use-case reviewers: sign off a versioned rubric, sampling/label coverage and redaction policy per use case. No inferred ground-truth accuracy without labels; mark unsupported metrics Unknown. Frontend team shows freshness, reason, provenance and authorized trace links through the monitor API.

## Sprint 1 — Oct 5–9: map sources and prove one run

- [ ] **Source owners:** Identify all 10 production IDs and map them to actual deployments (not just repository configs). Record owner, cadence, output/retention, completion-after-publication signal, run IDs, data sensitivity and labels; flag missing access or disappearing artifacts.
- [ ] **Platform + security:** Decide approved GCP→AWS read-only pull versus post-publication manifest per source, identity/egress/redaction rules, and the AWS cluster owner and access date. Log blockers with named owners.
- [ ] **Backend:** Agree a batch-run/metric contract with stable IDs, artifact version, provenance, completion/freshness and explicit Unknown fields. Add a parser fixture and tests for one authorized source; leave the existing v1.1 closed-window contract intact.
- [ ] **RAI + backend:** Review one task-specific rubric, sampling, available labels, judge provider/privacy and cost budget; specify which quality metrics are genuinely measurable.
- [ ] **Integration:** Import **one real completed batch**, apply the reviewed rubric to permitted evidence or explicitly record why it is Unknown, and show run identity, supported usage/status and evaluation provenance in the API/dashboard. A JSONL file alone is not proof of completed business publication.

**Exit:** 10-source inventory and decisions recorded; one authorized real run has a tested parsing path and visible, evidence-backed status.

## Sprint 2 — Oct 12–16: repeatable backend and local stack

- [ ] **Backend:** Implement a source registry and reusable pull/manifest adapters with normalized runs, durable checkpoints and `(use_case_id, run_id)` dedupe. Test identical retries, changed artifacts and restart recovery.
- [ ] **Source owners + backend:** Configure and verify real outputs for **at least four distinct use cases**, including one with a different output or completion pattern; do not count registration or fixture-only runs.
- [ ] **RAI + backend:** Adapt the existing judge/health machinery to approved batch rubrics; test missing labels, failed judge, minimum sample and task-specific thresholds. Persist rubric version, sample size and evidence with each result.
- [ ] **Platform + backend:** Run monitor, PostgreSQL, OTel Collector and self-hosted Langfuse in local Compose. Verify with a real completed run that import/evaluation spans arrive, the correct trace ID gets a linked score, and a retry does not duplicate it. Do not present importer duration as Gemini latency.
- [ ] **Frontend + backend:** Expose four sources' latest status, freshness, provenance, evaluation or Unknown reason, and authorized trace link through the monitor API; test read-only browser access and redaction.

**Exit:** 4 real sources visible; Collector→Langfuse trace and score write/read-back demonstrated locally. Compose does not prove AWS deployment.

## Sprint 3 — Oct 19–23: scale and harden

- [ ] **Source owners + backend:** Onboard **at least eight distinct real use cases**. Prove completion semantics for submit/harvest on different executions, deleted raw outputs, and partial business publication; add source-specific contract fixtures.
- [ ] **Backend + RAI:** Report label/judge coverage, versioned scores and Unknown reasons separately from operational failures. Test missing timing, malformed rows, insufficient labels, unsupported rubrics and changed artifact digests.
- [ ] **Backend + platform:** Test bounded retry, bad-record quarantine, staleness alerting, restart/replay, Collector outage and failed Langfuse score write; preserve normalized runs and retry trace/score export without duplicate observations.
- [ ] **Security + platform:** Review allowlisted fields, cross-cloud permissions, auth/TLS, retention and secret handling. Verify no customer text or credentials leak into spans, logs or dashboard.
- [ ] **Platform:** Prepare Kubernetes resources for monitor, Collector, Langfuse and dependencies, plus secrets, persistent storage, health checks and rollback. Exercise locally if available and record the result of target-AWS-cluster access/network tests.

**Exit:** 8 real sources visible; recovery/security tests pass; AWS deployment path and any access blockers are recorded.

## Sprint 4 — Oct 26–30: production verification and handoff

- [ ] **Source owners + backend:** Finish all **10 named sources**. Verify each against a real completed batch on its schedule, or an approved controlled real rerun; do not count configured-only sources or synthetic fixtures.
- [ ] **Platform:** Deploy monitor, OTel Collector, self-hosted Langfuse and backing services on the **target AWS Kubernetes cluster**; verify private access, ingress/TLS, secret injection, persistent storage and actual GCP-to-AWS retrieval/handoff.
- [ ] **Backend + frontend + RAI:** Check each source's run ID, completion evidence, freshness, evaluated result or explicit Unknown, and correlated Langfuse trace with linked score when evidence permits. Reconcile displayed counts against the 10-ID inventory.
- [ ] **Platform + operations:** Exercise restart, backup/restore, rollback, staleness/error alerts and score-export recovery on the target cluster. Publish runbooks, access model, source ownership and on-call escalation.
- [ ] **RAI + platform owners:** Sign off a per-source evidence checklist and the cluster smoke-test record; document any exception as an unmet release gate, not a passed MVP.

**Exit:** 10/10 verified real sources and a passed target-cluster operational handoff; otherwise report the achieved pilot and blockers accurately.

**Release gate:** A source with only a configured entry or synthetic fixture is not live. If a monthly schedule produces no run in the window, arrange a controlled real rerun. If GCP access, egress approval or AWS cluster access is unavailable, report the achieved local pilot and blocker explicitly—do not claim the AWS Kubernetes MVP shipped. Do not route existing Gemini traffic through LiteLLM solely for tracing. LIME remains a next-MVP extension, not an October gate.
