# Spec: the dashboard shows the GCP use cases (S2-07)

Intent: [intent.md](intent.md). Issue: S2-07 (#21).

## Names (use exactly these words in code comments, docs and logs)

| Name | What it is | Where |
|---|---|---|
| **front door** | The existing nginx that routes every request on the VM (S1-06). It does not serve app files. | Compose project `nginx`, service `nginx`, config `deploy/nginx/conf.d/*.conf`; host ports 80 (jobs), 3000 (Langfuse UI), **8082 (dashboard, new)** |
| **dashboard** | The new Compose service that holds the built dashboard files | Compose project `model-monitor`, service `dashboard`, network alias `model-monitor-dashboard`, image `…/dev/dashboard:<run number>` |
| **dashboard file server** | The small web server **inside** the dashboard image (nginx-unprivileged). It only hands out `dist/`. Never call it "the nginx". | `deploy/dashboard/file-server.conf`; port **8090**, inside Docker only, no published port |
| **dashboard API** | The 3 read-only routes `/api/live/*` of the backend | `backend/app/api/dashboard_routes.py`, view in `backend/app/dashboard_view.py` |
| **job API** | `POST /api/batch/runs` (S1-02), on front-door port 80 only | unchanged |

Ports in one place: front door 80 / 3000 / 8082 (host) and 8080 / 3000 / 8082 (container;
`127.0.0.1:8081` is its own health check); backend 8000; dashboard file server 8090;
Langfuse web 3000 (inside Docker).
## Files

| File | Change |
|---|---|
| `backend/app/dashboard_view.py` | New, pure. Registry entry + latest run + evaluations → the row and detail dicts the UI reads. |
| `backend/app/api/dashboard_routes.py` | New. `GET /api/live/portfolio`, `/api/live/use-case/{use_case_id}`, `/api/live/alerts`. |
| `backend/app/db.py` | New read functions for the dashboard (no schema change). |
| `backend/app/main.py` | Mount `dashboard_routes.router`; docstring names the new routes. |
| `deploy/dashboard/Dockerfile` | New. Multi-stage build of `artifacts/control-tower` (build context: repository root). |
| `deploy/dashboard/file-server.conf` | New. The configuration of the **dashboard file server** inside the dashboard image (port 8090). |
| `.dockerignore` | New or changed: keep `node_modules`, `.git`, `.env*`, `backend/.venv` out of the build context. |
| `deploy/nginx/conf.d/dashboard.conf` | New. Port 8082: the dashboard and the read-only API paths. |
| `deploy/nginx/compose.local.yaml`, `compose.testhost.yaml` | Publish port 8082 (`127.0.0.1:8082:8082` locally, `8082:8082` on the test host). |
| `deploy/compose/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml` | New service `dashboard` (alias `model-monitor-dashboard` on `edge`); local builds it, the test host uses `${DASHBOARD_IMAGE}`. |
| `.github/workflows/build-image.yml` | Also builds and pushes `…/dev/dashboard:<run number>`. |
| `.github/workflows/compose-smoke.yml` | Its paths also cover `artifacts/control-tower/**` and `deploy/dashboard/**`. |
| `scripts/compose-smoke.sh` | New dashboard checks. |
| `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md` | Docs. |
| `backend/tests/…` | Tests (section "Tests"). |

`artifacts/control-tower/src/**` does **not** change.

## Read functions (`backend/app/db.py`)

- `latest_batch_run(use_case_id) -> dict | None`: the row with the newest `received_at`.
- `latest_evaluation(batch_run_id) -> dict | None`: for `BANDS_VERSION`.
- `evaluation_history(use_case_id, limit=20) -> list[dict]`: newest first, by `evaluated_at`.

## View (`backend/app/dashboard_view.py`)

Pure functions; no I/O, no clock (`now` is a parameter), never raises for stored data.

```python
UI_LANES = ["Quality", "Safety & security", "Reliability", "Drift & degradation",
            "Feedback & action loop"]
LANE_OF = {"run_status": "Delivery", "turnaround_s": "Delivery",
           "failure_rate": "Reliability", "volume_change": "Drift & degradation",
           "valid_output_rate": "Quality", "block_rate": "Safety & security"}

def portfolio_row(use_case, run: dict | None, evaluation: dict | None, now: float) -> dict
def detail(use_case, run: dict | None, evaluation: dict | None,
           history: list[dict], now: float) -> dict
def summary(rows: list[dict], now: float) -> dict
```

### Row (`portfolio_row`)

| Field | Value |
|---|---|
| `registry_id` | `use_case.use_case_id` |
| `use_case_name` | `use_case.name` |
| `business_unit` | `use_case.owner` |
| `platform_or_app` | `"GCP batch job"` |
| `risk_tier` | `None` |
| `lane_kind` | `"llm"` |
| `status` | the latest run's `status`, or `"no run yet"` |
| `overall`, `current_health` | the evaluation's `grade`; `"Unknown"` with no evaluation |
| `lanes` | the 5 `UI_LANES`: `Reliability` = health of `failure_rate`, `Drift & degradation` = health of `volume_change`, the other three `"Unknown"`; all `"Unknown"` with no evaluation |
| `tooltips` | `{lane: {"metric": text}}`, see below |
| `feedback_unknown_reason` | `"no feedback source in October"` |
| `state` | `at_tail` when `now − completed_at ≤ expected_every_s + grace_s`; `stale` when older or the time cannot be read; `idle` with no run |
| `window_id` | `run_id` |
| `observation_id`, `trace_id` | the run's `trace_id` |
| `batch_id` | `batch_run_id` |
| `content_sha256` | the run's `content_sha256` |
| `model_version` | the run's `model` |
| `record_count` | the run's `record_count` |
| `last_success_at` | the run's `completed_at` |
| `grade`, `delivery_grade`, `bands_version` | from the evaluation, else `None` |
| `backlog`, `source_lag_ms`, `source_tick`, `observed_tick` | `None` |

Tooltips (`metric` text):
- `Reliability`: `failure_rate <value as %> (<health>)`, or `failure_rate Unknown: <reason>`
- `Drift & degradation`: `volume_change <value with 2 decimals> (<health>)`, or `volume_change Unknown: <reason>`
- `Quality`, `Safety & security`: `Unknown: records not approved`
- `Feedback & action loop`: `Unknown: no feedback source in October`
- No run: every lane `Unknown: no run yet`. A run but no evaluation: every lane `Unknown: not graded yet`.

Reason texts (UI wording for the S2-05 reasons): `no_requests` → "no requests in the run",
`no_baseline` → "no baseline: needs 5 earlier runs", `not_reported` → "not reported: no
limit in the registry or no submitted_at", `invalid_times` → "the run times cannot be read",
`invalid_counts` → "the run counts cannot be read", `invalid_status` → "unknown run status",
`records_not_approved` → "records not approved".

### Detail (`detail`)

The row fields, plus:

| Field | Value |
|---|---|
| `source_record_id` | `"registry: batch-use-cases.yaml"` |
| `business_owner`, `system_owner` | `use_case.owner` |
| `technical_owner` | `use_case.developer` |
| `monitoring_owner` | `"RAI team"` |
| `model_or_route` | the run's `model` |
| `data_sources` | `"<data_classification> (identity-only: no records)"` when `mode` is `identity_only`, else `"<data_classification>"` |
| `last_reviewed`, `next_review` | `None` |
| `judge` | `None`; `judge_sample` `[]` |
| `evidence_note` | `"no run yet"`, `"not graded yet"`, or `"graded with bands <bands_version>"` |
| `signals` | 6 rows (below); `[]` with no evaluation |

Signal row: `key`, `label`, `lane` (`LANE_OF`), `value`, `unit`, `direction`, `green_bar`,
`red_bar`, `health`, `pending_reason` (the reason text, `None` when known), `history`
(`[{tick, value, health}]` from `history`, oldest first, ticks 0, 1, 2…).

| key | label | unit | direction | green_bar | red_bar |
|---|---|---|---|---|---|
| `run_status` | Run status | `status` | `lower_is_better` | `"completed"` | `"failed"` |
| `turnaround_s` | Turnaround | `seconds` | `lower_is_better` | L | 2L (L = `turnaround_limit_s`; with no limit: `"limit"`, `"2 × limit"` and unit `s`) |
| `failure_rate` | Failure rate | `fraction` | `lower_is_better` | 0.01 | 0.05 |
| `volume_change` | Volume change (Green 0.7–1.3) | `ratio` | `higher_is_better` | 0.7 | 0.4 |
| `valid_output_rate` | Valid output rate | `fraction` | `higher_is_better` | 0.99 | 0.95 |
| `block_rate` | Block rate | `fraction` | `lower_is_better` | 0.01 | 0.05 |

### Summary (`summary`)

`use_case_count`, `as_of` (`{id: None}`), `overall_counts` (`{health: n}`), `lane_counts`
(`{lane: {health: n}}` over `UI_LANES`), `open_alerts` `{}`, `sync_state` (the worst row
state: `stale` > `idle` > `at_tail`; `idle` with no rows), `generated_at` (ISO UTC of `now`),
`build` `{"git_sha": config.BUILD_SHA}`.

## Routes (`backend/app/api/dashboard_routes.py`)

- `GET /api/live/portfolio` → `{**summary(rows), "rows": rows}` over the use cases of
  `registry.current()`, in registry order.
- `GET /api/live/use-case/{use_case_id}` → `detail(...)`; `404 {"detail": "unknown use case"}`
  when the ID is not in the registry.
- `GET /api/live/alerts` → `{"contract_version": "1.1", "redacted": True, "rows": []}`
  (query parameters are ignored).
- A database error gives `503 {"detail": "database is not reachable", "error": <class name>}`.
- No route returns `payload`, a record, a key or a token. Every response is built from the
  view functions, never from a whole stored row.
- `main.py` mounts the router. `test_app_surface.py`'s allowlist gets the 3 paths.

## Dashboard image (`deploy/dashboard/`)

`Dockerfile` (build context: repository root):

1. Stage `build`: a pinned Node 24 Alpine image (the plan names the exact tag, checked to
   exist), `corepack enable`, pnpm 10.15.1, copy the
   workspace files and `artifacts/control-tower`, `pnpm install --frozen-lockfile`, then
   `PORT=8090 BASE_PATH=/ CONTROL_TOWER_MODE=live pnpm run build:live` and
   `pnpm run check:strict-live`.
2. Stage `serve`: `nginxinc/nginx-unprivileged:1.28.0-alpine` (the same pin as the front
   door), copy `artifacts/control-tower/dist/public` to `/usr/share/nginx/html` and
   `deploy/dashboard/file-server.conf` to `/etc/nginx/conf.d/default.conf`. Port 8090, non-root.

`file-server.conf` (the dashboard file server, inside the image):
- `listen 8090; server_tokens off;`
- `location = /index.html` and `location /`: `try_files $uri $uri/ /index.html;` with
  `Cache-Control: no-cache` for `index.html`.
- `location /assets/`: `try_files $uri =404;` with `Cache-Control: public, max-age=31536000, immutable`.
- `location = /healthz`: `200`.

## Front door (`deploy/nginx/conf.d/dashboard.conf`)

```nginx
# Dashboard (S2-07). RAI team and engineers, through the IAP tunnel to host port 8082.
server {
    listen 8082;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    set $mm_backend http://model-monitor-backend:8000;
    set $mm_dashboard http://model-monitor-dashboard:8090;

    location = /api/live/portfolio { limit_except GET { deny all; } proxy_pass $mm_backend; }
    location ^~ /api/live/use-case/ { limit_except GET { deny all; } proxy_pass $mm_backend; }
    location = /api/live/alerts { limit_except GET { deny all; } proxy_pass $mm_backend; }
    location = /api/version { limit_except GET { deny all; } proxy_pass $mm_backend; }
    location /api/ { return 404; }
    location / { limit_except GET { deny all; } proxy_pass $mm_dashboard; }
}
```

(`limit_except` is valid only inside `location`; the plan writes it in each location. A
denied method gives `403`. `deny` is the nginx way; the spec accepts `403` for "refused".)

## Compose

- `compose.yaml`: service `dashboard` with a health check (`wget` on `127.0.0.1:8090/healthz`),
  `restart: unless-stopped`, networks `edge` with alias `model-monitor-dashboard`. No port.
- `compose.local.yaml`: `dashboard` builds `context: ../..`, `dockerfile: deploy/dashboard/Dockerfile`,
  image `model-monitor-dashboard:local`.
- `compose.testhost.yaml`: `dashboard.image: ${DASHBOARD_IMAGE:?DASHBOARD_IMAGE is not set}`.

## CI

- `build-image.yml`: a second job (or second build step) for `…/dev/dashboard:<run number>`;
  paths also `artifacts/control-tower/**`, `deploy/dashboard/**`, `pnpm-lock.yaml`. The
  backend and dashboard of one run share the run number.
- `scripts/compose-smoke.sh` after the existing checks:
  1. `GET http://127.0.0.1:8082/` → `200` and the body contains `<div id="root">`.
  2. `GET :8082/api/live/portfolio` → `200`; `rows` has `rtr-fraud-validation` with `overall`
     set (after the run is graded).
  3. `GET :8082/api/live/use-case/rtr-fraud-validation` → `200`, `trace_id` equals the smoke
     trace ID, and the body has no `payload` key.
  4. `POST :8082/api/batch/runs` → `403` or `404`; `GET :8082/api/readiness` → `404`.
- `strict-live-frontend.yml` already checks the frontend on any change under
  `artifacts/control-tower/**`.

## Test host

TESTHOST "Dashboard (S2-07)":
1. Firewall: `gcloud compute firewall-rules update langfuse-testhost-allow-iap --rules tcp:3000,tcp:8082`.
2. Copy `deploy/nginx/conf.d/dashboard.conf`, the nginx `compose.testhost.yaml` and the
   monitor `compose.yaml` and `compose.testhost.yaml`.
3. In `/opt/model-monitor/compose/.env`: set `BACKEND_IMAGE` and `DASHBOARD_IMAGE` to the
   same new run number; `pull`; `up -d --wait`; restart nginx.
4. On the laptop: `gcloud compute start-iap-tunnel ai-ml-monitoring-dev-env 8082 --local-host-port=localhost:8082 --zone asia-southeast3-c`
   (or VS Code port forwarding), then open `http://localhost:8082`.

## Tests

| File | Covers |
|---|---|
| `test_dashboard_view.py` | Each state: graded; each Unknown reason text; no run (`idle`); run without evaluation; `stale` vs `at_tail` at the exact limit; lane mapping; the 6 signal rows and their bands; history order; `summary` counts and worst state |
| `test_dashboard_routes.py` | Shape: every field the UI reads (`rows`, 5 lane names, `overall`, `signals`, `trace_id`); registry order; `404`; `503` with class name only; alerts empty; a run whose body has the S1-01 example texts → no response contains those texts or `payload` |
| `test_app_surface.py` | The allowlist has the 3 new GET paths |
| `test_nginx_files.py` | `dashboard.conf`: port 8082, the 4 API paths, `location /api/ { return 404; }`, `limit_except GET` in each location; local `127.0.0.1:8082:8082`, test host `8082:8082` |
| `test_compose_files.py` | The `dashboard` service in the three files; no published port in `compose.yaml` |
| `test_dashboard_files.py` | Dockerfile: two pinned stages, `--frozen-lockfile`, `check:strict-live`, non-root base; `file-server.conf`: SPA fallback, cache headers, `/assets/` `=404` |

## Not in scope

Alerting; a Delivery column; risk tiers; IT's HTTPS load balancer; Windows `vite dev`.
