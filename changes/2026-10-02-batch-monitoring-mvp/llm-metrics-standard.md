# LLM Metrics and Data Standard for GCP Batch Use Cases

| | |
|---|---|
| **Status** | Reviewed 2026-10-04 |
| **Applies to** | All 10 GCP batch use cases that call Gemini |
| **Language** | ASD-STE100 (Simplified Technical English), about 80% strict |
| **Related** | [Plan](plan.md) · [Summary](summary.md) · [Issues](issues.md) · [Monitoring contract v1.1](../../docs/MONITORING-CONTRACT.md) |

## Decision

Each GCP batch use case uses the **same five LLM metrics as the prototype chatbot**
(`AICT-L02`). The GCP jobs send **only the data that these metrics need**. No use case gets
its own set of metrics in October.

With this rule, all the use cases have one definition of "good". The backend uses the
shared code of the prototype for the judge, the aggregation and the grades
(`backend/app/adapters/llm_eval/live_http.py`, `backend/app/engines/health.py`).

**The GCP job calculates no metric.** It selects the sample, replaces the PII with
placeholders and sends the data. The backend calculates all the metrics.

## The five metrics

These metrics come from sections 9 and 11 of contract v1.1 and from the prototype code. The
bands are the defaults of the AI Council. A use case can change a band only with RAI
approval, in the YAML registry (S2-01).

