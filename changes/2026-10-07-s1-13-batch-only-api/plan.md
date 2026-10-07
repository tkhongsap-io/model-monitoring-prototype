# Serve only the batch MVP API (S1-13) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The backend app serves only `POST /api/batch/runs`, `/api/health`, `/api/healthz`, `/api/readiness` and `/api/version`; every other path returns `404`, with no mode.

**Architecture:** `main.py` becomes a short composition of two routers (`batch_routes`, new `ops_routes`). The old `main.py` moves unchanged into `backend/tests/prototype_app.py`, so the prototype tests keep running until S4-07. Readiness uses a new `config.batch_configuration_errors()`.

**Tech Stack:** Python 3.12, FastAPI 0.142, SQLAlchemy 2, pytest; GitHub Actions with PostgreSQL 18.6.

**Spec:** [spec.md](spec.md) (approved 2026-10-07). Intent: [intent.md](intent.md).

## Global Constraints

- Served: `POST /api/batch/runs`, `GET /api/health`, `GET /api/healthz`, `GET /api/readiness`, `GET /api/version`. Every other path is `404`; another method on a served path is `405`. No mode; `main.py` does not read `CONTROL_TOWER_MODE`.
- `/api/health` and `/api/healthz`: always `200`, no database call: `{"status": "ok", "service": "model-monitor", "build_sha": "<sha>"}`.
- `/api/readiness`: `200` or `503`; database errors show the exception **type name only**; key errors show **positions only**, never a hash.
- `/api/version`: `{"service": "model-monitor", "build_sha": "<sha>", "batch_schema": "batch-run/1"}`; no outbound call.
- OpenAPI pages off: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`. No SPA mount. No middleware. No poller.
- Do not delete prototype modules (`api/routes.py`, `api/live_routes.py`, `api/live_portfolio.py`, `live_poller.py`, `seeds_loader.py`) or `config.live_configuration_errors()` / `config.strict_live_mode()`. S4-07 removes them.
- No new package. No migration. No change to `batch_routes.py` behavior.
- Tests run from `backend/`: `.venv/bin/python -m pytest ...` (Windows: `.venv\Scripts\python.exe -m pytest ...`).
- Conventional Commits. Branch `feat/s1-13-batch-only-api`.

## Review Focus

- `CONTROL_TOWER_MODE=live` in the environment (CI sets it; Replit sets it) must not bring back any prototype route. (Task 2, `test_prototype_paths_are_404_in_any_mode`.)
- A database exception message can contain a host, a user or a password; readiness must show only the type name. (Task 2, `test_readiness_database_error_shows_type_only`.)
- A `BATCH_API_KEY_SHA256` value with only malformed entries gives two errors (malformed and no valid entry) and no hash text. (Task 2, `test_readiness_reports_batch_configuration_errors`.)
- Another method on a served path (`GET` or `PUT /api/batch/runs`) is `405`, the standard FastAPI answer, not `404`; a longer path (`/api/batch/runs/X`) is `404`. Nothing is stored. (Task 2, `test_get_and_other_methods_are_not_served` in `test_batch_runs_api.py`.)
- The prototype tests must still exercise the prototype composition, not the new app. (Task 1 moves them before Task 2 changes `main.py`.)

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `backend/tests/prototype_app.py` | Create (Task 1) | The old `main.py`, for prototype tests only |
| `backend/tests/test_strict_live_mode.py`, `test_alert_routes.py`, `test_operator_routes.py`, `test_poller_metrics.py`, `test_realized_view.py` | Modify (Task 1) | Import the prototype app from `tests.prototype_app` |
| `backend/app/config.py` | Modify (Task 2) | `batch_configuration_errors()` |
| `backend/app/api/ops_routes.py` | Create (Task 2) | Health, healthz, readiness, version |
| `backend/app/main.py` | Rewrite (Task 2) | Batch-only composition |
| `backend/tests/test_app_surface.py` | Create (Task 2) | The served surface of `main.app` |
| `backend/tests/test_batch_runs_api.py`, `test_batch_runs_tracing.py` | Modify (Task 2) | No strict-live middleware |
| `.github/workflows/backend-live.yml` | Modify (Task 3) | PostgreSQL 18.6, batch key, batch validation |
| `CLAUDE.md`, `README.md`, `docs/STRICT-LIVE.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md` | Modify (Task 3) | Docs |

---

### Task 1: Move the old composition into a test helper

**Files:**
- Create: `backend/tests/prototype_app.py`
- Modify: `backend/tests/test_strict_live_mode.py:7`, `backend/tests/test_alert_routes.py:7,31,39`, `backend/tests/test_operator_routes.py:12,30`, `backend/tests/test_poller_metrics.py:9,132-133`, `backend/tests/test_realized_view.py:132-133`

**Interfaces:**
- Produces: module `tests.prototype_app` with `app` (FastAPI), `strict_live_route_isolation` (middleware function), `poller` (the `live_poller.poller` function) — the same names the tests used from `app.main`.

- [ ] **Step 1: Create the helper from the current `main.py`**

Copy the current file without a change in behavior:

```bash
git show HEAD:backend/app/main.py > backend/tests/prototype_app.py
```

Then edit `backend/tests/prototype_app.py`:
1. Replace the module docstring (lines 1-10) with:

```python
"""The prototype app composition, for prototype tests only (S1-13).

This is `app/main.py` as it was before S1-13: the demo or strict-live router, the
strict-live middleware, the poller lifespan and the SPA mount. The production app
(`app/main.py`) serves only the batch MVP API. S4-07 removes this file with the
prototype code.
"""
```

2. Change the relative imports to absolute imports:

| Before | After |
|---|---|
| `from . import config, db, logging_setup, seeds_loader, tracing` | `from app import config, db, logging_setup, seeds_loader, tracing` |
| `from .api import batch_routes` | `from app.api import batch_routes` |
| `from .live_poller import poller` | `from app.live_poller import poller` |
| `from .api.live_routes import router` | `from app.api.live_routes import router` |
| `from .api.routes import router` | `from app.api.routes import router` |
| `from .api.live_portfolio import LIVE_UCS` | `from app.api.live_portfolio import LIVE_UCS` |
| `from .adapters.telemetry_http import pull_build_version` | `from app.adapters.telemetry_http import pull_build_version` |

3. Change the SPA path line to the same folder as before, from the test location:

```python
_SPA_DIST = Path(__file__).resolve().parents[2] / "artifacts" / "control-tower" / "dist" / "public"
```

(`backend/tests/prototype_app.py` → `parents[2]` is the repository root, the same as for `backend/app/main.py`. Keep the line as it is if it already reads like this.)

- [ ] **Step 2: Point the prototype tests at the helper**

`backend/tests/test_strict_live_mode.py` line 7: `from app.main import app` → `from tests.prototype_app import app`

`backend/tests/test_alert_routes.py`:
- line 7: `from app import config, db, main` → `from app import config, db` and add the line `from tests import prototype_app as main` directly after it.
- No other change: `main.strict_live_route_isolation` and `main.app` now come from the helper.

`backend/tests/test_operator_routes.py` line 12: `from app import config, db, main` → `from app import config, db` and add `from tests import prototype_app as main`.

`backend/tests/test_poller_metrics.py` line 9: `from app import config, db, live_poller, logging_setup, main` → `from app import config, db, live_poller, logging_setup` and add `from tests import prototype_app as main`.

`backend/tests/test_realized_view.py` line 132: `from app.main import app` → `from tests.prototype_app import app`

- [ ] **Step 3: Run the moved tests**

Run: `.venv/bin/python -m pytest -q tests/test_strict_live_mode.py tests/test_alert_routes.py tests/test_operator_routes.py tests/test_poller_metrics.py tests/test_realized_view.py`
Expected: all passed (the same count as on `dev`).

Run: `.venv/bin/python -m pytest -q -m "not slow"`
Expected: all passed, 9 deselected. `main.py` has not changed yet.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/prototype_app.py backend/tests/test_strict_live_mode.py backend/tests/test_alert_routes.py backend/tests/test_operator_routes.py backend/tests/test_poller_metrics.py backend/tests/test_realized_view.py
git commit -m "test(s1-13): move the prototype app composition into a test helper"
```

