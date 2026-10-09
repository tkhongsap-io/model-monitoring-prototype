"""S1-07: the check logic of the trace check tool. Pure: no I/O, no database, no files.

`scripts/check_trace.py` reads the run rows and the spans of one trace and prints
`render(check(...))`. The output contains only IDs, span names, outcomes, status values and
times, never other span attributes or body content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

FOUND, MISSING, SKIPPED = "found", "missing", "skipped"
INGEST, SEND, ROOT = "monitor.ingest", "batch.send", "batch.run"


@dataclass(frozen=True)
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str
    name: str
    start_ns: int
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunRow:
    use_case_id: str
    run_id: str
    status: str
    completed_at: str
    received_at: float
    trace_id_source: str


@dataclass(frozen=True)
class Item:
    name: str
    state: str
    detail: str = ""


@dataclass(frozen=True)
class Result:
    trace_id: str
    items: tuple[Item, ...]
    skipped_lines: int = 0

    @property
    def checked(self) -> list[Item]:
        return [item for item in self.items if item.state != SKIPPED]

    @property
    def ok(self) -> bool:
        return all(item.state == FOUND for item in self.checked)


def _iso(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ingests(spans: list[Span]) -> list[Span]:
    return sorted((s for s in spans if s.name == INGEST), key=lambda s: s.start_ns)


def stored_trace_ids(spans: list[Span]) -> list[str]:
    """The stored trace IDs of duplicate deliveries, in time order, without repeats."""
    ids: list[str] = []
    for s in _ingests(spans):
        stored = s.attributes.get("stored_trace_id")
        if s.attributes.get("outcome") == "duplicate" and stored and str(stored) not in ids:
            ids.append(str(stored))
    return ids


def _run_row(rows: list[RunRow], spans: list[Span],
             stored_rows: dict[str, list[RunRow]]) -> Item:
    name = "run row"
    if rows:
        return Item(name, FOUND, "; ".join(
            f"{r.use_case_id} / {r.run_id}, status {r.status}, received {_iso(r.received_at)}, "
            f"trace_id_source {r.trace_id_source}" for r in rows))
    ingests = _ingests(spans)
    for s in ingests:
        stored = s.attributes.get("stored_trace_id")
        if s.attributes.get("outcome") == "duplicate" and stored:
            if stored_rows.get(str(stored)):
                return Item(name, FOUND,
                            f"duplicate delivery; the run is stored under trace {stored}")
            return Item(name, MISSING, f"duplicate delivery, but trace {stored} has no run row")
    for s in ingests:
        if s.attributes.get("outcome") == "conflict":
            stored = s.attributes.get("stored_trace_id")
            suffix = f" under trace {stored}" if stored else ""
            return Item(name, MISSING,
                        f"rejected: another body is stored for this run_id{suffix}")
    for s in ingests:
        outcome = s.attributes.get("outcome")
        if outcome == "stored":
            return Item(name, MISSING,
                        "monitor.ingest says stored, but no run row has this trace ID")
        if outcome:
            return Item(name, MISSING, f"the backend did not store the run (outcome {outcome})")
    return Item(name, MISSING)


def _monitor_span(spans: list[Span]) -> Item:
    ingests = _ingests(spans)
    if not ingests:
        return Item("monitor span", MISSING)
    return Item("monitor span", FOUND, "; ".join(
        f"outcome {s.attributes.get('outcome', 'unknown')}, {_iso(s.start_ns / 1e9)}"
        for s in ingests))


def _root_span(spans: list[Span]) -> Item:
    roots = sorted((s for s in spans if s.name == ROOT), key=lambda s: s.start_ns)
    if not roots:
        return Item("gcp root span", MISSING)
    parts = []
    for s in roots:
        ident = " / ".join(str(s.attributes[k]) for k in ("use_case_id", "run_id")
                           if s.attributes.get(k))
        parts.append(f"{ident + ', ' if ident else ''}{_iso(s.start_ns / 1e9)}")
    return Item("gcp root span", FOUND, "; ".join(parts))


def _chain(start: Span, by_id: dict[str, Span]) -> tuple[bool, str]:
    names, seen, current = [start.name], {start.span_id}, start
    while True:
        parent = current.parent_span_id
        if not parent:
            return False, f"the chain stops at {current.name}: it has no parent"
        if parent in seen:
            return False, f"the chain stops at {current.name}: the parent links make a loop"
        nxt = by_id.get(parent)
        if nxt is None:
            return False, f"the chain stops at {current.name}: parent {parent} is not in the file"
        names.append(nxt.name)
        seen.add(parent)
        current = nxt
        if nxt.name == SEND:
            return True, " → ".join(names)


def _ancestor_link(spans: list[Span]) -> Item:
    ingests = _ingests(spans)
    if not ingests:
        return Item("ancestor link", MISSING, "no monitor.ingest span")
    by_id = {s.span_id: s for s in spans}
    first_failure = ""
    for s in ingests:
        reached, text = _chain(s, by_id)
        if reached:
            return Item("ancestor link", FOUND, text)
        first_failure = first_failure or text
    return Item("ancestor link", MISSING, first_failure)


def check(trace_id: str, rows: list[RunRow], spans: list[Span], *, backend_only: bool,
          stored_rows: dict[str, list[RunRow]] | None = None, skipped_lines: int = 0) -> Result:
    items = [_run_row(rows, spans, stored_rows or {}), _monitor_span(spans)]
    if backend_only:
        items += [Item("gcp root span", SKIPPED), Item("ancestor link", SKIPPED)]
    else:
        items += [_root_span(spans), _ancestor_link(spans)]
    return Result(trace_id=trace_id, items=tuple(items), skipped_lines=skipped_lines)


def render(result: Result) -> str:
    lines = [f"trace {result.trace_id}"]
    lines += [f"{item.name:<15}{item.state:<9}{item.detail}".rstrip() for item in result.items]
    if result.skipped_lines:
        lines.append(f"note: {result.skipped_lines} span file line(s) could not be read")
    found = sum(1 for item in result.checked if item.state == FOUND)
    word = "OK" if result.ok else "MISSING"
    lines.append(f"RESULT: {word} ({found} of {len(result.checked)} found)")
    return "\n".join(lines)
