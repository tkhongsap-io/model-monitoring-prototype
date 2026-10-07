# ADR 0002: GCP batch jobs push their run summaries to the monitor

- **Status:** Accepted
- **Date:** 2026-10-07 (records the decision of 2026-10-02 that #41 implemented)
- **Decision owners:** project owner (ta.khongsap); the GCP job developers as senders
- **Risk tier:** R2 — material workflow (measured below; the batch MVP only)
- **Review trigger:** the release sign-off (S4-06), a sender outside GCP, a new kind of
  data in the body, or a change to the trust boundary (for example, no IP allowlist on AWS)

## Context

The October batch MVP grades 10 GCP batch use cases. Each job runs on a schedule, writes
its results in GCP and stops. The monitor runs in GCP on the test host (Sprints 1 to 3)
and in AWS in production (Sprint 4). There is no VPN between GCP and AWS.

The existing rules were written for the pull-only prototype:

- Contract v1.1 (`docs/MONITORING-CONTRACT.md`) is pull-only: the monitor pulls closed
  windows from a producer server.
- `CLAUDE.md` says that the monitor "is a consumer and makes no producer demands", and
  that only the lease-held poller and the worker-token poll advance cursors.

`POST /api/batch/runs` (S1-02, #41) breaks the first rule and adds a new writer. The
`DEVLOG.md` entry of 2026-10-02 asked for this ADR before the code; the code merged first,
so this ADR records the decision after the fact.

## Decision criteria

- Proof of completion: the monitor must know that a run finished and published.
- Least access: no monitor credentials inside the GCP projects of 10 teams.
- Works across clouds with HTTPS only, from GCP to GCP (test host) and GCP to AWS.
- One run stored one time; a stored run never changes.
- No effect on the v1.1 pull lane of the prototype.

## Options considered

### Option A — Push: the job sends one run summary after it publishes (chosen)

The job sends a `batch-run/1` JSON body to `POST /api/batch/runs` with its API key.
Benefits: the send is the proof that the run is complete; no access into GCP storage; one
HTTPS call; the job developer owns the content. Drawbacks: a demand on each job (a new send
step and a body format); a new external writer that needs a trust boundary.

### Option B — Pull from GCP storage

The monitor reads the results from GCS or BigQuery. Benefits: no change in the jobs.
Drawbacks: GCP credentials for 10 projects in the monitor, also in AWS; no clear signal
that a run is complete; the monitor must know each storage layout. Rejected.

### Option C — Contract v1.1 pull from each job

Each job runs a `/telemetry/*` server. Rejected: a batch job has no server that stays up,
and a server for each job is a large change for each team.

## Decision

Option A. GCP batch jobs push one run summary to `POST /api/batch/runs`. This is an
exception to the "no producer demands" and "pull-only" rules, for the batch MVP only.
Contract v1.1 and the prototype pull lane do not change.

**Trust boundary**

| Layer | Control |
|---|---|
| Identity | One API key for each use case (`Authorization: Bearer`). The backend stores only the SHA-256 hash and compares in constant time. A key for one use case cannot write another use case (`403`). No configured key: every request is `401`. |
| Transport | HTTPS only: a private CA on the test host (S1-04), a public or company CA on AWS (S4-01) |
| Network | Test host: a private VPC path; port 443 only from the job network ranges. AWS: only the egress IPs of the jobs (S4-01). |
| Input | Strict schema `batch-run/1` (`400` with field errors, nothing stored); a body size limit (`413`); the key, the header and the body are never logged |
| Surface | Since S1-13 the app serves only the batch MVP API: `POST /api/batch/runs` and the service checks (`/api/health`, `/api/healthz`, `/api/readiness`, `/api/version`). The prototype routes are not mounted; every other path is `404`. |

**No cursor moves.** The receiver writes only the `batch_runs` table. It never reads or
advances a v1.1 telemetry cursor and never writes `live_observations`. The poller stays
the only writer of the pull lane.

**A stored run never changes.** `(use_case_id, run_id)` is unique (migration 8). The same
content again is `200 duplicate` and returns the stored row; other content is `409` and
the stored row stays. There is no update path and no delete path. A resend with a new
trace records `stored_trace_id` on its span (S1-05).

**Risk tier.** Measured with `handbook/risk-tiers.md` of
`tkhongsap-ai-engineering-playbook@5ba9dc8`. Base tier R1: an internal tool, and the RAI
team decides; the monitor never acts on a model. Two escalation rules apply: the system
uses confidential customer data (redacted records from 10 production use cases; names are
hard to remove), and the LLM judge reads untrusted text that can try to change its scores
(prompt injection). Result: **R2**. The prototype stays R1. The project owner accepted R2
on 2026-10-07. Details: [batch MVP intent](../../changes/2026-10-02-batch-monitoring-mvp/intent.md).

## Consequences

### Positive

- The run summary arrives when the run is complete, with no GCP access for the monitor.
- The same API-key method on the test host and on AWS, so the test proves production.
- The pull lane and contract v1.1 are untouched; the prototype keeps working.

### Negative and risk

- A stolen key lets a caller write runs for one use case. Mitigation: one key for each use
  case, the network rules, key rotation with two hashes, and the S2-01 registry. Owner:
  backend and platform.
- Each job must add a send step and keep the body format. Mitigation: one schema with
  examples (S1-01), and S1-02b to align the receiver with the approved schema.
- Records cross from GCP to the monitor, the judge and Langfuse. Mitigation:
  identity-only mode until security approves (S1-08), placeholders for PII before the
  data leaves GCP, and the retention review (S3-05).
- R2 needs a threat model, which the plan did not have. Mitigation: a new Sprint 2 issue
  (S2-11) before real records reach the judge (S2-05).

## Validation and rollback

Validated by `backend/tests/test_batch_runs_api.py` (each acceptance criterion of #4
on the deployed app, no key or body in logs), `test_app_surface.py` (the served
routes; S1-13), `test_batch_runs_store.py`
(migration 8, duplicate, conflict, unique pair), `test_batch_schema.py` and
`test_batch_runs_tracing.py`.

Invalidated by: a sender outside GCP, a need to change a stored run, or a security ruling
against API keys (then a Google identity token, S1-08). To stop the push lane: unset
`BATCH_API_KEY_SHA256`, so every request is `401`; the stored runs stay readable. A
different design supersedes this ADR with a new one.

## Sources

- `changes/2026-10-02-batch-monitoring-mvp/plan.md` (decisions of 2026-10-02 and 2026-10-05)
- `changes/2026-10-02-batch-monitoring-mvp/issues.md` (S1-02, S1-04, S1-05, S1-08, S4-01)
- `changes/2026-10-05-s1-02-batch-runs-api/spec.md`
- `backend/app/api/batch_routes.py`, `backend/app/batch_schema.py`, `backend/app/db.py`
- `changes/2026-10-07-s1-13-batch-only-api/spec.md` (the served surface)
- `handbook/risk-tiers.md` in `tkhongsap-ai-engineering-playbook@5ba9dc8`
