# October Batch Monitoring MVP — Plan

| | |
|---|---|
| **Status** | Reviewed sprint by sprint, 2026-10-03 and 2026-10-04. Revised 2026-10-05: SSO login and the LiteLLM judge. |
| **Period** | Monday 2026-10-05 to Friday 2026-10-30 (4 sprints of one week) |
| **Language** | ASD-STE100 (Simplified Technical English), about 80% strict |
| **Pull request** | [tkhongsap-io/model-monitoring-prototype#1](https://github.com/tkhongsap-io/model-monitoring-prototype/pull/1) |
| **Related** | [Summary and flows](summary.md) · [LLM metrics and data standard](llm-metrics-standard.md) · [Issues](issues.md) |

## Goal

By **Friday 30 October**, the **10 GCP batch use cases** send each completed run to the
monitor. The backend grades each run with the five LLM metrics of the prototype. The RAI
team sees the status, the freshness and the grade of each use case on the dashboard.
Engineers see one trace for each run in Langfuse. The stack runs on the **production AWS
Kubernetes cluster**.

A use case passes only when its quality grade works: real records arrive, and the judge
metrics have values (S4-03). If a use case, the production cluster or an approval is not
ready, we report the result as a pilot, with each blocker. We do not report a release.

## Decisions

| Date | Decision | Reason | Details |
|---|---|---|---|
| 2026-10-02 | Each GCP job **sends** a JSON run summary to the backend API after it publishes. The backend does not pull. | We work directly with the GCP job developer. The send is the proof that the run is complete. No access into GCP storage is necessary. | S1-01, S1-02, S1-03 |
| 2026-10-02 | Authentication: a static API key over HTTPS, with an IP allowlist. No VPN yet. | Low work. A Google identity token only if security requires it. | S1-02 |
| 2026-10-03 | **OpenTelemetry** is the tracing standard. GCP jobs use the OTel SDK and send to the Collector. The backend uses the Langfuse SDK v4 (which uses OTel) and sends to Langfuse. | One trace for each run, from the GCP job to the scores. No Langfuse keys in GCP. | S1-05, S2-02, S2-04 |
| 2026-10-03 | The trace ID goes in the `traceparent` HTTP header, not in the body | The OTel SDK adds it automatically | S1-05 |
| 2026-10-03 | All use cases use the **five LLM metrics of the prototype**. The GCP job sends only the data that these metrics need. **Replaced on 2026-10-08** (see below). | One definition of "good" for all use cases. The backend uses the shared judge and grade code. | [Standard](llm-metrics-standard.md) |
| 2026-10-03 | GCP spans contain no text. Backend spans can contain the redacted record text that the API accepted. | Text enters only through the API, which examines it | S1-05, S2-05 |
| 2026-10-03 | **Identity-only mode** until security approves the records | Tests can start on 6 October without text from GCP | S1-03 |
| 2026-10-03 | One front door on port 443 for the API and the Collector | One port, one certificate, one allowlist | S1-06 |
| 2026-10-03 | YAML registry for the settings, and a database table for the API key hashes | Changes to the settings are reviewed and have a history | S2-01 |
| 2026-10-03 | Langfuse is for engineers. The dashboard is for the RAI team. The dashboard shows only the GCP use cases, with the current UI and no record text. | No UI change. No text in the browser. | S2-07 |
| 2026-10-03 | The prototype use cases are a scaffold. Keep the shared code. Do not maintain the prototype-only code. Remove it after the release. | No work on code that we will remove | S4-07 |
| 2026-10-03 | Fixed versions: Python 3.12.15, PostgreSQL 17.11, Langfuse 4.50.0 (the monitor database changed to PostgreSQL 18.6 on 2026-10-07) | Stable and known versions | [Issues: fixed versions](issues.md#fixed-versions-checked-2026-10-03) |
| 2026-10-04 | On AWS: RDS and S3 (plan A), or everything in the cluster (plan B) | Less operations work with managed services | S3-06 |
| 2026-10-04 | Install on a test AWS cluster in Sprint 3 | Sprint 4 repeats a known installation | S3-06 |
| 2026-10-05 | The judge is a local model through the company LiteLLM proxy. Claude is not used. The backend calls the proxy with `httpx`. The `anthropic` package is removed. | Redacted records stay inside the company network. No new package. | S1-12, S2-09, S2-10 |
| 2026-10-05 | Staff log in with Google Workspace SSO: OAuth2 Proxy for the dashboard, the built-in SSO for Langfuse. The change to Entra ID later is a change of settings only. | Named access for each person instead of only an IP allowlist | S3-07 |
| 2026-10-05 | On port 443, the front door sends only `/api/batch/runs` and `/api/health` to the backend | Nobody reads the dashboard API around the SSO | S1-06 |
| 2026-10-05 | The test host for Sprints 1 to 3 is a Compute Engine VM in GCP with Docker Compose, on a private VPC path, with no public IP. The API key stays. The Sprint 3 Kubernetes test stays on the test AWS cluster. Production stays on AWS. | Real redacted data stays in GCP during the test. The same API key method as production. | S1-02, S1-04, S3-06 |
| 2026-10-06 | The monitor database on the test host is **Cloud SQL for PostgreSQL 18.6** (1 vCPU, 3.75 GiB, 100 GB SSD, private IP only, TLS only). The Langfuse database stays a PostgreSQL 17.11 container on the VM. Paid service on the GCP sandbox budget. | Managed backups and no database container on the VM, as on AWS (RDS) | S1-04, S1-11, S2-03 |
| 2026-10-07 | The monitor database is PostgreSQL 18.6 in every environment: Cloud SQL, the local stack and CI. AWS RDS targets PostgreSQL 18 (S3-06). | Tests run on the production version | S1-06, S3-06 |
| 2026-10-07 | The monitor team gets **no access to GCP logs**. The monitor sees failures only through what the job sends: a body with `status: failed`, and the OTel spans with an error status. | The jobs belong to teams across the company. Log access is hard to get. | S1-01, S1-05, S1-08 |
| 2026-10-08 | Each use case gets the **core metrics** and **one quality profile** for its task type. The five LLM metrics stay only for the generation profiles. | All 10 use cases are one-turn batch inference. The first job is an image classifier, and the chatbot metrics do not fit it. | [Core metrics](../2026-10-08-batch-metric-profiles/core-metrics.md), S1-09, S2-05 |
| 2026-10-08 | **Traceability first.** The scope stays the same: the receiving API plus OTel and the Collector. | The project owner wants each run to be traceable before the quality metrics | S1-02 to S1-07, S1-10 |
| 2026-10-08 | **Sprint 1 sends identity-only bodies** (`records: []`, `records_reason: records_not_approved`). The job keeps `SEND_RECORDS` off. The record fixes (no system prompt in `question`, one `[IMAGE]` for each image, `retrieval_context: []` for images) move to Sprint 2. | The trace needs no record text. No customer text leaves GCP in Sprint 1. | S1-01, S1-03, S1-10 |
| 2026-10-08 | **S1-08 for Sprint 1** approves only the run identity, the API key path, the certificate and the OTLP endpoint. The records, the PII list and the LiteLLM proxy logs are approved before Sprint 2 needs them. | Sprint 1 sends no text | S1-08 |
| 2026-10-08 | **Backlog:** a reporter library for other teams (one Python file, one function `report_run()`, also a command-line tool) that builds, samples, redacts and sends the run summary. Not in October. | Teams outside the GCP batch jobs need a minimal way to register | — |

## Sprints at a glance

| Sprint | Dates | Question | Use cases | Where it runs | Demo on Friday |
|---|---|---|---|---|---|
| **1** | 5 to 9 October | Can we get data out of GCP? | 1 | Test host: Compute Engine VM in GCP (Docker Compose) and Cloud SQL | One real run arrives. The backend span has the trace ID of the job. |
| **2** | 12 to 16 October | Can the jobs use the same path, with grades and traces? | 4 | Test host | One run is one trace in Langfuse, from the GCP job to the scores. Its grade is on the dashboard. |
| **3** | 19 to 23 October | What happens when something fails? | 8 | Test host, and the test AWS cluster | The drills pass. The stack runs on the test AWS cluster. |
| **4** | 26 to 30 October | Does it work in production? | 10 | Production AWS cluster | The 10-row evidence checklist is signed |

## Dates and requests from other teams

Send the long-lead requests in Sprint 1. Their approval can take a long time.

| Item | Owner | Needed by | If it is late |
|---|---|---|---|
| Test host VM and Cloud SQL instance in GCP, with the private VPC path from the first job (S1-04) | Platform + network team | Tue 6 October | Replay a saved real body into the local stack |
| JSON body v1 | GCP job developer + backend | Wed 7 October | The Sprint 1 demo moves |
| Security approval of the records, the PII list and the data flow | Security | Thu 8 October | Identity-only mode. A use case cannot pass the release without records. |
| Inventory of the 10 use cases and their October run dates | PM + owners | Fri 9 October | Sprint 2 cannot select the jobs |
| LiteLLM proxy access: URL, virtual keys, model alias, log policy (S1-12) | LiteLLM proxy owner | Fri 9 October | S2-09 is tested only on the local stack. No scores on the test host. |
| Langfuse SDK v4 and the OTel packages approved | Backend + project owner | Mon 12 October | The tracing work waits |
| Task description of the first use case | RAI | Wed 14 October | The judge metrics are "Unknown" |
| RAI accepts the local judge (S2-10) | RAI | Fri 16 October | The scores show, but no use case can pass the release |
| Private DNS name for the test host under a company domain, and two Google OAuth clients (long-lead) | Your team + network team + Google Workspace administrator | Mon 19 October | No SSO on the test host. Firewall rules only. |
| Test AWS Kubernetes cluster (long-lead) | Your team | Mon 19 October | Test on a local kind cluster only |
| RDS and S3 (long-lead) | Platform + AWS team | Wed 21 October | Plan B |
| DNS name and certificate (long-lead) | Your team + network team | Mon 26 October | IP address and a private CA certificate |
| Production AWS cluster (long-lead) | Platform | Mon 26 October | Pilot on the test AWS cluster |
| On-call owner and alert owner | Project owner | Before S4-06 | No sign-off |

## Sprint 1 — 5 to 9 October: get data out of GCP

| Issue | Title | Owner | Size |
|---|---|---|---|
| S1-01 | Map one GCP job and write the JSON body v1 | GCP job developer | M |
| S1-02 | Receiving API with API key | Backend | L |
| S1-03 | GCP job sends the run summary | GCP job developer | M |
| S1-04 | Test host in GCP (Compute Engine VM) | Platform | M |
| S1-05 | OTel in the GCP job and the backend | GCP job developer + backend | M + M |
| S1-06 | Minimal Collector and front door | Platform | M |
| S1-07 | Trace check tool | Backend | S |
| S1-08 | Security approval for the Sprint 1 data flow | Security | S |
| S1-09 | Inventory of the 10 use cases | PM + owners | M |
| S1-10 | First real run from start to end | Backend + GCP job developer | S |
| S1-11 | Database accounts | Platform + backend | S |
| S1-12 | Access to the company LiteLLM proxy for the judge | Backend + LiteLLM proxy owner | S |

**Done when:** the JSON body v1 is agreed, the API is merged with tests, one real run
arrived from a real GCP job with one trace, the inventory has 10 rows with run dates, and
the test host can call the LiteLLM proxy.

## Sprint 2 — 12 to 16 October: same path for many jobs, with grades and traces

| Issue | Title | Owner | Size |
|---|---|---|---|
| S2-01 | Registry: YAML settings and API key hashes | Backend + platform | M |
| S2-02 | Langfuse SDK v4 in the backend, and packages | Backend + project owner | M |
| S2-03 | Collector sends to self-hosted Langfuse | Platform | L |
| S2-04 | OTel helper file for the GCP jobs | GCP job developer | M |
| S2-05 | Batch evaluator with the five LLM metrics | Backend + RAI | L |
| S2-06 | Onboard 4 use cases | Job developers + backend + platform | L |
| S2-07 | Dashboard shows the GCP use cases | Backend | M |
| S2-08 | Sprint 2 demo | Backend + platform | S |
| S2-09 | Judge through the company LiteLLM proxy | Backend | M |
| S2-10 | RAI accepts the local judge | RAI + backend | M |

**Done when:** 4 real use cases are on the dashboard, one run is one trace in Langfuse
with its scores from the LiteLLM judge, and RAI decided on the judge. The Sprint 2 prerequisites (server size, ports, judge access) are in
[issues.md](issues.md).

## Sprint 3 — 19 to 23 October: 8 use cases, and stronger

| Issue | Title | Owner | Size |
|---|---|---|---|
| S3-01 | Onboard 8 use cases | Job developers + backend + platform | L |
| S3-02 | Delivery lane: missed-run and failed-job alerts | Backend | M |
| S3-03 | Collector hardening | Platform | M |
| S3-04 | Failure and recovery drills | Backend + platform | M |
| S3-05 | Security review and leak scan | Security + platform | M |
| S3-06 | Kubernetes files, installed on the test AWS cluster | Platform | L |
| S3-07 | SSO login for the dashboard and Langfuse | Platform | M |

**Done when:** 8 real use cases are visible, the staff log in with SSO, the drills and the
security review pass, and the stack runs on the test AWS cluster.

## Sprint 4 — 26 to 30 October: production and handoff

| Issue | Title | Owner | Size |
|---|---|---|---|
| S4-01 | Deploy to the production AWS cluster | Platform | L |
| S4-02 | Change every GCP job to send to AWS | Job developers + platform | M |
| S4-03 | Finish all 10 use cases | Job developers + backend + platform | L |
| S4-04 | 10-row evidence checklist | Backend + RAI | M |
| S4-05 | Operations drills and runbooks on AWS | Platform + operations | M |
| S4-06 | Release sign-off | RAI + platform owners | S |
| S4-07 | Remove the prototype-only code (after S4-06, or in the first week of November) | Backend | M |

**Done when:** all 10 use cases pass on the production cluster and the AWS drills pass. If
not, publish the result as a pilot, with each blocker.

## Rules for each issue

| Rule | Meaning |
|---|---|
| Real runs only | A use case counts only when a real run from the real job arrives. Test files, configuration entries and identity-only runs do not count for the release. |
| Unknown is not Green | If a value cannot be measured, show "Unknown" with the reason |
| No invented numbers | No latency, cost or accuracy that the data does not contain |
| Redacted records only | Only the fields of the standard leave GCP. PII is replaced by placeholders. GCP spans and logs never contain text. |
| Store one time, never change | One run for each `(use_case_id, run_id)`. A send again is safe. A stored run never changes. |
| The monitor advises | It shows results to people. It never changes or stops a model or a job. |
| Prototype code | Keep and test the shared code. Do not maintain the prototype-only code. |

## Glossary

| Term | Meaning |
|---|---|
| Batch job | A GCP job on a schedule that sends many requests to Gemini and gets the results later |
| Submit, harvest, publish | The three steps of a batch job. A run is complete only after publish. |
| Run summary | The JSON body that the GCP job sends after publish |
| Record | One sampled request: instruction, answer, source material, refused flag, latency |
| Identity-only mode | The job sends the run summary without records, until security approves |
| Judge | The local LLM behind the company LiteLLM proxy that scores each record |
| LiteLLM proxy | The company gateway, owned by another team, that gives an OpenAI-compatible API to the local models |
| SSO | Single sign-on: the staff log in with their company account (Google now, Entra ID later) |
| OAuth2 Proxy | The service in front of the dashboard that asks for the SSO login |
| Task description | One sentence for each use case that tells the judge what the outputs are |
| OTel / OpenTelemetry | The open standard for traces |
| Span | One timed step in a trace |
| Trace context (`traceparent`) | The standard header that connects the spans of different systems |
| OTel Collector | The service that receives the GCP spans and sends them to Langfuse |
| Langfuse | The self-hosted tool where engineers see the traces and the scores |
| Front door | The reverse proxy on the test host for the API, the Collector, the dashboard and Langfuse |
| Freshness | The time since the last completed run arrived |

## Risks

| Risk | Effect | Action |
|---|---|---|
| Security approves the records late | Use cases stay in identity-only mode and cannot pass | Send the request in Sprint 1. Start the tests in identity-only mode. |
| Monthly jobs do not run in October | Fewer than 10 use cases | Run dates by 9 October. Book controlled reruns early. |
| Approvals for DNS, the clusters, RDS or S3 are late | No production release | Long-lead requests in Sprint 1, each with a fallback |
| Only 6 pipelines in 4 repositories were examined | The 10-ID list can be different | The inventory (S1-09) is a Sprint 1 exit condition |
| Each job developer must change their job | Onboarding depends on many people | Keep the send step and the helper file small. Use the S2-06 steps for each job. |
| The local judge scores worse than Claude, mainly for Thai text | RAI does not accept the judge, and no use case passes | Reference set and limits in S2-10 by 16 October. Ask the proxy owner for a different model if necessary. |
| The LiteLLM proxy is slow or limits the calls when many runs arrive | Scores arrive late, or `judge_failed` | `LLM_JUDGE_CONCURRENCY` and the rate limit from S1-12. Drill in S3-04. |
| The proxy owner changes the model behind the alias | The scores change without notice | Each score stores the model name. S4-04 compares it with the accepted model. |
| No private DNS name for the test host by 19 October | No SSO on the test host | Long-lead request in Sprint 1. SSO must work on AWS. |
| The test host is on a private path, so Sprints 1 and 2 do not test the internet path to AWS | Network problems appear only in Sprint 4 | S3-06 sends from a GCP job runtime through Cloud NAT to the test AWS cluster |
| A job runtime cannot reach an internal IP (for example a Cloud Run job without VPC egress) | The job cannot send to the test host | S1-04 and S1-09 record the runtime of each job. Platform adds VPC egress before onboarding (S2-06). |
| Platform has three issues in Sprint 3 (S3-03, S3-06, S3-07) | Sprint 3 is late | S3-07 is settings only. Backend can help with the local stack and the check script. |
| The GCP developer has three issues in Sprint 1 | Sprint 1 is late | If necessary, move S1-05 part A to the start of Sprint 2 |

## Repository rules that this plan changes

Make these changes before the code that needs them is merged.

| Current rule | Change | Action |
|---|---|---|
| `CLAUDE.md`: the monitor is a consumer and makes no demands on the producer | The GCP jobs add a send step | Write an ADR in `docs/adr/` for the push method. Update `CLAUDE.md`. |
| `CLAUDE.md`: only the poller and the worker-token route change data | The receiving API writes runs | The same ADR. The API uses a key and stores each run one time. |
| `CLAUDE.md` project contract: three prototype models on Replit, risk tier R1 | 10 GCP use cases on AWS. Redacted customer data goes between the clouds. | Write `intent.md` for this change and examine the risk tier again. S4-07 updates `CLAUDE.md`. |
| No new packages without a plan entry | `opentelemetry-*`, `langfuse>=4.16,<5`. `anthropic` is removed (S2-09). New images: OAuth2 Proxy and the mock OIDC server (S3-07). | List them with versions in the Sprint 1 spec (OTel), in S2-02 (Langfuse) and in the fixed-versions table (images) |
| `docs/STRICT-LIVE.md`: `ANTHROPIC_API_KEY` is required | `LLM_JUDGE_BASE_URL`, `LLM_JUDGE_API_KEY` and `LLM_JUDGE_MODEL` are required | S2-09 updates `docs/STRICT-LIVE.md`, `.env.example` and the CI workflow |

## Not in October

Moving the Gemini traffic of the GCP jobs through LiteLLM (only the judge uses LiteLLM). Metrics other than the five LLM metrics. Replacing
the contract v1.1 data windows with OTel. An OTel metrics or logs backend. A Langfuse link in
the dashboard. LIME explanations. Any number that the data does not contain.