---

### Task 2: Batch-only `main.py`, `ops_routes` and readiness configuration

**Files:**
- Modify: `backend/app/config.py` (add a function after `batch_api_key_hashes`, about line 150)
- Create: `backend/app/api/ops_routes.py`
- Rewrite: `backend/app/main.py`
- Create: `backend/tests/test_app_surface.py`
- Modify: `backend/tests/test_batch_runs_api.py:18,39-50`, `backend/tests/test_batch_runs_tracing.py:15,38-43`

**Interfaces:**
- Consumes: `tests.prototype_app` (Task 1) — the prototype tests no longer import `app.main`.
- Produces:
  - `config.batch_configuration_errors() -> list[str]`
  - `app.api.ops_routes.router` (APIRouter, prefix `/api`) with `health`, `healthz`, `readiness`, `version`
  - `app.main.app` with exactly the five served routes

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_app_surface.py`:

```python
"""S1-13: the app serves only the batch MVP API."""
from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app import config, db, live_poller, main

GOOD_KEY = "test-key-surface-" + "a" * 32
GOOD_ENTRY = "GCP-UC-03:" + hashlib.sha256(GOOD_KEY.encode()).hexdigest()
PG_URL = "postgresql://monitor:secret-password@db.internal:5432/monitor"
ALLOWLIST = {
    ("/api/batch/runs", "post"),
    ("/api/health", "get"),
    ("/api/healthz", "get"),
    ("/api/readiness", "get"),
    ("/api/version", "get"),
}


