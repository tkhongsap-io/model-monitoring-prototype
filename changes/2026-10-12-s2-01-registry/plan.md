# Batch use-case registry (S2-01) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reviewed YAML registry of the batch use cases that the backend loads at start (and refuses to start without), a `403` for a key of an unregistered use case, a readiness error for such a key entry, and `scripts/batch_keys.py` to make, add, list and remove key entries without showing a key or a full hash.

**Architecture:** `backend/app/registry.py` (Pydantic models, loader, the current registry) reads `backend/registry/batch-use-cases.yaml`. `main.lifespan` loads it before the database. `batch_routes` and `ops_routes` read `registry.current()`. The key hashes stay in `BATCH_API_KEY_SHA256`; `backend/scripts/batch_keys.py` (standard library only) edits the host env file.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyYAML (installed), pytest.

**Spec:** [spec.md](spec.md) (approved 2026-10-12). Intent: [intent.md](intent.md).

## Global Constraints

- No new package. No database migration. No new route.
- The key hashes stay in `BATCH_API_KEY_SHA256`. Never put a key or a key hash in the registry, a test log, or any output; `batch_keys.py` prints at most 8 hash characters.
- Registry file: `backend/registry/batch-use-cases.yaml`; setting `BATCH_REGISTRY_PATH` (default that absolute path).
- October fields only: `use_case_id`, `name`, `owner`, `developer`, `mode` (`identity_only` | `records`), `schedule` (`expected_every_s` > 0, `grace_s` >= 0), `turnaround_limit_s` (null or > 0, required key), `data_classification` (`public` | `internal` | `confidential` | `restricted`), `band_overrides` (default `{}`). Unknown fields are errors.
- The backend does not start with a bad registry (`RegistryError` is not caught).
- A key for an unregistered use case: `403`, `{"detail": "the use case of this API key is not registered"}`, before the body is read.
- `batch_keys.py`: standard library only; exit `0` success, `1` refused, `2` usage error.
- The local stack and the smoke test map the local test key to `rtr-fraud-validation`.
- Tests run from `backend/`: `.venv\Scripts\python.exe -m pytest ...` (Windows). If pytest cannot open its temp or cache folder in the sandbox, add `-p no:cacheprovider --basetemp=.pytest-tmp` and delete `backend/.pytest-tmp` afterwards.
- Docker and bash are not available on the Windows computer: never claim the stack or the smoke test ran.
- **Codex: do not run `git commit` or `git add`.** Leave changes in the working tree; Claude reviews and commits each task.

## Review Focus

- A registry error must name the use case and the field, so a person can fix it from the log line alone. (Task 1: `test_bad_registry_messages`.)
- A key entry whose use case is not registered must show in readiness before a job sends, without showing the hash. (Task 2: `test_readiness_reports_unregistered_key_use_case`.)
- `batch_keys.py add` must keep every other line of `backend.env`, also comments and `DATABASE_URL`, or the backend loses its database. (Task 3: `test_add_keeps_other_lines_and_refuses_duplicates`.)
- `batch_keys.py remove` with a short or shared prefix must not remove the wrong key. (Task 3: `test_remove_refuses_ambiguous_or_short_prefixes`.)
- A key rotation must not change stored runs. (Task 2: `test_rotation_old_key_removed_new_key_works`.)

---

## File structure

