# Backend OpenTelemetry for batch runs (S1-05 part B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One GCP batch run is one trace: the backend continues the job's trace with a FastAPI server span and a `monitor.ingest` span, and stores the same trace ID in `batch_runs`.

**Architecture:** A new `backend/app/tracing.py` owns one `TracerProvider` (OTLP/HTTP export only when an endpoint is set) and instruments a FastAPI app so that only `POST /api/batch/runs` makes spans. `batch_routes.py` runs its handler inside `monitor.ingest` and takes the trace ID from the span context instead of the hand-written `parse_traceparent`. `db.BatchRunConflict` carries the stored trace ID for the `stored_trace_id` span attribute.

**Tech Stack:** Python 3.12, FastAPI 0.142, OpenTelemetry SDK 1.45, `opentelemetry-instrumentation-fastapi` 0.66b0, pytest with `InMemorySpanExporter`.

**Spec:** [spec.md](spec.md) (approved 2026-10-06). Intent: [intent.md](intent.md).

## Global Constraints

- Packages: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http` `>=1.45,<2` (already pinned); add only `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67`. No other package, no paid service.
- Only `POST /api/batch/runs` makes spans. `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS`, when set, replaces the default exclude pattern.
- Never in a span: the key, the key hash, the `Authorization` header, the body, a record field, or a field value from a validation error. Header capture stays off.
- `monitor.ingest` attributes: `outcome` (always: `created`, `duplicate`, `conflict`, `invalid`, `unauthorized`, `forbidden`, `too_large`); `use_case_id`, `run_id` after validation; `record_count` for `created` and `duplicate`; `stored_trace_id` for `duplicate` and `conflict`.
- `trace_id_source` is `traceparent` only when the request had a valid incoming W3C context; else `generated`. A run always has a 32-hex trace ID.
- Tracing never stops ingestion: a setup error, a disabled SDK or a failing exporter still stores the run.
- No migration. The `batch_runs` columns stay the same.
- Tests run from `backend/`: `.venv/bin/python -m pytest ...` (Windows: `.venv\Scripts\python.exe -m pytest ...`).
- Commit messages use Conventional Commits. Work on branch `feat/s1-05-backend-otel`.

## Review Focus

- A `traceparent` with leading or trailing spaces, or a future version (`01-...-future`): OTel accepts these as valid, the same as the S1-02 parser. Expect `trace_id_source = traceparent`. (Task 2, step 1, `test_valid_traceparent_variants_continue_the_trace`.)
- A query string on the batch URL (`/api/batch/runs?x=1`) is still traced; a longer path (`/api/batch/runs/x`) is not. (Task 1, step 1, `test_only_batch_runs_makes_spans`.)
- A `traceparent` on an excluded path does not create spans or errors. (Task 1, step 1, same test sends one.)
- A body that fails validation must not put field values in span attributes. (Task 2, step 1, `test_no_secret_or_body_text_in_any_span`.)
- An unexpected exception inside the handler (for example the database is down) marks `monitor.ingest` with status `ERROR` and still returns `500`. (Task 2, step 1, `test_unexpected_error_sets_span_status_error`.)

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Add the FastAPI instrumentation pin |
| `backend/app/tracing.py` | Create | Provider, exporter choice, app instrumentation, tracer access, shutdown |
| `backend/app/main.py` | Modify | Call `tracing.setup(app)`; call `tracing.shutdown()` at lifespan end |
| `backend/app/db.py` | Modify | `BatchRunConflict.stored_trace_id` |
| `backend/app/api/batch_routes.py` | Modify | `monitor.ingest` span, trace ID from the span, attributes; remove `parse_traceparent` |
| `backend/tests/conftest.py` | Modify | `spans` fixture (in-memory exporter on the shared provider) |
| `backend/tests/test_tracing.py` | Create | Provider and instrumentation tests |
| `backend/tests/test_batch_runs_tracing.py` | Create | Span and trace-ID tests for the receiver |
| `backend/tests/test_batch_runs_api.py` | Modify | Instrument the test app; remove `test_parse_traceparent` |
| `docs/STRICT-LIVE.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `changes/2026-10-06-s1-05-backend-otel/spec.md`, `CHANGELOG.md`, `DEVLOG.md` | Modify | Docs and plan text |

---

