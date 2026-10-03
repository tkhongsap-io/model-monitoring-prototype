# Batch Monitoring MVP — GitHub Issues by Sprint

| | |
|---|---|
| **Date** | 2026-10-03 |
| **Status** | Drafts, not yet posted to GitHub |
| **Related** | [Plan](plan.md) · [One-page summary and flows](summary.md) · [LLM metrics and data standard](llm-metrics-standard.md) |

Each issue below is ready to paste into GitHub. Every feature issue names the issue it is
**tested with**: a sender is proven by the receiver that sees its data arrive, and a
receiver is proven by a real sender. One shared tool (S1-08) follows a single trace ID
through every hop, so each paired test ends with the same question: did this run's data
reach the monitor database and Langfuse with the same trace ID?

## How to read an issue

| Field | Meaning |
|---|---|
| Type | Feature, Infrastructure, Decision, Discovery or Verification |
| Plan task | The matching row in [plan.md](plan.md) |
| Depends on | Issues that must be merged or decided first |
| Tested with | The partner issue used to prove this one works end to end |
| Size | Rough estimate: S (under 1 day), M (1–3 days), L (3–5 days) |
| Acceptance criteria | Checkboxes a reviewer ticks before closing |
| How to test | Exact steps, from unit tests to the paired end-to-end test |

## Test environments

| Name | What runs there | Used for |
|---|---|---|
| **Unit** | `pytest` in `backend/`; OTel in-memory span exporter | Logic, validation, span content |
| **Local stack** | Docker Compose: monitor, Postgres, OTel Collector, self-hosted Langfuse | Integration and paired tests on a laptop |
| **Test host** | The same Compose stack, reachable over HTTPS from the GCP dev project | Tests with real GCP job code |
| **AWS cluster** | Target Kubernetes deployment | Release (Sprint 4) |

## Done for every issue

- Pull request with tests; CI green; `CHANGELOG.md` and `DEVLOG.md` updated when behaviour changes.
- The PR description lists passed, failed, skipped and unavailable checks. An unavailable check is never reported as passed.
- No secrets or tokens anywhere. No text in OTel spans or logs. Fixtures and screenshots use synthetic or placeholder-redacted text only.

## All issues

| ID | Title | Type | Owner | Tested with |
|---|---|---|---|---|
| S1-01 | Walk through one GCP job and map its fields | Discovery | Backend + GCP job developer | Review by GCP developer |
| S1-02 | Run summary JSON body v1 | Feature | Backend | S1-04 (real body validates) |
| S1-03 | Receiving API `POST /api/batch/runs` | Feature | Backend | S1-04 |
| S1-04 | GCP job sends the run summary after publishing | Feature | GCP job developer | S1-03 |
| S1-05 | Test host reachable from GCP | Infrastructure | Platform | S1-04 |
| S1-06 | OTel SDK in the monitor; ingest continues the job's trace | Feature | Backend | S1-07 |
| S1-07 | Minimal OTel Collector in the local stack | Infrastructure | Platform | S1-06 |
| S1-08 | Trace check tool | Feature | Backend | S1-06 + S1-07 |
| S1-09 | Approve redacted records leaving GCP and PII placeholders | Decision | Security | — |
| S1-10 | Inventory of the 10 use cases and October run dates | Discovery | PM + source owners | — |
| S1-11 | First real run end to end | Verification | Backend + GCP job developer | S1-03 + S1-04 + S1-05 |
| S2-01 | Source registry and one token per use case | Feature | Backend | S2-07 |
| S2-02 | Langfuse SDK version and new packages approved | Decision | Backend + project owner | — |
| S2-03 | Collector exports to self-hosted Langfuse | Infrastructure | Platform | S2-04, S2-05 |
| S2-04 | OTel helper for GCP jobs | Feature | Backend + GCP job developer | S2-03 |
| S2-05 | Monitor moves off direct Langfuse SDK v2 calls | Feature | Backend | S2-03 |
| S2-06 | Batch evaluator with the five LLM metrics | Feature | Backend + RAI | S2-05 |
| S2-07 | Onboard 4 use cases | Feature | Job owners + backend | S2-01, S1-08 |
| S2-08 | Dashboard and API for batch runs | Feature | Frontend + backend | S2-07 |
| S2-09 | One run as a single trace, GCP job to score | Verification | Backend + platform | S2-03 + S2-04 + S2-06 |
| S3-01 | Onboard 8 use cases, including split submit and harvest | Feature | Job owners + backend | S1-08 |
| S3-02 | Missed-run detection and alert | Feature | Backend | S3-04 |
| S3-03 | Collector hardening: auth, TLS, redaction, durable queue | Infrastructure | Platform | S3-04, S3-05 |
| S3-04 | Failure and recovery drills | Verification | Backend + platform | S3-02 + S3-03 |
| S3-05 | Security and retention review with leak scan | Verification | Security + platform | S3-03 |
| S3-06 | Kubernetes manifests | Infrastructure | Platform | S4-01 |
| S4-01 | Deploy the stack to the target AWS cluster | Infrastructure | Platform | S4-02 |
| S4-02 | Switch every GCP job to the AWS endpoints | Feature | Job owners + platform | S4-01 |
| S4-03 | Finish all 10 use cases | Feature | Job owners + backend | S4-04 |
| S4-04 | 10-row evidence checklist | Verification | Backend + frontend + RAI | S1-08 |
| S4-05 | Operations drills and runbooks on AWS | Verification | Platform + operations | S4-01 |
| S4-06 | Release sign-off | Decision | RAI + platform owners | S4-04 + S4-05 |

