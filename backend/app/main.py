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
