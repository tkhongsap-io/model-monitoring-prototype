# Intent: the dashboard shows the GCP use cases (S2-07)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-14)
- **Issue:** S2-07 (#21). October scope from the 2026-10-09 change in
  `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S2-07.
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09)
- **Depends on:** S2-01 (registry, #80) and S2-05 (grades, #88), both merged.

## Problem

The batch runs are stored and graded (S2-05), but the RAI team cannot see them. The
existing dashboard (`artifacts/control-tower`) reads `/api/live/*`, which the batch MVP
backend does not serve (S1-13), and nothing serves the built dashboard on the test host.

## Outcome

The RAI team opens the existing dashboard through an IAP tunnel to port 8082 of the test
host. It shows each registered GCP use case with its latest run, freshness, grade, lanes,
"Unknown" reasons and trace ID. The frontend code does not change. No record text reaches
the browser.

## Decisions (project owner, 2026-10-14)

| Decision | Reason |
|---|---|
| **Serving (option A):** CI builds a `dashboard` image (multi-stage: Node builds `dist/`, a pinned `nginx-unprivileged` serves it). The main nginx gets a new port for the dashboard; `/` goes to the dashboard container, the read-only API paths go to the backend. | The common production pattern for a Vite app (Vite docs; Docker's React guide). The backend stays an API. The same container can move behind IT's IAP load balancer, or to S3 and CloudFront on AWS. |
| **Port 8082**, not 8081 as first discussed. | nginx already uses `127.0.0.1:8081` inside its container for its own health check. |
| **The frontend code does not change (lane option A).** The 5 fixed lane columns are filled: `Reliability` ← `failure_rate`; `Drift & degradation` ← `volume_change`; `Quality`, `Safety & security` ← Unknown "records not approved"; `Feedback & action loop` ← Unknown "no feedback source in October". Overall = `grade`. The Delivery metrics (`run_status`, `turnaround_s`) show only on the detail page. | Keeps the 2026-10-03 decision "the UI does not change". The delivery lane never changes the overall chip (S2-05 rule). |
| **Observation ID shows the `trace_id`.** The API also returns `trace_id`, `grade`, `delivery_grade`, `bands_version`. | An engineer copies it into Langfuse. The dashboard has no Langfuse link (S2-07 decision 2026-10-03). |
| **Risk tier is not set** (badge "Unknown"). | The registry has no tier field; the monitor does not invent one. |
| **`/api/live/alerts` returns an empty list.** | No alerting in October. |
| A **new** small module serves `/api/live/*`; the prototype `live_routes.py` stays unmounted. | The prototype routes depend on the old live runners (S4-07 deletes them). |

The design was previewed on 2026-10-14 with the real frontend and a mock API (before:
prototype data, after: the S2-07 data). The screenshots matched this design.

## Not in scope

Alerting, a Delivery column on the list pages, risk tiers in the registry, IT's HTTPS load
balancer, and Windows support for `vite dev` (the workspace installs Linux binaries only).

## Success criteria

- On the test host, the dashboard on port 8082 (IAP tunnel) shows only the registered GCP
  use cases, with the latest run, freshness, grade, lanes and "Unknown" reasons.
- No API response contains record text, `payload`, keys or tokens.
- `artifacts/control-tower/src` does not change; `typecheck`, `build:live` and
  `check:strict-live` pass in CI.
- CI `smoke` reaches the dashboard and its API through nginx port 8082, and a `POST` to the
  job API on that port is refused.