---

## Sprint 1 — Oct 5–9: get data out of GCP

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S1-04 GCP sender | S1-03 receiving API | A real run summary from GCP lands as one row in monitor Postgres | Test host |
| S1-06 monitor OTel | S1-07 Collector | The ingest span reaches the Collector with the trace ID the job sent | Local stack |
| S1-08 trace check tool | S1-06 + S1-07 | One command shows the same trace ID in the database and in the Collector output | Local stack |

### S1-01 — Walk through one GCP job and map its fields

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Discovery | 1.1 | Backend + GCP job developer | — | Review by GCP developer | S |

**What:** Sit with the GCP job developer and go through one job from submit to publish. Find
the exact point where results are published, and map the job to the record fields of the
[standard](llm-metrics-standard.md): which part of the prompt is the instruction
(`question`), which is source material (`retrieval_context`), where the output (`answer`)
is, how a refusal or safety block shows up (`refused`), and whether per-request latency
exists.

**Acceptance criteria**
- [ ] A mapping table: each standard field, where it comes from in the job, and any gap.
- [ ] The "published" moment is identified in the job code (file and function).
- [ ] Where PII can appear (instruction, source material, output) is listed, for the redaction step in S1-04.
- [ ] Batch API or online calls recorded, which decides whether `latency_s` is `null`.

**How to test**
1. The GCP job developer reviews the table and confirms each row against the code.
2. Attach the reviewed table to the issue before closing.

### S1-02 — Run summary JSON body v1

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.2 | Backend | S1-01 | S1-04 (a real body validates) | M |

**What:** Turn the [LLM metrics and data standard](llm-metrics-standard.md) into a JSON
Schema file with example bodies: run identity fields plus the sampled `records`
(`record_id`, `question`, `answer`, `retrieval_context`, `tool_calls`, `refused`,
`latency_s`). Unknown fields are rejected.

**Acceptance criteria**
- [ ] Schema file and 3 examples committed: normal run, partial failure, Batch API run with `latency_s` null. Examples use synthetic text only.
- [ ] Every field has a description; required and optional fields are explicit.
- [ ] `traceparent` follows the W3C Trace Context format.
- [ ] Free text is allowed only in `question`, `answer`, `retrieval_context` and `tool_calls`; no customer ID field exists.
- [ ] Reviewed by the GCP job developer, RAI and security (S1-09).

**How to test**
1. Unit: `pytest` validates every example against the schema; a broken example (missing `run_id`, wrong type) fails validation.
2. Paired with S1-04: the GCP developer generates a body from a real run and it validates against the schema.

### S1-03 — Receiving API `POST /api/batch/runs`

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.3 | Backend | S1-02 | S1-04 | L |

