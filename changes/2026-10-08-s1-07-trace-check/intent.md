# Intent: trace check tool (S1-07)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-08)
- **Issue:** S1-07 (#9)
- **Risk tier:** R2, the batch MVP tier (`changes/2026-10-02-batch-monitoring-mvp/intent.md`).
  A read-only developer and operator tool. It is not part of the product and not an API route.
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S1-07

## Problem

S1-05 (one trace for each run) and S1-10 (first real run) need proof that one batch run
arrived completely: the stored run row, the `monitor.ingest` span, the GCP `batch.run`
span, and the parent chain from `monitor.ingest` up to `batch.send`. Today the only check
is an inline Python block in `scripts/compose-smoke.sh` that finds `monitor.ingest`. On
the test host there is no check at all: the span file is in a Docker volume and the
database has a private IP only.

## Outcome

One command, `deploy/compose/check-trace.sh <trace_id> [--backend-only] [--wait SECONDS]`,
prints "found", "missing" or "skipped" for each item and exits `0`, `1` or `2`. It works
on the local stack and on the test host (through one `gcloud compute ssh --command` line),
with the read-only database user. The CI smoke test uses it.

## Decisions (project owner, 2026-10-08)

| Decision | Reason |
|---|---|
| The tool runs as a one-shot Compose service `trace-check` (profile `tools`) with the backend image, not inside the running backend container (approach B) | The backend container does not get the span volume. The read-only database URL comes from a host env file (`check.env`, mode 600), so the password is never in a command line or in `ps`. |
| On the test host, run it through one SSH command from the laptop | The span file is in a VM volume and Cloud SQL has a private IP. An API route is rejected: S1-13 allows only the batch MVP routes, and the plan says the tool is not part of the product. |
| The CI smoke test uses the tool (`--backend-only --wait 30`) instead of its inline span check | CI proves the tool on every pull request; one copy of the span logic |
| The tool reads only `CHECK_DATABASE_URL`, never `DATABASE_URL` | It can never use the backend's write user by mistake |
| A `conflict` (409) is reported as missing, with the stored trace ID; a `duplicate` (200) counts as found | The plan describes only the duplicate case; the backend also sets `stored_trace_id` on a conflict |

## Success criteria

- The unit tests and the script tests pass. The CI smoke test passes with the tool.
- On the test host: a request with a known `traceparent` gives exit `0` with
  `--backend-only`; a random trace ID gives exit `1`.
- The full four-item check with a real GCP job is S1-10; it is not a criterion here.
