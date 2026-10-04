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

## Fixed versions (checked 2026-10-03)

Use these exact versions. Do not use `latest`. To change a version, change this table in a
pull request first.

| Component | Image or package | Version | Note |
|---|---|---|---|
| Python (backend) | `python:3.12.15-slim-bookworm` | 3.12.15 | Released 2026-10-01. Python 3.12 gets security fixes only, until 2028-10-31. |
| PostgreSQL (monitor and Langfuse) | `postgres:17.11-bookworm` | 17.11 | Released 2026-08-10. PostgreSQL 17 is supported until 2029-11-08. |
| OTel Collector | `otel/opentelemetry-collector-contrib` | 0.161.0 | Newest image on Docker Hub. Release 0.162.0 (2026-09-29) has no Docker Hub image yet. |
| Langfuse web | `langfuse/langfuse` | 4.50.0 | Released 2026-10-02 |
| Langfuse worker | `langfuse/langfuse-worker` | 4.50.0 | Must be the same version as Langfuse web |
| ClickHouse | `clickhouse/clickhouse-server` | 25.12.11.4 | Newest patch of the 25.12 line that the Langfuse Compose file uses. Version 26.9 exists, but Langfuse does not use it. |
| Redis | `redis` | 7.4.11 | Newest patch of the 7 line that the Langfuse Compose file uses. Version 8 exists, but Langfuse does not use it. |
| S3 storage (MinIO) | `cgr.dev/chainguard/minio` | Fix by image digest | The image that the Langfuse Compose file uses. The free Chainguard image has only the `latest` tag, so record its digest. |
| Langfuse Python SDK | `langfuse` | `>=4.16,<5` | S2-02 |
| Langfuse Helm chart | `langfuse/langfuse` (langfuse-k8s) | 2.1.3 | Released 2026-09-28. Set the image tags to Langfuse 4.50.0 in the values file (S3-06). |

## Rule for prototype code (decided 2026-10-03)

The three prototype use cases (churn `AICT-L01`, chatbot `AICT-L02`, NBA `AICT-L03`) are a
scaffold. The real work is the GCP use cases.

| Code type | Example | Rule |
|---|---|---|
| Shared code: the GCP path uses it | The judge and the aggregation in `live_http.py`, `engines/health.py`, the alerts, the worker lease, the portfolio endpoints, the Langfuse settings in `config.py` | Keep it. Keep its tests. If a change breaks it, fix it. |
| Prototype-only code: the GCP path does not use it | The v1.1 telemetry adapter, the ML lane (Evidently, NannyML), the explanations (LIME, SHAP), the label backfill, the demo and scenario routes, the chatbot's Langfuse v2 store | Do not maintain it. If a change breaks it, remove it in the same pull request. Do not fix it. |

Before you remove code, search the repository to make sure that the GCP path does not use
it. The test host and AWS do not configure the prototype use cases. S4-07 removes the
remaining prototype-only code.

## Done for every issue

- Pull request with tests; CI green; `CHANGELOG.md` and `DEVLOG.md` updated when behaviour changes.
- The PR description lists passed, failed, skipped and unavailable checks. An unavailable check is never reported as passed.
- No secrets or tokens anywhere. No text in OTel spans or logs. Fixtures and screenshots use synthetic or placeholder-redacted text only.

## All issues

| ID | Title | Type | Owner | Tested with |
|---|---|---|---|---|
| S1-01 | Map one GCP job and write JSON body v1 | Feature | GCP job developer (backend reviews) | S1-04 (a real body validates) |
| S1-02 | *Merged into S1-01* | — | — | — |
| S1-03 | Receiving API `POST /api/batch/runs` with API key | Feature | Backend | S1-04 |
| S1-04 | GCP job sends the run summary after publishing | Feature | GCP job developer | S1-03 |
| S1-05 | Deploy the monitor backend to a test host reachable from GCP | Infrastructure | Platform | S1-04 |
| S1-06 | OTel in the GCP job and the monitor: one trace per run | Feature | GCP job developer + backend | S1-07 |
| S1-07 | Minimal OTel Collector and front door (local stack and test host) | Infrastructure | Platform | S1-06 |
| S1-08 | Trace check tool | Feature | Backend | S1-06 + S1-07 |
| S1-09 | Security approval for the Sprint 1 data flow | Decision | Security | — |
| S1-10 | Inventory of the 10 use cases and October run dates | Discovery | PM + source owners | — |
| S1-11 | First real run end to end | Verification | Backend + GCP job developer | S1-08 (trace check tool) |
| S1-12 | Database accounts for the backend and the developers | Infrastructure | Platform + backend | S1-03, S1-08 |
| S2-01 | Source registry: YAML settings and API key hashes | Feature | Backend + platform | S2-07 |
| S2-02 | Langfuse SDK v4 in the backend, and package approval | Decision + Feature | Backend + project owner | S2-06 |
| S2-03 | Collector exports to self-hosted Langfuse | Infrastructure | Platform | S2-04, S2-06 |
| S2-04 | OTel helper file for the GCP jobs | Feature | GCP job developer (backend reviews) | S2-03 |
| S2-05 | *Removed: prototype-only code (see S2-02)* | — | — | — |
| S2-06 | Batch evaluator with the five LLM metrics | Feature | Backend + RAI | S2-03 |
| S2-07 | Onboard 4 use cases | Feature | Job owners + backend | S2-01, S1-08 |
| S2-08 | Dashboard shows the GCP use cases with the current UI | Feature | Backend | S2-07 |
| S2-09 | One run as a single trace, GCP job to score | Verification | Backend + platform | S2-03 + S2-04 + S2-06 |
| S3-01 | Onboard 8 use cases, including split submit and harvest | Feature | Job developers + backend + platform | S1-08 |
| S3-02 | Delivery lane: missed-run and failed-job alerts | Feature | Backend | S3-04 |
| S3-03 | Collector hardening: attribute filter, memory limit, disk queue | Infrastructure | Platform | S3-04, S3-05 |
| S3-04 | Failure and recovery drills | Verification | Backend + platform | S3-02 + S3-03 |
| S3-05 | Security and retention review with leak scan | Verification | Security + platform | S3-03 |
| S3-06 | Kubernetes deployment files: Langfuse Helm chart and our manifests | Infrastructure | Platform | S4-01 |
| S4-01 | Deploy the stack to the target AWS cluster | Infrastructure | Platform | S4-02 |
| S4-02 | Switch every GCP job to the AWS endpoints | Feature | Job owners + platform | S4-01 |
| S4-03 | Finish all 10 use cases | Feature | Job owners + backend | S4-04 |
| S4-04 | 10-row evidence checklist | Verification | Backend + frontend + RAI | S1-08 |
| S4-05 | Operations drills and runbooks on AWS | Verification | Platform + operations | S4-01 |
| S4-06 | Release sign-off | Decision | RAI + platform owners | S4-04 + S4-05 |
| S4-07 | Remove the prototype-only code | Feature | Backend | Full test suite |

---

## Sprint 1 — Oct 5–9: get data out of GCP

> Review status (2026-10-03): Sprint 1 review complete. S1-07 to S1-12 are written in
> ASD-STE100; S1-01 to S1-06 change to STE in the final pass. Issue IDs stay stable during the review; S1-02 is merged into S1-01, and the
> IDs will be renumbered after all sprints are reviewed.

**Two channels, one trace ID**

| Channel | Carries | Path | If it fails |
|---|---|---|---|
| Receiving API (S1-03, S1-04) | The run summary: the official data | GCP job → HTTPS `POST` → monitor → Postgres | Job retries; the run must arrive |
| OpenTelemetry (S1-06, S1-07) | Timing of each step and the trace ID | GCP job and monitor → OTLP/HTTP → Collector | Data still arrives; the trace has a gap |

The GCP job's OTel SDK adds a W3C `traceparent` header to its API call automatically. The
monitor reads that header, so its spans join the job's trace and the trace ID is saved
with the stored run.

**Who does what**

| Track | Issues | Owner |
|---|---|---|
| GCP side | S1-01, S1-04, S1-06 part A | GCP job developer |
| Monitor side | S1-03, S1-06 part B, S1-08 | Backend |
| Infrastructure | S1-05, S1-07, S1-12 | Platform (firewall and certificates: your team) |