**What:** Add an authenticated endpoint that validates a run summary and stores it once in a
new `batch_runs` table (additive migration in `backend/app/db.py`). Store `trace_id` from
`traceparent`. A stored row is never edited.

**Acceptance criteria**
- [ ] Valid body with a valid token: `201`, one row stored.
- [ ] Same body sent again: `200`, still one row.
- [ ] Same `(use_case_id, run_id)` with different content: `409`, original row unchanged.
- [ ] Invalid body: `400` with field errors; nothing stored.
- [ ] Missing or wrong token: `401`; nothing stored; token never logged.
- [ ] Existing v1.1 live tests still pass; demo-mode routes unaffected.

**How to test**
1. Unit and integration: `pytest` covers each criterion above using the S1-02 examples.
2. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. Paired with S1-04: a real GCP job sends to the test host; check one row exists for that `run_id`.

### S1-04 — GCP job sends the run summary after publishing

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.4 | GCP job developer | S1-02, S1-05 | S1-03 | M |

**What:** Add a step at the end of one GCP job, after publish, that picks a uniform random
sample of records (default 50), replaces phone numbers, emails and national IDs with
`[PHONE]`, `[EMAIL]` and `[NATIONAL_ID]`, builds the run summary and sends it with the
token from GCP Secret Manager. Retry with backoff on network errors
and `5xx`. A send failure must not fail the business job.

**Acceptance criteria**
- [ ] The step runs only after publish succeeds.
- [ ] Retries on timeouts and `5xx`; no retry on `400`, `401` or `409`.
- [ ] The job finishes successfully even when the monitor is unreachable, and logs that the send failed.
- [ ] Sample size follows the registry setting; a run smaller than the sample sends every request.
- [ ] No raw phone number, email or national ID in the body.
- [ ] Token read from Secret Manager; never printed.

**How to test**
1. Unit (GCP repo): the builder produces a body that validates against the S1-02 schema; synthetic PII in input and output becomes placeholders; sample size is respected; the sender retries on a fake `503` and stops on `400`.
2. Paired with S1-03 on the test host: run the job in the GCP dev project. Expected: the job log shows `201`, and the monitor database has one `batch_runs` row with the same `run_id`. Run it again and expect `200` with still one row.
3. Failure check: point the job at a wrong URL; the job still succeeds and logs the failed send.

### S1-05 — Test host reachable from GCP

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | Deadline Tue Oct 6 | Platform | — | S1-04 | M |

**What:** Run the monitor (and later the local stack) on a host the GCP dev project can reach
over HTTPS, with its own database and secrets.

**Acceptance criteria**
- [ ] HTTPS with a valid certificate; plain HTTP refused.
- [ ] Database and Collector ports are not public.
- [ ] Tokens stored as host secrets, not in the repository.

**How to test**
1. From the GCP dev project: `curl https://<test-host>/api/health` returns `200`.
2. `POST /api/batch/runs` without a token returns `401`.
3. Port scan from outside shows only `443` open.
4. Fallback if late: the GCP developer captures a real body to a file and we replay it into the local stack; record that real delivery was not tested.

### S1-06 — OTel SDK in the monitor; ingest continues the job's trace

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.8 | Backend | S1-03, package entry in the Sprint 1 spec | S1-07 | M |

**What:** Add the OpenTelemetry SDK to the backend. `POST /api/batch/runs` starts a
`monitor.ingest` span that continues the trace from the body's `traceparent`. Export over
OTLP/HTTP to the Collector; the endpoint comes from `OTEL_EXPORTER_OTLP_ENDPOINT`.

**Acceptance criteria**
- [ ] `monitor.ingest` has the same trace ID as the incoming `traceparent`, and the job's span as parent.
- [ ] Span attributes: `use_case_id`, `run_id`, result (`stored`, `duplicate`, `rejected`). No body content.
- [ ] With no Collector configured, the API still works and no error is raised.
- [ ] A body without `traceparent` starts a new trace and stores its ID.

**How to test**
1. Unit: in-memory span exporter; assert trace ID, parent span ID and attribute list for each criterion.
2. Paired with S1-07: run the local stack, send an example body with a known `traceparent` using `curl`, and find that trace ID in the Collector output.

