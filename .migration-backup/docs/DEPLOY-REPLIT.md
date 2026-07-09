# Deploy — Replit (the chosen path): both services in one Reserved VM

Goal: the **existing** bake-mode simulation demo, unchanged, on a real URL —
entirely on Replit. (The Vercel/Fly split in `DEPLOY.md` remains as a fallback.)

```
Browser ──HTTPS──▶ Replit Reserved VM  (https://<name>.replit.app)
                     ├─ Next.js  (0.0.0.0:$PORT)  ← the exposed service
                     │     rewrites /api/*  →  http://127.0.0.1:8000
                     └─ uvicorn  (127.0.0.1:8000, internal only)
                           └─ SQLite baked at BUILD time (backend/bake.py, seed 42)
```

Why this shape:
- **Reserved VM, not Autoscale.** The scenario player + SSE subscribers live in
  process memory; Autoscale (scale-to-zero, multiple stateless instances) would
  break them. Reserved VM = one always-on machine. It's paid (~a few $/mo).
- **One VM, two processes.** Co-located means the frontend's default backend
  origin (`http://127.0.0.1:8000` in `frontend/next.config.mjs`) is already
  right — zero config — and SSE is a local hop (no proxy buffering).

Everything is driven by files already in the repo: `.replit` (modules, deployment
target, build/run commands, port map), `replit.nix` (native libs for
LightGBM/SHAP), `scripts/replit_build.sh`, `scripts/replit_start.sh`.

---

## 1. Import the repo

Replit → **Create Repl → Import from GitHub** → pick this repo
(**it's private — connect the GitHub account** so Replit gets access; per
README/AGENTS.md this repo must stay private).

The `.replit` file configures the workspace automatically (Python 3.12 + Node 20).

## 2. (Optional but recommended) try it in the workspace first

In the workspace **Shell**:

```bash
bash scripts/replit_build.sh   # venv + deps + ~2–5 min bake + frontend build
```

Then press **Run** (wired to `scripts/replit_start.sh`) — the webview should show
the dashboard. This proves the whole stack on Replit's Nix environment before
paying for a deployment.

If the bake or boot fails with `cannot open shared object file` for
`libgomp.so.1` / `libstdc++.so.6`: the fixup in `scripts/replit_env.sh` should
handle it automatically (it searches `/nix/store` and exports
`LD_LIBRARY_PATH`); check its `[replit_env]` log line. `replit.nix` provides the
libs themselves.

## 3. Deploy: Reserved VM

**Deploy** (Publish) → choose **Reserved VM** (`.replit` pins
`deploymentTarget = "gce"`, Replit's token for Reserved VM — but visually
confirm "Reserved VM" is what's selected before publishing):

- **Machine:** at least **2 GB RAM** (4 GB comfortable) — the ML stack
  (Evidently/NannyML/SHAP) is import-heavy and the build runs a full bake +
  `next build`.
- **App type / port:** web server; external port 80 → local **3000**
  (pre-declared in `.replit` `[[ports]]`).
- **Build / Run commands:** pre-filled from `.replit`
  (`bash scripts/replit_build.sh` / `bash scripts/replit_start.sh`).
- **Secrets (before sharing the link — repo is CPG Confidential):**
  - `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` → turns on the HTTP Basic Auth gate in
    `frontend/src/middleware.ts` (off when unset).

Deploy. The build takes several minutes (pip wheels + bake + npm build) — watch
the build logs for `[build] baking DEMO-FULL` and `[build] done`.

## 4. Verify end-to-end

Open `https://<name>.replit.app`:

1. Homepage portfolio map renders (proves the `/api/*` rewrite → uvicorn).
2. Open a use-case drill-down, e.g. AICT-P02 (artifact images + NannyML chart) and
   AICT-P01 (judge scores, traces).
3. Player bar (bottom): **DEMO-FULL → ▶ Play** (`Space`; `←`/`→` step, `R` reset).
   The heatmap advances and flips **Green → Red** as drift is injected, a Critical
   action fires, SLA breaches/escalates, then remediation turns it Green — with
   **live** updates (SSE via `/api/events`).

API spot-checks (same host): `/api/health` → `{"ok":true}`, `/api/summary` →
baked tick-0 portfolio.

## Ops notes

- **Reset the demo:** `R` in the player, or restart the deployment —
  `scripts/replit_start.sh` explicitly resets the player to baked tick 0 on
  every boot, so restart-to-reset is guaranteed (the player otherwise persists
  its tick to SQLite and would resume mid-scenario). Runtime action edits are
  not durable across redeploys; fine for a demo.
- **Redeploy after code changes:** push to GitHub → Redeploy (build re-bakes
  deterministically at seed 42).
- **Scale:** keep it at exactly **one** VM — the player is an in-memory singleton.
- **Port 8000** is intentionally not declared in `.replit` and binds `127.0.0.1`
  only: the backend is unreachable from outside except through the UI proxy
  (which the Basic Auth middleware gates).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `$'\r': command not found` | CRLF line endings — shouldn't happen (`.gitattributes` forces LF on `*.sh`); if it does: `sed -i 's/\r$//' scripts/*.sh` |
| `cannot open shared object file: libgomp.so.1` | See §2 — `replit_env.sh` fixup + `replit.nix` deps |
| Build killed / OOM | Bump the VM RAM (4 GB) and rebuild |
| UI up but `/api/*` 502s | Backend died — check logs for a Python traceback; the supervisor exits so the VM restarts; `bash scripts/replit_start.sh` in Shell to reproduce |
| Player doesn't advance live | Check the browser console for the `/api/events` EventSource. SSE streams through the Next rewrite proxy; `next.config.mjs` pins `experimental.proxyTimeout` to 5 min because the backend pings every 15s and Next's default 30s inactivity timeout would otherwise sit one missed ping away from cutting the stream |
