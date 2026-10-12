"""S2-01: scripts/batch_keys.py manages key entries without showing a key or a full hash."""
from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

from app import config

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "batch_keys.py"
A = "a" * 64
B = "b" * 64


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, timeout=60)


def env_file(tmp_path: Path, value: str | None = f"GCP-UC-03:{A}") -> Path:
    lines = ["# monitor backend settings", "DATABASE_URL=postgresql://u:p@h:5432/monitor"]
    if value is not None:
        lines.append(f"BATCH_API_KEY_SHA256={value}")
    path = tmp_path / "backend.env"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def key_value(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("BATCH_API_KEY_SHA256="):
            return line.split("=", 1)[1]
    raise AssertionError("no BATCH_API_KEY_SHA256 line")


def test_make_writes_two_private_files_and_prints_no_value(tmp_path):
    key_out, hash_out = tmp_path / "key.tmp", tmp_path / "hash.tmp"
    result = run("make", "--use-case", "rtr-fraud-validation",
                 "--key-out", str(key_out), "--hash-out", str(hash_out))
    assert result.returncode == 0, result.stderr
    key = key_out.read_text(encoding="utf-8")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    assert hash_out.read_text(encoding="utf-8").strip() == f"rtr-fraud-validation:{digest}"
    assert len(key) >= 40 and "\n" not in key
    output = result.stdout + result.stderr
    assert key not in output and digest not in output and digest[:9] not in output
    if os.name == "posix":
        for path in (key_out, hash_out):
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_make_refuses_existing_file_and_bad_id(tmp_path):
    key_out, hash_out = tmp_path / "key.tmp", tmp_path / "hash.tmp"
    key_out.write_text("old", encoding="utf-8")
    assert run("make", "--use-case", "UC-1", "--key-out", str(key_out),
               "--hash-out", str(hash_out)).returncode == 1
    assert key_out.read_text(encoding="utf-8") == "old" and not hash_out.exists()
    same = tmp_path / "same.tmp"
    assert run("make", "--use-case", "UC-1", "--key-out", str(same),
               "--hash-out", str(same)).returncode == 1
    assert not same.exists()
    assert run("make", "--use-case", "bad id", "--key-out", str(tmp_path / "k2"),
               "--hash-out", str(tmp_path / "h2")).returncode == 2


def test_add_keeps_other_lines_and_refuses_duplicates(tmp_path, monkeypatch):
    env = env_file(tmp_path)
    hash_file = tmp_path / "hash.tmp"
    hash_file.write_text(f"rtr-fraud-validation:{B}\n", encoding="utf-8")
    result = run("add", "--env-file", str(env), "--hash-file", str(hash_file))
    assert result.returncode == 0, result.stderr
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# monitor backend settings"
    assert lines[1] == "DATABASE_URL=postgresql://u:p@h:5432/monitor"
    assert key_value(env) == f"GCP-UC-03:{A}, rtr-fraud-validation:{B}"
    assert not hash_file.exists()
    assert B not in result.stdout + result.stderr
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", key_value(env))
    assert config.batch_api_key_hashes() == [(A, "GCP-UC-03"), (B, "rtr-fraud-validation")]
    hash_file.write_text(f"rtr-fraud-validation:{B}\n", encoding="utf-8")
    before = env.read_text(encoding="utf-8")
    assert run("add", "--env-file", str(env), "--hash-file", str(hash_file)).returncode == 1
    assert env.read_text(encoding="utf-8") == before


def test_add_creates_the_line_when_absent_and_refuses_a_bad_hash_file(tmp_path):
    env = env_file(tmp_path, value=None)
    hash_file = tmp_path / "hash.tmp"
    hash_file.write_text(f"GCP-UC-07:{B}", encoding="utf-8")
    assert run("add", "--env-file", str(env), "--hash-file", str(hash_file)).returncode == 0
    assert key_value(env) == f"GCP-UC-07:{B}"
    bad = tmp_path / "bad.tmp"
    bad.write_text("GCP-UC-07:not-a-hash", encoding="utf-8")
    assert run("add", "--env-file", str(env), "--hash-file", str(bad)).returncode == 1


def test_list_prints_only_prefixes(tmp_path):
    env = env_file(tmp_path, value=f"GCP-UC-03:{A}, rtr-fraud-validation:{B}, broken")
    result = run("list", "--env-file", str(env))
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "GCP-UC-03 aaaaaaaa", "rtr-fraud-validation bbbbbbbb", "#3 malformed"]


def test_remove_refuses_ambiguous_or_short_prefixes(tmp_path):
    almost = "a" * 63 + "b"
    env = env_file(tmp_path, value=f"GCP-UC-03:{A}, GCP-UC-03:{almost}, GCP-UC-07:{B}")
    assert run("remove", "--env-file", str(env), "--use-case", "GCP-UC-03",
               "--hash-prefix", "aaaaaaaa").returncode == 1                # matches 2
    assert run("remove", "--env-file", str(env), "--use-case", "GCP-UC-03",
               "--hash-prefix", "aaaa").returncode == 2                    # too short
    assert run("remove", "--env-file", str(env), "--use-case", "GCP-UC-03",
               "--hash-prefix", "ffffffff").returncode == 1                # matches 0
    assert run("remove", "--env-file", str(env), "--use-case", "GCP-UC-07",
               "--hash-prefix", "aaaaaaaa").returncode == 1                # other use case
    result = run("remove", "--env-file", str(env), "--use-case", "GCP-UC-03",
                 "--hash-prefix", A)
    assert result.returncode == 0, result.stderr
    assert key_value(env) == f"GCP-UC-03:{almost}, GCP-UC-07:{B}"
    assert A not in result.stdout + result.stderr
