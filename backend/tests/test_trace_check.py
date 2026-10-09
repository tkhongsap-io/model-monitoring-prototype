"""S1-07: the pure check logic of the trace check tool."""
from __future__ import annotations

from app.trace_check import (FOUND, MISSING, SKIPPED, RunRow, Span, check, render,
                             stored_trace_ids)

T = "4bf92f3577b34da6a3ce929d0e0e4736"
OTHER = "0af7651916cd43dd8448eb211c80319c"
NS = 1_791_442_803_000_000_000          # 2026-10-08T07:00:03Z


def span(name, span_id, parent="", **attributes):
    return Span(trace_id=T, span_id=span_id, parent_span_id=parent, name=name,
                start_ns=NS, attributes=attributes)


def row(trace_source="traceparent"):
    return RunRow(use_case_id="rtr-fraud-validation", run_id="run-20261008-01",
                  status="succeeded", completed_at="2026-10-08T06:59:00Z",
                  received_at=NS / 1e9, trace_id_source=trace_source)


def full_trace():
    return [
        span("batch.run", "a1", "", use_case_id="rtr-fraud-validation", run_id="run-20261008-01"),
        span("batch.send", "a2", "a1"),
        span("POST", "a3", "a2"),
        span("POST /api/batch/runs", "b1", "a3"),
        span("monitor.ingest", "b2", "b1", outcome="stored"),
    ]


def states(result):
    return {item.name: item.state for item in result.items}


def detail(result, name):
    return next(item.detail for item in result.items if item.name == name)


def test_all_four_found_with_the_path():
    result = check(T, [row()], full_trace(), backend_only=False)
    assert states(result) == {"run row": FOUND, "monitor span": FOUND,
                              "gcp root span": FOUND, "ancestor link": FOUND}
    assert result.ok
    assert detail(result, "ancestor link") == \
        "monitor.ingest → POST /api/batch/runs → POST → batch.send"
    assert "rtr-fraud-validation / run-20261008-01" in detail(result, "run row")
    assert "received 2026-10-08T07:00:03Z" in detail(result, "run row")


def test_each_item_missing_alone():
    spans = full_trace()
    no_root = [s for s in spans if s.name != "batch.run"]
    assert states(check(T, [row()], no_root, backend_only=False))["gcp root span"] == MISSING
    no_row = check(T, [], spans, backend_only=False)
    assert states(no_row)["run row"] == MISSING
    assert detail(no_row, "run row") == \
        "monitor.ingest says stored, but no run row has this trace ID"
    no_ingest = [s for s in spans if s.name != "monitor.ingest"]
    result = check(T, [row()], no_ingest, backend_only=False)
    assert states(result)["monitor span"] == MISSING
    assert detail(result, "ancestor link") == "no monitor.ingest span"
    assert not result.ok


def test_duplicate_found_only_when_the_stored_row_exists():
    spans = [span("monitor.ingest", "b2", "b1", outcome="duplicate", stored_trace_id=OTHER)]
    assert stored_trace_ids(spans) == [OTHER]
    found = check(T, [], spans, backend_only=True, stored_rows={OTHER: [row()]})
    assert states(found)["run row"] == FOUND
    assert detail(found, "run row") == f"duplicate delivery; the run is stored under trace {OTHER}"
    missing = check(T, [], spans, backend_only=True, stored_rows={})
    assert states(missing)["run row"] == MISSING
    assert detail(missing, "run row") == f"duplicate delivery, but trace {OTHER} has no run row"


def test_conflict_is_missing_with_and_without_stored_trace_id():
    with_id = [span("monitor.ingest", "b2", "", outcome="conflict", stored_trace_id=OTHER)]
    result = check(T, [], with_id, backend_only=True)
    assert states(result)["run row"] == MISSING
    assert detail(result, "run row") == \
        f"rejected: another body is stored for this run_id under trace {OTHER}"
    without = [span("monitor.ingest", "b2", "", outcome="conflict")]
    assert detail(check(T, [], without, backend_only=True), "run row") == \
        "rejected: another body is stored for this run_id"


def test_other_outcome_is_missing_with_the_outcome():
    spans = [span("monitor.ingest", "b2", "", outcome="invalid")]
    result = check(T, [], spans, backend_only=True)
    assert detail(result, "run row") == "the backend did not store the run (outcome invalid)"


def test_chain_stops_at_a_missing_parent_or_a_root():
    spans = [span("POST /api/batch/runs", "b1", "ffffffffffffffff"),
             span("monitor.ingest", "b2", "b1", outcome="stored")]
    result = check(T, [row()], spans, backend_only=False)
    assert detail(result, "ancestor link") == \
        "the chain stops at POST /api/batch/runs: parent ffffffffffffffff is not in the file"
    rootless = [span("monitor.ingest", "b2", "", outcome="stored")]
    assert detail(check(T, [row()], rootless, backend_only=False), "ancestor link") == \
        "the chain stops at monitor.ingest: it has no parent"


def test_chain_loop_does_not_hang():
    spans = [span("x", "c1", "c2"), span("y", "c2", "c1"),
             span("monitor.ingest", "b2", "c1", outcome="stored")]
    result = check(T, [row()], spans, backend_only=False)
    assert states(result)["ancestor link"] == MISSING
    assert detail(result, "ancestor link").startswith("the chain stops at ")


def test_retry_two_ingest_spans_one_chain_reaches_batch_send():
    spans = full_trace() + [span("monitor.ingest", "b9", "zz", outcome="duplicate",
                                 stored_trace_id=T)]
    result = check(T, [row()], spans, backend_only=False)
    assert states(result)["ancestor link"] == FOUND
    assert detail(result, "monitor span").count("outcome ") == 2


def test_backend_only_skips_the_gcp_items():
    result = check(T, [row()], full_trace(), backend_only=True)
    assert states(result)["gcp root span"] == SKIPPED
    assert states(result)["ancestor link"] == SKIPPED
    assert len(result.checked) == 2 and result.ok


def test_render_result_line_note_and_no_other_attributes():
    spans = full_trace()
    spans[-1] = span("monitor.ingest", "b2", "b1", outcome="stored",
                     **{"http.request.header.authorization": "Bearer SECRET"})
    text = render(check(T, [row()], spans, backend_only=True, skipped_lines=3))
    lines = text.splitlines()
    assert lines[0] == f"trace {T}"
    assert lines[-2] == "note: 3 span file line(s) could not be read"
    assert lines[-1] == "RESULT: OK (2 of 2 found)"
    assert "SECRET" not in text
    missing = render(check(T, [], [], backend_only=False))
    assert missing.splitlines()[-1] == "RESULT: MISSING (0 of 4 found)"
