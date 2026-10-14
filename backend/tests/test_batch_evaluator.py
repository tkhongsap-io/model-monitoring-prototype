"""Batch evaluator worker (S2-05)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import batch_evaluator as be
from app import db, main, registry
from app.engines import batch_grading
from tests.test_batch_runs_api import AUTH, URL, client, example  # noqa: F401 (fixture)
from tests.test_batch_runs_store import row as run_row


def store(run_id: str, use_case_id: str = "GCP-UC-03", **body) -> dict:
    payload = {"status": "completed", "completed_at": "2026-10-06T02:12:30Z",
               "request_count": 1000, "failed_count": 0, "records": [], **body}
    stored, _ = db.put_batch_run(run_row(
        run_id=run_id, use_case_id=use_case_id, payload=json.dumps(payload),
        request_count=payload["request_count"], failed_count=payload["failed_count"],
        completed_at=payload["completed_at"], content_sha256=run_id.ljust(64, "0")[:64]))
    return stored


class FakeSender:
    def __init__(self, fail_times: int = 0) -> None:
        self.sent: list[str] = []
        self.fail_times = fail_times

    def send(self, evaluation: dict) -> None:
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("down")
        self.sent.append(evaluation["evaluation_id"])


def evaluations() -> list[dict]:
    with db.engine().begin() as cx:
        return [dict(r) for r in cx.execute(db.select(db.batch_evaluations)).mappings().all()]


def test_cycle_grades_each_run_once(isolated_db):
    store("a")
    store("b")
    worker = be.Evaluator(sender=None)
    assert worker.run_cycle() == {"lease": True, "graded": 2, "sent": 0}
    assert worker.run_cycle()["graded"] == 0
    rows = evaluations()
    assert len(rows) == 2
    assert {r["langfuse_status"] for r in rows} == {"skipped"}
    assert all(r["bands_version"] == batch_grading.BANDS_VERSION for r in rows)
    assert worker.last_cycle_at is not None


def test_evaluation_row_content(isolated_db):
    for i in range(1, 7):
        store(f"r{i}", completed_at=f"2026-10-0{i}T00:00:00Z",
              submitted_at=f"2026-10-0{i}T00:00:00Z")
    be.Evaluator(sender=None).run_cycle()
    row = next(r for r in evaluations() if r["run_id"] == "r6")
    metrics = {m["name"]: m for m in json.loads(row["metrics"])}
    assert metrics["volume_change"]["value"] == 1.0                   # 5 earlier runs
    assert metrics["turnaround_s"]["health"] == "Green"               # GCP-UC-03 limit 3600
    assert len(json.loads(row["baseline_run_ids"])) == 5
    assert row["grade"] == "Green" and row["delivery_grade"] == "Green"
    first = next(r for r in evaluations() if r["run_id"] == "r1")
    assert first["grade"] == "Unknown"                                # no_baseline


def test_stored_run_does_not_change(isolated_db):
    stored = store("a")
    be.Evaluator(sender=None).run_cycle()
    assert db.get_batch_run("GCP-UC-03", "a") == stored


def test_second_owner_waits_for_the_lease(isolated_db):
    store("a")
    first, second = be.Evaluator(sender=None), be.Evaluator(sender=None)
    assert first.run_cycle()["lease"] is True
    store("b")
    assert second.run_cycle() == {"lease": False, "graded": 0, "sent": 0}
    assert len(evaluations()) == 1


def test_same_run_twice_makes_one_row(isolated_db, monkeypatch):
    stored = store("a")
    monkeypatch.setattr(db, "runs_without_evaluation", lambda *a, **k: [stored, stored])
    assert be.Evaluator(sender=None).run_cycle()["graded"] == 1
    assert len(evaluations()) == 1


def test_one_bad_run_does_not_stop_the_others(isolated_db, monkeypatch):
    store("bad")
    store("good")
    real = batch_grading.grade_run

    def flaky(body, earlier, limit):
        if body.get("request_count") == 13:
            raise RuntimeError("boom")
        return real(body, earlier, limit)

    db_payload = json.dumps({"status": "completed", "completed_at": "2026-10-06T02:12:30Z",
                             "request_count": 13, "failed_count": 0, "records": []})
    with db.engine().begin() as cx:
        cx.execute(db.update(db.batch_runs).where(db.batch_runs.c.run_id == "bad").values(
            payload=db_payload))
    monkeypatch.setattr(be, "grade_run", flaky)
    assert be.Evaluator(sender=None).run_cycle()["graded"] == 1
    assert [r["run_id"] for r in evaluations()] == ["good"]


def test_run_of_removed_use_case_is_still_graded(isolated_db, monkeypatch):
    store("a", use_case_id="GCP-UC-99", submitted_at="2026-10-06T02:00:00Z")
    be.Evaluator(sender=None).run_cycle()
    metrics = {m["name"]: m for m in json.loads(evaluations()[0]["metrics"])}
    assert metrics["turnaround_s"]["reason"] == "not_reported"


def test_scores_are_sent_and_retried(isolated_db):
    store("a")
    sender = FakeSender(fail_times=1)
    worker = be.Evaluator(sender=sender)
    assert worker.run_cycle()["sent"] == 0
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"], row["langfuse_error"]) == (
        "pending", 1, "ConnectionError")
    assert row["grade"] == "Unknown"
    assert worker.run_cycle()["sent"] == 1
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"]) == ("sent", 2)
    assert row["grade"] == "Unknown"                                  # never changed
    assert sender.sent == [row["evaluation_id"]]


def test_twenty_failures_mark_failed(isolated_db):
    store("a")
    worker = be.Evaluator(sender=FakeSender(fail_times=1000))
    for _ in range(25):
        worker.run_cycle()
    row = evaluations()[0]
    assert (row["langfuse_status"], row["langfuse_attempts"]) == ("failed", 20)


def test_post_does_not_grade(client):
    # `client` is the fixture of test_batch_runs_api.py (imported at the top of this file)
    body = example("01-completed-online.json")
    response = client.post(URL, json=body, headers=AUTH)
    assert response.status_code == 201, response.text
    assert evaluations() == []                       # the POST never grades inline


def test_status_without_worker(isolated_db):
    store("a")
    assert be.status() == {"enabled": False, "last_cycle_at": None,
                           "unevaluated": 1, "langfuse_pending": 0}


def test_readiness_evaluator_counts_when_database_fails(isolated_db, monkeypatch):
    def broken(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(db, "evaluator_counts", broken)
    assert be.status()["unevaluated"] is None and be.status()["langfuse_pending"] is None


def test_lifespan_starts_and_stops_the_worker(isolated_db, monkeypatch):
    monkeypatch.setattr(be.config, "BATCH_EVALUATOR_ENABLED", True)
    monkeypatch.setattr(be.config, "BATCH_EVALUATOR_INTERVAL_S", 0.05)
    monkeypatch.setattr(be.langfuse_scores, "make_sender", lambda: None)
    store("a")
    import time
    with TestClient(main.app):
        deadline = time.time() + 5
        while time.time() < deadline and not evaluations():
            time.sleep(0.05)
        assert be.current() is not None
    assert len(evaluations()) == 1
    assert be.current() is None