### Task 1: Tracing module and app instrumentation

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/tracing.py`
- Modify: `backend/app/main.py:22-65` (import, setup call) and `backend/app/main.py:50-54` (lifespan)
- Modify: `backend/tests/conftest.py` (add the `spans` fixture at the end)
- Create: `backend/tests/test_tracing.py`
- Modify: `changes/2026-10-06-s1-05-backend-otel/spec.md` (Component 1 signature)

**Interfaces:**
- Consumes: `config.BUILD_SHA` (str).
- Produces:
  - `tracing.PROVIDER: TracerProvider | None` — the shared provider, or `None` when tracing is off.
  - `tracing.build_provider(environ: Mapping[str, str]) -> TracerProvider | None`
  - `tracing.setup(app: FastAPI) -> None` — makes `PROVIDER` one time (and sets it as the global provider), then instruments `app`. Safe to call for more than one app.
  - `tracing.tracer() -> opentelemetry.trace.Tracer` — a tracer from `PROVIDER`, or a no-op tracer when `PROVIDER` is `None`.
  - `tracing.shutdown() -> None`
  - pytest fixture `spans` (in `conftest.py`) yields an `InMemorySpanExporter` that sees every span of `PROVIDER`, cleared before and after each test.

- [ ] **Step 1: Write the failing tests**

Add the pin to `backend/requirements.txt`, directly after the `opentelemetry-exporter-otlp-proto-http` line, and change the comment above the OTel lines:

```text
# S2-02 (approved 2026-10-05): Langfuse SDK v4 is built on OTel 1.45+. Read the release
# notes before a major upgrade. S1-05 part B adds the FastAPI instrumentation.
langfuse>=4.16,<5
opentelemetry-api>=1.45,<2
opentelemetry-sdk>=1.45,<2
opentelemetry-exporter-otlp-proto-http>=1.45,<2
opentelemetry-instrumentation-fastapi>=0.66b0,<0.67
```

Install it: `uv pip install -r requirements.txt` (from `backend/`).

Append to `backend/tests/conftest.py`:

```python
# ---- OpenTelemetry (S1-05) ------------------------------------------------------------

from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402
    InMemorySpanExporter,
)

_SPANS = InMemorySpanExporter()
_ATTACHED: list[object] = []


@pytest.fixture()
def spans():
    """Every span of the shared provider, cleared before and after the test."""
    from app import main, tracing  # noqa: F401 — importing main builds the provider

    provider = tracing.PROVIDER
    assert provider is not None, "tracing is off in the test process"
    if provider not in _ATTACHED:
        provider.add_span_processor(SimpleSpanProcessor(_SPANS))
        _ATTACHED.append(provider)
    _SPANS.clear()
    yield _SPANS
    _SPANS.clear()
```

Create `backend/tests/test_tracing.py`:

```python
"""S1-05 part B: the tracing module (provider, exporter choice, instrumentation)."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app import tracing

TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def _processors(provider: TracerProvider) -> list:
    return list(provider._active_span_processor._span_processors)  # noqa: SLF001


def test_disabled_sdk_builds_no_provider():
    assert tracing.build_provider({"OTEL_SDK_DISABLED": "true"}) is None
    assert tracing.build_provider({"OTEL_SDK_DISABLED": "TRUE"}) is None


def test_no_endpoint_means_spans_but_no_export():
    provider = tracing.build_provider({})
    assert isinstance(provider, TracerProvider)
    assert _processors(provider) == []
    assert provider.resource.attributes["service.name"] == "model-monitor"


def test_endpoint_adds_a_batch_exporter():
    for name in ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
        provider = tracing.build_provider({name: "http://collector:4318",
                                           "OTEL_SERVICE_NAME": "monitor-test"})
        try:
            assert [type(p) for p in _processors(provider)] == [BatchSpanProcessor]
            assert provider.resource.attributes["service.name"] == "monitor-test"
        finally:
            provider.shutdown()


def _app_with_routes() -> FastAPI:
    app = FastAPI()

    @app.post("/api/batch/runs")
    def runs():
        return {"ok": True}

    @app.get("/api/batch/runs/x")
    def longer():
        return {"ok": True}

    for path in ("/api/health", "/api/readiness", "/api/live/portfolio"):
        app.add_api_route(path, lambda: {"ok": True}, methods=["GET"])
    return app


def test_only_batch_runs_makes_spans(spans):
    app = _app_with_routes()
    tracing.setup(app)
    client = TestClient(app)
    for path in ("/api/health", "/api/readiness", "/api/live/portfolio", "/api/batch/runs/x"):
        assert client.get(path, headers={"traceparent": TRACEPARENT}).status_code == 200
    assert spans.get_finished_spans() == ()
    assert client.post("/api/batch/runs?x=1").status_code == 200
    names = [s.name for s in spans.get_finished_spans()]
    assert names == ["POST /api/batch/runs"]


def test_exclude_list_can_be_replaced_by_the_setting(spans, monkeypatch):
    monkeypatch.setenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "/api/batch/runs")
    app = _app_with_routes()
    tracing.setup(app)
    client = TestClient(app)
    client.post("/api/batch/runs")
    client.get("/api/health")
    assert [s.name for s in spans.get_finished_spans()] == ["GET /api/health"]


def test_setup_with_disabled_sdk_does_not_instrument(spans, monkeypatch):
    monkeypatch.setattr(tracing, "PROVIDER", None)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    app = _app_with_routes()
    tracing.setup(app)
    assert tracing.PROVIDER is None
    TestClient(app).post("/api/batch/runs")
    assert spans.get_finished_spans() == ()
    assert not tracing.tracer().start_span("x").get_span_context().is_valid


def test_setup_error_is_logged_and_the_app_still_works(monkeypatch, caplog):
    def broken(environ):
        raise ValueError("bad OTEL setting")

    monkeypatch.setattr(tracing, "PROVIDER", None)
    monkeypatch.setattr(tracing, "build_provider", broken)
    app = _app_with_routes()
    with caplog.at_level(logging.ERROR, logger="app.tracing"):
        tracing.setup(app)
    assert tracing.PROVIDER is None
    assert "tracing is off" in caplog.text
    assert TestClient(app).post("/api/batch/runs").status_code == 200


def test_main_app_sets_the_global_provider():
    from app import main  # noqa: F401

    assert tracing.PROVIDER is not None
    assert trace.get_tracer_provider() is tracing.PROVIDER


def test_shutdown_without_provider_is_safe(monkeypatch):
    monkeypatch.setattr(tracing, "PROVIDER", None)
    tracing.shutdown()
```

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `.venv/bin/python -m pytest -q tests/test_tracing.py`
Expected: FAIL — `ImportError: cannot import name 'tracing' from 'app'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/tracing.py`:

```python
"""OpenTelemetry for GCP batch runs (S1-05 part B).

