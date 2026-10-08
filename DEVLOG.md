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

### 2026-10-08 — `batch-run/1`: optional field `submitted_at`

- Decision (project owner): add the optional field `submitted_at`, the time when the job
  submitted the batch. The core metric `turnaround_s` = `completed_at` − `submitted_at`
  replaces the time of each request, which the Gemini Batch API does not have.
- Changed: `schema/batch-run-1.schema.json` (new property, UTC pattern), example
  `03-batch-api-null-latency.json` sends it, `schema/README.md`, `backend/app/batch_schema.py`
  (optional field; a real calendar time; rules: not `null` if present, not later than
  `completed_at`), `docs/STRICT-LIVE.md`, `core-metrics.md`. No migration: the field stays
  in `payload`; S2-05 adds a column when it calculates `turnaround_s`.
- Evidence: `tests/test_batch_schema.py` + `tests/test_batch_runs_api.py` 89 passed
  (new: optional, format, order, `null`, stored in `payload`); JSON Schema check with
  `jsonschema` (throwaway environment): 5 valid pass, 3 invalid + 9 built cases fail.
- Remaining: deploy to the test host before any job sends the field (an older backend
  answers `400`).

### 2026-10-08 — every database is PostgreSQL 17

- Changed: the project owner changed the monitor's Cloud SQL instance on the test host
  from PostgreSQL 18.6 to **17**. So every database is now PostgreSQL 17 in every
  environment: the local stack and CI use `postgres:17.11-bookworm` (the newest 17.x image,
  checked 2026-10-08), RDS is 17 on AWS, and Langfuse stays 17.11. The local volume path
  is `/var/lib/postgresql/data` again (PostgreSQL 18 had changed the layout).
  `issues.md` has the version rule: one major version everywhere, data only moves to the
  same or a newer major version, a major change only with a plan entry. The Langfuse
  facts (v4: minimum 15, recommended 16; CI tests 15 and 17, not 18) are in the
  fixed-versions table. New test: the CI database image must equal the local stack image.
- Evidence: `tests/test_compose_files.py` failed first (2 failed), then `test_compose_files.py`
  and `test_docs.py` 15 passed. The Compose smoke test and the full suite on PostgreSQL
  17.11 run in CI on the pull request.
- Remaining: record the minor version that the Cloud SQL instance shows. A Mac stack kept
  with `KEEP=1` needs `down -v` one time (see `deploy/compose/README.md`).

### 2026-10-08 — decision: core metrics for all use cases, one profile for each task type

- Input: the second GCP body (fraud validation, 50 records, stripped with
  `scripts/strip_record_text.py`; not committed) passed the JSON Schema and `validate_run`.
  Its values and the developer's answers showed that the job is an image classifier: a
  fixed prompt (the system prompt, about 9,600 characters, was in `question`), 3 images
  (sent as fake `retrieval_context` items with text `[IMAGE]`), and a fixed JSON answer.
  The project owner confirmed that all 10 GCP use cases are one-turn batch inference.
- Decision (project owner, 2026-10-08): the chatbot metrics do not fit all use cases. Each
  use case gets the core metrics (delivery, `turnaround_s`, `failure_rate`,
  `volume_change`, `valid_output_rate`, `block_rate`) and one profile
  (`classification`, `extraction`, `generation_from_text`, `generation_free`). The five
  LLM metrics stay for the generation profiles only. `p95_latency_s` is not a core metric,
  because batch inference has no time for each request.
- Changed: new `changes/2026-10-08-batch-metric-profiles/` (`core-metrics.md`,
  `use-case-template.md`); `llm-metrics-standard.md` status points to it; S1-09 in
  `issues.md` uses the template. The plan effect is posted on issue #3.
- Remaining: RAI approves the bands and the profiles; the job developers fill in the
  template (S1-09); S2-01, S2-05, S2-07, S2-09, S2-10 and S4-04 are planned again from
  the answers; `submitted_at` is added to `batch-run/1` (S1-01, S1-02b).

