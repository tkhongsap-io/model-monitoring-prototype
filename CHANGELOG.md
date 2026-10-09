# Changelog

Notable user- and operator-visible changes are recorded here. Development notes
and evidence belong in [DEVLOG.md](DEVLOG.md); decision rationale belongs in ADRs under
[docs/adr/](docs/adr/README.md).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Trace check tool (S1-07): `deploy/compose/check-trace.sh <trace_id> [--backend-only]
  [--wait SECONDS]` shows if the run row, the `monitor.ingest` span, the GCP `batch.run`
  span and the link to `batch.send` exist for one trace. Exit 0, 1 or 2. It uses the
  read-only database user and runs on the local stack and the test host. The CI smoke test
  uses it.

- The backend runs on the GCP test host (S1-04): VM `ai-ml-monitoring-dev-env` with Docker
  Compose (`deploy/compose/compose.testhost.yaml`, runbook `deploy/compose/TESTHOST.md`)
  and Cloud SQL `sandbox-pg17-db` (PostgreSQL 17.11, private IP, TLS). It listens only
  inside the VM until the front door exists.
- `POST /api/batch/runs` accepts the optional field `submitted_at` (UTC; not later than
  `completed_at`) in `batch-run/1`, for the core metric `turnaround_s`. It is stored in the
  run payload.
- `scripts/strip_record_text.py` writes a copy of a GCP run summary without its free text
  (`question`, `answer`, `retrieval_context`, `tool_calls` output), so a real body can be
  shared for development. It prints only counts. `/data/` is ignored by git.
- A local Docker Compose stack (`deploy/compose/`): the backend, PostgreSQL 17.11 and the
  OTel Collector 0.161.0, with a smoke test (`scripts/compose-smoke.sh`) that runs in CI
  (`compose-smoke.yml`) and on macOS (S1-06).
- A push to `dev` that changes `backend/` builds the backend image and pushes it to GCP
  Artifact Registry as `.../model-monitoring/dev/backend:<run_number>`
  (`.github/workflows/build-image.yml`, `backend/Dockerfile`). GitHub signs in with
  Workload Identity Federation; no service-account key exists.

### Changed

- Batch MVP plan, S1-09: the inventory has 7 GCP use cases, not 10. The other 3 run on
  NotebookLM and Gemini Enterprise and have no job code. Network ranges, egress IPs, the
  order of the use cases and the RAI profile confirmation are no longer in the inventory.
  The project owner accepted the October goal of 7: Sprint 3 onboards all 7, and the
  Sprint 4 release needs all 7 to pass.
- Batch MVP plan: the GCP use cases are graded with core metrics plus one profile for each
  task type (`changes/2026-10-08-batch-metric-profiles/`), not with the five chatbot
  metrics for all. The five LLM metrics stay for the generation profiles.
- The draft run summary `batch-run/1` (S1-01) states its meanings more clearly for GCP
  job developers: `request_count` counts all requests (successful + failed), the sample
  contains only requests that Gemini answered or refused, `retrieval_context` holds any
  input text that the answer must agree with, and an image in the prompt becomes
  `[IMAGE]` in `question`. No validation rule changed.
- The backend serves only the batch MVP API: `POST /api/batch/runs`, `/api/health`,
  `/api/healthz`, `/api/readiness` and `/api/version`. Health is a liveness check (no
  database call); readiness checks only `DATABASE_URL` (PostgreSQL) and
  `BATCH_API_KEY_SHA256`. CI uses PostgreSQL 17.11 (S1-13; 18.6 until 2026-10-08).
- `POST /api/batch/runs` continues the GCP job's trace with OpenTelemetry: a FastAPI
  server span and its child `monitor.ingest`, exported over OTLP/HTTP when
  `OTEL_EXPORTER_OTLP_ENDPOINT` is set. The stored `trace_id` comes from the span. A
  resend records `stored_trace_id` on its span. No other route makes spans (S1-05).

- The backend pins the Langfuse SDK v4 (`langfuse>=4.16,<5`) and the OpenTelemetry API,
  SDK and OTLP/HTTP exporter (`>=1.45,<2`) instead of `langfuse>=2.53,<3` (S2-02).
