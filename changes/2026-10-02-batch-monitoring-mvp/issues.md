# Batch Monitoring MVP — GitHub Issues by Sprint

| | |
|---|---|
| **Date** | 2026-10-05 |
| **Status** | Reviewed sprint by sprint on 2026-10-03 and 2026-10-04. Revised on 2026-10-05: SSO login, the judge through the company LiteLLM proxy, and the test host in GCP. Posted to GitHub as issues #3 to #38. |
| **Language** | ASD-STE100 (Simplified Technical English), about 80% strict |
| **Related** | [Plan](plan.md) · [One-page summary and flows](summary.md) · [LLM metrics and data standard](llm-metrics-standard.md) |

You can copy each issue into GitHub. Each feature issue names the issue that it is
**tested with**. A sender is proven by the receiver that sees its data arrive. A receiver
is proven by a real sender. One shared tool, the trace check tool (S1-07), follows one
trace ID through all the locations. Thus each paired test ends with the same question:
did the data of this run arrive in the monitor database and in Langfuse with the same
trace ID?

## Changes on 2026-10-05

| Change | Decision | Issues |
|---|---|---|
| LLM judge | The judge is a local model through the company LiteLLM proxy. Claude and the Anthropic API are not used. There is no second provider. The backend calls the proxy with `httpx`, which it already uses. The `anthropic` package is removed. | New: S1-12, S2-09, S2-10. Changed: S1-08, S1-09, Sprint 2 prerequisites, S2-05, S2-07, S3-04, S3-05, S4-01, S4-03, S4-04, S4-05 |
| SSO login | Staff log in with Google Workspace SSO. OAuth2 Proxy protects the dashboard. Langfuse uses its own SSO, with no password login. Later, the company changes to Microsoft Entra ID. This change is a change of settings only. | New: S3-07. Changed: S1-06, Sprint 2 prerequisites, S2-03, S3-04, S3-05, S3-06, S4-01, S4-05 |
| Front door path | On port 443, the front door sends only `/api/batch/runs` and `/api/health` to the backend, not all of `/api/*`. Thus nobody can read the dashboard API around the SSO. | S1-06 |
| Test host in GCP | The test host for Sprints 1 to 3 is one Compute Engine VM in GCP, with the same Docker Compose stack. The GCP jobs reach it on a private VPC path. The VM has no public IP. The API key stays, so the test uses the same method as production. The Sprint 3 Kubernetes test stays on the test AWS cluster, and production stays on AWS. | Changed: S1-02, S1-04, S1-06, S1-08, S1-09, S1-11, S1-12, Sprint 2 prerequisites, S2-03, S2-06, S3-05, S3-06, S3-07, S4-01, S4-02 |

**Review focus.** These five failure modes are the most likely to cause problems. Each one
has a test in the issue that owns it.

| Failure mode | Expected behavior | Test in |
|---|---|---|
| A person reads the dashboard data through port 443 and avoids the SSO | Port 443 gives `404` for `/api/live/*` | S1-06, S3-07 |
| The proxy owner changes the model behind the LiteLLM alias without notice | Each score records the model name that the proxy returns. S4-04 compares it with the model that RAI accepted. | S2-09, S2-10, S4-04 |
| The local model returns text that is not valid JSON, or values outside 0 to 1 | The answer is a judge failure. No score is stored. The heuristic judge is never used in strict live mode. | S2-09 |
| The LiteLLM proxy refuses calls (`429`) when many runs arrive together | The backend sends no more calls at the same time than the setting allows. It tries again after `429`. | S2-09, S3-04 |
| Langfuse password login is turned off before an SSO account has the owner role, or the emails in Entra ID differ from the emails in Google | Nobody is locked out. Each step has an order and an email check. | S3-07 |

## How to read an issue

| Field | Meaning |
|---|---|
| Type | Feature, Infrastructure, Decision, Discovery or Verification |
| Depends on | The issues that must be complete or decided first |
| Tested with | The partner issue that proves that this issue works from start to end |
| Size | Approximate work: S (less than 1 day), M (1 to 3 days), L (3 to 5 days) |
| Acceptance criteria | The checkboxes that a reviewer marks before the issue closes |
| How to test | The test steps, from the unit tests to the paired test |

## Test environments

| Name | What runs there | Used for |
|---|---|---|
| **Unit** | `pytest` in `backend/`, and the OTel in-memory span exporter | Logic, validation, span content |
| **Local stack** | Docker Compose: monitor, PostgreSQL, OTel Collector, self-hosted Langfuse | Integration tests and paired tests on a laptop |
| **Test host** | The same Compose stack on one Compute Engine VM in GCP. The GCP jobs reach it on a private VPC path. It has no public IP. | Tests with the real GCP job code (Sprints 1 to 3) |
| **Test AWS cluster** | The Kubernetes installation (S3-06) | Installation test in Sprint 3 |
| **Production AWS cluster** | The Kubernetes installation | Release (Sprint 4) |

## Fixed versions (checked 2026-10-03)

Use these exact versions. Do not use `latest`. To change a version, change this table in a
pull request first.

| Component | Image or package | Version | Note |
|---|---|---|---|
| Python (backend) | `python:3.12.15-slim-bookworm` | 3.12.15 | Released 2026-10-01. Python 3.12 gets security fixes only, until 2028-10-31. |
| PostgreSQL (monitor database: local stack and CI) | `postgres:17.11-bookworm` | 17.11 | Changed 2026-10-08 (was 18.6): the same major version as the Cloud SQL instance of the test host. Newest 17.x image on Docker Hub, checked 2026-10-08. |
| PostgreSQL (monitor database: test host) | Cloud SQL for PostgreSQL | 17 | Changed 2026-10-08 (the instance was 18.6). Paid; GCP sandbox budget (2026-10-06). Google manages the minor version. Record the version that the instance shows. |
| PostgreSQL (Langfuse database) | `postgres:17.11-bookworm` | 17.11 | Released 2026-08-10. Langfuse v4: minimum 15, recommended 16; its CI tests 15 (unit and integration) and 17 (end-to-end and Docker build, the Compose default); 18 is not tested (checked at tag v4.50.0 on 2026-10-07). A separate database from the monitor. |

**Rule for database versions (2026-10-08):** every database uses the same major version,
**PostgreSQL 17**, in every environment (local stack, CI, test host, AWS). Minor versions
can differ. Move data only to the same or a newer major version, never down. Change a
major version only with a plan entry, in every environment together, dev first.
| OTel Collector | `otel/opentelemetry-collector-contrib` | 0.161.0 | Newest image on Docker Hub. Release 0.162.0 (2026-09-29) has no Docker Hub image yet. |
| Volume setup for the Collector (one-time `collector-init`) | `busybox` | 1.37.0 | Added 2026-10-07 (S1-06). Gives the `collector-data` volume to the Collector user (uid 10001). Checked on Docker Hub 2026-10-07. |
| Langfuse web | `langfuse/langfuse` | 4.50.0 | Released 2026-10-02 |
| Langfuse worker | `langfuse/langfuse-worker` | 4.50.0 | Must be the same version as Langfuse web |
| ClickHouse | `clickhouse/clickhouse-server` | 25.12.11.4 | Newest patch of the 25.12 line that the Langfuse Compose file uses. Version 26.9 exists, but Langfuse does not use it. |
| Redis | `redis` | 7.4.11 | Newest patch of the 7 line that the Langfuse Compose file uses. Version 8 exists, but Langfuse does not use it. |
| S3 storage (MinIO) | `cgr.dev/chainguard/minio` | Fix by image digest | The image that the Langfuse Compose file uses. The free Chainguard image has only the `latest` tag, so record its digest. |
| Langfuse Python SDK | `langfuse` | `>=4.16,<5` | S2-02. Approved by the project owner on 2026-10-05. 4.17.0 was the newest on PyPI. |
| OTel API, SDK and OTLP/HTTP exporter (backend) | `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` | `>=1.45,<2` | S2-02. Approved 2026-10-05. `langfuse` 4.x needs 1.45 or later. S1-05 part B uses the same range. |
| OTel FastAPI instrumentation (backend) | `opentelemetry-instrumentation-fastapi` | `>=0.66b0,<0.67` | Approved 2026-10-05. 0.66b0 is the release for OTel 1.45. S1-05 part B adds it to `requirements.txt`. |
| Langfuse Helm chart | `langfuse/langfuse` (langfuse-k8s) | 2.1.3 | Released 2026-09-28. Set the image tags to Langfuse 4.50.0 in the values file (S3-06). |
| OAuth2 Proxy (SSO for the dashboard) | `quay.io/oauth2-proxy/oauth2-proxy` | v7.15.5 | Released 2026-10-01. Checked 2026-10-05 (S3-07). |
| Mock OIDC server (local stack and CI only) | `ghcr.io/navikt/mock-oauth2-server` | 6.0.4 | Released 2026-09-29. Checked 2026-10-05. Never on the test host or AWS (S3-07). |
| LiteLLM proxy (judge) | Owned by another team | Record in S1-12 | We do not install it. Record its version and the model behind the judge alias (S1-12, S2-10). |

## Rule for prototype code (decided 2026-10-03)

The three prototype use cases (churn `AICT-L01`, chatbot `AICT-L02`, NBA `AICT-L03`) are a
scaffold. The real work is the GCP use cases.

| Code type | Example | Rule |
|---|---|---|
| Shared code: the GCP path uses it | The judge client (`litellm_judge.py`, S2-09) and the aggregation in `live_http.py`, `engines/health.py`, the alerts, the worker lease, the portfolio endpoints, the Langfuse settings in `config.py` | Keep it. Keep its tests. If a change breaks it, fix it. |
| Prototype-only code: the GCP path does not use it | The v1.1 telemetry adapter, the ML lane (Evidently, NannyML), the explanations (LIME, SHAP), the label backfill, the demo and scenario routes, the chatbot's Langfuse v2 store | Do not maintain it. If a change breaks it, remove it in the same pull request. Do not fix it. |

Before you remove code, search the repository to make sure that the GCP path does not use
it. The test host and AWS do not configure the prototype use cases. S4-07 removes the
remaining prototype-only code.

## Done for every issue

- The pull request has tests, and CI passes. `CHANGELOG.md` and `DEVLOG.md` are updated when the behavior changes.
- The pull request lists the checks that passed, failed, were skipped or were not available. A check that was not available is never reported as passed.
- No secrets or tokens in the code, the logs, the spans, the test files or the screenshots.
- GCP spans contain no text. Test files and screenshots contain only synthetic text or text with placeholders.

## All issues

| ID | Title | Type | Owner | Tested with | Size |
|---|---|---|---|---|---|
| S1-01 | Map one GCP job and write the JSON body v1 | Feature | GCP job developer. Backend reviews and approves. | S1-03 (a real body agrees with the schema) | M |
| S1-02 | Receiving API `POST /api/batch/runs` with API key | Feature | Backend | S1-03 | L |
| S1-02a | Paired test: a real GCP job sends a run summary to the test host | Verification | Backend + GCP job developer | S1-03 | S |
| S1-02b | Make the receiver agree with the approved S1-01 schema | Feature | Backend | S1-03 | S |
| S1-02c | ADR: push ingestion of GCP batch run summaries | Decision | Backend + project owner | — | S |
| S1-03 | GCP job sends the run summary after it publishes | Feature | GCP job developer | S1-02 | M |
| S1-04 | Deploy the monitor backend to a test host in GCP | Infrastructure | Platform | S1-03 | M |
| S1-05 | OTel in the GCP job and the backend: one trace for each run | Feature | Part A: GCP job developer. Part B: backend. | S1-06 | M + M |
| S1-06 | Minimal OTel Collector and front door (local stack and test host) | Infrastructure | Platform | S1-05 | M |
| S1-07 | Trace check tool | Feature | Backend | S1-05 + S1-06 | S |
| S1-08 | Security approval for the Sprint 1 data flow | Decision | Security + platform | — | S |
| S1-09 | Inventory of the 10 use cases and October run dates | Discovery | PM + source owners | — | M |
| S1-10 | First real run end to end | Verification | Backend + GCP job developer | S1-07 (trace check tool) | S |
| S1-11 | Database accounts for the backend and the developers | Infrastructure | Platform + backend | S1-02, S1-07 | S |
| S1-12 | Access to the company LiteLLM proxy for the judge | Discovery | Backend + LiteLLM proxy owner | S2-09 | S |
| S1-13 | Serve only the batch MVP API | Feature | Backend | S1-06 | M |
| S2-01 | Source registry: YAML settings and API key hashes | Feature | Backend + platform | S2-06 | M |
| S2-02 | Langfuse SDK v4 in the backend, and package approval | Decision + Feature | Backend + project owner | S2-05 | M |
| S2-03 | Collector exports to self-hosted Langfuse | Infrastructure | Platform | S2-04, S2-05 | L |
| S2-04 | OTel helper file for the GCP jobs | Feature | GCP job developer; backend reviews | S2-03 | M |
| S2-05 | Batch evaluator with the five LLM metrics | Feature | Backend + RAI | S2-03 | L |
| S2-06 | Onboard 4 use cases | Feature | Job developers + backend + platform | S2-01, S1-07 | L |
| S2-07 | Dashboard shows the GCP use cases with the current UI | Feature | Backend | S2-06 | M |
| S2-08 | One run as a single trace, GCP job to score | Verification | Backend + platform | S1-07 | S |
| S2-09 | Judge through the company LiteLLM proxy | Feature | Backend | S2-05 | M |
| S2-10 | RAI accepts the local judge | Verification | RAI + backend | S2-09 | M |
| S2-11 | Threat model for the batch MVP (R2) | Decision | Backend + security | S2-05 | S |
| S3-01 | Onboard 8 use cases, including split submit and harvest | Feature | Job developers + backend + platform | S1-07 | L |
| S3-02 | Delivery lane: missed-run and failed-job alerts | Feature | Backend | S3-04 | M |
| S3-03 | Collector hardening: attribute filter, memory limit, disk queue | Infrastructure | Platform | S3-04, S3-05 | M |
| S3-04 | Failure and recovery drills | Verification | Backend + platform | S1-07 | M |
| S3-05 | Security and retention review with leak scan | Verification | Security + platform + source owners | S3-03 | M |
| S3-06 | Kubernetes deployment files: Langfuse Helm chart and our manifests | Infrastructure | Platform | S4-01 | L |
| S3-07 | SSO login for the dashboard and Langfuse (Google now, Entra ID later) | Infrastructure | Platform; backend reviews | S3-05, S3-04 | M |
| S4-01 | Deploy the stack to the production AWS cluster | Infrastructure | Platform | S4-02 | L |
| S4-02 | Change every GCP job to send to AWS | Feature | Job developers + platform | S4-01 | M |
| S4-03 | Finish all 10 use cases | Feature | Job developers + backend + platform | S4-04 | L |
| S4-04 | 10-row evidence checklist | Verification | Backend + RAI | S1-07 (trace check tool) | M |
| S4-05 | Operations drills and runbooks on AWS | Verification | Platform + operations | S1-07 (trace check tool) | M |
| S4-06 | Release sign-off | Decision | RAI + platform owners | — | S |
| S4-07 | Remove the prototype-only code | Feature | Backend | Full test suite | M |

