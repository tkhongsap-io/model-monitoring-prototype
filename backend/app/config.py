"""Configuration — env-driven, all optional (PRD Appendix E §E.4 / NF1).

The demo runs with an empty .env: zero keys, zero network (Langfuse stub default).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

try:  # best-effort .env loading (repo root, then backend-local); never clobber real env
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(BACKEND_DIR / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str) -> str:
    v = os.getenv(name, "").strip()
    return v or default


DEMO_SEED = int(_env("DEMO_SEED", "42"))
LLM_EVAL_ADAPTER = _env("LLM_EVAL_ADAPTER", "langfuse_stub")
ML_MONITOR_ADAPTER = _env("ML_MONITOR_ADAPTER", "evidently_nannyml")
EXPLAIN_ADAPTER = _env("EXPLAIN_ADAPTER", "lime_shap")

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "").strip() or "https://cloud.langfuse.com"

DB_PATH = Path(_env("RAI_DB_PATH", str(BACKEND_DIR / "control_tower.db")))
ARTIFACTS_DIR = Path(_env("RAI_ARTIFACTS_DIR", str(BACKEND_DIR / "artifacts")))
SCENARIOS_YAML = BACKEND_DIR / "scenarios" / "simulation.yaml"
SEEDS_DIR = BACKEND_DIR / "seeds"

DEFAULT_SCENARIO = _env("RAI_DEFAULT_SCENARIO", "DEMO-FULL")

# --- live monitoring (Stage 2+): the monitor PULLS telemetry from external model apps ---
# Base URLs are operator-configured; the demo still runs fully offline (baked DEMO-FULL)
# when the model apps aren't up — the live path is only exercised via /api/live/*.
LIVE_CHURN_URL = _env("LIVE_CHURN_URL", "http://127.0.0.1:8083")
LIVE_CHATBOT_URL = _env("LIVE_CHATBOT_URL", "http://127.0.0.1:8082")
LIVE_POLL_SECONDS = int(_env("LIVE_POLL_SECONDS", "0"))   # 0 = manual (POST /api/live/tick)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
LLM_JUDGE_MODEL = _env("LLM_JUDGE_MODEL", "claude-opus-4-8")


def langfuse_cloud_configured() -> bool:
    return bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)


def live_enabled() -> bool:
    return bool(LIVE_CHURN_URL)