### 2026-10-07 — S1-01: schema clarifications after the first GCP example

- Input: the GCP job developer sent one real body (fraud validation job, 8 records, text
  removed for privacy; the file is not committed). Its field set is the same as the draft:
  no unknown field, no missing required field. With placeholder text, `validate_run`
  accepts it.
- Found from its values, and confirmed by the project owner with the developer:
  - `request_count` was the successful requests only (243), with `failed_count` 106 on
    top. The schema means all requests (349). With the job's meaning, a run with more
    failures than successes fails `failed_count` ≤ `request_count`. The job changes, not
    the schema.
  - 3 sampled records were failed requests (`latency_s: null` in an online job). The job
    now samples only requests that Gemini answered or refused.
  - `sample.size` is the `SAMPLE_SIZE` setting.
  - The job is image input only (Gemini reads the image). `question` gets the marker
    `[IMAGE]`; `retrieval_context` is `[]`.
- Changed (descriptions only, no validation rule): `schema/batch-run-1.schema.json`
  (`request_count`, `failed_count`, `records`, `question`, `retrieval_context`),
  `schema/README.md` (clarifications and `retrieval_context` examples),
  `llm-metrics-standard.md` (the same rules; a selected online request that fails is not
  sent). `backend/app/batch_schema.py` does not change.
- Evidence: with the edited schema (`jsonschema` in a throwaway environment), the 5
  `examples/valid/` pass and the 3 `examples/invalid/` plus 6 built negative cases fail.
  `tests/test_docs.py` + `tests/test_batch_schema.py` 43 passed; fast suite 319 passed,
  9 deselected (1 warning). The local venv was synced to `requirements.txt` first (it
  lacked `opentelemetry-sdk`).
- Decision (project owner, 2026-10-07): the monitor team gets **no access to GCP logs**.
  The batch jobs belong to teams across the company, and log access is hard to get. The
  monitor uses only what the jobs send: the body (`status: failed` when possible) and the
  OTel spans. Changed in `issues.md`: S1-01 criterion 6; S1-05 gets a criterion for the
  error status on `batch.send` and `batch.run`; the S1-08 row "Read access to GCP Cloud
  Logging" is removed. `schema/README.md` questions 13 and 14 follow. The 10 open
  questions are posted on issue #3 for the developer.
- Removed (project owner): `model_monitoring_issues.xlsx` and `build_issues_xlsx.py`.
  GitHub issues are the tracker, and `issues.md` is the source of their text. (The script
  also stopped because S1-13 and S2-11 are not in the "Overview by phase" table.)
- The GitHub bodies of #3 (S1-01), #7 (S1-05) and #10 (S1-08) are updated from
  `issues.md` of this branch.
