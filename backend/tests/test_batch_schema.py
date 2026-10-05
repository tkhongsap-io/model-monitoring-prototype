"""Run summary `batch-run/1` (S1-01 draft) as the backend enforces it (S1-02).

The examples are read from the S1-01 change folder, so the schema draft and these tests
cannot drift apart while the GCP developer reviews it.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.batch_schema import BatchRunInvalid, validate_run

EXAMPLES = (Path(__file__).resolve().parents[2] / "changes" / "2026-10-02-batch-monitoring-mvp"
            / "schema" / "examples")
VALID = sorted((EXAMPLES / "valid").glob("*.json"))
INVALID = sorted((EXAMPLES / "invalid").glob("*.json"))


def example(name: str) -> dict:
    return json.loads((EXAMPLES / "valid" / name).read_text(encoding="utf-8"))


def raw(body: dict) -> bytes:
    return json.dumps(body).encode("utf-8")


def errors_for(body: dict | bytes) -> list[dict]:
    with pytest.raises(BatchRunInvalid) as caught:
        validate_run(body if isinstance(body, bytes) else raw(body))
    return caught.value.errors


def locs(errors: list[dict]) -> list[tuple]:
    return [tuple(e["loc"]) for e in errors]


def test_examples_are_present():
    assert len(VALID) == 5 and len(INVALID) == 3


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_examples_pass(path):
    run = validate_run(path.read_bytes())
    assert run.schema_version == "batch-run/1"


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_examples_fail(path):
    assert errors_for(path.read_bytes())


def test_invalid_examples_name_the_field():
    assert ("run_id",) in locs(errors_for((EXAMPLES / "invalid" / "missing-run-id.json").read_bytes()))
    unknown = errors_for((EXAMPLES / "invalid" / "unknown-field-customer-id.json").read_bytes())
    assert ("records", 0, "customer_id") in locs(unknown)
    wrong = locs(errors_for((EXAMPLES / "invalid" / "wrong-type-and-zero-latency.json").read_bytes()))
    assert ("request_count",) in wrong and ("records", 0, "latency_s") in wrong


def test_errors_never_echo_the_input():
    body = example("01-completed-online.json")
    body["records"][0]["latency_s"] = "SECRET-TEXT-[EMAIL]"
    body["unexpected"] = "SECRET-TEXT-[PHONE]"
    body["completed_at"] = "2026-13-40T02:15:00Z"
    body["run_id"] = "SECRET-TEXT with space"
    errors = errors_for(body)
    assert "SECRET-TEXT" not in json.dumps(errors)
    assert all(set(e) == {"loc", "msg", "type"} for e in errors)


def test_not_json_is_an_error():
    assert errors_for(b"{not json")
    assert errors_for(b"[]")


# ---- schema rules ---------------------------------------------------------------

def test_missing_record_field():
    body = example("01-completed-online.json")
    del body["records"][1]["retrieval_context"]
    assert ("records", 1, "retrieval_context") in locs(errors_for(body))


def test_latency_is_required_and_never_zero():
    body = example("01-completed-online.json")
    del body["records"][0]["latency_s"]
    assert ("records", 0, "latency_s") in locs(errors_for(body))
    body = example("01-completed-online.json")
    body["records"][0]["latency_s"] = 0
    assert ("records", 0, "latency_s") in locs(errors_for(body))
    body["records"][0]["latency_s"] = -1.5
    assert ("records", 0, "latency_s") in locs(errors_for(body))
    body["records"][0]["latency_s"] = 2                 # a JSON integer is a number
    validate_run(raw(body))


def test_strict_types():
    body = example("01-completed-online.json")
    body["records"][0]["refused"] = 0
    assert ("records", 0, "refused") in locs(errors_for(body))
    body = example("01-completed-online.json")
    body["failed_count"] = True
    assert ("failed_count",) in locs(errors_for(body))


@pytest.mark.parametrize("field, value", [
    ("schema_version", "batch-run/2"),
    ("status", "done"),
    ("completed_at", "2026-10-07T02:15:00+07:00"),
    ("completed_at", "2026-10-07 02:15:00Z"),
    ("completed_at", "2026-13-40T02:15:00Z"),
    ("run_id", "has space"),
    ("run_id", ""),
    ("use_case_id", "-starts-with-dash"),
    ("model", ""),
    ("request_count", -1),
])
def test_top_level_field_rules(field, value):
    body = example("04-identity-only.json")
    body[field] = value
    assert (field,) in locs(errors_for(body))


def test_unknown_fields_rejected_at_every_level():
    for mutate, loc in [
        (lambda b: b.update(trace_id="abc"), ("trace_id",)),
        (lambda b: b["sample"].update(seed=7), ("sample", "seed")),
        (lambda b: b["records"][0]["retrieval_context"][0].update(score=0.9),
         ("records", 0, "retrieval_context", 0, "score")),
        (lambda b: b["records"][1]["tool_calls"][0].update(input={}),
         ("records", 1, "tool_calls", 0, "input")),
    ]:
        body = example("01-completed-online.json")
        mutate(body)
        assert loc in locs(errors_for(body)), loc


def test_sample_rules():
    body = example("04-identity-only.json")
    body["sample"]["method"] = "stratified"
    assert ("sample", "method") in locs(errors_for(body))
    body = example("04-identity-only.json")
    body["sample"]["size"] = 201
    assert ("sample", "size") in locs(errors_for(body))


def test_answer_may_be_empty_only_when_refused():
    body = example("02-partial-failure.json")
    validate_run(raw(body))                     # record 1: answer "" with refused true
    body["records"][1]["refused"] = False
    assert ("records", 1, "answer") in locs(errors_for(body))


def test_question_and_text_lengths():
    body = example("01-completed-online.json")
    body["records"][0]["question"] = ""
    assert ("records", 0, "question") in locs(errors_for(body))
    body = example("01-completed-online.json")
    body["records"][0]["retrieval_context"][0]["text"] = ""
    assert ("records", 0, "retrieval_context", 0, "text") in locs(errors_for(body))


def test_zero_requests_means_no_records():
    body = example("01-completed-online.json")
    body["request_count"] = 0
    assert ("records",) in locs(errors_for(body))


def test_empty_records_with_requests_need_a_reason():
    body = example("04-identity-only.json")
    del body["records_reason"]
    assert ("records_reason",) in locs(errors_for(body))
    body["request_count"] = 0
    body["failed_count"] = 0
    validate_run(raw(body))                     # no requests: no reason needed


def test_records_present_means_no_reason():
    body = example("01-completed-online.json")
    body["records_reason"] = "records_not_approved"
    assert ("records_reason",) in locs(errors_for(body))


def test_failed_run_rules():
    body = example("05-failed-run.json")
    body["records_reason"] = "records_not_approved"
    assert ("records_reason",) in locs(errors_for(body))
    body = example("05-failed-run.json")
    body["records"] = copy.deepcopy(example("01-completed-online.json")["records"])
    del body["records_reason"]
    assert ("records",) in locs(errors_for(body))
    body = example("04-identity-only.json")
    body["records_reason"] = "job_failed"           # not failed: job_failed not allowed
    assert ("records_reason",) in locs(errors_for(body))


# ---- backend rules (schema README: JSON Schema cannot express them) --------------

def test_failed_count_not_more_than_request_count():
    body = example("04-identity-only.json")
    body["failed_count"] = body["request_count"] + 1
    assert ("failed_count",) in locs(errors_for(body))


def test_records_not_more_than_sample_size():
    body = example("01-completed-online.json")
    body["sample"]["size"] = 1
    assert ("records",) in locs(errors_for(body))


def test_records_not_more_than_request_count():
    body = example("03-batch-api-null-latency.json")
    body["request_count"] = 1
    assert ("records",) in locs(errors_for(body))


def test_record_id_unique_in_run():
    body = example("01-completed-online.json")
    body["records"][1]["record_id"] = body["records"][0]["record_id"]
    assert ("records", 1, "record_id") in locs(errors_for(body))


def test_records_keep_their_order_and_ids():
    run = validate_run(raw(example("01-completed-online.json")))
    assert [r.record_id for r in run.records] == ["req-000412", "req-001207"]
    assert run.records[1].tool_calls[0].output == {"plan": "Mobile 399", "months": 1}