## Overview by phase

For the overall view, the issues are in 16 workstreams. Each issue is in one workstream
only. GitHub issues are the tracker; this file is the source of their text.

| Phase | Workstream | Issues | PIC |
|---|---|---|---|
| Define | Security approval and use-case inventory | S1-08, S1-09 | Security + PM |
| Define | Package approval and LiteLLM proxy access | S1-12, S2-02 | Backend + project owner |
| Prepare | Test host, front door and database accounts | S1-04, S1-06, S1-11 | Platform |
| Prepare | Self-hosted Langfuse and Collector hardening | S2-03, S3-03 | Platform |
| Prepare | SSO login (Google now, Entra ID later) | S3-07 | Platform |
| Prepare | Kubernetes files and production AWS cluster | S3-06, S4-01 | Platform |
| Build | JSON body, receiving API and GCP send step | S1-01, S1-02, S1-02a, S1-02b, S1-02c, S1-03 | GCP job developer + backend |
| Build | OpenTelemetry tracing and trace check tool | S1-05, S1-07, S2-04 | GCP job developer + backend |
| Build | Registry, evaluator and LiteLLM judge | S2-01, S2-05, S2-09 | Backend |
| Build | Dashboard and delivery alerts | S2-07, S3-02 | Backend |
| Build | Onboard use cases (4, 8, 10) and move jobs to AWS | S2-06, S3-01, S4-02, S4-03 | Job developers + backend + platform |
| Validate | Sprint demos: first real run, one trace to the scores | S1-10, S2-08 | Backend + platform |
| Validate | RAI accepts the local judge | S2-10 | RAI + backend |
| Validate | Drills and security review | S3-04, S3-05, S4-05 | Platform + security |
| Conclude | Evidence checklist and release sign-off | S4-04, S4-06 | RAI + platform owners |
| Conclude | Remove the prototype-only code | S4-07 | Backend |

---

## Sprint 1 — Oct 5–9: get data out of GCP

**Two channels, one trace ID**

| Channel | Carries | Path | If it fails |
|---|---|---|---|
| Receiving API (S1-02, S1-03) | The run summary. This is the official data. | GCP job → HTTPS `POST` → backend → PostgreSQL | The job tries again. The run must arrive. |
| OpenTelemetry (S1-05, S1-06) | The time of each step, and the trace ID | GCP job and backend → OTLP/HTTP → Collector | The data still arrives. The trace has a gap. |

The OTel SDK in the GCP job adds a W3C `traceparent` header to its API call. The backend
reads this header. Thus the backend spans join the trace of the job, and the backend
stores the trace ID with the run.

**Who does what**

| Track | Issues | Owner |
|---|---|---|
| GCP side | S1-01, S1-03, S1-05 part A | GCP job developer |
| Monitor side | S1-02, S1-05 part B, S1-07 | Backend |
| Infrastructure | S1-04, S1-06, S1-11 | Platform. The firewall and the certificates: your team. |
| Decisions and discovery | S1-08, S1-09, S1-12 | Security, PM, backend |

The two tracks start on Monday with the draft schema from S1-01. They meet on the test host.

**Long-lead requests (send in Sprint 1)**

These requests need approval from other teams, and the approval can take a long time. Send
them in Sprint 1, so that the answers arrive before the sprint that needs them.

| Request | Owner | Needed by | If it is not approved in time |
|---|---|---|---|
| DNS name and certificate for the AWS production stack | Your team + network team | S4-01 (26 October) | Use the IP address and a private CA certificate |
| Production AWS Kubernetes cluster, its owner and access | Platform | S4-01 (26 October) | Report the result as a pilot on the test AWS cluster. Do not report a production release. |
| Amazon RDS for PostgreSQL 17 (monitor and Langfuse, two instances) and Amazon S3 (plan A, S3-06) | Platform + AWS team | 21 October | Use plan B: PostgreSQL and MinIO in the cluster |
| Test AWS Kubernetes cluster (not production) and access | Your team | S3-06 (19 October) | Test the S3-06 files on a disposable local cluster (kind) only |
| LiteLLM virtual keys for the judge (test host and AWS), the model alias, and a network path to the proxy (S1-12) | LiteLLM proxy owner + network team | S2-09 (12 October) | Do not deploy S2-09 to the test host. Test S2-05 and S2-09 on the local stack with a fake LiteLLM server. The Sprint 2 demo shows the trace without scores. |
| A private DNS name for the test host under a company domain, in a Cloud DNS private zone (for example `monitor-test.<company domain>`). Google does not accept an IP address or a `.internal` name in an SSO redirect URI. The name does not have to be public. | Your team + network team | S3-07 (19 October) | No SSO on the test host. The dashboard and Langfuse keep only the firewall rules and the Langfuse accounts. S3-05 records the exception. |
| Two Google OAuth clients of type "Internal" (dashboard and Langfuse), with the redirect URIs of the test host and AWS | Google Workspace administrator + platform | S3-07 (19 October) | The same as the DNS name |

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S1-03 GCP sender | S1-02 receiving API | A real run summary from GCP is stored as one row in PostgreSQL | Test host |
| S1-05 part A, GCP OTel | S1-06 Collector | The spans of the job arrive in the Collector | Test host |
| S1-05 part B, backend OTel | S1-05 part A + S1-06 | The backend span has the same trace ID as the root span of the job | Test host |
| S1-07 trace check tool | S1-05 + S1-06 | One command finds the same trace ID in the database and in the Collector output | Local stack, then test host |

### S1-01 — Map one GCP job and write the JSON body v1

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | GCP job developer. Backend reviews and approves. | — | S1-03 (a real body agrees with the schema) | M |

**What:** The GCP job developer maps one job to the record fields of the
[standard](llm-metrics-standard.md). Then the developer writes the JSON Schema of the run
summary, with example bodies. The schema is kept in this repository, because the backend
examines each request with it. Thus backend reviews and approves the schema. There is no
separate mapping table. The description of each field in the schema tells where its value
comes from in the job.

The developer answers these questions in the schema or in the pull request:
- Where does the job publish the results (file and function)? The send step comes after this point.
- Which part of the prompt is the instruction (`question`)? Which part is the source material (`retrieval_context`)?
- How does the job show a refusal or a safety block (`refused`)?
- Does the job use the Gemini Batch API (then `latency_s` is `null`) or online calls?
- Where can PII occur? The redaction in S1-03 must cover these locations.
- When the job fails, what does it log now? Can it still send a run summary with `status: failed`?

**Acceptance criteria**
- [ ] The schema file and 4 examples are in the repository: a normal run, a partial failure, a Batch API run with `latency_s` set to `null`, and an identity-only run (S1-03). The examples use synthetic text only.
- [ ] The schema accepts `records: []` with `records_reason: records_not_approved`. This is the identity-only mode.
- [ ] Each field has a description that tells its source in the job. The required fields and the optional fields are clear. The schema rejects unknown fields.
- [ ] Free text is allowed only in `question`, `answer`, `retrieval_context` and `tool_calls`. The schema has no customer ID field.
- [ ] The body has no trace field. The trace ID goes in the `traceparent` HTTP header (S1-05).
- [ ] The failure signals are agreed with the GCP developer. The job writes a log entry for its own team when the job fails and when a send to the monitor fails (never the key or the body). The monitor gets failures only from what the job sends: a body with `status: failed` when possible, and the OTel span of the send step with its error status (S1-05). The monitor team needs no access to GCP logs (decided 2026-10-07).
- [ ] Backend, RAI and security (S1-08) reviewed the schema.

**How to test**
1. Unit: `pytest` examines each example with the schema. Make sure that a wrong example (no `run_id`, a wrong type, an unknown field) fails.
2. Paired with S1-03: build a body from a real run. Make sure that it agrees with the schema.

### S1-02 — Receiving API `POST /api/batch/runs` with API key

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S1-01 (the draft schema is sufficient to start) | S1-03 | L |

**What:** Add an endpoint that examines the API key, examines the run summary with the
S1-01 schema, and stores the run one time in a new table `batch_runs`. Add the table with an
additive migration in `backend/app/db.py`. A stored row never changes. The trace ID comes
from the `traceparent` header through the OTel context (S1-05 part B). The backend stores it
with the row.

**Authentication: a static API key in all environments (decided 2026-10-05)**

The test host is in GCP (S1-04). There, the request stays on a private VPC path. In
Sprint 4, the jobs send to AWS, and the request goes across the internet, because there
is no VPN between GCP and AWS. The API key is the same in the two environments. Thus the
test on GCP proves the method that production uses. Three layers protect the request:

| Layer | Test host (GCP, Sprints 1 to 3) | Production (AWS, Sprint 4) | Owner |
|---|---|---|---|
| API key | `Authorization: Bearer <key>`. A random key of at least 32 bytes for this use case. The GCP job reads it from Secret Manager. The backend stores only its SHA-256 hash and compares in constant time. | The same | Backend + GCP developer |
| Encryption | HTTPS only, with a private CA certificate for the private DNS name (S1-04) | HTTPS only (S4-01) | Platform |
| Network | Private VPC path. A VPC firewall rule allows port 443 only from the network ranges of the GCP jobs. The VM has no public IP. (S1-04) | The AWS security rules allow only the egress IPs of the GCP jobs, for example Cloud NAT static IPs (S4-01) | Your team |

Other options:

| Option | Shared secret | Work | Decision |
|---|---|---|---|
| Static API key + HTTPS + network rules | Yes | Low. The same method as the existing tokens of the monitor. | **Selected** for GCP and for AWS |
| Google service-account identity token: the job gets a token that Google signs. The backend examines the signature and the service-account email. | No | Medium. It needs the `google-auth` package. | Not in October. Only if security requires it (S1-08). |
| Mutual TLS | No | High. Each job needs a client certificate. | Not planned |
| VPN or private link between GCP and AWS | — | Depends on the network team | Not available yet. The test host does not need it, because it is in GCP. |

**Acceptance criteria**
- [ ] A correct body with a correct key: `201`. One row is stored.
- [ ] The same body again: `200`. There is still one row.
- [ ] The same `(use_case_id, run_id)` with different content: `409`. The first row does not change.
- [ ] A wrong body: `400` with the field errors. Nothing is stored. This includes an unknown field, a missing record field, `latency_s` set to `0`, and more records than the sample size allows.
- [ ] No key or a wrong key: `401`. Nothing is stored. The key and the body are never written to a log.
- [ ] The records are stored in the run as they arrived. The backend keeps `record_id` for the evaluator.
- [ ] An identity-only body (`records: []`, reason `records_not_approved`) is stored. Later, all five metrics of this run show "Unknown" with this reason, because they all come from the records.

**How to test**
1. Unit and integration: `pytest` for each acceptance criterion, with the S1-01 examples.
2. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. Paired with S1-03: a real GCP job sends to the test host. Make sure that one row exists for its `run_id`.

### S1-02a — Paired test: a real GCP job sends a run summary to the test host

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Backend + GCP job developer | #41 merged, S1-03 (#5), S1-04 (#6) | S1-03 | S |

**What:** Do step 3 of "How to test" of #4. A real GCP job sends its run summary to
`POST /api/batch/runs` on the test host. This is the paired test of S1-02 and S1-03. The
code and the unit tests are in #41. They cannot prove this step, because no real job and
no test host were available.

**Preparation**
1. Make a key and its hash for the use case of the job (command in `docs/STRICT-LIVE.md`, "Batch run receiver").
2. Put the key in GCP Secret Manager of the job project.
3. Put only the hash in `BATCH_API_KEY_SHA256` on the test host.

Warning: never put the key or the hash in git, chat, email or a ticket.

