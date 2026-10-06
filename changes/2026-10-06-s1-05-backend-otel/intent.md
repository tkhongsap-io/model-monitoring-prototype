# Intent: backend OpenTelemetry for batch runs (S1-05 part B)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-06)
- **Issue:** S1-05 (#7), part B only. Part A (the GCP job) belongs to the GCP job developer.
- **Risk tier:** R1, the same as the project. Tracing records timing and IDs for engineers.
  It never changes a grade, a stored run or a telemetry cursor.
- **Plan of record:** [S1-05 in issues.md](../2026-10-02-batch-monitoring-mvp/issues.md#s1-05--otel-in-the-gcp-job-and-the-backend-one-trace-for-each-run)

## Problem

S1-02 stores each GCP batch run with a trace ID that it parses from the `traceparent`
header by hand. The backend makes no spans. Thus a trace in the Collector or in Langfuse
stops at the job, and engineers cannot see the backend step of a run.

## Outcome

One batch run is one trace. The backend continues the trace of the job: the FastAPI
server span is a child of the job's HTTP client span, and `monitor.ingest` is a child of
the server span. The `batch_runs` row stores the same trace ID. The spans go to the
Collector over OTLP/HTTP when an endpoint is set.

## Decisions (2026-10-06)

| Decision | Reason |
|---|---|
| Part B only | Part A is in the GCP job repository and has its own owner. |
| `batch.send` is an **ancestor** of `monitor.ingest`, not its parent | The job's instrumented HTTP client span carries the `traceparent` ID, and the backend server span sits between them. S1-05, S1-07 and S1-10 change from "parent" to "ancestor". |
| Only `POST /api/batch/runs` makes spans | Each trace is one batch run. The prototype routes and the health checks add no noise. |
| A small `tracing.py` with explicit FastAPI instrumentation | All packages are approved (S2-02). It is testable without a Collector. S2-02 uses the same provider later. |

## Success criteria

The acceptance criteria of S1-05 part B, with the "ancestor" change, pass in pytest with
an in-memory exporter. The paired test with S1-06 stays open, because the Collector and
the GCP job do not exist yet.
