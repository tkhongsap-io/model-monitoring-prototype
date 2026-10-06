"""`batch_runs` persistence (S1-02): migration 8, store once, never rewrite."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app import db


def row(**overrides) -> dict:
    base = {
        "use_case_id": "GCP-UC-03", "run_id": "invoice-summary-2026-10-06",
        "schema_version": "batch-run/1", "status": "completed",
        "completed_at": "2026-10-06T02:12:30Z", "request_count": 1795, "failed_count": 2,
        "model": "gemini-2.5-flash", "sample_method": "uniform_random", "sample_size": 50,
        "records_reason": "records_not_approved", "record_count": 0,
        "content_sha256": "a" * 64, "payload": '{"records":[]}',
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "trace_id_source": "traceparent",
    }
    return {**base, **overrides}


def test_migration_eight_is_recorded_and_idempotent(isolated_db):
    bind = db.engine()
    assert db.migrate_engine(bind) == []
    with bind.begin() as cx:
        versions = list(cx.execute(db.select(db.schema_migrations.c.version)).scalars())
        names = dict(cx.execute(db.select(db.schema_migrations.c.version,
                                          db.schema_migrations.c.name)).all())
    assert versions == [1, 2, 3, 4, 5, 6, 7, 8]
    assert names[8] == "batch run summaries"


def test_migration_eight_adds_the_table_to_an_old_database(isolated_db):
    bind = db.engine()
    with bind.begin() as cx:
        cx.exec_driver_sql("DROP TABLE batch_runs")
        cx.exec_driver_sql("DELETE FROM schema_migrations WHERE version = 8")
    assert db.migrate_engine(bind) == [8]
    stored, outcome = db.put_batch_run(row())
    assert outcome == "created" and stored["run_id"] == "invoice-summary-2026-10-06"


def test_put_created_then_duplicate(isolated_db):
    first, outcome = db.put_batch_run(row())
    assert outcome == "created"
    assert first["batch_run_id"] and first["received_at"] > 0
    again, outcome = db.put_batch_run(row(trace_id="c" * 32))
    assert outcome == "duplicate"
    assert again == first                         # the first row answers, unchanged
    assert len(db.list_batch_runs()) == 1


def test_put_conflict_leaves_first_row(isolated_db):
    first, _ = db.put_batch_run(row())
    with pytest.raises(db.BatchRunConflict):
        db.put_batch_run(row(content_sha256="b" * 64, failed_count=9))
    assert db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-06") == first
    assert len(db.list_batch_runs()) == 1


def test_same_run_id_for_other_use_case_is_another_run(isolated_db):
    db.put_batch_run(row())
    _, outcome = db.put_batch_run(row(use_case_id="GCP-UC-07"))
    assert outcome == "created"
    assert len(db.list_batch_runs()) == 2
    assert [r["use_case_id"] for r in db.list_batch_runs("GCP-UC-07")] == ["GCP-UC-07"]


def test_unique_pair_is_enforced_by_the_database(isolated_db):
    db.put_batch_run(row())
    with pytest.raises(IntegrityError):
        with db.engine().begin() as cx:
            cx.execute(db.insert(db.batch_runs), {
                **row(content_sha256="b" * 64), "batch_run_id": "other", "received_at": 1.0})


def test_get_missing_run_is_none(isolated_db):
    assert db.get_batch_run("GCP-UC-03", "nope") is None
