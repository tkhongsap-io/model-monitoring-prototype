"""Dashboard API (S2-07): read-only routes for the unchanged control-tower UI.

Served on front-door port 8082 only (deploy/nginx/conf.d/dashboard.conf); port 80 keeps
only the job API. Each response is built by `dashboard_view` from the registry, the latest
stored run and its evaluation: never a whole stored row, never `payload`, a record, a key
or a token. A database error gives 503 with the error class name only.
"""
from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .. import config, dashboard_view, db, registry
from ..engines.batch_grading import BANDS_VERSION

router = APIRouter(prefix="/api/live")


def _db_error(exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": "database is not reachable", "error": type(exc).__name__},
                        status_code=503)


def _latest(use_case_id: str) -> tuple[dict | None, dict | None]:
    run = db.latest_batch_run(use_case_id)
    evaluation = db.latest_evaluation(run["batch_run_id"], BANDS_VERSION) if run else None
    return run, evaluation


@router.get("/portfolio")
def portfolio():
    now = time.time()
    try:
        rows = [dashboard_view.portfolio_row(use_case, *_latest(use_case_id), now)
                for use_case_id, use_case in registry.current().items()]
    except SQLAlchemyError as exc:
        return _db_error(exc)
    return {**dashboard_view.summary(rows, now, config.BUILD_SHA), "rows": rows}


@router.get("/use-case/{use_case_id}")
def use_case(use_case_id: str):
    entry = registry.current().get(use_case_id)
    if entry is None:
        return JSONResponse({"detail": "unknown use case"}, status_code=404)
    now = time.time()
    try:
        run, evaluation = _latest(use_case_id)
        history = db.evaluation_history(use_case_id, BANDS_VERSION)
    except SQLAlchemyError as exc:
        return _db_error(exc)
    return dashboard_view.detail(entry, run, evaluation, history, now)


@router.get("/alerts")
def alerts():
    """No alerting in October: always an empty list (the UI badge shows 0)."""
    return {"contract_version": "1.1", "redacted": True, "rows": []}
