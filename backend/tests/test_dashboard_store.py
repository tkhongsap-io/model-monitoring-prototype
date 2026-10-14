"""Dashboard read functions (S2-07)."""
from __future__ import annotations

import json

from app import db, ids
from tests.test_batch_runs_store import row as run_row

BANDS = "core-2026-10-12"


def evaluation(stored: dict, at: float, grade: str = "Green") -> dict:
    return {"evaluation_id": ids.new_id(at), "batch_run_id": stored["batch_run_id"],
            "use_case_id": stored["use_case_id"], "run_id": stored["run_id"],
            "trace_id": stored["trace_id"], "bands_version": BANDS, "metrics": json.dumps([]),
            "delivery_grade": "Green", "grade": grade, "baseline_run_ids": "[]",
            "evaluated_at": at, "langfuse_status": "skipped", "langfuse_attempts": 0,
            "langfuse_error": None}


def test_latest_run_is_the_newest_received(isolated_db):
    db.put_batch_run(run_row(run_id="a"))
    second, _ = db.put_batch_run(run_row(run_id="b"))
    db.put_batch_run(run_row(run_id="c", use_case_id="GCP-UC-07"))
    assert db.latest_batch_run("GCP-UC-03")["run_id"] == second["run_id"]
    assert db.latest_batch_run("GCP-UC-99") is None


def test_latest_evaluation_and_history(isolated_db):
    a, _ = db.put_batch_run(run_row(run_id="a"))
    b, _ = db.put_batch_run(run_row(run_id="b"))
    db.put_batch_evaluation(evaluation(a, 10.0, "Amber"))
    db.put_batch_evaluation(evaluation(b, 20.0, "Green"))
    assert db.latest_evaluation(b["batch_run_id"], BANDS)["grade"] == "Green"
    assert db.latest_evaluation(b["batch_run_id"], "other") is None
    assert [e["grade"] for e in db.evaluation_history("GCP-UC-03", BANDS)] == ["Green", "Amber"]
    assert len(db.evaluation_history("GCP-UC-03", BANDS, limit=1)) == 1
