# Intent: nginx front door and the OTLP token (S1-06, test-host part)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-09)
- **Issue:** S1-06 (#8), test-host part. The local part is done (`changes/2026-10-07-s1-06-local-compose/`).
  Was assigned to Prakasit; the project owner moved the build to Claude + Codex on 2026-10-09.
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09)
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S1-06

## Problem

The GCP jobs cannot reach the monitor. The backend listens only on `127.0.0.1:8000` in the
VM, and the Collector is not reachable from outside its Docker network. S1-04 (the curl
test), S1-02a, S1-03, S1-05 part A and S1-10 wait for one entry point on port 80 that sends
only the job paths to the backend and the Collector, with a token for the spans.

## Outcome

`http://10.10.0.4` (port 80, open only to the job subnet) serves `/api/batch/runs` and
`/api/health` (backend, API key) and `/otlp/*` (Collector, OTLP token). Every other path is
`404`. The CI smoke test proves the routes, the token and one full fake-job trace (all four
trace check items found) on every pull request.

## Decisions (project owner, 2026-10-09)

| Decision | Reason |
|---|---|
| The Collector checks the OTLP token (`bearertokenauth` on a second receiver `otlp/external`, port 4319); nginx routes paths only (option A) | S4-01 replaces nginx with the AWS ingress, but the Collector moves as it is, so the token check moves with it |
| nginx is a standalone Compose project `nginx` (`deploy/nginx/`, `/opt/nginx/` on the VM), not a service of the model-monitor project | One front door for many apps: each app has its own file in `conf.d/`; adding an app does not restart the others |
| The apps reach nginx through an external Docker network `edge`, with app-specific aliases (`model-monitor-backend`, `model-monitor-collector`) | Two apps with a service named `backend` cannot collide |
| nginx resolves the apps at request time (`resolver 127.0.0.11`) | nginx starts even when one app is down; only that app gives `502` |
| Without DNS, apps are separated by port: 80 = model-monitor job paths; Sprint 2 adds 8080 (dashboard) and 3000 (Langfuse) | The test host has no DNS name (decided 2026-10-08) |
| The project owner runs the token steps (Secret Manager → VM); Claude writes the script and checks the output | The coding tool's safety check blocks Claude from handling secret values (as in S1-11) |
| The front door is also in the local stack and in CI | The smoke test proves the routes, the token and a full trace on every pull request |

## Success criteria

- The static tests and the CI smoke test pass. The smoke test shows all four trace check
  items found for a fake job trace sent through nginx.
- On the test host: `curl http://10.10.0.4/api/health` gives `200` from the VM and from the
  job runtime; `/api/live/portfolio` gives `404`; `/otlp/v1/traces` without the token gives `401`.
