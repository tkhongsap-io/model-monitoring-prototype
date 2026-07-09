"""FastAPI app — AI Use Case Observability Control Tower (simulation demo).

Startup: ensure the DB exists and the 130-row registry is seeded. Baking is done
via scripts/demo_reset or POST /api/sim/bake (dev-only) — never at request time.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import db, seeds_loader
from .api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.engine()
    n = seeds_loader.seed_registry()
    print(f"[startup] registry rows: {n}")
    yield


app = FastAPI(title="AI Use Case Observability Control Tower — Simulation Demo",
              version="1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/api/health")
def healthcheck():
    return {"ok": True}