@pytest.fixture()
def ready_config(isolated_db, monkeypatch):
    """A PostgreSQL URL value and one valid key; the engine is the test SQLite engine."""
    db.engine()                                   # build the SQLite engine first
    monkeypatch.setattr(config, "DATABASE_URL", PG_URL)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", GOOD_ENTRY)


def test_served_routes_are_exactly_the_allowlist():
    paths = main.app.openapi()["paths"]
    served = {(path, method) for path, ops in paths.items() for method in ops}
    assert served == ALLOWLIST


@pytest.mark.parametrize("mode", ["demo", "live"])
@pytest.mark.parametrize("method, path", [
    ("GET", "/"), ("GET", "/docs"), ("GET", "/redoc"), ("GET", "/openapi.json"),
    ("GET", "/api/live/portfolio"), ("POST", "/api/live/poll"),
    ("POST", "/api/live/sources/AICT-L01/skip"), ("GET", "/api/registry"),
    ("GET", "/api/scenario/state"), ("GET", "/api/board"), ("GET", "/heatmap"),
])
def test_prototype_paths_are_404_in_any_mode(monkeypatch, mode, method, path):
    monkeypatch.setattr(config, "CONTROL_TOWER_MODE", mode)
    assert TestClient(main.app).request(method, path).status_code == 404


def test_poller_does_not_start(ready_config):
    with TestClient(main.app):
        assert live_poller.poller().running is False


def test_health_needs_no_database(monkeypatch):
    def broken():
        raise RuntimeError("database is down")

    monkeypatch.setattr(db, "engine", broken)
    client = TestClient(main.app)                 # no lifespan: no startup database call
    for path in ("/api/health", "/api/healthz"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "model-monitor",
                                   "build_sha": config.BUILD_SHA}


def test_readiness_ready(ready_config):
    with TestClient(main.app) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready", "database": {"ok": True, "error": None},
                               "batch_api_keys": 1, "errors": []}


@pytest.mark.parametrize("url, entries, expected", [
    ("", GOOD_ENTRY, ["DATABASE_URL is not set (SQLite is for development only)"]),
    ("sqlite:///x.db", GOOD_ENTRY, ["DATABASE_URL must use PostgreSQL"]),
    (PG_URL, "", ["BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)"]),
    (PG_URL, f"bad-entry, {GOOD_ENTRY}",
     ["BATCH_API_KEY_SHA256 entries 1 are malformed (expected USE_CASE_ID:<64 hex>)"]),
    (PG_URL, "bad-entry, GCP-UC-07:" + "z" * 64,
     ["BATCH_API_KEY_SHA256 entries 1, 2 are malformed (expected USE_CASE_ID:<64 hex>)",
      "BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)"]),
])
def test_readiness_reports_batch_configuration_errors(ready_config, monkeypatch,
                                                      url, entries, expected):
    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", entries)
    with TestClient(main.app) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready" and body["errors"] == expected
    assert "z" * 64 not in response.text and "bad-entry" not in response.text


