"""S1-13: the app serves only the batch MVP API."""
from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app import config, db, live_poller, main

GOOD_KEY = "test-key-surface-" + "a" * 32
GOOD_ENTRY = "GCP-UC-03:" + hashlib.sha256(GOOD_KEY.encode()).hexdigest()
PG_URL = "postgresql://monitor:secret-password@db.internal:5432/monitor"
ALLOWLIST = {
    ("/api/batch/runs", "post"),
    ("/api/health", "get"),
    ("/api/healthz", "get"),
    ("/api/readiness", "get"),
    ("/api/version", "get"),
}


@pytest.fixture()
def ready_config(isolated_db, monkeypatch):
    """A PostgreSQL URL value and one valid key; the engine is the test SQLite engine."""
    db.engine()                                   # build the SQLite engine first
    monkeypatch.setattr(config, "DATABASE_URL", PG_URL)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", GOOD_ENTRY)


def test_served_routes_are_exactly_the_allowlist():
    paths = main.app.openapi()["paths"]
    served = {(path, method) for path, ops in paths.items() for method in ops}
    assert served == ALLOWLIST


@pytest.mark.parametrize("mode", ["demo", "live"])
@pytest.mark.parametrize("method, path", [
    ("GET", "/"), ("GET", "/docs"), ("GET", "/redoc"), ("GET", "/openapi.json"),
    ("GET", "/api/live/portfolio"), ("POST", "/api/live/poll"),
    ("POST", "/api/live/sources/AICT-L01/skip"), ("GET", "/api/registry"),
    ("GET", "/api/scenario/state"), ("GET", "/api/board"), ("GET", "/heatmap"),
])
def test_prototype_paths_are_404_in_any_mode(monkeypatch, mode, method, path):
    monkeypatch.setattr(config, "CONTROL_TOWER_MODE", mode)
    assert TestClient(main.app).request(method, path).status_code == 404


def test_poller_does_not_start(ready_config):
    with TestClient(main.app):
        assert live_poller.poller().running is False


def test_health_needs_no_database(monkeypatch):
    def broken():
        raise RuntimeError("database is down")

    monkeypatch.setattr(db, "engine", broken)
    client = TestClient(main.app)                 # no lifespan: no startup database call
    for path in ("/api/health", "/api/healthz"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "model-monitor",
                                   "build_sha": config.BUILD_SHA}


def test_readiness_ready(ready_config):
    with TestClient(main.app) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready", "database": {"ok": True, "error": None},
                               "batch_api_keys": 1, "errors": []}


@pytest.mark.parametrize("url, entries, expected", [
    ("", GOOD_ENTRY, ["DATABASE_URL is not set (SQLite is for development only)"]),
    ("sqlite:///x.db", GOOD_ENTRY, ["DATABASE_URL must use PostgreSQL"]),
    (PG_URL, "", ["BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)"]),
    (PG_URL, f"bad-entry, {GOOD_ENTRY}",
     ["BATCH_API_KEY_SHA256 entries 1 are malformed (expected USE_CASE_ID:<64 hex>)"]),
    (PG_URL, "bad-entry, GCP-UC-07:" + "z" * 64,
     ["BATCH_API_KEY_SHA256 entries 1, 2 are malformed (expected USE_CASE_ID:<64 hex>)",
      "BATCH_API_KEY_SHA256 has no valid entry (every request would be 401)"]),
])
def test_readiness_reports_batch_configuration_errors(ready_config, monkeypatch,
                                                      url, entries, expected):
    monkeypatch.setattr(config, "DATABASE_URL", url)
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", entries)
    with TestClient(main.app) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready" and body["errors"] == expected
    assert "z" * 64 not in response.text and "bad-entry" not in response.text


def test_batch_configuration_errors_ignore_prototype_settings(ready_config, monkeypatch):
    for name in ("LIVE_CHURN_URL", "LIVE_CHATBOT_URL", "LIVE_NBA_URL", "LIVE_PRODUCER_URL",
                 "LIVE_TELEMETRY_TOKEN", "LIVE_WORKER_TOKEN", "ANTHROPIC_API_KEY",
                 "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.setattr(config, name, "")
    assert config.batch_configuration_errors() == []


def test_readiness_database_error_shows_type_only(ready_config, monkeypatch):
    class SecretError(Exception):
        pass

    def broken():
        raise SecretError("password=secret-password host=db.internal")

    client = TestClient(main.app)                 # no lifespan: startup would raise
    monkeypatch.setattr(db, "engine", broken)
    response = client.get("/api/readiness")
    assert response.status_code == 503
    body = response.json()
    assert body["database"] == {"ok": False, "error": "SecretError"}
    assert body["errors"] == ["database is not reachable"]
    assert "secret-password" not in response.text and "db.internal" not in response.text


def test_version_makes_no_outbound_call(monkeypatch):
    import httpx

    def no_network(*args, **kwargs):
        raise AssertionError("no outbound call expected")

    # TestClient also inherits Client.send; keep its in-process request working.
    client = TestClient(main.app)
    monkeypatch.setattr(client, "send", client.send)
    monkeypatch.setattr(httpx, "get", no_network)
    monkeypatch.setattr(httpx.Client, "send", no_network)
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"service": "model-monitor", "build_sha": config.BUILD_SHA,
                               "batch_schema": "batch-run/1"}