- Issue check (all 41 S-numbered GitHub issues against `issues.md`): #8 (S1-06) and #30
  (S3-06) lacked text that #54 and #49 added to `issues.md`; both synced from `dev`.
  S1-02a, S1-02b and S1-02c (#43–#45) were made on GitHub only; their sections are now
  in `issues.md` (after S1-02), in "All issues" and in the overview. In S1-02a, the
  `401` criterion now says that the GCP developer confirms the job's own log entry.
  Known gap, not changed: S1-13 and S2-11 are not in "Overview by phase".
- New `scripts/strip_record_text.py` (standard library only): writes a copy of a run
  body with `question`, `answer`, `retrieval_context` title/text and `tool_calls` output
  replaced by `[REMOVED <n> chars <placeholder counts>]`, and prints only counts. The
  project owner uses it before a real GCP body is shared or given to Claude. `/data/` is
  now in `.gitignore`. Tests: `tests/test_strip_record_text.py` (synthetic text) 8 passed.
- Remaining for S1-01: the developer fixes `request_count` and the sample and answers
  issue #3; RAI decides `groundedness` and `hallucination_rate` for image-only use cases
  (registry, S2-01); reviews by RAI and security (S1-08).

### 2026-10-07 — S1-06 local part: Docker Compose stack and smoke test

- Changed: `deploy/compose/` (base and local Compose files, Collector configuration,
  README), `scripts/compose-smoke.sh`, `.github/workflows/compose-smoke.yml`,
  `backend/tests/test_compose_files.py`. Decisions with the project owner: CI smoke test
  plus a hand test on a Mac; base file plus one file for each environment; loopback-only
  ports; the Collector file in the `collector-data` volume (see below). Change package
  `changes/2026-10-07-s1-06-local-compose/`.
- First CI run of #54 failed at the last step: build, health checks, readiness, `201` and
  the `batch_runs` row passed, but the Collector restarted in a loop with
  `open /tmp/spans.jsonl: no such file or directory` — the distroless image has **no
  `/tmp`**. The design had assumed `/tmp`. Fix, chosen by the project owner: the file goes
  to `/data/spans.jsonl` in the named volume `collector-data`, and a one-time
  `collector-init` (`busybox:1.37.0`, new row in the fixed-versions table) gives the volume
  to uid 10001; the Collector stays non-root. Tests first: 5 failed, then green.
- CI evidence after the fix: `Compose smoke test` passed on `3918f0f` (run 37588234590,
  2 min 6 s): `SMOKE PASS: run smoke-20261007T073712Z-d478a3, trace
  080ed143ce9ccee4f06ea15b15389666`. `Strict live backend` passed on the same commit.
  The project owner ran `bash scripts/compose-smoke.sh` on a Mac on 2026-10-07: passed
  (reported in chat).
- Evidence: `tests/test_compose_files.py` 9 passed; fast suite 318 passed, 9 deselected
  (1 warning); `tests/test_docs.py` 5 passed (rerun by Claude). Codex implemented the
  plan; Claude reviewed it: four files are identical to the plan, and the comment in
  `compose.local.yaml` no longer names the plain test key (the plan's own test caught it).
  Not run here (no Docker and no bash on the Windows host): the stack, `docker compose
  config`, `bash -n`, the smoke test. CI runs the smoke test on the pull request; the project owner
  runs it on a Mac.
- Remaining: the test-host part of S1-06 (front door, OTLP token,
  `compose.testhost.yaml`) with S1-04. S1-07 can now read the Collector file.

### 2026-10-07 — S1-02c: ADR 0002 for push ingest; the batch MVP is risk tier R2

- Changed: `docs/adr/0002-batch-push-ingest.md` records why GCP batch jobs push to
  `POST /api/batch/runs` (options: push, pull from GCP storage, v1.1 pull), the trust
  boundary, why no cursor moves, and why a stored run never changes. New
  `changes/2026-10-02-batch-monitoring-mvp/intent.md`. The project owner measured the
  risk tier with `handbook/risk-tiers.md` of `tkhongsap-ai-engineering-playbook@5ba9dc8`
  and accepted **R2**: base R1, escalated for confidential customer data and for
  untrusted text read by the LLM judge. The prototype stays R1. `CLAUDE.md` (the push
  exception and the R2 line) and `README.md` point to the ADR. New issue S2-11 (threat
  model), because R2 requires one. The "Known gaps" line about the missing ADR is removed.
- Evidence: `tests/test_docs.py` passed; `CLAUDE.md` is 97 lines (budget 120).
- Remaining:
  - The AI system card (playbook `templates/ai-system-card.md`): the project owner
    decided to write it later, before S4-06.
  - S2-11 threat model, due Wednesday 14 October.

### 2026-10-07 — S1-13: serve only the batch MVP API

- Changed: `main.py` mounts only `batch_routes` and the new `ops_routes`; no mode, no
  poller, no middleware, no dashboard, no OpenAPI pages. `config.batch_configuration_errors()`.
  The old composition is `backend/tests/prototype_app.py` for the prototype tests. CI uses
  `postgres:18.6-bookworm` and validates the batch settings. Change package
  `changes/2026-10-07-s1-13-batch-only-api/`.
  Codex implemented the plan; Claude reviewed the diff and reran the checks.
- Deviations from the plan: the version test first blocked `httpx.Client.send`, which
  `TestClient` also uses; the test now keeps the test client's own `send` and still
  blocks every other outbound call. Another method on a served path is `405`, not `404`
  (spec updated while the plan was written).
- Evidence: fast suite 310 passed, 9 deselected (276 before); full suite 319 passed;
  `tests/test_docs.py` 5 passed (Windows, rerun by Claude). TDD: the new surface tests
  failed first (21 failed, 13 passed). Not run: the test host (S1-04), the Compose smoke
  test (S1-06, next), CI on PostgreSQL 18.6 (runs on the PR).
- Remaining: the dashboard returns with S2-07. S1-06 builds the Compose stack on this app.

### 2026-10-07 — batch MVP plan: Cloud SQL and PostgreSQL 18.6 for the monitor database

- Changed: the plan now matches the Cloud SQL decision of 2026-10-06. The project owner
  gave the instance settings: Cloud SQL for PostgreSQL 18.6, 1 vCPU, 3.75 GiB, 100 GB SSD,
  no public IP. The project owner also decided that the monitor database is PostgreSQL
  18.6 in every environment (Cloud SQL, the local stack and CI); AWS RDS targets
  PostgreSQL 18 (S3-06). The Langfuse database stays `postgres:17.11-bookworm` on the VM.
  `issues.md`: the fixed-versions table (three PostgreSQL rows), S1-04 (a Cloud SQL table:
  private IP only, TLS only with `sslmode=verify-ca`, daily backups kept 7 days and
  point-in-time recovery; new criteria and tests), S1-08 (data in Cloud SQL), S1-11 (Cloud
  SQL built-in users; developers use IAP SSH to the VM, then `psql` to the private IP; no
  Auth Proxy), the Sprint 2 prerequisites (VM size reason and ports), S2-03 (the Langfuse
  database rule), S3-06 and the long-lead request (RDS monitor 18, Langfuse 17).
  `plan.md`: two decision rows and the test-host text. GitHub issues #6, #10, #13 and #17
  got the same text.
- Evidence: `tests/test_docs.py` passed. `db.engine()` rewrites only the URL scheme, so
  `sslmode` and `sslrootcert` in `DATABASE_URL` reach psycopg. `postgres:18.6-bookworm`
  exists on Docker Hub (checked 2026-10-07).
- Remaining:
  - CI still uses `postgres:16` (`backend-live.yml`). Change it to
    `postgres:18.6-bookworm` with S1-06.
  - The VPC firewall rules do not protect the Cloud SQL private IP. The protection is the
    private IP, TLS only and the accounts (S1-11).

### 2026-10-06 — S1-05 part B: backend OpenTelemetry for batch runs

- Changed: new `backend/app/tracing.py` (one provider, OTLP/HTTP export only with an
  endpoint, FastAPI instrumentation that traces only `POST /api/batch/runs`).
  `batch_routes.py` runs in `monitor.ingest` and takes the trace ID from the span;
  `parse_traceparent` is removed. `db.BatchRunConflict.stored_trace_id`. Package:
  `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67` (approved in S2-02). Decisions with
  the project owner: part B only; `batch.send` is an ancestor (not the parent) of
  `monitor.ingest`, so S1-05, S1-07 and S1-10 in `issues.md` changed; `stored_trace_id`
  on a resend. Change package `changes/2026-10-06-s1-05-backend-otel/`. Codex
  implemented the plan; Claude reviewed the diff and reran the checks.
- Deviations from the plan:
  - FastAPI 0.142 has its own native telemetry. It traces **every** route when a global
    OTel provider exists, which breaks the "only `/api/batch/runs`" rule. `setup` turns
    it off on each app (`app._telemetry`, a private attribute; FastAPI reads it at
    request time). One `test_tracing.py` test failed before this change.
  - The `spans` fixture attaches a new in-memory exporter in each test, because a
    `TestClient(main.app)` lifespan in another test shuts the shared provider down.
  - The missing-flags `traceparent` case of the removed parser test moved to the
    invalid-header test of `test_batch_runs_api.py`.
- Evidence: fast suite 276 passed, 9 deselected; full suite 285 passed; docs test 5 passed
  (Windows, rerun by Claude). TDD: Task 1 failed first at import; Task 2 failed first with 12
  failed, 4 passed. Not run: a real Collector (S1-06), a real GCP job (part A), the test
  host, the paired test S1-05 + S1-06.
- Remaining:
  - S1-07 must follow the parent IDs upward. The GitHub issues #7, #9 and #12 were
    updated to "ancestor" on 2026-10-07, with the project owner's approval.
  - `app._telemetry` is private FastAPI API. A FastAPI upgrade can change it; the
    exclude-list tests in `test_tracing.py` should detect that.

### 2026-10-06 — decision: the test host uses Cloud SQL for the monitor database

- Decided: the project owner decided that the monitor database on the GCP test host is
  **Cloud SQL for PostgreSQL**, not a PostgreSQL container on the VM. Cloud SQL is a paid
  service; the GCP sandbox has a budget for it. The Langfuse database stays a PostgreSQL
  container in Docker Compose on the VM (S2-03).
- Effect: no backend code change. The backend needs only a PostgreSQL `DATABASE_URL`, and
  the in-code migrations in `db.py` run on Cloud SQL as before (no Alembic).
- Remaining (done on 2026-10-07, see the entry above): `issues.md` and the GitHub issues
  still say "PostgreSQL on the VM". Change them in a pull request:
  - S1-04 (#6): a Cloud SQL instance with a private IP only, in the VM's VPC; Cloud SQL
    backups instead of VM disk snapshots for the monitor data; the acceptance criterion
    "the monitor backend, PostgreSQL and the Collector run on the VM".
  - S1-11 (#13): the accounts become Cloud SQL users; the developer access path (Cloud SQL
    Auth Proxy or IAM database login instead of `psql` on the VM).
  - S1-08 (#10): real redacted data in Cloud SQL.
  - S2-03 (#17): record that the Langfuse PostgreSQL stays on the VM.
  - `plan.md` decision table, the fixed-versions table (a Cloud SQL PostgreSQL 17 row)
    and the VM size in the Sprint 2 prerequisites (one PostgreSQL container, not two).

### 2026-10-06 — CI builds the backend image for GCP Artifact Registry

- Changed: added `backend/Dockerfile`, `backend/.dockerignore` and
  `.github/workflows/build-image.yml`. A push to `dev` that changes `backend/` builds the
  image, runs an import smoke test, and pushes `dev/backend:<run_number>` to the
  `model-monitoring` repository in `asia-southeast3`. Plan:
  [changes/2026-10-06-ci-gcp-image/plan.md](changes/2026-10-06-ci-gcp-image/plan.md).
- GCP setup by hand: the repository, the `gh-ci-pusher` service account, the Workload
  Identity pool and provider, and the GitHub repository variables.
- Evidence: after merging `dev` (with S1-02 and S2-02), `import app.main` passed and the
  fast backend suite gave 251 passed, 9 deselected (slow). A local `docker build` was not
  run (no Docker daemon on the host).
- Remaining:
  - The first real proof is the first green run on `dev` and the image in the registry.
  - The VM pull (reader role, Private Google Access) and the `uat` and `main` builds.
  - The image has no dashboard SPA.

### 2026-10-05 — S2-02 slice 1: Langfuse SDK v4 packages, v2 store removed

- Changed: the project owner approved the packages for S2-02 (#16). `requirements.txt` now
  pins `langfuse>=4.16,<5` and `opentelemetry-api`, `opentelemetry-sdk` and
  `opentelemetry-exporter-otlp-proto-http` at `>=1.45,<2`.
  `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67` is approved; S1-05 part B adds it.
  The fixed-versions table in `issues.md` has the new rows. `LangfuseCloudStore` is
  removed; `judge.py` and `live_http.py` use only `SqliteTraceStore`. Plan:
  `changes/2026-10-05-s2-02-langfuse-v4-packages/`. S1-02 was started in a separate
  session while S1-01 waits for the GCP developer to confirm the schema.
- Evidence: new `tests/test_llm_eval_local_store.py` failed 4 of 4 before the change.
  After the change, the fast suite passed (163 passed, 9 deselected) with `langfuse` 4.17.0
  and OTel 1.45.0 from PyPI on Windows. The full suite with the slow bakes passed (172
  passed), so the golden bake did not change. Not run: the frontend checks (no frontend
  change) and a real Langfuse server (not available locally).
- Remaining:
  - S2-02 still needs the `monitor.evaluate` span and `create_score` (after S1-05 part B)
    and the one-trace check (after S2-03).
  - Strict live mode still requires `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`. The
    monitor does not use them until the SDK v4 work. The check stays so that the Replit
    deploy keeps the same secrets.

### 2026-10-05 — S1-02: receiving API `POST /api/batch/runs` (issue #4)

- Changed: new `backend/app/batch_schema.py` (Pydantic model `BatchRunV1` of the S1-01
  draft `batch-run/1`: strict types, unknown fields rejected at every level, the schema's
  `allOf` rules, and the README backend rules: `failed_count` ≤ `request_count`, records ≤
  `sample.size` and ≤ `request_count`, unique `record_id`; errors never echo the input).
  New `backend/app/api/batch_routes.py` (key → size → body → use case → store; W3C
  `traceparent` parser), mounted in both modes; the strict-live middleware lets
  `POST /api/batch/runs` through. `db.py`: table `batch_runs` (migration 8, unique
  `(use_case_id, run_id)`), `put_batch_run` (created / duplicate / `BatchRunConflict`),
  `get_batch_run`, `list_batch_runs`; no update or delete path. `config.py`:
  `BATCH_API_KEY_SHA256`, `BATCH_MAX_BODY_BYTES`, malformed entries reported by position in
  readiness. Change package `changes/2026-10-05-s1-02-batch-runs-api/`. Docs: README,
  `docs/STRICT-LIVE.md` (Batch run receiver), CHANGELOG.
- Evidence: from `backend/` on Windows with the main checkout's `.venv` (Python 3.12,
  pydantic 2.13.5, FastAPI 0.142.2), `python -m pytest -q -m "not slow"` → 247 passed,
  9 deselected (159 before). New: `test_batch_schema.py` (38: the 5 valid and 3 invalid
  S1-01 examples, each rule), `test_batch_runs_api.py` (each acceptance criterion of #4
  behind the strict-live middleware, traceparent cases, a log capture that finds no key,
  hash or record text), `test_batch_runs_store.py` (migration 8 on a new and an old
  database, duplicate, conflict, unique pair). Three tests that list the migration
  versions now expect 8. `scripts/migrate.py` twice on a scratch SQLite file → versions
  1–8 both times. Not run: the slow suite and PostgreSQL (CI runs both); `pnpm` checks (no
  frontend change). Unavailable: a real GCP job (S1-03 paired test), the test host (S1-04).
- Learned: FastAPI 0.142 keeps an included router as one `_IncludedRouter` entry in
  `app.routes`, so a mount test must send a request instead of reading the route paths.
  `datetime.fromisoformat` puts the input in its error message, so the validator raises its
  own message.
- Remaining:
  - The schema is a draft (S1-01). The per-use-case sample-size range (8 to 200) and the
    registry keys come with S2-01; OTel context (S1-05 part B) replaces the header parser.
  - An ADR for push ingest is still open (see 2026-10-02 below).
  - The body limit is checked while the body streams in; a front-door limit (S1-06) is
    still advised.

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
  policy, Alembic, Prometheus metrics, Slack SDK, paging/escalation,
  skops/ONNX artifacts, retention pruning.
