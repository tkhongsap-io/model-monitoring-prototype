#!/usr/bin/env bash
# Production build for the FastAPI backend: venv + deps + bake the demo scenario.
set -euo pipefail
cd "$(dirname -- "$0")/.."
export MPLBACKEND="${MPLBACKEND:-Agg}"
if [ ! -x .venv-backend/bin/python ]; then
  python3 -m venv .venv-backend
fi
PY=".venv-backend/bin/python"
PIP_USER=0 "$PY" -m pip install --no-user -r backend/requirements.txt
if [ ! -f backend/control_tower.db ]; then
  echo "[build] baking DEMO-FULL (seed 42)…"
  (cd backend && "../$PY" demo_reset.py)
fi
echo "[build] done"
