# Model Monitoring Prototype

Strict-live AI observability control tower for the `ai-use-cases` producer. The monitor
pulls authenticated telemetry, persists cursors and observations in its own PostgreSQL
database, evaluates real closed windows, and acknowledges matching window digests back
to the producer. Production never serves baked scenario data.

## Run and operate

- `bash scripts/deploy-build.sh` — install dependencies, run migrations, and build the SPA
- `bash scripts/deploy-run.sh` — start the single-port strict-live deployment
- `cd backend && .venv/bin/python -m pytest tests` — backend regression suite
- `cd frontend && pnpm typecheck && pnpm build` — frontend validation

The root `.replit` publishes an Autoscale deployment. `scripts/deploy-run.sh` always sets
`CONTROL_TOWER_MODE=live`; local demo mode must use a separate development command.

## Required Replit Secrets

- `DATABASE_URL` — monitor-owned managed PostgreSQL, never the producer database
- `LIVE_CHURN_URL`, `LIVE_CHATBOT_URL`, `LIVE_NBA_URL` — producer gateway service prefixes
- `LIVE_PRODUCER_URL` — producer gateway root for version checks and acknowledgements
- `LIVE_TELEMETRY_TOKEN` — same value as producer `RAI_TELEMETRY_TOKEN`
- `LIVE_WORKER_TOKEN` — same value as GitHub secret `MONITOR_WORKER_TOKEN`
- `ANTHROPIC_API_KEY` — real Claude judge
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `LIVE_POLL_SECONDS` — positive warm-instance polling interval

`.env` files are excluded from Replit deployment images. Use Replit Secrets for runtime
credentials. `ALLOW_INSECURE_LIVE_TESTING` must remain unset in production.

## Architecture and evidence

- Browser presence never advances telemetry; the backend poller owns progress.
- A PostgreSQL lease elects one polling process across Autoscale instances, and a local
  cycle guard prevents concurrent wake/background cycles inside one process.
- Window IDs and SHA-256 content digests are persisted before cursors advance.
- Public live APIs expose redacted observations only; demo/scenario routes return 404.
- `GET /api/readiness`, `/api/version`, and `/api/live/sync` are the release diagnostics.

The source of truth is `docs/MONITORING-CONTRACT.md`; deployment safety and exact URL
mapping are documented in `docs/STRICT-LIVE.md` and `docs/LIVE-DEMO.md`.
