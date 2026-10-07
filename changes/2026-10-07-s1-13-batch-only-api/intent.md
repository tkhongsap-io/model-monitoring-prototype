# Intent: serve only the batch MVP API (S1-13)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-07)
- **Issue:** S1-13 (#52)
- **Risk tier:** R2, the batch MVP tier (`changes/2026-10-02-batch-monitoring-mvp/intent.md`).
  This change makes the exposed surface smaller.
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S1-13

## Problem

`main.py` mounts the prototype: the demo routes or the strict-live routes, the pull-lane
poller, the operator routes and the dashboard. In strict live mode the backend is "ready"
only with the prototype settings (three producer URLs, `LIVE_PRODUCER_URL`,
`LIVE_TELEMETRY_TOKEN`, `LIVE_WORKER_TOKEN`, `ANTHROPIC_API_KEY`, the Langfuse keys). The
batch MVP has none of them. Thus the GCP test host (S1-04) would report "not ready", and
the prototype API would be reachable next to the batch receiver.

## Outcome

The app serves only the batch MVP API: `POST /api/batch/runs`, `/api/health`,
`/api/healthz`, `/api/readiness` and `/api/version`. Every other path returns `404`. There
is no mode. The prototype code stays in the repository, with its tests, until S4-07 removes
it.

## Decisions (project owner, 2026-10-07)

| Decision | Reason |
|---|---|
| No mode: the prototype routers are not mounted; they are not blocked by a switch | A mode can be set wrongly; a route that is not mounted cannot be reached |
| The dashboard is not served until S2-07 | Its pages call prototype routes that return `404`; no broken page |
| `/api/health` and `/api/healthz` are liveness checks (always `200`, no database call); `/api/readiness` checks the database and the API keys | A database problem must not make Docker restart the backend in a loop |
| Approach: a short `main.py` with only the batch routers; the old composition moves to a test helper | The rule "only the batch API is served" is true by construction and a route-table test proves it |
| Readiness reports `503` when `DATABASE_URL` is not set or is not PostgreSQL | SQLite is for development only; no silent SQLite fallback on the test host |

## Accepted effects

- The current dashboard has no data source until S2-07.
- The Replit prototype stops working if it is redeployed from `dev`. Replit is not a
  release target (#42).
- `LIVE_WORKER_TOKEN` and the other prototype settings are not used by the app.

## Success criteria

The acceptance criteria of #52 pass in pytest and in CI on PostgreSQL 18.6.
