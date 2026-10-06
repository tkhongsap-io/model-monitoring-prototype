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
