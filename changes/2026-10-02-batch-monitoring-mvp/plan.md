# October Batch Monitoring MVP — Plan

| | |
|---|---|
| **Status** | Draft for review |
| **Date** | 2026-10-02 |
| **Period** | Mon 2026-10-05 to Fri 2026-10-30 (4 one-week sprints) |
| **Pull request** | [tkhongsap-io/model-monitoring-prototype#1](https://github.com/tkhongsap-io/model-monitoring-prototype/pull/1) |
| **Related** | [One-page summary and flows](summary.md) · [Issue drafts](issues.md) · [Older GCP → AWS flow](flow.html) |

## Goal

By **Friday 2026-10-30**, all **10 GCP batch use cases** send each completed run to the
monitor. The RAI dashboard shows every run with its status, freshness and evaluation
result (or a clear "Unknown" with a reason), plus a linked trace in Langfuse. The whole
stack runs on the **target AWS Kubernetes cluster**.

The existing three live use cases (churn, chatbot, NBA, contract v1.1) keep working
unchanged. The batch path is added next to them.

## How data gets out of GCP (decided 2026-10-02)

Each GCP batch job **pushes** a small JSON summary to the monitor's API **after** its
results are published to the business. We agree on the JSON body with the GCP job
developer in Sprint 1.

| Option | Decision | Why |
|---|---|---|
| **Push**: GCP job calls the monitor API after publishing | **Chosen** | We work directly with the GCP job developer. The job knows exactly when a run is finished, so the push itself is the completion proof. No cross-cloud read access to buckets is needed. |
| Pull: monitor reads GCP buckets and job state | Not chosen for MVP | Needs read access into GCP for every source, and the monitor would have to guess when a run is truly published. Some jobs delete raw outputs after harvest. |

## Tracing standard: OpenTelemetry (decided 2026-10-03)

Today the stack has no OpenTelemetry. "Telemetry" means our own JSON contract (v1.1), and
the monitor writes to Langfuse with the Langfuse SDK v2 directly. From October,
OpenTelemetry is the tracing standard for the monitor and the GCP batch jobs.

| Area | Old way | New way |
|---|---|---|
| Monitor → Langfuse | Langfuse SDK v2 calls straight to Langfuse Cloud | OTel SDK spans → OTel Collector → self-hosted Langfuse; scores through the Langfuse score API on the same trace ID |
| Monitor's own visibility | JSON logs only | OTel spans for API, outgoing HTTP and database calls; logs carry the trace ID |
| GCP batch jobs | Nothing | OTel SDK in each job: one trace per run, with the trace ID passed in the run summary (W3C `traceparent`) |
| Run summary from GCP | — | Stays a JSON push: it is the official record and must arrive exactly once |
| Contract v1.1 data windows | Custom JSON pull | Unchanged in October; moving chatbot traces to OTel is a later step |

A use case counts as live when its run summary arrives. A complete trace is required for
sign-off wherever OTLP traffic from GCP is approved.

## Sprints at a glance

| Sprint | Dates | Question it answers | Real use cases live | Where it runs | Demo on Friday |
|---|---|---|---|---|---|
| **1** | Oct 5–9 | Can we get data out of GCP? | 1 | Monitor API on a reachable test host | One real run sent by a GCP job and visible through the monitor API; its ingest span carries the job's trace ID |
| **2** | Oct 12–16 | Can every job use the same path, with evaluation and tracing? | 4 | Local Docker Compose (monitor + Postgres + OTel Collector + Langfuse) | 4 use cases on the dashboard; one run shown as a single Langfuse trace from GCP job to score |
| **3** | Oct 19–23 | What happens when things break? | 8 | Compose, plus Kubernetes manifests ready | Failure drills pass; security review done |
| **4** | Oct 26–30 | Does it work in the real place? | 10 | Target AWS Kubernetes cluster | 10-row evidence checklist signed off |

## Deadlines for things outside our control

These items belong to other people. If one is late, the fallback applies. We do not
discover it in week 4.

| Item | Owner | Needed by | If late |
|---|---|---|---|
| Test host the GCP job can reach in Sprint 1 | Platform | Tue Oct 6 | GCP developer captures the real JSON body from a real run; we replay it into a local monitor and record that delivery was not tested |
| Agreed JSON body v1 (fields, meaning, examples) | Backend + GCP job developer | Wed Oct 7 | Sprint 1 demo slips; nothing else can start |
| Security approval of which fields may leave GCP | Security | Thu Oct 8 | Send only IDs, counts, status and timestamps until approved |
| Final list of the 10 use-case IDs, owners and run schedule | PM + source owners | Fri Oct 9 | Sprint 2 onboarding order cannot be planned |
| Langfuse SDK v2 or v3, and new `opentelemetry-*` pip packages approved | Backend + project owner | Mon Oct 12 | Sprint 2 tracing work waits; data path continues |
| One use case with a reviewed evaluation rubric | RAI reviewers | Wed Oct 14 | Evaluation shows Unknown; tracing still ships |
| GCP → AWS OTLP traffic and allowed span attributes approved | Security + platform | Fri Oct 16 | GCP jobs keep spans local; traces start at the monitor; run summaries still count |
| AWS cluster owner and access granted | Platform | Wed Oct 14 | Target becomes a local pilot; report that the AWS release is blocked |
| Each GCP job adds the send step | Each job owner | Sprint 2: 4 jobs; Sprint 3: 8; Sprint 4: 10 | Use case reported as blocked, not live |
| Monthly jobs that will not run in October | Source owners | Fri Oct 9 (from the run schedule) | Book a controlled real rerun date now |

## Sprint 1 — Oct 5–9: get data out of GCP

**Goal:** Agree the JSON body with the GCP job developer, build the API that receives it,
and see one real run arrive.

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 1.1 | Walk through one GCP job with its developer: where is the "results published" moment, and which fields already exist (run ID, model, token counts, row counts, status, timestamps)? | Backend + GCP job developer | Notes list every field available at the publish step and where it comes from | — |
| 1.2 | Write **JSON body v1** for a completed run, with 2–3 example files (normal run, partial failure, missing fields). Include the job's trace context (W3C `traceparent`) | Backend | GCP developer, RAI and security have reviewed it; a version number is in the body | 1.1 |
| 1.3 | Build the receiving API (proposed `POST /api/batch/runs`): checks the token, validates the body, stores the run once | Backend | Tests pass for: valid run saved; same run sent twice = saved once; same run ID with different content = rejected; bad body = rejected; wrong or missing token = rejected | 1.2 |
| 1.4 | Add the "send summary" step to one GCP job, right after publishing, with retries | GCP job developer | Job sends to the test host and logs the response; a send failure does not break the business job | 1.2, test host |
| 1.5 | Security check: which fields may leave GCP, where the token is stored (GCP Secret Manager), HTTPS only | Security + platform | Field allowlist and token handling approved, or blocked with a named owner and date | 1.2 |
| 1.6 | End-to-end: one real run, sent by the real job, stored and visible through the monitor API | Backend + GCP job developer | Run ID, status, counts and freshness visible; no customer text stored | 1.3, 1.4, 1.5 |
| 1.7 | Inventory of all 10 use cases: ID, owner, GCP job, schedule (which days it runs in October), labels available, data sensitivity | PM + source owners | Table has exactly 10 rows with named owners, and the October run dates are known | — |
| 1.8 | Add the OTel SDK to the monitor: the receiving API starts a span that continues the job's trace from `traceparent`; export to a console or local Collector | Backend | A test shows the ingest span has the trace ID sent in the body; no body content in span attributes | 1.3 |

**Sprint 1 is done when:** JSON body v1 is agreed and versioned, the receiving API is
merged with tests, one real run has arrived from a real GCP job, the monitor emits an
OTel span that continues the job's trace, and the 10-row inventory with run dates exists.

## Sprint 2 — Oct 12–16: same path for many jobs, plus evaluation and tracing

**Goal:** Make onboarding a new job a small change, add evaluation and Langfuse tracing,
and show 4 use cases on the dashboard.

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 2.1 | Source registry: list of allowed use-case IDs, one token per use case | Backend | A token can only write its own use case; unknown IDs are rejected | 1.3 |
| 2.2 | Onboard **4 different use cases** (at least one with a different output shape) | Job owners + backend | 4 real runs received and confirmed by each owner; configuration or test files alone do not count | 2.1, 1.7 |
| 2.3 | Evaluate batch runs with the existing judge and scoring, using the reviewed rubric | RAI + backend | Score saved with rubric version, sample size and run ID; missing labels or judge failure gives Unknown, never Green | rubric (Oct 14) |
| 2.4 | Local stack in Docker Compose: monitor, Postgres, OTel Collector, self-hosted Langfuse (started on this branch) | Platform + backend | A real run creates one trace in Langfuse with its score attached; sending again does not create duplicates | 1.3 |
| 2.5 | Dashboard and API show each use case: last run, freshness, status, score or Unknown reason, trace link | Frontend + backend | 4 use cases visible; browser uses only read APIs; no Langfuse or database keys reach the browser | 2.2, 2.3, 2.4 |
| 2.6 | Move the monitor off direct Langfuse SDK v2 calls: judge and evaluator spans go through the OTel Collector; scores use the Langfuse score API on the same trace ID | Backend | Existing chatbot judge tests still pass; a judged trace and its score are read back from local Langfuse | 2.4, SDK decision |
| 2.7 | Shared OTel helper for GCP jobs (root span per run, child spans for submit, harvest, publish and each Gemini call with model and token counts; no prompts or customer text), added to the 4 onboarded jobs | Backend + job owners | Each of the 4 jobs produces one trace per run that continues into the monitor's ingest and evaluate spans | 1.8, 2.4 |

**Sprint 2 is done when:** 4 real use cases are visible, and one run was shown in local
Langfuse as a single trace from GCP job to score. Compose does not prove the AWS
deployment.

## Sprint 3 — Oct 19–23: scale to 8 and harden

**Goal:** Reach 8 use cases, prove recovery from failures, pass security review, and
have Kubernetes manifests ready.

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 3.1 | Onboard **8 different use cases**, including harder ones (submit and harvest in different job runs, partial publication), each with the OTel helper | Job owners + backend | 8 real runs received and confirmed by owners; a job that was only submitted does not send; submit and harvest in different runs still join one trace | 2.2, 2.7 |
| 3.2 | Missed-run detection: alert when a use case's expected run (from the schedule) did not arrive | Backend | Stale use case shows on the dashboard and alerts; it is shown as a delivery problem, not a model-quality problem | 1.7 |
| 3.3 | Failure drills: monitor down while a job sends, Collector down, Langfuse score write fails, monitor restart | Backend + platform | GCP job retries succeed later; each run is stored once with one linked score; nothing is lost | 2.4 |
| 3.4 | Security and retention review for all onboarded use cases, including Collector hardening: authenticated OTLP over TLS, attribute allowlist and redaction in the Collector, bounded retry queue | Security + platform + source owners | No customer text, identifiers or credentials in stored runs, traces, logs or the dashboard; unauthenticated OTLP is rejected; exceptions written down with owners | 3.1 |
| 3.5 | Kubernetes manifests for monitor, Collector, Langfuse and their storage: secrets, TLS ingress, health checks, rollback | Platform | Manifests validate; tested on a disposable cluster if one is available (otherwise recorded as not tested); backup and rollback steps written | 2.4 |

**Sprint 3 is done when:** 8 real use cases are visible, failure drills and security review
pass, and the AWS deployment path is ready or its blockers are recorded.

## Sprint 4 — Oct 26–30: AWS release and handoff

**Goal:** Deploy to the target AWS cluster, point all 10 jobs at it, and sign off on
evidence.

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 4.1 | Deploy monitor, Collector, Langfuse and backing services to the **target AWS cluster** | Platform | Private services, TLS, secrets and storage verified; data survives a pod restart | 3.5, cluster access |
| 4.2 | Switch every GCP job to send run summaries and OTel spans to the AWS endpoints | Job owners + platform | Each job's next run arrives in AWS with its trace in Langfuse | 4.1 |
| 4.3 | Finish all **10 use cases** with a real run on their schedule, or an agreed controlled rerun | Job owners + backend | 10 owner-confirmed real runs; none counted from test data or configuration only | 3.1, 4.2 |
| 4.4 | Evidence checklist: for each of the 10, run ID, completion time, freshness, score or Unknown reason, trace ID | Backend + frontend + RAI | 10 rows filled in; trace and score IDs match; RAI accepts what is shown | 4.3 |
| 4.5 | Operations drills on the AWS cluster: restart, backup and restore, rollback, alerts; write runbooks and on-call | Platform + operations | Drills recorded with no duplicates or data loss; runbooks name owners and escalation | 4.1 |
| 4.6 | Release sign-off | RAI + platform owners | Signed only if 10/10 real use cases and the AWS drills pass; otherwise publish the pilot result and its open blockers | 4.4, 4.5 |

**Sprint 4 is done when:** 10 of 10 real use cases are verified on the AWS cluster and
the operations handoff passes. Otherwise we report what was achieved and what is blocked.

## Rules for every task

| Rule | Meaning |
|---|---|
| Real runs only | A use case is live only when a real completed run from the real GCP job has arrived. Test files, configuration entries and submitted-only jobs do not count. |
| Unknown is not Green | If something cannot be measured (no labels, judge failed, field missing), show Unknown with the reason. |
| No invented numbers | No latency, cost or accuracy unless the data actually contains it. Monitor processing time is not Gemini latency. |
| No customer content | Only approved fields leave GCP. No customer text, identifiers or credentials in storage, traces, logs or the dashboard. |
| Store once, never rewrite | A run is stored once per `(use_case_id, run_id)`. Sending again is safe. A stored run is never edited. |
| The monitor advises | It shows results to people. It never changes or stops a model or a job. |
| Existing use cases untouched | Contract v1.1 and the three live use cases keep working; their tests must keep passing. |

## Glossary

| Term | Meaning |
|---|---|
| Batch job | A scheduled GCP job that sends many requests to Gemini at once and collects results later |
| Submit / harvest / publish | The three steps of a batch job: send the work to Gemini, collect the results, then deliver them to where the business uses them (GCS, SharePoint). A run is **completed** only after publish. |
| JSON body | The small summary of one completed run that the GCP job sends to the monitor |
| Receiving API | The monitor endpoint that accepts the JSON body (proposed `POST /api/batch/runs`) |
| Rubric | The written rules for judging the quality of one use case's output, with a version number |
| Judge | The LLM that scores outputs against the rubric |
| Labels | Real outcomes ("ground truth") used to measure accuracy. Without them, accuracy is Unknown. |
| OTel / OpenTelemetry | Open standard for traces (timing records of each processing step). The OTel SDK is the library added to our code to create them. |
| Span | One timed step inside a trace, such as "harvest" or one Gemini call |
| Trace context (`traceparent`) | A standard ID passed between systems so their spans join the same trace |
| OTLP | The protocol OTel uses to send spans to a Collector |
| OTel Collector | The service that receives spans, removes disallowed fields, retries, and forwards them to Langfuse |
| Langfuse | Self-hosted tool that stores LLM traces and evaluation scores |
| Linked score | A score attached to a specific Langfuse trace. It is written through a separate Langfuse call, not through OTel. |
| Freshness | How long ago the last completed run arrived |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| The monitor is down when a job sends | That run is missing | Job retries with backoff; sending again is safe; missed-run alert (3.2) catches anything still missing |
| Monthly jobs do not run in the window | Cannot reach 10 by Oct 30 | Run schedule known by Oct 9; book reruns early |
| AWS cluster access is late | No AWS release | Deadline Oct 14; fallback is an honest local pilot report |
| Only 6 pipelines in 4 repositories have been inspected so far | The 10-ID list may differ from what we expect | Inventory (1.7) is a Sprint 1 exit condition |
| Each job owner must change their job | Onboarding depends on 10 teams | Keep the send step and OTel helper small; give owners a copy-paste example and a test endpoint |
| OTel delivery is best-effort (spans can be dropped or sampled) | Gaps in traces | Grading uses the run summary, never spans; traces are for inspection |
| Langfuse accepts OTel traces only, and OTLP cannot write scores | Scores missing from traces | Scores always go through the Langfuse score API, tested in 2.6 |
| Langfuse SDK v2 to v3 change | Existing judge write-back breaks | Decide by Oct 12; keep chatbot judge tests green in 2.6 |

## Repository rules this plan changes

These need an explicit decision before code merges.

| Current rule | Change | Action |
|---|---|---|
| `CLAUDE.md`: the monitor is a consumer and makes no producer demands | GCP jobs add a send step | Write an ADR under `docs/adr/` for push ingestion; update `CLAUDE.md` |
| `CLAUDE.md`: only the poller and the worker-token poll route change data | New receiving API writes runs | Cover it in the same ADR; keep it token-protected and idempotent |
| `CLAUDE.md` project contract: three models, Replit release, risk tier R1 | 10 GCP use cases, AWS Kubernetes, customer-related data crossing clouds | Write `intent.md` for this change and re-assess the risk tier |
| No new pip or npm packages without a plan entry | `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, instrumentation for FastAPI, httpx and SQLAlchemy; possibly `langfuse` v3 | List each package and version in the Sprint 1 spec (monitor SDK) and Sprint 2 spec (instrumentation, Langfuse) before adding it |

## Out of scope for October

Moving existing Gemini traffic through LiteLLM; replacing contract v1.1 data windows
(features, labels, reference, chatbot traces) with OTel; an OTel metrics or logs backend
(Langfuse stores traces only); LIME explanations (next MVP); any number the data does not
contain.