| File | Task | Responsibility |
|---|---|---|
| `backend/registry/batch-use-cases.yaml` | 1 | The registry |
| `backend/app/registry.py` | 1 | Models, loader, current registry |
| `backend/app/config.py` | 1 | `BATCH_REGISTRY_PATH` |
| `backend/tests/fixtures/batch-use-cases.test.yaml`, `backend/tests/conftest.py` | 1 | Test registry for all tests |
| `backend/tests/test_registry.py` | 1 | Loader tests |
| `backend/app/main.py`, `backend/app/api/batch_routes.py`, `backend/app/api/ops_routes.py` | 2 | Start, `403`, readiness |
| `backend/tests/test_batch_runs_api.py`, `backend/tests/test_app_surface.py` | 2 | API and readiness tests |
| `backend/scripts/batch_keys.py`, `backend/tests/test_batch_keys.py` | 3 | Key tool |
| `deploy/compose/compose.local.yaml`, `scripts/compose-smoke.sh`, `backend/tests/test_compose_files.py` | 4 | Local key mapping |
| `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `docs/STRICT-LIVE.md`, `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md` | 5 | Docs |

---

### Task 1: the registry and its loader

**Files:**
- Create: `backend/registry/batch-use-cases.yaml`, `backend/app/registry.py`, `backend/tests/fixtures/batch-use-cases.test.yaml`, `backend/tests/test_registry.py`
- Modify: `backend/app/config.py` (after `BATCH_MAX_BODY_BYTES`), `backend/tests/conftest.py`

**Interfaces:**
- Produces: `registry.UseCase`, `registry.Schedule`, `registry.RegistryError`, `registry.load(path) -> dict[str, UseCase]`, `registry.current() -> dict[str, UseCase]`, `registry.set_current(dict[str, UseCase]) -> None`, `registry.unregistered(ids: Iterable[str], reg: dict[str, UseCase]) -> list[str]`; `config.BATCH_REGISTRY_PATH: str`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_registry.py`:

```python
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
    (lambda t: t.replace("UC-A", "UC A"), ["use_case_id"]),
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
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_registry.py -q`
Expected: FAIL (`ImportError: cannot import name 'registry'`)

- [ ] **Step 3: Implement**

`backend/registry/batch-use-cases.yaml`:

```yaml
# Batch use cases of the October MVP (S2-01). A change is a pull request, approved by
# backend; RAI also approves band_overrides. Never put an API key or a key hash here:
# the hashes are in BATCH_API_KEY_SHA256 of the host env file (scripts/batch_keys.py).
# turnaround_limit_s: null means no limit is set yet (turnaround_s is Unknown, not_reported).
use_cases:
  - use_case_id: rtr-fraud-validation
    name: RTR fraud validation
    owner: RTR fraud team
    developer: Prakasit Issanapong
    mode: identity_only
    schedule:
      expected_every_s: 86400
      grace_s: 21600
    turnaround_limit_s: null
    data_classification: confidential
    band_overrides: {}
```

`backend/app/registry.py`:

```python
"""Batch use-case registry (S2-01): the reviewed settings of each GCP batch use case.

The file is `backend/registry/batch-use-cases.yaml` (setting `BATCH_REGISTRY_PATH`). The
backend loads it at start and does not start when it has an error. The API key hashes are
not here: they stay in `BATCH_API_KEY_SHA256` of the host env file (scripts/batch_keys.py).
October fields only (identity-only MVP); the task description, the profile and the sample
size come back with SEND_RECORDS, so they are unknown fields until then.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Iterable, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .batch_schema import Identifier


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Schedule(_Strict):
    expected_every_s: int = Field(gt=0)
    grace_s: int = Field(ge=0)


class UseCase(_Strict):
    use_case_id: Identifier
    name: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=128)
    developer: str = Field(min_length=1, max_length=128)
    mode: Literal["identity_only", "records"]
    schedule: Schedule
    turnaround_limit_s: Annotated[int, Field(gt=0)] | None
    data_classification: Literal["public", "internal", "confidential", "restricted"]
    band_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)


class _File(_Strict):
    use_cases: list[UseCase] = Field(min_length=1)


class RegistryError(Exception):
    """A registry problem. The message names the file, the use case and the field."""


_current: dict[str, UseCase] | None = None


def _who(cases: Any, index: int) -> str:
    entry = cases[index] if isinstance(cases, list) and 0 <= index < len(cases) else None
    use_case_id = entry.get("use_case_id") if isinstance(entry, dict) else None
    if isinstance(use_case_id, str) and use_case_id:
        return f"use case {use_case_id}"
    return f"use case #{index + 1}"


def _messages(path: Path, raw: Any, exc: ValidationError) -> list[str]:
    cases = raw.get("use_cases") if isinstance(raw, dict) else None
    lines = []
    for error in exc.errors():
        loc = list(error["loc"])
        if len(loc) >= 2 and loc[0] == "use_cases" and isinstance(loc[1], int):
            who, rest = _who(cases, loc[1]), loc[2:]
        else:
            who, rest = "file", loc
        field = ".".join(str(part) for part in rest) or "(entry)"
        lines.append(f"batch registry {path}: {who}: {field}: {error['msg']}")
    return lines


def load(path: str | Path) -> dict[str, UseCase]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        raise RegistryError(f"batch registry {path}: the file cannot be read") from None
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RegistryError(
            f"batch registry {path}: not valid YAML ({type(exc).__name__})") from None
    if raw is None:
        raise RegistryError(f"batch registry {path}: the file is empty")
    try:
        parsed = _File.model_validate(raw)
    except ValidationError as exc:
        raise RegistryError("\n".join(_messages(path, raw, exc))) from None
    out: dict[str, UseCase] = {}
    for use_case in parsed.use_cases:
        if use_case.use_case_id in out:
            raise RegistryError(
                f"batch registry {path}: use case {use_case.use_case_id}: duplicate use_case_id")
        out[use_case.use_case_id] = use_case
    return out


def set_current(reg: dict[str, UseCase]) -> None:
    global _current
    _current = reg


def current() -> dict[str, UseCase]:
    if _current is None:
        raise RegistryError("batch registry is not loaded")
    return _current


def unregistered(use_case_ids: Iterable[str], reg: dict[str, UseCase]) -> list[str]:
    return sorted({use_case_id for use_case_id in use_case_ids if use_case_id not in reg})
```

