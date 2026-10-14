"""Dashboard image (S2-07): pinned stages, frozen install, dashboard file server."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "deploy" / "dashboard"


def test_dockerfile_two_pinned_stages():
    text = (DASH / "Dockerfile").read_text(encoding="utf-8")
    assert "\r\n" not in text
    froms = re.findall(r"^FROM\s+(\S+)(?:\s+AS\s+(\w+))?", text, flags=re.MULTILINE)
    assert froms == [("node:24.21.0-bookworm-slim", "build"),
                     ("nginxinc/nginx-unprivileged:1.28.0-alpine", "")]
    assert "pnpm@10.15.1" in text and "--frozen-lockfile" in text
    assert "run build:live" in text and "run check:strict-live" in text
    assert "COPY --from=build /app/artifacts/control-tower/dist/public /usr/share/nginx/html" in text
    assert "COPY deploy/dashboard/file-server.conf /etc/nginx/conf.d/default.conf" in text
    assert "EXPOSE 8090" in text
    assert "USER root" not in text


def test_file_server_conf():
    text = (DASH / "file-server.conf").read_text(encoding="utf-8")
    assert "\r\n" not in text
    assert re.search(r"^\s*listen 8090;", text, flags=re.MULTILINE)
    assert "server_tokens off;" in text
    assert "try_files $uri $uri/ /index.html;" in text            # SPA fallback
    assert re.search(r"location /assets/ \{[^}]*try_files \$uri =404;", text, flags=re.S)
    assert "max-age=31536000, immutable" in text
    assert re.search(r'location = /index.html \{[^}]*no-cache', text, flags=re.S)
    assert re.search(r"location = /healthz \{[^}]*return 200", text, flags=re.S)
    assert "proxy_pass" not in text                               # file server only


def test_dockerignore_keeps_secrets_and_bulk_out():
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for entry in ("**/node_modules", ".git", "**/.env", "**/.env.*", "backend",
                  "**/dist", ".claude"):
        assert entry in lines, entry
