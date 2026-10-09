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
    assert set(base) == {"backend", "collector", "collector-init", "trace-check"}
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


def test_collector_config_has_internal_and_token_receivers():
    text = (COMPOSE / "otel-collector.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    receivers = config["receivers"]
    assert receivers["otlp"]["protocols"] == {"http": {"endpoint": "0.0.0.0:4318"}}
    external = receivers["otlp/external"]["protocols"]["http"]
    assert external == {"endpoint": "0.0.0.0:4319",
                        "auth": {"authenticator": "bearertokenauth"}}
    assert config["extensions"]["bearertokenauth"] == {
        "scheme": "Bearer", "token": "${env:OTLP_TOKEN}"}
    assert config["service"]["extensions"] == ["health_check", "bearertokenauth"]
    assert config["exporters"]["file"]["path"] == "/data/spans.jsonl"
    traces = config["service"]["pipelines"]["traces"]
    assert traces == {"receivers": ["otlp", "otlp/external"], "processors": ["batch"],
                      "exporters": ["debug", "file"]}
    for word in ("password", "secret", "authorization", "local-dev-otlp-token"):
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
    assert "docker compose" in text and "/tmp/spans.jsonl" not in text
    # the span check is the S1-07 tool, not an inline copy
    # the full trace through nginx: all four trace check items (S1-06 + S1-05 + S1-07)
    assert 'check-trace.sh" "$TRACE_ID" --wait 30' in text
    assert "--backend-only" not in text
    assert "docker network create edge" in text and "docker network rm edge" in text
    assert "deploy/nginx/compose.yaml" in text and "deploy/nginx/compose.local.yaml" in text
    assert 'FRONT="http://127.0.0.1:8080"' in text
    for path in ("/api/live/portfolio", "/api/readiness", "/api/healthx", "/otlp/v1/traces"):
        assert path in text
    assert "Bearer wrong-token" in text and '"401"' in text and '"404"' in text
    assert '"$FRONT/api/batch/runs"' in text
    assert "batch.run" in text and "batch.send" in text
    assert " cp " not in text
    assert "SMOKE PASS" in text and "SMOKE FAIL" in text
    # the key and the token are sent only in headers, never echoed
    secret_lines = [line for line in text.splitlines()
                    if ("KEY" in line or "OTLP_TOKEN" in line) and "echo" in line]
    assert secret_lines == []
    assert "\r\n" not in text                       # LF line endings for bash


def test_ci_workflow_paths():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow[True]                       # PyYAML reads the key `on` as True
    paths = {"deploy/compose/**", "deploy/nginx/**", "backend/**", "scripts/compose-smoke.sh",
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
    assert set(host) == {"backend", "collector", "trace-check"}   # no database on the VM
    backend = host["backend"]
    assert backend["image"] == "${BACKEND_IMAGE:?BACKEND_IMAGE is not set}"
    assert "build" not in backend and "environment" not in backend
    assert backend["env_file"] == ["/opt/model-monitor/backend.env"]
    assert backend["ports"] == ["127.0.0.1:8000:8000"]   # for operators in the VM; jobs use nginx
    assert backend["volumes"] == [
        "/opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro"]


def test_env_example_has_names_only():
    text = (COMPOSE / "backend.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert set(values) == {"DATABASE_URL", "BATCH_API_KEY_SHA256"}
    assert values["BATCH_API_KEY_SHA256"] == ""
    assert "<password>" in values["DATABASE_URL"] and "sslmode=verify-ca" in values["DATABASE_URL"]


def test_trace_check_service_is_a_read_only_tool():
    base = _load("compose.yaml")["services"]["trace-check"]
    assert base["profiles"] == ["tools"]
    assert base["entrypoint"] == ["python", "scripts/check_trace.py"]
    assert base["volumes"] == ["collector-data:/otel:ro"]
    assert base["restart"] == "no"
    for key in ("ports", "depends_on", "environment", "build"):
        assert key not in base
    local = _load("compose.local.yaml")["services"]["trace-check"]
    assert local["image"] == "model-monitor-backend:local"
    assert local["environment"] == {
        "CHECK_DATABASE_URL": "postgresql://monitor:monitor@postgres:5432/monitor"}
    assert "DATABASE_URL" not in local["environment"]
    host = _load("compose.testhost.yaml")["services"]["trace-check"]
    assert host["image"] == "${BACKEND_IMAGE:?BACKEND_IMAGE is not set}"
    assert host["env_file"] == ["/opt/model-monitor/check.env"]
    assert host["volumes"] == [
        "/opt/model-monitor/cloudsql-server-ca.pem:/etc/model-monitor/cloudsql-server-ca.pem:ro"]
    assert "environment" not in host and "ports" not in host


def test_check_env_example_has_names_only():
    text = (COMPOSE / "check.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert set(values) == {"CHECK_DATABASE_URL"}
    url = values["CHECK_DATABASE_URL"]
    assert url.startswith("postgresql://monitor_readonly:<password>@")
    assert "sslmode=verify-ca" in url


def test_trace_check_shell_scripts():
    wrapper = (COMPOSE / "check-trace.sh").read_text(encoding="utf-8")
    setup = (COMPOSE / "make-check-env.sh").read_text(encoding="utf-8")
    for text in (wrapper, setup):
        assert text.startswith("#!/usr/bin/env bash\n")
        assert "set -euo pipefail" in text and "\r\n" not in text
    assert "/opt/model-monitor/check.env" in wrapper
    assert "compose.testhost.yaml" in wrapper and "compose.local.yaml" in wrapper
    assert "--profile tools run --rm -T --no-deps trace-check" in wrapper
    assert '"$@"' in wrapper
    assert "/opt/model-monitor/secrets/monitor-readonly.password" in setup
    assert "monitor_readonly" in setup and "10.188.112.8" in setup
    assert "umask 077" in setup and "chmod 600" in setup
    for line in setup.splitlines():
        if "echo" in line:
            assert "PW" not in line and "password)" not in line, line


def test_backend_and_collector_join_edge_with_aliases():
    base = _load("compose.yaml")
    services = base["services"]
    assert services["backend"]["networks"] == {
        "default": {}, "edge": {"aliases": ["model-monitor-backend"]}}
    assert services["collector"]["networks"] == {
        "default": {}, "edge": {"aliases": ["model-monitor-collector"]}}
    for name in ("collector-init", "trace-check"):
        assert "networks" not in services[name]
    assert base["networks"] == {"edge": {"external": True}}


def test_port_4319_is_never_published():
    for path in COMPOSE.glob("compose*.yaml"):
        services = yaml.safe_load(path.read_text(encoding="utf-8"))["services"]
        for service in services.values():
            assert not any("4319" in str(port) for port in service.get("ports", [])), path.name


def test_local_collector_uses_the_local_test_token():
    local = _load("compose.local.yaml")["services"]["collector"]
    assert local["environment"] == {"OTLP_TOKEN": "local-dev-otlp-token-not-a-secret"}


def test_testhost_collector_requires_the_env_file():
    host = _load("compose.testhost.yaml")["services"]["collector"]
    assert host["env_file"] == [{"path": "/opt/model-monitor/collector.env", "required": True}]
    assert "environment" not in host


def test_collector_env_example_has_names_only():
    text = (COMPOSE / "collector.env.example").read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
    assert values == {"OTLP_TOKEN": ""}


def test_make_collector_env_refuses_short_tokens():
    text = (COMPOSE / "make-collector-env.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "\r\n" not in text
    assert "umask 077" in text and "chmod 600" in text
    assert "/opt/model-monitor/collector.env" in text
    assert '${#TOKEN}' in text and "-lt 32" in text
    assert "printf 'OTLP_TOKEN=%s\\n'" in text
    for line in text.splitlines():
        if "echo" in line:
            assert "TOKEN" not in line.replace("OTLP_TOKEN", ""), line
