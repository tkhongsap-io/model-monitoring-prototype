"""Configuration for the RAI monitoring prototype.

A single dataclass loaded from the environment, mirroring the repo's house style
(cf. tools/llamaindex/llamaparse/config.py): read a repo-root .env, fall back to a
tool-local .env, never overwrite variables already set in the process.

Secrets (OPENAI_API_KEY, LANGFUSE_*) live in .env and are never committed.
Absence of the LLM keys is fine — the LLM lane degrades to a deterministic offline
mode so the whole control tower still runs and demos.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOL_DIR.parents[1]  # tools/rai-monitoring-prototype -> tools -> repo root


def _load_dotenv() -> None:
    """Best-effort .env loading: repo-root first, then tool-local, without clobbering
    variables already present in the environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # dotenv not installed yet — env vars can still be set manually
        return
    load_dotenv(REPO_ROOT / ".env", override=False)
    load_dotenv(TOOL_DIR / ".env", override=False)


@dataclass
class Config:
    # LLM lane (optional)
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    judge_model: str = "gpt-4o-mini"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # paths
    data_dir: Path = field(default_factory=lambda: TOOL_DIR / "artifacts" / "data")
    artifacts_dir: Path = field(default_factory=lambda: TOOL_DIR / "artifacts")

    seed: int = 42

    @property
    def llm_enabled(self) -> bool:
        """True only when we can actually call OpenAI. Without it, the LLM lane runs
        a deterministic offline judge so the demo still works."""
        return bool(self.openai_api_key)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    _load_dotenv()
    return Config(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        chat_model=os.getenv("RAI_CHAT_MODEL", "gpt-4o-mini").strip(),
        judge_model=os.getenv("RAI_JUDGE_MODEL", "gpt-4o-mini").strip(),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "").strip(),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", "").strip(),
        langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip(),
    )
