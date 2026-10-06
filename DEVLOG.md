# Development Log

## Current outcome

An operator can trust the Green/Amber/Red board for the three live use cases, is told
when a use case goes Red, can see realized performance once labels arrive, and can
unstick a stalled source without a database session. A new agent or engineer can orient
from `README.md` / `CLAUDE.md` and find the change history in `CHANGELOG.md` / this log.
Why it matters: the strict-live plumbing (lease, digest-before-cursor, ack retry) is
sound, but the monitoring on top of it is not yet trustworthy enough for the pilot to
depend on. The spec is
[changes/2026-10-01-monitoring-gap-closure/spec.md](changes/2026-10-01-monitoring-gap-closure/spec.md).

## Done when

- A: `backend/tests/test_docs.py` passes (required files exist, one H1, `CLAUDE.md` within
  120 lines, no machine-local paths, links resolve) and `scripts/post-merge.sh` no longer
  contains `db push`.
- B: with a fake producer, a `count=0` tick stores an observation and advances the cursor;
  labels arriving two ticks later produce a `realized` row in `live_realized_metrics` and
  `as_of_tick` in the detail payload; 40 % coverage yields `insufficient_coverage`; a 404 on
  backfill yields `evicted` with the cursor untouched; stored payload and digest are
  byte-identical before and after backfill.
- C: state-machine unit tests (Green→Amber opens, Amber→Red opens, Red→Green resolves,
  Unknown never alerts, dedupe); webhook test asserts payload shape, that a 500 records
  `delivery_error` and retries next cycle; `/api/live/alerts` is redacted and filtered; the
  bundle check rejects `LIVE_ALERT_WEBHOOK_URL`.
- D: retry tests (429 with `Retry-After`, 503 twice then 200, 404 not retried); the skip
  endpoint requires the worker token, writes a stub observation and advances the cursor;
  the NBA baseline survives a new runner instance.
- E: `pnpm run typecheck`, `pnpm run build:live`, `pnpm run check:strict-live` pass after
  the deletions; contract tests for version rejection, missing `latency_s`, and `http://`
  rejection in strict mode.
- Every slice: full backend suite green, both CI workflows green on the PR.

## Current plan

