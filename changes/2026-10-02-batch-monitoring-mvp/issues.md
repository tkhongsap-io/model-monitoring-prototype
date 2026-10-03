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
| S2-02 | Langfuse SDK v4 in the backend, and package approval | Decision + Feature | Backend + project owner | S2-05, S2-06 |
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
| Google service-account ID token (OIDC): the job gets a Google-signed token; the monitor checks the signature and the service-account email | No | Medium; needs the `google-auth` package (plan entry) | Upgrade candidate in Sprint 3 (S3-03) |
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
- [ ] The Collector image has a fixed version. It does not use `latest`.
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

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S2-04 GCP OTel helper | S2-03 Collector → Langfuse | The job's spans flow through the Collector into Langfuse, and the run summary lands in monitor Postgres, all with one trace ID | Local stack, then test host |
| S2-05 monitor off SDK v2 | S2-03 Collector → Langfuse | Judge spans arrive through the Collector and the score is attached to the same trace | Local stack |
| S2-06 batch evaluator | S2-05 | The evaluation score appears on the run's trace in Langfuse | Local stack |
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
| Decision + Feature | Deadline Mon Oct 12 | Backend + project owner | S1-06 | S2-05, S2-06 | M |

**Decision (2026-10-03):** Use the Langfuse Python SDK v4 (`langfuse` 4.x) in the backend.
The backend uses it for these items:
- The `monitor.evaluate` span. This span can contain the redacted record text that the API accepted.
- The scores, with `create_score`.

The GCP jobs do not use the Langfuse SDK. They use the OTel SDK and send their spans to the
Collector (S1-06, S1-07). Thus the Langfuse keys stay in AWS.

**Facts that affect this issue**

| Fact | Effect |
|---|---|
| SDK v4 does not have the v2 functions `trace()` and `score()`. The chatbot store (`backend/app/adapters/llm_eval/stores.py`) uses these functions. | When the version changes to v4, the chatbot store stops sending to Langfuse. The code catches the error, so the chatbot continues to work, but its Langfuse traces stop. S2-05 must change the chatbot store in the same pull request. |
| SDK v4 needs `opentelemetry-api`, `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`, version 1.45 or later. | S1-06 part B must use the same OTel versions. |
| Langfuse released three major SDK versions in three years. v2 is deprecated. | Pin `langfuse>=4.16,<5`. Read the release notes before an upgrade. |

**Acceptance criteria**
- [ ] The spec lists each new or changed package with a version range: `langfuse>=4.16,<5`, the OTel packages, and the OTel instrumentation packages.
- [ ] The self-hosted Langfuse server has a fixed version that supports SDK v4 (S2-03).
- [ ] In one backend process, the SDK v4 and the FastAPI OTel instrumentation put `monitor.ingest` and `monitor.evaluate` in the same trace as the GCP spans.
- [ ] The version change and the S2-05 chatbot change are in the same pull request.

**How to test**
1. Compare `backend/requirements.txt` with the approved list.
2. Run the full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. In the local stack, send one run with a known `traceparent`. Make sure that Langfuse shows the GCP spans, `monitor.ingest`, `monitor.evaluate` and the scores in one trace.

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

**What:** Add the run summary step (sampling and placeholder redaction) and the OTel helper to
4 different jobs, including one with a different output shape. Map each job to the
[standard](llm-metrics-standard.md) record fields, as in S1-01.

**Acceptance criteria**
- [ ] 4 real runs received, each confirmed by its owner.
- [ ] Each use case has an RAI-approved task description and its five metrics graded, or Unknown with a reason.
- [ ] Each has its own token and one trace per run.
- [ ] Test files or configuration entries do not count.

**How to test**
1. For each job: run on its schedule or in the dev project, then `scripts/check_trace.py <trace_id>` shows all hops.
2. Check one stored run per job: records validate, and a spot check finds placeholders instead of raw PII.
3. Record the 4 trace IDs and their five metric values in this issue.

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
- [ ] 8 real runs confirmed by owners, each with an approved task description and its five metrics graded or Unknown with a reason.
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
