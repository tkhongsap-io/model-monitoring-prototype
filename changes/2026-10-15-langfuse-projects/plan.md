# One Langfuse Project per Use Case (S2-03b, #96) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **In this project Codex implements ONE task per run (`codex exec`, reasoning effort medium) and does not commit; Claude reviews, runs the tests and commits after each task.**

**Goal:** Every span and score of a run lands in the Langfuse project of its use case (named the `use_case_id`); spans with no known use case land in `unrouted`.

**Architecture:** A pure module (`app/langfuse_projects.py`) validates one YAML project file per project and renders two generated files: the Collector routes file (routing connector, one exporter per project) and an env file with the keys. A project tool (`scripts/langfuse_projects.py`, run in the backend image) checks new keys against Langfuse and writes the files. The backend labels its HTTP span with the use case; the evaluator and the trace check pick the key pair of the run's use case.

**Tech Stack:** Python 3.12, PyYAML, Pydantic v2, OpenTelemetry Collector Contrib 0.161.0 (routing connector), Docker Compose, Langfuse 4.50.0 public API, GitHub Actions.

**Spec:** `changes/2026-10-15-langfuse-projects/spec.md` (intent: `intent.md`). Read both, and the spec's "Names" table, before you start.

## Global Constraints

- Project name = `use_case_id`. The default project is `unrouted`.
- Routing order for each use case X: resource `use.case.id` == X; else (no resource label) span `use_case_id` == X; else (no label at all) resource `service.name` == X. Anything else → `unrouted`.
- env slug: `use_case_id` upper case, every character not `A-Z0-9` replaced by `_`.
- Env names: `LANGFUSE_PROJECTS` (comma list), `LANGFUSE_PK__<slug>`, `LANGFUSE_SK__<slug>`, `LANGFUSE_OTLP_AUTH__<slug>`.
- No new Python or npm package. Collector image stays `otel/opentelemetry-collector-contrib:0.161.0`.
- Never print or log a full key. `list` shows at most 8 characters of a public key and nothing of a secret key. Error messages name fields, never values.
- Project files: mode 600, folder 700, root. The generated env: mode 600. The generated routes file: mode 644 (it holds no secret; the Collector runs as uid 10001).
- LF line endings. No `git add`, no `git commit` (Claude commits).
- Run tests from `backend/` with `.venv\Scripts\python.exe -m pytest ...`; if the sandbox blocks the temp folder, add `-p no:cacheprovider --basetemp=.pytest-tmp`. Never patch `os.mkdir` or other globals in `conftest.py`.
- Do not run Docker, Compose, the shell scripts or CI.

### Corrections to the spec (they win over the spec)

1. **Generated files folder:** `/opt/model-monitor/langfuse-generated/routes.yaml` (644) and `/opt/model-monitor/langfuse-generated/projects.env` (600), not the compose folder.
2. **The keys file** given to the wrapper is copied by the wrapper into the project folder as `.incoming.keys` (so the tool container can read it) and the original is deleted; the tool deletes `.incoming.keys` after use.
3. **`render_routes` takes use case IDs, not project files:** the routes file holds no keys, so the committed local routes file can be compared with the generator in a unit test.
4. **The project tool has a fifth command `routes`** (`--exporter file --file-dir D --output F`), used only by the CI routing test.

## Review Focus

1. **A project file whose YAML has a key typo** (`secret_kay`): refused with the field name, nothing written, the running routes unchanged. Test in Task 1 (`test_unknown_field_is_refused_without_values`).
2. **A use case ID with `.` or `:`** (allowed by the registry): slug and quotes stay valid in the routes file. Test in Task 1 (`test_ids_with_dots_and_colons`).
3. **Two IDs with the same slug** (`a-b` and `a.b`): refused. Test in Task 1 (`test_slug_collision_is_refused`).
4. **`LANGFUSE_PROJECTS` set but one project has no keys:** that project falls back to `unrouted`, not an error. Test in Task 1 (`test_keys_for_falls_back_to_unrouted`).
5. **A trace found in `unrouted` only:** the 5th item is MISSING with "in unrouted, not in <project>". Test in Task 4 (`test_langfuse_item_reports_unrouted`).

---

### Task 1: Pure project module and key lookup

**Files:**
- Create: `backend/app/langfuse_projects.py`
- Modify: `backend/app/config.py` (add `langfuse_project_keys()` after the evaluator settings)
- Test: `backend/tests/test_langfuse_projects.py`

**Interfaces:**
- Produces (`app.langfuse_projects`):
  - `UNROUTED = "unrouted"`, `RESOURCE_LABEL = "use.case.id"`, `SPAN_LABEL = "use_case_id"`
  - `class ProjectError(ValueError)`
  - `class ProjectFile(BaseModel)`: `use_case_id: str`, `public_key: str`, `secret_key: str`, `added_at: str`
  - `env_slug(use_case_id: str) -> str`
  - `parse_project(file_name: str, text: str, registered: set[str]) -> ProjectFile`
  - `check_set(projects: list[ProjectFile]) -> list[ProjectFile]` (sorted: `unrouted` first, then by ID)
  - `routing_condition(use_case_id: str) -> str`
  - `render_routes(use_case_ids: list[str], *, exporter: str = "otlphttp", file_dir: str = "/out") -> str`
  - `render_env(projects: list[ProjectFile]) -> str`
  - `otlp_auth(public_key: str, secret_key: str) -> str`
  - `keys_from_env(environ: Mapping[str, str], fallback: tuple[str, str] = ("", "")) -> dict[str, tuple[str, str]]`
  - `keys_for(keys: dict[str, tuple[str, str]], use_case_id: str | None) -> tuple[str, tuple[str, str]] | None`
- Produces (`app.config`): `langfuse_project_keys() -> dict[str, tuple[str, str]]`

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_langfuse_projects.py`:

```python
"""One Langfuse project per use case (S2-03b): the pure module."""
from __future__ import annotations

import base64

import pytest
import yaml

from app import config
from app import langfuse_projects as lp

REG = {"rtr-fraud-validation", "GCP-UC-03", "a-b", "a.b", "uc.v2:x"}


def text(uc="rtr-fraud-validation", pk="pk-lf-1111", sk="sk-lf-2222", **extra) -> str:
    body = {"use_case_id": uc, "public_key": pk, "secret_key": sk,
            "added_at": "2026-10-15T08:00:00Z", **extra}
    return yaml.safe_dump(body)


def project(uc, pk="pk-lf-1111", sk="sk-lf-2222"):
    return lp.parse_project(f"{uc}.yaml", text(uc, pk, sk), REG)


def test_env_slug():
    assert lp.env_slug("rtr-fraud-validation") == "RTR_FRAUD_VALIDATION"
    assert lp.env_slug("uc.v2:x") == "UC_V2_X"
    assert lp.env_slug("unrouted") == "UNROUTED"


def test_parse_good_file():
    p = project("rtr-fraud-validation")
    assert (p.use_case_id, p.public_key, p.secret_key) == ("rtr-fraud-validation", "pk-lf-1111",
                                                           "sk-lf-2222")


def test_unknown_field_is_refused_without_values():
    with pytest.raises(lp.ProjectError) as exc:
        lp.parse_project("rtr-fraud-validation.yaml",
                         text(secret_kay="sk-lf-leak").replace("secret_key: sk-lf-2222\n", ""),
                         REG)
    message = str(exc.value)
    assert "secret_kay" in message and "sk-lf-leak" not in message and "sk-lf-2222" not in message


@pytest.mark.parametrize("name, body, words", [
    ("other.yaml", text(), ["file name", "rtr-fraud-validation.yaml"]),
    ("nope.yaml", text("nope"), ["not in the registry"]),
    ("rtr-fraud-validation.yaml", text(pk="pk-xx"), ["public_key"]),
    ("rtr-fraud-validation.yaml", text(sk="secret"), ["secret_key"]),
    ("rtr-fraud-validation.yaml", "use_case_id: [", ["not valid YAML"]),
])
def test_bad_files(name, body, words):
    with pytest.raises(lp.ProjectError) as exc:
        lp.parse_project(name, body, REG)
    for word in words:
        assert word in str(exc.value)


def test_unrouted_needs_no_registry_entry():
    assert project("unrouted").use_case_id == "unrouted"


