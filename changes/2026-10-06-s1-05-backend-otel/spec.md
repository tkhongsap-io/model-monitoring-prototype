# Spec: backend OpenTelemetry for batch runs (S1-05 part B)

## Packages

| Package | Range | Status |
|---|---|---|
| `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` | `>=1.45,<2` | Already in `requirements.txt` (S2-02, #40) |
| `opentelemetry-instrumentation-fastapi` | `>=0.66b0,<0.67` | Approved 2026-10-05 (S2-02 spec). Added by this change. |

No other package. No paid service.

## Component 1: `backend/app/tracing.py`

`build_provider(environ) -> TracerProvider | None`, `setup(app) -> None`,
`tracer() -> Tracer`, `shutdown() -> None`, and the module value `PROVIDER`. Tests attach
an in-memory exporter to `PROVIDER` (a `spans` fixture) instead of an `exporter` argument.

1. If `OTEL_SDK_DISABLED` is `true`, do nothing.
2. Make one `TracerProvider` with these resource attributes:
   - `service.name`: `OTEL_SERVICE_NAME`, default `model-monitor`
   - `service.version`: `config.BUILD_SHA`
3. Add the span processor:
   - Else, if `OTEL_EXPORTER_OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` is
     set: a `BatchSpanProcessor(OTLPSpanExporter())`. The exporter reads the standard
     `OTEL_EXPORTER_OTLP_*` variables.
   - Else: no processor. The spans and the trace IDs exist, but nothing is exported.
4. Set the provider as the global provider. Do this one time for each process.
5. Call `FastAPIInstrumentor.instrument_app(app, tracer_provider=..., excluded_urls=...)`.
   The exclude pattern matches every path except `/api/batch/runs`.
   Before this, turn off the native telemetry of FastAPI 0.142 on the app (it traces
   every route when a global provider exists), also when the SDK is disabled.
6. If a step raises, log one error (no secret, no header value) and continue without
   tracing.

At app shutdown, call `provider.shutdown()`. The export of the remaining spans has a
time limit, so a stop cannot hang.

`main.py` calls `tracing.setup(app)` one time, after the app is made.

## Component 2: `backend/app/api/batch_routes.py`

- Remove `parse_traceparent`. The FastAPI instrumentation reads the `traceparent` header.
- The whole handler runs in a span `monitor.ingest` (kind `INTERNAL`). Its parent is the
  FastAPI server span `POST /api/batch/runs`.
- Trace ID: the trace ID of the `monitor.ingest` span context, as 32 lowercase hex digits.
  If the span context is not valid (tracing is off or failed), use a random 32-hex ID, as
  S1-02 does now.
- `trace_id_source`:
  - `traceparent`, if the request had a valid incoming W3C trace context
  - `generated`, in all other cases
- A duplicate (`200`) returns and keeps the stored trace ID of the first request. Its
  `monitor.ingest` span has the trace ID of the resend.
  - A retry inside the same job execution has the same trace ID, because it is a second
    client span under the same `batch.send`.
  - A new job execution with the same `run_id`, or a first request without
    `traceparent`, has a different trace ID. The attribute `stored_trace_id` (below)
    connects the two traces. A `409 conflict` works the same way. (Decided 2026-10-06.)
- `db.BatchRunConflict` gets the attribute `stored_trace_id`, which `put_batch_run` sets
  from the existing row. The handler needs no second query. No migration.

### `monitor.ingest` attributes

| Attribute | When |
|---|---|
| `outcome` | Always. One of `created`, `duplicate`, `conflict`, `invalid`, `unauthorized`, `forbidden`, `too_large`. |
| `use_case_id`, `run_id` | After the body passed the validation |
| `record_count` | For `created` and `duplicate` |
| `stored_trace_id` | For `duplicate` and `conflict`: the trace ID in the stored `batch_runs` row. It can be the same as the span's own trace ID. |

Never in a span: the key, the key hash, the `Authorization` header, the body, a record
field, or a field value from a validation error. Header capture of the FastAPI
instrumentation stays off.

The span status stays unset for a `4xx` result. A `4xx` is a correct answer to a wrong
request. An unexpected exception sets the status to `ERROR`.

## Trace shape

```
batch.run → batch.send → HTTP client span      (GCP job, part A)
  → POST /api/batch/runs (server span)         (backend)
    → monitor.ingest                           (backend)
```

## Errors

| Case | Result |
|---|---|
| Collector down or slow | The batch processor drops the spans and logs a warning. The request does not wait. The run is stored. |
| Bad `OTEL_*` setting | `setup` logs one error. The app starts without tracing. Runs get a generated trace ID. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` not set | Not an error. Not a readiness or strict-live condition. |

## Plan text changes

In `changes/2026-10-02-batch-monitoring-mvp/issues.md`:

- S1-05: step 4 and the part B acceptance criterion say that the server span is a child of
  the job's HTTP client span, and `monitor.ingest` is a child of the server span.
  `batch.send` is an ancestor of `monitor.ingest`.
- S1-07: the "Parent link" row becomes "Ancestor link". The script follows the parent IDs
  in the Collector file from `monitor.ingest` up to `batch.send`. If no `batch_runs` row
  has the trace ID, but a `monitor.ingest` span with this trace ID has `stored_trace_id`,
  the script shows "duplicate delivery; the run is stored under trace `<id>`", not only
  "missing".
- S1-10: the acceptance criterion says "ancestor", not "parent".

The GitHub issues change only after the project owner agrees.

## Tests

pytest with an in-memory exporter. No Collector, no network.

1. A known `traceparent`: `monitor.ingest` has the trace ID of the header; its parent is
   the server span; the parent of the server span is the span ID of the header; the stored
   `trace_id` agrees; `trace_id_source` is `traceparent`.
2. No `traceparent`: a new trace; the stored ID is the span's trace ID; the source is
   `generated`.
3. An invalid `traceparent` (the S1-02 header cases): the same as test 2.
4. `GET /api/health`, `GET /api/readiness` and `GET /api/live/portfolio` make no spans.
5. For `201`, `200`, `409`, `400`, `401`, `403` and `413`: the correct `outcome`. No span
   attribute contains the key, the hash, the `Authorization` value or body text.
6. An exporter that raises: the request returns `201`, and the row is stored.
7. `OTEL_SDK_DISABLED=true`: no spans; the run is stored with a generated ID.
8. The S1-02 tests that used `parse_traceparent` use the OTel path.
9. A resend of a stored run with a different `traceparent`: the `200` span has
   `outcome = duplicate` and `stored_trace_id` = the first trace ID, and the row keeps the
   first trace ID. The same for a `409` with different content.
10. A retry with the same trace ID: `stored_trace_id` equals the span's trace ID.

Then the fast suite and the full suite. CI runs on the pull request.

Not tested (report as unavailable): a real Collector (S1-06), a real GCP job (part A), the
test host, the paired test S1-05 + S1-06.