Both tracks start Monday using the draft schema from S1-01 and meet on the test host.

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S1-04 GCP sender | S1-03 receiving API | A real run summary from GCP lands as one row in monitor Postgres | Test host |
| S1-06 part A, GCP OTel | S1-07 Collector | The job's spans reach the Collector | Test host |
| S1-06 part B, monitor OTel | S1-06 part A + S1-07 | The monitor's span has the same trace ID as the job's root span | Test host |
| S1-08 trace check tool | S1-06 + S1-07 | One command shows the same trace ID in the database and in the Collector output | Local stack, then test host |

### S1-01 — Map one GCP job and write JSON body v1

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.1 + 1.2 | GCP job developer; backend reviews and approves | — | S1-04 (a real body validates) | M |

**What:** The GCP job developer maps one job to the record fields of the
[standard](llm-metrics-standard.md) and writes the JSON Schema for the run summary, with
example bodies. The schema lives in this repository because the monitor validates every
request against it, so backend reviews and approves it. There is no separate mapping
table: each field's description in the schema says where its value comes from in the job.

Questions the developer answers in the schema or the pull request:
- Where is the "results published" point (file and function)? The send step goes after it.
- Which part of the prompt is the instruction (`question`) and which is source material (`retrieval_context`)?
- How does a refusal or safety block show up (`refused`)?
- Does the job use the Gemini Batch API (`latency_s` is `null`) or online calls?
- Where can PII appear? The redaction in S1-04 covers those places.
- When the job fails, what does it log today, and can it still send a run summary with status `failed`?

**Acceptance criteria**
- [ ] Schema file and 4 examples committed: normal run, partial failure, Batch API run with `latency_s` null, and an identity-only run (S1-04). Synthetic text only.
- [ ] The schema accepts `records: []` with the reason `records_not_approved`. This is the identity-only mode.
- [ ] Every field has a description that includes its source in the job; required and optional fields are explicit; unknown fields are rejected.
- [ ] Free text only in `question`, `answer`, `retrieval_context` and `tool_calls`; no customer ID field.
- [ ] No trace field in the body: the trace ID travels in the `traceparent` HTTP header (S1-06).
- [ ] Logging agreed with the GCP developer: the job writes a log entry when the job fails and when sending to the monitor fails, and the monitor team can read those logs (access or export) during the pilot.
- [ ] Reviewed by backend, RAI and security (S1-09).

**How to test**
1. Unit: `pytest` validates every example against the schema; a broken example (missing `run_id`, wrong type, unknown field) fails.
2. Paired with S1-04: a body built from a real run validates against the schema.

### S1-02 — Merged into S1-01

The JSON body work is now part of S1-01, owned by the GCP job developer.

### S1-03 — Receiving API `POST /api/batch/runs` with API key

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.3 | Backend | S1-01 (draft schema is enough to start) | S1-04 | L |

**What:** Add an endpoint that checks an API key, validates the run summary against the
S1-01 schema, and stores it once in a new `batch_runs` table (additive migration in
`backend/app/db.py`). A stored row is never edited. The trace ID comes from the
`traceparent` header through the OTel context (S1-06 part B) and is saved with the row.

**Authentication: static API key now, Google identity token later**

There is no VPN between GCP and AWS yet, so the request crosses the internet. Three layers
protect it:

| Layer | How | Owner |
|---|---|---|
| API key | `Authorization: Bearer <key>`. A random key of at least 32 bytes for this use case. The GCP job reads it from Secret Manager. The monitor stores only its SHA-256 hash and compares in constant time. | Backend + GCP developer |
| Encryption | HTTPS only, so the key is never visible on the network (S1-05) | Platform |
| Network | Firewall allows only the GCP job's egress IP, for example a Cloud NAT static IP (S1-05) | Your team |

Options considered:

| Option | Shared secret | Effort | Decision |
|---|---|---|---|
| Static API key + HTTPS + IP allowlist | Yes | Low; same pattern as the monitor's existing tokens | **Sprint 1** |
| Google service-account ID token (OIDC): the job gets a Google-signed token; the monitor checks the signature and the service-account email | No | Medium; needs the `google-auth` package (plan entry) | Not in October. Only if security requires it (S1-09). |
| Mutual TLS | No | High; a client certificate for every job | Not planned |
| VPN or private link | — | Depends on network team | Not available yet |

**Acceptance criteria**
- [ ] Valid body with a valid key: `201`, one row stored.
- [ ] Same body sent again: `200`, still one row.
- [ ] Same `(use_case_id, run_id)` with different content: `409`, original row unchanged.
- [ ] Invalid body: `400` with field errors; nothing stored. This includes unknown fields, a missing record field, `latency_s` of `0`, and more records than the sample size allows.
- [ ] Missing or wrong key: `401`; nothing stored; the key and the body are never logged.
- [ ] Records stored inside the run exactly as received; `record_id` kept for the evaluator.
- [ ] An identity-only body (`records: []`, reason `records_not_approved`) is stored. Later, the four judged metrics for this run show "Unknown" with this reason.
- [ ] Existing v1.1 live tests still pass; demo-mode routes unaffected.

**How to test**
1. Unit and integration: `pytest` covers each criterion above using the S1-01 examples.
2. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. Paired with S1-04: a real GCP job sends to the test host; check one row exists for that `run_id`.

### S1-04 — GCP job sends the run summary after publishing

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.4 | GCP job developer | Build: S1-01. End-to-end test: S1-03 and S1-05 | S1-03 | M |

**What:** This is a feature in the GCP job's code, not a test step. Add a step after publish
that picks a uniform random sample of records (default 50), replaces phone numbers, emails
and national IDs with `[PHONE]`, `[EMAIL]` and `[NATIONAL_ID]`, builds the run summary and
sends it with the API key from Secret Manager. Retry with backoff on network errors and
`5xx`. A send failure must not fail the business job.

**Identity-only mode (decided 2026-10-03).** A setting `SEND_RECORDS` controls the
records. Until security approves (S1-09), the setting is off. Then the job sends only the
run identity, with `records: []` and the reason `records_not_approved`. No text leaves GCP.
With this mode, the team can test the send step, the API key, the retries and OTel from
6 October. When security approves, set `SEND_RECORDS` to on. No code change is necessary.

The developer can build and unit test it from Monday with the S1-01 schema and a fake
server. Only the end-to-end test waits for the real API (S1-03) on the test host (S1-05).

**Acceptance criteria**
- [ ] The step runs only after publish succeeds.
- [ ] Retries on timeouts and `5xx`; no retry on `400`, `401` or `409`.
- [ ] The job finishes successfully even when the monitor is unreachable.
- [ ] Every failed send writes a log entry with `run_id`, HTTP status or error type, and attempt number; never the key or the body.
- [ ] A failed job writes a log entry, and sends a `failed` run summary if S1-01 agreed it can.
- [ ] Sample size follows the setting; a run smaller than the sample sends every request.
- [ ] No raw phone number, email or national ID in the body.
- [ ] With `SEND_RECORDS` off, the body has `records: []` and the reason `records_not_approved`. The default is off.
- [ ] HTTPS certificate is verified. With a private or self-signed certificate (S1-05), the job trusts that CA file; it never turns verification off.

**How to test**
1. Unit (GCP repo): the body validates against the S1-01 schema; synthetic PII becomes placeholders; sample size is respected; the sender retries on a fake `503`, stops on `400`, and logs each failure.
2. Paired with S1-03 on the test host: run the job in the GCP dev project. Expected: the job log shows `201`, and the monitor database has one `batch_runs` row with the same `run_id`. Run it again: `200`, still one row.
3. Failure check: point the job at a wrong URL; the job still succeeds, and Cloud Logging shows the failed-send entries.
4. Identity-only check: with `SEND_RECORDS` off, run the job. Make sure that the stored run has no records and has the reason `records_not_approved`.

### S1-05 — Deploy the monitor backend to a test host reachable from GCP

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | Deadline Tue Oct 6 | Platform | Prerequisites below | S1-04 | M |

**What:** Deploy the monitor backend, its database and the Collector (S1-07) on a test host
the GCP dev project can reach.

**Prerequisites (ask the network team first)**