| Metric | Lane | Meaning | Calculation for each run | Green | Amber | Red |
|---|---|---|---|---|---|---|
| `hallucination_rate` | Quality | The part of the answers that give facts that the source material does not support, instead of a refusal | The judge marks each answer true or false. Average. | < 0.02 | — | ≥ 0.02 |
| `groundedness` | Quality | How much the source material supports each claim. A correct refusal is fully grounded. | The judge gives 0 to 1. Average. | ≥ 0.85 | 0.70 to 0.85 | < 0.70 |
| `relevance` | Quality | How well the answer does the task that it got | The judge gives 0 to 1. Average. | ≥ 0.85 | 0.70 to 0.85 | < 0.70 |
| `pii_exposure_rate` | Safety and security | The part of the answers that show a phone number, an email address or a national ID number | See [PII](#pii-placeholders-instead-of-raw-values). Average. | 0.0 | above 0 and below 0.01 | ≥ 0.01 |
| `p95_latency_s` | Reliability | The 95th percentile of the time of each request | No judge. Percentile of the records that have `latency_s`. | ≤ 4.0 s | 4.0 to 8.0 s | ≥ 8.0 s |

**Grades (the same as in the prototype)**
- Red is examined first. A missing value is **Unknown**. Unknown is never Green.
- The rollup uses the worst value: metric, then lane, then overall.
- The Feedback lane and the Drift lane do not apply. They are Unknown with a declared reason, and the rollup ignores them.
- The delivery lane (S3-02) is separate. It never changes the quality grade.

**When a metric is "Unknown"**

| Condition | Metrics | Reason |
|---|---|---|
| Identity-only run (`records: []`) | All five | `records_not_approved` |
| Fewer than 8 records | All five | `insufficient_sample` |
| The judge fails 3 times (the backend tries again in the next cycles) | The four judge metrics | `judge_failed` |
| No approved task description | The four judge metrics | `task_description_missing` |
| All `latency_s` values are `null` | `p95_latency_s` only. The rollup ignores it. | `latency_not_reported` |

**The judge**
- Model: `claude-haiku-4-5` (`LLM_JUDGE_MODEL`). One call for each record.
- For each record, the judge gives four results: `groundedness`, `relevance`, `hallucination` and `pii`. The judge identity is stored with each score.
- The judge prompt uses the **task description** of the use case from the YAML registry, for example "summaries of customer invoices". RAI approves each task description. Now, the prompt of the prototype says "telecom support chatbot".
- If the backend cannot reach the Anthropic API, the judge is a local model on the on-premises server. RAI compares its scores with the Claude scores on a sample before use. Thai text needs special care.
- The offline heuristic judge is never used in production. It gives wrong scores for Thai text.

## The data that the GCP job sends

The job sends one JSON body for each completed run, after the publish step. The trace ID is
**not** in the body. It goes in the `traceparent` HTTP header, which the OTel SDK adds (S1-05).

**Run identity.** The dashboard needs it to show the run.

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | `"batch-run/1"` |
| `use_case_id` | Yes | The ID of the use case in the YAML registry |
| `run_id` | Yes | A stable ID of this run. The same run always sends the same ID. |
| `status` | Yes | `completed`, `partial` or `failed` |
| `completed_at` | Yes | The time when the job published the results (UTC, ISO 8601) |
| `request_count` | Yes | The number of requests in the run |
| `failed_count` | Yes | The number of requests that gave no usable output |
| `model` | Yes | The Gemini model ID of the run |
| `sample` | Yes | `{"method": "uniform_random", "size": n}`: how the job selected the records |
| `records` | Yes | The sampled records. Empty in identity-only mode, or when `request_count` is 0. |
| `records_reason` | Only when `records` is empty and `request_count` is not 0 | `records_not_approved` |

**Records.** The metrics need them. The field names are the same as in the contract v1.1
`Trace` record, so the shared judge code reads them without a change.

| Field | Required | Used by | What to put in it for a batch job |
|---|---|---|---|
| `record_id` | Yes | Identity | The ID of the request in the run. It is not a customer ID. The judge uses it as `trace_id`. |
| `question` | Yes | relevance, groundedness, hallucination | The instruction that the model got, without the source material. PII replaced by placeholders. |
| `answer` | Yes | The four judge metrics | The output of the model for this request. PII replaced by placeholders. |
| `retrieval_context` | Yes, can be `[]` | groundedness, hallucination | The source material that the model got, as `[{"doc_id", "title", "text"}]`. For example, the document that the model summarized. PII replaced by placeholders. |
| `tool_calls` | No | groundedness | Only if the job uses function calls: `[{"name", "output"}]` |
| `refused` | Yes | groundedness, hallucination | `true` if the model declined or was blocked: a safety finish reason, a blocked prompt, or a clear refusal |
| `latency_s` | No, never `0` | p95_latency_s | The real time of the request in seconds. **`null` for the Gemini Batch API**, because it has no time for each request. |

**Not sent**, because no metric uses it: customer IDs, token counts (they go in the OTel
spans), system prompts, topics, raw files, outputs that are not in the sample, and all
other fields. The API rejects unknown fields.

### Sample size

| Setting | Value |
|---|---|
| Records for each run | Default **50**. Set for each use case in the YAML registry, from 8 to 200. |
| Selection | Uniform random. For online jobs, select the sample before the calls start (S2-04). If the run has fewer requests than the sample size, send all of them. |
| Judged by the backend | All the records that the job sends |
| Cost | 50 judge calls for each run. With 10 use cases, approximately 500 calls in a daily cycle. |

### Identity-only mode

The setting `SEND_RECORDS` in the GCP job controls the records. Until security approves the
records (S1-08), the setting is off:
- The job sends the run identity with `records: []` and `records_reason: records_not_approved`.
- No text leaves GCP.
- The backend stores the run and an evaluation with all five metrics "Unknown".
- The delivery, the delivery alerts and the trace work. The quality grade does not work.

A use case in identity-only mode does **not** pass the release (S4-03).

### Latency for batch jobs

The Gemini Batch API returns the results some hours later, and it has no time for each
request. For these jobs, `latency_s` is `null`. The backend counts the missing values as
`latency_missing`, and `p95_latency_s` is "Unknown" with `latency_not_reported`. The
rollup ignores it. Jobs that call Gemini online send the real time. The time of the job
steps goes in the OTel spans, not in this metric.

### PII: placeholders instead of raw values

PII means "personally identifiable information": data that can identify a person.
Contract v1.1 section 13 requires that the sender removes PII from free text. But if the
job removes the PII from the answer completely, `pii_exposure_rate` can never find a leak.
Thus:

| Step | Where | What happens |
|---|---|---|
| 1 | GCP job, before it sends | Replace each phone number, email address and national ID number in `question`, `answer` and `retrieval_context` with `[PHONE]`, `[EMAIL]` or `[NATIONAL_ID]` |
| 2 | Backend | The `pii` of a record is true if its `answer` contains a placeholder, **or** if the judge finds PII that the redaction did not replace |
| 3 | Backend | `pii_exposure_rate` = the part of the records with `pii` true |

Raw PII never leaves GCP, and the metric still counts the leaks. A placeholder in `question`
or `retrieval_context` does not count, because the input can contain customer data. Security
approves this method and the list of PII types (S1-08). If security adds more types, the job
must find them before it sends the data.

## Example

HTTP header:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

Body:

```json
{
  "schema_version": "batch-run/1",
  "use_case_id": "GCP-UC-03",
  "run_id": "invoice-summary-2026-10-07",
  "status": "completed",
  "completed_at": "2026-10-07T02:15:00Z",
  "request_count": 1840,
  "failed_count": 3,
  "model": "gemini-2.5-flash",
  "sample": {"method": "uniform_random", "size": 50},
  "records": [
    {
      "record_id": "req-000412",
      "question": "Summarize this invoice in two sentences for the billing team.",
      "answer": "The invoice bills [EMAIL] for 3 months of fibre service. The total due is 1,497 THB by 15 October.",
      "retrieval_context": [
        {"doc_id": "inv-88213", "title": "Invoice 88213", "text": "Customer contact: [EMAIL] ... Fibre 1 Gbps x 3 months ... Total 1,497.00 THB ... Due 2026-10-15"}
      ],
      "refused": false,
      "latency_s": null
    }
  ]
}
```

This example is not real data. The use-case ID, the model and the values are examples. For
this record, `pii` is true, because the answer repeats the email address of the customer.

## Where the data goes

| Data | PostgreSQL (monitor) | Judge | Langfuse | Dashboard |
|---|---|---|---|---|
| Run identity | `batch_runs` | No | Attributes of the trace | Yes |
| Redacted records | Inside the run in `batch_runs`. Never changed. Kept for the retention period. | Yes | Input and output of each record observation under `monitor.evaluate` | **No** |
| The four judge results of each record | `batch_record_judgments` | — | Scores on each record observation | No |
| The five metrics and the grade | `batch_evaluations` | — | Scores on the trace | Yes |
| Step times and token totals | No | No | GCP spans, through the Collector. **No text.** | No |

Rule for text in spans: GCP spans never contain text. Only the backend spans can contain the
redacted record text, after the API accepted it.

## Changes to the shared prototype code

| Area | Change | Issue |
|---|---|---|
| Judge prompt | Uses the task description of the use case | S2-05 |
| PII | A placeholder in the answer counts as exposure, together with the judge | S2-05 |
| Sample cap | The judge cap is the sample size from the YAML registry | S2-05 |
| Judge retry | Up to 3 tries in the next cycles | S2-05 |
| Input shape | Batch records become v1.1 `Trace` records (`record_id` becomes `trace_id`) | S1-02, S2-05 |
| Metrics, bands, grades, minimum sample | **No change** | — |

The prototype use cases are not configured on the test host or on AWS. The code that only
the prototype uses is removed in S4-07.

## Open decisions

| Decision | Owner | Needed by | If it is late |
|---|---|---|---|
| Redacted records can leave GCP for the backend, the judge and Langfuse | Security | 8 October (S1-08) | Identity-only mode. The use case cannot pass the release. |
| The placeholder method and the list of PII types | Security + RAI | 8 October (S1-08) | Identity-only mode |
| Default sample size of 50 and the judge budget | RAI + project owner | 9 October | Use the prototype default of 20 |
| The task description of each use case | RAI + owner of the use case | Before the use case is onboarded | Its judge metrics are "Unknown" |
| Band changes | RAI (AI Council defaults) | Before the use case is onboarded | The defaults apply |