- The chatbot judge keeps its traces and scores in the local store only. The monitor no
  longer pushes them to Langfuse Cloud with the SDK v2, also when the Langfuse keys are
  set. The producer score write-back does not change (S2-02).
- Every pulled telemetry window must carry `contract_version` `"1.0"` or `"1.1"`;
  any other value (or a missing field) is a `ContractVersionError`, recorded as the
  window's telemetry error, and holds the source cursor. `/telemetry/meta` is checked
  only when it carries the field (spec E.2).
- Strict live mode requires `https://` for `LIVE_CHURN_URL`, `LIVE_CHATBOT_URL`,
  `LIVE_NBA_URL` and `LIVE_PRODUCER_URL`; `GET /api/readiness` lists
  `<NAME> must use https in strict live mode` otherwise. `ALLOW_INSECURE_LIVE_TESTING=1`
  remains the only bypass (spec E.4).
- Root `pnpm run typecheck` now runs the `artifacts/*` packages only (the `tsc --build`
  over `lib/*` is gone with the libraries).

### Deprecated or removed

- Not served any more (S1-13): the demo and strict-live prototype routes, the operator
  routes, the pull-lane poller, the dashboard and the OpenAPI pages. The code stays until
  S4-07.
- The `autoscale-poll.yml` schedule (every five minutes) is removed. CI no longer wakes
  the Replit prototype; the workflow runs by hand only. Replit is not a release target:
  the batch MVP releases to the GCP test host, then to AWS.
- Dead scaffold deleted (spec E.1): `.migration-backup/`, `lib/api-spec`, `lib/api-zod`,
  `lib/api-client-react`, `lib/db`, `artifacts/mockup-sandbox`, the TypeScript stub under
  `artifacts/api-server/src` (plus its `build.mjs` / `tsconfig.json`; the Replit
  `artifact.toml` wrapper and a minimal `package.json` stay), `backend/fly.toml`,
  `backend/Dockerfile`, `backend/.dockerignore`, `scripts/src/hello.ts` and
  `scripts/tsconfig.json`.
- Unused npm dependencies removed: `@replit/connectors-sdk`, `@tanstack/react-query`,
  `@workspace/api-client-react`, the `drizzle-orm` / `tsx` catalog entries and the
  `@expo/ngrok-bin` platform overrides. `pnpm-lock.yaml` regenerated.

### Added

- `POST /api/batch/runs` receives one GCP batch run summary (`batch-run/1`, S1-01 draft
  schema; issue S1-02). `Authorization: Bearer <key>`, checked against the SHA-256 hashes
  in the new `BATCH_API_KEY_SHA256` setting in constant time. `201` stores the run once in
  the new `batch_runs` table (migration 8); the same body again is `200`; other content
  for the same `(use_case_id, run_id)` is `409` and the stored run does not change; `400`
  lists the field errors; `401` no or wrong key; `403` a key of another use case; `413`
  above `BATCH_MAX_BODY_BYTES` (default 10 MB). The trace ID comes from the `traceparent`
  header, or is new. The key and the body are never logged. Available in strict live mode.
- Operational resilience (spec D). Producer pulls, acknowledgements, score write-back
  and the alert webhook retry on 429/502/503/504 and connection errors: three attempts,
  exponential backoff 0.5 s → 4 s with jitter, `Retry-After` honoured; other 4xx are
  never retried (`backend/app/http_retry.py`, contract §12).
- Structured logging: `LOG_FORMAT=json` emits one JSON object per line; every poll
  cycle logs `cycle_id, source_id, tick, duration_ms, outcome, backlog` per source, and
  `GET /api/readiness` exposes the last cycle (duration, outcome, last error per source)
  under `poller.last_cycle`. Startup `print`s are gone.
- Operator unstick: `POST /api/live/sources/{uc}/skip` (worker token, `{"reason"}`)
  skips the tick a source is held on — only when the cursor state is `error` (409
  otherwise) — writing an auditable stub observation (`record_count=0`, `skipped=true`,
  reason, `ack_status=skipped` so it is never acknowledged to the producer), finalising
  the tick's realized rows and advancing the cursor in one transaction;
  `POST /api/live/sources/{uc}/reset-ack` abandons a poisoned pending acknowledgement. Every other POST under `/api/live/` is still 404.
  Runbook: `docs/STRICT-LIVE.md` "Unsticking a source".