### S1-07 — Minimal OTel Collector in the local stack

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 1.9 | Platform | — | S1-06 | S |

**What:** Add the OTel Collector (contrib image) to Docker Compose with an OTLP/HTTP receiver,
the `debug` exporter and the `file` exporter writing to a mounted folder. Langfuse export
comes in S2-03.

**Acceptance criteria**
- [ ] `docker compose up` starts the Collector with a health check.
- [ ] Spans received on OTLP/HTTP appear in the file output.
- [ ] Collector config is in the repository; no secrets in it.

**How to test**
1. Standalone: send synthetic spans with `telemetrygen traces --otlp-http --otlp-insecure` and check the file output contains them.
2. Paired with S1-06: send a run summary to the monitor and find its `monitor.ingest` span in the file output.

### S1-08 — Trace check tool

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.10 | Backend | S1-03 | S1-06 + S1-07 | S |

**What:** A script, `scripts/check_trace.py <trace_id>`, that prints one row per hop: the
monitor `batch_runs` row, the Collector file output and (from S2-03) the Langfuse trace and
score. Every paired test from here on ends by running it.

**Acceptance criteria**
- [ ] Prints found or missing for each hop, with run ID and timestamps.
- [ ] Exits non-zero if any expected hop is missing, so CI and drills can use it.
- [ ] Reads credentials from environment variables; never prints them.

**How to test**
1. Paired with S1-06 + S1-07: send one example body, run the tool with its trace ID; expect "found" for database and Collector.
2. Run it with a random trace ID; expect "missing" everywhere and a non-zero exit.

### S1-09 — Approve redacted records leaving GCP and PII placeholders

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Decision | 1.5 | Security + platform | S1-02 | — | S |

**What:** Approve the data flow in the [standard](llm-metrics-standard.md): placeholder-redacted records go from GCP to the monitor, to the Claude judge (Anthropic API) and to Langfuse; retention period; token handling (Secret Manager, HTTPS only).

**Acceptance criteria**
- [ ] Record fields, placeholder redaction, judge provider and Langfuse storage approved in writing, or blocked with an owner and date.
- [ ] Retention period for stored records set.
- [ ] Token storage, rotation owner and transport approved.

**How to test**
1. The approval is linked in this issue; S1-02's schema matches the approved fields one by one.
2. If not approved by Oct 8: S1-02 ships with run identity only and the judged metrics are Unknown.

### S1-10 — Inventory of the 10 use cases and October run dates

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Discovery | 1.7 | PM + source owners | — | — | M |

**What:** One table with every use case: ID, owner, GCP job, repository, October run dates,
data sensitivity, Batch API or online calls, owner for the task description.

**Acceptance criteria**
- [ ] Exactly 10 rows, each with a named owner.
- [ ] Every use case has at least one October run date, or a booked controlled rerun.
- [ ] Onboarding order for Sprints 2–4 agreed.

**How to test**
1. Each owner confirms their row in the issue comments.

### S1-11 — First real run end to end

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 1.6 | Backend + GCP job developer | S1-03, S1-04, S1-05, S1-09 | — | S |

**What:** The Sprint 1 demo: one real run, sent by the real job, stored and visible through
the monitor API.

**Acceptance criteria**
- [ ] The source owner confirms the run was a real published run.
- [ ] `batch_runs` holds it once; the API shows run ID, status, counts and freshness.
- [ ] Stored records contain placeholders, not raw PII.

**How to test**
1. Trigger or wait for the job's real run.
2. Run `scripts/check_trace.py <trace_id>`; database hop found.
3. Read the run back from the monitor API; attach the output (no secrets) to the issue.

---

## Sprint 2 — Oct 12–16: same path for many jobs, plus evaluation and tracing

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S2-04 GCP OTel helper | S2-03 Collector → Langfuse | The job's spans flow through the Collector into Langfuse, and the run summary lands in monitor Postgres, all with one trace ID | Local stack, then test host |
| S2-05 monitor off SDK v2 | S2-03 Collector → Langfuse | Judge spans arrive through the Collector and the score is attached to the same trace | Local stack |
| S2-06 batch evaluator | S2-05 | The evaluation score appears on the run's trace in Langfuse | Local stack |
| S2-01 registry | S2-07 onboarding | Each real job can write only its own use case | Test host |