One TracerProvider for the process.  The FastAPI instrumentation reads the W3C
`traceparent` header, so the backend server span continues the job's trace.  Only
`POST /api/batch/runs` makes spans; every other path is excluded (the prototype routes and
the health checks add no traces).  Spans go to the Collector over OTLP/HTTP only when
`OTEL_EXPORTER_OTLP_ENDPOINT` (or `..._TRACES_ENDPOINT`) is set; without it the spans and
trace IDs still exist.  `OTEL_SDK_DISABLED=true` turns tracing off.  A setup error is
logged and tracing stays off: tracing never stops ingestion.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Mapping

from opentelemetry import trace

from . import config

log = logging.getLogger(__name__)

PROVIDER = None  # opentelemetry.sdk.trace.TracerProvider | None

# Every URL except the batch receiver.  The instrumentation matches the URL without the
# query string, so `/api/batch/runs?x=1` is traced and `/api/batch/runs/x` is not.
_EXCLUDE_ALL_BUT_BATCH = r"^(?!.*/api/batch/runs$).*$"
_ENDPOINT_SETTINGS = ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")


def _disabled(environ: Mapping[str, str]) -> bool:
    return environ.get("OTEL_SDK_DISABLED", "").strip().lower() == "true"


def build_provider(environ: Mapping[str, str]):
    """A provider for these settings, or None when the SDK is disabled."""
    if _disabled(environ):
        return None
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    resource = Resource.create({
        "service.name": environ.get("OTEL_SERVICE_NAME", "").strip() or "model-monitor",
        "service.version": config.BUILD_SHA,
    })
    provider = TracerProvider(resource=resource)
    if any(environ.get(name, "").strip() for name in _ENDPOINT_SETTINGS):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # The exporter reads the standard OTEL_EXPORTER_OTLP_* settings itself.
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return provider


def setup(app) -> None:
    """Make the shared provider one time, then instrument `app`."""
    global PROVIDER
    if _disabled(os.environ):
        return
    try:
        if PROVIDER is None:
            PROVIDER = build_provider(os.environ)
            if PROVIDER is None:
                return
            trace.set_tracer_provider(PROVIDER)
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app, tracer_provider=PROVIDER,
            excluded_urls=os.environ.get("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS",
                                         _EXCLUDE_ALL_BUT_BATCH),
            exclude_spans=["receive", "send"])
    except Exception as exc:  # noqa: BLE001 — tracing must never stop the service
        PROVIDER = None
        log.error("tracing is off: setup failed: %s", type(exc).__name__)


def tracer() -> trace.Tracer:
    if PROVIDER is None:
        return trace.NoOpTracer()
    return PROVIDER.get_tracer("app.batch")


def shutdown() -> None:
    """Send the remaining spans.  The OTLP exporter has its own time limit
    (`OTEL_EXPORTER_OTLP_TIMEOUT`, default 10 s), so a stop cannot hang."""
    if PROVIDER is not None:
        PROVIDER.shutdown()
```

In `backend/app/main.py`, change the import line `from . import config, db, logging_setup, seeds_loader` to:

```python
from . import config, db, logging_setup, seeds_loader, tracing
```

Change the `finally:` block of `lifespan` to:

```python
    try:
        yield
    finally:
        poller().stop()
        tracing.shutdown()
```

Directly after `app.include_router(batch_routes.router)  # GCP batch run summaries (S1-02), both modes`, add:

```python
tracing.setup(app)  # only POST /api/batch/runs makes spans (S1-05)
```

In `changes/2026-10-06-s1-05-backend-otel/spec.md`, replace the line `` `setup(app, exporter=None) -> None` `` with:

```markdown
`build_provider(environ) -> TracerProvider | None`, `setup(app) -> None`,
`tracer() -> Tracer`, `shutdown() -> None`, and the module value `PROVIDER`. Tests attach
an in-memory exporter to `PROVIDER` (a `spans` fixture) instead of an `exporter` argument.
```

and replace step 3's first bullet (`- If `exporter` is given (tests): a `SimpleSpanProcessor(exporter)`.`) with nothing (delete the line).

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `.venv/bin/python -m pytest -q tests/test_tracing.py`
Expected: 9 passed.

