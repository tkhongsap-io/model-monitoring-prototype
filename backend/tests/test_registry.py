"""S2-01: the batch use-case registry (backend/registry/batch-use-cases.yaml)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app import registry

REAL = Path(__file__).resolve().parents[1] / "registry" / "batch-use-cases.yaml"

GOOD = """use_cases:
  - use_case_id: UC-A
    name: Use case A
    owner: team-a
    developer: dev-a
    mode: identity_only
    schedule: {expected_every_s: 86400, grace_s: 3600}
    turnaround_limit_s: null
    data_classification: internal
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "reg.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_path_is_the_real_file():
    # a fresh process: the autouse fixture sets the test registry in this process
    env = {k: v for k, v in os.environ.items() if k != "BATCH_REGISTRY_PATH"}
    out = subprocess.run(
        [sys.executable, "-c", "from app import config; print(config.BATCH_REGISTRY_PATH)"],
        cwd=REAL.parents[1], env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert Path(out.stdout.strip()) == REAL


def test_real_registry_loads_with_october_fields_only():
    reg = registry.load(REAL)
    assert list(reg) == ["rtr-fraud-validation"]
    rtr = reg["rtr-fraud-validation"]
    assert rtr.mode == "identity_only"
    assert rtr.schedule.expected_every_s > 0 and rtr.band_overrides == {}
    text = REAL.read_text(encoding="utf-8")
    for word in ("task_description", "profile", "sample_size"):
        assert word not in text
    assert re.search(r"[0-9a-f]{64}", text) is None        # never a key hash


def test_good_file_loads(tmp_path):
    reg = registry.load(write(tmp_path, GOOD))
    assert list(reg) == ["UC-A"] and reg["UC-A"].turnaround_limit_s is None


@pytest.mark.parametrize("change, words", [
    (lambda t: t + t.split("use_cases:\n", 1)[1], ["use case UC-A", "duplicate use_case_id"]),
    (lambda t: t.replace("UC-A", "UC A"), ["use case #1", "use_case_id"]),
    (lambda t: t + "    task_description: x\n", ["use case UC-A", "task_description"]),
    (lambda t: t.replace("identity_only", "other"), ["use case UC-A", "mode"]),
    (lambda t: t.replace("expected_every_s: 86400", "expected_every_s: 0"),
     ["use case UC-A", "schedule.expected_every_s"]),
    (lambda t: t.replace("grace_s: 3600", "grace_s: -1"), ["schedule.grace_s"]),
    (lambda t: t.replace("turnaround_limit_s: null", "turnaround_limit_s: 0"),
     ["turnaround_limit_s"]),
    (lambda t: t.replace("    turnaround_limit_s: null\n", ""), ["turnaround_limit_s"]),
])
def test_bad_registry_messages(tmp_path, change, words):
    path = write(tmp_path, change(GOOD))
    with pytest.raises(registry.RegistryError) as exc:
        registry.load(path)
    message = str(exc.value)
    assert message.startswith(f"batch registry {path}: ")
    for word in words:
        assert word in message, message


@pytest.mark.parametrize("text, words", [
    ("", ["the file is empty"]),
    ("use_cases: []\n", ["use_cases"]),
    ("use_cases: [\n", ["not valid YAML"]),
])
def test_bad_file_level_messages(tmp_path, text, words):
    with pytest.raises(registry.RegistryError) as exc:
        registry.load(write(tmp_path, text))
    for word in words:
        assert word in str(exc.value)


def test_missing_file(tmp_path):
    with pytest.raises(registry.RegistryError) as exc:
        registry.load(tmp_path / "absent.yaml")
    assert "cannot be read" in str(exc.value)


def test_unregistered_is_sorted_and_unique(tmp_path):
    reg = registry.load(write(tmp_path, GOOD))
    assert registry.unregistered(["UC-Z", "UC-A", "UC-B", "UC-Z"], reg) == ["UC-B", "UC-Z"]


def test_current_after_set_current(tmp_path):
    reg = registry.load(write(tmp_path, GOOD))
    registry.set_current(reg)
    assert registry.current() is reg


def test_band_overrides_stop_the_load(tmp_path):
    text = GOOD + "    band_overrides: {failure_rate: {red: 0.1}}\n"
    with pytest.raises(registry.RegistryError) as exc:
        registry.load(write(tmp_path, text))
    assert "use case UC-A: band_overrides is not supported yet (S2-05)" in str(exc.value)
