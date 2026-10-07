"""scripts/strip_record_text.py removes the free text of a batch-run/1 body and keeps the rest.

All text here is synthetic.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "strip_record_text.py"
_spec = importlib.util.spec_from_file_location("strip_record_text", SCRIPT)
strip_record_text = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(strip_record_text)

SECRET_Q = "SECRET-QUESTION call [PHONE] about the account"
SECRET_A = "SECRET-ANSWER send to [EMAIL] and [EMAIL]"
SECRET_CTX = "SECRET-CONTEXT national id [NATIONAL_ID]"
SECRET_TOOL = {"note": "SECRET-TOOL output"}

BODY = {
    "schema_version": "batch-run/1",
    "use_case_id": "GCP-UC-03",
    "run_id": "run-2026-10-07",
    "status": "partial",
    "completed_at": "2026-10-07T08:09:52Z",
    "request_count": 349,
    "failed_count": 106,
    "model": "gemini-2.5-flash",
    "sample": {"method": "uniform_random", "size": 50},
    "records": [
        {
            "record_id": "req-000047",
            "question": "[IMAGE] " + SECRET_Q,
            "answer": SECRET_A,
            "retrieval_context": [{"doc_id": "req-000047-input", "title": "SECRET-TITLE", "text": SECRET_CTX}],
            "tool_calls": [{"name": "lookup_plan", "output": SECRET_TOOL}],
            "refused": False,
            "latency_s": 1.2,
        },
        {
            "record_id": "req-000048",
            "question": "short",
            "answer": "",
            "retrieval_context": [],
            "refused": True,
            "latency_s": None,
        },
    ],
}


def run(tmp_path, capsys, body=BODY, name="run.json"):
    src = tmp_path / name
    src.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    code = strip_record_text.main([str(src)])
    out = capsys.readouterr()
    return code, tmp_path / "run.stripped.json", out.out + out.err


def test_text_removed_and_other_values_kept(tmp_path, capsys):
    code, dst, _ = run(tmp_path, capsys)
    assert code == 0
    raw = dst.read_text(encoding="utf-8")
    assert "SECRET" not in raw
    clean = json.loads(raw)
    for key in BODY:
        if key != "records":
            assert clean[key] == BODY[key]
    first, second = clean["records"]
    assert first["record_id"] == "req-000047" and first["refused"] is False and first["latency_s"] == 1.2
    assert first["retrieval_context"][0]["doc_id"] == "req-000047-input"
    assert first["tool_calls"][0]["name"] == "lookup_plan"
    assert second == {**BODY["records"][1], "question": "[REMOVED 5 chars]"}


def test_marker_keeps_length_and_placeholder_counts(tmp_path, capsys):
    _, dst, _ = run(tmp_path, capsys)
    first = json.loads(dst.read_text(encoding="utf-8"))["records"][0]
    question = "[IMAGE] " + SECRET_Q
    assert first["question"] == f"[REMOVED {len(question)} chars [IMAGE]x1 [PHONE]x1]"
    assert first["answer"] == f"[REMOVED {len(SECRET_A)} chars [EMAIL]x2]"
    assert first["retrieval_context"][0]["text"] == f"[REMOVED {len(SECRET_CTX)} chars [NATIONAL_ID]x1]"


def test_empty_answer_stays_empty(tmp_path, capsys):
    _, dst, _ = run(tmp_path, capsys)
    assert json.loads(dst.read_text(encoding="utf-8"))["records"][1]["answer"] == ""


def test_output_never_prints_text(tmp_path, capsys):
    code, _, printed = run(tmp_path, capsys)
    assert code == 0
    assert "SECRET" not in printed
    assert "2 records, 6 text values removed" in printed


def test_invalid_json_error_has_no_content(tmp_path, capsys):
    src = tmp_path / "bad.json"
    src.write_text('{"question": "SECRET-BROKEN', encoding="utf-8")
    assert strip_record_text.main([str(src)]) == 2
    out = capsys.readouterr()
    assert "SECRET" not in out.out + out.err
    assert "not valid JSON at line 1" in out.err


def test_refuses_to_overwrite_the_input(tmp_path, capsys):
    src = tmp_path / "run.json"
    src.write_text(json.dumps(BODY), encoding="utf-8")
    assert strip_record_text.main([str(src), "-o", str(src)]) == 2
    assert json.loads(src.read_text(encoding="utf-8")) == BODY


@pytest.mark.parametrize("wrapper", ["list", "nested"])
def test_text_removed_in_any_shape(tmp_path, capsys, wrapper):
    body = [BODY] if wrapper == "list" else {"payload": BODY}
    code, dst, _ = run(tmp_path, capsys, body=body)
    assert code == 0
    assert "SECRET" not in dst.read_text(encoding="utf-8")
