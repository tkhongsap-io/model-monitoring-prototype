"""Dashboard API (S2-07): read-only, registry use cases, no record text."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import batch_evaluator, db, main
from tests.test_batch_runs_api import AUTH, URL, client, example  # noqa: F401 (fixture)

UI_ROW_FIELDS = {"registry_id", "use_case_name", "business_unit", "overall", "current_health",
                 "lanes", "tooltips", "state", "window_id", "observation_id", "batch_id",
                 "content_sha256", "model_version", "record_count", "last_success_at",
                 "trace_id", "grade", "delivery_grade", "bands_version"}


def strings(node) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for value in node.values() for s in strings(value)]
    if isinstance(node, list):
        return [s for value in node for s in strings(value)]
    return []


def test_portfolio_lists_registry_use_cases_in_order(client):
    body = client.get("/api/live/portfolio").json()
    assert [r["registry_id"] for r in body["rows"]] == ["GCP-UC-03", "GCP-UC-07"]
    assert all(r["state"] == "idle" for r in body["rows"])
    for key in ("use_case_count", "overall_counts", "lane_counts", "sync_state", "rows"):
        assert key in body


def test_graded_run_shows_in_portfolio_and_detail(client):
    response = client.post(URL, json=example("01-completed-online.json"), headers=AUTH)
    assert response.status_code == 201, response.text
    batch_evaluator.Evaluator(sender=None).run_cycle()
    row = client.get("/api/live/portfolio").json()["rows"][0]
    assert UI_ROW_FIELDS <= set(row)
    assert set(row["lanes"]) == {"Quality", "Safety & security", "Reliability",
                                 "Drift & degradation", "Feedback & action loop"}
    assert row["grade"] is not None and row["window_id"] == "invoice-summary-2026-10-07"
    detail = client.get("/api/live/use-case/GCP-UC-03").json()
    assert len(detail["signals"]) == 6 and detail["trace_id"] == row["trace_id"]


def test_no_record_text_in_any_response(client):
    body = example("01-completed-online.json")
    client.post(URL, json=body, headers=AUTH)
    batch_evaluator.Evaluator(sender=None).run_cycle()
    secrets = {s for s in strings(body["records"]) if len(s) >= 8}
    assert secrets, "the example must carry record text"
    for path in ("/api/live/portfolio", "/api/live/use-case/GCP-UC-03", "/api/live/alerts"):
        text = client.get(path).text
        assert '"payload"' not in text, path
        for secret in secrets:
            assert secret not in text, (path, secret)


def test_unknown_use_case_is_404(client):
    response = client.get("/api/live/use-case/AICT-L01")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown use case"}


def test_alerts_are_empty(client):
    assert client.get("/api/live/alerts?uc=GCP-UC-03&open=true").json() == {
        "contract_version": "1.1", "redacted": True, "rows": []}


def test_database_error_is_503_with_class_only(client, monkeypatch):
    def broken(*a, **k):
        raise OperationalError("SELECT secret", {}, Exception("password=hunter2"))

    monkeypatch.setattr(db, "latest_batch_run", broken)
    for path in ("/api/live/portfolio", "/api/live/use-case/GCP-UC-03"):
        response = client.get(path)
        assert response.status_code == 503
        assert response.json() == {"detail": "database is not reachable",
                                   "error": "OperationalError"}
        assert "hunter2" not in response.text


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_routes_are_read_only(client, method):
    assert getattr(client, method)("/api/live/portfolio").status_code == 405
