"""S2-03: static checks of the self-hosted Langfuse project (deploy/langfuse)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LANGFUSE = ROOT / "deploy" / "langfuse"
SERVICES = {"langfuse-web", "langfuse-worker", "postgres", "clickhouse", "redis", "minio"}
IMAGES = {
    "langfuse-web": "langfuse/langfuse:4.50.0",
    "langfuse-worker": "langfuse/langfuse-worker:4.50.0",
    "postgres": "postgres:17.11-bookworm",
    "clickhouse": "clickhouse/clickhouse-server:25.12.11.4",
    "redis": "redis:7.4.11",
    "minio": "cgr.dev/chainguard/minio@sha256:"
             "dc455cdd4db6e390b1b26514f15ff37681a777bf8dab41aac445a0259f751e56",
}


def _load(name: str) -> dict:
    return yaml.safe_load((LANGFUSE / name).read_text(encoding="utf-8"))


def _env_lines(name: str) -> dict[str, str]:
    text = (LANGFUSE / name).read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines()
                if line and not line.startswith("#"))


def test_images_are_pinned():
    base = _load("compose.yaml")
    assert base["name"] == "langfuse"
    assert set(base["services"]) == SERVICES
    for name, image in IMAGES.items():
        assert base["services"][name]["image"] == image, name


def test_no_published_port_and_only_web_on_edge():
    base = _load("compose.yaml")
    for name in ("compose.yaml", "compose.local.yaml", "compose.testhost.yaml"):
        for service in _load(name)["services"].values():
            assert "ports" not in service, name
    services = base["services"]
    assert services["langfuse-web"]["networks"] == {
        "default": {}, "edge": {"aliases": ["langfuse-web"]}}
    for name in SERVICES - {"langfuse-web"}:
        assert "edge" not in str(services[name].get("networks", "")), name
    assert base["networks"] == {"edge": {"external": True}}
    for service in services.values():
        assert service["restart"] == "unless-stopped"
        assert "healthcheck" in service


def test_base_settings_turn_off_signup_and_telemetry():
    services = _load("compose.yaml")["services"]
    for name in ("langfuse-web", "langfuse-worker"):
        env = services[name]["environment"]
        assert env["TELEMETRY_ENABLED"] == "false"
        assert env["HOSTNAME"] == "0.0.0.0"   # else it binds the container ID, not localhost
        assert env["AUTH_DISABLE_SIGNUP"] == "true"
        assert env["LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES"] == "false"
        assert env["LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT"] == "http://minio:9000"
        for dep in ("postgres", "clickhouse", "redis", "minio"):
            assert services[name]["depends_on"][dep] == {"condition": "service_healthy"}
    assert services["langfuse-web"]["environment"]["LANGFUSE_INIT_PROJECT_NAME"] == "model-monitor"
    assert "noeviction" in " ".join(services["redis"]["command"])
    for name in ("compose.yaml", "compose.local.yaml", "compose.testhost.yaml"):
        text = (LANGFUSE / name).read_text(encoding="utf-8")
        assert not re.search(r"(PASSWORD|SECRET|_KEY|_AUTH)\s*:\s*\S", text), name


def test_every_service_reads_the_host_env_file():
    local = _load("compose.local.yaml")["services"]
    host = _load("compose.testhost.yaml")["services"]
    assert set(local) == set(host) == SERVICES
    for name in SERVICES:
        assert local[name]["env_file"] == ["./local.env"]
        assert host[name]["env_file"] == [{"path": "/opt/langfuse/langfuse.env", "required": True}]


def test_local_env_is_marked_and_uses_password_login():
    text = (LANGFUSE / "local.env").read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("# Local test values, not secrets")
    env = _env_lines("local.env")
    assert env["AUTH_DISABLE_USERNAME_PASSWORD"] == "false"
    assert env["LANGFUSE_INIT_PROJECT_PUBLIC_KEY"] == "pk-lf-local-00000000-0000-0000-0000-000000000000"
    assert env["LANGFUSE_INIT_PROJECT_SECRET_KEY"] == "sk-lf-local-00000000-0000-0000-0000-000000000000"
    assert "AUTH_GOOGLE_CLIENT_ID" not in env
    assert len(env["ENCRYPTION_KEY"]) == 64


def test_examples_have_names_only():
    for name in ("langfuse.env.example", "google-oauth.env.example"):
        values = _env_lines(name)
        assert values and all(v == "" for v in values.values()), name
    assert set(_env_lines("google-oauth.env.example")) == {
        "AUTH_GOOGLE_CLIENT_ID", "AUTH_GOOGLE_CLIENT_SECRET"}


def test_make_langfuse_env_script():
    text = (LANGFUSE / "make-langfuse-env.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "\r\n" not in text
    assert "umask 077" in text and "chmod 600" in text
    assert "/opt/langfuse/langfuse.env" in text and "exists" in text   # refuses a second run
    assert "AUTH_DISABLE_USERNAME_PASSWORD" in text and '"true"' in text
    assert "LANGFUSE_OTLP_AUTH" in text and "CHECK_LANGFUSE_SECRET_KEY" in text
    assert "os.remove(google_file)" in text
    # the Google secret is read by Python from the file, never passed as an argument
    assert "GOOGLE_SECRET" not in text
    for line in text.splitlines():
        if line.lstrip().startswith("echo"):
            assert "$" not in line.replace('"$OUT"', "").replace("$0", ""), line


SMOKE = ROOT / "scripts" / "langfuse-smoke.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "langfuse-smoke.yml"


def test_langfuse_smoke_script():
    text = SMOKE.read_text(encoding="utf-8")
    assert 'export BACKEND_LANGFUSE_HOST="http://langfuse-web:3000"' in text
    assert "/api/public/v3/scores" in text and "name=grade" in text
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text and "trap cleanup EXIT" in text and "\r\n" not in text
    assert "deploy/langfuse/compose.yaml" in text and "deploy/langfuse/compose.local.yaml" in text
    assert "RESULT: OK (5 of 5 found)" in text
    # The plain compose smoke has no Langfuse; only this script turns the 5th item on.
    assert 'export CHECK_LANGFUSE_URL="http://langfuse-web:3000"' in text
    assert text.count("check-trace.sh") >= 2 and "restart" in text
    assert "http://127.0.0.1:3000/api/public/health" in text
    assert "down -v" in text and "docker network rm edge" in text
    for line in text.splitlines():
        if "echo" in line:
            assert "KEY" not in line and "OTLP_TOKEN" not in line, line


def test_langfuse_smoke_workflow():
    text = WORKFLOW.read_text(encoding="utf-8")
    for path in ("backend/app/batch_evaluator.py", "backend/app/adapters/langfuse_scores.py"):
        assert text.count(path) == 2
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    paths = {"deploy/langfuse/**", "deploy/nginx/**", "deploy/compose/otel-collector.yaml",
             "scripts/langfuse-smoke.sh", ".github/workflows/langfuse-smoke.yml",
             "backend/app/trace_check.py", "backend/scripts/check_trace.py",
             "backend/app/batch_evaluator.py", "backend/app/adapters/langfuse_scores.py",
             "backend/app/engines/batch_grading.py"}
    triggers = workflow[True]
    assert set(triggers["pull_request"]["paths"]) == paths
    assert set(triggers["push"]["paths"]) == paths and triggers["push"]["branches"] == ["dev"]
    job = workflow["jobs"]["langfuse-smoke"]
    assert job["runs-on"] == "ubuntu-latest" and job["timeout-minutes"] == 30
    assert workflow["permissions"] == {"contents": "read"}
    assert any(step.get("run") == "bash scripts/langfuse-smoke.sh" for step in job["steps"])
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")
