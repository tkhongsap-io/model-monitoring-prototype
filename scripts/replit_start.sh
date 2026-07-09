#!/usr/bin/env bash
# Replit RUN step (.replit run + [deployment].run) — supervise both processes:
#   uvicorn  127.0.0.1:8000   (internal only; reached via the Next /api rewrite,
#                              which is BAKED to 127.0.0.1:8000 at build time —
#                              changing the port requires a frontend rebuild
#                              with BACKEND_ORIGIN set, so it is not a knob here)
#   Next.js  0.0.0.0:$PORT    (the exposed service; $PORT injected by Replit,
#                              falls back to 3000 = the .replit ports map)
# Boot resets the scenario player to baked tick 0, so every (re)start lands on
# a clean demo — the R-34 reset semantics. If either process dies, the trap
# kills the other and exits non-zero so the Reserved VM restarts the service.
set -euo pipefail
cd "$(dirname -- "$0")/.."
source scripts/replit_env.sh

if [ -z "${PY:-}" ]; then
  echo "[start] no venv found — run: bash scripts/replit_build.sh" >&2
  exit 1
fi
if [ ! -f backend/control_tower.db ]; then
  echo "[start] no baked database — run: bash scripts/replit_build.sh" >&2
  exit 1
fi
if [ ! -d frontend/.next ] || [ ! -e frontend/node_modules/.bin/next ]; then
  echo "[start] no frontend build/node_modules — run: bash scripts/replit_build.sh" >&2
  exit 1
fi

UI_PORT="${PORT:-3000}"

# deterministic boot: player at baked tick 0, paused (makes restart == demo reset)
(cd backend && "$PY" -c "from app import db, config; db.put_state(scenario_id=config.DEFAULT_SCENARIO, tick=0, playing=0, speed=1, mode='baked', seed=config.DEMO_SEED)")
echo "[start] player reset to baked tick 0"

trap 'trap - TERM INT EXIT; kill 0 2>/dev/null || true' TERM INT EXIT

echo "[start] backend: uvicorn on 127.0.0.1:8000"
(cd backend && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK_PID=$!

# wait for the API before exposing the UI; fail fast if the backend died
healthy=0
for _ in $(seq 1 60); do
  if ! kill -0 "$BACK_PID" 2>/dev/null; then
    echo "[start] backend process died during startup — see traceback above" >&2
    exit 1
  fi
  if "$PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" >/dev/null 2>&1; then
    healthy=1
    break
  fi
  sleep 1
done
if [ "$healthy" != 1 ]; then
  echo "[start] backend not healthy after 60s — aborting so the VM restarts" >&2
  exit 1
fi
echo "[start] backend healthy"

echo "[start] frontend: next start on 0.0.0.0:${UI_PORT}"
# pinned local binary on purpose — bare `npx next` would silently download
# next@latest if node_modules were missing, instead of failing loudly
(cd frontend && exec node_modules/.bin/next start -H 0.0.0.0 -p "$UI_PORT") &

wait -n
echo "[start] a process exited — shutting down" >&2
exit 1