Run: `.venv/bin/python -m pytest -q -m "not slow"`
Expected: all passed (the S1-02 tests still pass; `parse_traceparent` still exists in this task).

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/tracing.py backend/app/main.py backend/tests/conftest.py backend/tests/test_tracing.py changes/2026-10-06-s1-05-backend-otel/spec.md
git commit -m "feat(tracing): OTel provider and FastAPI instrumentation for batch runs (S1-05)"
```

---

### Task 2: `monitor.ingest` span and the trace ID from OTel

**Files:**
- Modify: `backend/app/db.py:1131-1132` (`BatchRunConflict`) and `backend/app/db.py:1160-1161` (the `raise`)
- Modify: `backend/app/api/batch_routes.py` (whole file; full content below)
- Modify: `backend/tests/test_batch_runs_api.py:39-49` (fixture) and `:255-262` (remove `test_parse_traceparent`)
- Create: `backend/tests/test_batch_runs_tracing.py`

**Interfaces:**
- Consumes: `tracing.setup(app)`, `tracing.tracer()`, `tracing.PROVIDER`, fixture `spans` (Task 1).
- Produces: `db.BatchRunConflict(message: str, stored_trace_id: str | None = None)` with attribute `stored_trace_id`. `batch_routes.parse_traceparent` no longer exists.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_batch_runs_api.py`:
- Change the import line `from app import config, db, main` to `from app import config, db, main, tracing`.
- In the `client` fixture, after `strict_app.middleware("http")(main.strict_live_route_isolation)`, add the line `tracing.setup(strict_app)`.
- Delete the whole function `test_parse_traceparent` (lines 255-262). Its valid cases move to the new file below; its invalid cases stay in `test_missing_or_invalid_traceparent_starts_a_new_trace`.

Create `backend/tests/test_batch_runs_tracing.py`:

