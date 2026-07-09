# Deploy — Vercel + Fly.io (ALTERNATIVE path — kept as fallback)

> **The chosen deployment path is Replit — see `docs/DEPLOY-REPLIT.md`.**
> This Vercel/Fly split remains fully prepared (Dockerfile, fly.toml) if we
> ever outgrow the single-VM shape.

# Deploy — Phase 0 (the current bake-mode demo on a real URL)

Goal: put the **existing** simulation demo online, unchanged. No model work yet —
this de-risks deployment on its own. Topology:

```
Browser ──HTTPS──▶ Vercel (Next.js UI)
                     │  rewrites /api/*  (BACKEND_ORIGIN, set at build)
                     ▼
                   Fly.io (FastAPI + ML engines, always-on 1 machine)
                     └─ SQLite baked into the image at build time (seed 42)
```

Why this split: the backend is a **stateful, fat, always-on** process (persistent
SQLite, a long-running `/api/events` SSE stream, an in-process asyncio scenario
player, 300MB+ of Evidently/NannyML/SHAP). That does not fit serverless — it needs
Fly's real container. The Next.js UI is a natural fit for Vercel.

---

## 0. Prerequisites (one-time)

- A [Fly.io](https://fly.io) account and a [Vercel](https://vercel.com) account.
- Install the CLIs (PowerShell):
  ```powershell
  # Fly (no local Docker needed — Fly builds remotely)
  iwr https://fly.io/install.ps1 -useb | iex
  # Vercel
  npm i -g vercel
  ```
- Log in. These are **interactive** — run them from the Claude prompt with a
  leading `!` so the browser-auth output lands in this session:
  ```
  ! fly auth login
  ! vercel login
  ```

You do **not** need Docker locally; `fly deploy` uses a remote builder.

---

## 1. Backend → Fly.io

From the `backend/` directory (the `Dockerfile`, `.dockerignore`, `fly.toml`,
and `bake.py` are already here):

```powershell
cd backend

# First time: create the app. Reuse the existing fly.toml when prompted; say NO
# to "deploy now" and NO to Postgres/Redis. Pick a unique app name (or keep the
# one in fly.toml if free) and region 'sin' (Singapore).
fly launch --no-deploy

# Build (remote) + bake (seed 42, ~90s inside the build) + release.
fly deploy
```

The build runs `python bake.py` so the image ships demo-ready. When it finishes:

```powershell
fly open            # opens https://<your-app>.fly.dev
fly logs            # watch startup: "[startup] registry rows: 130"
```

Smoke-test the API directly:
```powershell
curl https://<your-app>.fly.dev/api/health      # {"ok":true}
curl https://<your-app>.fly.dev/api/summary      # baked tick-0 portfolio
```

Note the URL — you need it for the frontend. If `fly` rejects
`auto_stop_machines = "off"`, change it to `false` in `fly.toml` and redeploy.

---

## 2. Frontend → Vercel

The UI only ever calls same-origin `/api/*`; `next.config.mjs` rewrites those to
`BACKEND_ORIGIN`. Point that at the Fly URL.

**Dashboard route (simplest):** New Project → import this repo →
- **Root Directory:** `frontend`
- **Framework preset:** Next.js (auto-detected)
- **Environment Variables:**
  - `BACKEND_ORIGIN = https://<your-app>.fly.dev`  ← no trailing slash
- Deploy.

**CLI route (from `frontend/`):**
```powershell
cd frontend
vercel                     # link/create the project (root dir = current)
vercel env add BACKEND_ORIGIN production   # paste https://<your-app>.fly.dev
vercel --prod              # build + deploy
```

`BACKEND_ORIGIN` is read at **build time**, so after changing it, redeploy
(`vercel --prod`) for it to take effect.

---

## 3. Verify end-to-end

Open the Vercel URL and:
1. The homepage portfolio map renders (proves `/api/summary` proxies to Fly).
2. Open a use-case drill-down (proves artifact/trace reads).
3. In the docked player bar: pick **DEMO-FULL** → **▶ Play** (or `Space`).
   The heatmap should advance and eventually flip **Green → Red** as drift is
   injected, then recover. This exercises the SSE stream `/api/events`.

If the player advances but the UI doesn't update live (values only refresh on
manual reload), SSE is being **buffered** by the rewrite proxy — see below.

---

## SSE caveat (only if step 3's live updates stall)

Vercel rewrites can buffer streamed responses. Fallback: point the browser's
`EventSource` straight at the Fly origin (bypassing the rewrite) and enable CORS
on the backend. That's a ~10-line change (a `NEXT_PUBLIC_EVENTS_URL` env for the
`EventSource("/api/events")` in `frontend/src/lib/sim.tsx`, plus FastAPI
`CORSMiddleware`). Ping me and I'll wire it — leaving it out for now since the
rewrite handles SSE fine in most setups.

---

## Hardening (before sharing the link — this repo is CPG Confidential)

README/AGENTS.md: **keep private, no real True data, no PII.** Phase 0 gives a
public URL, so gate it:

- **Frontend:** set both `BASIC_AUTH_USER` and `BASIC_AUTH_PASS` in Vercel env
  → `frontend/src/middleware.ts` enforces HTTP Basic Auth over the whole app.
  (Or use Vercel's built-in Deployment Protection / password on paid plans.)
- **Backend:** the Fly URL stays directly reachable. For a small demo, keep it
  unguessable. To lock it down properly later, put it behind Fly private
  networking + a server-side proxy, or add a shared-secret header the rewrite
  forwards. Ask when you want this.
- **Data:** all telemetry here is synthetic by design — keep it that way. The
  Phase-1 "real model" experiment must run on synthetic or public data only.

---

## Cost & ops

- Fly: one `shared-cpu-1x` / 1GB machine, always on. Small. `fly scale count 1`
  keeps it single (required — the player is an in-memory singleton).
- Vercel: Hobby tier covers this.
- **Redeploy after code changes:** backend → `cd backend && fly deploy`
  (re-bakes in the build); frontend → `cd frontend && vercel --prod`.
- **Reset the demo:** `fly apps restart <your-app>` returns it to baked tick 0.