1. Slice A — playbook baseline and `postMerge` fix: merged (#9).
2. Slice B — monitoring correctness (`count=0` observation, label-lag backfill): merged
   (#10).
3. Slice C — alerting (transition state machine, API, webhook, UI, ADR 0001): merged
   (#11).
4. Slice D — operational resilience (HTTP retry, structured logging, operator skip, NBA
   baseline persistence): merged (#12).
5. Slice E — repository hygiene and contract strictness: done (this branch,
   `chore/hygiene-and-contract-strictness`).

## Work log

### 2026-10-06 — CI builds the backend image for GCP Artifact Registry

- Changed: added `backend/Dockerfile`, `backend/.dockerignore` and
  `.github/workflows/build-image.yml`. A push to `dev` that changes `backend/` builds the
  image, runs an import smoke test, and pushes `dev/backend:<run_number>` to the
  `model-monitoring` repository in `asia-southeast3`. Plan:
  [changes/2026-10-06-ci-gcp-image/plan.md](changes/2026-10-06-ci-gcp-image/plan.md).
- GCP setup by hand: the repository, the `gh-ci-pusher` service account, the Workload
  Identity pool and provider, and the GitHub repository variables.
- Evidence: `import app.main` passed locally. Fast backend suite: 159 passed, 9
  deselected (slow). A local `docker build` was not run (no Docker daemon on the host).
- Remaining:
  - The first real proof is the first green run on `dev` and the image in the registry.
  - The VM pull (reader role, Private Google Access) and the `uat` and `main` builds.
  - The image has no dashboard SPA.

### 2026-10-05 — CI: no Replit deploy or wake

- Changed: the project owner decided that CI must not deploy to Replit. No workflow
  deployed to Replit before this change; `backend-live.yml` and
  `strict-live-frontend.yml` only run checks. The only automatic link was the
  `autoscale-poll.yml` schedule, which called the Replit app every five minutes (288 calls
  each day). The schedule is removed; `workflow_dispatch` stays for a manual poll.
  `CLAUDE.md`, `README.md`, `docs/STRICT-LIVE.md`, `docs/LIVE-DEMO.md` and `replit.md`
  now say that Replit is the prototype only and that the batch MVP releases to the GCP
  test host (S1-04), then to AWS (S4-01).
- Evidence: `tests/test_docs.py` passed. A search of `.github/` found no other Replit URL
  or deploy step.
- Remaining:
  - The Replit Autoscale deployment and its secrets still exist. To stop it, unpublish it
    in Replit by hand. CI cannot do this.
  - The GitHub secret `MONITOR_WORKER_TOKEN` and the variable `MONITOR_URL` stay for the
    manual workflow.

### 2026-10-05 — batch MVP plan: the test host moves to GCP

- Changed: the project owner decided that the Sprint 1 to 3 test host runs in GCP. It is
  one Compute Engine VM (`e2-standard-8`, no external IP, IAP SSH, Cloud NAT for outbound)
  with the same Docker Compose stack. The GCP jobs reach it on a private VPC path through a
  private DNS name and a private CA certificate. The API key stays in S1-02, so the test
  uses the same method as production. The Sprint 3 Kubernetes test stays on the test AWS
  cluster, and production stays on AWS. S3-06 now also tests the internet path from a GCP
  job through Cloud NAT to AWS, because the test host no longer tests it. Changed issues:
  S1-02, S1-04 (new title), S1-06, S1-08, S1-09, S1-11, S1-12, Sprint 2 prerequisites,
  S2-03, S2-06, S3-03, S3-05, S3-06, S3-07, S4-01, S4-02. `plan.md`, `summary.md` and the
  workbook match.
- Evidence: `tests/test_docs.py` 5 passed. The workbook was rebuilt from `issues.md`.
- Posted: the 15 changed GitHub issues were updated from `issues.md` (#4, #6 with its new
  title, #8, #10, #11, #13, #14, #17, #20, #27, #29, #30, #31, #32, #33). A second compare
  found no difference between GitHub and `issues.md`.
- Remaining:
  - S1-04 is due Tuesday 6 October. Its prerequisites (GCP project, VPC connection, job
    runtimes, private DNS name) need answers from the network team first.

### 2026-10-05 — batch MVP plan: SSO login and the LiteLLM judge

- Changed: revised `changes/2026-10-02-batch-monitoring-mvp/` for two decisions of the
  project owner:
  - The LLM judge is a local model through the company LiteLLM proxy. Claude and the
    Anthropic API are not used, and there is no second provider. The backend will call the
    proxy with `httpx` (already a dependency); `anthropic` will be removed. New issues S1-12
    (proxy access), S2-09 (judge client) and S2-10 (RAI accepts the judge against human
    labels, the new release gate).
  - Staff log in with Google Workspace SSO (Entra ID later, settings only): OAuth2 Proxy in
    front of the dashboard, the built-in SSO of Langfuse with no password login. New issue
    S3-07. Google does not accept an IP address in a redirect URI, so a DNS name for the
    test host is a new long-lead request.
  - S1-06: port 443 now sends only `/api/batch/runs` and `/api/health` to the backend, so
    nobody reads the dashboard API around the SSO.

  36 issues now (12, 10, 7 and 7). An "Overview by phase" table groups them in 16
  workstreams. `plan.md`, `summary.md` and `llm-metrics-standard.md` match.
  `model_monitoring_issues.xlsx` replaces `issues.xlsx` and is built from `issues.md` by
  the new `build_issues_xlsx.py`, with a Tracker sheet in the team's phase template. No
  application code changed.
- Evidence: `tests/test_docs.py` 5 passed (`uvx`, `--noconftest`). The workbook was
  rebuilt and compared with the previous one: the 15 issues that were not changed are
  identical, except four fixes of formatting errors in the old export. The Tracker sheet
  was rendered with LibreOffice. The Google redirect-URI rule, the OAuth2 Proxy and mock
  OIDC server versions, the OAuth2 Proxy provider names, the Langfuse SSO settings and the
  LiteLLM `json_schema` request format were read from the official documentation on
  2026-10-05.
- Posted: GitHub issues were enabled on the repository, and the 36 issues were created as
  #3 (S1-01) to #38 (S4-07), with sprint and type labels. Each issue links to `issues.md`;
  `issues.md` stays the source of the plan.
- Remaining:
  - The S2-10 acceptance limits are a proposal; RAI must confirm them.
  - Open requests: LiteLLM proxy access (S1-12), the test-host DNS name and the Google
    OAuth clients.

### 2026-10-04 — batch MVP plan reviewed sprint by sprint; final pass

- Changed: the project owner reviewed `changes/2026-10-02-batch-monitoring-mvp/issues.md`
  sprint by sprint on 2026-10-03 and 2026-10-04. All four files of the change folder are
  now in ASD-STE100. Main decisions:
  - OpenTelemetry in the GCP jobs, through a front door and the Collector.
  - Langfuse SDK v4 in the backend only.
  - The trace ID in the `traceparent` header.
  - Identity-only mode until security approves the records.
  - A static API key with an IP allowlist.
  - A YAML registry with API key hashes in the database.
  - A dashboard with only the GCP use cases, the current UI and no record text. Langfuse for engineers only.
  - A delivery lane on the existing alert engine.
  - A judge retry, with a local-model fallback.
  - Fixed versions: Python 3.12.15, PostgreSQL 17.11, Langfuse 4.50.0.
  - RDS and S3 as plan A, with an in-cluster plan B.
  - An installation on a test AWS cluster in Sprint 3.
  - A use case passes only when its quality grade works.
  - Prototype-only code is not maintained and is removed in S4-07.

  The issues are renumbered: 32 issues (11, 8, 6 and 7). `plan.md`, `summary.md` and
  `llm-metrics-standard.md` are rewritten to match. `flow.html` is marked as superseded.
  No application code changed.
- Evidence: `tests/test_docs.py` 5 passed (`uvx`, `--noconftest`). Both Mermaid diagrams
  in `summary.md` rendered in a browser with Mermaid 11, with no errors. The versions were
  read from endoflife.date, Docker Hub, PyPI and GitHub releases on 2026-10-03 and
  2026-10-04. SDK v4 has no `trace()` or `score()`; this was confirmed by installing
  `langfuse==4.16.0`.
- Remaining:
  - The issues are not posted to GitHub.
  - The ADR for push ingestion and `intent.md` with a new risk tier are not written yet.
  - Open approvals: security (S1-08), the long-lead requests, and the on-call owner (S4-05).

### 2026-10-03 — batch MVP: one LLM metric and data standard from the prototype

- Changed: added `changes/2026-10-02-batch-monitoring-mvp/llm-metrics-standard.md`. All
  10 GCP batch use cases are graded with the prototype's five LLM signals
  (`hallucination_rate`, `groundedness`, `relevance`, `pii_exposure_rate`,
  `p95_latency_s`), the contract §11 bands, the Claude Haiku judge, and the minimum sample
  of 8. GCP jobs send only run identity plus a sample (default 50) of records using the
  v1.1 `Trace` field names: `question`, `answer`, `retrieval_context`, `tool_calls`,
  `refused`, `latency_s` (null for the Gemini Batch API). PII is replaced with typed
  placeholders in GCP, and a placeholder in the answer counts as exposure. Plan, summary
  and issues now use the standard: "reviewed rubric" became a per-use-case task
  description for the judge prompt; "no customer text" became "redacted records only,
  never text in spans or logs"; S1-01, S1-02, S1-04, S1-09, S2-06 and S2-08 updated.
  No application code changed.
- Evidence: signal names, bands, judge fields, `MIN_LIVE_TRACES = 8`,
  `LLM_JUDGE_MAX_TRACES` default 20 and the `latency_missing` handling read from
  `engines/health.py`, `adapters/llm_eval/live_http.py`, `config.py` and contract §9, §11,
  §13, §14. `tests/test_docs.py` 5 passed (`uvx`, `--noconftest`).
- Remaining: redacted text now leaves GCP (to the monitor, the Anthropic judge and
  Langfuse), which needs security approval by Oct 8 (S1-09). The placeholder rule, the
  sample size of 50 and the per-use-case task descriptions are open decisions.

### 2026-10-03 — batch MVP issues rewritten as paired, testable GitHub issues

- Changed: rewrote `changes/2026-10-02-batch-monitoring-mvp/issues.md` as 32 issue drafts
  (11, 9, 6 and 6 per sprint). Each has type, plan task, owner, dependencies, a "tested
  with" partner issue, size, acceptance criteria and test steps. Each sprint opens with a
  paired-test table; for example, the GCP OTel helper (S2-04) is proven by the Collector to
  Langfuse issue (S2-03), with the run summary checked in monitor Postgres under the same
  trace ID. Added plan tasks 1.9 (minimal Collector) and 1.10 (trace check tool,
  `scripts/check_trace.py`), which every paired test uses. No application code changed.
- Evidence: `tests/test_docs.py` 5 passed (`uvx`, `--noconftest`).
- Remaining: issues are not posted to GitHub (account suspended). Test host location and
  the Langfuse SDK version are still open.

### 2026-10-03 — batch MVP plan: OpenTelemetry as the tracing standard

- Changed: added `changes/2026-10-02-batch-monitoring-mvp/summary.md`, a one-page summary
  with the current flow (contract v1.1 pull on Replit, Langfuse SDK v2 direct, no OTel)
  and the October target flow as Mermaid diagrams. `plan.md` now records OpenTelemetry as
  the tracing standard for the monitor and the GCP batch jobs: one trace per batch run,
  joined through `traceparent` in the run summary; monitor spans go through the OTel
  Collector to self-hosted Langfuse; scores stay on the Langfuse score API. New tasks 1.8,
  2.6 and 2.7, plus OTel deadlines, risks, glossary entries and the candidate pip packages.
  The run summary push and the v1.1 data windows stay outside OTel because grading needs
  exactly-once, checksummed records and lagged labels. No application code changed.
- Evidence: a code search found no `opentelemetry`, `otel` or `otlp` usage in `backend/`,
  `artifacts/`, `scripts/` or `docs/`; `backend/requirements.txt` pins
  `langfuse>=2.53,<3`; `adapters/llm_eval/stores.py` calls the SDK v2 directly. Both
  Mermaid diagrams rendered in a browser with Mermaid 11 and no errors.
  `tests/test_docs.py` 5 passed (run with `uvx` and `--noconftest`; no backend `.venv` on
  this host).
- Remaining: the Langfuse SDK v2-or-v3 choice, the OTLP cross-cloud approval and the
  span attribute allowlist are open decisions. `flow.html` predates the OTel decision and
  still shows GCP spans as optional.

### 2026-10-02 — October batch monitoring MVP plan: push ingestion, PM table format

- Changed: moved `docs/mvp1st/` to `changes/2026-10-02-batch-monitoring-mvp/`
  (`plan.md`, `issues.md`, `flow.html`) per the repository's change-plan convention.
  Rewrote `plan.md` as tables for PM readers: sprints at a glance, deadlines for external
  dependencies with fallbacks, per-sprint task tables (owner, done when, depends on),
  shared rules, glossary, risks. Sprint 1 now covers getting data out of GCP: agree a
  JSON body with the GCP job developer and build a token-protected, idempotent receiving
  API (proposed `POST /api/batch/runs`) that each job calls after publishing. Pull
  ingestion is recorded as not chosen. `flow.html` relabelled from pull to push;
  `issues.md` marked out of date for Sprint 1. No application code changed.
- Evidence: `tests/test_docs.py` 5 passed (run with `uvx` and `--noconftest`; the backend
  `.venv` was not set up on this host). Diagram labels checked in a browser for overlap.
- Remaining: push ingestion conflicts with the `CLAUDE.md` rules that the monitor makes
  no producer demands and that only the poller writes data; needs an ADR, an `intent.md`
  with a re-assessed risk tier, and a `spec.md` for JSON body v1 before code. Issue drafts
  need rewriting to match the plan.

### 2026-10-02 — slow calibration tests C3 and C8: missing OpenMP runtime on macOS

- Changed: `backend/tests/test_calibration.py` reads the estimate through a new
  `_estimated_auc` helper that fails with the engine error recorded in the baked payload
  (`use_cases["AICT-P02"]["errors"]["nannyml"]`) when CBPE degraded; the C3 and C8
  assertions and every band are unchanged. `TESTING.md` documents the OpenMP prerequisite
  and states that CI runs the slow tests. No application code changed.
- Evidence: root cause traced with a one-off script that printed the exception
  `EvidentlyNannyMLAdapter._fit_cbpe` remembers: `XGBoostError: libxgboost.dylib could not
  be loaded … Library not loaded: @rpath/libomp.dylib`, raised by `import nannyml`
  (`nannyml` → `flaml` → `xgboost`; `import lightgbm` fails the same way). All 20 ticks
  carried that error and a `None` estimate. With
  `DYLD_FALLBACK_LIBRARY_PATH=.venv/lib/python3.12/site-packages/sklearn/.dylibs` and no
  other change the estimates are 0.8515 … 0.8162 with no engine error. From `backend/` on
  this macOS host (Python 3.12.14, nannyml 0.13.1, xgboost 2.1.4, lightgbm 4.5.0):
  `.venv/bin/python -m pytest -q` with that variable → 168 passed; without it → 166
  passed, 2 failed (C3, C8, now "NannyML CBPE degraded to None: XGBoostError …"). Linux CI
  (`backend-live.yml`, `python -m pytest -q backend/tests`, no marker filter) was already
  green on `main` with 168 passed (run 36900072022). Unavailable: real producer,
  Langfuse, live Claude judge; `build:live` / `check:strict-live` (macOS; no frontend
  change).
- Learned: the earlier Known-gaps entry was wrong twice — the failure is host-specific,
  and CI does run the slow tests. A `None` signal from a bake is a degraded engine, so
  read the payload's `errors` before the code. An in-process preload of scikit-learn's
  `libomp` (`ctypes.CDLL(..., RTLD_GLOBAL)`) does not satisfy dyld because the vendored
  copy has a different install name; the path must be on the loader's search list before
  Python starts.
- Remaining: on a Mac without `libomp` the plain `pytest -q` still fails C3 and C8 until
  the prerequisite in `TESTING.md` is met; a local demo bake or live run on such a host
  shows the estimate as Unknown for the same reason (`backend/run.sh` only probes for the
  Linux `libgomp`).

### 2026-10-02 — repository hygiene and contract strictness (slice E)

- Changed: deleted the dead scaffold (`.migration-backup/`, `lib/*`,
  `artifacts/mockup-sandbox`, `artifacts/api-server/src` + `build.mjs` + `tsconfig.json`,
  `backend/fly.toml`, `backend/Dockerfile`, `scripts/src/hello.ts`,
  `scripts/tsconfig.json`); `artifacts/api-server` keeps `.replit-artifact/artifact.toml`
  and a minimal `package.json`. `pnpm-workspace.yaml` lists `artifacts/*` and `scripts`
  only and drops the `@tanstack/react-query`, `drizzle-orm`, `tsx` catalog entries, the
  `@expo/ngrok-bin` overrides and the drizzle-kit `@esbuild-kit/esm-loader` override;
  root `package.json` loses `@replit/connectors-sdk` and `typecheck:libs`;
  `artifacts/control-tower` loses `@tanstack/react-query` /
  `@workspace/api-client-react` and its `lib/api-client-react` project reference;
  `.gitignore` / `.replitignore` no longer mention `.migration-backup`. Backend:
  `telemetry_http.pull` validates `contract_version` (`SUPPORTED_CONTRACT_VERSIONS =
  {"1.0", "1.1"}`, `ContractVersionError`), `pull_meta` checks it when present;
  `llm_eval/live_http.py` excludes traces without `latency_s` from the p95, counts
  them in `metadata["latency_missing"]`, stores `None` instead of 0.0, and its docstring
  names `claude-haiku-4-5`; `config.live_configuration_errors` requires `https` for the
  four producer URLs. Docs: CHANGELOG, README, `docs/STRICT-LIVE.md`, this log.
- Evidence: from `backend/`, `.venv/bin/python -m pytest -q -m "not slow"` → 159 passed,
  9 deselected (144 before this slice). New `tests/test_contract_strictness.py` (15 tests:
  `"0.9"` / `"2.0"` / `"1"` / missing rejected, `"1.0"` / `"1.1"` accepted, `pull_meta`
  strict vs advisory, half-missing latency → p95 9.6 and `latency_missing == 5`, all
  missing → `p95_latency_s` None, docstring guard, `http://` → four configuration
  errors, `https://` → none, insecure switch bypass). From the repo root `pnpm install`
  (lockfile regenerated: 3 added, 248 removed), `pnpm install --frozen-lockfile` → Done,
  `pnpm run typecheck` → Done for `artifacts/control-tower` (the only package with a
  `typecheck` script left). `bash -n` on the three `scripts/*.sh`; no `lib/`, `mockup`,
  `fly` or `Dockerfile` reference remains in `.replit`, `scripts/`, the workflows or the
  docs. `pnpm run build:live` and `pnpm run check:strict-live` are unavailable on this
  macOS host (lockfile drops `@rollup/rollup-darwin-arm64`); the strict-live frontend
  workflow runs them on the PR. Unavailable: real producer, Langfuse, live Claude judge.
- Learned: the existing fakes already carried `contract_version: "1.1"` (the
  `fake_producer` fixture and the `httpx.get` seams in `test_http_retry.py`), so the
  validation landed without touching a test. `docs/LIVE-DEMO.md` never had a
  mockup-sandbox / port 8081 clash note — port 8081 there is the producer's account API,
  which is correct and stays.
- Remaining: nothing in the five-slice plan. Known gaps below are out of scope or
  unscheduled.

### 2026-10-01 — live resilience: retry, logging, operator skip, baseline persistence (slice D)

- Changed: new `backend/app/http_retry.py` (`request_with_retry`: three attempts on
  429/502/503/504 and `httpx.TransportError`, backoff 0.5 s → 4 s with ±25 % jitter,
  `Retry-After` honoured and capped, other statuses returned at once, the last response
  returned when retryable statuses are exhausted); `telemetry_http` (`pull`,
  `pull_meta`, `pull_build_version`, `pull_model`, `push_scores`,
  `acknowledge_observation`) and `alert_delivery._default_post` go through it via a
  `send` callable that still calls the module-level `httpx.get` / `httpx.post`. New
  `backend/app/logging_setup.py` (`configure`: JSON lines when `LOG_FORMAT=json`, plain
  otherwise, idempotent); `main.py` configures it and its startup `print`s are log
  calls; `LivePoller.last_cycle` records cycle id, timing, outcome, backlog and per-source
  tick/duration/outcome/error, logged as one structured line per source and exposed by
  `/api/readiness` under `poller.last_cycle`. New `db.skip_live_tick` (`NothingToSkip`
  unless the cursor state is `error`; stub observation through `put_live_observation`)
  and `db.abandon_live_acks`; `POST /api/live/sources/{uc}/skip` and `/reset-ack` on the
  strict router behind the worker token; the strict-live middleware allows POST only for
  `/api/live/poll` and `/api/live/sources/*`; `realized_keys_for(uc)` lets the skip route
  mark the tick's realized rows final; the detail view passes `skipped` / `skip_reason`
  through. New `live_baselines` table (migration 7) with `put_baseline` / `get_baseline`;
  `LiveHttpNBAAdapter` stores the captured offer mix per model version and reads it back
  on cold start and rebaseline. Docs: CHANGELOG, README, `docs/STRICT-LIVE.md`
  ("Unsticking a source", retry policy, cycle logs, baselines).
- Evidence: from `backend/`, `.venv/bin/python -m pytest -q -m "not slow"` → 141 passed,
  9 deselected (112 before this slice). New tests: `test_http_retry.py` (429 with
  `Retry-After`, cap, 503 ×2 then 200 with exact backoff, jitter bound, connection errors
  retried then raised, 404 not retried, exhaustion returns the last response, `pull` /
  `acknowledge_observation` / the webhook default go through the policy and the `httpx`
  monkeypatch seam still intercepts), `test_poller_metrics.py` (per-source `ok` /
  `waiting` / `held` / `error` outcomes, structured log fields, JSON formatter,
  idempotent `configure`, readiness `last_cycle`), `test_operator_routes.py`
  (`test_skip_requires_held_cursor` → 409 and no cursor movement, 401 without the token,
  stub observation audited and realized rows final, 422 on a blank reason, 404 unknown
  use case, reset-ack abandons only the named source's acks, every other POST under
  `/api/live/` is 404), `test_nba_baseline.py` (capture persists; a second adapter
  instance measures drift 0.4 against the stored baseline instead of re-capturing a
  shifted mix — the test fails when the cold-start read is disabled; keyed by model
  version; rebaseline reloads; `clear_live_state` drops; migration 7 recorded). No file
  under `artifacts/`, `scripts/`, `lib/` or the workspace manifests changed, so the pnpm
  checks were not rerun. Unavailable: real producer, Langfuse, live Claude judge, a real
  webhook receiver.
- Learned: a default argument bound to `time.sleep` cannot be monkeypatched through the
  module, so `request_with_retry` resolves `sleep` / `rng` per call (the first version
  of the retry test slept for real and still passed). A restart test must change what
  the producer serves between the two instances, or re-capturing the baseline passes it
  vacuously. The skip stub becomes the newest observation, so the detail view, portfolio
  summary and alert evaluation have to render it: `signals: {}` and all-Unknown lanes
  do, and Unknown never opens an alert.
- Remaining: slice E below.

### 2026-10-01 — live alerting: state machine, webhook, API, UI (slice C)

- Changed: new pure engine `backend/app/engines/alerts.py` (`transitions(prev, curr,
  open_keys)`: opens on `* → Red` and `Green → Amber`, resolves on Green, dedupes on
  `(lane, to_health)` while open; a current Unknown never opens or resolves, a previous
  Unknown followed by Red opens per `* → Red`). New tables `live_alerts`
  and `live_health_snapshots` (migration 6) with `open_alert`, `resolve_alerts`,
  `list_alerts`, `open_alert_keys`, `alerts_pending_delivery`, `mark_alert_delivery`.
  New `backend/app/alerting.py` evaluates each use case after its tick inside the
  lease-held cycle, on the grading view (`apply_realized`) so a realized-AUC Red alerts.
  New `backend/app/alert_delivery.py` POSTs a Slack-compatible body to
  `LIVE_ALERT_WEBHOOK_URL` on open and resolve, records failures per phase and retries
  next cycle (one attempt per cycle until slice D), logs the host only; a missing webhook
  marks the phase `skipped`. `GET /api/live/alerts` on both routers; detail `alerts`
  replaces `actions`; portfolio `open_alerts`. Frontend `components/alerts.tsx`
  (`AlertsStrip`, `AlertsPanel`), `LiveAlert` type; bundle guard gains
  `LIVE_ALERT_WEBHOOK_URL`. `docs/adr/0001-alert-ownership.md` and the ADR index.
- Evidence: from `backend/`, `.venv/bin/python -m pytest -q -m "not slow"` → 112 passed,
  9 deselected (86 before this slice). New tests: `test_alert_engine.py`,
  `test_alerting.py` (including a poll cycle that survives a webhook outage),
  `test_alert_delivery.py` (500 → connection error → 200 delivers exactly once; logs
  carry the host, never the URL path or body), `test_alert_routes.py` (strict router
  behind the real middleware: listing, `uc`/`open`/`limit` filters, POST → 404, columns
  only; detail and portfolio fields). From the repo root `pnpm run typecheck` → Done for
  every package. `pnpm run build:live` and `pnpm run check:strict-live` are unavailable
  on this macOS host (lockfile drops `@rollup/rollup-darwin-arm64`; the build fails with
  that exact error); the strict-live frontend workflow is the proof. Unavailable: real
  producer, Langfuse, live Claude judge, a real webhook receiver.
- Learned: `app.main` chooses its router when first imported, and
  `test_strict_live_mode.py` imports it at collection time in demo mode, so a full run
  never mounts the strict router on `main.app`; a strict-router test must assemble
  `live_routes.router` plus `main.strict_live_route_isolation` itself. The plan's
  "Unknown in either position never opens" conflicts with the spec's `* → Red`; the
  spec wins (Unknown → Red opens, dedupe still prevents the Red → Unknown → Red
  duplicate), because a lane that was never measured and now reads Red is the alert
  the monitor exists to raise.
- Remaining: slices D and E below; retry with backoff for webhook delivery arrives with
  D1.

### 2026-10-01 — count=0 windows and label-lag realized metrics (slice B)

- Changed: `backend/app/adapters/ml_monitor/live_http.py` stores a `count=0` window as an
  observation (`errors["empty_window"]`, reason "empty window", NBA Feedback/mix pending)
  and uses the new pure `realized.join_realized`; `telemetry_http.pull` raises
  `WindowEvicted` on 404. New `live_realized_metrics` table (migration 4) with
  `put_realized_metric` (realized/evicted rows are final), `latest_realized`,
  `realized_history`, `ticks_needing_realization`. New `backend/app/label_backfill.py`
  revisits ticks in `[t - L - 1, t)` after each observed tick and while waiting at the tail
  (`L` from `/telemetry/meta`, default 3), verifies the re-pulled window digest against the
  stored observation, and writes `realized` / `pending` / `insufficient_coverage` /
  `single_class` / `no_labels` / `evicted` / `error`. New `backend/app/realized_view.py`
  grades the detail, portfolio rows and summary on the latest realized value with
  `as_of_tick`; runners persist `rollup_meta` so the rollup can be recomputed at read time.
- Evidence: from `backend/`, `.venv/bin/python -m pytest -q -m "not slow"` → 75 passed,
  9 deselected (40 before this slice). New tests: `test_realized_join.py`,
  `test_count_zero_window.py`, `test_realized_store.py`, `test_label_backfill.py`,
  `test_realized_view.py`; shared `tests/conftest.py` carries `isolated_db` and a
  deterministic `fake_producer`. No file under `artifacts/`, `scripts/`, `lib/` or the
  workspace manifests changed, so the pnpm checks were not rerun. Unavailable: real
  producer, Langfuse, live Claude judge.
- Learned: the backfill cannot append to `live_signal_history` (its unique key is
  `(observation_id, signal_key)` and the original observation already holds the pending
  row), so realized sparklines come from `live_realized_metrics`. In the fake-producer
  tests `estimated_roc_auc` is unmeasured (no model artifact) and is not a reasoned
  exclusion, so the Quality lane stays Unknown even when the realized AUC is Green — the
  rollup is doing what it should.
- Review fix: the spec's "`available_at_tick` ≤ current tick with no labels ⇒ final
  `no_labels`" rule is now implemented rather than approximated. Migration 5 adds a
  `final` flag to `live_realized_metrics` (set for `realized`, `evicted`, and overdue
  `no_labels`); `realize_tick` takes `current_tick` / `due_tick`, a 404 on the labels
  window alone is `pending` (not `evicted`) until the due tick passes, and `pending` rows
  that slipped below the window during an outage are swept once more. Fast suite: 84
  passed, 9 deselected.
- Review fix (second pass): finality is judged against the producer's source tick
  (`latest_tick - 1`), not the monitor's tick. While waiting at the tail the monitor's
  tick equals the producer's still-open window, so the previous rule finalized
  `no_labels` one tick early and, because final rows are immutable, lost labels published
  later in that window. `label_backfill.run` takes `source_tick` and forwards it to
  `realize_tick` for both the `available_at_tick` and the `due_tick` comparisons; the
  monitor's tick now only bounds the window. Also: an empty labels window with no
  `available_at_tick` follows the 404 rule (pending until `t + L` closes, then final
  `no_labels`) instead of lingering as non-final `no_labels`, and `count=0` / undersized
  inference windows are final at once so they are not re-pulled every cycle. Fast suite:
  86 passed, 9 deselected.
- Remaining: slices C–E below.

### 2026-10-01 — audit and playbook baseline

- Changed: three read-only audit passes (backend, frontend/deploy, playbook) produced the
  intent, spec and plan under `changes/2026-10-01-monitoring-gap-closure/`. Added
  `README.md`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`, `TESTING.md` and this log from the
  playbook templates; shrank `replit.md` to Replit-specific notes and removed its two wrong
  claims (`cd frontend`, "runs migrations"); `scripts/post-merge.sh` no longer runs
  `pnpm --filter db push`; added `backend/tests/test_docs.py`.
- Evidence: from `backend/`, `.venv/bin/python -m pytest -q -m "not slow"` → 40 passed,
  9 deselected (35 before this slice); `.venv/bin/python scripts/migrate.py` against a
  scratch SQLite file prints versions 1–3. From the repo root, `pnpm run typecheck` → Done
  for `scripts`, `api-server`, `control-tower`, `mockup-sandbox`. `pnpm run build:live` and
  `pnpm run check:strict-live` are unavailable on macOS (lockfile drops
  `@rollup/rollup-darwin-arm64`); the strict-live frontend workflow is the proof. The venv
  setup line was verified in a scratch directory (157 packages installed). Unavailable:
  real producer, Langfuse, live Claude judge.
- Learned: the lockfile's platform overrides make the Vite build Linux-only, so every
  document must say so instead of listing `build:live` as a local check. The docs test
  must match actual home-directory paths (a `Users` folder followed by a user name), not
  the mention of the rule, or the spec and plan trip it.
- Remaining: slices B–E below; the `.migration-backup/` copy of the old `AGENTS.md` and
  `README.md` is skipped by the docs test until slice E deletes it.

## Known gaps

- Alert triage ownership (contract §18 Q1) is open at the contract level; resolved for
  this repository by [docs/adr/0001-alert-ownership.md](docs/adr/0001-alert-ownership.md)
  (RAI team via the webhook channel; producers are not paged). Alerts have no
  acknowledge workflow, SLA timer or escalation.
- Out of scope and unscheduled: per-use-case thresholds, LIME in production, §14 sampling
  policy, Alembic, Prometheus metrics, Slack SDK, paging/escalation, push ingest,
  skops/ONNX artifacts, retention pruning.
