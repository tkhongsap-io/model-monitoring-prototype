"""FastAPI app of the October batch MVP (S1-13).

It serves only the batch MVP API: `POST /api/batch/runs` (S1-02, S1-05) and the service
checks in `api/ops_routes.py`.  Every other path returns 404.  There is no mode: the
prototype code (demo and strict-live routers, the pull-lane poller, the dashboard) stays in
the repository until S4-07, but this module does not import it.  The prototype tests build
the old composition from `tests/prototype_app.py`.

Startup loads the batch use-case registry (S2-01; a bad registry stops the start) and runs
the ordered migrations (`db.engine()`); shutdown sends the remaining spans.
When `BATCH_EVALUATOR_ENABLED` is true, the lifespan also runs the batch evaluator (S2-05).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import batch_evaluator, config, db, logging_setup, registry, tracing
from .api import batch_routes, ops_routes

logging_setup.configure(config.LOG_FORMAT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.set_current(registry.load(config.BATCH_REGISTRY_PATH))   # error: no start
    db.engine()
    if config.BATCH_EVALUATOR_ENABLED:
        batch_evaluator.start()                                       # S2-05
    try:
        yield
    finally:
        await batch_evaluator.stop()
        tracing.shutdown()


app = FastAPI(title="Batch run monitor", version="batch-mvp", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(batch_routes.router)
app.include_router(ops_routes.router)
tracing.setup(app)  # only POST /api/batch/runs makes spans (S1-05)
