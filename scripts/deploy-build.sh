#!/usr/bin/env bash
# Deployment build (Replit Reserved VM): build the dashboard SPA, then the backend.
# The FastAPI backend serves the built SPA from artifacts/control-tower/dist/public,
# so the deployed monitor is ONE service on $PORT (dashboard + /api together).
set -euo pipefail
cd "$(dirname -- "$0")/.."

echo "[deploy-build] 1/3 workspace install (pnpm)…"
corepack enable >/dev/null 2>&1 || true
CI=true corepack pnpm install --frozen-lockfile || CI=true corepack pnpm install

echo "[deploy-build] 2/3 dashboard build (vite)…"
# vite.config.ts requires PORT + BASE_PATH; PORT is unused by `build` but validated.
(cd artifacts/control-tower && PORT="${PORT:-5000}" BASE_PATH="/" \
  node node_modules/vite/bin/vite.js build)

echo "[deploy-build] 3/3 backend build (venv + deps + bake)…"
bash backend/build.sh

echo "[deploy-build] done"
