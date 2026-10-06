"""Run summary `batch-run/1` — the body a GCP batch job POSTs to /api/batch/runs (S1-02).

DRAFT: this mirrors `changes/2026-10-02-batch-monitoring-mvp/schema/batch-run-1.schema.json`
(S1-01), which the GCP job developer has not approved yet.  Every rule of the schema and
every backend-only rule of its README lives in this one module, so a schema change is a
change here and in its tests only.

Pure: no I/O.  Field errors never carry the input value, because record text can reach
the error list and the body is never logged or echoed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator,
)

SCHEMA_VERSION = "batch-run/1"

Identifier = Annotated[str, StringConstraints(
    min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
_UTC_TIMESTAMP = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$"


class _Strict(BaseModel):
    # strict: "1840" is not an integer and 0 is not a boolean; forbid: unknown fields
    # (for example a customer ID) are rejected at every level.
    model_config = ConfigDict(strict=True, extra="forbid")


class Sample(_Strict):
    method: Literal["uniform_random"]
    size: int = Field(ge=1, le=200)


class RetrievalDoc(_Strict):
    doc_id: Identifier
    title: str = Field(max_length=512)
    text: str = Field(min_length=1, max_length=64000)


class ToolCall(_Strict):
    name: str = Field(min_length=1, max_length=128)
    output: Any


class Record(_Strict):
    record_id: Identifier
    question: str = Field(min_length=1, max_length=32000)
    answer: str = Field(max_length=32000)
    retrieval_context: list[RetrievalDoc] = Field(max_length=20)
    tool_calls: list[ToolCall] | None = Field(default=None, max_length=20)
    refused: bool
    # required, and either a positive number or null (Gemini Batch API); never 0
    latency_s: float | None = Field(gt=0)


class BatchRunV1(_Strict):
    schema_version: Literal["batch-run/1"]
    use_case_id: Identifier
    run_id: Identifier
    status: Literal["completed", "partial", "failed"]
    completed_at: str = Field(pattern=_UTC_TIMESTAMP)
    request_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    model: str = Field(min_length=1, max_length=128)
    sample: Sample
    records: list[Record] = Field(max_length=200)
    records_reason: Literal["records_not_approved", "job_failed"] | None = None

    @field_validator("completed_at")
    @classmethod
    def _real_timestamp(cls, value: str) -> str:
        try:  # the pattern passes 2026-13-40; the calendar does not
            datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("not a valid calendar date and time") from None  # no input echo
        return value

    def rule_errors(self) -> list[dict]:
        """Rules across fields: the schema's `allOf` and the backend rules of its README."""
        errors: list[dict] = []

        def err(loc: tuple, msg: str) -> None:
            errors.append({"loc": list(loc), "msg": msg, "type": "batch_run_rule"})

        n = len(self.records)
        if "records_reason" in self.model_fields_set and self.records_reason is None:
            err(("records_reason",), "must be omitted, not null")
        if self.failed_count > self.request_count:
            err(("failed_count",), "must not be more than request_count")
        if self.request_count == 0 and n:
            err(("records",), "a run with request_count 0 has no records")
        if n > self.sample.size:
            err(("records",), "more records than sample.size")
        if 0 < self.request_count < n:
            err(("records",), "more records than request_count")
        if n == 0 and self.request_count > 0 and self.records_reason is None:
            err(("records_reason",), "required when records is empty and request_count > 0")
        if n and self.records_reason is not None:
            err(("records_reason",), "not allowed when records has items")
        if self.status == "failed":
            if n:
                err(("records",), "a failed run sends no records")
            if self.records_reason not in (None, "job_failed"):
                err(("records_reason",), "must be job_failed when status is failed")
        elif self.records_reason == "job_failed":
            err(("records_reason",), "job_failed is only for status failed")
        seen: set[str] = set()
        for i, record in enumerate(self.records):
            if record.record_id in seen:
                err(("records", i, "record_id"), "record_id is not unique in the run")
            seen.add(record.record_id)
            if not record.refused and record.answer == "":
                err(("records", i, "answer"), "can be empty only when refused is true")
            if "tool_calls" in record.model_fields_set and record.tool_calls is None:
                err(("records", i, "tool_calls"), "must be omitted, not null")
        return errors


class BatchRunInvalid(ValueError):
    """The body does not agree with `batch-run/1`; `errors` is a list of {loc, msg, type}."""

    def __init__(self, errors: list[dict]):
        super().__init__(f"{len(errors)} field error(s)")
        self.errors = errors


def validate_run(raw: bytes) -> BatchRunV1:
    """Parse and validate one request body.  Raises `BatchRunInvalid`."""
    try:
        run = BatchRunV1.model_validate_json(raw)
    except ValidationError as exc:
        raise BatchRunInvalid([
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors(include_url=False, include_input=False, include_context=False)
        ]) from None
    rule_errors = run.rule_errors()
    if rule_errors:
        raise BatchRunInvalid(rule_errors)
    return run
