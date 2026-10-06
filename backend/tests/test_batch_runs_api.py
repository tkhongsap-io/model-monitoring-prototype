"""Receiving API `POST /api/batch/runs` (S1-02, issue #4).

The route runs behind the real strict-live middleware, as on the test host. Each
acceptance criterion of the issue has a test here; the S1-01 examples are the bodies.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import config, db, main
from app.api import batch_routes

EXAMPLES = (Path(__file__).resolve().parents[2] / "changes" / "2026-10-02-batch-monitoring-mvp"
            / "schema" / "examples")
KEY_03 = "test-key-uc03-" + "a" * 32
KEY_07 = "test-key-uc07-" + "b" * 32
AUTH = {"Authorization": f"Bearer {KEY_03}"}
TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
TRACEPARENT = f"00-{TRACE_ID}-00f067aa0ba902b7-01"
URL = "/api/batch/runs"


def sha(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def example(name: str, folder: str = "valid") -> dict:
    return json.loads((EXAMPLES / folder / name).read_text(encoding="utf-8"))


@pytest.fixture()
def client(isolated_db, monkeypatch) -> TestClient:
    monkeypatch.setattr(config, "LIVE_POLL_SECONDS", 0)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{sha(KEY_03)}, GCP-UC-07:{sha(KEY_07)}")
    assert config.strict_live_mode()
    strict_app = FastAPI()
    strict_app.include_router(batch_routes.router)
    strict_app.middleware("http")(main.strict_live_route_isolation)
    with TestClient(strict_app) as c:
        yield c


def rows() -> list[dict]:
    return db.list_batch_runs()


# ---- acceptance criteria ----------------------------------------------------------

def test_correct_body_and_key_201_one_row(client):
    body = example("01-completed-online.json")
    response = client.post(URL, json=body, headers={**AUTH, "traceparent": TRACEPARENT})
    assert response.status_code == 201, response.text
    out = response.json()
    assert out["status"] == "created"
    assert (out["use_case_id"], out["run_id"]) == ("GCP-UC-03", "invoice-summary-2026-10-07")
    assert out["record_count"] == 2 and out["trace_id"] == TRACE_ID
    stored = rows()
    assert len(stored) == 1
    assert stored[0]["trace_id"] == TRACE_ID and stored[0]["trace_id_source"] == "traceparent"
    assert stored[0]["status"] == "completed" and stored[0]["sample_size"] == 50


def test_same_body_again_200_still_one_row(client):
    body = example("01-completed-online.json")
    first = client.post(URL, json=body, headers={**AUTH, "traceparent": TRACEPARENT})
    assert first.status_code == 201
    before = db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-07")
    # a retry: other whitespace and key order, and a new trace, is the same content
    retry = json.dumps(dict(reversed(list(body.items()))), indent=2)
    other_trace = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
    again = client.post(URL, content=retry, headers={
        **AUTH, "traceparent": other_trace, "Content-Type": "application/json"})
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "duplicate"
    assert again.json()["trace_id"] == TRACE_ID          # the stored row answers
    assert len(rows()) == 1
    assert db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-07") == before


def test_same_run_other_content_409_first_row_unchanged(client):
    body = example("01-completed-online.json")
    assert client.post(URL, json=body, headers=AUTH).status_code == 201
    before = db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-07")
    body["failed_count"] = 3
    response = client.post(URL, json=body, headers=AUTH)
    assert response.status_code == 409, response.text
    assert len(rows()) == 1
    assert db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-07") == before


def _unknown_field(b):
    b["records"][0]["customer_id"] = "C-0000001"


def _missing_record_field(b):
    del b["records"][0]["refused"]


def _zero_latency(b):
    b["records"][0]["latency_s"] = 0


def _more_records_than_sample(b):
    b["sample"]["size"] = 1


@pytest.mark.parametrize("mutate, loc", [
    (_unknown_field, ["records", 0, "customer_id"]),
    (_missing_record_field, ["records", 0, "refused"]),
    (_zero_latency, ["records", 0, "latency_s"]),
    (_more_records_than_sample, ["records"]),
])
def test_wrong_body_400_with_field_errors_nothing_stored(client, mutate, loc):
    body = example("01-completed-online.json")
    mutate(body)
    response = client.post(URL, json=body, headers=AUTH)
    assert response.status_code == 400, response.text
    assert loc in [e["loc"] for e in response.json()["errors"]]
    assert rows() == []


@pytest.mark.parametrize("name", sorted(p.name for p in (EXAMPLES / "invalid").glob("*.json")))
def test_invalid_examples_400(client, name):
    response = client.post(URL, json=example(name, "invalid"), headers=AUTH)
    assert response.status_code == 400
    assert response.json()["errors"]
    assert rows() == []


def test_not_json_400(client):
    response = client.post(URL, content=b"{not json",
                           headers={**AUTH, "Content-Type": "application/json"})
    assert response.status_code == 400
    assert rows() == []


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer wrong-key"},
    {"Authorization": KEY_03},                         # no Bearer scheme
    {"Authorization": "Basic " + KEY_03},
    {"Authorization": "Bearer "},
    {"Authorization": "Bearer " + sha(KEY_03)},        # the hash is not the key
])
def test_no_key_or_wrong_key_401_nothing_stored(client, headers):
    response = client.post(URL, json=example("01-completed-online.json"), headers=headers)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert rows() == []


def test_key_check_comes_before_body_check(client):
    response = client.post(URL, json={"not": "a run"}, headers={"Authorization": "Bearer x"})
    assert response.status_code == 401


def test_no_keys_configured_fails_closed(client, monkeypatch):
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", "")
    response = client.post(URL, json=example("01-completed-online.json"), headers=AUTH)
    assert response.status_code == 401
    assert rows() == []


def test_key_of_other_use_case_403_nothing_stored(client):
    body = example("01-completed-online.json")                  # GCP-UC-03
    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {KEY_07}"})
    assert response.status_code == 403
    assert rows() == []
    ok = client.post(URL, json=example("03-batch-api-null-latency.json"),
                     headers={"Authorization": f"Bearer {KEY_07}"})
    assert ok.status_code == 201


def test_two_keys_for_one_use_case_both_work(client, monkeypatch):
    new_key = "rotated-key-" + "c" * 32
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{sha(KEY_03)},GCP-UC-03:{sha(new_key)}")
    assert client.post(URL, json=example("01-completed-online.json"),
                       headers=AUTH).status_code == 201
    assert client.post(URL, json=example("02-partial-failure.json"),
                       headers={"Authorization": f"Bearer {new_key}"}).status_code == 201


def test_records_stored_as_they_arrived(client):
    body = example("01-completed-online.json")
    assert client.post(URL, json=body, headers=AUTH).status_code == 201
    stored = db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-07")
    payload = json.loads(stored["payload"])
    assert payload == body
    assert [r["record_id"] for r in payload["records"]] == ["req-000412", "req-001207"]
    assert stored["record_count"] == 2
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert stored["content_sha256"] == hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_identity_only_body_is_stored(client):
    body = example("04-identity-only.json")
    response = client.post(URL, json=body, headers=AUTH)
    assert response.status_code == 201
    stored = db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-06")
    assert stored["record_count"] == 0
    assert stored["records_reason"] == "records_not_approved"
    assert json.loads(stored["payload"])["records"] == []


@pytest.mark.parametrize("name", sorted(p.name for p in (EXAMPLES / "valid").glob("*.json")))
def test_every_valid_example_is_stored(client, name):
    body = example(name)
    key = KEY_07 if body["use_case_id"] == "GCP-UC-07" else KEY_03
    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {key}"})
    assert response.status_code == 201, response.text


def test_body_too_large_413_nothing_stored(client, monkeypatch):
    monkeypatch.setattr(config, "BATCH_MAX_BODY_BYTES", 100)
    response = client.post(URL, json=example("01-completed-online.json"), headers=AUTH)
    assert response.status_code == 413
    assert rows() == []


# ---- trace ID ---------------------------------------------------------------------

@pytest.mark.parametrize("header", [
    None,
    "",
    "garbage",
    "00-" + "0" * 32 + "-00f067aa0ba902b7-01",           # all-zero trace ID
    f"00-{TRACE_ID}-" + "0" * 16 + "-01",                # all-zero parent ID
    f"ff-{TRACE_ID}-00f067aa0ba902b7-01",                # forbidden version
    f"00-{TRACE_ID.upper()}-00f067aa0ba902b7-01",        # upper case
    f"00-{TRACE_ID}-00f067aa0ba902b7-01-extra",          # version 00 has four parts
])
def test_missing_or_invalid_traceparent_starts_a_new_trace(client, header):
    headers = dict(AUTH)
    if header is not None:
        headers["traceparent"] = header
    response = client.post(URL, json=example("04-identity-only.json"), headers=headers)
    assert response.status_code == 201
    trace_id = response.json()["trace_id"]
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id) and trace_id != "0" * 32
    assert trace_id != TRACE_ID
    stored = db.get_batch_run("GCP-UC-03", "invoice-summary-2026-10-06")
    assert stored["trace_id"] == trace_id and stored["trace_id_source"] == "generated"


def test_parse_traceparent():
    parse = batch_routes.parse_traceparent
    assert parse(TRACEPARENT) == TRACE_ID
    assert parse(f"  {TRACEPARENT} ") == TRACE_ID
    # a later version may add fields after the flags (W3C Trace Context, versioning)
    assert parse(f"01-{TRACE_ID}-00f067aa0ba902b7-01-future") == TRACE_ID
    assert parse(f"00-{TRACE_ID}-00f067aa0ba902b7") is None
    assert parse(None) is None


# ---- logging and routing ----------------------------------------------------------

def test_key_and_body_never_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    body = example("01-completed-online.json")
    client.post(URL, json=body, headers=AUTH)                                   # 201
    client.post(URL, json=body, headers=AUTH)                                   # 200
    changed = {**body, "failed_count": 9}
    client.post(URL, json=changed, headers=AUTH)                                # 409
    client.post(URL, json={**body, "extra": "x"}, headers=AUTH)                 # 400
    client.post(URL, json=body, headers={"Authorization": f"Bearer {KEY_03}x"})  # 401
    client.post(URL, json=body, headers={"Authorization": f"Bearer {KEY_07}"})   # 403
    text = "\n".join(r.getMessage() + " " + json.dumps(r.__dict__, default=str)
                     for r in caplog.records)
    assert "batch run" in text                                # the route does log
    for secret in (KEY_03, KEY_07, sha(KEY_03), "Summarize this invoice", "[EMAIL]",
                   "Fibre 1 Gbps"):
        assert secret not in text


def test_get_and_other_methods_unreachable_in_strict_mode(client):
    assert client.get(URL).status_code == 404
    assert client.get("/api/batch/runs/GCP-UC-03").status_code == 404
    assert client.put(URL, json={}, headers=AUTH).status_code == 404


def test_route_is_mounted_on_the_app(monkeypatch):
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", "")
    # no lifespan (no `with`): the key check answers before any database access
    response = TestClient(main.app).post(URL, json={})
    assert response.status_code == 401                       # not 404: the route exists


# ---- configuration ----------------------------------------------------------------

def test_key_hash_parsing_and_configuration_errors(monkeypatch):
    good = sha(KEY_03)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{good}, bad-entry, GCP-UC-07:{'z' * 64}, :{good}")
    assert config.batch_api_key_hashes() == [(good, "GCP-UC-03")]
    monkeypatch.setattr(config, "CONTROL_TOWER_MODE", "live")
    monkeypatch.setattr(config, "ALLOW_INSECURE_LIVE_TESTING", False)
    errors = [e for e in config.live_configuration_errors() if "BATCH_API_KEY_SHA256" in e]
    assert errors == ["BATCH_API_KEY_SHA256 entries 2, 3, 4 are malformed "
                      "(expected USE_CASE_ID:<64 hex>)"]
    assert "bad-entry" not in errors[0] and good not in errors[0]
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", "")
    assert not [e for e in config.live_configuration_errors() if "BATCH" in e]


def test_upper_case_hash_is_accepted(monkeypatch):
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", f"GCP-UC-03:{sha(KEY_03).upper()}")
    assert config.batch_api_key_hashes() == [(sha(KEY_03), "GCP-UC-03")]