`backend/app/config.py`: in the comment above `BATCH_API_KEY_SHA256`, replace the sentence "The source registry (S2-01) replaces this setting." with "The source registry (S2-01) lists the use cases; the hashes stay here (scripts/batch_keys.py)." After the `BATCH_MAX_BODY_BYTES` line add:

```python
# Batch use-case registry (S2-01): a reviewed YAML file in the image. The backend does not
# start when the file has an error.
BATCH_REGISTRY_PATH = (os.getenv("BATCH_REGISTRY_PATH", "").strip()
                       or str(BACKEND_DIR / "registry" / "batch-use-cases.yaml"))
```

`backend/tests/fixtures/batch-use-cases.test.yaml`:

```yaml
# Test registry (S2-01): the use cases of the S1-01 example bodies. Tests only.
use_cases:
  - use_case_id: GCP-UC-03
    name: Invoice summary (test)
    owner: test-team
    developer: test-developer
    mode: records
    schedule: {expected_every_s: 86400, grace_s: 21600}
    turnaround_limit_s: 3600
    data_classification: internal
  - use_case_id: GCP-UC-07
    name: Second use case (test)
    owner: test-team
    developer: test-developer
    mode: identity_only
    schedule: {expected_every_s: 86400, grace_s: 21600}
    turnaround_limit_s: null
    data_classification: internal
```

`backend/tests/conftest.py`: add `from pathlib import Path` to the imports, add `registry` to `from app import config, db`, and add after `LABEL_LAG = 3`:

```python
TEST_REGISTRY = Path(__file__).resolve().parent / "fixtures" / "batch-use-cases.test.yaml"


@pytest.fixture(autouse=True)
def batch_registry(monkeypatch):
    """Every test uses the test registry (S2-01), also routes called without the lifespan."""
    monkeypatch.setattr(config, "BATCH_REGISTRY_PATH", str(TEST_REGISTRY))
    registry.set_current(registry.load(TEST_REGISTRY))
    yield
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_registry.py -q`, then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: PASS (the fast suite does not change yet)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-01): batch use-case registry and loader`)

---

### Task 2: start, the `403` and readiness

**Files:**
- Modify: `backend/app/main.py`, `backend/app/api/batch_routes.py`, `backend/app/api/ops_routes.py`
- Test: `backend/tests/test_batch_runs_api.py`, `backend/tests/test_app_surface.py`

**Interfaces:**
- Consumes: Task 1 `registry.load`, `registry.set_current`, `registry.current`, `registry.unregistered`, `registry.RegistryError`, `config.BATCH_REGISTRY_PATH`.
- Produces: readiness body field `use_cases: int`; span outcome `unregistered`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_batch_runs_api.py`:

