"""`batch_evaluations` (S2-05): migrations 9 and 10, store functions."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app import db, ids
from tests.test_batch_runs_store import row as run_row

BANDS = "core-2026-10-12"


def evaluation(stored: dict, **overrides) -> dict:
    base = {
        "evaluation_id": ids.new_id(), "batch_run_id": stored["batch_run_id"],
        "use_case_id": stored["use_case_id"], "run_id": stored["run_id"],
        "trace_id": stored["trace_id"], "bands_version": BANDS,
        "metrics": json.dumps([]), "delivery_grade": "Green", "grade": "Unknown",
        "baseline_run_ids": json.dumps([]), "evaluated_at": 1.0,
        "langfuse_status": "pending", "langfuse_attempts": 0, "langfuse_error": None,
    }
    return {**base, **overrides}


def test_migrations_nine_and_ten_are_recorded(isolated_db):
    bind = db.engine()
    with bind.begin() as cx:
        names = dict(cx.execute(db.select(db.schema_migrations.c.version,
                                          db.schema_migrations.c.name)).all())
    assert names[9] == "batch evaluations"
    assert names[10] == "uuid7 batch run IDs"


def test_migration_ten_rewrites_old_ids_once(isolated_db):
    bind = db.engine()
    old = str(uuid.uuid5(uuid.NAMESPACE_URL, "batch-run/GCP-UC-03/r1"))
    with bind.begin() as cx:
        cx.execute(db.insert(db.batch_runs), {**run_row(run_id="r1"), "batch_run_id": old,
                                              "received_at": 1_760_000_000.5})
        cx.exec_driver_sql("DELETE FROM schema_migrations WHERE version = 10")
    before = db.get_batch_run("GCP-UC-03", "r1")
    assert db.migrate_engine(bind) == [10]
    after = db.get_batch_run("GCP-UC-03", "r1")
    assert ids.is_uuid7(after["batch_run_id"])
    assert uuid.UUID(after["batch_run_id"]).int >> 80 == 1_760_000_000_500
    assert {k: v for k, v in after.items() if k != "batch_run_id"} == {
        k: v for k, v in before.items() if k != "batch_run_id"}
    with bind.begin() as cx:                         # a second run changes nothing
        cx.exec_driver_sql("DELETE FROM schema_migrations WHERE version = 10")
    assert db.migrate_engine(bind) == [10]
    assert db.get_batch_run("GCP-UC-03", "r1") == after


def test_put_evaluation_once_per_run_and_bands(isolated_db):
    stored, _ = db.put_batch_run(run_row())
    assert db.put_batch_evaluation(evaluation(stored)) is True
    assert db.put_batch_evaluation(evaluation(stored)) is False      # same run, same bands
    assert db.put_batch_evaluation(evaluation(stored, bands_version="other")) is True


def test_unique_key_is_enforced_by_the_database(isolated_db):
    stored, _ = db.put_batch_run(run_row())
    db.put_batch_evaluation(evaluation(stored))
    with pytest.raises(IntegrityError):
        with db.engine().begin() as cx:
            cx.execute(db.insert(db.batch_evaluations), evaluation(stored))


def test_runs_without_evaluation_oldest_first(isolated_db):
    first, _ = db.put_batch_run(run_row(run_id="a"))
    second, _ = db.put_batch_run(run_row(run_id="b"))
    assert [r["run_id"] for r in db.runs_without_evaluation(BANDS)] == ["a", "b"]
    db.put_batch_evaluation(evaluation(first))
    assert [r["run_id"] for r in db.runs_without_evaluation(BANDS)] == ["b"]
    assert [r["run_id"] for r in db.runs_without_evaluation("other")] == ["a", "b"]


def test_batch_run_history_is_the_use_case_only(isolated_db):
    db.put_batch_run(run_row(run_id="a"))
    db.put_batch_run(run_row(run_id="b", use_case_id="GCP-UC-07"))
    history = db.batch_run_history("GCP-UC-03")
    assert len(history) == 1
    assert set(history[0]) == {"batch_run_id", "completed_at", "request_count"}


def test_langfuse_result_and_counts(isolated_db):
    a, _ = db.put_batch_run(run_row(run_id="a"))
    db.put_batch_run(run_row(run_id="b"))
    ev = evaluation(a)
    db.put_batch_evaluation(ev)
    assert db.evaluator_counts(BANDS) == {"unevaluated": 1, "langfuse_pending": 1}
    assert [e["evaluation_id"] for e in db.evaluations_for_langfuse()] == [ev["evaluation_id"]]
    db.set_langfuse_result(ev["evaluation_id"], "pending", "ConnectError")
    pending = db.evaluations_for_langfuse()[0]
    assert pending["langfuse_attempts"] == 1 and pending["langfuse_error"] == "ConnectError"
    db.set_langfuse_result(ev["evaluation_id"], "sent", None)
    assert db.evaluations_for_langfuse() == []
    assert db.evaluator_counts(BANDS) == {"unevaluated": 1, "langfuse_pending": 0}