### S2-01 — Source registry and one token per use case

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.1 | Backend | S1-03 | S2-07 | M |

**What:** A registry of allowed use-case IDs, each with its own token (stored as a hash).

**Acceptance criteria**
- [ ] Token for use case A writing use case B: `403`.
- [ ] Unknown use-case ID: `403`.
- [ ] Rotating a token does not lose stored runs.

**How to test**
1. Unit and integration: `pytest` for each criterion.
2. Paired with S2-07: each onboarded job sends with its own token and succeeds; a swapped token is rejected.

### S2-02 — Langfuse SDK version and new packages approved

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Decision | Deadline Mon Oct 12 | Backend + project owner | — | — | S |

**What:** Decide Langfuse Python SDK v2 or v3, and approve the `opentelemetry-*` packages with
versions in the Sprint 2 spec.

**Acceptance criteria**
- [ ] Decision and reason recorded in the spec; package list with pinned version ranges approved.

**How to test**
1. `backend/requirements.txt` changes in S2-05 match the approved list exactly.

### S2-03 — Collector exports to self-hosted Langfuse

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 2.4 | Platform | S1-07 | S2-04, S2-05 | L |

**What:** Add self-hosted Langfuse (web, worker, Postgres, ClickHouse, Redis, S3-compatible
storage) to Compose. Add an `otlphttp` exporter in the Collector that sends to Langfuse's
OTLP endpoint (`/api/public/otel`) with project keys from environment variables. Keep the
file exporter for tests. Extend S1-08 to query Langfuse.

**Acceptance criteria**
- [ ] `docker compose up` brings up Langfuse with persistent volumes; data survives a restart.
- [ ] Spans sent to the Collector appear as traces in Langfuse.
- [ ] Langfuse keys only in environment files that are not committed.
- [ ] `scripts/check_trace.py` reports the Langfuse hop.

**How to test**
1. Standalone: `telemetrygen` spans arrive in Langfuse; read back with the Langfuse public API (`GET /api/public/traces/{traceId}`).
2. Restart: `docker compose restart`; the same trace is still there.
3. Paired with S2-04 and S2-05 (see those issues).

### S2-04 — OTel helper for GCP jobs

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.7 | Backend + GCP job developer | S1-04, S1-06 | S2-03 | L |

**What:** A small shared helper that GCP jobs import to send OTel spans: a root `batch.run`
span; child spans `batch.submit`, `batch.harvest`, `batch.publish`; one span per Gemini call
with model and token counts (OTel GenAI conventions). It also puts the current
`traceparent` into the run summary. Attributes pass through an allowlist, so prompts and
customer text cannot be attached.

**Acceptance criteria**
- [ ] One trace per run; the run summary's `traceparent` matches the root span.
- [ ] Gemini call spans carry model, input tokens, output tokens and real call duration.
- [ ] Attributes outside the allowlist are dropped, with a debug log of the dropped key name only.
- [ ] Export failure never fails the job.
- [ ] Added to the first job (the one from S1-04).

**How to test**
1. Unit (GCP repo): in-memory exporter; assert span names, parent-child links, attributes, and that a forbidden attribute (for example `prompt`) is dropped.
2. Local paired test with S2-03: run the job code locally against a recorded Gemini response, with `OTEL_EXPORTER_OTLP_ENDPOINT` pointed at the local Collector and the run summary pointed at the local monitor.
3. Real paired test with S2-03 on the test host: run the job in the GCP dev project.
4. For both: run `scripts/check_trace.py <trace_id>`. Expected: the `batch_runs` row in monitor Postgres, the spans in the Collector output, and one Langfuse trace containing both the GCP spans and `monitor.ingest`, all with the same trace ID.

### S2-05 — Monitor moves off direct Langfuse SDK v2 calls

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.6 | Backend | S2-02, S2-03 | S2-03 | L |