```python
"""S1-05 part B: spans and trace IDs of POST /api/batch/runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.trace import StatusCode

from app import config, db, main, tracing
from app.api import batch_routes

EXAMPLES = (Path(__file__).resolve().parents[2] / "changes" / "2026-10-02-batch-monitoring-mvp"
            / "schema" / "examples")
KEY_03 = "test-key-uc03-" + "a" * 32
KEY_07 = "test-key-uc07-" + "b" * 32
AUTH = {"Authorization": f"Bearer {KEY_03}"}
TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
PARENT_ID = "00f067aa0ba902b7"
TRACEPARENT = f"00-{TRACE_ID}-{PARENT_ID}-01"
URL = "/api/batch/runs"
RUN = ("GCP-UC-03", "invoice-summary-2026-10-07")


def sha(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def example(name: str, folder: str = "valid") -> dict:
    return json.loads((EXAMPLES / folder / name).read_text(encoding="utf-8"))


def _strict_app() -> FastAPI:
    app = FastAPI()
    app.include_router(batch_routes.router)
    app.middleware("http")(main.strict_live_route_isolation)
    tracing.setup(app)
    return app


@pytest.fixture()
def configured(isolated_db, monkeypatch):
    monkeypatch.setattr(config, "LIVE_POLL_SECONDS", 0)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{sha(KEY_03)}, GCP-UC-07:{sha(KEY_07)}")


@pytest.fixture()
def client(configured, spans) -> TestClient:
    with TestClient(_strict_app(), raise_server_exceptions=False) as c:
        yield c


def by_name(spans, name: str) -> list:
    return [s for s in spans.get_finished_spans() if s.name == name]


def ingest(spans):
    found = by_name(spans, "monitor.ingest")
    assert len(found) == 1, [s.name for s in spans.get_finished_spans()]
    return found[0]


def hex_trace(span) -> str:
    return format(span.context.trace_id, "032x")


# ---- trace continuation ----------------------------------------------------------------

def test_known_traceparent_continues_the_job_trace(client, spans):
    response = client.post(URL, json=example("01-completed-online.json"),
                           headers={**AUTH, "traceparent": TRACEPARENT})
    assert response.status_code == 201, response.text
    server = by_name(spans, "POST /api/batch/runs")[0]
    span = ingest(spans)
    assert hex_trace(span) == hex_trace(server) == TRACE_ID
    assert span.parent.span_id == server.context.span_id
    assert format(server.parent.span_id, "016x") == PARENT_ID and server.parent.is_remote
    stored = db.get_batch_run(*RUN)
    assert stored["trace_id"] == TRACE_ID == response.json()["trace_id"]
    assert stored["trace_id_source"] == "traceparent"


@pytest.mark.parametrize("header", [
    f"  {TRACEPARENT} ",                                   # spaces around the value
    f"01-{TRACE_ID}-{PARENT_ID}-01-future",                # a later version may add fields
])
def test_valid_traceparent_variants_continue_the_trace(client, spans, header):
    response = client.post(URL, json=example("01-completed-online.json"),
                           headers={**AUTH, "traceparent": header})
    assert response.status_code == 201
    assert response.json()["trace_id"] == TRACE_ID
    assert db.get_batch_run(*RUN)["trace_id_source"] == "traceparent"


def test_no_traceparent_starts_a_new_trace_and_stores_its_id(client, spans):
    response = client.post(URL, json=example("01-completed-online.json"), headers=AUTH)
    assert response.status_code == 201
    span = ingest(spans)
    assert span.parent is not None and not span.parent.is_remote
    stored = db.get_batch_run(*RUN)
    assert stored["trace_id"] == hex_trace(span) != TRACE_ID
    assert stored["trace_id_source"] == "generated"


# ---- attributes and outcomes -------------------------------------------------------------

def _post_created(client):
    return client.post(URL, json=example("01-completed-online.json"),
                       headers={**AUTH, "traceparent": TRACEPARENT})


def test_created_attributes(client, spans):
    assert _post_created(client).status_code == 201
    attrs = dict(ingest(spans).attributes)
    assert attrs == {"outcome": "created", "use_case_id": RUN[0], "run_id": RUN[1],
                     "record_count": 2}


def test_resend_with_other_trace_records_the_stored_trace(client, spans):
    assert _post_created(client).status_code == 201
    spans.clear()
    other = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
    again = client.post(URL, json=example("01-completed-online.json"),
                        headers={**AUTH, "traceparent": other})
    assert again.status_code == 200
    span = ingest(spans)
    assert hex_trace(span) == "c" * 32
    assert span.attributes["outcome"] == "duplicate"
    assert span.attributes["stored_trace_id"] == TRACE_ID
    assert span.attributes["record_count"] == 2
    assert db.get_batch_run(*RUN)["trace_id"] == TRACE_ID


def test_retry_in_the_same_trace_has_the_same_stored_trace(client, spans):
    assert _post_created(client).status_code == 201
    spans.clear()
    retry = f"00-{TRACE_ID}-" + "e" * 16 + "-01"         # another client span, same trace
    assert client.post(URL, json=example("01-completed-online.json"),
                       headers={**AUTH, "traceparent": retry}).status_code == 200
    span = ingest(spans)
    assert hex_trace(span) == span.attributes["stored_trace_id"] == TRACE_ID


def test_conflict_records_the_stored_trace(client, spans):
    assert _post_created(client).status_code == 201
    spans.clear()
    body = example("01-completed-online.json")
    body["failed_count"] = 3
    other = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
    assert client.post(URL, json=body,
                       headers={**AUTH, "traceparent": other}).status_code == 409
    attrs = dict(ingest(spans).attributes)
    assert attrs == {"outcome": "conflict", "use_case_id": RUN[0], "run_id": RUN[1],
                     "stored_trace_id": TRACE_ID}


@pytest.mark.parametrize("make_request, status, outcome", [
    (lambda c: c.post(URL, json=example("01-completed-online.json")), 401, "unauthorized"),
    (lambda c: c.post(URL, json={"schema_version": "x"}, headers=AUTH), 400, "invalid"),
    (lambda c: c.post(URL, json=example("01-completed-online.json"),
                      headers={"Authorization": f"Bearer {KEY_07}"}), 403, "forbidden"),
])
def test_rejected_requests_have_their_outcome(client, spans, make_request, status, outcome):
    assert make_request(client).status_code == status
    span = ingest(spans)
    assert span.attributes["outcome"] == outcome
    assert span.status.status_code == StatusCode.UNSET
    if outcome == "forbidden":
        assert set(span.attributes) == {"outcome", "use_case_id", "run_id"}
    else:
        assert set(span.attributes) == {"outcome"}


def test_too_large_has_its_outcome(client, spans, monkeypatch):
    monkeypatch.setattr(config, "BATCH_MAX_BODY_BYTES", 10)
    assert client.post(URL, json=example("01-completed-online.json"),
                       headers=AUTH).status_code == 413
    assert dict(ingest(spans).attributes) == {"outcome": "too_large"}


def test_no_secret_or_body_text_in_any_span(client, spans):
    body = example("01-completed-online.json")
    _post_created(client)
    bad = json.loads(json.dumps(body))
    bad["records"][0]["unknown_field"] = "SECRET-FIELD-VALUE"
    client.post(URL, json=bad, headers=AUTH)
    client.post(URL, json=body, headers={"Authorization": "Bearer wrong-key-value"})
    forbidden = {KEY_03, sha(KEY_03), f"Bearer {KEY_03}", "wrong-key-value",
                 "SECRET-FIELD-VALUE"}
    forbidden |= {str(r[k]) for r in body["records"] for k in r if isinstance(r[k], str)}
    forbidden = {f for f in forbidden if len(f) >= 6}
    for span in spans.get_finished_spans():
        text = json.dumps({k: str(v) for k, v in (span.attributes or {}).items()})
        for value in forbidden:
            assert value not in text, (span.name, value)


def test_unexpected_error_sets_span_status_error(client, spans, monkeypatch):
    def broken(row):
        raise RuntimeError("database is down")

    monkeypatch.setattr(db, "put_batch_run", broken)
    assert client.post(URL, json=example("01-completed-online.json"),
                       headers=AUTH).status_code == 500
    assert ingest(spans).status.status_code == StatusCode.ERROR


# ---- tracing must never stop ingestion --------------------------------------------------

class _FailingExporter(SpanExporter):
    def export(self, spans):
        raise ConnectionError("collector is down")

    def shutdown(self):
        pass


def test_failing_exporter_does_not_stop_the_run(configured, monkeypatch):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_FailingExporter()))
    monkeypatch.setattr(tracing, "PROVIDER", provider)
    with TestClient(_strict_app()) as c:
        response = c.post(URL, json=example("01-completed-online.json"),
                          headers={**AUTH, "traceparent": TRACEPARENT})
    assert response.status_code == 201
    assert db.get_batch_run(*RUN)["trace_id"] == TRACE_ID


def test_disabled_sdk_still_stores_with_a_generated_id(configured, spans, monkeypatch):
    monkeypatch.setattr(tracing, "PROVIDER", None)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    with TestClient(_strict_app()) as c:
        response = c.post(URL, json=example("01-completed-online.json"),
                          headers={**AUTH, "traceparent": TRACEPARENT})
    assert response.status_code == 201
    assert spans.get_finished_spans() == ()
    stored = db.get_batch_run(*RUN)
    assert stored["trace_id_source"] == "generated" and stored["trace_id"] != TRACE_ID
    assert len(stored["trace_id"]) == 32
```