```python
KEY_99 = "test-key-uc99-" + "c" * 32


def test_key_of_unregistered_use_case_403_nothing_stored(client, monkeypatch):
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", f"GCP-UC-99:{sha(KEY_99)}")
    body = example("01-completed-online.json")
    body["use_case_id"] = "GCP-UC-99"
    response = client.post(URL, json=body, headers={"Authorization": f"Bearer {KEY_99}"})
    assert response.status_code == 403
    assert response.json() == {"detail": "the use case of this API key is not registered"}
    assert rows() == []


def test_unregistered_check_comes_before_the_body(client, monkeypatch):
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", f"GCP-UC-99:{sha(KEY_99)}")
    response = client.post(URL, content=b"not json",
                           headers={"Authorization": f"Bearer {KEY_99}"})
    assert response.status_code == 403


def test_rotation_old_key_removed_new_key_works(client, monkeypatch):
    new_key = "test-key-uc03-new-" + "d" * 32
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256",
                        f"GCP-UC-03:{sha(KEY_03)}, GCP-UC-03:{sha(new_key)}")
    first = example("01-completed-online.json")
    second = {**first, "run_id": "rotation-second-run"}
    assert client.post(URL, json=first, headers=AUTH).status_code == 201
    assert client.post(URL, json=second,
                       headers={"Authorization": f"Bearer {new_key}"}).status_code == 201
    before = rows()
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", f"GCP-UC-03:{sha(new_key)}")
    assert client.post(URL, json=first, headers=AUTH).status_code == 401     # removed key
    assert client.post(URL, json=first,
                       headers={"Authorization": f"Bearer {new_key}"}).status_code == 200
    assert rows() == before                                                  # runs unchanged
```

In `backend/tests/test_app_surface.py`: add `from app import registry` to the imports (keep the existing import line and add `registry` to it), change the expected body of `test_readiness_ready` to

```python
    assert response.json() == {"status": "ready", "database": {"ok": True, "error": None},
                               "batch_api_keys": 1, "use_cases": 2, "errors": []}
```

and append:

```python
def test_readiness_reports_unregistered_key_use_case(ready_config, monkeypatch):
    other = hashlib.sha256(b"key of an unregistered use case").hexdigest()
    monkeypatch.setattr(config, "BATCH_API_KEY_SHA256", f"{GOOD_ENTRY}, GCP-UC-99:{other}")
    with TestClient(main.app) as client:
        response = client.get("/api/readiness")
    assert response.status_code == 503
    assert ("BATCH_API_KEY_SHA256 has entries for use cases that are not in the registry: "
            "GCP-UC-99") in response.json()["errors"]
    assert other not in response.text


def test_backend_does_not_start_with_a_bad_registry(isolated_db, monkeypatch, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("use_cases: []\n", encoding="utf-8")
    monkeypatch.setattr(config, "BATCH_REGISTRY_PATH", str(bad))
    with pytest.raises(registry.RegistryError):
        with TestClient(main.app):
            pass
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_runs_api.py tests/test_app_surface.py -q`
Expected: FAIL (the new tests; `use_cases` missing in readiness)

- [ ] **Step 3: Implement**

`backend/app/main.py`: change the import line to `from . import config, db, logging_setup, registry, tracing`; in the module docstring replace the last sentence with "Startup loads the batch use-case registry (S2-01; a bad registry stops the start) and runs the ordered migrations (`db.engine()`); shutdown sends the remaining spans."; and in `lifespan` replace `db.engine()` with:

```python
    registry.set_current(registry.load(config.BATCH_REGISTRY_PATH))   # error: no start
    db.engine()
```

`backend/app/api/batch_routes.py`: change the import line to `from .. import config, db, registry, tracing`, and in `_ingest`, directly after the `if key_use_case is None:` block (the `401` return), add:

```python
    if key_use_case not in registry.current():
        span.set_attribute("outcome", "unregistered")
        log.warning("batch run rejected: the use case of the API key is not registered",
                    extra={"outcome": "unregistered", "key_use_case_id": key_use_case})
        return JSONResponse({"detail": "the use case of this API key is not registered"},
                            status_code=403)
```

