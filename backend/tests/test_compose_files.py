"""S1-06 (local part): static checks of the Compose stack.

Docker does not run on every development computer, so these checks read the files.
The stack itself is tested by scripts/compose-smoke.sh in CI and on macOS.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy" / "compose"
LOCAL_KEY = "local-dev-batch-key-not-a-secret"


def _load(name: str) -> dict:
    return yaml.safe_load((COMPOSE / name).read_text(encoding="utf-8"))


def test_images_are_pinned():
    base, local = _load("compose.yaml"), _load("compose.local.yaml")
    assert base["services"]["collector"]["image"] == \
        "otel/opentelemetry-collector-contrib:0.161.0"
    # every database is PostgreSQL 17 (decided 2026-10-08: Cloud SQL is 17)
    assert local["services"]["postgres"]["image"] == "postgres:17.11-bookworm"
    assert base["services"]["collector-init"]["image"] == "busybox:1.37.0"
    for doc in (base, local):
        for service in doc["services"].values():
            assert not str(service.get("image", "")).endswith(":latest")


def test_base_file_has_no_local_settings():
    base = _load("compose.yaml")["services"]
    assert set(base) == {"backend", "collector", "collector-init"}
    for service in base.values():
        assert "build" not in service and "ports" not in service
    backend = base["backend"]
    env = backend["environment"]
    assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://collector:4318"
    assert env["OTEL_SERVICE_NAME"] == "model-monitor"
    assert "DATABASE_URL" not in env and "BATCH_API_KEY_SHA256" not in env
    assert backend["depends_on"] == {"collector": {"condition": "service_started"}}
    assert "/api/health" in " ".join(backend["healthcheck"]["test"])


def test_local_file_builds_backend_and_waits_for_postgres():
    local = _load("compose.local.yaml")["services"]
    backend = local["backend"]
    assert backend["build"] == "../../backend"
    assert backend["depends_on"]["postgres"] == {"condition": "service_healthy"}
    env = backend["environment"]
    assert env["DATABASE_URL"] == "postgresql://monitor:monitor@postgres:5432/monitor"
    expected = hashlib.sha256(LOCAL_KEY.encode()).hexdigest()
    assert env["BATCH_API_KEY_SHA256"] == f"GCP-UC-03:{expected}"
    assert "ports" not in local["postgres"]
    # PostgreSQL 17 images keep the data in /var/lib/postgresql/data (18 changed it)
    assert local["postgres"]["volumes"] == ["pgdata:/var/lib/postgresql/data"]


def test_ci_database_is_the_local_stack_database():
    ci = yaml.safe_load((ROOT / ".github" / "workflows" / "backend-live.yml")
                        .read_text(encoding="utf-8"))
    ci_image = ci["jobs"]["test-migrate-and-configure"]["services"]["postgres"]["image"]
    local_image = _load("compose.local.yaml")["services"]["postgres"]["image"]
    assert ci_image == local_image


def test_published_ports_are_loopback_only():
    local = _load("compose.local.yaml")["services"]
    published = [port for service in local.values() for port in service.get("ports", [])]
    assert sorted(published) == ["127.0.0.1:4318:4318", "127.0.0.1:8000:8000"]


def test_collector_writes_to_a_volume_that_its_user_owns():
    # The distroless Collector image has no /tmp and runs as uid 10001; a new named volume
    # belongs to root. collector-init gives the volume to uid 10001 before the Collector
    # starts (first CI run of #54 failed with "open /tmp/spans.jsonl: no such file").
    base = _load("compose.yaml")
    init, collector = base["services"]["collector-init"], base["services"]["collector"]
    assert init["volumes"] == ["collector-data:/data"]
    assert init["command"] == ["chown", "-R", "10001:10001", "/data"]
    assert collector["depends_on"] == {
        "collector-init": {"condition": "service_completed_successfully"}}
    assert "collector-data:/data" in collector["volumes"]
    assert "user" not in collector                      # the Collector stays non-root
    assert "collector-data" in base["volumes"]


def test_collector_config_writes_spans_to_the_volume_without_secrets():
    text = (COMPOSE / "otel-collector.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    assert config["receivers"]["otlp"]["protocols"] == {"http": {"endpoint": "0.0.0.0:4318"}}
    assert config["exporters"]["file"]["path"] == "/data/spans.jsonl"
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp"], "processors": ["batch"],
                      "exporters": ["debug", "file"]}
    for word in ("password", "token", "secret", "authorization"):
        assert word not in text.lower()


def test_no_plain_key_in_compose_files():
    for path in COMPOSE.glob("*.yaml"):
        assert LOCAL_KEY not in path.read_text(encoding="utf-8"), path.name


SMOKE = ROOT / "scripts" / "compose-smoke.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "compose-smoke.yml"


def test_smoke_script_cleans_up_and_fails_fast():
    text = SMOKE.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "trap cleanup EXIT" in text and "down -v" in text
    assert 'KEEP:-0' in text
    assert "--wait" in text and "/api/readiness" in text
    assert "monitor.ingest" in text and "docker compose" in text and " cp " in text
    assert "collector:/data/spans.jsonl" in text and "/tmp/spans.jsonl" not in text
    assert "SMOKE PASS" in text and "SMOKE FAIL" in text
    # the key is sent only in the Authorization header, never echoed
    key_lines = [line for line in text.splitlines() if "KEY" in line and "echo" in line]
    assert key_lines == []
    assert "\r\n" not in text                       # LF line endings for bash


def test_ci_workflow_paths():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow[True]                       # PyYAML reads the key `on` as True
    paths = {"deploy/compose/**", "backend/**", "scripts/compose-smoke.sh",
             ".github/workflows/compose-smoke.yml"}
    assert set(triggers["pull_request"]["paths"]) == paths
    assert set(triggers["push"]["paths"]) == paths
    assert triggers["push"]["branches"] == ["dev"]
    job = workflow["jobs"]["smoke"]
    assert job["runs-on"] == "ubuntu-latest" and job["timeout-minutes"] == 15
    assert workflow["permissions"] == {"contents": "read"}
    assert any(step.get("run") == "bash scripts/compose-smoke.sh" for step in job["steps"])
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")


def test_testhost_file_uses_registry_image_and_host_secrets():
    host = _load("compose.testhost.yaml")["services"]
    assert set(host) == {"backend"}                     # no database on the VM (Cloud SQL)
    backend = host["backend"]
    assert backend["image"] == "${BACKEND_IMAGE:?BACKEND_IMAGE is not set}"
    assert "build" not in backend and "environment" not in backend
    assert backend["env_file"] == ["/opt/model-monitor/backend.env"]
    assert backend["ports"] == ["127.0.0.1:8000:8000"]   # no front door yet
    assert backend["volumes"] == [
        "/opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro"]


def test_env_example_has_names_only():
    text = (COMPOSE / "backend.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert set(values) == {"DATABASE_URL", "BATCH_API_KEY_SHA256"}
    assert values["BATCH_API_KEY_SHA256"] == ""
    assert "<password>" in values["DATABASE_URL"] and "sslmode=verify-ca" in values["DATABASE_URL"]