| Question | Why it matters | Owner |
|---|---|---|
| Where does the test host run (AWS account, VM or other)? | Decides firewall and certificate options | Your team |
| How is traffic between GCP and that host allowed today? | No VPN yet; requests cross the internet | Network team |
| Can port `443` open for one front door (S1-07)? The front door serves both the API and the Collector | GCP spans and API calls both need a path; one port, one certificate, one allowlist | Network team |
| What is the GCP job's egress IP (for example Cloud NAT static IP)? | Firewall allowlist (S1-03 network layer) | GCP developer |
| Public DNS name for the host? | Needed for a public certificate | Your team |
| Certificate: public CA or private / self-signed? | See below | Your team |

**Certificate options — both are real HTTPS**

| Option | Needs | GCP job side |
|---|---|---|
| Public CA (for example Let's Encrypt or AWS Certificate Manager) | A public DNS name and a way to prove ownership (DNS or HTTP challenge) | Nothing; trusted by default |
| Private CA or self-signed | Nothing public; we create and rotate the certificate | Job trusts our CA file (S1-04); verification stays on |

Plain HTTP is not allowed: the API key would travel unencrypted.

**Acceptance criteria**
- [ ] Prerequisites answered and recorded in this issue.
- [ ] Monitor backend, Postgres and Collector running on the test host.
- [ ] HTTPS on the API (public or private CA); plain HTTP refused.
- [ ] Only the GCP egress IP can reach the API and the OTLP endpoint; the database port is closed to the internet.
- [ ] API key and other secrets stored as host secrets, not in the repository.

**How to test**
1. From the GCP dev project: `curl https://<test-host>/api/health` returns `200` (with `--cacert` for a private CA).
2. From an IP that is not allowlisted: the connection is refused.
3. `POST /api/batch/runs` without a key returns `401`.
4. Port scan from outside shows only the agreed ports.
5. Fallback if late: the GCP developer saves a real body to a file and we replay it into the local stack; record that real delivery was not tested.

### S1-06 — OTel in the GCP job and the monitor: one trace per run

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.8 | Part A: GCP job developer. Part B: backend | S1-04 (A), S1-03 (B), package entries in the Sprint 1 spec | S1-07 | M + M |

**What:** Add the OpenTelemetry SDK on both sides so one batch run is one trace.

| Step | Where | What happens |
|---|---|---|
| 1 | GCP job (part A) | Start a root span `batch.run` with `use_case_id` and `run_id` |
| 2 | GCP job (part A) | Child spans `batch.submit`, `batch.harvest`, `batch.publish`, `batch.send` |
| 3 | GCP job (part A) | The API call uses an OTel-instrumented HTTP client, which adds the `traceparent` header automatically |
| 4 | Monitor (part B) | FastAPI instrumentation reads the header; the `monitor.ingest` span becomes a child of the job's `batch.send` span |
| 5 | Monitor (part B) | The trace ID is saved in the `batch_runs` row |
| 6 | Both | Spans are exported over OTLP/HTTP to the Collector (S1-07) |

Gemini call spans, token counts and the attribute allowlist come in Sprint 2 (S2-04).

**Acceptance criteria**
- [ ] Part A: one trace per run; `batch.send` is the parent of the HTTP client span; the request carries `traceparent`.
- [ ] Part B: `monitor.ingest` has the same trace ID as the job's root span; the `batch_runs` row stores that trace ID.
- [ ] A request without `traceparent` starts a new trace on the monitor, and its ID is stored.
- [ ] Spans carry IDs and status only (`use_case_id`, `run_id`, result); no text from the body.
- [ ] If the Collector is unreachable, the job and the API still work; the job logs the export failure.

**How to test**
1. Unit, part A (GCP repo): in-memory span exporter; check span names, parent links, and that the outgoing request has a `traceparent` header.
2. Unit, part B (monitor): send a request with a known `traceparent`; check the span's trace ID and parent, and the stored trace ID.
3. Paired with S1-07 on the test host: run the job; find the job's spans and the monitor's span with the same trace ID in the Collector output; run `scripts/check_trace.py <trace_id>`.
4. Fallback if GCP cannot reach the Collector yet: the job exports spans to Cloud Logging; the trace still links because the header reaches the monitor.

### S1-07 — Minimal OTel Collector and front door (local stack and test host)

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 1.9 | Platform | Local: none. Test host: S1-05 | S1-06 | M |

**What:** Add the OTel Collector to Docker Compose. Use the contrib image with a fixed
version. The Collector receives spans on OTLP/HTTP. It writes the spans to the `debug`
output and to a file in a mounted folder. The Langfuse export comes in S2-03.

On the test host, put one reverse proxy (the front door) in front of the backend and the
Collector:

| Path | Goes to | Who calls it | Protection |
|---|---|---|---|
| `https://<host>/api/*` | Backend | GCP job | API key, IP allowlist |
| `https://<host>/otlp/*` | Collector | GCP job | OTLP token, IP allowlist |
| Private network inside the host | Collector | Backend | Not open to the internet |

The firewall opens only port 443. The front door has one certificate (S1-05).

**Acceptance criteria**
- [ ] `docker compose up` starts the Collector with a health check.
- [ ] The Collector image has the version from the fixed-versions table. It does not use `latest`.
- [ ] Spans that come in on OTLP/HTTP appear in the file output.
- [ ] On the test host, the front door is the only public entry. It accepts only port 443 and only the GCP egress IP.
- [ ] `/otlp/*` rejects a request without the correct OTLP token. The OTLP token is different from the API key.
- [ ] The GCP job reads the OTLP token from Secret Manager and sends it with `OTEL_EXPORTER_OTLP_HEADERS`.
- [ ] The Collector configuration is in the repository. It contains no secrets.
- [ ] After S2-03 works, a cleanup step deletes the file output on the test host.

**How to test**
1. Local: send test spans with `telemetrygen traces --otlp-http`. Make sure that the file output contains them.
2. Test host, from the GCP dev project: send test spans to `https://<host>/otlp/v1/traces` with the token. Make sure that the file output contains them.
3. Send spans without the token. Make sure that they are rejected.
4. Send a request from an IP that is not on the allowlist. Make sure that the connection is refused.
5. Paired with S1-06: see the test steps in S1-06.

### S1-08 — Trace check tool

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 1.10 | Backend | S1-03, S1-06 part B, S1-07, S1-12 | S1-06 + S1-07 | S |

**What:** Write the script `scripts/check_trace.py <trace_id>`. The script shows the result
for each item:

| Item | Where the script looks | "Found" means |
|---|---|---|
| Run row | Postgres table `batch_runs` | A row has this trace ID |
| GCP root span | Collector file | A `batch.run` span has this trace ID |
| Monitor span | Collector file | A `monitor.ingest` span has this trace ID |
| Parent link | Collector file | The parent of `monitor.ingest` is the job's `batch.send` span |
| Langfuse trace and score | Langfuse API | Added in S2-03 |

Run the script on the host where the stack runs. The script uses the read-only database
account from S1-12. It is a tool for developers and operators. It is not part of the
product.

**Acceptance criteria**
- [ ] The script shows "found" or "missing" for each item, with the run ID and the times.
- [ ] If an item is missing, the script stops with a non-zero exit code. CI and the drills can use this code.
- [ ] The script reads credentials from environment variables. It never shows them.
- [ ] The script only reads. It does not change the database or the files.

**How to test**
1. Paired with S1-06 and S1-07: send one example request with a known `traceparent`. Run the script with this trace ID. Make sure that the run row and the monitor span are "found".
2. On the test host, run the GCP job. Run the script with the trace ID of the run. Make sure that all four items are "found".
3. Run the script with a random trace ID. Make sure that all items are "missing" and the exit code is not zero.

### S1-09 — Security approval for the Sprint 1 data flow

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Decision | 1.5 | Security + platform | S1-01 | — | S |

**What:** Get written approval for all the data that Sprint 1 sends between the clouds.

**PII** means "personally identifiable information". PII is data that can identify a
person, for example a name, a phone number, an email address, a national ID number, a
home address or a customer account number. The [standard](llm-metrics-standard.md)
replaces phone numbers, email addresses and national ID numbers with placeholders before
the data leaves GCP. Security must tell us if other types of PII must also be replaced.
If security adds more types, the job must find them before it sends the data. Names are
difficult to find automatically.

Security must approve these items:

| Item | Issue |
|---|---|
| Redacted records leave GCP. They go to the monitor, the Claude judge (Anthropic API) and Langfuse. | S1-01, S1-04 |
| The list of PII types that the job replaces with placeholders | S1-04 |
| The retention period for stored records | S1-03 |
| An API key on the internet without a VPN, with an IP allowlist | S1-03, S1-05 |
| The certificate type (public CA or private CA) | S1-05 |
| The OTLP endpoint that GCP can reach through the front door | S1-07 |
| Real redacted data on the test host | S1-05 |
| Read access to GCP Cloud Logging for the monitor team | S1-01 |
| Database accounts, and who can read real data | S1-12 |

**Acceptance criteria**
- [ ] Each item in the table is approved in writing, or blocked with an owner and a date.
- [ ] The list of PII types is written down.
- [ ] The name of a security contact is in this issue.

**How to test**
1. Link the approval in this issue.
2. Compare the S1-01 schema with the approved fields, one field at a time.
3. Compare the S1-04 placeholder list with the approved PII types.
4. If the approval is not complete by 8 October, the job does not send records. The four judged metrics show "Unknown".

### S1-10 — Inventory of the 10 use cases and October run dates

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Discovery | 1.7 | PM + source owners | — | — | M |

**What:** Make one table with one row for each of the 10 GCP use cases. Sprints 2, 3 and 4
use this table to select the order of the use cases. The due date is Friday 9 October.

| Column | Why we need it |
|---|---|
| Use-case ID | The registry and the API use this ID |
| Owner | The person who confirms that a run is real |
| GCP job and repository | The location of the code that sends the data |
| Developer of the job | The person who adds the send step and OTel. This person can be different for each job. |
| GCP project and egress IP | The firewall allows only known IP addresses (S1-05). Each project can have a different IP. |
| October run dates | The dates when a real run can arrive. If a job does not run in October, book a controlled rerun. |
| Batch API or online calls | With the Batch API, `latency_s` is `null` |
| Approximate number of requests in each run | This number sets the sample size and the judge cost |
| Language: Thai, English or mixed | RAI must know the language that the judge examines |
| Data sensitivity | Security uses this for the approval (S1-09) |
| Owner of the task description | The person who writes the task description for the judge, with RAI |

**Acceptance criteria**
- [ ] The table has exactly 10 rows. Each row has a named owner and a named developer.
- [ ] Each use case has at least one October run date, or a booked controlled rerun.
- [ ] Each GCP project has a known egress IP for the allowlist.
- [ ] The order of the use cases for Sprints 2 to 4 is agreed.

**How to test**
1. Each owner confirms their row in the issue comments.
2. Platform adds all the egress IPs to the allowlist plan (S1-05).

**Risk:** The team examined only 6 pipelines in 4 repositories. If the table has fewer
than 10 real jobs on 9 October, change the October goal and tell the project owner.

### S1-11 — First real run end to end

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 1.6 | Backend + GCP job developer | S1-01, S1-03, S1-04, S1-05, S1-06, S1-07, S1-08, S1-12 | S1-08 (trace check tool) | S |

**What:** This is the Sprint 1 demo. One real GCP job does one real run. Show that the data
and the trace arrived. Use the S1-08 tool to show the result. Sprint 1 has no read API.
The read API for the dashboard comes in S2-08.

**Acceptance criteria**
- [ ] The source owner confirms that the run was a real published run.
- [ ] The `batch_runs` table has the run one time only.
- [ ] The job spans and the `monitor.ingest` span have the same trace ID in the Collector.
- [ ] The parent of `monitor.ingest` is the job's `batch.send` span.
- [ ] If records were sent, they contain placeholders and no raw PII.
- [ ] If security did not approve records yet, the run is in identity-only mode. The result says "records not yet approved".

**How to test**
1. Start the real run, or wait for the scheduled run.
2. Find the trace ID of the run in the job log.
3. Run `scripts/check_trace.py <trace_id>` on the test host. Make sure that all four items are "found".
4. Attach the output of the tool to this issue. Do not attach secrets or record text.

### S1-12 — Database accounts for the backend and the developers

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | New (1.11) | Platform + backend | S1-05 | S1-03, S1-08 | S |

**What:** Make database accounts on the test host. Do not use one shared administrator
account.

| Account | Type | Used by | Permissions |
|---|---|---|---|
| `monitor_app` | Bot | The backend service | Owns the monitor schema. Reads and writes the monitor tables. Runs the migrations when the backend starts, as the backend does now. |
| `monitor_readonly` | Bot | The S1-08 tool and other checks | Reads the monitor tables only |
| `dev_<name>` | Person, one for each developer | Developers | Read-only on the test host, because the test host has real redacted data. Full access only on the local stack. |
| Postgres administrator | Person | Platform only | For emergencies only. The backend and the tools do not use it. |

Rules:
- Keep the passwords as host secrets. Do not put them in the repository or in chat.
- The database port is not open to the internet. Developers connect through SSH or a bastion host.
- Remove a developer account when the person leaves the project.
- Langfuse gets its own database account in S2-03.

**Acceptance criteria**
- [ ] Each account in the table exists, with the given permissions.
- [ ] The backend uses `monitor_app` in `DATABASE_URL`. It does not use the administrator account.
- [ ] A developer can connect through SSH or the bastion host. A developer cannot connect directly from the internet.
- [ ] This issue lists the accounts and their owners. It contains no passwords.

**How to test**
1. Start the backend with `monitor_app`. Make sure that the migrations run and the API stores a run.
2. Connect as `monitor_readonly`. Make sure that `SELECT` works and `INSERT` fails.
3. Connect as a `dev_<name>` account on the test host. Make sure that `INSERT` fails.
4. Try to connect to the database port from the internet. Make sure that the connection is refused.

---

## Sprint 2 — Oct 12–16: same path for many jobs, plus evaluation and tracing

> Review status (2026-10-03): Sprint 2 review complete. S2-05 is removed. All Sprint 2
> issues are written in ASD-STE100.

**Sprint 2 prerequisites (answers from 2026-10-03; confirm after S1-05 is complete)**

| Question | Answer | Effect |
|---|---|---|
| Is the test host large enough for Langfuse? | The test server does not exist yet. Request this size. | See the server size below. |
| How do the engineers and the RAI team open the dashboard and Langfuse? | Through the IP address and a port. A DNS name comes later. | See the ports below. Use a private CA certificate that contains the IP address. When the DNS name exists, change the certificate and the Langfuse URL setting. |
| Can the test host send traffic out to the Anthropic API? | Probably yes. If not, the judge uses a local model on an on-premises server. | S2-06 must support a second judge provider. RAI must examine the local judge before use. |

Server size for the test host:

| Item | Minimum | Recommended | Reason |
|---|---|---|---|
| CPU | 6 vCPU | 8 vCPU | Langfuse alone needs at least 4 cores (Langfuse self-hosting guide). The monitor backend, two PostgreSQL databases and the Collector need more. |
| Memory | 24 GiB | 32 GiB | Langfuse alone needs at least 16 GiB. The monitor backend loads pandas, Evidently and NannyML. |
| Disk | 150 GiB SSD | 200 GiB SSD | Langfuse recommends 100 GiB for its data. The monitor database, the logs and the Docker images need more. |
| Operating system | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS | Docker Engine and Docker Compose v2 |
| AWS example | `t3.xlarge` is too small for all services | `m6i.2xlarge` or `t3.2xlarge` | — |

Ports on the test host (until a DNS name exists):

| Port | Service | Who connects | Allowlist |
|---|---|---|---|
| 443 | Front door: `/api/*` and `/otlp/*` | GCP jobs | GCP egress IPs |
| 8443 | Monitor dashboard | RAI team, engineers | Office or VPN IPs |
| 3443 | Langfuse UI | Engineers only | Office or VPN IPs of the engineers |
| None | PostgreSQL, ClickHouse, Redis, MinIO | — | Closed to the network. Developers use SSH (S1-12). |

Langfuse uses its own port because it does not work easily under a URL path.

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S2-04 GCP OTel helper | S2-03 Collector → Langfuse | The job's spans flow through the Collector into Langfuse, and the run summary lands in monitor Postgres, all with one trace ID | Local stack, then test host |
| S2-06 batch evaluator | S2-03 Collector → Langfuse | The run scores and the record scores appear on the run's trace in Langfuse | Local stack |
| S2-01 registry | S2-07 onboarding | Each real job can write only its own use case | Test host |

### S2-01 — Source registry: YAML settings and API key hashes

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.1 | Backend + platform | S1-03, S1-12 | S2-07 | M |

**What:** Make a registry of the batch use cases in two parts. This follows the YAML
registry in section 15 of the [monitoring contract](../../docs/MONITORING-CONTRACT.md).

| Part | Location | Contains | How it changes |
|---|---|---|---|
| Settings | YAML file in the repository | Use-case ID, name, owner, developer, mode (`identity_only` or `records`), sample size, task description with version and approver, run schedule, data classification, band overrides | Pull request, approved by backend. RAI also approves changes to the task description or the bands. |
| API key hashes | Database table | The SHA-256 hash of each API key, the use-case ID, and the key status | The script `scripts/batch_keys.py` |

The API key itself is kept only in the GCP Secret Manager of that project. Never put a
key or a key hash in git, chat or email.

Example entry:

```yaml
use_case_id: GCP-UC-03
name: Invoice summary
owner: billing-ai-team
developer: <job developer>
mode: identity_only
sample_size: 50
task_description:
  text: "summaries of customer invoices for the billing team"
  version: 1
  approved_by: <RAI reviewer>
schedule: "daily 02:00 UTC"
data_classification: confidential
band_overrides: {}
```

How a request is accepted:
1. The monitor finds the hash of the API key in the database.
2. The monitor finds the use case of that key in the YAML file.
3. The use case in the body must be the same as the use case of the key.

**Key rotation:** The monitor accepts two active keys for one use case. Make the new key,
put it in Secret Manager, wait for one successful run, then remove the old key.

**OTLP token:** All GCP jobs use one OTLP token (S1-07). The Collector cannot connect a
token to a use case. Spans are not used for grades, so this risk is low.

**Acceptance criteria**
- [ ] The monitor reads the YAML file when it starts. If the file has an error, the monitor does not start and shows the error.
- [ ] A key for use case A with a body for use case B: `403`.
- [ ] A correct key for a use case that is not in the YAML file: `403`.
- [ ] A removed key: `401`.
- [ ] During rotation, both keys work. After the old key is removed, only the new key works.
- [ ] Key rotation does not change or remove stored runs.
- [ ] `scripts/batch_keys.py` can make, list and remove keys. It shows a new key one time only and never writes the key to a log.
- [ ] Platform puts each new key directly into GCP Secret Manager.

**How to test**
1. Unit and integration: `pytest` for each acceptance criterion.
2. Load a YAML file with an error. Make sure that the monitor does not start.
3. Paired with S2-07: each onboarded job sends with its own key and the request is accepted. Change the key of one job to the key of another use case. Make sure that the request is rejected.

### S2-02 — Langfuse SDK v4 in the backend, and package approval

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Decision + Feature | Deadline Mon Oct 12 | Backend + project owner | S1-06 | S2-06 | M |

**Decision (2026-10-03):** Use the Langfuse Python SDK v4 (`langfuse` 4.x) in the backend.
The backend uses it for these items:
- The `monitor.evaluate` span. This span can contain the redacted record text that the API accepted.
- The scores, with `create_score`.

The GCP jobs do not use the Langfuse SDK. They use the OTel SDK and send their spans to the
Collector (S1-06, S1-07). Thus the Langfuse keys stay in AWS.

**Facts that affect this issue**

| Fact | Effect |
|---|---|
| SDK v4 does not have the v2 functions `trace()` and `score()`. The chatbot store (`backend/app/adapters/llm_eval/stores.py`) uses these functions. | The class `LangfuseCloudStore` is prototype-only code. Remove it in the same pull request, and make the chatbot use only its local store. Do not change it to v4. |
| SDK v4 needs `opentelemetry-api`, `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`, version 1.45 or later. | S1-06 part B must use the same OTel versions. |
| Langfuse released three major SDK versions in three years. v2 is deprecated. | Pin `langfuse>=4.16,<5`. Read the release notes before an upgrade. |

**Acceptance criteria**
- [ ] The spec lists each new or changed package with a version range: `langfuse>=4.16,<5`, the OTel packages, and the OTel instrumentation packages.
- [ ] The self-hosted Langfuse server has a fixed version that supports SDK v4 (S2-03).
- [ ] In one backend process, the SDK v4 and the FastAPI OTel instrumentation put `monitor.ingest` and `monitor.evaluate` in the same trace as the GCP spans.
- [ ] `LangfuseCloudStore` is removed in the same pull request. `judge.py` and `live_http.py` use only the local store for the chatbot. No call to the v2 functions `trace()` or `score()` remains.

**How to test**
1. Compare `backend/requirements.txt` with the approved list.
2. Run the full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. In the local stack, send one run with a known `traceparent`. Make sure that Langfuse shows the GCP spans, `monitor.ingest`, `monitor.evaluate` and the scores in one trace.

### S2-03 — Collector exports to self-hosted Langfuse

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 2.4 | Platform | S1-07, S1-12, Sprint 2 prerequisites | S2-04, S2-06 | L |

**What:** Add self-hosted Langfuse to Docker Compose: Langfuse web, Langfuse worker,
PostgreSQL, ClickHouse, Redis and S3 storage (MinIO). Use the versions in the
fixed-versions table. Add an `otlphttp` exporter to the Collector. This exporter sends the
GCP spans to the Langfuse OTLP endpoint (`/api/public/otel`) with the Langfuse project keys.

**Prerequisites (answer after S1-05 is complete)**

| Question | Owner |
|---|---|
| Is the test host large enough for Langfuse (CPU, memory, disk)? Examine the Langfuse self-hosting requirements. | Platform |
| How do the engineers open the Langfuse UI? The front door allows only the GCP IP now. Options: add the office or VPN IP, or use an SSH tunnel. | Network team |

**Rules**
- Langfuse uses its own PostgreSQL container and account. It does not share the monitor database (S1-12).
- Turn off public sign-up in Langfuse. Make one account for each engineer. Langfuse is for engineers. The RAI team uses the dashboard.
- The Collector exporter sends the header `x-langfuse-ingestion-version: 4`. Without this header, new data can appear in Langfuse up to 10 minutes late.
- Set the retention period in Langfuse from S1-09.
- Keep the Langfuse keys as host secrets. Do not put them in files in git.
- When this issue works, delete the Sprint 1 file output on the test host (S1-07).

**Change to S1-08:** The trace check tool reads Langfuse through the Observations API v2.
Most other Langfuse read APIs can be up to 10 minutes behind, so the tool would show
"missing" for a correct trace.

**Acceptance criteria**
- [ ] `docker compose up` starts all Langfuse containers with the fixed versions and health checks.
- [ ] Langfuse data stays after `docker compose restart`.
- [ ] Spans that the Collector receives appear as traces in Langfuse within one minute.
- [ ] Public sign-up is off. A person without an account cannot open a project.
- [ ] No Langfuse key is in the repository.
- [ ] `scripts/check_trace.py` shows the Langfuse trace and its scores through the Observations API v2.

**How to test**
1. Send test spans with `telemetrygen`. Make sure that they appear in Langfuse within one minute.
2. Run `docker compose restart`. Make sure that the same trace is still in Langfuse.
3. Open the Langfuse sign-up page without an account. Make sure that sign-up is refused.
4. Paired with S2-04 and S2-06: see the test steps in those issues.

### S2-04 — OTel helper file for the GCP jobs

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.7 | GCP job developer; backend reviews | S1-06 | S2-03 | M |

**What:** Move the OTel code from S1-06 part A into one reusable Python file,
`otel_helper.py`. Add the token data and the attribute allowlist. Use the file in the first
job. The other jobs get the file in S2-07, S3-01 and S4-03. Each job repository copies the
file, because we have no package registry.

| Function | Detail |
|---|---|
| Run trace | The root span `batch.run` and the step spans, as in S1-06 |
| Token totals, Batch API jobs | Attributes on the `batch.harvest` span: model, input tokens, output tokens |
| Token data, online jobs | One span for each sampled request only, with model, tokens and the real call time. The totals go on `batch.run`. Select the sample before the calls start, so the same requests get spans and become records. |
| Attribute names | The OTel GenAI names: `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| Attribute allowlist | Only the allowed keys go into a span. The helper drops other keys and logs only the key name. GCP spans contain no text. |
| Export | OTLP/HTTP to the front door (`/otlp/*`) with the OTLP token. If the export fails, the job continues. |

**Acceptance criteria**
- [ ] One trace for each run, with the step spans from S1-06.
- [ ] Batch API jobs: the token totals are on `batch.harvest`.
- [ ] Online jobs: spans exist only for the sampled requests; the totals are on `batch.run`.
- [ ] An attribute that is not on the allowlist (for example `prompt`) is dropped. The log shows only its key name.
- [ ] No span attribute contains record text.
- [ ] If the Collector is not available, the job ends normally and writes a log entry.
- [ ] The first job uses the file. The file has a version number at the top.

**How to test**
1. Unit (GCP repository): use an in-memory span exporter. Make sure that the span names, the parent links and the GenAI attributes are correct. Make sure that a forbidden attribute is dropped. Stop the exporter and make sure that the job ends normally.
2. Paired with S2-03, local: run the first job with a recorded Gemini response. Send the spans to the local Collector and the run summary to the local backend.
3. Paired with S2-03, test host: run the first job in the GCP dev project.
4. For tests 2 and 3: run `scripts/check_trace.py`. Make sure that Langfuse shows the GCP spans with the token attributes in the same trace as `monitor.ingest`.

### S2-05 — Removed

The chatbot store is prototype-only code. S2-02 removes the Langfuse v2 part of it. We do not
change it to SDK v4.

### S2-06 — Batch evaluator with the five LLM metrics

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.3 | Backend + RAI | S2-01, S2-02, S2-03, task description (Wed 14 October) | S2-03 | L |

**What:** Grade each stored run with the LLM lane of the prototype. Map the records to the
v1.1 `Trace` shape. Use the Claude judge and the aggregation in
`backend/app/adapters/llm_eval/live_http.py`. Grade with `backend/app/engines/health.py`.
The five metrics, the bands and the grading rules do not change.

Three changes from the [standard](llm-metrics-standard.md):
1. The judge prompt uses the task description of the use case from the YAML registry (S2-01).
2. A placeholder (`[PHONE]`, `[EMAIL]`, `[NATIONAL_ID]`) in the answer counts as PII exposure.
3. The judge examines all the records of the run, up to the sample size in the registry.

**When the evaluation runs**

The background worker that has the lease (`backend/app/live_poller.py`) finds the stored
runs that have no evaluation and evaluates them. The `POST /api/batch/runs` request does
not wait for the judge. It returns immediately.

**Where the results go**

| Result | Our database | Langfuse |
|---|---|---|
| The five run metrics and the grade | Table `batch_evaluations` | Scores on the trace of the run |
| The four judge results of each record | Table `batch_record_judgments` | Scores on the observation of that record |
| The redacted text of each judged record | Already in the stored run (S1-03) | Input and output of the record observation, under `monitor.evaluate` |

- The stored run never changes. The evaluation is a separate row.
- If the task description changes, add a new evaluation row with the new version. Keep the old row.
- The dashboard and the grade use our database. Langfuse is for engineers.

**Langfuse (SDK v4, S2-02)**

```
Trace of the run (same trace ID as the GCP spans)
  Scores: the five run metrics
  └─ monitor.evaluate
      ├─ record <record_id>   Scores: groundedness, relevance, hallucination, pii
      └─ … one observation for each judged record
```

- Use a stable `score_id`: from the run ID and the metric name for a run score, and from the run ID, the record ID and the metric name for a record score. If a score is sent again, Langfuse does not make a duplicate.
- If a write to Langfuse fails, record it and try again in the next worker cycle. A Langfuse failure does not change the grade.

**Judge provider**

| Provider | When | Rule |
|---|---|---|
| Claude, `claude-haiku-4-5` (now) | The test host can reach the Anthropic API | `ANTHROPIC_API_KEY` is a host secret |
| Local model on the on-premises server | The test host cannot reach the Anthropic API | RAI compares its scores with the Claude scores on a sample before use. Thai text needs special care. |

Each score records the judge identity. The offline heuristic judge is never used in
strict live mode.

**When a metric is "Unknown"**

| Condition | Reason |
|---|---|
| Identity-only run (`records: []`) | `records_not_approved` |
| Fewer than 8 records | `insufficient_sample` |
| The judge fails 3 times. After each failure, the worker tries again in the next cycle. | `judge_failed` |
| No task description is approved | `task_description_missing` |
| All `latency_s` values are `null` | `latency_not_reported` (only `p95_latency_s`; excluded from the rollup) |

An "Unknown" is never shown as Green. An evaluation problem is never shown as a delivery
problem, and a delivery problem is never shown as an evaluation problem.

**Acceptance criteria**
- [ ] The five metrics, the bands and the grading are the same as in the chatbot lane.
- [ ] The worker evaluates each new run one time. The `POST` request does not wait for it.
- [ ] `batch_evaluations` stores the metrics with the task description version, the judge identity, the sample size and the run ID.
- [ ] `batch_record_judgments` stores the four results of each judged record.
- [ ] Each condition in the "Unknown" table gives "Unknown" with its reason.
- [ ] If the judge fails, the worker tries again in the next cycles, up to 3 times. A later success gives normal scores.
- [ ] Langfuse shows the run scores on the trace and the record scores on each record observation.
- [ ] A score that is sent two times makes one score in Langfuse.
- [ ] If Langfuse is not available, the grade is stored, and the score write is tried again later.
- [ ] The chatbot (`AICT-L02`) tests pass.

**How to test**
1. Unit: use a fake judge. Make sure that each "Unknown" condition gives its reason. Make sure that the band limits are correct, for example a hallucination rate of exactly 0.02 is Red. Make sure that a placeholder counts as PII only in `answer`.
2. Unit: use a fake Langfuse client. Make sure that the `score_id` values are stable, and that a failed write is tried again.
3. Unit: make the fake judge fail two times and then succeed. Make sure that the run gets normal scores. Make it fail three times, and make sure that the metrics are "Unknown" with `judge_failed`.
4. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
5. Paired with S2-03: store one run in the local stack and let the worker evaluate it. Run `scripts/check_trace.py`. Make sure that `monitor.evaluate`, the run scores and the record scores are "found" on the same trace.

**Risk:** The task description is due Wednesday 14 October. Then only two days remain in
Sprint 2 for the first graded run.

### S2-07 — Onboard 4 use cases

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.2 | Job developers + backend + platform | S1-10, S2-01, S2-04 | S2-01, S1-08 | L |

**What:** Add the send step (S1-04) and the OTel helper file (S2-04) to 4 different jobs.
Include one job with a different output shape. Use the order and the developers in the
S1-10 table.

For each job, do these steps:
1. Add the use case to the YAML registry (S2-01) in a pull request. Set `mode: identity_only`.
2. Platform makes the API key with `scripts/batch_keys.py` and puts it into the GCP Secret Manager of that project.
3. Platform adds the egress IP of the GCP project to the allowlist.
4. The job developer maps the job to the record fields of the [standard](llm-metrics-standard.md), as in S1-01.
5. The job developer adds the send step and the helper file. The job uses the shared OTLP token. It needs no Langfuse key.
6. Run the job. If the job does not run between 12 and 16 October, use a controlled rerun.
7. After S1-09 approves the records, change `mode` to `records` and set `SEND_RECORDS` to on.

**Acceptance criteria**
- [ ] 4 real runs arrive. The owner of each use case confirms that the run is real.
- [ ] Each use case has its own API key and one trace for each run.
- [ ] Each use case has an approved task description and its five metrics graded, or "Unknown" with a reason.
- [ ] Test files or configuration entries do not count as a live use case.

**How to test**
1. For each job: run `scripts/check_trace.py <trace_id>`. Make sure that all the items are "found".
2. For each job: examine one stored run. Make sure that the records agree with the schema and contain placeholders, not raw PII.
3. Record the 4 trace IDs and their five metric values in this issue.

### S2-08 — Dashboard shows the GCP use cases with the current UI

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 2.5 | Backend | S2-01, S2-06 | S2-07 | M |

**Decision (2026-10-03):** The dashboard shows only the GCP batch use cases. The UI does not
change. The dashboard shows no record text.

**What:** The frontend reads only two endpoints: `GET /api/live/portfolio` and
`GET /api/live/use-case/{id}`. It does not contain fixed use-case IDs. Thus the backend
returns the GCP use cases through these two endpoints, in the same shape that the LLM lane
of the chatbot uses now. The frontend code does not change.

| UI field | Source for a GCP use case |
|---|---|
| Name and owner | YAML registry (S2-01) |
| Five LLM signals, lanes and grade | `batch_evaluations` (S2-06) |
| Freshness | `completed_at` of the latest run |
| `judge` | The judge identity |
| `judge_sample` | Always empty. No record text goes to the browser. |
| Errors and "Unknown" reasons | The reasons from S2-06 |

- On the test host and on AWS, the three prototype use cases are not configured. `LIVE_CHURN_URL`, `LIVE_CHATBOT_URL` and `LIVE_NBA_URL` are not set. Thus they do not appear on the dashboard.
- The dashboard is for the RAI team. It has no Langfuse link, because Langfuse is for engineers. The API returns `trace_id`, so an engineer can find the trace in Langfuse.
- The dashboard uses port 8443 (Sprint 2 prerequisites).

**Acceptance criteria**
- [ ] On the test host, the portfolio shows only the GCP use cases.
- [ ] Each use case shows the latest run, the freshness, the five signals, the grade and the "Unknown" reasons in the current cards.
- [ ] No API response for a GCP use case contains question, answer or source text.
- [ ] The frontend files do not change (`artifacts/control-tower/src`).
- [ ] The API response contains `trace_id`.
- [ ] `pnpm run typecheck`, `pnpm run build:live` and `pnpm run check:strict-live` pass.

**How to test**
1. API tests for each state: scored, each "Unknown" reason, stale, identity-only.
2. Search all API responses for the text in the S1-01 examples. Make sure that the text is not found.
3. Run the pnpm checks. `build:live` and `check:strict-live` run in CI on Linux.
4. Paired with S2-07: open the dashboard on port 8443. Make sure that the onboarded use cases show the correct freshness and grades.

### S2-09 — One run as a single trace, GCP job to score

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | Sprint 2 exit | Backend + platform | S2-03, S2-04, S2-06, S2-08 | S1-08 | S |

**What:** This is the Sprint 2 demo. Show one real run as one trace in Langfuse, from the
GCP job to the scores. Show the same run with its grade on the dashboard.

**Acceptance criteria**
- [ ] Langfuse shows one trace with the GCP spans, `monitor.ingest`, `monitor.evaluate`, the run scores and the record scores.
- [ ] The dashboard shows the same run with its grade. An engineer finds its trace in Langfuse with the `trace_id` from the API.
- [ ] If the run is in identity-only mode, the demo shows the trace and the "Unknown" reason `records_not_approved`, without scores. The result says "records not yet approved".
- [ ] If the task description is not approved, the judged metrics show "Unknown" with the reason `task_description_missing`. The result records this.

**How to test**
1. Run `scripts/check_trace.py <trace_id>`. The tool reads Langfuse through the Observations API v2. Make sure that all the items are "found".
2. Attach the output of the tool and a screenshot of the dashboard row. Do not attach record text or secrets.

---

## Sprint 3 — Oct 19–23: scale to 8 and harden

> Review status (2026-10-04): Sprint 3 review complete. All Sprint 3 issues are written in
> ASD-STE100.

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S3-03 Collector hardening | S3-04 drills | Spans survive a Langfuse outage and arrive after recovery, once | Local stack |
| S3-03 Collector hardening | S3-05 leak scan | Forbidden attributes are removed before storage | Local stack, test host |
| S3-02 missed-run alert | S3-04 drills | A run that never arrives raises a delivery alert, not a quality alert | Local stack |

### S3-01 — Onboard 8 use cases, including split submit and harvest

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 3.1 | Job developers + backend + platform | S2-04, S2-07 | S1-08 | L |

**What:** Onboard 4 more use cases, to a total of 8. Use the seven steps in S2-07 for each
job. Include the difficult jobs from the S1-10 table.

**Jobs with separate submit and harvest.** In some jobs, one run of the code submits the
Gemini batch job, and a later run of the code harvests the results. To make one trace for
the two runs:
1. Add a function to the helper file (S2-04) that continues a trace from a stored `traceparent`. Increase the version number of the file.
2. The submit run stores its `traceparent` in the same location as the Gemini batch job ID.
3. The harvest run reads the `traceparent` and continues the same trace.

**Partial publication.** If only part of the results are published, the job sends
`status: partial` with the counts. The job does not send `completed` before all the results
are published.

**Acceptance criteria**
- [ ] 8 real runs in total. The owner of each use case confirms that the run is real.
- [ ] A job that only submitted sends nothing.
- [ ] For a job with separate submit and harvest, Langfuse shows the submit spans and the harvest spans under the same root span.
- [ ] A partial publication arrives with `status: partial`.
- [ ] Each use case has an approved task description and its five metrics graded, or "Unknown" with a reason.

**How to test**
1. For each new job: run `scripts/check_trace.py <trace_id>`. Make sure that all the items are "found". Record the trace IDs in this issue.
2. For a job with separate submit and harvest: run the submit, then the harvest. Make sure that one trace contains both.
3. Unit (GCP repository): store a `traceparent`, continue the trace in a new process, and make sure that the trace ID is the same.

### S3-02 — Delivery lane: missed-run and failed-job alerts

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | 3.2 | Backend | S2-01, S1-03 | S3-04 | M |

**What:** Add a "delivery" lane for each GCP use case. Use the existing alert code: the
transition engine (`backend/app/engines/alerts.py`), the table `live_alerts`, the webhook
(`backend/app/alert_delivery.py`) and the endpoint `/api/live/alerts`. The current UI
already shows alerts, so the UI does not change.

| Delivery health | Condition | Reason |
|---|---|---|
| Green | The last run arrived on time | — |
| Amber | The last run has `status: partial` | `partial_publication` |
| Red | No run arrived before the end of the grace period | `run_missing` |
| Red | The last run has `status: failed` | `job_failed` |
| Unknown | No run has arrived yet, or the use case has no schedule | `no_run_yet` or `no_schedule` |

The existing engine opens an alert on Red and on Green to Amber, resolves it on Green, and
keeps one open alert only. Unknown never opens an alert. The delivery lane is **not** part
of the overall quality grade, so a missed run never changes the quality grade.

**Steps**
1. Add the schedule to each use case in the YAML registry (S2-01): `schedule.expected_every` (for example `24h`) and `schedule.grace` (for example `2h`). Use an interval, not a cron expression, so that no new package is necessary. For a monthly job, use `31d`.
2. Write the pure function `delivery_health(last_run, every, grace, now)` in the new file `backend/app/engines/delivery.py`. It returns the health and the reason. It does no I/O. The caller gives the time `now`.
3. Add `evaluate_delivery(uc, now)` to `backend/app/alerting.py`. It reads the latest run from `batch_runs`, calls `delivery_health`, and calls the existing `transitions()` with the key `"delivery"` only.
4. In `backend/app/live_poller.py`, call `evaluate_delivery` for each GCP use case in each cycle, inside the lease. The existing `alert_delivery.deliver_pending()` sends the webhook.

| File | Change |
|---|---|
| YAML registry | Add `schedule.expected_every` and `schedule.grace` |
| `backend/app/engines/delivery.py` | New pure function |
| `backend/app/alerting.py` | New function `evaluate_delivery` |
| `backend/app/live_poller.py` | Call `evaluate_delivery` in each cycle |
| Frontend | No change |

**Acceptance criteria**
- [ ] Each condition in the table gives the correct health and reason.
- [ ] A missing run opens one alert only, also after many cycles.
- [ ] A new run that arrives on time resolves the alert.
- [ ] The overall quality grade does not change because of the delivery lane.
- [ ] The webhook receives the open and the resolve messages.
- [ ] The current UI shows the delivery alert. If it does not show the lane name "delivery", map the alert to a name that the UI shows.
- [ ] No new package and no new table.

**How to test**
1. Unit tests for `delivery_health` with a fixed clock (every 24h, grace 2h):

   | Test | Expected result |
   |---|---|
   | No run yet | Unknown, `no_run_yet` |
   | Last run 20 hours ago | Green |
   | Last run 25 hours ago (inside the grace period) | Green |
   | Last run 27 hours ago (after the grace period) | Red, `run_missing` |
   | Last run has `status: failed` | Red, `job_failed` |
   | Last run has `status: partial` | Amber, `partial_publication` |

2. Integration test with SQLite, a fixed clock and a fake webhook: store a run, move the clock 27 hours, run one cycle, and make sure that one alert opens. Run another cycle, and make sure that no second alert opens. Store a new run, run a cycle, and make sure that the alert resolves and the quality grade did not change.
3. Paired with S3-04: on the test host, stop the send step of one job. After the grace period, make sure that the alert shows in the UI and in the webhook. Start the send step again, and make sure that the alert resolves.

### S3-03 — Collector hardening: attribute filter, memory limit, disk queue

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 3.4 | Platform | S1-07, S2-03 | S3-04, S3-05 | M |

**What:** Make the Collector safe and reliable before AWS. S1-07 already added the token,
HTTPS through the front door and the IP allowlist. This issue does not repeat them.

| Addition | Why |
|---|---|
| Attribute filter in the Collector | The helper file removes attributes in the GCP job (S2-04). The Collector filter is a second protection, for example for a job that uses an old helper file. Use the same allowlist. |
| Memory limit | A large burst of spans cannot stop the Collector |
| Disk queue for the Langfuse exporter | If Langfuse is down, or the Collector restarts, the spans wait on disk and are not lost |

The API keeps the API key in October. We do not change to a Google identity token, unless
security requires it in S1-09.

**Acceptance criteria**
- [ ] A span with an attribute that is not on the allowlist arrives in Langfuse without that attribute.
- [ ] A burst of spans above the memory limit does not stop the Collector. The Collector refuses the extra spans, and the senders try again.
- [ ] Spans that arrive while Langfuse is down are in Langfuse after recovery, one time only.
- [ ] Spans in the disk queue stay after a Collector restart.

**How to test**
1. Send a span with a forbidden attribute (for example `prompt`). Make sure that Langfuse does not show it.
2. Send a large burst with `telemetrygen`. Make sure that the Collector continues to run.
3. Stop Langfuse. Send spans. Restart the Collector. Start Langfuse. Make sure that all the spans arrive one time.

### S3-04 — Failure and recovery drills

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 3.3 | Backend + platform | S2-06, S3-02, S3-03 | S1-08 | M |

**What:** Stop each part of the system on purpose. Make sure that no data is lost and
nothing is duplicated. Do the drills on the test host.

| Drill | Expected result |
|---|---|
| The monitor is down while a job sends | The job tries again and logs each failure. After recovery, the run is stored one time. |
| The Collector is down | The run summary is still stored. The spans arrive later from the disk queue (S3-03). |
| Langfuse is down | The spans wait in the Collector. The backend tries the scores again. After recovery, each score is in Langfuse one time. |
| The judge is down (Anthropic or the local model) | The worker tries again in the next cycles, up to 3 times (S2-06). If the judge comes back, the run gets normal scores. If not, the metrics are "Unknown" with `judge_failed`. |
| The monitor restarts during an ingest | No half-written run. The job sends again, and the run is stored one time. |
| A job does not send | The delivery alert opens (S3-02). It resolves when the next run arrives. |
| The monitor database restarts | No stored run is lost |

**Acceptance criteria**
- [ ] Each drill in the table has a result: pass, fail or not done, with the date.
- [ ] Each failed drill has an issue for the fix, with an owner.

**How to test**
1. Do each drill. After each drill, run `scripts/check_trace.py` for the affected trace IDs.
2. Record the results in this issue.

### S3-05 — Security and retention review with leak scan

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 3.4 | Security + platform + source owners | S3-01, S3-03 | S3-03 | M |

**What:** A script searches the stored data for items that must not be there. Security also
examines the access.

| Location | Allowed | Not allowed |
|---|---|---|
| `batch_runs` and `batch_record_judgments` | Redacted text with placeholders | Raw phone numbers, emails, national IDs |
| GCP spans in Langfuse | Names, times, counts, IDs | Any text |
| `monitor.evaluate` in Langfuse | Redacted record text | Raw PII |
| Dashboard and API responses | Metrics and reasons | Any record text |
| Logs | IDs and errors | Keys, tokens, record text |

Security also examines these items:
- The database accounts (S1-12).
- The Langfuse accounts. They are for engineers only.
- One key rotation (S2-01).
- A request without a key or a token is refused, on the API and on the Collector.
- The retention periods in the monitor database and in Langfuse (S1-09).

**Acceptance criteria**
- [ ] The leak scan finds nothing in the "Not allowed" column.
- [ ] Each access item in the list passes.
- [ ] Each exception is written down, with an owner and a date.

**How to test**
1. Run the leak scan script on a sample of each location. The script searches for phone numbers, email addresses, national ID numbers, token formats and record text in the wrong locations.
2. Send a request without a key to the API, and spans without a token to the Collector. Make sure that both are refused.

### S3-06 — Kubernetes deployment files: Langfuse Helm chart and our manifests

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Infrastructure | 3.5 | Platform | S3-03 | S4-01 | L |

**What:** Prepare the files that install the stack on the AWS Kubernetes cluster in
Sprint 4. Use the versions in the fixed-versions table.

**Decisions (2026-10-04)**

| Part | Plan A (selected) | Plan B (fallback) |
|---|---|---|
| PostgreSQL 17 (monitor and Langfuse) | Amazon RDS for PostgreSQL 17 | Container in the cluster, with our backups |
| S3 storage for Langfuse | Amazon S3 | MinIO container in the cluster |
| Langfuse, ClickHouse, Redis | Official Langfuse Helm chart | Official Langfuse Helm chart |
| Monitor backend, Collector, front door | Our own manifests | Our own manifests |

Request RDS and S3 from the AWS team at the start of Sprint 3. If the request is not
approved by **Wednesday 21 October**, use plan B. Write the deployment files so that a
values file selects plan A or plan B.

**Acceptance criteria**
- [ ] The RDS and S3 request is sent at the start of Sprint 3. The answer, or plan B, is recorded by 21 October.
- [ ] The Langfuse Helm chart uses version 2.1.3 and the Langfuse image tag 4.50.0.
- [ ] Our manifests for the monitor backend, the Collector and the front door pass validation (`kubeconform`, or `kubectl apply --dry-run=server`).
- [ ] Secrets come from the Kubernetes secret store. No secret is in the files.
- [ ] Each service has health checks, resource limits and a rollback step.
- [ ] Backup, restore and rollback steps are written. For plan A, they use the RDS backups.

**How to test**
1. Validate all the files.
2. If a disposable local cluster (for example kind) is available, install the stack in it with plan B. Send one example run and spans. Run `scripts/check_trace.py`, and make sure that all the items are "found". If no cluster is available, record that this test was not done.

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
- [ ] Every use case has an approved task description and follows the [standard](llm-metrics-standard.md).
- [ ] No test data or configuration-only entries counted.

**How to test**
1. Covered by the S4-04 checklist.

### S4-04 — 10-row evidence checklist

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Verification | 4.4 | Backend + frontend + RAI | S4-03 | S1-08 | M |

**What:** One table with a row per use case: run ID, completion time, freshness, records
judged, the five metric values (or Unknown with reason), overall grade, task description
version, trace ID, and the result of `scripts/check_trace.py`.

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

### S4-07 — Remove the prototype-only code

| Type | Plan task | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|---|
| Feature | New | Backend | S4-06 | Full test suite | M |

**What:** Remove the code of the three prototype use cases that the GCP path does not use.
Follow the rule for prototype code at the start of this file. Do this after the release
sign-off (S4-06), so that the AWS release does not change at the last moment.

**Acceptance criteria**
- [ ] A list of the removed files and a list of the kept shared files are in the pull request.
- [ ] Each removed item has no use in the GCP path. A repository search shows this.
- [ ] The tests of the shared code use GCP-style data, not prototype data.
- [ ] Packages that only the removed code used are removed from `backend/requirements.txt`.
- [ ] `CLAUDE.md`, `README.md` and the contract documents describe the GCP use cases.

**How to test**
1. Run the full backend suite and the pnpm checks.
2. On the test host, send one GCP run. Run `scripts/check_trace.py`. Make sure that all the items are "found".
