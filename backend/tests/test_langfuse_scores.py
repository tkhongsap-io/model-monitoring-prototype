"""Langfuse scores of one evaluation (S2-05)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app import config
from app.adapters import langfuse_scores as ls


def metrics(**health) -> str:
    base = [
        {"name": "run_status", "lane": "Delivery", "value": None, "health": "Green",
         "reason": None, "in_rollup": True},
        {"name": "turnaround_s", "lane": "Delivery", "value": None, "health": "Unknown",
         "reason": "not_reported", "in_rollup": True},
        {"name": "failure_rate", "lane": "Reliability", "value": 0.002, "health": "Green",
         "reason": None, "in_rollup": True},
        {"name": "volume_change", "lane": "Reliability", "value": None, "health": "Unknown",
         "reason": "no_baseline", "in_rollup": True},
        {"name": "valid_output_rate", "lane": "Output", "value": None, "health": "Unknown",
         "reason": "records_not_approved", "in_rollup": False},
    ]
    return json.dumps(base)


EVALUATION = {"use_case_id": "rtr-fraud-validation",
              "evaluation_id": "0199e0a0-0000-7000-8000-000000000001",
              "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "bands_version": "core-2026-10-12",
              "metrics": metrics(), "grade": "Unknown", "delivery_grade": "Unknown"}


class FakeScores:
    def __init__(self, fail_times: int = 0) -> None:
        self.calls: list[dict] = []
        self.fail_times = fail_times

    def create(self, **kwargs):
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("down")
        self.calls.append(kwargs)


def fake_client(scores: FakeScores):
    return SimpleNamespace(api=SimpleNamespace(scores=scores))


def test_score_list():
    scores = {s["name"]: s for s in ls.scores_for(EVALUATION)}
    assert set(scores) == {"grade", "delivery_grade", "failure_rate"}
    assert scores["grade"]["value"] == "Unknown" and scores["grade"]["data_type"] == "CATEGORICAL"
    assert scores["grade"]["comment"] == "bands core-2026-10-12; unknown: volume_change=no_baseline"
    assert scores["delivery_grade"]["comment"] == (
        "bands core-2026-10-12; unknown: turnaround_s=not_reported")
    assert scores["failure_rate"] == {
        "id": ls.score_id(EVALUATION["evaluation_id"], "failure_rate"), "name": "failure_rate",
        "value": 0.002, "data_type": "NUMERIC", "comment": "Green"}


def test_comment_without_unknown():
    clean = json.dumps([{"name": "failure_rate", "lane": "Reliability", "value": 0.0,
                         "health": "Green", "reason": None, "in_rollup": True}])
    grade = next(s for s in ls.scores_for({**EVALUATION, "metrics": clean})
                 if s["name"] == "grade")
    assert grade["comment"] == "bands core-2026-10-12; unknown: none"


def test_score_ids_are_stable_and_distinct():
    first = [s["id"] for s in ls.scores_for(EVALUATION)]
    again = [s["id"] for s in ls.scores_for(EVALUATION)]
    assert first == again and len(set(first)) == len(first)
    other = ls.score_id("0199e0a0-0000-7000-8000-000000000002", "grade")
    assert other not in first


def test_send_calls_the_sync_api_with_the_trace():
    scores = FakeScores()
    ls.LangfuseScoreSender(lambda uc: fake_client(scores)).send(EVALUATION)
    assert {c["name"] for c in scores.calls} == {"grade", "delivery_grade", "failure_rate"}
    for call in scores.calls:
        assert call["trace_id"] == EVALUATION["trace_id"]
        assert call["id"] == ls.score_id(EVALUATION["evaluation_id"], call["name"])
        assert str(call["data_type"]) in ("CATEGORICAL", "NUMERIC")


def test_send_raises_on_failure():
    with pytest.raises(ConnectionError):
        ls.LangfuseScoreSender(lambda uc: fake_client(FakeScores(fail_times=1))).send(EVALUATION)


def test_make_sender_never_uses_the_cloud_default():
    # a fresh process without LANGFUSE_HOST: the prototype default is the cloud, but the
    # evaluator host stays empty, so no sender is made
    import os
    import subprocess
    import sys
    from pathlib import Path
    env = {k: v for k, v in os.environ.items() if k != "LANGFUSE_HOST"}
    env.update(LANGFUSE_PUBLIC_KEY="pk-lf-x", LANGFUSE_SECRET_KEY="sk-lf-x")
    code = ("from app import config; from app.adapters import langfuse_scores as ls; "
            "print(repr(config.EVALUATOR_LANGFUSE_HOST), config.LANGFUSE_HOST, ls.make_sender())")
    out = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                         env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["''", "https://cloud.langfuse.com", "None"]


def test_make_sender_needs_host_and_keys(monkeypatch):
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {"unrouted": ("pk", "sk")})
    assert ls.make_sender() is None
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {})
    assert ls.make_sender() is None


def test_sender_uses_the_project_of_the_use_case(monkeypatch):
    made = []

    class FakeLangfuse:
        def __init__(self, **kwargs):
            made.append(kwargs)
            self.api = SimpleNamespace(scores=FakeScores())

    import langfuse
    monkeypatch.setattr(langfuse, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {
        "unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")})
    sender = ls.make_sender()
    sender.send({**EVALUATION, "use_case_id": "rtr-fraud-validation"})
    sender.send({**EVALUATION, "use_case_id": "rtr-fraud-validation"})   # cached client
    sender.send({**EVALUATION, "use_case_id": "GCP-UC-03"})               # → unrouted
    assert [(m["public_key"], m["secret_key"]) for m in made] == [("pk-r", "sk-r"),
                                                                  ("pk-u", "sk-u")]
    assert all(m["tracing_enabled"] is False and m["host"] == "http://langfuse-web:3000"
               for m in made)


def test_send_without_a_project_raises():
    with pytest.raises(LookupError):
        ls.LangfuseScoreSender(lambda uc: None).send(EVALUATION)