def test_check_set_needs_unrouted_and_sorts():
    with pytest.raises(lp.ProjectError, match="unrouted.yaml is missing"):
        lp.check_set([project("rtr-fraud-validation")])
    ordered = lp.check_set([project("rtr-fraud-validation"), project("GCP-UC-03"),
                            project("unrouted")])
    assert [p.use_case_id for p in ordered] == ["unrouted", "GCP-UC-03", "rtr-fraud-validation"]


def test_slug_collision_is_refused():
    with pytest.raises(lp.ProjectError, match="A_B"):
        lp.check_set([project("unrouted"), project("a-b"), project("a.b")])


def test_routing_condition_order():
    c = lp.routing_condition("rtr-fraud-validation")
    assert c == (
        'resource.attributes["use.case.id"] == "rtr-fraud-validation"'
        ' or (resource.attributes["use.case.id"] == nil'
        ' and attributes["use_case_id"] == "rtr-fraud-validation")'
        ' or (resource.attributes["use.case.id"] == nil and attributes["use_case_id"] == nil'
        ' and resource.attributes["service.name"] == "rtr-fraud-validation")')


def test_render_routes_otlphttp():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "rtr-fraud-validation"]))
    routing = doc["connectors"]["routing/langfuse"]
    assert routing["default_pipelines"] == ["traces/langfuse-unrouted"]
    assert routing["error_mode"] == "ignore"
    assert [r["pipelines"] for r in routing["table"]] == [["traces/langfuse-rtr-fraud-validation"]]
    assert routing["table"][0]["context"] == "span"
    assert routing["table"][0]["condition"] == lp.routing_condition("rtr-fraud-validation")
    exp = doc["exporters"]["otlphttp/langfuse-rtr-fraud-validation"]
    assert exp == {"endpoint": "http://langfuse-web:3000/api/public/otel",
                   "headers": {"Authorization": "Basic ${env:LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION}",
                               "x-langfuse-ingestion-version": "4"}}
    assert "otlphttp/langfuse-unrouted" in doc["exporters"]
    pipes = doc["service"]["pipelines"]
    assert pipes["traces/langfuse-unrouted"] == {"receivers": ["routing/langfuse"],
                                                 "exporters": ["otlphttp/langfuse-unrouted"]}
    assert lp.render_routes(["unrouted", "rtr-fraud-validation"]).startswith("# Generated")


def test_render_routes_file_mode_for_ci():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "rtr-fraud-validation"],
                                          exporter="file", file_dir="/out"))
    assert doc["exporters"]["file/langfuse-rtr-fraud-validation"] == {
        "path": "/out/rtr-fraud-validation.jsonl"}
    assert doc["exporters"]["file/langfuse-unrouted"] == {"path": "/out/unrouted.jsonl"}


def test_ids_with_dots_and_colons():
    doc = yaml.safe_load(lp.render_routes(["unrouted", "uc.v2:x"]))
    assert "otlphttp/langfuse-uc.v2:x" in doc["exporters"]
    assert "LANGFUSE_OTLP_AUTH__UC_V2_X" in doc["exporters"]["otlphttp/langfuse-uc.v2:x"][
        "headers"]["Authorization"]


def test_render_env():
    env = lp.render_env(lp.check_set([project("unrouted", "pk-lf-u", "sk-lf-u"),
                                      project("rtr-fraud-validation", "pk-lf-r", "sk-lf-r")]))
    lines = [l for l in env.splitlines() if l and not l.startswith("#")]
    assert lines == [
        "LANGFUSE_PROJECTS=unrouted,rtr-fraud-validation",
        "LANGFUSE_PK__UNROUTED=pk-lf-u", "LANGFUSE_SK__UNROUTED=sk-lf-u",
        "LANGFUSE_OTLP_AUTH__UNROUTED=" + base64.b64encode(b"pk-lf-u:sk-lf-u").decode(),
        "LANGFUSE_PK__RTR_FRAUD_VALIDATION=pk-lf-r", "LANGFUSE_SK__RTR_FRAUD_VALIDATION=sk-lf-r",
        "LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION=" + base64.b64encode(b"pk-lf-r:sk-lf-r").decode(),
    ]
    assert env.startswith("# Generated")


def test_keys_from_env_with_projects():
    env = {"LANGFUSE_PROJECTS": "unrouted, rtr-fraud-validation",
           "LANGFUSE_PK__UNROUTED": "pk-u", "LANGFUSE_SK__UNROUTED": "sk-u",
           "LANGFUSE_PK__RTR_FRAUD_VALIDATION": "pk-r", "LANGFUSE_SK__RTR_FRAUD_VALIDATION": "sk-r"}
    assert lp.keys_from_env(env, ("pk-old", "sk-old")) == {
        "unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")}


def test_keys_from_env_fallback_is_unrouted():
    assert lp.keys_from_env({}, ("pk-old", "sk-old")) == {"unrouted": ("pk-old", "sk-old")}
    assert lp.keys_from_env({}, ("", "")) == {}


def test_keys_for_falls_back_to_unrouted():
    keys = {"unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")}
    assert lp.keys_for(keys, "rtr-fraud-validation") == ("rtr-fraud-validation", ("pk-r", "sk-r"))
    assert lp.keys_for(keys, "GCP-UC-03") == ("unrouted", ("pk-u", "sk-u"))
    assert lp.keys_for(keys, None) == ("unrouted", ("pk-u", "sk-u"))
    assert lp.keys_for({"rtr-fraud-validation": ("pk-r", "sk-r")}, "other") is None


def test_config_langfuse_project_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PROJECTS", raising=False)
    monkeypatch.setattr(config, "LANGFUSE_PUBLIC_KEY", "pk-old")
    monkeypatch.setattr(config, "LANGFUSE_SECRET_KEY", "sk-old")
    assert config.langfuse_project_keys() == {"unrouted": ("pk-old", "sk-old")}
    monkeypatch.setenv("LANGFUSE_PROJECTS", "unrouted")
    monkeypatch.setenv("LANGFUSE_PK__UNROUTED", "pk-u")
    monkeypatch.setenv("LANGFUSE_SK__UNROUTED", "sk-u")
    assert config.langfuse_project_keys() == {"unrouted": ("pk-u", "sk-u")}
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_projects.py -q`
Expected: FAIL (`ModuleNotFoundError: app.langfuse_projects`).

- [ ] **Step 3: Write `backend/app/langfuse_projects.py`:**

```python
"""One Langfuse project for each use case (S2-03b). Pure: no I/O, no clock.

A project file (`<use_case_id>.yaml`) holds the keys of one Langfuse project, named exactly
the use case ID; `unrouted.yaml` is the default project. From the set of project files this
module renders the Collector routes file (no secrets) and one env file (the keys). Error
messages name files and fields, never key values.
"""
from __future__ import annotations

import base64
import re
from typing import Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

UNROUTED = "unrouted"
RESOURCE_LABEL = "use.case.id"
SPAN_LABEL = "use_case_id"
OTEL_ENDPOINT = "http://langfuse-web:3000/api/public/otel"
CONNECTOR = "routing/langfuse"
GENERATED_HEADER = ("# Generated by the project tool (backend/scripts/langfuse_projects.py) from\n"
                    "# langfuse-projects/*.yaml (S2-03b). Do not edit.\n")


class ProjectError(ValueError):
    """A project file or the set of project files is not valid. Names no key value."""


class ProjectFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use_case_id: str = Field(min_length=1, max_length=128,
                             pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    public_key: str = Field(pattern=r"^pk-lf-[A-Za-z0-9-]+$")
    secret_key: str = Field(pattern=r"^sk-lf-[A-Za-z0-9-]+$")
    added_at: str = Field(min_length=1)


def env_slug(use_case_id: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", use_case_id.upper())


def parse_project(file_name: str, text: str, registered: set[str]) -> ProjectFile:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        raise ProjectError(f"{file_name}: not valid YAML") from None
    try:
        project = ProjectFile.model_validate(raw)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) or "(file)" for e in exc.errors()})
        raise ProjectError(f"{file_name}: bad or unknown fields: {', '.join(fields)}") from None
    if file_name != f"{project.use_case_id}.yaml":
        raise ProjectError(f"{file_name}: the file name must be {project.use_case_id}.yaml")
    if project.use_case_id != UNROUTED and project.use_case_id not in registered:
        raise ProjectError(f"{file_name}: use case {project.use_case_id} is not in the registry")
    return project