def test_batch_configuration_errors_ignore_prototype_settings(ready_config, monkeypatch):
    for name in ("LIVE_CHURN_URL", "LIVE_CHATBOT_URL", "LIVE_NBA_URL", "LIVE_PRODUCER_URL",
                 "LIVE_TELEMETRY_TOKEN", "LIVE_WORKER_TOKEN", "ANTHROPIC_API_KEY",
                 "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.setattr(config, name, "")
    assert config.batch_configuration_errors() == []


def test_readiness_database_error_shows_type_only(ready_config, monkeypatch):
    class SecretError(Exception):
        pass

    def broken():
        raise SecretError("password=secret-password host=db.internal")

    client = TestClient(main.app)                 # no lifespan: startup would raise
    monkeypatch.setattr(db, "engine", broken)
    response = client.get("/api/readiness")
    assert response.status_code == 503
    body = response.json()
    assert body["database"] == {"ok": False, "error": "SecretError"}
    assert body["errors"] == ["database is not reachable"]
    assert "secret-password" not in response.text and "db.internal" not in response.text


def test_version_makes_no_outbound_call(monkeypatch):
    import httpx

    def no_network(*args, **kwargs):
        raise AssertionError("no outbound call expected")

    monkeypatch.setattr(httpx, "get", no_network)
    monkeypatch.setattr(httpx.Client, "send", no_network)
    response = TestClient(main.app).get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"service": "model-monitor", "build_sha": config.BUILD_SHA,
                               "batch_schema": "batch-run/1"}
```

In `backend/tests/test_batch_runs_api.py`:
- line 18: `from app import config, db, main, tracing` → `from app import config, db, main`
- replace the `client` fixture (lines 39-50) with:

```python
@pytest.fixture()
def client(isolated_db, monkeypatch) -> TestClient:
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{sha(KEY_03)}, GCP-UC-07:{sha(KEY_07)}")
    with TestClient(main.app) as c:              # the app that is deployed (S1-13)
        yield c
```

- `FastAPI` is no longer used in this file: remove `from fastapi import FastAPI` if no other line uses it.
- Replace the test `test_get_and_other_methods_unreachable_in_strict_mode` with:

```python
def test_get_and_other_methods_are_not_served(client):
    # the strict-live middleware answered 404; without it FastAPI answers 405 for another
    # method on a served path (S1-13). Nothing is stored either way.
    assert client.get(URL).status_code == 405
    assert client.put(URL, json={}, headers=AUTH).status_code == 405
    assert client.get("/api/batch/runs/GCP-UC-03").status_code == 404
    assert rows() == []
```

In `backend/tests/test_batch_runs_tracing.py`:
- line 15: `from app import config, db, main, tracing` → `from app import config, db, tracing`
- in `_strict_app()`, delete the line `app.middleware("http")(main.strict_live_route_isolation)`. Keep the rest: these tests replace `tracing.PROVIDER`, so they need a new app that `tracing.setup` instruments after the replacement.

- [ ] **Step 2: Run the new tests to make sure they fail**

Run: `.venv/bin/python -m pytest -q tests/test_app_surface.py`
Expected: FAIL. `test_served_routes_are_exactly_the_allowlist` shows the prototype routes; `test_readiness_*` fail on `AttributeError: module 'app.config' has no attribute 'batch_configuration_errors'` or on the old body shape.

- [ ] **Step 3: Write the implementation**

In `backend/app/config.py`, directly after the function `batch_api_key_hashes()`, add:

```python
def batch_configuration_errors() -> list[str]:
    """Readiness blockers of the batch MVP app (S1-13).

    Only the batch settings count: the prototype settings (`LIVE_*`, Anthropic, Langfuse)
    are not read.  A malformed key entry is named by position only, never by its text.
    """
    errors: list[str] = []
    if not DATABASE_URL:
        errors.append("DATABASE_URL is not set (SQLite is for development only)")
    elif not DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        errors.append("DATABASE_URL must use PostgreSQL")
    entries = _batch_key_entries()
    malformed = [str(position) for position, pair in entries if pair is None]
    if malformed:
        errors.append(f"BATCH_API_KEY_SHA256 entries {', '.join(malformed)} are malformed "
                      "(expected USE_CASE_ID:<64 hex>)")
    if not any(pair is not None for _, pair in entries):
        errors.append("BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)")
    return errors
