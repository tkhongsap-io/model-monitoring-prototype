"""Batch use-case registry (S2-01): the reviewed settings of each GCP batch use case.

The file is `backend/registry/batch-use-cases.yaml` (setting `BATCH_REGISTRY_PATH`). The
backend loads it at start and does not start when it has an error. The API key hashes are
not here: they stay in `BATCH_API_KEY_SHA256` of the host env file (scripts/batch_keys.py).
October fields only (identity-only MVP); the task description, the profile and the sample
size come back with SEND_RECORDS, so they are unknown fields until then.
"""
from __future__ import annotations

import re
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
    if isinstance(use_case_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", use_case_id):
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
        if use_case.band_overrides:
            raise RegistryError(
                f"batch registry {path}: use case {use_case.use_case_id}: band_overrides is "
                "not supported yet (S2-05); remove it or wait for support")
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