**What:** The chatbot judge currently calls the Langfuse SDK v2 directly
(`adapters/llm_eval/stores.py`). Replace that with OTel spans through the Collector, and
write scores with the Langfuse score API on the same trace ID. The SQLite and Postgres
stores the dashboard reads stay as they are.

**Acceptance criteria**
- [ ] No direct Langfuse trace calls remain; scores use the score API with the span's trace ID.
- [ ] Existing chatbot judge tests pass unchanged.
- [ ] Langfuse unavailable: judging and grading continue; the score write is recorded for retry.
- [ ] Sending the same score twice does not create a duplicate (stable score ID).

**How to test**
1. Unit: in-memory exporter for spans; a fake score API for score calls, including a failing one.
2. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. Paired with S2-03: run one judged chatbot window in the local stack; `scripts/check_trace.py` shows the trace and its score in Langfuse.

### S2-06 — Batch evaluator with the five LLM metrics

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.3 | Backend + RAI | Task description (Oct 14), S2-05 | S2-05 | L |

**What:** Grade each stored run with the prototype's LLM lane: map records to the v1.1
`Trace` shape, reuse the Claude judge and aggregation in
`backend/app/adapters/llm_eval/live_http.py`, and grade with `engines/health.py`. Three
changes from the [standard](llm-metrics-standard.md): the judge prompt takes the use
case's task description; a placeholder in the answer counts as PII exposure; the judge cap
equals the registry sample size. Emit a `monitor.evaluate` span and write scores to
Langfuse.

**Acceptance criteria**
- [ ] The five metrics, bands and grading match the chatbot lane exactly.
- [ ] Scores stored with task description version, judge model, sample size and run ID.
- [ ] Fewer than 8 records, judge failure, or `latency_s` all null give Unknown with a reason, never Green.
- [ ] Chatbot (`AICT-L02`) tests pass unchanged.
- [ ] Evaluation problems are not shown as ingest problems, and the reverse.

**How to test**
1. Unit: `pytest` with a fake judge for each Unknown reason, the band boundaries (for example hallucination exactly 0.02 is Red), and placeholder PII counted only in `answer`.
2. Paired with S2-05: evaluate a stored real run in the local stack; `scripts/check_trace.py` shows `monitor.evaluate` and the score on the same trace.

### S2-07 — Onboard 4 use cases

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.2 | Job owners + backend | S2-01, S2-04, S1-10 | S2-01, S1-08 | L |

**What:** Add the run summary step and the OTel helper to 4 different jobs, including one with
a different output shape.

**Acceptance criteria**
- [ ] 4 real runs received, each confirmed by its owner.
- [ ] Each has its own token and one trace per run.
- [ ] Test files or configuration entries do not count.

**How to test**
1. For each job: run on its schedule or in the dev project, then `scripts/check_trace.py <trace_id>` shows all hops.
2. Record the 4 trace IDs in this issue.

### S2-08 — Dashboard and API for batch runs

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.5 | Frontend + backend | S2-06 | S2-07 | M |

**What:** Show each batch use case with the same five LLM metric cards the chatbot uses, plus
last run, freshness, status, Unknown reasons and a link to its Langfuse trace.

**Acceptance criteria**
- [ ] Data comes from read-only monitor API routes; the browser never calls Langfuse or the database.
- [ ] Missing score or trace shows a clear reason.
- [ ] No Langfuse keys or tokens in the browser bundle.

**How to test**
1. API tests for each state: scored, Unknown, stale, no trace.
2. `pnpm run typecheck`; `pnpm run build:live` and `pnpm run check:strict-live` in CI.
3. Paired with S2-07: the 4 onboarded use cases appear with correct freshness.

### S2-09 — One run as a single trace, GCP job to score

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | Sprint 2 exit | Backend + platform | S2-03, S2-04, S2-06 | — | S |

**What:** The Sprint 2 demo.

**Acceptance criteria**
- [ ] One real run shows in Langfuse as one trace: GCP spans, `monitor.ingest`, `monitor.evaluate`, and the score.
- [ ] The dashboard shows the same run with a working trace link.

