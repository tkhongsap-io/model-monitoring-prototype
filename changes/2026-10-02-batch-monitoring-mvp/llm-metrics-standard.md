# LLM Metrics and Data Standard for GCP Batch Use Cases

| | |
|---|---|
| **Status** | Draft for review (decided direction 2026-10-03) |
| **Applies to** | All 10 GCP batch use cases that call Gemini |
| **Related** | [Plan](plan.md) · [Summary](summary.md) · [Issues](issues.md) · [Monitoring contract v1.1](../../docs/MONITORING-CONTRACT.md) |

## Decision

Every GCP batch use case is evaluated with the **same five LLM metrics the current
prototype uses** for the support chatbot (`AICT-L02`). GCP jobs send **only the data
those metrics need**. No use case gets its own metric set in October.

This keeps one definition of "good" across all use cases. It also lets the monitor reuse
the prototype's judge, aggregation and grading code
(`backend/app/adapters/llm_eval/live_http.py`, `backend/app/engines/health.py`) instead
of building new evaluators.

## The five metrics

These come from contract v1.1 §9 and §11 and the prototype code. Bands are the AI Council
defaults. A use case may override a band only with RAI sign-off, recorded in the registry.

| Metric | Lane | What it means | How it is computed per run | Green | Amber | Red |
|---|---|---|---|---|---|---|
| `hallucination_rate` | Quality | Share of answers that state facts not supported by the source material, instead of declining | Judge marks each answer true or false; average | < 0.02 | — | ≥ 0.02 |
| `groundedness` | Quality | How fully each claim is supported by the source material (a correct refusal counts as fully grounded) | Judge scores 0–1; average | ≥ 0.85 | 0.70–0.85 | < 0.70 |
| `relevance` | Quality | How well the answer addresses the task it was given | Judge scores 0–1; average | ≥ 0.85 | 0.70–0.85 | < 0.70 |
| `pii_exposure_rate` | Safety & security | Share of answers that expose a phone number, email or national ID | See [PII](#pii-placeholders-instead-of-raw-values); average | 0.0 | above 0 and below 0.01 | ≥ 0.01 |
| `p95_latency_s` | Reliability | 95th percentile of per-request wall time | Not judged; percentile over records that carry `latency_s` | ≤ 4.0 s | 4.0–8.0 s | ≥ 8.0 s |

**Grading rules (unchanged from the prototype)**
- Red is checked first. A missing value is **Unknown**, never Green.
- Rollup is worst-of: metric, then lane, then overall.
- The Feedback and Drift lanes do not apply to these use cases. They are set to Unknown
  with a declared reason and excluded from the rollup.
- Fewer than **8** records in a run: all five metrics are Unknown with reason
  `insufficient_sample`.
- Judge call fails in strict live mode: the judged metrics are Unknown. The offline
  heuristic judge is never used in production; it also mis-scores Thai text.

**Judge (unchanged from the prototype)**
- Model: `claude-haiku-4-5` (`LLM_JUDGE_MODEL`), one call per judged record.
- For each record it returns four fields: `groundedness`, `relevance`, `hallucination`
  and `pii`. The judge model ID is stored with every score.
- One change for batch: today the judge prompt says "telecom support chatbot". It will
  take a short **task description** per use case from the registry (for example
  "summaries of customer invoices"). The four judgments and their definitions stay the
  same. RAI approves each task description.

## Data the GCP job sends

The job sends one JSON body per completed run, after publishing. The body has two parts.

**Run identity** — needed to show the run on the dashboard:

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | Yes | `"batch-run/1"` |
| `use_case_id` | Yes | Registry ID of the use case |
| `run_id` | Yes | Stable ID of this run; the same run always sends the same ID |
| `status` | Yes | `completed`, `partial` or `failed` |
| `completed_at` | Yes | When results were published (UTC, ISO 8601) |
| `request_count` | Yes | Requests in the run |
| `failed_count` | Yes | Requests that returned no usable output |
| `model` | Yes | Gemini model ID that served the run |
| `traceparent` | Yes | W3C trace context of the job's OTel trace |
| `sample` | Yes | `{"method": "uniform_random", "size": n}`: how the records were picked |
| `records` | Yes | The sampled records below (empty only when `request_count` is 0) |

**Records** — a sample of requests, needed to compute the five metrics. Field names match
the contract v1.1 `Trace` record, so the prototype's judge reads them unchanged.

| Field | Required | Used by | What to put in it for a batch job |
|---|---|---|---|
| `record_id` | Yes | Identity | Request ID within the run. Not a customer ID. Stored as `trace_id` for the judge. |
| `question` | Yes | relevance, groundedness, hallucination | The instruction the model was given, without the source material. PII replaced by placeholders. |
| `answer` | Yes | All four judged metrics | The model's output for this request. PII replaced by placeholders. |
| `retrieval_context` | Yes, may be `[]` | groundedness, hallucination | The source material given to the model, as `[{"doc_id", "title", "text"}]`, for example the document being summarized. PII replaced by placeholders. |
| `tool_calls` | No | groundedness | Only if the job uses function calling: `[{"name", "output"}]` |
| `refused` | Yes | groundedness, hallucination | `true` if the model declined or was blocked (safety finish reason, blocked prompt, or an explicit decline) |
| `latency_s` | No | p95_latency_s | Real per-request wall time in seconds. **`null` for the Gemini Batch API**, which has no per-request time. Never `0`. |

**Not sent**, because no metric uses it: customer IDs, token counts (they go in OTel
spans), system prompts, topics, raw files, output beyond the sample, and any field not
listed above. The receiving API rejects unknown fields.

### Sample size

| Setting | Value |
|---|---|
| Records per run | Default **50**, set per use case in the registry, between 8 and 200 |
| How they are picked | Uniform random over the run's requests. If the run has fewer requests than the sample size, send all of them. |
| Judged by the monitor | Every record sent. For batch runs `LLM_JUDGE_MAX_TRACES` equals the sample size (today's default is 20). |
| Cost | 50 Haiku calls per run; with 10 use cases, about 500 judge calls per daily cycle |

### Latency for batch jobs

The Gemini Batch API returns results hours later and has no per-request latency. For
those jobs, `latency_s` is `null`. The prototype already handles this: missing values are
excluded and counted as `latency_missing`, and with no values `p95_latency_s` is Unknown
with a declared reason, excluded from the rollup. Jobs that call Gemini online send the
real wall time. Job duration and step timings go in OTel spans, not in this metric.

### PII: placeholders instead of raw values

Contract v1.1 §13 requires the sender to redact free text. But if the job removes PII from
the answer completely, `pii_exposure_rate` can never detect a leak. The proposed fix:

| Step | Where | What happens |
|---|---|---|
| 1 | GCP job, before sending | Replace each phone number, email and national ID in `question`, `answer` and `retrieval_context` with a typed placeholder: `[PHONE]`, `[EMAIL]`, `[NATIONAL_ID]` |
| 2 | Monitor | A record's `pii` is true if its `answer` contains a placeholder **or** the judge flags PII the redaction missed |
| 3 | Monitor | `pii_exposure_rate` = share of records with `pii` true |

Raw PII never leaves GCP, and the metric still counts leaks. Placeholders in `question` or
`retrieval_context` do not count, because the input is allowed to contain customer data.
**Security must approve this** (issue S1-09).

## Example body

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
  "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
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

This example is illustrative: the use case ID, model and values are placeholders. With
this record, `pii` is true because the answer repeats the customer's email.

## Where the data goes

| Data | Monitor Postgres | Claude judge (Anthropic API) | Langfuse | OTel spans |
|---|---|---|---|---|
| Run identity | Yes | No | Trace attributes | Yes |
| Redacted records | Yes, inside the stored run; never edited; kept for the registry retention period | Yes, judged records only | Judged records, with their scores (subject to S1-09) | **No.** Spans never carry text. |
| Scores and metrics | Yes | — | Yes, scores on the run's trace | No |

## What this changes in the prototype

| Area | Change | Issue |
|---|---|---|
| Judge prompt | Takes a per-use-case task description instead of the fixed chatbot sentence | S2-06 |
| PII | Placeholder in the answer counts as exposure, in addition to the judge | S2-06 |
| Sample cap | Batch runs use the registry sample size as the judge cap | S2-06 |
| Input shape | Batch records mapped to the v1.1 `Trace` shape (`record_id` stored as `trace_id`) | S1-03, S2-06 |
| Metrics, bands, grading, minimum sample | **No change** | — |

The three live use cases and contract v1.1 are not affected.

## Open decisions

| Decision | Owner | Needed by | If late |
|---|---|---|---|
| Redacted text may leave GCP for the monitor, the Claude judge and Langfuse | Security | Thu Oct 8 | Send run identity only; the four judged metrics are Unknown; the run still counts |
| Placeholder approach for PII | Security + RAI | Thu Oct 8 | `pii_exposure_rate` relies on the judge alone, over fully redacted text, and is reported as limited |
| Default sample size 50 and judge budget | RAI + project owner | Fri Oct 9 | Use the prototype default of 20 |
| Task description for each use case | RAI + source owner | Before that use case is onboarded | Its judged metrics are Unknown until approved |
| Any band override | RAI (AI Council defaults) | Before onboarding | Defaults apply |
