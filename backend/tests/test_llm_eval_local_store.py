"""S2-02: the chatbot judge keeps traces in the local store only.

The Langfuse SDK v2 store (`LangfuseCloudStore`) was prototype-only code; SDK v4 has no
`trace()` / `score()`. Langfuse keys in the environment must not change the store.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import config
from app.adapters.llm_eval import judge, live_http, stores
from app.adapters.llm_eval.stores import SqliteTraceStore

LLM_EVAL_DIR = Path(__file__).resolve().parents[1] / "app" / "adapters" / "llm_eval"


@pytest.fixture()
def langfuse_keys_set(monkeypatch):
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk")


def test_cloud_store_is_removed():
    assert not hasattr(stores, "LangfuseCloudStore")


def test_seeded_judge_uses_local_store_with_langfuse_keys(langfuse_keys_set):
    adapter = judge.make_llm_eval(42, "DEMO-FULL", "AICT-L02", impl="langfuse_cloud")
    assert type(adapter.store) is SqliteTraceStore


def test_live_adapter_uses_local_store_with_langfuse_keys(langfuse_keys_set):
    adapter = live_http.LiveHttpLLMAdapter("https://producer", "LIVE", "AICT-L02")
    assert type(adapter.store) is SqliteTraceStore


def test_no_langfuse_v2_calls_remain():
    for path in LLM_EVAL_DIR.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from langfuse" not in source, path.name
        assert "import langfuse" not in source, path.name
        assert "._lf" not in source, path.name