- [ ] **Step 2: Run the tests to make sure they fail**

Run: `.venv/bin/python -m pytest -q tests/test_batch_runs_tracing.py`
Expected: FAIL — `ingest()` finds no `monitor.ingest` span (`assert 0 == 1`), and the conflict test has no `stored_trace_id`.

- [ ] **Step 3: Write the implementation**

In `backend/app/db.py`, replace the class `BatchRunConflict` with:

```python
class BatchRunConflict(RuntimeError):
    """The (use_case_id, run_id) is stored with another content digest; it is not changed.

    `stored_trace_id` is the trace ID of the stored row (S1-05: the `monitor.ingest` span
    of the refused request records it)."""

    def __init__(self, message: str, stored_trace_id: str | None = None) -> None:
        super().__init__(message)
        self.stored_trace_id = stored_trace_id
```

and replace the `raise` in `put_batch_run` with:

```python
            raise BatchRunConflict(f"run {run_id} of {use_case_id} is stored with other content",
                                   stored_trace_id=existing["trace_id"])
```

Replace the whole content of `backend/app/api/batch_routes.py` with:

```python
"""Receiving API for GCP batch run summaries: POST /api/batch/runs (S1-02).

Order of checks: API key (401) → body size (413) → `batch-run/1` (400) → the key's use
case (403) → store once (201 created, 200 duplicate, 409 other content).  Nothing is
stored unless every check passes.  The key, the Authorization header and the body are
never logged; log lines carry the outcome, the run identity, the record count and the
trace ID only.

Tracing (S1-05 part B): the FastAPI instrumentation (`app/tracing.py`) reads the W3C
`traceparent` header and starts the server span; the handler runs in its child span
`monitor.ingest`.  Span attributes carry only the outcome, the run identity, the record
count and, for a resend, the stored trace ID.

This router is mounted in demo and strict live mode.  It never touches a v1.1 telemetry
cursor.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets

import anyio
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace

from .. import config, db, tracing
from ..batch_schema import BatchRunInvalid, validate_run

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _has_incoming_context() -> bool:
    """True when the current server span continues a valid remote (W3C) context."""
    parent = getattr(trace.get_current_span(), "parent", None)
    return parent is not None and parent.is_remote and parent.is_valid


def _trace_id(span: trace.Span, incoming: bool) -> tuple[str, str]:
    """(trace ID, source).  A random ID when tracing is off, so a run always has one."""
    context = span.get_span_context()
    if context.is_valid:
        return format(context.trace_id, "032x"), ("traceparent" if incoming else "generated")
    return secrets.token_hex(16), "generated"


def _use_case_of_key(authorization: str | None) -> str | None:
    """The use case of a valid `Bearer <key>`, else None.

    The key is hashed and compared with every configured hash in constant time; the loop
    does not stop at the first match.
    """
    scheme, _, key = (authorization or "").strip().partition(" ")
    key = key.strip()
    if scheme.lower() != "bearer" or not key:
        return None
    supplied = hashlib.sha256(key.encode("utf-8")).hexdigest().encode("ascii")
    found = None
    for digest, use_case_id in config.batch_api_key_hashes():
        if hmac.compare_digest(supplied, digest.encode("ascii")) and found is None:
            found = use_case_id
    return found


def _canonical(body: object) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _too_large(span: trace.Span) -> JSONResponse:
    span.set_attribute("outcome", "too_large")
    log.warning("batch run rejected: body too large", extra={"outcome": "too_large"})
    return JSONResponse({"detail": f"body is larger than {config.BATCH_MAX_BODY_BYTES} bytes"},
                        status_code=413)


@router.post("/batch/runs")
async def receive_batch_run(request: Request,
                            authorization: str | None = Header(default=None)):
    incoming = _has_incoming_context()
    with tracing.tracer().start_as_current_span("monitor.ingest") as span:
        return await _ingest(request, authorization, span, incoming)


async def _ingest(request: Request, authorization: str | None, span: trace.Span,
                  incoming: bool) -> JSONResponse:
    key_use_case = _use_case_of_key(authorization)
    if key_use_case is None:
        span.set_attribute("outcome", "unauthorized")
        log.warning("batch run rejected: invalid API key", extra={"outcome": "unauthorized"})
        return JSONResponse({"detail": "invalid API key"}, status_code=401,
                            headers={"WWW-Authenticate": "Bearer"})

    limit = config.BATCH_MAX_BODY_BYTES
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return _too_large(span)
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():  # stop reading as soon as the limit is passed
        size += len(chunk)
        if size > limit:
            return _too_large(span)
        chunks.append(chunk)
    raw = b"".join(chunks)

    try:
        run = validate_run(raw)
    except BatchRunInvalid as exc:
        span.set_attribute("outcome", "invalid")
        log.warning("batch run rejected: %d field error(s)", len(exc.errors),
                    extra={"outcome": "invalid", "key_use_case_id": key_use_case})
        return JSONResponse({"detail": "body does not agree with batch-run/1",
                             "errors": exc.errors}, status_code=400)

    identity = {"use_case_id": run.use_case_id, "run_id": run.run_id}
    span.set_attributes(identity)
    if run.use_case_id != key_use_case:
        span.set_attribute("outcome", "forbidden")
        log.warning("batch run rejected: the API key is for another use case",
                    extra={"outcome": "forbidden", "key_use_case_id": key_use_case, **identity})
        return JSONResponse({"detail": "the API key is not for this use case"}, status_code=403)

    canonical = _canonical(json.loads(raw))
    trace_id, trace_id_source = _trace_id(span, incoming)
    row = {
        **identity,
        "schema_version": run.schema_version, "status": run.status,
        "completed_at": run.completed_at, "request_count": run.request_count,
        "failed_count": run.failed_count, "model": run.model,
        "sample_method": run.sample.method, "sample_size": run.sample.size,
        "records_reason": run.records_reason, "record_count": len(run.records),
        "content_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "payload": canonical, "trace_id": trace_id, "trace_id_source": trace_id_source,
    }
    try:
        stored, outcome = await anyio.to_thread.run_sync(db.put_batch_run, row)
    except db.BatchRunConflict as exc:
        span.set_attribute("outcome", "conflict")
        if exc.stored_trace_id:
            span.set_attribute("stored_trace_id", exc.stored_trace_id)
        log.warning("batch run rejected: stored with other content",
                    extra={"outcome": "conflict", **identity})
        return JSONResponse({"detail": "this run_id is stored with other content; "
                                       "the stored run is not changed", **identity},
                            status_code=409)
    span.set_attributes({"outcome": outcome, "record_count": stored["record_count"]})
    if outcome == "duplicate":
        span.set_attribute("stored_trace_id", stored["trace_id"])
    log.info("batch run %s", outcome, extra={
        "outcome": outcome, **identity, "record_count": stored["record_count"],
        "trace_id": stored["trace_id"]})
    return JSONResponse({
        "status": outcome, "batch_run_id": stored["batch_run_id"], **identity,
        "record_count": stored["record_count"], "trace_id": stored["trace_id"],
        "received_at": stored["received_at"],
    }, status_code=201 if outcome == "created" else 200)
```