**Acceptance criteria**
- [ ] A real run of the job gives `201`. One row exists in `batch_runs` for its `(use_case_id, run_id)`.
- [ ] A retry of the same send gives `200`. There is still one row.
- [ ] The stored body agrees with what the job sent (record count, `record_id` values).
- [ ] If S1-05 part A is ready: the stored `trace_id` is the trace ID of the job, and `trace_id_source` is `traceparent`. If not: `trace_id_source` is `generated`. Record which.
- [ ] The logs of the test host contain no key, no `Authorization` header and no body text.
- [ ] A send with a wrong key gives `401`. The GCP developer confirms that the job logged the failed send for its own team (S1-01 criterion 6; the monitor team has no access to GCP logs).

**How to test**
1. Run the job on the test host path. Query `batch_runs` for its `run_id`.
2. Send the same body again from the job (retry). Count the rows again.
3. Search the test host logs for the key, the record text and `Authorization`.
4. Record the evidence in `DEVLOG.md` and in a comment on #4.

### S1-02b — Make the receiver agree with the approved S1-01 schema

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S1-01 (#3) approved, #41 merged | S1-03 | S |

**What:** #41 builds the receiver against the S1-01 **draft** schema `batch-run/1`. When
the GCP developer, RAI and security approve S1-01, make the backend agree with the
approved schema. All the rules are in one module, `backend/app/batch_schema.py`, so the
change is small.

The schema README says that the schema "moves to the backend" with S1-02. Today the
tests read the examples from `changes/2026-10-02-batch-monitoring-mvp/schema/examples/`.

**Acceptance criteria**
- [ ] Compare the approved `batch-run-1.schema.json` with `BatchRunV1` field by field (types, lengths, required fields, the `allOf` rules). Record each difference in the pull request.
- [ ] Change `batch_schema.py` and its tests for each difference. Remove the "DRAFT" note.
- [ ] Move the approved schema file and its examples to the backend (for example `backend/schemas/batch-run/1/`). Point `tests/test_batch_schema.py` and `tests/test_batch_runs_api.py` to the new location.
- [ ] If a change makes stored rows invalid, the schema version changes (`batch-run/2`). Stored rows never change (#4).
- [ ] Update `docs/STRICT-LIVE.md` ("Batch run receiver"), `CHANGELOG.md` and `DEVLOG.md`.

**How to test**
1. `.venv/bin/python -m pytest -q -m "not slow"` from `backend/`.
2. Each approved example passes. Each invalid example fails with the expected field.

### S1-02c — ADR: push ingestion of GCP batch run summaries

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Decision | Backend + project owner | — | — | S |

**What:** Write an ADR for push ingestion of GCP batch run summaries
(`POST /api/batch/runs`, #41). The monitoring contract v1.1 is pull-only, and
`CLAUDE.md` says that the monitor makes no producer demands and that only the poller
writes monitoring data. `DEVLOG.md` (2026-10-02) asked for this ADR before code. #41 added
the endpoint as #4 specifies, so the ADR records the decision after the fact.

**Acceptance criteria**
- [ ] `docs/adr/0002-batch-push-ingest.md` and its line in `docs/adr/README.md`.
- [ ] The ADR states: why push and not pull for the GCP jobs, the trust boundary (API key, HTTPS, network rules), why the endpoint never touches a v1.1 cursor, and how stored runs stay immutable.
- [ ] The ADR states the risk tier (`intent.md` of the batch MVP) and who accepted it.
- [ ] `CLAUDE.md` and `README.md` agree with the ADR (`CLAUDE.md` stays within 120 lines).
- [ ] The "Known gaps" entry in `DEVLOG.md` about the missing ADR is removed.

**How to test**
1. `backend/tests/test_docs.py` passes (links resolve, one H1, `CLAUDE.md` ≤ 120 lines).
2. The project owner approves the pull request.

### S1-03 — GCP job sends the run summary after it publishes

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | GCP job developer | To build: S1-01. To test from start to end: S1-02 and S1-04. | S1-02 | M |

**What:** This is a feature in the code of the GCP job. It is not a test step. Add a step
after the publish step. The step does these actions:
1. It selects a uniform random sample of records (default 50).
2. It replaces phone numbers, email addresses and national ID numbers with `[PHONE]`, `[EMAIL]` and `[NATIONAL_ID]`.
3. It builds the run summary.
4. It sends the run summary with the API key from Secret Manager.
5. It tries again with a delay after a network error or a `5xx` response.

A failed send must not stop the business job.

**Identity-only mode.** The setting `SEND_RECORDS` controls the records. Until security
approves (S1-08), the setting is off. Then the job sends only the run identity, with
`records: []` and the reason `records_not_approved`. No text leaves GCP. With this mode, the
team can test the send step, the API key, the retries and OTel from 6 October. When security
approves, set `SEND_RECORDS` to on. No code change is necessary.

The developer can build and unit test the step from Monday with the S1-01 schema and a fake
server. Only the test from start to end waits for the API (S1-02) on the test host (S1-04).

**Acceptance criteria**
- [ ] The step runs only after the publish step is successful.
- [ ] The step tries again after a timeout or a `5xx`. It does not try again after `400`, `401` or `409`.
- [ ] The job ends successfully also when the monitor is not available.
- [ ] Each failed send writes a log entry with `run_id`, the HTTP status or the error type, and the attempt number. The log entry never contains the key or the body.
- [ ] A failed job writes a log entry. It sends a run summary with `status: failed` if S1-01 agreed that it can.
- [ ] The sample size follows the setting. A run that is smaller than the sample sends all its requests.
- [ ] The body contains no raw phone number, email address or national ID number.
- [ ] When `SEND_RECORDS` is off, the body has `records: []` and the reason `records_not_approved`. The default is off.
- [ ] The job verifies the HTTPS certificate. With a private CA (S1-04), the job trusts that CA file. It never turns the verification off.

**How to test**
1. Unit (GCP repository): make sure that the body agrees with the S1-01 schema, that synthetic PII becomes placeholders, and that the sample size is correct. Make sure that the sender tries again after a fake `503`, stops after `400`, and logs each failure.
2. Paired with S1-02 on the test host: run the job in the GCP dev project. Make sure that the job log shows `201`, and that `batch_runs` has one row with the same `run_id`. Run the job again. Make sure that the log shows `200` and that there is still one row.
3. Failure test: give the job a wrong URL. Make sure that the job ends successfully and that Cloud Logging shows the failed sends.
4. Identity-only test: set `SEND_RECORDS` to off and run the job. Make sure that the stored run has no records and has the reason `records_not_approved`.

### S1-04 — Deploy the monitor backend to a test host in GCP

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | The prerequisites below. Due Tuesday 6 October. | S1-03 | M |

**What:** Make one Compute Engine VM in GCP (decided 2026-10-05). Install the monitor
backend and the Collector (S1-06) on it with Docker Compose. The monitor database is a
**Cloud SQL for PostgreSQL** instance with a private IP only (decided 2026-10-06), not a
container on the VM. The GCP jobs reach the VM on a private VPC path. The VM has no public
IP. In Sprint 2, Langfuse comes on the same VM, with its own PostgreSQL container (S2-03).

**Prerequisites (ask the network team and the GCP owner first)**

| Question | Why it is important | Owner |
|---|---|---|
| Which GCP project and billing account hold the VM? | The owner of the cost and of the access | Your team |
| How does the VM network connect to the job projects: the same VPC, Shared VPC, or VPC peering? | The private path from the jobs to the VM | Network team |
| Where does each job run: Cloud Run jobs, GKE, Compute Engine, Vertex AI or Dataflow? | Cloud Run and serverless jobs need Direct VPC egress or a Serverless VPC Access connector to reach an internal IP. Record the runtime of each job in S1-09. | GCP developer |
| What are the network ranges of the jobs? | The VPC firewall rule for port 443 (S1-02, S1-06) | Network team |
| Which private DNS name does the VM get? | A Cloud DNS private zone that the job VPC can see. Use a name under a company domain, because SSO needs it later (S3-07). | Your team |
| Can the VM reach the company LiteLLM proxy? | The judge (S1-12, S2-09) | Network team |
| How do the staff reach the VPC from the office: the company VPN or Interconnect to GCP? | The dashboard and Langfuse from Sprint 2 (Sprint 2 prerequisites) | Network team |

**The VM**

| Item | Setting |
|---|---|
| Machine | `e2-standard-8` (8 vCPU, 32 GiB), the recommended size of the Sprint 2 prerequisites. It is large enough for Langfuse. Thus no resize is necessary in Sprint 2. |
| Disk | 200 GiB `pd-balanced`. A daily snapshot schedule that keeps 7 snapshots. The snapshots hold the Langfuse data (S2-03) and the Collector files. The monitor data is in Cloud SQL, with its own backups. |
| Image | Ubuntu 24.04 LTS, Shielded VM on |
| Network | No external IP. Cloud NAT for outbound traffic only (Docker images, operating-system updates). |
| Service account | A dedicated account with only the roles that the VM needs, for example log and metric writer. Do not use the default Compute Engine service account. |
| SSH | Only through IAP: `gcloud compute ssh <vm> --tunnel-through-iap`. The firewall allows port 22 only from the IAP range `35.235.240.0/20`. |

**The Cloud SQL instance (monitor database)**

| Item | Setting |
|---|---|
| Engine | Cloud SQL for PostgreSQL 17 (fixed-versions table; changed from 18.6 on 2026-10-08). Google manages the minor version. |
| Size | 1 vCPU, 3.75 GiB memory, 100 GB SSD. Zonal, not high availability, because it is a test host. |
| Network | **Private IP only**, in the VM's VPC (Private Services Access). No public IP and no authorized networks. |
| Encryption | Allow only TLS connections. The backend uses `sslmode=verify-ca` in `DATABASE_URL` with the server CA file of the instance. |
| Backups | Automatic daily backups, 7 kept, and point-in-time recovery |
| Cost | A paid service, approved on the GCP sandbox budget (2026-10-06) |
| Accounts | S1-11. The backend never uses the `postgres` user. |

**VPC firewall rules (ingress)**

| Port | From | For |
|---|---|---|
| 443 | The network ranges of the GCP jobs | The API and the Collector (S1-06) |
| 8443, 3443 | The staff network ranges (from Sprint 2) | The dashboard and Langfuse |
| 22 | `35.235.240.0/20` (IAP) | SSH for platform and developers (S1-11) |
| All other ports | — | Refused. The database ports on the VM (Langfuse, from Sprint 2) are never open. |

The VPC firewall rules do not protect the Cloud SQL private IP. Cloud SQL is protected by
the private IP only, TLS only, and the database accounts (S1-11).

**Certificate.** The name is private. Thus a public CA cannot sign it. Make a private CA
and a certificate for the private DNS name. Replace the certificate before it expires. The
job trusts the CA file (S1-03). The verification stays on. Google Certificate Authority
Service is a paid service. Do not use it without a plan entry. Plain HTTP is not allowed.

**Acceptance criteria**
- [ ] The answers to the prerequisites are in this issue.
- [ ] The VM exists with the settings in the table. It has no external IP.
- [ ] The monitor backend and the Collector run on the VM.
- [ ] The Cloud SQL instance has the settings in the table. It has no public IP. It accepts only TLS connections.
- [ ] The backend connects to Cloud SQL over the private IP with `sslmode=verify-ca`. The migrations run when the backend starts.
- [ ] The private DNS name resolves from the job VPC to the internal IP of the VM.
- [ ] The API uses HTTPS with the private CA certificate. Plain HTTP is refused.
- [ ] Only the network ranges of the jobs can reach port 443. The database ports on the VM are closed.
- [ ] SSH works only through IAP.
- [ ] The API key and the other secrets are host secrets. They are not in the repository.

**How to test**
1. From the GCP dev project, on the job runtime: `curl --cacert <ca-file> https://<private-dns-name>/api/health` returns `200`.
2. From a network range that is not in the firewall rule: the connection is refused or times out.
3. `POST /api/batch/runs` without a key returns `401`.
4. `gcloud compute instances describe <vm>` shows no external IP. The private DNS name does not resolve from the internet.
5. `gcloud compute ssh <vm> --tunnel-through-iap` works. SSH to the internal IP from outside the VPC does not work.
6. `gcloud sql instances describe <instance>` shows no public IP (`ipv4Enabled: false`) and the TLS-only setting. On the VM, `GET /api/readiness` shows `database.ok: true`.
7. On the VM, `psql "host=<private-ip> sslmode=disable ..."` is refused. With `sslmode=verify-ca` it works.
8. If the VM is late: the GCP developer saves a real body to a file. We send it to the local stack and record that the real delivery was not tested.

### S1-05 — OTel in the GCP job and the backend: one trace for each run

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Part A: GCP job developer. Part B: backend. | Part A: S1-03. Part B: S1-02. The OTel packages are approved in the Sprint 1 spec. | S1-06 | M + M |

**What:** Add the OpenTelemetry SDK on the two sides, so that one batch run is one trace.

| Step | Where | What happens |
|---|---|---|
| 1 | GCP job (part A) | Start a root span `batch.run` with `use_case_id` and `run_id` |
| 2 | GCP job (part A) | Make the child spans `batch.submit`, `batch.harvest`, `batch.publish` and `batch.send` |
| 3 | GCP job (part A) | Call the API with an HTTP client that has OTel instrumentation. The client adds the `traceparent` header. |
| 4 | Backend (part B) | The FastAPI instrumentation reads the header. The backend server span is a child of the job's HTTP client span, and the `monitor.ingest` span is a child of the server span. Thus `batch.send` is an ancestor of `monitor.ingest` (decided 2026-10-06). |
| 5 | Backend (part B) | The backend stores the trace ID in the `batch_runs` row |
| 6 | Both | The spans go over OTLP/HTTP to the Collector (S1-06) |

Text in spans: GCP spans contain no text. Backend spans can contain the redacted record
text that the API accepted (the `monitor.evaluate` span in S2-05). The `monitor.ingest` span
contains no body content. The token spans and the attribute allowlist come in S2-04.

**Acceptance criteria**
- [ ] Part A: one trace for each run. `batch.send` is the parent of the HTTP client span. The request has a `traceparent` header.
- [ ] Part B: `monitor.ingest` has the same trace ID as the root span of the job, and `batch.send` is its ancestor (job HTTP client span → backend server span → `monitor.ingest`). The `batch_runs` row stores this trace ID.
- [ ] A request without `traceparent` starts a new trace in the backend. The backend stores its ID.
- [ ] The spans contain only IDs and the status (`use_case_id`, `run_id`, result). They contain no text from the body.
- [ ] Part A: a failed send sets the error status on `batch.send`, with the attempt number and the HTTP status or the error type. A failed job sets the error status on `batch.run`. These spans are how the monitor sees GCP-side failures, because the monitor team has no access to GCP logs (S1-01).
- [ ] If the Collector is not available, the job and the API continue to work. The job logs the failed export.

**How to test**
1. Unit, part A (GCP repository): use an in-memory span exporter. Make sure that the span names and the parent links are correct, and that the request has a `traceparent` header.
2. Unit, part B (backend): send a request with a known `traceparent`. Make sure that the trace ID is correct, that the parent of the server span is the span ID in the header, that `monitor.ingest` is a child of the server span, and that the stored trace ID is correct.
3. Paired with S1-06 on the test host: run the job. Make sure that the spans of the job and the backend span have the same trace ID in the Collector output. Run `scripts/check_trace.py <trace_id>`.
4. If GCP cannot reach the Collector yet: the job sends its spans to Cloud Logging. The trace is still connected, because the header arrives at the backend.

### S1-06 — Minimal OTel Collector and front door (local stack and test host)

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | Local: none. Test host: S1-04 | S1-05 | M |

**What:** Add the OTel Collector to Docker Compose. Use the contrib image with a fixed
version. The Collector receives spans on OTLP/HTTP. It writes the spans to the `debug`
output and to a file in a mounted folder. The Langfuse export comes in S2-03.

**Local part (done in `changes/2026-10-07-s1-06-local-compose/`):** `deploy/compose/compose.yaml`
(base), `compose.local.yaml`, `otel-collector.yaml`, `scripts/compose-smoke.sh` and
`.github/workflows/compose-smoke.yml`. The file output is `/data/spans.jsonl` in the
named volume `collector-data`. The distroless Collector image has no `/tmp` and runs as
uid 10001, so a one-time `collector-init` service (`busybox:1.37.0`) gives the volume to
that user first; the Collector stays non-root. Read the file with `docker compose cp`. The test host adds `compose.testhost.yaml` (S1-04).

On the test host, put one reverse proxy (the front door) in front of the backend and the
Collector:

| Path | Goes to | Who calls it | Protection |
|---|---|---|---|
| `https://<host>/api/batch/runs` and `https://<host>/api/health` | Backend | GCP job | API key, VPC firewall rule |
| `https://<host>/otlp/*` | Collector | GCP job | OTLP token, VPC firewall rule |
| Other paths on port 443, for example `/api/live/*` | Nothing. The front door returns `404`. | — | The dashboard data is not available to GCP (S3-07) |
| Docker network inside the VM | Collector | Backend | Not open outside the VM |

`<host>` is the private DNS name of the VM (S1-04). The VPC firewall opens port 443 only
for the network ranges of the GCP jobs. The front door has one certificate (S1-04). From
Sprint 2, the same front door also serves the staff: the dashboard on port 8443 and Langfuse
on port 3443, for the staff network ranges only (Sprint 2 prerequisites). From Sprint 3,
the staff also log in with SSO (S3-07).

**Acceptance criteria**
- [ ] `docker compose up` starts the Collector with a health check.
- [ ] The Collector image has the version from the fixed-versions table. It does not use `latest`.
- [ ] Spans that come in on OTLP/HTTP appear in the file output.
- [ ] On the test host, the front door is the only entry. It has no public IP. Port 443 accepts only the network ranges of the GCP jobs.
- [ ] On port 443, `GET /api/live/portfolio` returns `404`. Only `/api/batch/runs`, `/api/health` and `/otlp/*` reach a service.
- [ ] `/otlp/*` rejects a request without the correct OTLP token. The OTLP token is different from the API key.
- [ ] The GCP job reads the OTLP token from Secret Manager and sends it with `OTEL_EXPORTER_OTLP_HEADERS`.
- [ ] The Collector configuration is in the repository. It contains no secrets.
- [ ] After S2-03 works, a cleanup step deletes the file output on the test host.

**How to test**
1. Local: send test spans with `telemetrygen traces --otlp-http`. Make sure that the file output contains them.
2. Test host, from the GCP dev project: send test spans to `https://<host>/otlp/v1/traces` with the token. Make sure that the file output contains them.
3. Send spans without the token. Make sure that they are rejected.
4. Send a request from a network range that is not in the firewall rule. Make sure that the connection is refused or times out.
5. From the GCP dev project: `curl --cacert <ca-file> https://<host>/api/live/portfolio`. Make sure that the result is `404`.
6. Paired with S1-05: see the test steps in S1-05.

### S1-07 — Trace check tool

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S1-02, S1-05 part B, S1-06, S1-11 | S1-05 + S1-06 | S |

**What:** Write the script `scripts/check_trace.py <trace_id>`. The script shows the result
for each item:

| Item | Where the script looks | "Found" means |
|---|---|---|
| Run row | Postgres table `batch_runs` | A row has this trace ID |
| GCP root span | Collector file | A `batch.run` span has this trace ID |
| Monitor span | Collector file | A `monitor.ingest` span has this trace ID |
| Ancestor link | Collector file | Following the parent IDs up from `monitor.ingest` reaches the job's `batch.send` span (through the job's HTTP client span and the backend server span). If no run row has the trace ID, but a `monitor.ingest` span has `stored_trace_id`, show "duplicate delivery; the run is stored under trace `<id>`". |
| Langfuse trace and score | Langfuse API | Added in S2-03 |

Run the script on the host where the stack runs. The script uses the read-only database
account from S1-11. It is a tool for developers and operators. It is not part of the
product.

**Acceptance criteria**
- [ ] The script shows "found" or "missing" for each item, with the run ID and the times.
- [ ] If an item is missing, the script stops with a non-zero exit code. CI and the drills can use this code.
- [ ] The script reads credentials from environment variables. It never shows them.
- [ ] The script only reads. It does not change the database or the files.

**How to test**
1. Paired with S1-05 and S1-06: send one example request with a known `traceparent`. Run the script with this trace ID. Make sure that the run row and the monitor span are "found".
2. On the test host, run the GCP job. Run the script with the trace ID of the run. Make sure that all four items are "found".
3. Run the script with a random trace ID. Make sure that all items are "missing" and the exit code is not zero.

### S1-08 — Security approval for the Sprint 1 data flow

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Decision | Security + platform | S1-01 | — | S |

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
| Redacted records leave GCP. They go to the monitor, to the local judge model through the company LiteLLM proxy, and to Langfuse. They do not go to an external LLM provider. | S1-01, S1-03, S1-12 |
| The LiteLLM proxy logs: does the proxy store the judge prompts and answers? Where, and for how long? Does it send them to other tools? | S1-12 |
| The list of PII types that the job replaces with placeholders | S1-03 |
| The retention period for stored records | S1-02 |
| An API key on a private VPC path in GCP (test host), and later on the internet with an IP allowlist (AWS, Sprint 4) | S1-02, S1-04, S4-01 |
| The private CA certificate of the test host | S1-04 |
| The OTLP endpoint that the GCP jobs reach through the front door | S1-06 |
| Real redacted data on the test host in GCP: on the VM and in the Cloud SQL instance (private IP only, TLS only, automatic backups for 7 days). On the test host, the records stay in GCP. Only the judge calls go to the LiteLLM proxy. | S1-04, S1-11, S1-12 |
| Database accounts, and who can read real data | S1-11 |

**Acceptance criteria**
- [ ] Each item in the table is approved in writing, or blocked with an owner and a date.
- [ ] The list of PII types is written down.
- [ ] The name of a security contact is in this issue.

**How to test**
1. Link the approval in this issue.
2. Compare the S1-01 schema with the approved fields, one field at a time.
3. Compare the S1-03 placeholder list with the approved PII types.
4. If the approval is not complete by 8 October, the job does not send records. All five metrics show "Unknown".

### S1-09 — Inventory of the 10 use cases and October run dates

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Discovery | PM + source owners | — | — | M |

**What:** Make one table with one row for each of the 10 GCP use cases. Sprints 2, 3 and 4
use this table to select the order of the use cases. The due date is Friday 9 October.

**Added 2026-10-08:** each job developer also fills in the
[use-case template](../2026-10-08-batch-metric-profiles/use-case-template.md) (task type,
input, output format, labels later), one comment for each use case. The answers select the
quality profile of each use case ([core metrics and profiles](../2026-10-08-batch-metric-profiles/core-metrics.md)).
Sprint 2 cannot be planned again without these answers.

| Column | Why we need it |
|---|---|
| Use-case ID | The registry and the API use this ID |
| Owner | The person who confirms that a run is real |
| GCP job and repository | The location of the code that sends the data |
| Developer of the job | The person who adds the send step and OTel. This person can be different for each job. |
| GCP project, job runtime and network range | The private path and the VPC firewall rule to the test host (S1-04). Cloud Run and serverless jobs need VPC egress. |
| Egress IP of the job, for example a Cloud NAT static IP | The AWS security rules in Sprint 4 allow only known IP addresses (S4-01). Each project can have a different IP. |
| October run dates | The dates when a real run can arrive. If a job does not run in October, book a controlled rerun. |
| Batch API or online calls | With the Batch API, `latency_s` is `null` |
| Approximate number of requests in each run | This number sets the sample size and the load on the LiteLLM proxy (S1-12) |
| Language: Thai, English or mixed | RAI must know the language that the judge examines. The reference set of S2-10 uses the same mix. |
| Data sensitivity | Security uses this for the approval (S1-08) |
| Owner of the task description | The person who writes the task description for the judge, with RAI |

**Acceptance criteria**
- [ ] The table has exactly 10 rows. Each row has a named owner and a named developer.
- [ ] Each use case has at least one October run date, or a booked controlled rerun.
- [ ] Each GCP job has a known runtime and network range for the test host, and a known egress IP for AWS.
- [ ] The order of the use cases for Sprints 2 to 4 is agreed.
- [ ] Each use case has a filled use-case template, and RAI confirmed its profile.

**How to test**
1. Each owner confirms their row in the issue comments.
2. Platform adds the network ranges to the firewall plan of the test host (S1-04), and the egress IPs to the AWS plan (S4-01).

**Risk:** The team examined only 6 pipelines in 4 repositories. If the table has fewer
than 10 real jobs on 9 October, change the October goal and tell the project owner.

### S1-10 — First real run end to end

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Backend + GCP job developer | S1-01, S1-02, S1-03, S1-04, S1-05, S1-06, S1-07, S1-11 | S1-07 (trace check tool) | S |

**What:** This is the Sprint 1 demo. One real GCP job does one real run. Show that the data
and the trace arrived. Use the S1-07 tool to show the result. Sprint 1 has no read API.
The read API for the dashboard comes in S2-07.

**Acceptance criteria**
- [ ] The source owner confirms that the run was a real published run.
- [ ] The `batch_runs` table has the run one time only.
- [ ] The job spans and the `monitor.ingest` span have the same trace ID in the Collector.
- [ ] The job's `batch.send` span is an ancestor of `monitor.ingest`.
- [ ] If records were sent, they contain placeholders and no raw PII.
- [ ] If security did not approve records yet, the run is in identity-only mode. The result says "records not yet approved".

**How to test**
1. Start the real run, or wait for the scheduled run.
2. Find the trace ID of the run in the job log.
3. Run `scripts/check_trace.py <trace_id>` on the test host. Make sure that all four items are "found".
4. Attach the output of the tool to this issue. Do not attach secrets or record text.

### S1-11 — Database accounts for the backend and the developers

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform + backend | S1-04 | S1-02, S1-07 | S |

**What:** Make database accounts in the Cloud SQL instance of the test host (S1-04). Use
Cloud SQL built-in users. Do not use one shared administrator account.

| Account | Type | Used by | Permissions |
|---|---|---|---|
| `monitor_app` | Bot | The backend service | Owns the monitor schema. Reads and writes the monitor tables. Runs the migrations when the backend starts, as the backend does now. |
| `monitor_readonly` | Bot | The S1-07 tool and other checks | Reads the monitor tables only |
| `dev_<name>` | Person, one for each developer | Developers | Read-only on the test host, because the test host has real redacted data. Full access only on the local stack. |
| `postgres` (the Cloud SQL administrator user) | Person | Platform only | For emergencies and for making the other accounts. The backend and the tools do not use it. |

Rules:
- Keep the passwords as host secrets. Do not put them in the repository or in chat.
- Cloud SQL has a private IP only and accepts only TLS (S1-04). Developers connect through IAP SSH to the VM (`gcloud compute ssh <vm> --tunnel-through-iap`), then use `psql` with `sslmode=verify-ca` to the Cloud SQL private IP. No Cloud SQL Auth Proxy is necessary.
- Remove a developer account when the person leaves the project.
- Langfuse gets its own database and account in its PostgreSQL container on the VM (S2-03). It does not use Cloud SQL.

**Acceptance criteria**
- [ ] Each account in the table exists in Cloud SQL, with the given permissions.
- [ ] The backend uses `monitor_app` in `DATABASE_URL`. It does not use the `postgres` user.
- [ ] A developer can connect through IAP SSH and the VM. A developer cannot reach the Cloud SQL instance from outside the VPC.
- [ ] This issue lists the accounts and their owners. It contains no passwords.

**How to test**
1. Start the backend with `monitor_app`. Make sure that the migrations run and the API stores a run.
2. Connect as `monitor_readonly`. Make sure that `SELECT` works and `INSERT` fails.
3. Connect as a `dev_<name>` account on the test host. Make sure that `INSERT` fails.
4. From a computer outside the VPC, try to connect to the Cloud SQL instance. Make sure that it cannot be reached (it has no public IP).
5. On the VM, connect with `sslmode=disable`. Make sure that Cloud SQL refuses the connection.

### S1-12 — Access to the company LiteLLM proxy for the judge

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Discovery | Backend + LiteLLM proxy owner | — | S2-09 | S |

**What:** The judge is a local model behind the company LiteLLM proxy (decided
2026-10-05). Another team owns the proxy. Get the answers below from the proxy owner, and
make sure that the test host can call the proxy. The due date is Friday 9 October, so that
S2-09 can start on Monday 12 October.

| Question | Why we need it |
|---|---|
| The URL of the proxy, for the test host (a VM in a GCP VPC) and for AWS | The network path and the firewall rules (S1-04, S4-01) |
| How does the GCP VPC reach the proxy: Interconnect, VPN, or a public endpoint through Cloud NAT? | The test host has no public IP. Its outbound traffic goes through Cloud NAT or a private link. |
| The model alias for the judge, and the model behind it: name, version, context length | The judge identity on each score. RAI accepts this model (S2-10). |
| Does the model support `response_format` with `type: json_schema`? | S2-09 asks for the four scores as JSON with a fixed schema |
| Does the model understand Thai well? | Many use cases are in Thai (S1-09) |
| One virtual key for each environment (test host, AWS), with a budget and a rate limit | A leaked key affects only one environment. The keys are host secrets. |
| The rate limit: requests and tokens for each minute | The setting `LLM_JUDGE_CONCURRENCY` (S2-09). Up to 10 use cases × 50 records arrive on the same night. |
| Does the proxy log the prompts and the answers? Where, and for how long? Does it send them to other tools, for example a Langfuse of the proxy team? | Security approval (S1-08). The prompts contain redacted record text. |
| Is the proxy certificate from a public CA or a private CA? | The setting `LLM_JUDGE_CA_FILE` (S2-09) |
| Does the proxy owner tell us before the model behind the alias changes? | A new model needs a new acceptance by RAI (S2-10) |
| Contact for an outage | The runbook for a judge outage (S4-05) |

**Acceptance criteria**
- [ ] Each question has an answer in this issue, or an owner and a date.
- [ ] The virtual key of the test host is a host secret. It is not in this issue, in chat or in git.
- [ ] The answer about the proxy logs goes to security for S1-08.
- [ ] From the test host, a call with synthetic text gets an answer in the requested JSON schema.

**How to test**
1. On the test host: `curl -H "Authorization: Bearer $LLM_JUDGE_API_KEY" https://<litellm-proxy>/v1/models`. Make sure that the list contains the judge alias. Use `--cacert` for a private CA.
2. On the test host: send one `POST /v1/chat/completions` request with synthetic text and the `json_schema` response format of S2-09. Make sure that the answer is a JSON object with the four fields.
3. Record the model name in the `model` field of the answer. Compare it with the answer of the proxy owner.

### S1-13 — Serve only the batch MVP API (prototype routes not mounted)

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S1-02, S1-05 | S1-06 (Compose smoke test), S1-04 | M |

**What:** The backend app serves only the batch MVP API. The prototype code stays in the repository until S4-07 removes it, but `main.py` does not mount it. There is no mode: a prototype route is not in the app, so it returns `404` (decided 2026-10-07).

Why now: in strict live mode, the backend is not "ready" without the prototype settings (`LIVE_*` producer URLs, `LIVE_TELEMETRY_TOKEN`, `LIVE_WORKER_TOKEN`, `ANTHROPIC_API_KEY`, the Langfuse keys). The batch MVP has none of them. Thus the test host (S1-04) health check would fail.

| Route | Served | Why |
|---|---|---|
| `POST /api/batch/runs` | Yes | The batch receiver (S1-02, S1-05) |
| `GET /api/health`, `GET /api/healthz` | Yes | Front door and Compose health checks |
| `GET /api/readiness` | Yes | Checks only the batch settings |
| `GET /api/version` | Yes | `build_sha` only, no producer SHA |
| Demo routes (`/api/scenario`, `/api/sim`, `/api/registry`, `/api/board`, ...) | No (`404`) | Prototype only (S4-07 removes the code) |
| Prototype live routes (`/api/live/*`), including `poll`, `skip` and `reset-ack` | No (`404`) | Prototype pull lane |

Other changes:
- The prototype poller does not start.
- `CONTROL_TOWER_MODE` is not used by `main.py`. The strict-live route middleware is removed, because routes that are not mounted need no blocking.
- Readiness does not check the `LIVE_*` settings, `ANTHROPIC_API_KEY` (the judge is the local model through LiteLLM, S2-09) or the Langfuse keys (S2-02 and S2-09 add their own checks).
- Tests of the prototype code build a test app that mounts the prototype router directly. The prototype code keeps its tests until S4-07.

Accepted effects: the current dashboard cannot load `/api/live/*` data until S2-07. The Replit prototype stops working if it is redeployed from `dev` (Replit is not a release target, #42).

**Acceptance criteria**
- [ ] `POST /api/batch/runs`, `/api/health`, `/api/healthz`, `/api/readiness` and `/api/version` work with only `DATABASE_URL` and `BATCH_API_KEY_SHA256` set.
- [ ] Every demo and prototype route returns `404`, with any value of `CONTROL_TOWER_MODE`.
- [ ] The prototype poller does not start.
- [ ] Readiness reports only batch settings. No `LIVE_*`, Anthropic or Langfuse setting is required.
- [ ] The prototype tests still pass with their own test app.
- [ ] `CLAUDE.md`, `README.md` and `docs/STRICT-LIVE.md` say that only the batch API is served.

**How to test**
1. Unit: a route table test lists every served path. Any other path returns `404`.
2. Start the backend with only `DATABASE_URL` and `BATCH_API_KEY_SHA256`. Make sure that `/api/readiness` is `200` and a batch run is stored.
3. Full backend suite.
4. Paired with S1-06: the Compose smoke test uses this app.

---

## Sprint 2 — Oct 12–16: same path for many jobs, plus evaluation and tracing

**Sprint 2 prerequisites (answers from 2026-10-03; confirm after S1-04 is complete)**

| Question | Answer | Effect |
|---|---|---|
| Is the test host large enough for Langfuse? | S1-04 makes the VM with the recommended size below | See the server size below |
| How do the engineers and the RAI team open the dashboard and Langfuse? | The test host is a VM in GCP with no public IP (S1-04). The staff use the company network path to the GCP VPC (VPN or Interconnect), and the private DNS name of the VM. | See the ports below. The private CA certificate contains the private DNS name. Set the Langfuse URL setting to this name. SSO (S3-07) uses the same name. |
| Can the test host call the company LiteLLM proxy? | Answer from S1-12 | The judge is a local model behind the proxy (S2-09). There is no second judge provider. RAI accepts the judge before its scores count for the release (S2-10). |

Server size for the test host:

| Item | Minimum | Recommended | Reason |
|---|---|---|---|
| CPU | 6 vCPU | 8 vCPU | Langfuse alone needs at least 4 cores (Langfuse self-hosting guide). The monitor backend, the Langfuse PostgreSQL container and the Collector need more. The monitor database is in Cloud SQL, not on the VM (S1-04). |
| Memory | 24 GiB | 32 GiB | Langfuse alone needs at least 16 GiB. The monitor backend loads pandas, Evidently and NannyML. |
| Disk | 150 GiB SSD | 200 GiB SSD | Langfuse recommends 100 GiB for its data. The monitor database, the logs and the Docker images need more. |
| Operating system | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS | Docker Engine and Docker Compose v2 |
| GCP machine type | `e2-standard-4` is too small for all services | `e2-standard-8` (8 vCPU, 32 GiB), used in S1-04 | — |

Ports on the test host (VPC firewall rules, S1-04):

| Port | Service | Who connects | Allowed sources |
|---|---|---|---|
| 443 | Front door: `/api/batch/runs`, `/api/health` and `/otlp/*` | GCP jobs | The network ranges of the GCP jobs |
| 8443 | Monitor dashboard | RAI team, engineers | The staff network ranges. From S3-07, also Google SSO. |
| 3443 | Langfuse UI | Engineers only | The staff network ranges. From S3-07, also Google SSO, with no password login. |
| 22 | SSH | Platform, developers | IAP only (`35.235.240.0/20`) |
| None | Langfuse PostgreSQL, ClickHouse, Redis, MinIO (on the VM) | — | Closed. Developers use IAP SSH (S1-11). |
| 5432 on the Cloud SQL private IP | Monitor database (Cloud SQL) | The backend and developers, from the VM | Private IP only, TLS only (S1-04, S1-11) |

Langfuse uses its own port because it does not work easily under a URL path.

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S2-04 GCP OTel helper | S2-03 Collector → Langfuse | The job's spans flow through the Collector into Langfuse, and the run summary lands in monitor Postgres, all with one trace ID | Local stack, then test host |
| S2-05 batch evaluator | S2-03 Collector → Langfuse | The run scores and the record scores appear on the run's trace in Langfuse | Local stack |
| S2-01 registry | S2-06 onboarding | Each real job can write only its own use case | Test host |
| S2-09 LiteLLM judge | S2-05 batch evaluator | A stored run is scored through the LiteLLM proxy, and each score has the judge identity | Local stack (fake LiteLLM server), then test host |
| S2-10 judge acceptance | S2-09 on the test host | The local judge agrees with the RAI labels within the agreed limits | Test host |

### S2-01 — Source registry: YAML settings and API key hashes

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend + platform | S1-02, S1-11 | S2-06 | M |

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

**OTLP token:** All GCP jobs use one OTLP token (S1-06). The Collector cannot connect a
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
3. Paired with S2-06: each onboarded job sends with its own key and the request is accepted. Change the key of one job to the key of another use case. Make sure that the request is rejected.

### S2-02 — Langfuse SDK v4 in the backend, and package approval

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Decision + Feature | Backend + project owner | S1-05 | S2-05 | M |

**Decision (2026-10-03):** Use the Langfuse Python SDK v4 (`langfuse` 4.x) in the backend.
The backend uses it for these items:
- The `monitor.evaluate` span. This span can contain the redacted record text that the API accepted.
- The scores, with `create_score`.

The GCP jobs do not use the Langfuse SDK. They use the OTel SDK and send their spans to the
Collector (S1-05, S1-06). Thus the Langfuse keys stay in AWS.

**Facts that affect this issue**

| Fact | Effect |
|---|---|
| SDK v4 does not have the v2 functions `trace()` and `score()`. The chatbot store (`backend/app/adapters/llm_eval/stores.py`) uses these functions. | The class `LangfuseCloudStore` is prototype-only code. Remove it in the same pull request, and make the chatbot use only its local store. Do not change it to v4. |
| SDK v4 needs `opentelemetry-api`, `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http`, version 1.45 or later. | S1-05 part B must use the same OTel versions. |
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

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | S1-06, S1-11, Sprint 2 prerequisites | S2-04, S2-05 | L |

**What:** Add self-hosted Langfuse to Docker Compose: Langfuse web, Langfuse worker,
PostgreSQL, ClickHouse, Redis and S3 storage (MinIO). Use the versions in the
fixed-versions table. Add an `otlphttp` exporter to the Collector. This exporter sends the
GCP spans to the Langfuse OTLP endpoint (`/api/public/otel`) with the Langfuse project keys.

**Prerequisites (answer after S1-04 is complete)**

| Question | Owner |
|---|---|
| Is the test host VM large enough for Langfuse (CPU, memory, disk)? S1-04 uses `e2-standard-8` and 200 GiB. Examine the Langfuse self-hosting requirements. | Platform |
| Do the engineers reach port 3443 through the company network path to the VPC? If not, use an IAP tunnel: `gcloud compute start-iap-tunnel <vm> 3443`. | Network team |

**Rules**
- Langfuse uses its own PostgreSQL container (`postgres:17.11-bookworm`) and account on the VM (decided 2026-10-06). It does not use the Cloud SQL monitor database (S1-04, S1-11).
- Turn off public sign-up in Langfuse. Make one account for each engineer. Langfuse is for engineers. The RAI team uses the dashboard.
- Use the company Google email of each engineer for the account. Then S3-07 can link the account to SSO and keep its project role.
- The Collector exporter sends the header `x-langfuse-ingestion-version: 4`. Without this header, new data can appear in Langfuse up to 10 minutes late.
- Set the retention period in Langfuse from S1-08.
- Keep the Langfuse keys as host secrets. Do not put them in files in git.
- When this issue works, delete the Sprint 1 file output on the test host (S1-06).

**Change to S1-07:** The trace check tool reads Langfuse through the Observations API v2.
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
4. Paired with S2-04 and S2-05: see the test steps in those issues.

### S2-04 — OTel helper file for the GCP jobs

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | GCP job developer; backend reviews | S1-05 | S2-03 | M |

**What:** Move the OTel code from S1-05 part A into one reusable Python file,
`otel_helper.py`. Add the token data and the attribute allowlist. Use the file in the first
job. The other jobs get the file in S2-06, S3-01 and S4-03. Each job repository copies the
file, because we have no package registry.

| Function | Detail |
|---|---|
| Run trace | The root span `batch.run` and the step spans, as in S1-05 |
| Token totals, Batch API jobs | Attributes on the `batch.harvest` span: model, input tokens, output tokens |
| Token data, online jobs | One span for each sampled request only, with model, tokens and the real call time. The totals go on `batch.run`. Select the sample before the calls start, so the same requests get spans and become records. |
| Attribute names | The OTel GenAI names: `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` |
| Attribute allowlist | Only the allowed keys go into a span. The helper drops other keys and logs only the key name. GCP spans contain no text. |
| Export | OTLP/HTTP to the front door (`/otlp/*`) with the OTLP token. If the export fails, the job continues. |

**Acceptance criteria**
- [ ] One trace for each run, with the step spans from S1-05.
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

### S2-05 — Batch evaluator with the five LLM metrics

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend + RAI | S2-01, S2-02, S2-03, S2-09, task description (Wed 14 October) | S2-03 | L |

**What:** Grade each stored run with the LLM lane of the prototype. Map the records to the
v1.1 `Trace` shape. Use the judge client of S2-09 (the company LiteLLM proxy) and the
aggregation in `backend/app/adapters/llm_eval/live_http.py`. Grade with
`backend/app/engines/health.py`.
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
| The redacted text of each judged record | Already in the stored run (S1-02) | Input and output of the record observation, under `monitor.evaluate` |

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

The only provider is the local model behind the company LiteLLM proxy (S2-09). The Anthropic
API is not used. The settings are `LLM_JUDGE_BASE_URL`, `LLM_JUDGE_API_KEY` (a host secret)
and `LLM_JUDGE_MODEL` (the alias on the proxy). RAI accepts the judge before its scores
count for the release (S2-10).

Each score records the judge identity from S2-09. The offline heuristic judge is never used
in strict live mode.

**When a metric is "Unknown"**

| Condition | Reason |
|---|---|
| Identity-only run (`records: []`) | `records_not_approved` |
| Fewer than 8 records | `insufficient_sample` |
| The judge fails 3 times: no answer, an error, or an answer that does not agree with the score schema (S2-09). After each failure, the worker tries again in the next cycle. | `judge_failed` |
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

### S2-06 — Onboard 4 use cases

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Job developers + backend + platform | S1-09, S2-01, S2-04 | S2-01, S1-07 | L |

**What:** Add the send step (S1-03) and the OTel helper file (S2-04) to 4 different jobs.
Include one job with a different output shape. Use the order and the developers in the
S1-09 table.

For each job, do these steps:
1. Add the use case to the YAML registry (S2-01) in a pull request. Set `mode: identity_only`.
2. Platform makes the API key with `scripts/batch_keys.py` and puts it into the GCP Secret Manager of that project.
3. Platform gives the job a private path to the test host: VPC access for the job runtime, and its network range in the firewall rule (S1-04). Record the egress IP of the job for AWS (S4-01).
4. The job developer maps the job to the record fields of the [standard](llm-metrics-standard.md), as in S1-01.
5. The job developer adds the send step and the helper file. The job uses the shared OTLP token. It needs no Langfuse key.
6. Run the job. If the job does not run between 12 and 16 October, use a controlled rerun.
7. After S1-08 approves the records, change `mode` to `records` and set `SEND_RECORDS` to on.

**Acceptance criteria**
- [ ] 4 real runs arrive. The owner of each use case confirms that the run is real.
- [ ] Each use case has its own API key and one trace for each run.
- [ ] Each use case has an approved task description and its five metrics graded, or "Unknown" with a reason.
- [ ] Test files or configuration entries do not count as a live use case.

**How to test**
1. For each job: run `scripts/check_trace.py <trace_id>`. Make sure that all the items are "found".
2. For each job: examine one stored run. Make sure that the records agree with the schema and contain placeholders, not raw PII.
3. Record the 4 trace IDs and their five metric values in this issue.

### S2-07 — Dashboard shows the GCP use cases with the current UI

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S2-01, S2-05 | S2-06 | M |

**Decision (2026-10-03):** The dashboard shows only the GCP batch use cases. The UI does not
change. The dashboard shows no record text.

**What:** The frontend reads only two endpoints: `GET /api/live/portfolio` and
`GET /api/live/use-case/{id}`. It does not contain fixed use-case IDs. Thus the backend
returns the GCP use cases through these two endpoints, in the same shape that the LLM lane
of the chatbot uses now. The frontend code does not change.

| UI field | Source for a GCP use case |
|---|---|
| Name and owner | YAML registry (S2-01) |
| Five LLM signals, lanes and grade | `batch_evaluations` (S2-05) |
| Freshness | `completed_at` of the latest run |
| `judge` | The judge identity from S2-09, for example `litellm/<alias> (<model>)` |
| `judge_sample` | Always empty. No record text goes to the browser. |
| Errors and "Unknown" reasons | The reasons from S2-05 |

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
4. Paired with S2-06: open the dashboard on port 8443. Make sure that the onboarded use cases show the correct freshness and grades.

### S2-08 — One run as a single trace, GCP job to score

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Backend + platform | S2-03, S2-04, S2-05, S2-07 | S1-07 | S |

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

### S2-09 — Judge through the company LiteLLM proxy

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | To build: none (use a fake server). To test on the test host: S1-12. | S2-05 | M |

**What:** Replace the Claude call in `backend/app/adapters/llm_eval/live_http.py`
(`_judge_claude`, which uses `anthropic.Anthropic().messages.parse`) with a call to the
OpenAI-compatible endpoint of the company LiteLLM proxy. Use `httpx`. It is already in
`backend/requirements.txt`, so no new package is necessary. Remove the `anthropic` package.
The five metrics, the bands and the aggregation do not change. The judge is shared code:
the batch evaluator (S2-05) and the chatbot lane use it.

**Settings**

| Setting | Meaning | Rule |
|---|---|---|
| `LLM_JUDGE_BASE_URL` | The URL of the proxy, for example `https://<litellm-proxy>` | Required in strict live mode |
| `LLM_JUDGE_API_KEY` | The LiteLLM virtual key of this environment (S1-12) | Required in strict live mode. A host secret. Never in a log. |
| `LLM_JUDGE_MODEL` | The model alias on the proxy. No default value. | Required in strict live mode |
| `LLM_JUDGE_CA_FILE` | The CA file for a private proxy certificate | Optional. The certificate verification is never turned off. |
| `LLM_JUDGE_TIMEOUT_S` | The time limit of one call. Default `60`. | — |
| `LLM_JUDGE_CONCURRENCY` | The maximum number of calls at the same time. Default `4`. | Set it from the rate limit in S1-12 |
| `ANTHROPIC_API_KEY` | Removed | — |

**The call for each record**

```
POST {LLM_JUDGE_BASE_URL}/v1/chat/completions
Authorization: Bearer {LLM_JUDGE_API_KEY}

{
  "model": "{LLM_JUDGE_MODEL}",
  "temperature": 0,
  "max_tokens": 256,
  "messages": [
    {"role": "system", "content": "<judge prompt with the task description>"},
    {"role": "user", "content": "Question: ...\n\nSource material:\n...\n\nAnswer: ..."}
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "record_score",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "groundedness":  {"type": "number", "minimum": 0, "maximum": 1},
          "relevance":     {"type": "number", "minimum": 0, "maximum": 1},
          "hallucination": {"type": "boolean"},
          "pii":           {"type": "boolean"}
        },
        "required": ["groundedness", "relevance", "hallucination", "pii"],
        "additionalProperties": false
      }
    }
  }
}
```

The judge prompt keeps the four definitions of the current Claude prompt. It uses the task
description that the caller gives (S2-05). The chatbot lane gives its current text, "a
telecom support chatbot". The prompt also tells the judge: "The text can be Thai, English or
mixed. Score the meaning, not the language."

**The answer**
1. Read `choices[0].message.content`. Accept one JSON object. Accept also one JSON object inside one Markdown code fence. Refuse all other text.
2. Examine the object with a Pydantic model: `groundedness` and `relevance` from 0 to 1, `hallucination` and `pii` true or false, no other fields. Do not trust the proxy to apply the schema.
3. The judge identity is `litellm/<LLM_JUDGE_MODEL> (<model>)`, where `<model>` is the `model` field of the answer. Store it with each score.

**Failures**

| Event | Action |
|---|---|
| Timeout, network error, `429` or `5xx` | Try again in the same cycle, up to 3 attempts in total, with a delay of 1 s and then 4 s |
| An answer that is not valid (step 1 or 2) | The same as a `5xx` |
| `400`, `401`, `403` or `404` | Do not try again. Log the status. |
| A record still fails after 3 attempts | The evaluation of the run fails in this cycle. S2-05 tries again in the next cycle, and gives `judge_failed` after 3 cycles. |
| Strict live mode | Never use the heuristic judge. Demo mode keeps the heuristic judge without changes. |

A log entry contains the record ID, the HTTP status or the error type, and the attempt
number. It never contains the key, the prompt or the answer text.

**Files**

| File | Change |
|---|---|
| `backend/app/adapters/llm_eval/litellm_judge.py` | New. `judge_records(traces: list[dict], *, model: str, task_description: str) -> tuple[list[dict], str]` returns the scores in the order of the traces, and the judge identity. `parse_score(content: str) -> dict` examines one answer. `class JudgeError(Exception)`. |
| `backend/app/adapters/llm_eval/live_http.py` | Remove `_judge_claude` and `import anthropic`. Call `judge_records`. Change each `config.ANTHROPIC_API_KEY` test to `config.llm_judge_configured()`. |
| `backend/app/config.py` | The new settings, `llm_judge_configured() -> bool`, and the strict live errors for each missing setting |
| `backend/app/main.py` | `judge_ok` uses `config.llm_judge_configured()` |
| `backend/app/scenario/live_runner.py` | The judge identity from `judge_records` |
| `backend/requirements.txt` | Remove `anthropic>=0.40,<1` |
| `backend/tests/test_litellm_judge.py` | New. A fake proxy with `httpx.MockTransport`. |
| The tests that set `ANTHROPIC_API_KEY` or replace `_judge_claude`: `test_alert_routes.py`, `test_contract_strictness.py`, `test_live_judge_strict.py`, `test_operator_routes.py`, `test_poller_metrics.py`, `test_realized_view.py`, `test_strict_live_mode.py` | Use the new settings, and replace `judge_records` |
| `.env.example`, `docs/STRICT-LIVE.md`, `.github/workflows/backend-live.yml` | The new setting names. CI uses a fake value, never a real key. |

**Acceptance criteria**
- [ ] With a fake proxy: a valid answer gives the four results. The request has the bearer key, the model alias, `temperature: 0` and the `json_schema` response format.
- [ ] `groundedness: 1.4`, a missing field, an extra field and plain text are each refused with `JudgeError`. No score is stored.
- [ ] `429`, `503` and a timeout are tried again, with at most 3 attempts. `401` is not tried again.
- [ ] The fake proxy never has more calls at the same time than `LLM_JUDGE_CONCURRENCY`.
- [ ] In strict live mode, each missing setting gives a startup error with its name. The heuristic judge is never used.
- [ ] Each score stores the judge identity with the alias and the `model` field of the answer.
- [ ] No log entry contains the key, the prompt or the answer text.
- [ ] `anthropic` is not in `backend/requirements.txt`. A search for `ANTHROPIC_API_KEY` finds it only in `CHANGELOG.md` and in old `changes/` folders.
- [ ] The chatbot (`AICT-L02`) tests pass.

**How to test**
1. Unit: `.venv/bin/python -m pytest -q tests/test_litellm_judge.py`. One test for each acceptance criterion above, with `httpx.MockTransport` and `caplog`.
2. Full backend suite: `.venv/bin/python -m pytest -q -m "not slow"`.
3. Paired with S2-05 on the local stack: point `LLM_JUDGE_BASE_URL` to a fake proxy that returns fixed scores. Store one run, and let the worker evaluate it. Make sure that the scores and the judge identity are in `batch_evaluations` and in Langfuse.
4. On the test host (after S1-12): run `backend/scripts/judge_check.py --smoke`. It judges 3 synthetic records (Thai, English, a refusal) and shows the scores and the judge identity.

### S2-10 — RAI accepts the local judge

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | RAI + backend | S1-12, S2-09 | S2-09 on the test host | M |

**What:** There are no Claude scores to compare with. Thus RAI compares the local judge
with labels from people. The due date is Friday 16 October. A use case passes the release
only with a judge that RAI accepted (S4-03).

1. **Reference set.** RAI makes a set of at least 60 records in the language mix of S1-09: at least 20 Thai, at least 20 English, and some mixed. The set contains correct answers, refusals, answers with hallucinations, off-topic answers, and answers with placeholders (`[PHONE]`). Synthetic records go in the repository, in `backend/tests/fixtures/judge_reference/`. Redacted real records (after S1-08) stay on the test host and never go into git.
2. **Labels.** Two RAI reviewers label each record for the four results, separately. They agree on a final label for each difference.
3. **Limits first.** RAI writes the acceptance limits in this issue before the first run. Proposed limits: at least 85% agreement for `hallucination` and for "groundedness ≥ 0.70" and "relevance ≥ 0.70", and no missed `pii` case.
4. **Run.** Backend adds `backend/scripts/judge_check.py --set <folder>`. It judges the set two times, through S2-09, and reports the agreement for each result, each missed `pii` case, and the records that got different results in the two runs. The report contains record IDs only, no record text.
5. **Decision.** RAI accepts or rejects the judge identity (alias and model) and the prompt version. If RAI rejects, the backend changes the prompt (a new prompt version) or asks the proxy owner for a different model. Then run the set again.

**Acceptance criteria**
- [ ] The limits are in this issue before the first run.
- [ ] The reference set has at least 60 labelled records, with the language mix of S1-09.
- [ ] The report of the two runs is attached. It contains no record text.
- [ ] The decision is in this issue: the accepted judge identity, the prompt version, the name of the RAI reviewer and the date. Or the rejection, with the next step and an owner.
- [ ] `llm-metrics-standard.md` records the accepted judge identity and prompt version.

**How to test**
1. Run `backend/scripts/judge_check.py --set backend/tests/fixtures/judge_reference/` on the test host two times. Make sure that the results agree with the limits.
2. Unit: test the agreement calculation of `judge_check.py` with a fake judge and a set of 4 records with known results.

### S2-11 — Threat model for the batch MVP (R2)

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Decision | Backend + security | — | S2-05 | S |

**What:** The batch MVP is risk tier R2 (decided 2026-10-07,
[intent](intent.md), [ADR 0002](../../docs/adr/0002-batch-push-ingest.md)). The playbook
requires a threat model and abuse cases for R2. A short, proportionate threat model is
enough. Write it before real records reach the judge (S2-05). The due date is Wednesday
14 October.

Write `changes/2026-10-02-batch-monitoring-mvp/threat-model.md`. For each threat: what
can happen, the effect, the control that exists, the gap, and an owner. Cover at least:

| Threat | Where |
|---|---|
| Prompt injection: text in a record tries to change the judge's scores or its output format | S2-05, S2-09 |
| A stolen or leaked API key writes false runs for one use case | S1-02, S2-01 |
| A replay or a resend of an old run | S1-02 (duplicate and conflict), S1-05 (`stored_trace_id`) |
| PII that the redaction misses (for example names) reaches the monitor, the judge or Langfuse | S1-03, S1-08, S3-05 |
| A large or malformed body, or many requests (denial of service) | S1-02 (size limit), S1-06 (front door) |
| The OTLP endpoint is used to send false spans | S1-06 (OTLP token) |
| A secret (API key, judge key, Langfuse keys, database password) in logs, spans or git | S1-02, S1-05, S3-05 |
| One wrong grade affects many use cases (a judge or prompt change) | S2-10 |

**Acceptance criteria**
- [ ] `threat-model.md` covers each threat in the table, with the control, the gap and an owner.
- [ ] Each gap is accepted in writing, or it has an issue and a date.
- [ ] Security reads the threat model. Their comments are in this issue.

**How to test**
1. Compare `threat-model.md` with the table. Make sure that no row is missing.
2. For each "control exists" claim, link the test or the setting that proves it.

---

## Sprint 3 — Oct 19–23: scale to 8 and harden

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S3-03 Collector hardening | S3-04 drills | Spans survive a Langfuse outage and arrive after recovery, once | Local stack |
| S3-03 Collector hardening | S3-05 leak scan | Forbidden attributes are removed before storage | Local stack, test host |
| S3-02 missed-run alert | S3-04 drills | A run that never arrives raises a delivery alert, not a quality alert | Local stack |
| S3-07 SSO | S3-05 security review | Only the staff on the allowlist open the dashboard. Langfuse has no password login. Nobody reads the dashboard API around the SSO. | Local stack (mock OIDC server), then test host |
| S3-07 SSO | S3-04 drills | An SSO outage stops the logins, but not the ingest or the evaluation | Test host |

### S3-01 — Onboard 8 use cases, including split submit and harvest

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Job developers + backend + platform | S2-04, S2-06 | S1-07 | L |

**What:** Onboard 4 more use cases, to a total of 8. Use the seven steps in S2-06 for each
job. Include the difficult jobs from the S1-09 table.

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

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S2-01, S1-02 | S3-04 | M |

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

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | S1-06, S2-03 | S3-04, S3-05 | M |

**What:** Make the Collector safe and reliable before AWS. S1-06 already added the token,
HTTPS through the front door and the network rules. This issue does not repeat them.

| Addition | Why |
|---|---|
| Attribute filter in the Collector | The helper file removes attributes in the GCP job (S2-04). The Collector filter is a second protection, for example for a job that uses an old helper file. Use the same allowlist. |
| Memory limit | A large burst of spans cannot stop the Collector |
| Disk queue for the Langfuse exporter | If Langfuse is down, or the Collector restarts, the spans wait on disk and are not lost |

The API keeps the API key in October. We do not change to a Google identity token, unless
security requires it in S1-08.

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

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Backend + platform | S2-05, S2-09, S3-02, S3-03, S3-07 | S1-07 | M |

**What:** Stop each part of the system on purpose. Make sure that no data is lost and
nothing is duplicated. Do the drills on the test host.

| Drill | Expected result |
|---|---|
| The monitor is down while a job sends | The job tries again and logs each failure. After recovery, the run is stored one time. |
| The Collector is down | The run summary is still stored. The spans arrive later from the disk queue (S3-03). |
| Langfuse is down | The spans wait in the Collector. The backend tries the scores again. After recovery, each score is in Langfuse one time. |
| The judge is down (the LiteLLM proxy or the model behind it) | The worker tries again in the next cycles, up to 3 times (S2-05). If the judge comes back, the run gets normal scores. If not, the metrics are "Unknown" with `judge_failed`. |
| The LiteLLM proxy returns `429` for many calls (8 runs arrive together) | The backend sends no more than `LLM_JUDGE_CONCURRENCY` calls at the same time and tries again after `429` (S2-09). All the runs get scores, or "Unknown" with `judge_failed`. |
| Google SSO is down | Nobody can log in to the dashboard or Langfuse. The ingest, the evaluation and the alerts continue. After recovery, the login works. No run is lost. |
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

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Security + platform + source owners | S3-01, S3-03, S3-07 | S3-03, S3-07 | M |

**What:** A script searches the stored data for items that must not be there. Security also
examines the access.

| Location | Allowed | Not allowed |
|---|---|---|
| `batch_runs` and `batch_record_judgments` | Redacted text with placeholders | Raw phone numbers, emails, national IDs |
| GCP spans in Langfuse | Names, times, counts, IDs | Any text |
| `monitor.evaluate` in Langfuse | Redacted record text | Raw PII |
| Dashboard and API responses | Metrics and reasons | Any record text |
| Logs | IDs, errors, and the email of a person who logs in | Keys, tokens, OAuth client secrets, session cookies, record text |
| LiteLLM proxy logs (the proxy owner examines them) | What security approved in S1-08 | Record text kept longer than the approved period |

Security also examines these items:
- The database accounts (S1-11).
- The SSO (S3-07): a person who is not on the allowlist cannot open the dashboard. Langfuse has no password login. A company account that is not a project member sees no project. Port 443 gives `404` for `/api/live/*`.
- The Langfuse accounts. They are for engineers only.
- One key rotation (S2-01).
- A request without a key or a token is refused, on the API and on the Collector.
- The test host VM has no external IP. The VPC firewall rules allow only the ranges in S1-04. The VM uses its own service account, not the default one.
- The retention periods in the monitor database and in Langfuse (S1-08).

**Acceptance criteria**
- [ ] The leak scan finds nothing in the "Not allowed" column.
- [ ] Each access item in the list passes.
- [ ] Each exception is written down, with an owner and a date.

**How to test**
1. Run the leak scan script on a sample of each location. The script searches for phone numbers, email addresses, national ID numbers, token formats and record text in the wrong locations.
2. Send a request without a key to the API, and spans without a token to the Collector. Make sure that both are refused.

### S3-06 — Kubernetes deployment files: Langfuse Helm chart and our manifests

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | S3-03, S3-07 | S4-01 | L |

**What:** Prepare the files that install the stack on Kubernetes. Install them on the
**test AWS Kubernetes cluster** in Sprint 3, so that Sprint 4 repeats a known installation
on the production cluster. Use the versions in the fixed-versions table.

**Decisions (2026-10-04)**

| Part | Plan A (selected) | Plan B (fallback) |
|---|---|---|
| PostgreSQL 17 (monitor and Langfuse) | Amazon RDS for PostgreSQL 17: one instance for the monitor and one for Langfuse | Containers in the cluster, with our backups |
| S3 storage for Langfuse | Amazon S3 | MinIO container in the cluster |
| Langfuse, ClickHouse, Redis | Official Langfuse Helm chart | Official Langfuse Helm chart |
| Monitor backend, Collector, front door, OAuth2 Proxy (S3-07) | Our own manifests | Our own manifests |
| Langfuse SSO (S3-07) | SSO settings in the Helm values file. The client secret comes from the Kubernetes secret store. | The same |

Send the RDS and S3 request in Sprint 1 (long-lead requests). If the request is not
approved by **Wednesday 21 October**, use plan B. Write the deployment files so that a
values file selects plan A or plan B.

**The first test of the internet path.** The test host is in GCP, on a private path
(S1-04). Thus Sprints 1 and 2 do not test the path that production uses: from a GCP job,
through its Cloud NAT egress IP, across the internet, to AWS. Test this path here, on the
test AWS cluster, before Sprint 4.

**Acceptance criteria**
- [ ] The answer to the RDS and S3 request (sent in Sprint 1), or plan B, is recorded by 21 October.
- [ ] The Langfuse Helm chart uses version 2.1.3 and the Langfuse image tag 4.50.0.
- [ ] Our manifests for the monitor backend, the Collector and the front door pass validation (`kubeconform`, or `kubectl apply --dry-run=server`).
- [ ] Secrets come from the Kubernetes secret store. No secret is in the files. This includes `LLM_JUDGE_API_KEY`, the OAuth client secrets and the OAuth2 Proxy cookie secret.
- [ ] Each service has health checks, resource limits and a rollback step.
- [ ] Backup, restore and rollback steps are written. For plan A, they use the RDS backups.
- [ ] The stack runs on the test AWS Kubernetes cluster, and the smoke test passes.
- [ ] A job runtime in the GCP dev project sends one example run and spans to the test AWS cluster, through its Cloud NAT egress IP. The AWS security rules allow that IP only. A request from another IP is refused.

**How to test**
1. Validate all the files.
2. Install the stack on the test AWS Kubernetes cluster. Send one example run and spans from the job runtime in the GCP dev project, through Cloud NAT. Run `scripts/check_trace.py`, and make sure that all the items are "found".
3. If the test cluster is not available by 19 October, install the stack on a disposable local cluster (for example kind) with plan B, and record that the AWS test was not done.

### S3-07 — SSO login for the dashboard and Langfuse (Google now, Entra ID later)

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform; backend reviews | S1-06, S2-03, S2-07, long-lead requests: DNS name for the test host and Google OAuth clients | S3-05, S3-04 | M |

**What:** The staff log in with their company Google Workspace account. Later, the company
changes to Microsoft Entra ID. Thus the identity provider is a setting only, and a runbook
describes the change. The VPC firewall rules for the staff network ranges stay as a second
protection. The test host uses its private DNS name (S1-04). Google accepts a private name
under a company domain, because the browser follows the redirect inside the company
network.

| Part | How | Code change |
|---|---|---|
| Dashboard (port 8443) | OAuth2 Proxy (fixed versions table) in front of the dashboard and its API. Provider `google`. Only the emails in the allowlist file can enter. | None. The frontend files do not change. The backend port stays private. |
| Langfuse (port 3443) | The built-in SSO of Langfuse, with Google. Password login is off. | None. Settings only. |
| GCP paths on port 443 | No change: the API key and the OTLP token. Never SSO. | None |

**Who can enter**

| Group | Dashboard | Langfuse |
|---|---|---|
| RAI team | Yes, if the email is on the allowlist | No. They are not project members. |
| Engineers | Yes, if the email is on the allowlist | Yes, as project members |
| Other company accounts | No (`403`) | They can log in, but they see no project |
| Accounts outside the company | No | No |

The allowlist file is a host file (a ConfigMap on Kubernetes), not a file in git. Platform
changes it. The RAI lead approves each person who is added. Record each change in this issue.

**OAuth2 Proxy settings (test host)**

```
OAUTH2_PROXY_PROVIDER=google
OAUTH2_PROXY_CLIENT_ID=<dashboard OAuth client>          # host secret
OAUTH2_PROXY_CLIENT_SECRET=<dashboard OAuth secret>      # host secret
OAUTH2_PROXY_COOKIE_SECRET=<32 random bytes>             # host secret
OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE=/etc/oauth2-proxy/emails.txt
OAUTH2_PROXY_REDIRECT_URL=https://<test-host-dns>:8443/oauth2/callback
OAUTH2_PROXY_UPSTREAMS=http://<dashboard service>/
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_COOKIE_SAMESITE=lax
OAUTH2_PROXY_COOKIE_EXPIRE=8h
OAUTH2_PROXY_COOKIE_REFRESH=1h
OAUTH2_PROXY_REVERSE_PROXY=true
OAUTH2_PROXY_SKIP_PROVIDER_BUTTON=true
```

Do not set `OAUTH2_PROXY_EMAIL_DOMAINS` to the company domain. Then each company account
could enter. Do not add routes that skip the login. The health check uses `/ping` of OAuth2
Proxy.

**Langfuse settings (test host)**

```
NEXTAUTH_URL=https://<test-host-dns>:3443
AUTH_GOOGLE_CLIENT_ID=<Langfuse OAuth client>            # host secret
AUTH_GOOGLE_CLIENT_SECRET=<Langfuse OAuth secret>        # host secret
AUTH_GOOGLE_ALLOWED_DOMAINS=<company domain>
AUTH_GOOGLE_ALLOW_ACCOUNT_LINKING=true
AUTH_DISABLE_USERNAME_PASSWORD=true
```

**Order of the steps (so that nobody is locked out)**
1. Register the redirect URIs in the two Google OAuth clients: `https://<test-host-dns>:8443/oauth2/callback` and `https://<test-host-dns>:3443/api/auth/callback/google`.
2. Turn on Google login in Langfuse, with password login still on. Make sure that the engineer with the owner role logs in with Google and keeps the owner role (account linking by email, S2-03).
3. Then set `AUTH_DISABLE_USERNAME_PASSWORD=true`.
4. Put OAuth2 Proxy in front of the dashboard. Keep the firewall rules for the staff network ranges.

**Local stack and CI.** Use the mock OIDC server (fixed versions table) as the identity
provider: OAuth2 Proxy with `OAUTH2_PROXY_PROVIDER=oidc` and
`OAUTH2_PROXY_OIDC_ISSUER_URL=http://mock-oidc:8080/default`, and Langfuse with the
`AUTH_CUSTOM_*` settings. The browser and the containers must use the same host name for the
issuer. For example, add `mock-oidc` to the hosts file of the laptop. This setup also proves
that a change of provider is a change of settings only.

**Change to Microsoft Entra ID (later)**

Write the runbook `docs/runbooks/sso-entra-id.md`:

| Part | Change |
|---|---|
| OAuth2 Proxy | `OAUTH2_PROXY_PROVIDER=entra-id`, `OAUTH2_PROXY_OIDC_ISSUER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0`, a new client ID and secret from an Entra app registration with the same redirect URI |
| Langfuse | Remove the `AUTH_GOOGLE_*` settings. Add `AUTH_AZURE_AD_CLIENT_ID`, `AUTH_AZURE_AD_CLIENT_SECRET`, `AUTH_AZURE_AD_TENANT_ID` and `AUTH_AZURE_AD_ALLOW_ACCOUNT_LINKING=true`. |
| Emails | Before the change, make sure that the Entra email of each person is the same as the Google email. If not, the allowlist refuses the person, and Langfuse makes a new account without a project. |
| Rollback | Put back the Google settings |

**Acceptance criteria**
- [ ] Test host: a person without a session goes to the Google login. An email on the allowlist opens the dashboard. A company email that is not on the allowlist gets `403`. A personal Google account is refused.
- [ ] `GET /api/live/portfolio` on port 8443 without a session gives no data. On port 443, it gives `404` (S1-06).
- [ ] The GCP paths on port 443 do not change. The S1-02 and S1-06 tests pass. `POST /api/batch/runs` with the API key gives `201` and no redirect.
- [ ] Langfuse shows no password form. Engineers log in with Google and keep their projects and roles. A company account that is not invited sees no project.
- [ ] The engineer with the owner role logged in with Google before password login was turned off.
- [ ] A session ends after 8 hours, and `/oauth2/sign_out` ends it at once.
- [ ] The client secrets and the cookie secret are host secrets. No log contains a token, a cookie or a secret.
- [ ] The local stack uses the mock OIDC server with the same files. Only the settings are different.
- [ ] The runbook for Entra ID is written and platform reviewed it.
- [ ] The frontend files do not change (`artifacts/control-tower/src`).

**How to test**
1. Local stack: run `deploy/sso/check_sso.sh <host>`. Without a session, `/` and `/api/live/portfolio` on port 8443 redirect to the login and contain no data. Port 443 gives `404` for `/api/live/portfolio`. `POST /api/batch/runs` with the API key gives `201`.
2. Local stack: in the mock OIDC login form, log in as an email on the allowlist (the dashboard opens) and as an email that is not on it (`403`).
3. Test host: do steps 1 and 2 with real Google accounts: one RAI person, one engineer, one company account that is not on the allowlist.
4. Test host: open Langfuse. Make sure that there is no password form, and that the engineer sees the same projects as before.
5. Paired with S3-05: security examines the SSO items. Paired with S3-04: the SSO outage drill.

**Risk:** If the DNS name for the test host does not exist by 19 October, Google SSO cannot
work on the test host. Then use the fallback of the long-lead request. SSO must still work on
AWS (S4-01).

---

## Sprint 4 — Oct 26–30: AWS release and handoff

**Paired tests this sprint**

| Feature | Tested with | The test proves | Environment |
|---|---|---|---|
| S4-02 jobs switched to AWS | S4-01 AWS stack | Real runs and spans from GCP arrive in the AWS monitor and in Langfuse | Production AWS cluster |
| S4-03 all 10 use cases | S4-04 evidence checklist | Each use case has a real run with its five metrics graded, and the same trace ID in the monitor and in Langfuse | Production AWS cluster |

### S4-01 — Deploy the stack to the production AWS cluster

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Infrastructure | Platform | S3-06, long-lead requests (Sprint 1) | S4-02 | L |

**What:** Install the stack on the production AWS Kubernetes cluster. Use the S3-06 files.
The installation on the test AWS cluster in Sprint 3 is the model for this installation.

1. Select plan A (RDS and S3) or plan B (in the cluster), from the S3-06 decision.
2. Replace the test-host front door with the AWS load balancer and ingress. Keep the same paths: `/api/batch/runs`, `/api/health` and `/otlp/*` for GCP, and the dashboard and Langfuse behind SSO for the staff (S3-07).
3. Use the DNS name and the certificate from the long-lead requests. If they are not available, use the IP address and a private CA certificate. Without a DNS name, Google SSO does not work. Then the dashboard has only the IP allowlist, and the release result records this exception.
4. Allow the egress IPs of all 10 GCP jobs (S1-09) in the AWS security rules. The S3-06 test already proved this path for one job.
5. Allow a network path from the cluster to the company LiteLLM proxy. Use the AWS virtual key from S1-12.
6. Add the AWS redirect URIs to the two Google OAuth clients (S3-07).
7. Do not configure the prototype use cases.

**Open decisions (decide at the start of Sprint 4)**
- Is a production cluster available? If not, report the result as a pilot on the test AWS cluster. Do not report a production release.
- Does AWS start clean, or do we move the data from the test host?

**Acceptance criteria**
- [ ] Only the front door is reachable from the internet. The databases, ClickHouse, Redis and the storage are private.
- [ ] The data stays after a pod restart.
- [ ] The S3-07 SSO checks pass on AWS.
- [ ] `backend/scripts/judge_check.py --smoke` passes from the cluster, with the judge identity that RAI accepted (S2-10).
- [ ] The cluster name, the deployed versions and any missing prerequisite are recorded.

**How to test**
1. From a GCP dev machine, send one example run and spans. Run `scripts/check_trace.py`. Make sure that all the items are "found".
2. Delete the monitor pod and the Langfuse pods. After the restart, make sure that the same run and trace are still there.

### S4-02 — Change every GCP job to send to AWS

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Job developers + platform | S4-01 | S4-01 | M |

**What:** Change one job at a time. For each job, change three things:
1. The API URL.
2. The OTLP endpoint.
3. The API key. Make a new production key with `scripts/batch_keys.py`, and put it into the GCP Secret Manager of that project.

If AWS uses a private CA, the job trusts the new CA file.

The network path also changes. On the test host, the job used a private VPC path. To AWS,
the job sends across the internet through its Cloud NAT egress IP. Make sure that the job
runtime has outbound internet access through Cloud NAT, and that the egress IP is in the AWS
security rules (S4-01).

**Fallback:** Keep the test host running for one week after the change. If AWS has a
problem, a job can go back to the test host with its old settings.

**Acceptance criteria**
- [ ] The next run of each job arrives in AWS, with its trace in Langfuse.
- [ ] After the first production run of a job arrives, its test-host key is removed.
- [ ] One week after the last job changes, the test host is stopped. Its data is kept until the end of its retention period.

**How to test**
1. After the next run of each job, run `scripts/check_trace.py <trace_id>` on AWS. Make sure that all the items are "found".
2. Send a request with a removed test-host key to AWS. Make sure that it is refused.

### S4-03 — Finish all 10 use cases

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Job developers + backend + platform | S4-02 | S4-04 | L |

**What:** Onboard the last use cases with the S2-06 steps. Get a real run for each use case,
on its schedule or as an agreed controlled rerun. Use the S1-09 run dates. If a job does not
run before 30 October, book a controlled rerun now.

**When a use case passes (decided 2026-10-04)**

A use case passes only when its quality grade works. All of these must be true:
- A real run arrived, and the owner confirms it.
- The run contains records (`mode: records`). Security approved the records (S1-08).
- The task description is approved.
- The four judge metrics have values. `p95_latency_s` can be "Unknown" only with the reason `latency_not_reported` (Batch API jobs).
- The judge identity of the scores is the identity that RAI accepted (S2-10).

A use case in identity-only mode does **not** pass. Thus the security approval of the
records is a release blocker.

**Acceptance criteria**
- [ ] Each of the 10 use cases passes, or is listed as blocked with the reason, an owner and the next step.
- [ ] No test data, configuration-only entry or identity-only run counts as a pass.

**How to test**
1. The S4-04 checklist examines each use case.

### S4-04 — 10-row evidence checklist

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Backend + RAI | S4-03 | S1-07 (trace check tool) | M |

**What:** Make one table with one row for each use case. Each row contains:
- the use case,
- the run ID,
- the completion time and the freshness,
- the number of judged records,
- the five metric values, or "Unknown" with the reason,
- the overall grade,
- the task description version,
- the judge identity, and if it is the identity that RAI accepted (S2-10),
- the trace ID,
- the result of `scripts/check_trace.py`,
- the confirmation of the owner,
- the result: pass, or blocked with the reason (S4-03).

**Acceptance criteria**
- [ ] The table has 10 rows. All the columns are filled in.
- [ ] The trace ID and the score IDs are the same in the monitor and in Langfuse.
- [ ] The judge identity of each row is the identity that RAI accepted in S2-10. If the model behind the alias changed, the row is blocked until RAI accepts the new model.
- [ ] RAI accepts what the dashboard shows, including each "Unknown".

**How to test**
1. Run `scripts/check_trace.py` for all 10 trace IDs. Attach the output.

### S4-05 — Operations drills and runbooks on AWS

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Verification | Platform + operations | S4-01 | S1-07 (trace check tool) | M |

**What:** Do the S3-04 drills again on AWS. Also test the backup, the restore and the
rollback. Write the runbooks.

| Item | How |
|---|---|
| Backup and restore | Plan A: restore an RDS snapshot. Plan B: restore from our backup. Make sure that no run is lost or duplicated. |
| Rollback | Install the previous version with the Helm rollback command. Make sure that the system works. |
| Runbooks | A missed run, a failed job, a GCP network problem, a Langfuse outage, a judge outage (with the contact of the LiteLLM proxy owner, S1-12), a key rotation (also the LiteLLM virtual key), a full disk, an SSO outage, adding or removing a dashboard user, the change to Entra ID (S3-07) |

**Open decision:** Who is on call, and who owns the alerts? Decide this during Sprint 4. The
alert webhook goes to this person or team.

**Acceptance criteria**
- [ ] Each drill has a result: pass, fail or not done, with the date.
- [ ] Restore and rollback work with no lost or duplicated runs.
- [ ] Each runbook names an owner. The on-call owner is named before the sign-off (S4-06).

**How to test**
1. Do each drill. After each drill, run `scripts/check_trace.py` for the affected trace IDs.
2. Record the results in this issue.

### S4-06 — Release sign-off

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Decision | RAI + platform owners | S4-04, S4-05 | — | S |

**What:** Approve the release only on evidence. List each use case as "pass" or "blocked,
with the reason" (S4-03).

**Acceptance criteria**
- [ ] The release is approved only if all 10 use cases pass and the AWS drills pass.
- [ ] If not, publish the result as a pilot, with each open blocker, its owner and its next step.
- [ ] The result says clearly if it is a production release or a pilot on the test AWS cluster.

**How to test**
1. The reviewers examine the S4-04 checklist and the S4-05 drill record.

### S4-07 — Remove the prototype-only code

| Type | Owner | Depends on | Tested with | Size |
|---|---|---|---|---|
| Feature | Backend | S4-06 | Full test suite | M |

**What:** Remove the code of the three prototype use cases that the GCP path does not use.
Follow the rule for prototype code at the start of this file. Do this after the release
sign-off (S4-06), so that the AWS release does not change at the last moment. If Sprint 4
has no time left, do this issue in the first week of November.

**Acceptance criteria**
- [ ] A list of the removed files and a list of the kept shared files are in the pull request.
- [ ] Each removed item has no use in the GCP path. A repository search shows this.
- [ ] The tests of the shared code use GCP-style data, not prototype data.
- [ ] Packages that only the removed code used are removed from `backend/requirements.txt`.
- [ ] `CLAUDE.md`, `README.md` and the contract documents describe the GCP use cases.

**How to test**
1. Run the full backend suite and the pnpm checks.
2. On the test host, send one GCP run. Run `scripts/check_trace.py`. Make sure that all the items are "found".