```

Create `backend/app/api/ops_routes.py`:

```python
"""Service checks of the batch MVP app (S1-13): liveness, readiness and version.

`/api/health` and `/api/healthz` are liveness checks: they answer while the process runs
and never touch the database, so a database problem does not make Docker restart the app.
`/api/readiness` answers whether a batch run can be stored now.  No answer contains a
secret: a database error is reported by its type name only, and a key entry by position.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import config, db
from ..batch_schema import SCHEMA_VERSION

router = APIRouter(prefix="/api")
SERVICE = "model-monitor"


def _liveness() -> dict:
    return {"status": "ok", "service": SERVICE, "build_sha": config.BUILD_SHA}


@router.get("/health")
def health():
    return _liveness()


@router.get("/healthz")
def healthz():
    return _liveness()


@router.get("/readiness")
def readiness():
    database = {"ok": True, "error": None}
    try:
        with db.engine().connect() as cx:
            cx.exec_driver_sql("SELECT 1")
    except Exception as exc:  # noqa: BLE001 — report, never raise; type name only
        database = {"ok": False, "error": type(exc).__name__}
    errors = config.batch_configuration_errors()
    if not database["ok"]:
        errors.append("database is not reachable")
    body = {"status": "ready" if not errors else "not_ready", "database": database,
            "batch_api_keys": len(config.batch_api_key_hashes()), "errors": errors}
    return JSONResponse(body, status_code=200 if not errors else 503)


@router.get("/version")
def version():
    return {"service": SERVICE, "build_sha": config.BUILD_SHA, "batch_schema": SCHEMA_VERSION}
```

Replace the whole content of `backend/app/main.py` with:

```python
"""FastAPI app of the October batch MVP (S1-13).

It serves only the batch MVP API: `POST /api/batch/runs` (S1-02, S1-05) and the service
checks in `api/ops_routes.py`.  Every other path returns 404.  There is no mode: the
prototype code (demo and strict-live routers, the pull-lane poller, the dashboard) stays in
the repository until S4-07, but this module does not import it.  The prototype tests build
the old composition from `tests/prototype_app.py`.

Startup runs the ordered migrations (`db.engine()`); shutdown sends the remaining spans.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import config, db, logging_setup, tracing
from .api import batch_routes, ops_routes