**How to test**
1. Run `scripts/check_trace.py <trace_id>`; every hop found.
2. Screenshot of the Langfuse trace and the dashboard row (placeholder-redacted text only) attached.

---

## Sprint 3 — Oct 19–23: scale to 8 and harden

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S3-03 Collector hardening | S3-04 drills | Spans survive a Langfuse outage and arrive after recovery, once | Local stack |
| S3-03 Collector hardening | S3-05 leak scan | Forbidden attributes are removed before storage | Local stack, test host |
| S3-02 missed-run alert | S3-04 drills | A run that never arrives raises a delivery alert, not a quality alert | Local stack |

### S3-01 — Onboard 8 use cases, including split submit and harvest

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 3.1 | Job owners + backend | S2-07 | S1-08 | L |

**What:** Reach 8 use cases. For jobs where submit and harvest run in different executions,
store the submit `traceparent` with the batch job ID so harvest continues the same trace.

**Acceptance criteria**
- [ ] 8 real runs confirmed by owners.
- [ ] A submitted-only job sends nothing.
- [ ] Split submit and harvest still show as one trace.

**How to test**
1. Per job: `scripts/check_trace.py <trace_id>` shows all hops; record trace IDs here.
2. Split job: the Langfuse trace shows submit and harvest spans under the same root.

### S3-02 — Missed-run detection and alert

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 3.2 | Backend | S1-10 | S3-04 | M |

**What:** Use each use case's schedule to detect a run that did not arrive in time, and alert
through the existing alert path.

**Acceptance criteria**
- [ ] Late run: use case shown as stale, alert opened as a delivery problem.
- [ ] Run arrives: alert resolves.
- [ ] Never turns a model-quality grade Green or Red.

**How to test**
1. Unit: fixed clock; expected run missing past the grace period opens an alert; arrival resolves it.
2. Paired with S3-04: stop one job's send in the drill and watch the alert open and resolve.

### S3-03 — Collector hardening: auth, TLS, redaction, durable queue

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 3.4 | Platform | S2-03, approved attribute list | S3-04, S3-05 | L |

**What:** Require a token on the OTLP receiver, use TLS, drop attributes outside the approved
list, limit memory, and keep a disk-backed retry queue so spans survive a Langfuse outage.

**Acceptance criteria**
- [ ] OTLP without a valid token is rejected.
- [ ] Attributes outside the allowlist never reach Langfuse.
- [ ] Langfuse down for 10 minutes: spans arrive after recovery, without duplicates.
- [ ] Collector restart does not lose queued spans.

**How to test**
1. Send spans without a token; expect rejection in the Collector log.
2. Send a span with a forbidden attribute; it is missing in Langfuse.
3. Outage and restart steps in S3-04.

### S3-04 — Failure and recovery drills

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 3.3 | Backend + platform | S3-02, S3-03 | — | M |

**What:** Break each part on purpose and check nothing is lost or duplicated.

**Acceptance criteria**

| Drill | Expected result |
|---|---|
| Monitor down while a job sends | Job retries; run stored once after recovery |
| Collector down | Run summary still stored; spans arrive after recovery or the gap is recorded |
| Langfuse down | Spans queued; score write retried; one score per run after recovery |
| Monitor restart mid-ingest | No half-written run; resend succeeds once |
| Job never sends | Missed-run alert (S3-02) |

**How to test**
1. Run each drill in the local stack, then `scripts/check_trace.py` for the affected trace IDs.
2. Record results (pass, fail, not run) in this issue.

### S3-05 — Security and retention review with leak scan

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 3.4 | Security + platform + source owners | S3-03, S3-01 | S3-03 | M |

**What:** Review identity, transport, secrets and retention for all onboarded use cases, and
scan stored data for leaks.

**Acceptance criteria**
- [ ] No raw phone numbers, emails, national IDs or credentials in `batch_runs`, Langfuse, logs or API responses; OTel spans and logs contain no text at all.
- [ ] Retention period set for monitor Postgres and Langfuse.
- [ ] Exceptions listed with owner and date.

**How to test**
1. A leak scan script searches a sample of stored runs, Langfuse traces and logs for forbidden patterns (token formats, email, phone, ID numbers); expect zero matches.
2. Unauthorized requests to the API and Collector are rejected.

