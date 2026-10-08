# S1-01 — Run summary JSON Schema `batch-run/1` (draft)

| | |
|---|---|
| **Status** | Draft 2026-10-05, for review by the GCP job developers. Not yet approved by backend, RAI or security (S1-08). |
| **Schema** | [`batch-run-1.schema.json`](batch-run-1.schema.json) (JSON Schema draft 2020-12) |
| **Examples** | [`examples/valid/`](examples/valid/) (5 files) and [`examples/invalid/`](examples/invalid/) (3 files). All text is synthetic. |
| **Based on** | [LLM metrics and data standard](../llm-metrics-standard.md), [issue S1-01](../issues.md#s1-01--map-one-gcp-job-and-write-the-json-body-v1) |

## What the GCP developer does

1. Read the schema. Each `description` that starts with **"SOURCE: GCP job developer to fill in"** needs
   your answer: where the value comes from in your job (file, function, variable).
2. Answer the questions below, in the pull request or as comments on the issue.
3. Build one body from a real run of your job (with synthetic or redacted text) and check it
   with the schema. Any JSON Schema 2020-12 validator works, for example Python `jsonschema`:

   ```bash
   python -c "import json,jsonschema; jsonschema.Draft202012Validator(json.load(open('batch-run-1.schema.json'))).validate(json.load(open('my-body.json')))"
   ```

## Share a real body without its text

A real body can contain customer data. Before you share it, or give it to Claude, remove
the free text. Put the file in `data/` (git ignores it), then run this from the
repository root:

```bash
python scripts/strip_record_text.py data/<file>.json
```

The script writes `data/<file>.stripped.json`. In the copy, `question`, `answer`,
`retrieval_context[].title/text` and `tool_calls[].output` become
`[REMOVED <n> chars <placeholder counts>]`, for example `[REMOVED 142 chars [EMAIL]x1]`.
All other values do not change. The script prints only counts, never text. Share only
the `.stripped.json` file. It keeps the lengths and the placeholder counts, so the
schema checks and the PII rule can still be examined.

## Shape at a glance

```
HTTP header   traceparent: 00-<trace-id>-<span-id>-01      (added by the OTel SDK, S1-05)
Body
├─ schema_version   "batch-run/1"
├─ use_case_id      registry ID
├─ run_id           stable per run (idempotency key with use_case_id)
├─ status           completed | partial | failed
├─ submitted_at     optional; UTC, ends in Z; not later than completed_at
├─ completed_at     UTC, ends in Z
├─ request_count, failed_count
├─ model            Gemini model ID
├─ sample           { method: "uniform_random", size: 1..200 }
├─ records[]        0..200, redacted
│   ├─ record_id, question, answer, refused, latency_s (number > 0 or null)
│   ├─ retrieval_context[]  { doc_id, title, text }
│   └─ tool_calls[]         { name, output }      (optional)
└─ records_reason   only when records is empty and request_count > 0
```

## Rules in the schema

- Unknown fields are rejected at every level (`additionalProperties: false`). There is no
  customer ID field and no trace field.
- Free text only in `question`, `answer`, `retrieval_context[].title/text` and `tool_calls[].output`.
- `latency_s` is required and is either a number above 0 or `null`. Never `0`.
- `answer` can be empty only when `refused` is `true`.
- `request_count: 0` means `records: []`.
- `records: []` with `request_count > 0` needs `records_reason`. Records present means no `records_reason`.
- `status: failed` means `records: []` and `records_reason: job_failed`.

## Clarifications after the first GCP example (2026-10-07)

The first real body from a GCP job (a fraud validation job, `request_count` 243,
`failed_count` 106, 8 records) agreed with the field shape. Its values showed these
points. The schema descriptions now state each rule.

| Topic | Rule |
|---|---|
| `request_count` | **All** requests sent to Gemini: successful + failed, each request one time, no retries. `failed_count` is a part of it. **Correction 2026-10-08:** the job already counted this way. In the first example, 243 = 137 successful + 106 failed. An earlier version of this README said "349", which was a mistake of the monitor team. |
| `record_id` | The row number of the input (`req-<row>`), not a request counter. Rows that make no request (no photo, fewer than 3 photos, a storage error) leave gaps, so an ID can be larger than `request_count`. This is correct. |
| Sample | Sample only from the requests that Gemini answered or refused. Never include a failed request. In an online job, every sampled record then has a `latency_s`. |
| `sample.size` | The `SAMPLE_SIZE` setting (confirmed), not `len(records)` |
| `retrieval_context` | Any input text that the answer must agree with: a document, a transaction, a complaint, OCR text, retrieved chunks. Not only for document retrieval. |
| Image input (Gemini reads the image directly) | `question` is the text instruction with `[IMAGE]` where each image was. `retrieval_context` is `[]` if the prompt has no other text. Never send the image, base64 data or an image URL. |

`[IMAGE]` is not a PII placeholder. It does not count for `pii_exposure_rate`. For a use
case with image input only, the judge has no source material, so `groundedness` and
`hallucination_rate` have no useful meaning. RAI decides how to treat them for that use
case in the registry (S2-01).

### `retrieval_context` examples (synthetic)

| Case | Item |
|---|---|
| Document summary | `{"doc_id": "inv-88213", "title": "Invoice 88213", "text": "Customer contact: [EMAIL]. Total 1,497.00 THB."}` |
| Transaction check | `{"doc_id": "req-000047-input", "title": "Transaction", "text": "Amount 45,000 THB; channel card-not-present; device new"}` |
| Complaint | `{"doc_id": "cmp-5521", "title": "", "text": "No signal since Monday. Call me at [PHONE]."}` |
| OCR step before Gemini | `{"doc_id": "req-000047-ocr", "title": "Invoice scan (OCR)", "text": "INVOICE No. INV-88213 Total 1,497.00 THB"}` |
| Retrieved chunk | `{"doc_id": "kb-roaming-004#2", "title": "Roaming packages", "text": "Asia roaming pack 399 THB, 7 days."}` |
| Image only, or no source material | `[]` |

If the input has no document ID, use `<record_id>-input`. Never use a customer, card,
account or phone number as `doc_id`.

## Rules the backend checks (JSON Schema cannot express them)

The backend (S1-02) returns `400` for these:

| Rule | Why |
|---|---|
| `failed_count` ≤ `request_count` | Counts must agree |
| `submitted_at` is not later than `completed_at`; if the field is present, it is not `null` | Turnaround cannot be negative |
| Number of records ≤ `sample.size` and ≤ `request_count` | The job sent more than it sampled |
| `record_id` is unique in the run | The judge stores one result for each record |
| `sample.size` is in the registry range of the use case (8 to 200) | Registry setting (S2-01) |
| `use_case_id` is the use case of the API key | One key cannot write for another use case |
| Total body size ≤ limit (proposed 10 MB) | Protect the API |

## Added 2026-10-08: `submitted_at` (optional)

The time when the job submitted the batch to Gemini. The core metric `turnaround_s`
(`completed_at` − `submitted_at`) needs it; see
[core metrics](../../2026-10-08-batch-metric-profiles/core-metrics.md). It replaces the time
of each request, which the Gemini Batch API does not have. A job that does not send it is
still valid, and `turnaround_s` is "Unknown". The backend accepts the field from this
change on. **Send it only after this change is deployed to the test host**, because an
older backend rejects unknown fields with `400`.

## Changes from the standard (please confirm)

| Change | Reason |
|---|---|
| `latency_s` is **required** (value or `null`), not optional | An explicit `null` shows that the job knows it has no time. A missing field is more likely a bug. |
| New `records_reason: job_failed` for `status: failed` | The standard allows only `records_not_approved`, but a failed run with requests also has no records. |
| Length limits: `question`/`answer` 32,000 chars, `retrieval_context` 20 items × 64,000 chars, `title` 512, records 200 | Proposed. Tell us if your real prompts or documents are longer. |
| `retrieval_context[].score` and `tool_calls[].input` from contract v1.1 are not included | No metric uses them (standard: "send only the data that these metrics need"). |

## Questions for the GCP developers

**Job and run**
1. Where does the job publish the results (file and function)? The send step comes after this point.
2. What is a stable `run_id` for your job? If the job is run again for the same business date, must it be the same run or a new run?
3. Does the job use the Gemini **Batch API** (then `latency_s` is `null`) or online calls? If online, can you measure the time of each call?
4. Is `model` one value for the whole run? Does the job call more than one model (for example a fallback model)?

**Prompt mapping**
5. Which part of the prompt is the instruction (`question`)? Which part is the source material (`retrieval_context`)? Is there a system prompt that you leave out?
6. If one request has more than one source document, how do you split them into `retrieval_context` items? What is a good `doc_id`?
7. Does the job use function calls (`tool_calls`)?

**Status and counts**
8. When is a run `completed` and when `partial`? Our draft: `partial` = the job published, but some requests gave no usable output. Is a run with a few failed requests `completed` or `partial` in your job?
9. What counts as a failed request in `failed_count`: API error, timeout, empty output, output that does not parse? Do you retry a request before you count it as failed?
10. Do you sample from all requests, or only from the requests with an output? (Our proposal: from all requests that reached the model, so that refusals are in the sample. Failed requests with no output are not sent.)

**Refusals and safety**
11. How does the job see a refusal or a safety block? Which `finishReason` and `promptFeedback.blockReason` values occur? Is there a refusal text in your prompt rules?

**PII**
12. Where can PII occur: in the input data, in the documents, in the output? Which types (phone, email, national ID, other)? The redaction in S1-03 must cover all these locations.

**Failure and logs**
13. When the job fails, can it still send a run summary with `status: failed`? What `request_count` can it report then?
14. Does the job write a log entry for its own team when the job fails and when a send fails? The monitor team does not need access to these logs (decided 2026-10-07). The monitor sees failures only through the body and the OTel spans (`batch.send`, `batch.run`) with an error status (S1-05).

## How to test (from the issue)

1. Unit: `pytest` checks each file in `examples/valid/` passes and each file in
   `examples/invalid/` fails (added with S1-02 when the schema moves to the backend).
2. Paired with S1-03: build a body from a real run and check it with the schema.
