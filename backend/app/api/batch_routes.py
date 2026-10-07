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