def check_set(projects: list[ProjectFile]) -> list[ProjectFile]:
    ids = [p.use_case_id for p in projects]
    if UNROUTED not in ids:
        raise ProjectError("unrouted.yaml is missing")
    seen: dict[str, str] = {}
    for p in projects:
        slug = env_slug(p.use_case_id)
        if slug in seen:
            raise ProjectError(f"{seen[slug]} and {p.use_case_id} have the same env name {slug}")
        seen[slug] = p.use_case_id
    return sorted(projects, key=lambda p: (p.use_case_id != UNROUTED, p.use_case_id))


def routing_condition(use_case_id: str) -> str:
    res, span, uc = RESOURCE_LABEL, SPAN_LABEL, use_case_id
    return (f'resource.attributes["{res}"] == "{uc}"'
            f' or (resource.attributes["{res}"] == nil and attributes["{span}"] == "{uc}")'
            f' or (resource.attributes["{res}"] == nil and attributes["{span}"] == nil'
            f' and resource.attributes["service.name"] == "{uc}")')


def _exporter(use_case_id: str, exporter: str, file_dir: str) -> tuple[str, dict]:
    if exporter == "file":
        return f"file/langfuse-{use_case_id}", {"path": f"{file_dir}/{use_case_id}.jsonl"}
    if exporter != "otlphttp":
        raise ProjectError(f"unknown exporter {exporter}")
    return f"otlphttp/langfuse-{use_case_id}", {
        "endpoint": OTEL_ENDPOINT,
        "headers": {"Authorization": f"Basic ${{env:LANGFUSE_OTLP_AUTH__{env_slug(use_case_id)}}}",
                    "x-langfuse-ingestion-version": "4"}}


def render_routes(use_case_ids: list[str], *, exporter: str = "otlphttp",
                  file_dir: str = "/out") -> str:
    ids = sorted(set(use_case_ids) - {UNROUTED})
    exporters: dict[str, dict] = {}
    pipelines: dict[str, dict] = {}
    for uc in [UNROUTED, *ids]:
        name, body = _exporter(uc, exporter, file_dir)
        exporters[name] = body
        pipelines[f"traces/langfuse-{uc}"] = {"receivers": [CONNECTOR], "exporters": [name]}
    doc = {
        "connectors": {CONNECTOR: {
            "default_pipelines": [f"traces/langfuse-{UNROUTED}"],
            "error_mode": "ignore",
            "table": [{"context": "span", "condition": routing_condition(uc),
                       "pipelines": [f"traces/langfuse-{uc}"]} for uc in ids],
        }},
        "exporters": exporters,
        "service": {"pipelines": pipelines},
    }
    return GENERATED_HEADER + yaml.safe_dump(doc, sort_keys=False, width=1000)


def otlp_auth(public_key: str, secret_key: str) -> str:
    return base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()


def render_env(projects: list[ProjectFile]) -> str:
    lines = [GENERATED_HEADER.rstrip("\n"),
             "LANGFUSE_PROJECTS=" + ",".join(p.use_case_id for p in projects)]
    for p in projects:
        slug = env_slug(p.use_case_id)
        lines += [f"LANGFUSE_PK__{slug}={p.public_key}", f"LANGFUSE_SK__{slug}={p.secret_key}",
                  f"LANGFUSE_OTLP_AUTH__{slug}={otlp_auth(p.public_key, p.secret_key)}"]
    return "\n".join(lines) + "\n"


def keys_from_env(environ: Mapping[str, str],
                  fallback: tuple[str, str] = ("", "")) -> dict[str, tuple[str, str]]:
    names = [n.strip() for n in environ.get("LANGFUSE_PROJECTS", "").split(",") if n.strip()]
    if not names:
        public_key, secret_key = (fallback[0] or "").strip(), (fallback[1] or "").strip()
        return {UNROUTED: (public_key, secret_key)} if public_key and secret_key else {}
    out: dict[str, tuple[str, str]] = {}
    for uc in names:
        slug = env_slug(uc)
        public_key = environ.get(f"LANGFUSE_PK__{slug}", "").strip()
        secret_key = environ.get(f"LANGFUSE_SK__{slug}", "").strip()
        if public_key and secret_key:
            out[uc] = (public_key, secret_key)
    return out


def keys_for(keys: dict[str, tuple[str, str]],
             use_case_id: str | None) -> tuple[str, tuple[str, str]] | None:
    if use_case_id and use_case_id in keys:
        return use_case_id, keys[use_case_id]
    if UNROUTED in keys:
        return UNROUTED, keys[UNROUTED]
    return None
```

- [ ] **Step 4: Add to `backend/app/config.py`**, after `EVALUATOR_LANGFUSE_HOST`:

```python
def langfuse_project_keys() -> dict[str, tuple[str, str]]:
    """Key pairs of the Langfuse projects (S2-03b), by use case ID; `unrouted` is the default.

    From LANGFUSE_PROJECTS and LANGFUSE_PK__/SK__<slug>; without LANGFUSE_PROJECTS the old
    single key pair counts as `unrouted` (compatibility during the switch)."""
    from .langfuse_projects import keys_from_env
    return keys_from_env(os.environ, (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY))
```

- [ ] **Step 5: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_projects.py -q`
Expected: PASS.

- [ ] **Step 6: Commit** (Claude): `feat(s2-03b): project files, routes and key lookup (pure)`

---

### Task 2: The project tool

**Files:**
- Create: `backend/scripts/langfuse_projects.py`
- Test: `backend/tests/test_langfuse_projects_tool.py`

**Interfaces:**
- Consumes: Task 1 (`parse_project`, `check_set`, `render_routes`, `render_env`, `ProjectError`, `UNROUTED`); `app.registry.load(path) -> dict`; `app.config.BATCH_REGISTRY_PATH`.
- Produces: CLI `python scripts/langfuse_projects.py [--projects-dir D] [--generated-dir G] [--registry R] [--langfuse-url U] <command>` with commands:
  - `add <use_case_id> --keys-file F` | `add <use_case_id> --from-langfuse-env F`
  - `regenerate`
  - `list`
  - `routes --exporter {otlphttp,file} --file-dir D --output F` (no keys needed)
  - Defaults: `--projects-dir /projects`, `--generated-dir /generated`, `--registry` = `config.BATCH_REGISTRY_PATH`, `--langfuse-url` = env `LANGFUSE_URL` or `http://langfuse-web:3000`.
  - Exit 0 ok, 1 check failed (nothing written), 2 usage.
  - `main(argv: list[str] | None = None, *, fetch=None) -> int`; `fetch(url, auth_header) -> tuple[int, bytes]` is injectable for tests.

- [ ] **Step 1: Write the failing tests** in `backend/tests/test_langfuse_projects_tool.py`:

```python
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
```

