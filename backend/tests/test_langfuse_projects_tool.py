"""Project tool (S2-03b): add, regenerate, list, routes."""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))
import langfuse_projects as tool  # noqa: E402

REGISTRY = BACKEND / "tests" / "fixtures" / "batch-use-cases.test.yaml"   # GCP-UC-03, GCP-UC-07


def fake_fetch(name: str, status: int = 200):
    calls = []

    def fetch(url, auth):
        calls.append((url, auth))
        return status, json.dumps({"data": [{"id": "p1", "name": name}]}).encode()
    fetch.calls = calls
    return fetch


def args(tmp_path, *rest):
    return ["--projects-dir", str(tmp_path / "projects"), "--generated-dir",
            str(tmp_path / "generated"), "--registry", str(REGISTRY),
            "--langfuse-url", "http://lf.test", *rest]


def keys_file(tmp_path, pk="pk-lf-aaaa1111", sk="sk-lf-bbbb2222") -> Path:
    path = tmp_path / "projects" / ".incoming.keys"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"LANGFUSE_PUBLIC_KEY={pk}\nLANGFUSE_SECRET_KEY={sk}\n", encoding="utf-8")
    return path


def add_unrouted(tmp_path):
    env = tmp_path / "langfuse.env"
    env.write_text("LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-unr\n"
                   "LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-unr\nOTHER=x\n", encoding="utf-8")
    assert tool.main(args(tmp_path, "add", "unrouted", "--from-langfuse-env", str(env)),
                     fetch=fake_fetch("unrouted")) == 0


def test_add_unrouted_then_use_case(tmp_path, capsys):
    add_unrouted(tmp_path)
    keys = keys_file(tmp_path)
    fetch = fake_fetch("GCP-UC-03")
    assert tool.main(args(tmp_path, "add", "GCP-UC-03", "--keys-file", str(keys)),
                     fetch=fetch) == 0
    assert fetch.calls[0][0] == "http://lf.test/api/public/projects"
    assert not keys.exists()                                         # deleted after use
    saved = yaml.safe_load((tmp_path / "projects" / "GCP-UC-03.yaml").read_text())
    assert saved["public_key"] == "pk-lf-aaaa1111" and saved["use_case_id"] == "GCP-UC-03"
    env = (tmp_path / "generated" / "projects.env").read_text()
    assert "LANGFUSE_PROJECTS=unrouted,GCP-UC-03" in env
    routes = yaml.safe_load((tmp_path / "generated" / "routes.yaml").read_text())
    assert "otlphttp/langfuse-GCP-UC-03" in routes["exporters"]
    out = capsys.readouterr()
    assert "sk-lf-bbbb2222" not in out.out + out.err and "pk-lf-aaaa1111" not in out.out + out.err
    if os.name != "nt":
        assert stat.S_IMODE((tmp_path / "projects" / "GCP-UC-03.yaml").stat().st_mode) == 0o600
        assert stat.S_IMODE((tmp_path / "generated" / "projects.env").stat().st_mode) == 0o600
        assert stat.S_IMODE((tmp_path / "generated" / "routes.yaml").stat().st_mode) == 0o644


def test_keys_of_another_project_are_refused(tmp_path, capsys):
    add_unrouted(tmp_path)
    keys = keys_file(tmp_path)
    assert tool.main(args(tmp_path, "add", "GCP-UC-03", "--keys-file", str(keys)),
                     fetch=fake_fetch("GCP-UC-07")) == 1
    assert not (tmp_path / "projects" / "GCP-UC-03.yaml").exists()
    assert not keys.exists()
    err = capsys.readouterr().err
    assert "GCP-UC-07" in err and "sk-lf-bbbb2222" not in err


def test_langfuse_refusal_is_one_safe_line(tmp_path, capsys):
    add_unrouted(tmp_path)
    keys = keys_file(tmp_path)
    assert tool.main(args(tmp_path, "add", "GCP-UC-03", "--keys-file", str(keys)),
                     fetch=fake_fetch("GCP-UC-03", status=401)) == 1
    assert "Langfuse answered 401" in capsys.readouterr().err


def test_unregistered_use_case_is_refused(tmp_path):
    add_unrouted(tmp_path)
    keys = keys_file(tmp_path)
    assert tool.main(args(tmp_path, "add", "nope", "--keys-file", str(keys)),
                     fetch=fake_fetch("nope")) == 1


def test_regenerate_refuses_a_bad_file_and_keeps_old_output(tmp_path, capsys):
    add_unrouted(tmp_path)
    before = (tmp_path / "generated" / "routes.yaml").read_text()
    (tmp_path / "projects" / "GCP-UC-07.yaml").write_text("use_case_id: GCP-UC-07\n")
    assert tool.main(args(tmp_path, "regenerate")) == 1
    assert (tmp_path / "generated" / "routes.yaml").read_text() == before
    assert "GCP-UC-07.yaml" in capsys.readouterr().err


def test_list_shows_no_full_key(tmp_path, capsys):
    add_unrouted(tmp_path)
    assert tool.main(args(tmp_path, "list")) == 0
    out = capsys.readouterr().out
    assert "unrouted" in out and "pk-lf-un" in out and "pk-lf-unr" not in out.replace(
        "pk-lf-un…", "") and "sk-lf" not in out


def test_routes_command_needs_no_keys(tmp_path):
    (tmp_path / "projects").mkdir()
    out = tmp_path / "routes.yaml"
    assert tool.main(args(tmp_path, "routes", "--use-cases", "unrouted,GCP-UC-03",
                          "--exporter", "file", "--file-dir", "/out",
                          "--output", str(out))) == 0
    doc = yaml.safe_load(out.read_text())
    assert doc["exporters"]["file/langfuse-GCP-UC-03"] == {"path": "/out/GCP-UC-03.jsonl"}


def test_usage_errors_exit_2(tmp_path):
    assert tool.main(args(tmp_path, "add", "GCP-UC-03")) == 2
