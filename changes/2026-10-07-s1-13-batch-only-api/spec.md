# Spec: serve only the batch MVP API (S1-13)

## Served routes (the allowlist)

| Method and path | Response |
|---|---|
| `POST /api/batch/runs` | Unchanged (S1-02, S1-05) |
| `GET /api/health`, `GET /api/healthz` | Always `200` while the process runs: `{"status": "ok", "service": "model-monitor", "build_sha": "<sha>"}`. No database call. |
| `GET /api/readiness` | `200` `{"status": "ready", "database": {"ok": true, "error": null}, "batch_api_keys": <n>, "errors": []}` or `503` with `"status": "not_ready"` and the errors |
| `GET /api/version` | `200` `{"service": "model-monitor", "build_sha": "<sha>", "batch_schema": "batch-run/1"}`. No outbound call. |

Every other method and path returns `404`. The OpenAPI pages (`/docs`, `/redoc`,
`/openapi.json`) are off. The dashboard is not served.

## Component 1: `backend/app/main.py`

- Sets up logging (`logging_setup.configure(config.LOG_FORMAT)`) and tracing
  (`tracing.setup(app)`), as now.
- Mounts `batch_routes.router` and `ops_routes.router` only.
- Lifespan: at start `db.engine()` (runs the ordered migrations); at stop
  `tracing.shutdown()`.
- Does not import `api.routes`, `api.live_routes`, `api.live_portfolio`, `live_poller` or
  `seeds_loader`. Does not read `CONTROL_TOWER_MODE`. No middleware. No static mount.
- `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`.

## Component 2: `backend/app/api/ops_routes.py`

- `health()` and `healthz()` return the liveness body above.
- `readiness()`:
  1. `database.ok`: `db.engine().connect()` and `SELECT 1`. On an exception:
     `ok: false`, `error: "<ExceptionType>"` (the type name only, never the message,
     because a message can contain a host or a user name).
  2. `errors`: `config.batch_configuration_errors()`, plus `"database is not reachable"`
     when `database.ok` is false.
  3. `batch_api_keys`: `len(config.batch_api_key_hashes())`.
  4. `200` when `errors` is empty, else `503`.
- `version()` returns the version body above.

## Component 3: `config.batch_configuration_errors() -> list[str]`

In this order:
1. `DATABASE_URL is not set (SQLite is for development only)` when it is empty.
2. `DATABASE_URL must use PostgreSQL` when it does not start with `postgres://`,
   `postgresql://` or `postgresql+psycopg://`.
3. `BATCH_API_KEY_SHA256 entries <positions> are malformed (expected USE_CASE_ID:<64 hex>)`
   when an entry is malformed. Positions only, never a hash.
4. `BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)` when no entry is
   valid.

It does not read a `LIVE_*`, Anthropic or Langfuse setting.

## Kept, not used by the app (S4-07 removes them)

`api/routes.py`, `api/live_routes.py`, `api/live_portfolio.py`, `live_poller.py`,
`seeds_loader.py`, `config.live_configuration_errors()`, `config.strict_live_mode()`, and
the `LIVE_*`, `ANTHROPIC_API_KEY` and `LANGFUSE_*` settings.

## Component 4: `backend/tests/prototype_app.py`

The old `main.py` composition, for the prototype tests only: the router chosen by
`CONTROL_TOWER_MODE`, the strict-live route middleware, the lifespan that starts the
poller and seeds the registry, and the old `health`, `healthz`, `version` and `readiness`
handlers. It exports `app`, `strict_live_route_isolation` and `poller`.

## Tests

New `backend/tests/test_app_surface.py`, against `main.app`:

1. The routes of `main.app` are exactly the allowlist (method and path).
2. For `CONTROL_TOWER_MODE` `demo` and `live`, these return `404`: `GET /`, `GET /docs`,
   `GET /openapi.json`, `GET /api/live/portfolio`, `POST /api/live/poll`,
   `POST /api/live/sources/AICT-L01/skip`, `GET /api/registry`, `GET /api/scenario`,
   `GET /api/board`.
3. After the lifespan starts, `live_poller.poller().running` is `False`.
4. `GET /api/health` and `GET /api/healthz` return `200` when `db.engine` raises.
5. `GET /api/readiness`:
   - `200` with a PostgreSQL `DATABASE_URL` value and one valid key (the engine is the
     test SQLite engine).
   - `503` for each case: no `DATABASE_URL`; a non-PostgreSQL URL; no valid key; a
     malformed key (the text names the position and contains no hash); the database
     raises (the error is the type name only).
6. `GET /api/version` returns `build_sha` and makes no outbound call.

Changed tests:

| File | Change |
|---|---|
| `test_batch_runs_api.py`, `test_batch_runs_tracing.py` | Use `main.app`, not a test app with the strict-live middleware. The assertions do not change. |
| `test_strict_live_mode.py`, `test_alert_routes.py`, `test_operator_routes.py`, `test_poller_metrics.py`, `test_realized_view.py` | Use `tests/prototype_app.py` instead of `app.main`. The assertions do not change. |

## CI: `.github/workflows/backend-live.yml`

- The PostgreSQL service image: `postgres:18.6-bookworm` (was `postgres:16`).
- Add `BATCH_API_KEY_SHA256` with a test entry `CI-UC:<sha256 of a test key>`.
- The validation step calls `config.batch_configuration_errors()` and expects `[]`.
- The prototype settings stay, because the prototype tests read them until S4-07.

## Docs

- `CLAUDE.md`: the poller, cursor and demo-route rules are marked "prototype code, not
  mounted since S1-13". New rule: "`main.py` mounts only the batch API; a new route needs
  a plan entry." 120 lines or fewer.
- `README.md`: the first-success readiness example and the API list.
- `docs/STRICT-LIVE.md`: a note at the top that the page describes prototype code that is
  not served since S1-13.
- `changes/2026-10-02-batch-monitoring-mvp/issues.md`: the S1-13 row and section; GitHub
  issue #52 gets the same text.
- `CHANGELOG.md` and `DEVLOG.md`.

## Not tested here

The test host (S1-04) and the Compose smoke test (S1-06, the next task).