### S3-06 — Kubernetes manifests

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 3.5 | Platform | S3-03 | S4-01 | L |

**What:** Manifests for the monitor, Collector, Langfuse and their storage, with secrets, TLS
ingress, health checks, resource limits and a rollback path.

**Acceptance criteria**
- [ ] Manifests pass schema validation.
- [ ] Smoke test on a disposable cluster (for example kind) if available; otherwise recorded as not run.
- [ ] Backup, restore and rollback steps written.

**How to test**
1. `kubectl apply --dry-run=server` or `kubeconform` passes.
2. On a disposable cluster: send one example run and spans; `scripts/check_trace.py` shows all hops.

---

## Sprint 4 — Oct 26–30: AWS release and handoff

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S4-02 jobs switched to AWS | S4-01 AWS stack | Real runs and spans from GCP arrive in the AWS monitor and Langfuse | AWS cluster |
| S4-03 all 10 use cases | S4-04 evidence checklist | Every use case has a real run with matching trace and score | AWS cluster |

### S4-01 — Deploy the stack to the target AWS cluster

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 4.1 | Platform | S3-06, cluster access | S4-02 | L |

**What:** Deploy the monitor, Collector, Langfuse and backing services to the target cluster.

**Acceptance criteria**
- [ ] Only the monitor API and the authenticated Collector endpoint are reachable from GCP; databases are private.
- [ ] Data survives a pod restart.
- [ ] Cluster name and deployed version recorded.

**How to test**
1. Send one example run and spans from a GCP dev machine; `scripts/check_trace.py` shows all hops.
2. Delete the monitor and Langfuse pods; after restart, the same trace and run are still there.

### S4-02 — Switch every GCP job to the AWS endpoints

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 4.2 | Job owners + platform | S4-01 | S4-01 | M |

**What:** Point each job's run summary URL and OTLP endpoint at AWS; rotate tokens for
production.

**Acceptance criteria**
- [ ] Each job's next run arrives in AWS with its trace in Langfuse.
- [ ] Test host tokens revoked.

**How to test**
1. After each job's next run, `scripts/check_trace.py <trace_id>` against AWS shows all hops.

### S4-03 — Finish all 10 use cases

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 4.3 | Job owners + backend | S4-02 | S4-04 | L |

**What:** Onboard the last use cases and get a real run for each, on schedule or as an agreed
controlled rerun.

**Acceptance criteria**
- [ ] 10 owner-confirmed real runs in AWS.
- [ ] No test data or configuration-only entries counted.

**How to test**
1. Covered by the S4-04 checklist.

### S4-04 — 10-row evidence checklist

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 4.4 | Backend + frontend + RAI | S4-03 | S1-08 | M |

**What:** One table with a row per use case: run ID, completion time, freshness, score or
Unknown reason, trace ID, and the result of `scripts/check_trace.py`.

**Acceptance criteria**
- [ ] 10 rows filled in; trace and score IDs match between the monitor and Langfuse.
- [ ] RAI accepts what the dashboard shows, including any Unknown.

**How to test**
1. Run `scripts/check_trace.py` for all 10 trace IDs; attach the output.

### S4-05 — Operations drills and runbooks on AWS

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 4.5 | Platform + operations | S4-01 | — | M |

**What:** Repeat the S3-04 drills on the cluster, plus backup and restore and rollback; write
runbooks.

**Acceptance criteria**
- [ ] Restore and rollback tested with no duplicates or data loss.
- [ ] Runbooks name service owners, source owners, token rotation and escalation.

**How to test**
1. Run each drill; check affected trace IDs with `scripts/check_trace.py`; record results.

### S4-06 — Release sign-off

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Decision | 4.6 | RAI + platform owners | S4-04, S4-05 | — | S |

**What:** Approve the release only on evidence.

**Acceptance criteria**
- [ ] 10 of 10 real use cases and the AWS drills passed; otherwise publish the pilot result and its open blockers.
- [ ] Any unmet item recorded with owner and next action.

**How to test**
1. Reviewers check the S4-04 checklist and the S4-05 drill record.
