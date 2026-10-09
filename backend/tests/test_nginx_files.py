"""S1-06 (test-host part): static checks of the standalone nginx front door."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "deploy" / "nginx"
CONF = NGINX / "conf.d"


def _load(name: str) -> dict:
    return yaml.safe_load((NGINX / name).read_text(encoding="utf-8"))


def _locations(text: str) -> list[str]:
    return re.findall(r"^\s*location\s+([^{]+?)\s*\{", text, flags=re.MULTILINE)


def test_nginx_project_is_pinned_non_root_and_on_edge():
    base = _load("compose.yaml")
    assert base["name"] == "nginx"
    nginx = base["services"]["nginx"]
    assert nginx["image"] == "nginxinc/nginx-unprivileged:1.28.0-alpine"
    assert nginx["volumes"] == ["./conf.d:/etc/nginx/conf.d:ro"]
    assert nginx["networks"] == ["edge"]
    assert "/healthz" in " ".join(nginx["healthcheck"]["test"])
    assert "ports" not in nginx and "user" not in nginx
    assert base["networks"] == {"edge": {"external": True}}


def test_nginx_ports_per_host():
    assert _load("compose.local.yaml")["services"]["nginx"]["ports"] == ["127.0.0.1:8080:8080"]
    assert _load("compose.testhost.yaml")["services"]["nginx"]["ports"] == ["80:8080"]


def test_model_monitor_conf_allows_only_three_routes():
    text = (CONF / "model-monitor.conf").read_text(encoding="utf-8")
    assert _locations(text) == ["= /api/batch/runs", "= /api/health", "/otlp/", "/"]
    catch_all = text.split("location / {", 1)[1].split("}", 1)[0]
    assert "return 404;" in catch_all
    assert re.search(r"^\s*listen 8080;", text, flags=re.MULTILINE)
    assert "client_max_body_size 10m;" in text
    assert "rewrite ^/otlp/(.*)$ /$1 break;" in text


def test_model_monitor_conf_resolves_at_request_time():
    text = (CONF / "model-monitor.conf").read_text(encoding="utf-8")
    assert "set $mm_backend http://model-monitor-backend:8000;" in text
    assert "set $mm_collector http://model-monitor-collector:4319;" in text
    # every proxy_pass uses a variable, so nginx starts even when the app is down
    passes = re.findall(r"proxy_pass\s+([^;]+);", text)
    assert passes and all(p.startswith("$") for p in passes)
    common = (CONF / "00-common.conf").read_text(encoding="utf-8")
    assert "resolver 127.0.0.11" in common


def test_common_conf_hides_version_and_has_internal_health():
    text = (CONF / "00-common.conf").read_text(encoding="utf-8")
    assert "server_tokens off;" in text
    assert "listen 127.0.0.1:8081;" in text
    assert "location = /healthz" in text


def test_nginx_files_log_no_headers():
    for path in NGINX.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "log_format" not in text, path.name
            assert "local-dev-otlp-token-not-a-secret" not in text, path.name
            if path.suffix == ".conf":
                assert "authorization" not in text.lower(), path.name
            assert "\r\n" not in text, path.name
