"""FastAPI app — AI Use Case Observability Control Tower.

Startup: ensure the DB exists and the 130-row registry is seeded. Baking is done
via scripts/demo_reset or POST /api/sim/bake (dev-only) — never at request time.

Serving: /api/* is the contract; if the dashboard has been built
(artifacts/control-tower/dist/public — see scripts/deploy-build.sh) it is served
from this same app, so a deployment is ONE service on ONE port. In dev the Vite
server (:5000, proxying /api -> :8000) is used instead and the mount is skipped.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import db, seeds_loader
from .api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.engine()
    n = seeds_loader.seed_registry()
    print(f"[startup] registry rows: {n}")
    yield


app = FastAPI(title="AI Use Case Observability Control Tower",
              version="1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/api/health")
def healthcheck():
    return {"ok": True}


@app.get("/api/healthz")
def healthz():
    return {"status": "ok"}


# --- dashboard (built SPA), mounted LAST so the /api routes above always win ---

_SPA_DIST = Path(__file__).resolve().parents[2] / "artifacts" / "control-tower" / "dist" / "public"


class _SPAFiles(StaticFiles):
    """Static files with an SPA fallback: unknown non-API paths (client-side routes
    like /heatmap, /use-case/AICT-L01) serve index.html; /api/* keeps real 404s.
    Starlette signals a missing file either by RAISING HTTPException(404) (current
    versions) or by returning a 404 response (older) — handle both."""

    async def get_response(self, path: str, scope):
        from starlette.exceptions import HTTPException as StarletteHTTPException
        try:
            resp = await super().get_response(path, scope)
        except StarletteHTTPException as e:
            if e.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise
        if resp.status_code == 404 and not path.startswith("api"):
            return await super().get_response("index.html", scope)
        return resp


if _SPA_DIST.is_dir():  # present only after a frontend build — dev machines skip this
    app.mount("/", _SPAFiles(directory=_SPA_DIST, html=True), name="dashboard")
    print(f"[startup] serving dashboard from {_SPA_DIST}")
