"""S1-07: the trace check command (span file, read-only database, exit codes)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert

from app import db

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_trace.py"
spec = importlib.util.spec_from_file_location("check_trace", SCRIPT)
check_trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_trace)

T = "4bf92f3577b34da6a3ce929d0e0e4736"
NS = "1791442803000000000"


def otlp_line(*spans):
    return json.dumps({"resourceSpans": [{"scopeSpans": [{"spans": list(spans)}]}]})


def raw_span(name, span_id, parent="", trace=T, **attributes):
    return {"traceId": trace, "spanId": span_id, "parentSpanId": parent, "name": name,
            "startTimeUnixNano": NS,
            "attributes": [{"key": k, "value": {"stringValue": v}} for k, v in attributes.items()]}


@pytest.fixture()
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'check.db'}"
    engine = create_engine(url)
    db.batch_runs.create(engine)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CHECK_DATABASE_URL", url)
    return engine


def add_row(engine, trace_id=T, run_id="run-1"):
    with engine.begin() as cx:
        cx.execute(insert(db.batch_runs), {
            "batch_run_id": f"check-{run_id}",
            "use_case_id": "rtr-fraud-validation", "run_id": run_id, "schema_version": "1",
            "status": "succeeded", "completed_at": "2026-10-08T06:59:00Z", "request_count": 1,
            "failed_count": 0, "model": "m", "sample_method": "all", "sample_size": 1,
            "records_reason": "records_not_approved", "record_count": 0,
            "content_sha256": "0" * 64, "payload": "{}", "trace_id": trace_id,
            "trace_id_source": "traceparent", "received_at": 1791442803.0})


def spans_file(tmp_path, *lines):
    path = tmp_path / "spans.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def run(argv, **kwargs):
    return check_trace.main(argv, **kwargs)


def test_exit_0_when_backend_items_are_found(database, tmp_path, capsys):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", "b1", outcome="stored")))
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "RESULT: OK (2 of 2 found)"


def test_exit_1_when_an_item_is_missing(database, tmp_path, capsys):
    path = spans_file(tmp_path, otlp_line(raw_span("other", "c1", trace="1" * 32)))
    assert run([T, "--spans-file", path]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "RESULT: MISSING (0 of 4 found)"


def test_upper_case_trace_id_is_accepted(database, tmp_path):
    add_row(database)
    path = spans_file(tmp_path, otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")))
    assert run([T.upper(), "--backend-only", "--spans-file", path]) == 0


@pytest.mark.parametrize("bad", [T[:-1], "g" * 32, "0" * 32, T + "0"])
def test_trace_id_rules(database, tmp_path, bad):
    path = spans_file(tmp_path, "")
    with pytest.raises(SystemExit) as exc:
        run([bad, "--spans-file", path])
    assert exc.value.code == 2


def test_no_check_database_url_is_exit_2(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("CHECK_DATABASE_URL", raising=False)
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    assert "CHECK_DATABASE_URL" in capsys.readouterr().err


def test_database_url_is_never_used(monkeypatch, tmp_path):
    monkeypatch.delenv("CHECK_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'write.db'}")
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    assert not (tmp_path / "write.db").exists()


def test_no_span_file_is_exit_2(database, tmp_path, capsys):
    assert run([T, "--spans-file", str(tmp_path / "absent.jsonl")]) == 2
    captured = capsys.readouterr()
    assert "span file" in captured.err and "RESULT" not in captured.out


def test_broken_lines_are_skipped_and_counted(database, tmp_path, capsys):
    add_row(database)
    good = otlp_line(raw_span("monitor.ingest", "b2", outcome="stored"))
    path = spans_file(tmp_path, "{not json", good, '{"resourceSpans": 5}', '{"resourceSpans": [{"scopeSp')
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    out = capsys.readouterr().out
    assert "note: 3 span file line(s) could not be read" in out


def test_duplicate_reads_the_stored_row(database, tmp_path, capsys):
    other = "0af7651916cd43dd8448eb211c80319c"
    add_row(database, trace_id=other)
    path = spans_file(tmp_path, otlp_line(raw_span(
        "monitor.ingest", "b2", outcome="duplicate", stored_trace_id=other)))
    assert run([T, "--backend-only", "--spans-file", path]) == 0
    assert f"stored under trace {other}" in capsys.readouterr().out


def test_password_never_printed_on_connection_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CHECK_DATABASE_URL",
                       "postgresql://monitor_readonly:S3cretPw-Kq7@127.0.0.1:1/monitor?connect_timeout=2")
    assert run([T, "--spans-file", spans_file(tmp_path, "")]) == 2
    captured = capsys.readouterr()
    assert "S3cretPw" not in captured.out + captured.err
    assert "127.0.0.1" not in captured.err
    assert captured.err.startswith("error: cannot read the database (")


def test_wait_finds_a_span_written_during_the_wait(database, tmp_path):
    add_row(database)
    path = spans_file(tmp_path, "")
    now = [0.0]

    def fake_sleep(seconds):
        now[0] += seconds
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(otlp_line(raw_span("monitor.ingest", "b2", outcome="stored")) + "\n")

    assert run([T, "--backend-only", "--wait", "10", "--spans-file", path],
               sleep=fake_sleep, clock=lambda: now[0]) == 0


def test_wait_ends_with_exit_1(database, tmp_path):
    now = [0.0]

    def fake_sleep(seconds):
        now[0] += seconds

    path = spans_file(tmp_path, "")
    assert run([T, "--wait", "5", "--spans-file", path],
               sleep=fake_sleep, clock=lambda: now[0]) == 1
    assert now[0] >= 5


@pytest.mark.parametrize("line", ['{}', '{"resourceSpans": {}}',
                                  '{"resourceSpans": [{"scopeSpans": {}}]}'])
def test_wrong_shape_lines_are_counted(database, tmp_path, capsys, line):
    path = spans_file(tmp_path, line)
    assert run([T, "--backend-only", "--spans-file", path]) == 1
    assert "note: 1 span file line(s) could not be read" in capsys.readouterr().out


def test_span_file_read_error_is_exit_2(database, monkeypatch, capsys):
    class Unreadable:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def __iter__(self):
            raise OSError("test read error")
    monkeypatch.setattr(check_trace, "open", lambda *args, **kwargs: Unreadable(), raising=False)
    assert run([T]) == 2
    captured = capsys.readouterr()
    assert captured.err == "error: span file /otel/spans.jsonl cannot be read\n"
    assert captured.out == ""


def test_usage_error_is_one_stderr_line(capsys):
    with pytest.raises(SystemExit) as exc:
        run([T, "--wait", "-1"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert len(captured.err.splitlines()) == 1
    assert captured.out == ""
