#!/usr/bin/env bash
# Replit deployment BUILD step (.replit [deployment].build).
# Python deps -> bake DEMO-FULL (seed 42; the baked SQLite ships in the deployed
# filesystem so boot is instant) -> frontend production build.
set -euo pipefail
cd "$(dirname -- "$0")/.."

# 1) venv at repo root — the Nix store is read-only, never pip-install globally
if [ ! -x .venv/bin/python ] && [ ! -x .venv/Scripts/python.exe ]; then
  PYBIN="$(command -v python3 || command -v python)"
  echo "[build] creating .venv with $PYBIN"
  "$PYBIN" -m venv .venv
fi
source scripts/replit_env.sh          # resolves PY now that .venv exists
echo "[build] python: $PY"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r backend/requirements.txt

# re-probe native libs now the ML wheels are installed (no-op if loader is happy)
source scripts/replit_env.sh

# 2) bake the demo scenario through the real engines (~90s locally, longer here)
echo "[build] baking DEMO-FULL (seed 42)…"
(cd backend && "$PY" bake.py)

# 3) frontend production build (BACKEND_ORIGIN unset -> default 127.0.0.1:8000,
#    which is exactly right co-located in one VM)
echo "[build] building frontend…"
(cd frontend && npm ci && npm run build)

echo "[build] done"
