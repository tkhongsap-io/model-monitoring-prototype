# October Batch Monitoring MVP — Plan

| | |
|---|---|
| **Status** | Reviewed sprint by sprint, 2026-10-03 and 2026-10-04 |
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
| 2026-10-03 | All use cases use the **five LLM metrics of the prototype**. The GCP job sends only the data that these metrics need. | One definition of "good" for all use cases. The backend uses the shared judge and grade code. | [Standard](llm-metrics-standard.md) |
| 2026-10-03 | GCP spans contain no text. Backend spans can contain the redacted record text that the API accepted. | Text enters only through the API, which examines it | S1-05, S2-05 |
| 2026-10-03 | **Identity-only mode** until security approves the records | Tests can start on 6 October without text from GCP | S1-03 |
| 2026-10-03 | One front door on port 443 for the API and the Collector | One port, one certificate, one allowlist | S1-06 |
| 2026-10-03 | YAML registry for the settings, and a database table for the API key hashes | Changes to the settings are reviewed and have a history | S2-01 |
| 2026-10-03 | Langfuse is for engineers. The dashboard is for the RAI team. The dashboard shows only the GCP use cases, with the current UI and no record text. | No UI change. No text in the browser. | S2-07 |
| 2026-10-03 | The prototype use cases are a scaffold. Keep the shared code. Do not maintain the prototype-only code. Remove it after the release. | No work on code that we will remove | S4-07 |
| 2026-10-03 | Fixed versions: Python 3.12.15, PostgreSQL 17.11, Langfuse 4.50.0 | Stable and known versions | [Issues: fixed versions](issues.md#fixed-versions-checked-2026-10-03) |
| 2026-10-04 | On AWS: RDS and S3 (plan A), or everything in the cluster (plan B) | Less operations work with managed services | S3-06 |
| 2026-10-04 | Install on a test AWS cluster in Sprint 3 | Sprint 4 repeats a known installation | S3-06 |

## Sprints at a glance

| Sprint | Dates | Question | Use cases | Where it runs | Demo on Friday |
|---|---|---|---|---|---|
| **1** | 5 to 9 October | Can we get data out of GCP? | 1 | Test host (Docker Compose) | One real run arrives. The backend span has the trace ID of the job. |
| **2** | 12 to 16 October | Can the jobs use the same path, with grades and traces? | 4 | Test host | One run is one trace in Langfuse, from the GCP job to the scores. Its grade is on the dashboard. |
| **3** | 19 to 23 October | What happens when something fails? | 8 | Test host, and the test AWS cluster | The drills pass. The stack runs on the test AWS cluster. |
| **4** | 26 to 30 October | Does it work in production? | 10 | Production AWS cluster | The 10-row evidence checklist is signed |

## Dates and requests from other teams

Send the long-lead requests in Sprint 1. Their approval can take a long time.

| Item | Owner | Needed by | If it is late |
|---|---|---|---|
| Test host | Platform | Tue 6 October | Replay a saved real body into the local stack |
| JSON body v1 | GCP job developer + backend | Wed 7 October | The Sprint 1 demo moves |
| Security approval of the records, the PII list and the data flow | Security | Thu 8 October | Identity-only mode. A use case cannot pass the release without records. |
| Inventory of the 10 use cases and their October run dates | PM + owners | Fri 9 October | Sprint 2 cannot select the jobs |
| Langfuse SDK v4 and the OTel packages approved | Backend + project owner | Mon 12 October | The tracing work waits |
| Task description of the first use case | RAI | Wed 14 October | The judge metrics are "Unknown" |
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
| S1-04 | Test host that GCP can reach | Platform | M |
| S1-05 | OTel in the GCP job and the backend | GCP job developer + backend | M + M |
| S1-06 | Minimal Collector and front door | Platform | M |
| S1-07 | Trace check tool | Backend | S |
| S1-08 | Security approval for the Sprint 1 data flow | Security | S |
| S1-09 | Inventory of the 10 use cases | PM + owners | M |
| S1-10 | First real run from start to end | Backend + GCP job developer | S |
| S1-11 | Database accounts | Platform + backend | S |

**Done when:** the JSON body v1 is agreed, the API is merged with tests, one real run
arrived from a real GCP job with one trace, and the inventory has 10 rows with run dates.

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

**Done when:** 4 real use cases are on the dashboard, and one run is one trace in Langfuse
with its scores. The Sprint 2 prerequisites (server size, ports, judge access) are in
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

**Done when:** 8 real use cases are visible, the drills and the security review pass, and the
stack runs on the test AWS cluster.

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
| Judge | The LLM (Claude Haiku, or a local model) that scores each record |
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
| The backend cannot reach the Anthropic API | No judge | Local model on the on-premises server, after RAI examines it |
| The GCP developer has three issues in Sprint 1 | Sprint 1 is late | If necessary, move S1-05 part A to the start of Sprint 2 |

## Repository rules that this plan changes

Make these changes before the code that needs them is merged.

| Current rule | Change | Action |
|---|---|---|
| `CLAUDE.md`: the monitor is a consumer and makes no demands on the producer | The GCP jobs add a send step | Write an ADR in `docs/adr/` for the push method. Update `CLAUDE.md`. |
| `CLAUDE.md`: only the poller and the worker-token route change data | The receiving API writes runs | The same ADR. The API uses a key and stores each run one time. |
| `CLAUDE.md` project contract: three prototype models on Replit, risk tier R1 | 10 GCP use cases on AWS. Redacted customer data goes between the clouds. | Write `intent.md` for this change and examine the risk tier again. S4-07 updates `CLAUDE.md`. |
| No new packages without a plan entry | `opentelemetry-*`, `langfuse>=4.16,<5` | List them with versions in the Sprint 1 spec (OTel) and in S2-02 (Langfuse) |

## Not in October

Moving the Gemini traffic through LiteLLM. Metrics other than the five LLM metrics. Replacing
the contract v1.1 data windows with OTel. An OTel metrics or logs backend. A Langfuse link in
the dashboard. LIME explanations. Any number that the data does not contain.
