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
