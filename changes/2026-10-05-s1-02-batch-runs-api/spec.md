# Spec: `POST /api/batch/runs` (S1-02)

Source: [issue #4](https://github.com/tkhongsap-io/model-monitoring-prototype/issues/4),
[S1-01 draft schema](../2026-10-02-batch-monitoring-mvp/schema/README.md).

## Request

| Part | Rule |
|---|---|
| Method and path | `POST /api/batch/runs`. Available in demo mode and in strict live mode. |
| `Authorization` | `Bearer <key>`. Required. |
| `traceparent` | Optional W3C trace context header. |
| `Content-Type` | JSON body, `batch-run/1`. |
| Body size | Not more than `BATCH_MAX_BODY_BYTES` (default 10 MB). |

## Order of checks and responses

| Step | Check | Failure |
|---|---|---|
| 1 | The SHA-256 hash of the key is in `BATCH_API_KEY_SHA256` | `401`, nothing stored |
| 2 | Body size | `413`, nothing stored |
| 3 | Body is valid JSON and agrees with `batch-run/1` (schema and backend rules below) | `400` with `errors: [{loc, msg, type}]`, nothing stored |
| 4 | `use_case_id` of the body is the use case of the key | `403`, nothing stored |
| 5 | `(use_case_id, run_id)` is new | `201`, one row stored |
| 5 | Same pair, same content digest | `200`, no change |
| 5 | Same pair, other content digest | `409`, the first row does not change |

The `400` errors never echo the input value (the body can contain redacted text).

## Authentication

- `BATCH_API_KEY_SHA256`: comma-separated `USE_CASE_ID:<64 hex>` entries. Each entry is
  the lowercase hex SHA-256 of the UTF-8 key. Two entries for one use case are allowed
  (key rotation, S2-01).
- The backend hashes the supplied key and compares it with every configured hash with
  `hmac.compare_digest`. It does not stop at the first match.
- No configured hash: every request is `401` (fail closed).
- A malformed entry is ignored and reported by `GET /api/readiness` in strict live mode,
  by its position only (never its value).

## Validation (`backend/app/batch_schema.py`)

All JSON Schema rules of `batch-run-1.schema.json`, with strict types (`"1840"` is not an
integer, `1` is not a boolean) and `extra="forbid"` at every level. Plus the backend rules
from the schema README:

- `failed_count` ≤ `request_count`.
- Number of records ≤ `sample.size` and ≤ `request_count`.
- `record_id` is unique in the run.

Deferred to S2-01: the per-use-case sample-size range from the registry.

## Trace ID

Parse `traceparent` as `version-traceid-parentid-flags` (W3C Trace Context level 1):
two lowercase hex digits for the version (not `ff`), 32 hex for the trace ID (not all
zero), 16 hex for the parent ID (not all zero), two hex for the flags. Version `00` must
have exactly four parts. If the header is valid, store its trace ID with
`trace_id_source = "traceparent"`. If it is missing or invalid, store a new random trace
ID with `trace_id_source = "generated"`. S1-05 part B replaces this parser with the OTel
context; the column stays.

## Storage: `batch_runs` (migration 8)

| Column | Content |
|---|---|
| `batch_run_id` | Primary key, UUIDv5 of `use_case_id/run_id` |
| `use_case_id`, `run_id` | Unique together |
| `schema_version`, `status`, `completed_at`, `request_count`, `failed_count`, `model`, `sample_method`, `sample_size`, `records_reason` | Copied from the body for queries |
| `record_count` | Number of records |
| `content_sha256` | SHA-256 of the canonical JSON of the body (sorted keys, no spaces) |
| `payload` | The canonical JSON of the body, records in arrival order with `record_id` |
| `trace_id`, `trace_id_source` | From the trace ID step |
| `received_at` | Server time of the first store |

No code path updates or deletes a `batch_runs` row.

## Response body

`{"status": "created" | "duplicate", "batch_run_id", "use_case_id", "run_id",
"record_count", "trace_id", "received_at"}`. A duplicate returns the stored values.

## Logging

One line per request: outcome, `use_case_id` and `run_id` when known, record count and
trace ID. Never the key, the `Authorization` header, or the body.