Note: `routes` takes `--use-cases <comma list>` (the IDs), because it needs no project files.

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_projects_tool.py -q`
Expected: FAIL (`ModuleNotFoundError: langfuse_projects`).

- [ ] **Step 3: Write `backend/scripts/langfuse_projects.py`:**

```python
#!/usr/bin/env python3
"""Project tool (S2-03b): one Langfuse project for each use case.

Runs in the backend image as the Compose tool service `langfuse-projects` (root; mounts the
project folder, the generated folder and /opt/langfuse/langfuse.env). Commands:
  add <use_case_id> --keys-file F          keys made in the Langfuse UI; checked first
  add unrouted --from-langfuse-env F       today's project keys from langfuse.env
  regenerate                               rewrite routes.yaml and projects.env
  list                                     use case, 8 characters of the public key, date
  routes --use-cases a,b --exporter file --file-dir D --output F   (CI routing test)
Never prints a full key. Exit 0 ok, 1 a check failed (nothing written), 2 usage.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config, registry  # noqa: E402
from app import langfuse_projects as lp  # noqa: E402

Fetch = Callable[[str, str], tuple[int, bytes]]


def _fetch(url: str, auth: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Authorization": auth,
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def _write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, mode)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _env_values(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip()
    return values


def _load_all(projects_dir: Path, registered: set[str]) -> list[lp.ProjectFile]:
    files = sorted(projects_dir.glob("*.yaml")) if projects_dir.exists() else []
    projects = [lp.parse_project(f.name, f.read_text(encoding="utf-8"), registered)
                for f in files]
    return lp.check_set(projects)


def _regenerate(projects_dir: Path, generated_dir: Path, registered: set[str]) -> list[str]:
    projects = _load_all(projects_dir, registered)        # raises before anything is written
    ids = [p.use_case_id for p in projects]
    _write(generated_dir / "routes.yaml", lp.render_routes(ids), 0o644)
    _write(generated_dir / "projects.env", lp.render_env(projects), 0o600)
    return ids


def _check_keys(base_url: str, use_case_id: str, public_key: str, secret_key: str,
                fetch: Fetch) -> None:
    auth = "Basic " + base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    status, body = fetch(f"{base_url.rstrip('/')}/api/public/projects", auth)
    if status != 200:
        raise lp.ProjectError(f"Langfuse answered {status} for these keys")
    try:
        names = [p.get("name") for p in json.loads(body).get("data", [])]
    except (ValueError, AttributeError):
        raise lp.ProjectError("Langfuse answered with bad JSON") from None
    if names != [use_case_id]:
        raise lp.ProjectError(
            f"these keys belong to project {', '.join(map(str, names)) or '(none)'}, "
            f"not {use_case_id}; create the project with that exact name")


def _add(ns, registered: set[str], fetch: Fetch) -> int:
    projects_dir, uc = Path(ns.projects_dir), ns.use_case_id
    source = Path(ns.keys_file or ns.from_langfuse_env)
    try:
        values = _env_values(source)
    finally:
        if ns.keys_file:
            source.unlink(missing_ok=True)                 # the keys file never stays
    if ns.keys_file:
        pk, sk = values.get("LANGFUSE_PUBLIC_KEY", ""), values.get("LANGFUSE_SECRET_KEY", "")
    else:
        pk = values.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY", "")
        sk = values.get("LANGFUSE_INIT_PROJECT_SECRET_KEY", "")
    if not pk or not sk:
        raise lp.ProjectError(f"{source.name}: the public and the secret key are needed")
    if uc != lp.UNROUTED and uc not in registered:
        raise lp.ProjectError(f"use case {uc} is not in the registry")
    _check_keys(ns.langfuse_url, uc, pk, sk, fetch)
    text = (f"use_case_id: {uc}\npublic_key: {pk}\nsecret_key: {sk}\n"
            f"added_at: \"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\"\n")
    lp.parse_project(f"{uc}.yaml", text, registered)        # same rules as regenerate
    target = projects_dir / f"{uc}.yaml"
    previous = target.read_text(encoding="utf-8") if target.exists() else None
    _write(target, text, 0o600)
    try:
        ids = _regenerate(projects_dir, Path(ns.generated_dir), registered)
    except lp.ProjectError:
        if previous is None:                                # undo: nothing half-written
            target.unlink(missing_ok=True)
        else:
            _write(target, previous, 0o600)
        raise
    print(f"added {uc}; projects: {', '.join(ids)}")
    return 0


def _list(ns, registered: set[str]) -> int:
    for p in _load_all(Path(ns.projects_dir), registered):
        print(f"{p.use_case_id}\t{p.public_key[:8]}…\t{p.added_at}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="langfuse_projects.py")
    parser.add_argument("--projects-dir", default="/projects")
    parser.add_argument("--generated-dir", default="/generated")
    parser.add_argument("--registry", default=config.BATCH_REGISTRY_PATH)
    parser.add_argument("--langfuse-url",
                        default=os.environ.get("LANGFUSE_URL", "http://langfuse-web:3000"))
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("use_case_id")
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument("--keys-file")
    source.add_argument("--from-langfuse-env")
    sub.add_parser("regenerate")
    sub.add_parser("list")
    routes = sub.add_parser("routes")
    routes.add_argument("--use-cases", required=True)
    routes.add_argument("--exporter", choices=["otlphttp", "file"], default="otlphttp")
    routes.add_argument("--file-dir", default="/out")
    routes.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None, *, fetch: Fetch | None = None) -> int:
    try:
        ns = _parser().parse_args(argv)
    except SystemExit:
        return 2
    try:
        if ns.command == "routes":
            ids = [x.strip() for x in ns.use_cases.split(",") if x.strip()]
            _write(Path(ns.output), lp.render_routes(ids, exporter=ns.exporter,
                                                     file_dir=ns.file_dir), 0o644)
            return 0
        registered = set(registry.load(ns.registry))
        if ns.command == "add":
            return _add(ns, registered, fetch or _fetch)
        if ns.command == "regenerate":
            ids = _regenerate(Path(ns.projects_dir), Path(ns.generated_dir), registered)
            print(f"regenerated; projects: {', '.join(ids)}")
            return 0
        return _list(ns, registered)
    except (lp.ProjectError, registry.RegistryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {type(exc).__name__} on a file", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Note on `test_list_shows_no_full_key`: `list` prints `pk-lf-un…` (8 characters and an ellipsis) for the key `pk-lf-unr`. If the assertion in that test is awkward with the ellipsis, simplify only the test to check `"pk-lf-unr" not in out` and `"sk-lf" not in out`, and list it under "Deviations".

- [ ] **Step 4: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_projects_tool.py -q`
Expected: PASS (on Windows the mode checks are skipped).

- [ ] **Step 5: Commit** (Claude): `feat(s2-03b): project tool (add, regenerate, list, routes)`

---

### Task 3: Backend span label and per-project scores

**Files:**
- Modify: `backend/app/api/batch_routes.py` (`receive_batch_run`, `_ingest`)
- Modify: `backend/app/adapters/langfuse_scores.py` (`LangfuseScoreSender`, `make_sender`)
- Test: `backend/tests/test_batch_runs_tracing.py`, `backend/tests/test_langfuse_scores.py`

**Interfaces:**
- Consumes: Task 1 (`config.langfuse_project_keys()`, `langfuse_projects.keys_for`).
- Produces: `LangfuseScoreSender(client_for: Callable[[str], object | None])`; `send(evaluation)` uses `client_for(evaluation["use_case_id"])` and raises `LookupError` when it returns None. `make_sender() -> LangfuseScoreSender | None` (None when no host or no keys).

- [ ] **Step 1: Write the failing tests.** Add to `backend/tests/test_batch_runs_tracing.py`:

```python
def test_server_span_carries_the_use_case(client, spans):
    response = client.post(URL, json=example("01-completed-online.json"),
                           headers={**AUTH, "traceparent": TRACEPARENT})
    assert response.status_code == 201, response.text
    server = [s for s in spans.get_finished_spans() if s.name == "POST /api/batch/runs"]
    assert len(server) == 1
    assert server[0].attributes["use_case_id"] == RUN[0]
    assert server[0].attributes["run_id"] == RUN[1]


def test_rejected_request_server_span_has_no_use_case(client, spans):
    response = client.post(URL, json=example("01-completed-online.json"),
                           headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    server = [s for s in spans.get_finished_spans() if s.name == "POST /api/batch/runs"]
    assert "use_case_id" not in server[0].attributes
```

In `backend/tests/test_langfuse_scores.py`: add `"use_case_id": "rtr-fraud-validation"` to `EVALUATION`; change every `ls.LangfuseScoreSender(fake_client(scores))` to `ls.LangfuseScoreSender(lambda uc: fake_client(scores))`; replace `test_make_sender_builds_a_client_without_tracing` and `test_make_sender_needs_host_and_keys` with:

```python
def test_make_sender_needs_host_and_keys(monkeypatch):
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {"unrouted": ("pk", "sk")})
    assert ls.make_sender() is None
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {})
    assert ls.make_sender() is None


def test_sender_uses_the_project_of_the_use_case(monkeypatch):
    made = []

    class FakeLangfuse:
        def __init__(self, **kwargs):
            made.append(kwargs)
            self.api = SimpleNamespace(scores=FakeScores())

    import langfuse
    monkeypatch.setattr(langfuse, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(config, "EVALUATOR_LANGFUSE_HOST", "http://langfuse-web:3000")
    monkeypatch.setattr(config, "langfuse_project_keys", lambda: {
        "unrouted": ("pk-u", "sk-u"), "rtr-fraud-validation": ("pk-r", "sk-r")})
    sender = ls.make_sender()
    sender.send({**EVALUATION, "use_case_id": "rtr-fraud-validation"})
    sender.send({**EVALUATION, "use_case_id": "rtr-fraud-validation"})   # cached client
    sender.send({**EVALUATION, "use_case_id": "GCP-UC-03"})               # → unrouted
    assert [(m["public_key"], m["secret_key"]) for m in made] == [("pk-r", "sk-r"),
                                                                  ("pk-u", "sk-u")]
    assert all(m["tracing_enabled"] is False and m["host"] == "http://langfuse-web:3000"
               for m in made)


def test_send_without_a_project_raises():
    with pytest.raises(LookupError):
        ls.LangfuseScoreSender(lambda uc: None).send(EVALUATION)
```

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_runs_tracing.py tests/test_langfuse_scores.py -q`
Expected: FAIL.

- [ ] **Step 3: Label the server span** in `backend/app/api/batch_routes.py`. In `receive_batch_run`, before `with tracing.tracer()...`, add `server = trace.get_current_span()` and pass it: `return await _ingest(request, authorization, span, incoming, server)`. Change `_ingest`'s signature to add `server: trace.Span`, and after `span.set_attributes(identity)` add:

```python
    server.set_attributes(identity)     # S2-03b: the Collector routes the server span too
```

- [ ] **Step 4: Per-project sender** in `backend/app/adapters/langfuse_scores.py`. Replace `LangfuseScoreSender` and `make_sender` with:

```python
class LangfuseScoreSender:
    """Sends the scores of one evaluation to the Langfuse project of its use case (S2-03b)."""

    def __init__(self, client_for) -> None:
        self._client_for = client_for

    def send(self, evaluation: dict) -> None:
        from langfuse.api import ScoreDataType
        client = self._client_for(evaluation.get("use_case_id"))
        if client is None:
            raise LookupError("no Langfuse project keys for this use case")
        for score in scores_for(evaluation):
            client.api.scores.create(
                name=score["name"], value=score["value"], id=score["id"],
                trace_id=evaluation["trace_id"], data_type=ScoreDataType(score["data_type"]),
                comment=score["comment"])


def make_sender() -> LangfuseScoreSender | None:
    host = config.EVALUATOR_LANGFUSE_HOST
    keys = config.langfuse_project_keys()
    if not host or not keys:
        return None
    from ..langfuse_projects import keys_for
    clients: dict[str, object] = {}

    def client_for(use_case_id: str | None):
        found = keys_for(keys, use_case_id)
        if found is None:
            return None
        project, (public_key, secret_key) = found
        if project not in clients:
            import langfuse
            clients[project] = langfuse.Langfuse(public_key=public_key, secret_key=secret_key,
                                                 host=host, tracing_enabled=False, timeout=10)
        return clients[project]

    return LangfuseScoreSender(client_for)
```

Update the module docstring: add "Each run's scores go to the project of its use case (S2-03b); without its keys, to `unrouted`."

- [ ] **Step 5: Run the tests and make sure they pass, then the full fast suite.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_batch_runs_tracing.py tests/test_langfuse_scores.py tests/test_batch_evaluator.py -q`, then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`.
Expected: PASS. (`test_make_sender_never_uses_the_cloud_default` still passes: no host → None.)

- [ ] **Step 6: Commit** (Claude): `feat(s2-03b): backend labels its server span; scores per project`

---

### Task 4: The trace check reads the run's project

**Files:**
- Modify: `backend/scripts/check_trace.py` (`read_langfuse`, `run_once`, docstring)
- Modify: `backend/app/trace_check.py` (`_langfuse`, `check`)
- Test: `backend/tests/test_check_trace_script.py`, `backend/tests/test_trace_check.py`

**Interfaces:**
- Consumes: Task 1 (`keys_from_env`, `keys_for`, `UNROUTED`).
- Produces: `read_langfuse(trace_id: str, use_case_id: str | None) -> tuple[list[str] | None, str | None, str | None]` (names, error, project). `check(..., langfuse_project: str | None = None)`; found detail `"<n> observations in Langfuse project <project>"` (or `"<n> observations in Langfuse"` when the project is None).

- [ ] **Step 1: Write the failing tests.** In `backend/tests/test_trace_check.py`, change the expectation `"4 observations in Langfuse"` to pass `langfuse_project="rtr"` in that test's `check(...)` call and expect `"4 observations in Langfuse project rtr"`. In `backend/tests/test_check_trace_script.py`, change `langfuse_env` and `FakeLangfuse` and add tests:

```python
def langfuse_env(monkeypatch, url, projects=None):
    monkeypatch.setenv("CHECK_LANGFUSE_URL", url)
    monkeypatch.setenv("CHECK_LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("CHECK_LANGFUSE_SECRET_KEY", "sk-lf-secret-value")
    if projects:
        monkeypatch.setenv("LANGFUSE_PROJECTS", ",".join(projects))
        for name, (pk, sk) in projects.items():
            slug = name.upper().replace("-", "_")
            monkeypatch.setenv(f"LANGFUSE_PK__{slug}", pk)
            monkeypatch.setenv(f"LANGFUSE_SK__{slug}", sk)
```

In `FakeLangfuse`, let `body` be a dict from the Basic auth header to a body, or one body for all: in `do_GET`, `reply = outer.body.get(self.headers.get("Authorization"), {"data": []}) if outer.by_auth else outer.body`, with a new constructor flag `by_auth=False`. Then:

```python
def basic(pk, sk):
    return "Basic " + __import__("base64").b64encode(f"{pk}:{sk}".encode()).decode()


def test_langfuse_item_reads_the_run_project(database, tmp_path, monkeypatch, capsys):
    add_row(database)                         # use case of the row: see add_row (GCP-UC-03)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    fake = FakeLangfuse(by_auth=True, body={
        basic("pk-r", "sk-r"): {"data": [{"name": "monitor.ingest"}]}})
    try:
        langfuse_env(monkeypatch, fake.url, {"unrouted": ("pk-u", "sk-u"),
                                             "GCP-UC-03": ("pk-r", "sk-r")})
        assert run([T, "--backend-only", "--spans-file", path]) == 0
    finally:
        fake.close()
    out = " ".join(capsys.readouterr().out.split())
    assert "observations in Langfuse project GCP-UC-03" in out


def test_langfuse_item_reports_unrouted(database, tmp_path, monkeypatch, capsys):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    fake = FakeLangfuse(by_auth=True, body={
        basic("pk-u", "sk-u"): {"data": [{"name": "monitor.ingest"}]}})
    try:
        langfuse_env(monkeypatch, fake.url, {"unrouted": ("pk-u", "sk-u"),
                                             "GCP-UC-03": ("pk-r", "sk-r")})
        assert run([T, "--backend-only", "--spans-file", path]) == 1
    finally:
        fake.close()
    out = " ".join(capsys.readouterr().out.split())
    assert "in unrouted, not in GCP-UC-03" in out
```

Before writing these, open `add_row` in the same file and use the use case ID it really stores; if it is not `GCP-UC-03`, use that ID in both tests. Keep the existing tests passing (the old `CHECK_LANGFUSE_PUBLIC_KEY` / `SECRET_KEY` pair is the `unrouted` fallback when `LANGFUSE_PROJECTS` is not set).

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_check_trace_script.py tests/test_trace_check.py -q`
Expected: FAIL.

- [ ] **Step 3: Change `backend/app/trace_check.py`.** `_langfuse(names, error, backend_only, project=None)`: the found detail becomes `f"{len(names or [])} observations in Langfuse project {project}"` when `project`, else the old text. `check(...)` gets `langfuse_project: str | None = None` and passes it to `_langfuse`.

- [ ] **Step 4: Change `backend/scripts/check_trace.py`.** Replace `read_langfuse` with:

```python
def _observations(url: str, trace_id: str, public_key: str,
                  secret_key: str) -> tuple[list[str], str | None]:
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"{url}/api/public/v2/observations?traceId={trace_id}&limit=100",
        headers={"Authorization": f"Basic {token}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            document = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return [], f"Langfuse answered {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return [], f"Langfuse is not reachable ({type(exc).__name__})"
    except ValueError:
        return [], "Langfuse answered with bad JSON"
    data = document.get("data") if isinstance(document, dict) else None
    if not isinstance(data, list):
        return [], "Langfuse answered with bad JSON"
    return [str(item.get("name", "")) for item in data if isinstance(item, dict)], None


def read_langfuse(trace_id: str, use_case_id: str | None
                  ) -> tuple[list[str] | None, str | None, str | None]:
    """Observation names of the trace in the run's Langfuse project (S2-03b).

    (None, None, None) when not set up. A trace that is only in `unrouted` is reported."""
    url = os.environ.get("CHECK_LANGFUSE_URL", "").strip().rstrip("/")
    keys = lp.keys_from_env(os.environ, (os.environ.get("CHECK_LANGFUSE_PUBLIC_KEY", ""),
                                         os.environ.get("CHECK_LANGFUSE_SECRET_KEY", "")))
    found = lp.keys_for(keys, use_case_id)
    if not url or found is None:
        return None, None, None
    project, (public_key, secret_key) = found
    names, error = _observations(url, trace_id, public_key, secret_key)
    if error or names or project == lp.UNROUTED or lp.UNROUTED not in keys:
        return names, error, project
    other, other_error = _observations(url, trace_id, *keys[lp.UNROUTED])
    if other and not other_error:
        return [], f"in unrouted, not in {project}", project
    return names, None, project
```

Add `from app import langfuse_projects as lp` next to the other `app` imports. In `run_once`, find the use case and pass the project:

```python
    use_case_id = rows[0].use_case_id if rows else next(
        (str(s.attributes.get("use_case_id")) for s in spans
         if s.name == "batch.run" and s.attributes.get("use_case_id")), None)
    names, error, project = read_langfuse(args.trace_id, use_case_id)
    return check(args.trace_id, rows, spans, backend_only=args.backend_only,
                 stored_rows=stored, skipped_lines=skipped,
                 langfuse_names=names, langfuse_error=error, langfuse_project=project)
```

(`RunRow` has `use_case_id`; check its field name in `app/trace_check.py` and use the real one.) Update the module docstring: "The 5th item reads the run's Langfuse project (S2-03b)."

- [ ] **Step 5: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_check_trace_script.py tests/test_trace_check.py -q`
Expected: PASS.

- [ ] **Step 6: Commit** (Claude): `feat(s2-03b): trace check reads the run's Langfuse project`

---

### Task 5: Collector config, Compose, the local routes file and the wrapper

**Files:**
- Modify: `deploy/compose/otel-collector.yaml`
- Create: `deploy/compose/otel-collector.routes.local.yaml` (generated with the tool, committed)
- Modify: `deploy/compose/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml`
- Create: `deploy/compose/add-langfuse-project.sh`
- Test: `backend/tests/test_compose_files.py`, `backend/tests/test_langfuse_projects.py` (sync test)

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces: Collector loads `/etc/otelcol/config.yaml` and `/etc/otelcol/routes.yaml`; tool service `langfuse-projects`; host paths `/opt/model-monitor/langfuse-projects/` and `/opt/model-monitor/langfuse-generated/{routes.yaml,projects.env}`.

- [ ] **Step 1: Write the failing tests.** Add to `backend/tests/test_langfuse_projects.py`:

```python
def test_committed_local_routes_file_is_generated():
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "deploy" / "compose" / "otel-collector.routes.local.yaml"
    assert path.read_text(encoding="utf-8") == lp.render_routes(["unrouted", "rtr-fraud-validation"])
```

Add to `backend/tests/test_compose_files.py` (replace the old asserts on `LANGFUSE_OTLP_AUTH`, `LANGFUSE_PUBLIC_KEY`, `CHECK_LANGFUSE_PUBLIC_KEY` and the old Collector command wherever an existing test checks them):

```python
def test_collector_loads_base_and_routes():
    base = _load("compose.yaml")["services"]["collector"]
    assert base["command"] == ["--config=/etc/otelcol/config.yaml",
                               "--config=/etc/otelcol/routes.yaml"]
    local = _load("compose.local.yaml")["services"]["collector"]
    assert "./otel-collector.routes.local.yaml:/etc/otelcol/routes.yaml:ro" in local["volumes"]
    env = local["environment"]
    assert set(k for k in env if k.startswith("LANGFUSE_OTLP_AUTH__")) == {
        "LANGFUSE_OTLP_AUTH__UNROUTED", "LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION"}
    host = _load("compose.testhost.yaml")["services"]["collector"]
    assert "/opt/model-monitor/langfuse-generated/routes.yaml:/etc/otelcol/routes.yaml:ro" in host["volumes"]
    assert {"path": "/opt/model-monitor/langfuse-generated/projects.env",
            "required": False} in host["env_file"]


def test_base_collector_config_routes_to_langfuse():
    import yaml as _yaml
    text = (COMPOSE / "otel-collector.yaml").read_text(encoding="utf-8")
    cfg = _yaml.safe_load(text)
    assert "otlphttp/langfuse" not in cfg["exporters"]
    assert cfg["service"]["pipelines"]["traces"]["exporters"] == ["debug", "file", "routing/langfuse"]


def test_langfuse_projects_tool_service():
    base = _load("compose.yaml")["services"]["langfuse-projects"]
    assert base["profiles"] == ["tools"]
    assert base["entrypoint"] == ["python", "scripts/langfuse_projects.py"]
    assert base["networks"] == ["default", "edge"]
    host = _load("compose.testhost.yaml")["services"]["langfuse-projects"]
    assert host["user"] == "0:0"
    assert set(host["volumes"]) == {
        "/opt/model-monitor/langfuse-projects:/projects",
        "/opt/model-monitor/langfuse-generated:/generated",
        "/opt/langfuse/langfuse.env:/langfuse.env:ro"}


def test_backend_and_trace_check_read_projects_env_on_the_test_host():
    host = _load("compose.testhost.yaml")["services"]
    entry = {"path": "/opt/model-monitor/langfuse-generated/projects.env", "required": False}
    for name in ("backend", "trace-check"):
        assert entry in host[name]["env_file"], name


def test_local_project_keys():
    local = _load("compose.local.yaml")["services"]
    for name in ("backend", "trace-check"):
        env = local[name]["environment"]
        assert env["LANGFUSE_PROJECTS"] == "unrouted,rtr-fraud-validation"
        for slug in ("UNROUTED", "RTR_FRAUD_VALIDATION"):
            assert env[f"LANGFUSE_PK__{slug}"] == "pk-lf-local-00000000-0000-0000-0000-000000000000"
            assert env[f"LANGFUSE_SK__{slug}"] == "sk-lf-local-00000000-0000-0000-0000-000000000000"


def test_add_langfuse_project_wrapper():
    text = (COMPOSE / "add-langfuse-project.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n") and "\r\n" not in text
    assert "set -euo pipefail" in text
    for word in ("/opt/model-monitor/langfuse-projects", "/opt/model-monitor/langfuse-generated",
                 ".incoming.keys", "--profile tools run --rm -T langfuse-projects",
                 "--from-langfuse-env /langfuse.env", "--force-recreate collector backend"):
        assert word in text, word
```

Note: on the test host the env-file entries become lists that mix strings and `{path, required}` mappings; if an existing test asserts `env_file == ["/opt/model-monitor/backend.env"]` exactly, change it to check membership instead.

- [ ] **Step 2: Run the tests and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_langfuse_projects.py -q`
Expected: FAIL.

- [ ] **Step 3: Change `deploy/compose/otel-collector.yaml`.** Remove the `otlphttp/langfuse` exporter block and its comment. Change the `traces` pipeline's `exporters` to `[debug, file, routing/langfuse]`. Update the header comment: "Writes the spans to the log, to /data/spans.jsonl (rotated) and, through the connector routing/langfuse (defined in the routes file, S2-03b), to the Langfuse project of each span's use case."

- [ ] **Step 4: Generate and commit the local routes file.** From `backend/`:

```
.venv\Scripts\python.exe scripts/langfuse_projects.py routes --use-cases unrouted,rtr-fraud-validation --output ../deploy/compose/otel-collector.routes.local.yaml
```

- [ ] **Step 5: Change the Compose files.**

`compose.yaml`, service `collector`: `command: ["--config=/etc/otelcol/config.yaml", "--config=/etc/otelcol/routes.yaml"]`. Add after `trace-check`:

```yaml
  # S2-03b project tool: a one-shot service, never started by `up` (profile tools). Run it
  # with deploy/compose/add-langfuse-project.sh on the test host.
  langfuse-projects:
    profiles: ["tools"]
    entrypoint: ["python", "scripts/langfuse_projects.py"]
    restart: "no"
    networks: [default, edge]
```

`compose.local.yaml`:
- `collector.volumes`: `["./otel-collector.routes.local.yaml:/etc/otelcol/routes.yaml:ro"]`; `collector.environment`: replace `LANGFUSE_OTLP_AUTH` with `LANGFUSE_OTLP_AUTH__UNROUTED` and `LANGFUSE_OTLP_AUTH__RTR_FRAUD_VALIDATION`, both the same local value as before.
- `backend.environment`: replace `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` with `LANGFUSE_PROJECTS: unrouted,rtr-fraud-validation` and `LANGFUSE_PK__UNROUTED`, `LANGFUSE_SK__UNROUTED`, `LANGFUSE_PK__RTR_FRAUD_VALIDATION`, `LANGFUSE_SK__RTR_FRAUD_VALIDATION` (the local test keys; comment "local test values").
- `trace-check.environment`: the same five values; keep `CHECK_LANGFUSE_URL` and `CHECK_DATABASE_URL`; remove `CHECK_LANGFUSE_PUBLIC_KEY` / `SECRET_KEY`.
- Add `langfuse-projects: {image: model-monitor-backend:local}`.

`compose.testhost.yaml`:
- `collector`: `volumes: ["/opt/model-monitor/langfuse-generated/routes.yaml:/etc/otelcol/routes.yaml:ro"]`; add `{path: /opt/model-monitor/langfuse-generated/projects.env, required: false}` to its `env_file`.
- `backend` and `trace-check`: add the same `env_file` entry.
- Add:

```yaml
  langfuse-projects:
    image: ${BACKEND_IMAGE:?BACKEND_IMAGE is not set}
    user: "0:0"
    volumes:
      - /opt/model-monitor/langfuse-projects:/projects
      - /opt/model-monitor/langfuse-generated:/generated
      - /opt/langfuse/langfuse.env:/langfuse.env:ro
```

- [ ] **Step 6: Write `deploy/compose/add-langfuse-project.sh`:**

```bash
#!/usr/bin/env bash
# S2-03b, test host only: add a Langfuse project for a use case, or rebuild the routes.
#   sudo bash add-langfuse-project.sh <use_case_id> --keys-file <path>   keys from the Langfuse UI
#   sudo bash add-langfuse-project.sh unrouted --from-langfuse-env       today's project keys
#   sudo bash add-langfuse-project.sh --regenerate | --list
# The keys file needs LANGFUSE_PUBLIC_KEY= and LANGFUSE_SECRET_KEY=; it is deleted.
# Prints names only. Then restart the Collector and the backend (the command is printed).
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "run with sudo" >&2; exit 1; }
cd "$(dirname "$0")"
PROJECTS=/opt/model-monitor/langfuse-projects
GENERATED=/opt/model-monitor/langfuse-generated
install -d -m 700 "$PROJECTS"
install -d -m 755 "$GENERATED"
RUN=(docker compose -f compose.yaml -f compose.testhost.yaml --profile tools run --rm -T langfuse-projects)
usage() { sed -n '2,7p' "$0" >&2; exit 2; }
trap 'rm -f "$PROJECTS/.incoming.keys"' EXIT
case "${1:-}" in
  --regenerate) "${RUN[@]}" regenerate ;;
  --list) "${RUN[@]}" list; exit 0 ;;
  ""|-*) usage ;;
  *)
    UC="$1"; shift
    case "${1:-}" in
      --keys-file)
        SRC="${2:-}"
        [ -s "$SRC" ] || { echo "the keys file is missing or empty" >&2; exit 1; }
        install -m 600 "$SRC" "$PROJECTS/.incoming.keys"
        rm -f "$SRC"
        "${RUN[@]}" add "$UC" --keys-file /projects/.incoming.keys ;;
      --from-langfuse-env)
        "${RUN[@]}" add "$UC" --from-langfuse-env /langfuse.env ;;
      *) usage ;;
    esac ;;
esac
echo "Now restart: sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate collector backend"
```

- [ ] **Step 7: Run the tests and make sure they pass, then the full fast suite.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_compose_files.py tests/test_langfuse_projects.py -q`, then `.venv\Scripts\python.exe -m pytest -q -m "not slow"`.
Expected: PASS.

- [ ] **Step 8: Commit** (Claude): `feat(s2-03b): Collector routes, Compose tool service and wrapper` (and `git update-index --chmod=+x deploy/compose/add-langfuse-project.sh`)

---

### Task 6: CI — routing test and smoke

**Files:**
- Create: `scripts/collector-routing-test.sh`, `.github/workflows/collector-routing.yml`
- Modify: `scripts/langfuse-smoke.sh`, `.github/workflows/langfuse-smoke.yml` (paths)
- Test: `backend/tests/test_langfuse_files.py` (or `test_compose_files.py`)

- [ ] **Step 1: Write the failing tests** (add to `backend/tests/test_langfuse_files.py`):

```python
def test_collector_routing_test_script():
    text = (ROOT / "scripts" / "collector-routing-test.sh").read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n") and "set -euo pipefail" in text
    assert "otel/opentelemetry-collector-contrib:0.161.0" in text
    assert "routes --use-cases unrouted,rtr-fraud-validation --exporter file" in text
    for case in ("resource-label", "span-label", "service-name", "no-label", "resource-wins"):
        assert case in text, case
    wf = (ROOT / ".github" / "workflows" / "collector-routing.yml").read_text(encoding="utf-8")
    assert "bash scripts/collector-routing-test.sh" in wf
    for path in ("backend/app/langfuse_projects.py", "backend/scripts/langfuse_projects.py",
                 "deploy/compose/otel-collector.yaml", "scripts/collector-routing-test.sh"):
        assert path in wf, path


def test_langfuse_smoke_checks_the_project():
    text = SMOKE.read_text(encoding="utf-8")
    assert "observations in Langfuse project rtr-fraud-validation" in text
```

(Use the names `ROOT` and `SMOKE` that the file already defines.)

- [ ] **Step 2: Run them and make sure they fail.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py -q`
Expected: FAIL.

- [ ] **Step 3: Write `scripts/collector-routing-test.sh`:**

```bash
#!/usr/bin/env bash
# S2-03b: proves the Collector routing with the real Collector image, without Langfuse.
# The project tool renders the routes with file exporters; spans with each label case are
# sent; each must land in the file of the right project. Linux CI; needs docker, python3.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="otel/opentelemetry-collector-contrib:0.161.0"
WORK="$(mktemp -d)"
NAME="routing-test-$$"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT
mkdir -p "$WORK/out"; chmod 777 "$WORK/out"

python3 "$ROOT/backend/scripts/langfuse_projects.py" routes --use-cases unrouted,rtr-fraud-validation --exporter file --file-dir /out --output "$WORK/routes.yaml"
cat > "$WORK/base.yaml" <<'YAML'
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [routing/langfuse]
YAML
docker run -d --name "$NAME" -p 127.0.0.1:14318:4318 -v "$WORK:/cfg:ro" -v "$WORK/out:/out" \
  "$IMAGE" --config=/cfg/base.yaml --config=/cfg/routes.yaml >/dev/null
for i in $(seq 1 30); do
  curl -s -o /dev/null -X POST http://127.0.0.1:14318/v1/traces -H 'Content-Type: application/json' --data '{"resourceSpans":[]}' && break
  [ "$i" = "30" ] && { docker logs "$NAME"; echo "Collector did not start"; exit 1; }
  sleep 1
done

send() {  # send <span name> <resource attrs json> <span attrs json>
  python3 - "$1" "$2" "$3" > "$WORK/body.json" <<'PY'
import json, secrets, sys, time
name, res, attrs = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
kv = lambda d: [{"key": k, "value": {"stringValue": v}} for k, v in d.items()]
now = time.time_ns()
print(json.dumps({"resourceSpans": [{"resource": {"attributes": kv(res)}, "scopeSpans": [{
    "scope": {"name": "routing-test"}, "spans": [{"traceId": secrets.token_hex(16),
    "spanId": secrets.token_hex(8), "name": name, "kind": 1,
    "startTimeUnixNano": str(now), "endTimeUnixNano": str(now + 1000),
    "attributes": kv(attrs)}]}]}]}))
PY
  curl -fsS -o /dev/null -X POST http://127.0.0.1:14318/v1/traces -H 'Content-Type: application/json' --data-binary "@$WORK/body.json"
}
send resource-label '{"service.name":"x","use.case.id":"rtr-fraud-validation"}' '{}'
send span-label '{"service.name":"model-monitor"}' '{"use_case_id":"rtr-fraud-validation"}'
send service-name '{"service.name":"rtr-fraud-validation"}' '{}'
send no-label '{"service.name":"model-monitor"}' '{}'
send resource-wins '{"service.name":"x","use.case.id":"other-use-case"}' '{"use_case_id":"rtr-fraud-validation"}'
sleep 3
docker stop "$NAME" >/dev/null   # flush the file exporters
expect() {  # expect <span name> <project>
  grep -q "\"$1\"" "$WORK/out/$2.jsonl" || { echo "FAIL: $1 is not in $2"; cat "$WORK/out/"*.jsonl || true; exit 1; }
}
expect resource-label rtr-fraud-validation
expect span-label rtr-fraud-validation
expect service-name rtr-fraud-validation
expect no-label unrouted
expect resource-wins unrouted
if grep -q '"no-label"\|"resource-wins"' "$WORK/out/rtr-fraud-validation.jsonl"; then echo "FAIL: unrouted spans in rtr-fraud-validation"; exit 1; fi
echo "ROUTING PASS"
```

The tool needs PyYAML and Pydantic; in the workflow install the backend requirements first.

- [ ] **Step 4: Write `.github/workflows/collector-routing.yml`:**

```yaml
name: Collector routing test

on:
  pull_request:
    paths:
      - "backend/app/langfuse_projects.py"
      - "backend/scripts/langfuse_projects.py"
      - "deploy/compose/otel-collector.yaml"
      - "deploy/compose/otel-collector.routes.local.yaml"
      - "scripts/collector-routing-test.sh"
      - ".github/workflows/collector-routing.yml"
  push:
    branches: [dev]
    paths:
      - "backend/app/langfuse_projects.py"
      - "backend/scripts/langfuse_projects.py"
      - "deploy/compose/otel-collector.yaml"
      - "deploy/compose/otel-collector.routes.local.yaml"
      - "scripts/collector-routing-test.sh"
      - ".github/workflows/collector-routing.yml"

permissions:
  contents: read

jobs:
  routing:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install -r backend/requirements.txt
      - run: bash scripts/collector-routing-test.sh
```

- [ ] **Step 5: Change `scripts/langfuse-smoke.sh`.** After the first `grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"`, add `grep -q "observations in Langfuse project rtr-fraud-validation" <<<"$OUT"`. In `.github/workflows/langfuse-smoke.yml`, add to both `paths` lists: `"backend/app/langfuse_projects.py"`, `"deploy/compose/otel-collector.routes.local.yaml"`, `"deploy/compose/compose.local.yaml"`.

- [ ] **Step 6: Run the tests and make sure they pass.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_langfuse_files.py tests/test_compose_files.py -q`
Expected: PASS.

- [ ] **Step 7: Commit** (Claude): `test(s2-03b): CI routing test with the real Collector; smoke checks the project` (and `git update-index --chmod=+x scripts/collector-routing-test.sh`)

---

### Task 7: Docs

**Files:**
- Modify: `deploy/compose/TESTHOST.md`, `CHANGELOG.md`, `DEVLOG.md`, `changes/2026-10-02-batch-monitoring-mvp/issues.md`

- [ ] **Step 1: TESTHOST — add the section "Langfuse projects per use case (S2-03b)"** after "Dashboard (S2-07)", with two parts:

```markdown
## Langfuse projects per use case (S2-03b)

Each use case has its own Langfuse project, named exactly its `use_case_id`. Spans with no
known use case go to the project `unrouted`. Project files (the keys) are in
`/opt/model-monitor/langfuse-projects/` (700, files 600); the tool generates
`/opt/model-monitor/langfuse-generated/routes.yaml` and `projects.env`. Never edit the
generated files.

### The switch (one time)

1. Copy `deploy/compose/` (compose files, `otel-collector.yaml`, `add-langfuse-project.sh`) to
   `/opt/model-monitor/compose/`, and set `BACKEND_IMAGE` and `DASHBOARD_IMAGE` to the build
   that contains S2-03b; `pull`.
2. In the Langfuse UI (tunnel to 3000): Settings of the project `model-monitor` → rename it
   to `unrouted`.
3. On the VM:

   ```sh
   sudo bash /opt/model-monitor/compose/add-langfuse-project.sh unrouted --from-langfuse-env
   ```

4. Add `rtr-fraud-validation` with the steps below, then restart:

   ```sh
   cd /opt/model-monitor/compose && sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate --wait collector backend
   ```

5. After the next RTR run: `check-trace.sh <trace_id>` shows `5 of 5` and
   `observations in Langfuse project rtr-fraud-validation`.

### Add a project for a use case (about 2 minutes)

1. The use case must be in `backend/registry/batch-use-cases.yaml` (deployed).
2. Langfuse UI → New project, named exactly the `use_case_id` → Settings → API keys →
   Create. In a new file on the VM (for example with VS Code), write
   `LANGFUSE_PUBLIC_KEY=<pk-lf-…>` and `LANGFUSE_SECRET_KEY=<sk-lf-…>`. Never paste keys in chat.
3. Run, then restart as the script prints:

   ```sh
   sudo bash /opt/model-monitor/compose/add-langfuse-project.sh <use_case_id> --keys-file <path>
   ```

   The script checks that the keys belong to the project `<use_case_id>`, writes the
   project file, regenerates the routes, and deletes the keys file. `--list` shows the
   projects; `--regenerate` rebuilds after a project file is removed.
4. Add the team members to the project in the Langfuse UI.
```

- [ ] **Step 2: CHANGELOG** — under "Unreleased" / "Added", first item:

```markdown
- One Langfuse project for each use case (S2-03b, #96): the Collector routes every span to the
  project named its `use_case_id` (resource `use.case.id`, else span `use_case_id`, else a
  registered `service.name`); others go to `unrouted`. The backend labels its server span;
  the evaluator and the trace check use the run's project. Projects are created in the
  Langfuse UI; `add-langfuse-project.sh` checks the keys and regenerates the routes. New CI
  test `collector-routing`.
```

- [ ] **Step 3: DEVLOG** — add at the top of "Work log" (em dash `—`):

```markdown
### 2026-10-15 — S2-03b: one Langfuse project per use case

- Built (Codex task by task from `changes/2026-10-15-langfuse-projects/plan.md`, reviewed by
  Claude after each task): `app/langfuse_projects.py`, `scripts/langfuse_projects.py`, the
  routes file and the `routing/langfuse` connector, the server-span label, per-project
  scores and trace check, `add-langfuse-project.sh`, CI `collector-routing`.
- Decisions: access per team; project name = `use_case_id`; `unrouted` for the rest; routing
  resource label, then span label, then `service.name`; one YAML file per project;
  projects created in the UI (the project API needs Langfuse Enterprise).
- Evidence: (Claude fills in after the review).
```

- [ ] **Step 4: issues.md** — under S2-03, add a line: "**S2-03b (#96, 2026-10-15):** one Langfuse project per use case; design in `changes/2026-10-15-langfuse-projects/`." Under S2-04, add: "The OTel helper sets the resource label `use.case.id` (S2-03b routing)."

- [ ] **Step 5: Run the docs tests.**
Run: `.venv\Scripts\python.exe -m pytest tests/test_docs.py tests/test_compose_files.py -q`
Expected: PASS.

- [ ] **Step 6: Commit** (Claude): `docs(s2-03b): project runbook, changelog and devlog`