- The NBA baseline offer mix is persisted per `(source, model_version)` in the new
  `live_baselines` table (migration 7) and read on cold start, so
  `recommendation_drift` survives Autoscale restarts.
- Live alerting (spec C). After every poll cycle each use case's graded health
  (including lagged realized metrics) is diffed against its last snapshot: `* → Red` and
  `Green → Amber` open an alert, a return to Green resolves it, a current Unknown never
  opens or resolves, and
  an open `(lane, health)` is never duplicated. Alerts live in the new `live_alerts`
  table (migration 6, with `live_health_snapshots`).
- `GET /api/live/alerts?uc=&open=&limit=` on the strict router (read-only, derived
  columns only); the live use-case detail carries `alerts` (its open alerts) instead of
  the demo-era `actions: []`; the portfolio summary reports `open_alerts` by severity.
- Webhook delivery: when `LIVE_ALERT_WEBHOOK_URL` is set, each opened and resolved alert
  is POSTed once as a Slack-incoming-webhook-compatible `{text, blocks, alert}` body
  (use case, lane, health, tick, dashboard link from `LIVE_DASHBOARD_URL`; no features,
  no trace text). A failed POST is recorded on the alert and retried next cycle; logs name
  the webhook host only. The strict-live bundle check rejects the secret name.
- Dashboard: an "Alerts" strip on the home page (open Red/Amber counts, newest five) and
  an "Alerts" panel on each use-case page (open and the last 20 resolved). Read-only.
- `docs/adr/0001-alert-ownership.md`: the RAI team owns alert triage via the webhook
  channel; producers are not paged.

- Playbook baseline documents: `README.md`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`,
  `DEVLOG.md`, `TESTING.md`.
- `backend/tests/test_docs.py` enforces the documentation contract (required files,
  one H1, `CLAUDE.md` within 120 lines, internal links resolve, no machine-local paths,
  `postMerge` hook never pushes a schema).

### Fixed

- The slow calibration tests C3 and C8 (`backend/tests/test_calibration.py`) no longer
  fail with a `TypeError` on a `None` `estimated_roc_auc` on macOS. The cause was the
  host, not the code: without an OpenMP runtime `import nannyml` fails and every CBPE
  estimate degrades to `None`. [TESTING.md](TESTING.md) now lists the prerequisite and a
  no-install workaround, and the two tests report the engine's own error when a bake is
  degraded.
- A chatbot trace without `latency_s` is no longer read as 0.0 seconds: it is excluded
  from `p95_latency_s` and counted in the observation's `latency_missing`; its stored
  and sampled latency is `null` (spec E.3). The judge docstring in
  `backend/app/adapters/llm_eval/live_http.py` now names the configured default model
  (`claude-haiku-4-5`) instead of a wrong hard-coded id (spec E.5).
- A closed producer window with `count=0` is stored as an observation (every signal
  Unknown, reason "empty window") and the source cursor advances; it no longer holds the
  cursor as a telemetry error (contract §6).
- Realized ROC-AUC and NBA acceptance rate are computed once lagged labels arrive: the
  poller backfills the ticks within `label_lag_ticks` / `reward_lag_ticks` into the new
  `live_realized_metrics` table (migrations 4 and 5), and the live use-case detail,
  portfolio and summary grade the Performance and Feedback lanes on the latest realized
  value with an `as_of_tick` (contract §7). A tick whose labels never arrive is final
  `no_labels` once the producer's `available_at_tick` is at or before its latest closed
  tick (`latest_tick - 1`). Stored observations are never rewritten.
- The Replit `postMerge` hook no longer runs `pnpm --filter db push`, which pushed an
  empty Drizzle schema at the backend's PostgreSQL database. It only reinstalls
  workspace dependencies; the backend migrates itself at startup.
- `replit.md` no longer tells operators to `cd frontend` (that directory is not a
  workspace package) or that the deploy build "runs migrations".