logging_setup.configure(config.LOG_FORMAT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.engine()
    try:
        yield
    finally:
        tracing.shutdown()


app = FastAPI(title="Batch run monitor", version="batch-mvp", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(batch_routes.router)
app.include_router(ops_routes.router)
tracing.setup(app)  # only POST /api/batch/runs makes spans (S1-05)
```

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `.venv/bin/python -m pytest -q tests/test_app_surface.py tests/test_batch_runs_api.py tests/test_batch_runs_tracing.py tests/test_tracing.py`
Expected: all passed.

Run: `.venv/bin/python -m pytest -q -m "not slow"`
Expected: all passed, 9 deselected. If a test outside this task imports `app.main` for a prototype route, change it to `tests.prototype_app` (the same pattern as Task 1) and record it.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/api/ops_routes.py backend/app/main.py backend/tests/test_app_surface.py backend/tests/test_batch_runs_api.py backend/tests/test_batch_runs_tracing.py
git commit -m "feat(s1-13): serve only the batch MVP API; batch-only readiness"
```

---

### Task 3: CI, docs and plan text

**Files:**
- Modify: `.github/workflows/backend-live.yml`
- Modify: `CLAUDE.md`, `README.md`, `docs/STRICT-LIVE.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `CHANGELOG.md`, `DEVLOG.md`

**Interfaces:**
- Consumes: `config.batch_configuration_errors()` (Task 2).

- [ ] **Step 1: Change CI**

In `.github/workflows/backend-live.yml`:
- `image: postgres:16` → `image: postgres:18.6-bookworm`
- In the job `env:` block, after `LIVE_POLL_SECONDS: "5"`, add:

```yaml
      # batch MVP (S1-13): a test entry; sha256 of "ci-batch-key-not-a-secret-000000000000"
      BATCH_API_KEY_SHA256: CI-UC:<HASH>
```

  Replace `<HASH>` with the output of:
  `python -c "import hashlib; print(hashlib.sha256(b'ci-batch-key-not-a-secret-000000000000').hexdigest())"`
- Replace the step `Validate strict-live configuration` with:

```yaml
      - name: Validate batch MVP configuration
        run: python -c "from app import config; assert config.batch_configuration_errors() == [], config.batch_configuration_errors()"
```

- Keep the prototype settings in `env:`; the prototype tests read them until S4-07.

- [ ] **Step 2: Change the docs**

`CLAUDE.md`, section "Architecture and code rules":
- Replace the two bullets that start with "The browser never advances telemetry cursors." and "Demo and scenario routes return 404 in strict live mode" with:

```markdown
- `backend/app/main.py` mounts only the batch MVP API (`api/batch_routes.py`,
  `api/ops_routes.py`); every other path is 404, with no mode (S1-13). A new route needs
  a plan entry. The prototype code (demo and strict-live routers, `live_poller.py`, the
  dashboard) is not mounted; its tests use `backend/tests/prototype_app.py`; S4-07
  removes it.
```

- Keep `CLAUDE.md` at 120 lines or fewer (`tests/test_docs.py` checks it).

`README.md`:
- In "First success", replace the paragraph that starts "To see the API, from `backend/` run" with:

```markdown
To see the API, from `backend/` run
`.venv/bin/python -m uvicorn app.main:app --port 8000` and open
`http://127.0.0.1:8000/api/health`. It returns HTTP 200 with `{"status": "ok", ...}`.
`/api/readiness` returns 503 with the missing batch settings (`DATABASE_URL`,
`BATCH_API_KEY_SHA256`) until they are set. The app serves only the batch MVP API
(S1-13); see `changes/2026-10-07-s1-13-batch-only-api/spec.md`.
```

- In "Release and operations", in the "Monitoring" bullet, replace the text about `GET /api/live/sync`, `GET /api/live/alerts` and `autoscale-poll.yml` with: "`GET /api/readiness` (database and batch settings). The prototype endpoints are not served since S1-13."

`docs/STRICT-LIVE.md`: directly under the H1, before the existing "Prototype only" note, add:

```markdown
> **Not served since S1-13.** `app/main.py` mounts only the batch MVP API. This page
> describes prototype code that stays in the repository until S4-07; only the "Batch run
> receiver" section applies to the running app.
```

`changes/2026-10-02-batch-monitoring-mvp/issues.md`:
- In the Sprint 1 summary table, after the `S1-12` row, add:

```markdown
| S1-13 | Serve only the batch MVP API | Feature | Backend | S1-06 | M |
```

- After the whole `### S1-12` section (before the `---` line that ends Sprint 1), add a `### S1-13 — Serve only the batch MVP API (prototype routes not mounted)` section with the body of GitHub issue #52 (`gh issue view 52 --json body --jq .body`), without its last `---` footer.

`CHANGELOG.md`, under `## [Unreleased]`:
- In `### Changed`, add as the first bullet:

```markdown
- The backend serves only the batch MVP API: `POST /api/batch/runs`, `/api/health`,
  `/api/healthz`, `/api/readiness` and `/api/version`. Health is a liveness check (no
  database call); readiness checks only `DATABASE_URL` (PostgreSQL) and
  `BATCH_API_KEY_SHA256`. CI uses PostgreSQL 18.6 (S1-13).
```

- In `### Deprecated or removed`, add as the first bullet:

```markdown
- Not served any more (S1-13): the demo and strict-live prototype routes, the operator
  routes, the pull-lane poller, the dashboard and the OpenAPI pages. The code stays until
  S4-07.
```

`DEVLOG.md`: add an entry at the top of `## Work log`:

```markdown
### 2026-10-07 — S1-13: serve only the batch MVP API

- Changed: `main.py` mounts only `batch_routes` and the new `ops_routes`; no mode, no
  poller, no middleware, no dashboard, no OpenAPI pages. `config.batch_configuration_errors()`.
  The old composition is `backend/tests/prototype_app.py` for the prototype tests. CI uses
  `postgres:18.6-bookworm` and validates the batch settings. Change package
  `changes/2026-10-07-s1-13-batch-only-api/`.
- Evidence: <fast suite result>; <full suite result>; `tests/test_docs.py` <result>.
  Not run: the test host (S1-04), the Compose smoke test (S1-06, next).
- Remaining: the dashboard returns with S2-07. S1-06 builds the Compose stack on this app.
```

- [ ] **Step 3: Run every required check**

Run: `.venv/bin/python -m pytest -q -m "not slow"` — expected: all passed, 9 deselected.
Run: `.venv/bin/python -m pytest -q` — expected: all passed.
Run: `.venv/bin/python -m pytest -q tests/test_docs.py` — expected: 5 passed.
Put the results in the DEVLOG entry instead of the `<...>` text.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/backend-live.yml CLAUDE.md README.md docs/STRICT-LIVE.md changes/2026-10-02-batch-monitoring-mvp/issues.md CHANGELOG.md DEVLOG.md
git commit -m "docs(s1-13): batch-only API in CI and docs; S1-13 plan text"
```

Do not push and do not open a pull request; the reviewer does that.