- [ ] **Step 4: Run the tests to make sure they pass**

Run: `.venv/bin/python -m pytest -q tests/test_batch_runs_tracing.py tests/test_batch_runs_api.py tests/test_batch_runs_store.py`
Expected: all passed. `test_missing_or_invalid_traceparent_starts_a_new_trace` (7 cases) still passes through the OTel path.

Run: `.venv/bin/python -m pytest -q -m "not slow"`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db.py backend/app/api/batch_routes.py backend/tests/test_batch_runs_api.py backend/tests/test_batch_runs_tracing.py
git commit -m "feat(batch): monitor.ingest span and trace ID from OTel context (S1-05)"
```

---

### Task 3: Docs, plan text and the full check

**Files:**
- Modify: `docs/STRICT-LIVE.md:159-161` ("Batch run receiver")
- Modify: `changes/2026-10-02-batch-monitoring-mvp/issues.md:421`, `:431`, `:438`, `:497-501`, `:612`
- Modify: `CHANGELOG.md` (`## [Unreleased]` → `### Changed`)
- Modify: `DEVLOG.md` (new entry at the top of `## Work log`)

**Interfaces:**
- Consumes: the behavior of Tasks 1 and 2.
- Produces: no code.

- [ ] **Step 1: Change `docs/STRICT-LIVE.md`**

Replace the bullet that starts with `- Trace ID: from a valid W3C `traceparent` header` (and its continuation line) with:

