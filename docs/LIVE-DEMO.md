# Live Control Tower — demo runbook

**Classification: CPG Confidential — internal True Corporation use only.**

The dashboard shows **three real AI models being monitored live** — not a simulation:

| Use case | Lane | What it demonstrates |
|---|---|---|
| **AICT-L01 — Customer Churn Prediction** (`telco-churn`, :8083) | ML | Evidently drift, NannyML label-free AUC estimate, realized AUC (label lag), LIME/SHAP |
| **AICT-L02 — Support Chatbot** (`telco-support-chatbot`, :8082) | LLM | LLM-as-judge: groundedness / relevance / hallucination / PII / latency, traces pushed to Langfuse |
| **AICT-L03 — Next-Best-Action Recommender** (`telco-nba`, :8084) | ML+NBA | drift, estimated/realized accept-AUC, **acceptance rate**, **recommendation-mix drift**, offer-mix panel |

Each model implements the same small **telemetry contract** (`docs/MONITORING-CONTRACT.md`); the monitor
reaches OUT to their `/telemetry/*` endpoints, runs the shared health engine, and grades every lane
Green / Amber / Red. **Onboarding a 4th model = one seed row + one URL** (see "Plug in a new model" below).

The baked 130-row simulated portfolio still exists (deterministic golden-bake demo) but is no longer on the
dashboard nav — the dashboard is now live-first.

---

## 1. One-time setup

```powershell
# Python side (monitor + the 3 model apps share the monitor venv):
#   the venv at backend/.venv already has fastapi, evidently, nannyml, lime, shap, rank-bm25, anthropic, langfuse
# Model apps also need the shared package on PYTHONPATH: …/ai-use-cases/shared

# Frontend (once):  from the monitor repo root
corepack pnpm install            # installs the control-tower React app
```

`.env` (monitor repo root, gitignored) should hold your keys — already configured this session:
`ANTHROPIC_API_KEY` (real judge), `LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST` (JP region), and the
`LIVE_CHURN_URL` / `LIVE_CHATBOT_URL` / `LIVE_NBA_URL` app URLs. Judge cost is bounded by
`LLM_JUDGE_MAX_TRACES` (default 20 sampled traces/tick) so a live tick stays ~10-15 s.

## 2. Start everything

Ports: model apps 8081-8084, monitor API 8000, dashboard 5000.

```powershell
$py  = "…/model-monitoring-prototype/backend/.venv/Scripts/python.exe"
$uc  = "…/ai-use-cases"
$be  = "…/model-monitoring-prototype/backend"
$ct  = "…/model-monitoring-prototype/artifacts/control-tower"

# (a) the 3 model apps + account API
$env:PYTHONPATH = "$uc\shared"
uvicorn app.main:app --app-dir "$uc\apps\telecom-account-api" --port 8081   # tool target for the chatbot
uvicorn app.main:app --app-dir "$uc\apps\chatbot"             --port 8082
uvicorn app.main:app --app-dir "$uc\apps\churn-predictor"     --port 8083
uvicorn app.main:app --app-dir "$uc\apps\nba-recommender"     --port 8084

# (b) the monitor backend (reads .env for keys + LIVE_*_URL)
uvicorn app.main:app --app-dir "$be" --port 8000

# (c) the dashboard (Vite dev server, proxies /api -> :8000)
$env:PORT = "5000"; $env:BASE_PATH = "/"
node "$ct\node_modules\vite\bin\vite.js" --port 5000
```

Open **http://localhost:5000**.

## 3. Make it move

The monitor observes **closed** telemetry windows, so the model apps need real traffic first. Two ways:

- **Traffic driver** (drives real inference + advances the apps' clocks + ramps the drift knob):
  ```powershell
  python "$uc\tools\traffic.py" --churn http://127.0.0.1:8083 --chatbot http://127.0.0.1:8082 --nba http://127.0.0.1:8084
  ```
- **Or** just click **"Observe next window"** on the dashboard PlayerBar (or toggle **Auto-observe**) — each
  click advances all three models one window and re-grades. The first tick is ~25 s (baselines + judge warm-up);
  subsequent ticks ~15 s.

Watch the **Heatmap** and **At A Glance** pages turn Green → Amber → Red as drift ramps, then recover after a
retrain. The chatbot's judged traces appear in your Langfuse project in real time.

## 4. Plug in a new model (the template pitch)

This is the story for other IT teams — onboarding a model is **config, not code**:

1. **Implement the contract** on your model service (`docs/MONITORING-CONTRACT.md`): `GET /telemetry/meta`,
   the per-window telemetry pull for your lane (ML: `/telemetry/inferences|labels|reference`; LLM:
   `/telemetry/traces`), and optionally `GET /model/artifact`.
2. **Register it**: add one row to `backend/seeds/live_registry_seed.json` (name / owner / risk tier /
   platform), add its id to `LIVE_UCS` + a `lane_kind` (`"ml"` or `"llm"`) in
   `backend/app/api/live_portfolio.py`, and set its base-URL env var.
3. **Watch it appear** — the shared health engine grades it with the same rubric, and it renders as a new
   Heatmap row + At-A-Glance card + full drill-down. No frontend change.

> "These three are not screenshots — they're real models graded by the same governance rubric. Onboarding a
> fourth is a seed row and a URL, and it renders identically."
