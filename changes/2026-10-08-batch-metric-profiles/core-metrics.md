# Batch MVP metrics: core set for all use cases, and one profile for each task type

| | |
|---|---|
| **Status** | Draft 2026-10-08. The project owner approved the direction: use metrics that fit each use case, not the chatbot metrics for all. The bands are proposals for RAI. |
| **Replaces** | The rule "the same five LLM metrics for all use cases" in [`llm-metrics-standard.md`](../2026-10-02-batch-monitoring-mvp/llm-metrics-standard.md). The five metrics stay, but only for the "generation from text" profile. |
| **Related** | [Use-case template for GCP developers](use-case-template.md) · [Issues](../2026-10-02-batch-monitoring-mvp/issues.md) · S1-01 (#3), S1-09 |
| **Language** | ASD-STE100 (Simplified Technical English), about 80% strict |

## Why the plan changes

The standard used the five metrics of the prototype chatbot (`AICT-L02`) for all 10 GCP use
cases. The first real GCP job showed that this does not fit:

- All 10 use cases are **batch inference with one turn**: one prompt in, one answer out.
- The first job is a **fraud classifier**: a fixed prompt, 3 images, and a fixed JSON
  answer. It has no source text, so the judge cannot check `groundedness` or
  `hallucination_rate`. The judge also cannot see the images.

The type of task decides which metrics work, not the number of turns. Thus each use case
gets the **core metrics** (section 1) and **one quality profile** for its task type
(section 2).

## 1. Core metrics (all 10 use cases)

The core metrics need no judge, no labels from people, and almost no text. Most of them work
also in identity-only mode (`records: []`), before security approves the records (S1-08).

| Lane | Metric | Calculation | Data | Works in identity-only mode | Green | Amber | Red |
|---|---|---|---|---|---|---|---|
| Delivery (S3-02) | Run on time | The run arrived before `expected_every` + `grace` (registry) | Arrival time, `status` | Yes | On time | `status: partial` | Missing, or `status: failed` |
| Delivery | `turnaround_s` | `completed_at` − `submitted_at`. **Needs the new field `submitted_at`** (section 4). | Body | Yes | ≤ registry limit | ≤ 2 × limit | > 2 × limit |
| Reliability | `failure_rate` | `failed_count / request_count` | Body | Yes | < 0.01 | 0.01 to 0.05 | ≥ 0.05 |
| Reliability | `volume_change` | `request_count` / median `request_count` of the last 5 runs | Body + history | Yes | 0.7 to 1.3 | 0.4 to 0.7 or 1.3 to 2.0 | < 0.4 or > 2.0 |
| Output | `valid_output_rate` | The part of the not-refused records whose `answer` agrees with the output contract of the use case (section 3) | Records | No | ≥ 0.99 | 0.95 to 0.99 | < 0.95 |
| Output | `block_rate` | The part of the records with `refused: true` | Records | No | < 0.01 | 0.01 to 0.05 | ≥ 0.05 |

All the bands are **proposals**. RAI approves them. A use case can change a band in the
registry, with RAI approval. For example, a fraud classifier can expect more safety blocks.

**`p95_latency_s` is not a core metric.** All 10 jobs use batch inference, and the Gemini
Batch API has no time for each request. `turnaround_s` replaces it. If a job calls Gemini
online, `p95_latency_s` can be an extra metric for that use case.

### When a core metric is "Unknown"

| Condition | Metrics | Reason |
|---|---|---|
| `request_count` is 0 | `failure_rate` | `no_requests` |
| Fewer than 5 earlier runs | `volume_change` | `no_baseline` |
| No `submitted_at` in the body, or no limit in the registry | `turnaround_s` | `not_reported` |
| Identity-only run (`records: []`) | `valid_output_rate`, `block_rate` | `records_not_approved` |
| Fewer than 8 records | `valid_output_rate`, `block_rate` | `insufficient_sample` |

Unknown is never Green. The rules of the prototype stay: Red is examined first, and the rollup
uses the worst value (metric, then lane, then overall). The delivery lane stays separate: it
never changes the quality grade (S3-02).

## 2. Quality profiles (one for each use case)

The use-case template ([use-case-template.md](use-case-template.md)) gives the facts that
select the profile. The registry (S2-01) records the profile of each use case.

| Profile | Input → output | Quality metrics | Judge | Labels from people |
|---|---|---|---|---|
| `classification` | Text or images → one label (JSON) | `label_distribution_change`: the share of each label against the baseline. `confidence_p10`: the 10th percentile of the confidence, if the output has one. Later: `accuracy` against confirmed labels. | No | Needed for `accuracy` only |
| `extraction` | Document, text or images → structured fields (JSON) | `field_completeness`: the part of the required fields that are not empty. `field_format_rate`: the part of the fields with a valid format (date, amount, ID pattern). Later: `field_accuracy` on a reviewed sample. | No | Needed for `field_accuracy` only |
| `generation_from_text` | Text source → free text | `groundedness`, `hallucination_rate`, `relevance`, `pii_exposure_rate`: the current standard | Yes (LiteLLM, S2-09) | No |
| `generation_free` | Instruction only → free text | `relevance`, `pii_exposure_rate` | Yes | No |

Notes:
- **A drift metric shows change, not correctness.** A classifier that is wrong in the same
  way every day stays Green. Only `accuracy` from labels shows correctness. Labels come from
  business outcomes that arrive later (for example confirmed fraud cases), or from a small
  sample that people review. Accuracy is planned **after October**.
- **Baseline.** `label_distribution_change` needs the label shares of the last 5 runs. Until
  then it is "Unknown" (`no_baseline`). A daily job has a baseline after one week. A weekly
  job does not have one in October.
- `pii_exposure_rate` applies to each use case with a free-text field in the output, also in
  a `classification` or `extraction` profile (for example a "reason" field).
- The band proposals for the profile metrics come after the template answers, because they
  depend on the labels and the fields of each use case.

## 3. Output contract (registry)

Each use case with a JSON output declares its output format in the registry (S2-01):

```yaml
use_case_id: GCP-UC-01
profile: classification
output_contract:
  format: json
  required_fields: [label, confidence]
  label_field: label
  labels: [FRAUD, SUSPICIOUS, NORMAL]   # example only
  confidence_field: confidence          # optional
  free_text_fields: [reason]            # optional; these fields get pii_exposure_rate
```

The backend parses `answer` with this contract. `answer` stays a string in the body, so
`batch-run/1` does not change for this.

## 4. Changes to the run summary `batch-run/1`

| Change | Why | Issue |
|---|---|---|
| New optional field `submitted_at` (UTC, ISO 8601): the time when the job submitted the batch | `turnaround_s` needs it. Optional, so that the jobs that do not send it are still valid. | S1-01, S1-02b |
| `retrieval_context` stays `[]` for image input. The system prompt is not sent. `question` is a short instruction with one `[IMAGE]` for each image. | Already decided 2026-10-07 | S1-01 |
| No other change | The core metrics and the profiles use the existing fields | — |

The schema rejects unknown fields. Thus the backend must accept `submitted_at` **before** a job
sends it (S1-02b).

## 5. Effect on the plan

| Issue | Change |
|---|---|
| S1-01 (#3) | Add `submitted_at` to the draft schema. Otherwise no change. |
| S1-09 | The inventory uses the use-case template. The template answers select the profile of each use case. **This is now on the critical path.** |
| S2-01 | The registry gets `profile`, `output_contract`, the `turnaround` limit and the band overrides |
| S2-05 | The evaluator calculates the core metrics for all use cases, and the profile metrics. It calls the judge only for the `generation_from_text` and `generation_free` profiles. New: the baseline of the last 5 runs. |
| S2-07 | The dashboard shows the core lanes and the metrics of each profile |
| S2-09, S2-10 | The judge is necessary only for the generation profiles. If no use case has a generation profile, S2-09 and S2-10 can move after October. |
| S3-02 | No change. It is the delivery lane of the core set. |
| S4-04 | The evidence checklist uses the metrics of the profile of each use case |
| `llm-metrics-standard.md` | Becomes the standard of the `generation_from_text` profile |

**Timeline effect (estimate, for the project owner to confirm):**
- **More work:** the output contract in the registry, the core metrics and the baseline in
  the evaluator, and the profile views in the dashboard. Each of these is about S to M.
- **Less work:** fewer judge calls, and S2-10 becomes smaller, or moves, if few use cases
  have a generation profile.
- **Risk:** the drift metrics are "Unknown" until each use case has 5 runs. Accuracy is not in
  October. The S1-09 answers must arrive before Sprint 2 can be planned again.

## Open decisions

| Decision | Owner | Needed by |
|---|---|---|
| The core bands in section 1 | RAI | Before S2-05 starts |
| The profile of each use case | RAI + use-case owner, from the template answers | S1-09 |
| The baseline: 5 runs, and the limits of the label change | RAI | Before S2-05 starts |
| A label source or a reviewer for accuracy, for each `classification` and `extraction` use case | RAI + use-case owner | After October |
| `submitted_at` in `batch-run/1` | Backend + GCP developers | S1-01 |
