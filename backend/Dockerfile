# AI Use Case Observability Control Tower — backend (FastAPI + ML engines).
# Deploy target: Fly.io (a real always-on container; NOT serverless — the app
# holds a persistent SQLite file, a long-running SSE stream, an in-process
# asyncio scenario player, and 300MB+ of ML deps: Evidently/NannyML/SHAP/LIME).
#
# The DEMO-FULL scenario is baked at BUILD time (deterministic seed-42, ~90s),
# so the image ships demo-ready and boot is instant — health checks pass right
# away instead of racing a 90s first-request bake.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg

# build-essential: any sdist that needs a C/C++ compiler (SHAP helpers).
# libgomp1: OpenMP runtime for LightGBM (pulled in by NannyML).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Deps first for layer caching (this is the slow layer — fat ML wheels).
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code (see .dockerignore — no .venv, no prebaked *.db, no artifacts/).
COPY . .

# Bake the scenario into the image (config.DB_PATH -> /app/control_tower.db,
# artifacts -> /app/artifacts). Deterministic; two bakes are byte-identical.
RUN python bake.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