`backend/app/api/ops_routes.py`: change the import line to `from .. import config, db, registry`, and in `readiness` replace the lines from `errors = config.batch_configuration_errors()` to the `body = ...` assignment with:

```python
    errors = config.batch_configuration_errors()
    use_cases = registry.current()
    missing = registry.unregistered(
        (use_case_id for _, use_case_id in config.batch_api_key_hashes()), use_cases)
    if missing:
        errors.append("BATCH_API_KEY_SHA256 has entries for use cases that are not in the "
                      f"registry: {', '.join(missing)}")
    if not database["ok"]:
        errors.append("database is not reachable")
    body = {"status": "ready" if not errors else "not_ready", "database": database,
            "batch_api_keys": len(config.batch_api_key_hashes()),
            "use_cases": len(use_cases), "errors": errors}
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_runs_api.py tests/test_app_surface.py tests/test_registry.py -q`, then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`
Expected: PASS. If another existing test compares the readiness body exactly, add `"use_cases": 2` to its expected value and list it under Deviations.

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-01): refuse keys of unregistered use cases; registry at start and in readiness`)

---

### Task 3: `scripts/batch_keys.py`

**Files:**
- Create: `backend/scripts/batch_keys.py`, `backend/tests/test_batch_keys.py`

**Interfaces:**
- Produces: the command line `batch_keys.py make|add|list|remove` (spec, section "`scripts/batch_keys.py`").

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_batch_keys.py`:

```python
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
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_keys.py -q`
Expected: FAIL (the script does not exist: return code 2 from Python, file not found)

- [ ] **Step 3: Implement** — `backend/scripts/batch_keys.py`:

```python
#!/usr/bin/env python3
"""S2-01: manage the API key entries of the batch jobs (BATCH_API_KEY_SHA256).

    batch_keys.py make   --use-case ID --key-out KEY_FILE --hash-out HASH_FILE   (laptop)
    batch_keys.py add    --env-file ENV --hash-file HASH_FILE                    (VM, sudo)
    batch_keys.py list   --env-file ENV
    batch_keys.py remove --env-file ENV --use-case ID --hash-prefix PREFIX

The key goes only to KEY_FILE (then to GCP Secret Manager); the monitor keeps only its
SHA-256. No output contains a key or more than 8 characters of a hash. Standard library
only, so it runs on the laptop and on the VM host. Restart the backend after add/remove.
Exit 0: done; 1: refused; 2: usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
PREFIX = re.compile(r"^[0-9a-f]{8,64}$")
NAME = "BATCH_API_KEY_SHA256"


class Refused(Exception):
    """A refused action: the message is safe to print."""


def _private_write(path: Path, text: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _entries(value: str) -> list[str]:
    return [entry.strip() for entry in value.split(",") if entry.strip()]


def _parse(entry: str) -> tuple[str, str] | None:
    use_case_id, _, digest = entry.rpartition(":")
    use_case_id, digest = use_case_id.strip(), digest.strip().lower()
    if ID.match(use_case_id) and DIGEST.match(digest):
        return use_case_id, digest
    return None


def _read_env(path: Path) -> tuple[list[str], int | None]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise Refused(f"cannot read {path}") from None
    index = next((i for i, line in enumerate(lines) if line.startswith(f"{NAME}=")), None)
    return lines, index


def _write_env(path: Path, lines: list[str]) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".batch_keys-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def make(args: argparse.Namespace) -> None:
    key_out, hash_out = Path(args.key_out), Path(args.hash_out)
    for path in (key_out, hash_out):
        if path.exists():
            raise Refused(f"{path} exists; nothing written")
    key = secrets.token_urlsafe(32)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    _private_write(key_out, key)
    _private_write(hash_out, f"{args.use_case}:{digest}\n")
    print(f"wrote key to {key_out} and hash line to {hash_out}")


def add(args: argparse.Namespace) -> None:
    env, hash_file = Path(args.env_file), Path(args.hash_file)
    try:
        entry = hash_file.read_text(encoding="utf-8").strip()
    except OSError:
        raise Refused(f"cannot read {hash_file}") from None
    parsed = _parse(entry)
    if parsed is None or "\n" in entry:
        raise Refused(f"{hash_file} does not contain one USE_CASE_ID:<64 hex> line")
    use_case_id, digest = parsed
    lines, index = _read_env(env)
    current = _entries(lines[index].split("=", 1)[1]) if index is not None else []
    if any((_parse(e) or ("", ""))[1] == digest for e in current):
        raise Refused("this key hash is already in the env file; nothing changed")
    value = ", ".join(current + [f"{use_case_id}:{digest}"])
    if index is None:
        lines.append(f"{NAME}={value}")
    else:
        lines[index] = f"{NAME}={value}"
    _write_env(env, lines)
    hash_file.unlink()
    print(f"added a key for {use_case_id} ({digest[:8]})")


def list_keys(args: argparse.Namespace) -> None:
    lines, index = _read_env(Path(args.env_file))
    current = _entries(lines[index].split("=", 1)[1]) if index is not None else []
    for position, entry in enumerate(current, start=1):
        parsed = _parse(entry)
        print(f"{parsed[0]} {parsed[1][:8]}" if parsed else f"#{position} malformed")


def remove(args: argparse.Namespace) -> None:
    env = Path(args.env_file)
    prefix = args.hash_prefix.lower()
    lines, index = _read_env(env)
    if index is None:
        raise Refused(f"{NAME} is not in the env file; nothing removed")
    current = _entries(lines[index].split("=", 1)[1])
    matches = [i for i, entry in enumerate(current)
               if (p := _parse(entry)) and p[0] == args.use_case and p[1].startswith(prefix)]
    if len(matches) != 1:
        raise Refused(f"{len(matches)} keys match; nothing removed")
    del current[matches[0]]
    lines[index] = f"{NAME}={', '.join(current)}"
    _write_env(env, lines)
    print(f"removed a key for {args.use_case} ({prefix[:8]})")


def _use_case(value: str) -> str:
    if not ID.match(value):
        raise argparse.ArgumentTypeError("not a valid use case ID")
    return value


def _prefix(value: str) -> str:
    if not PREFIX.match(value.lower()):
        raise argparse.ArgumentTypeError("8 to 64 hex characters")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="batch_keys.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("make")
    p.add_argument("--use-case", required=True, type=_use_case)
    p.add_argument("--key-out", required=True)
    p.add_argument("--hash-out", required=True)
    p.set_defaults(func=make)
    p = sub.add_parser("add")
    p.add_argument("--env-file", required=True)
    p.add_argument("--hash-file", required=True)
    p.set_defaults(func=add)
    p = sub.add_parser("list")
    p.add_argument("--env-file", required=True)
    p.set_defaults(func=list_keys)
    p = sub.add_parser("remove")
    p.add_argument("--env-file", required=True)
    p.add_argument("--use-case", required=True, type=_use_case)
    p.add_argument("--hash-prefix", required=True, type=_prefix)
    p.set_defaults(func=remove)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_keys.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Stop for review** (Claude commits `feat(s2-01): batch_keys.py to make, add, list and remove key entries`)

---

### Task 4: local stack uses `rtr-fraud-validation`

**Files:**
- Modify: `deploy/compose/compose.local.yaml`, `scripts/compose-smoke.sh`, `backend/tests/test_compose_files.py`

- [ ] **Step 1: Update the tests** in `backend/tests/test_compose_files.py`

In `test_local_file_builds_backend_and_waits_for_postgres`, replace

```python
    assert env["BATCH_API_KEY_SHA256"] == f"GCP-UC-03:{expected}"
```

with

```python
    # the local test key belongs to a registered use case (S2-01 registry)
    assert env["BATCH_API_KEY_SHA256"] == f"rtr-fraud-validation:{expected}"
```

In `test_smoke_script_cleans_up_and_fails_fast`, add:

```python
    assert 'body["use_case_id"] = "rtr-fraud-validation"' in text
```

- [ ] **Step 2: Run them and make sure they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: FAIL in the two changed tests

- [ ] **Step 3: Implement**

`deploy/compose/compose.local.yaml`: change the backend line to

```yaml
      BATCH_API_KEY_SHA256: rtr-fraud-validation:ca9263478834f0d9f054e84eda1a55dee86d8a6551f27aa8a2c751a4b541b200
```

`scripts/compose-smoke.sh`: in the Python block that writes `body.json`, after `body["run_id"] = sys.argv[2]` add the line

```python
body["use_case_id"] = "rtr-fraud-validation"   # a registered use case (S2-01)
```

- [ ] **Step 4: Run the tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py -q`
Expected: PASS. (The CI smoke test runs on the pull request; do not claim it ran.)

- [ ] **Step 5: Stop for review** (Claude commits `test(s2-01): local stack uses the registered use case`)

---

### Task 5: documentation

**Files:**
- Modify: `changes/2026-10-02-batch-monitoring-mvp/issues.md`, `docs/STRICT-LIVE.md`, `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`

- [ ] **Step 1: `issues.md` S2-01** — after the meta table of S2-01, add:
`**Changed 2026-10-12 (design: changes/2026-10-12-s2-01-registry/):** the key hashes stay in the backend env file (BATCH_API_KEY_SHA256), not in a database table; scripts/batch_keys.py edits that file. The registry is backend/registry/batch-use-cases.yaml with the October fields only (identity-only). A key for an unregistered use case gives 403.`
In the S2-01 "Part" table, change the "API key hashes" row location from "Database table" to "The backend env file (`BATCH_API_KEY_SHA256`)".

- [ ] **Step 2: `docs/STRICT-LIVE.md`**, section "Batch run receiver": add two sentences: the registry file and that a key for an unregistered use case gives `403`; the readiness error for a key entry of an unregistered use case.

- [ ] **Step 3: `deploy/compose/TESTHOST.md`** — add a section `## Add or rotate an API key (S2-01)` before `## Check a trace (S1-07)`, with numbered steps, each command in its own block:
  1. Laptop (PowerShell, repository root): `backend\.venv\Scripts\python.exe backend\scripts\batch_keys.py make --use-case <use_case_id> --key-out key.tmp --hash-out hash.tmp`
  2. New use case: `gcloud secrets create batch-api-key-<use_case_id> --data-file key.tmp`. Rotation: `gcloud secrets versions add batch-api-key-<use_case_id> --data-file key.tmp`.
  3. `gcloud compute scp hash.tmp backend/scripts/batch_keys.py ai-ml-monitoring-dev-env:/tmp/ --zone asia-southeast3-c --tunnel-through-iap`, then `Remove-Item key.tmp`.
  4. VM: `sudo python3 /tmp/batch_keys.py add --env-file /opt/model-monitor/backend.env --hash-file /tmp/hash.tmp`
  5. VM: in `/opt/model-monitor/compose`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate --wait backend`
  6. Rotation only, after one successful run with the new key: `sudo python3 /tmp/batch_keys.py list --env-file /opt/model-monitor/backend.env`, then `sudo python3 /tmp/batch_keys.py remove --env-file /opt/model-monitor/backend.env --use-case <use_case_id> --hash-prefix <old prefix>`, then step 5 again.
  - Note: a new use case also needs its entry in `backend/registry/batch-use-cases.yaml` (pull request and a new image) before its key works.

- [ ] **Step 4: `CHANGELOG.md`** — under `## [Unreleased]` / `### Added`, first item:

```markdown
- Batch use-case registry (S2-01): `backend/registry/batch-use-cases.yaml` lists each batch
  use case with its October settings. The backend does not start with a bad registry, a key
  for an unregistered use case gives `403`, and readiness reports such a key entry.
  `backend/scripts/batch_keys.py` makes, adds, lists and removes API key entries without
  showing a key or a full hash.
```

- [ ] **Step 5: `DEVLOG.md`** — add at the top of `## Work log` an entry `### 2026-10-12 — S2-01: batch use-case registry` with: what was built (files), the decisions from `intent.md`, the exact pytest results you ran, and "Not yet run: the CI smoke test (on the pull request) and the test-host deploy (readiness must stay ready with the existing key)".

- [ ] **Step 6: Run** `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py -q`, then the fast suite `.venv\Scripts\python.exe -m pytest -q -m "not slow"`. Expected: PASS.

- [ ] **Step 7: Stop for review** (Claude commits `docs(s2-01): registry, key runbook, changelog and devlog`)
