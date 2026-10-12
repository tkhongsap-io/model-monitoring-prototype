"""Service checks of the batch MVP app (S1-13): liveness, readiness and version.

`/api/health` and `/api/healthz` are liveness checks: they answer while the process runs
and never touch the database, so a database problem does not make Docker restart the app.
`/api/readiness` answers whether a batch run can be stored now.  No answer contains a
secret: a database error is reported by its type name only, and a key entry by position.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import config, db, registry
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
    use_cases = registry.current()
    missing = registry.unregistered(
        (use_case_id for _, use_case_id in config.batch_api_key_hashes()), use_cases)
    if missing:
        errors.append("BATCH_API_KEY_SHA256 has entries for use cases that are not in the "
                      f"registry: {', '.join(missing)}")
    if not database["ok"]:
        errors.append("database is not reachable")
    body = {"status": "ready" if not errors else "not_ready", "database": database,
            "batch_api_keys": len(config.batch_api_key_hashes()),
            "use_cases": len(use_cases), "errors": errors}
    return JSONResponse(body, status_code=200 if not errors else 503)


@router.get("/version")
def version():
    return {"service": SERVICE, "build_sha": config.BUILD_SHA, "batch_schema": SCHEMA_VERSION}
