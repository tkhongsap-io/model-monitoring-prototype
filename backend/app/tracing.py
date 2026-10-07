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
    # FastAPI 0.142 also enables native telemetry when a global provider exists.
    # This app uses the explicit OTel instrumentor, including when tracing is off.
    native = getattr(app, "_telemetry", None)
    if native is not None:
        native.update(tracing=False, metrics=False, logs=False, auto_configure=False,
                      operation_spans=False)
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