```markdown
- Trace ID: the OTel FastAPI instrumentation reads the W3C `traceparent` header and the
  handler runs in the span `monitor.ingest`; the row stores that span's trace ID with
  `trace_id_source = traceparent`. Without a valid header, or with tracing off, a new ID
  is stored with `trace_id_source = generated`. Only `POST /api/batch/runs` makes spans.
- Tracing settings (all optional): `OTEL_EXPORTER_OTLP_ENDPOINT` sends the spans to the
  Collector over OTLP/HTTP (unset: no export); `OTEL_SERVICE_NAME` (default
  `model-monitor`); `OTEL_SDK_DISABLED=true` turns tracing off;
  `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` replaces the exclude pattern. A failed export never
  stops a run.
```

- [ ] **Step 2: Change the plan text in `issues.md`**

Line 421 (S1-05 step 4), replace the row with:

```markdown
| 4 | Backend (part B) | The FastAPI instrumentation reads the header. The backend server span is a child of the job's HTTP client span, and the `monitor.ingest` span is a child of the server span. Thus `batch.send` is an ancestor of `monitor.ingest` (decided 2026-10-06). |
```

Line 431, replace with:

```markdown
- [ ] Part B: `monitor.ingest` has the same trace ID as the root span of the job, and `batch.send` is its ancestor (job HTTP client span → backend server span → `monitor.ingest`). The `batch_runs` row stores this trace ID.
```

Line 438, replace with:

```markdown
2. Unit, part B (backend): send a request with a known `traceparent`. Make sure that the trace ID is correct, that the parent of the server span is the span ID in the header, that `monitor.ingest` is a child of the server span, and that the stored trace ID is correct.
```

Line 501 (S1-07 table), replace with:

```markdown
| Ancestor link | Collector file | Following the parent IDs up from `monitor.ingest` reaches the job's `batch.send` span (through the job's HTTP client span and the backend server span). If no run row has the trace ID, but a `monitor.ingest` span has `stored_trace_id`, show "duplicate delivery; the run is stored under trace `<id>`". |
```

Line 612 (S1-10), replace with:

```markdown
- [ ] The job's `batch.send` span is an ancestor of `monitor.ingest`.
```

- [ ] **Step 3: Update `CHANGELOG.md` and `DEVLOG.md`**

Under `## [Unreleased]` → `### Changed` in `CHANGELOG.md`, add as the first bullet:

```markdown
- `POST /api/batch/runs` continues the GCP job's trace with OpenTelemetry: a FastAPI
  server span and its child `monitor.ingest`, exported over OTLP/HTTP when
  `OTEL_EXPORTER_OTLP_ENDPOINT` is set. The stored `trace_id` comes from the span. A
  resend records `stored_trace_id` on its span. No other route makes spans (S1-05).
```

At the top of `## Work log` in `DEVLOG.md`, add an entry. Fill the numbers from Step 4:

```markdown
### 2026-10-06 — S1-05 part B: backend OpenTelemetry for batch runs

- Changed: new `backend/app/tracing.py` (one provider, OTLP/HTTP export only with an
  endpoint, FastAPI instrumentation that traces only `POST /api/batch/runs`).
  `batch_routes.py` runs in `monitor.ingest` and takes the trace ID from the span;
  `parse_traceparent` is removed. `db.BatchRunConflict.stored_trace_id`. Package:
  `opentelemetry-instrumentation-fastapi>=0.66b0,<0.67` (approved in S2-02). Decisions with
  the project owner: part B only; `batch.send` is an ancestor (not the parent) of
  `monitor.ingest`, so S1-05, S1-07 and S1-10 in `issues.md` changed; `stored_trace_id`
  on a resend. Change package `changes/2026-10-06-s1-05-backend-otel/`.
- Evidence: <fast suite result>; <full suite result>; new tests `test_tracing.py` and
  `test_batch_runs_tracing.py`. Not run: a real Collector (S1-06), a real GCP job (part
  A), the test host, the paired test S1-05 + S1-06.
- Remaining: the GitHub issues #7, #9 and #12 still say "parent"; change them after the
  project owner agrees. S1-07 must follow the parent IDs upward.
```

- [ ] **Step 4: Run every required check**

Run: `.venv/bin/python -m pytest -q -m "not slow"` — expected: all passed, 9 deselected.
Run: `.venv/bin/python -m pytest -q` — expected: all passed.
Run: `.venv/bin/python -m pytest -q tests/test_docs.py` — expected: 5 passed.
Put the two suite results in the DEVLOG entry (replace the `<...>` text).

- [ ] **Step 5: Commit and open the pull request**

```bash
git add docs/STRICT-LIVE.md changes/2026-10-02-batch-monitoring-mvp/issues.md CHANGELOG.md DEVLOG.md
git commit -m "docs(s1-05): tracing settings, ancestor link in S1-05/S1-07/S1-10"
git push -u origin feat/s1-05-backend-otel
gh pr create --base dev --head feat/s1-05-backend-otel --title "feat(batch): S1-05 part B — backend OpenTelemetry for batch runs"
```

The PR body lists: what changed, the acceptance criteria of #7 part B that pass, the test evidence, and the unavailable checks (real Collector, GCP job, test host).
