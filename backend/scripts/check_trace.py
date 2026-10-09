"""S1-07: trace check tool. Shows if one batch run arrived completely.

Run it through deploy/compose/check-trace.sh (the Compose service `trace-check`):
    check_trace.py <trace_id> [--backend-only] [--wait SECONDS] [--spans-file PATH]
Reads only CHECK_DATABASE_URL (the read-only user), never DATABASE_URL, and never runs the
migrations. Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app import db  # noqa: E402
from app.trace_check import Result, RunRow, Span, check, render, stored_trace_ids  # noqa: E402

TRACE_ID = re.compile(r"^[0-9a-f]{32}$")
POLL_SECONDS = 2.0
COLUMNS = ("use_case_id", "run_id", "status", "completed_at", "received_at", "trace_id_source")


class SetupError(Exception):
    """A setup problem: the message is safe to print (no URL, no secret)."""


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, f"error: {message}\n")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = ArgumentParser(
        prog="check_trace.py", description="Check that one batch run arrived completely (S1-07).")
    parser.add_argument("trace_id", help="32 hex characters")
    parser.add_argument("--backend-only", action="store_true",
                        help="check only the run row and the monitor span")
    parser.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                        help="check again every 2 seconds until all items are found")
    parser.add_argument("--spans-file", default="/otel/spans.jsonl", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.trace_id = args.trace_id.lower()
    if not TRACE_ID.match(args.trace_id) or set(args.trace_id) == {"0"}:
        parser.error("trace_id must be 32 hex characters and not all zeros")
    if args.wait < 0:
        parser.error("--wait must be 0 or more")
    return args


def _value(value: dict[str, Any]) -> Any:
    for key in ("stringValue", "boolValue", "doubleValue"):
        if key in value:
            return value[key]
    if "intValue" in value:
        return int(value["intValue"])          # OTLP JSON writes int64 as a string
    return None


def _list(node: dict[str, Any], key: str) -> list[Any]:
    value = node[key]
    if not isinstance(value, list):
        raise ValueError("invalid span file shape")
    return value


def read_spans(path: str, trace_id: str) -> tuple[list[Span], int]:
    """The spans of one trace, and the number of lines that could not be read."""
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        raise SetupError(f"span file {path} not found") from None
    spans: list[Span] = []
    skipped = 0
    try:
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    found = []
                    for resource in _list(json.loads(line), "resourceSpans"):
                        for scope in _list(resource, "scopeSpans"):
                            for raw in _list(scope, "spans"):
                                if str(raw.get("traceId", "")).lower() != trace_id:
                                    continue
                                found.append(Span(
                                    trace_id=trace_id,
                                    span_id=str(raw.get("spanId", "")).lower(),
                                    parent_span_id=str(raw.get("parentSpanId") or "").lower(),
                                    name=str(raw.get("name", "")),
                                    start_ns=int(raw.get("startTimeUnixNano") or 0),
                                    attributes={a["key"]: _value(a.get("value", {}))
                                                for a in raw.get("attributes", [])}))
                except (ValueError, TypeError, AttributeError, KeyError):
                    skipped += 1
                    continue
                spans.extend(found)
    except (OSError, UnicodeError):
        raise SetupError(f"span file {path} cannot be read") from None
    return spans, skipped


def make_engine(url: str) -> Engine:
    url = db.driver_url(url)
    kwargs: dict[str, Any] = {"future": True}
    if url.startswith("postgresql"):
        kwargs["connect_args"] = {"options": "-c default_transaction_read_only=on"}
    return create_engine(url, **kwargs)


def read_rows(engine: Engine, trace_id: str) -> list[RunRow]:
    table = db.batch_runs
    stmt = (select(*(table.c[name] for name in COLUMNS))
            .where(table.c.trace_id == trace_id).order_by(table.c.received_at))
    with engine.connect() as cx:
        return [RunRow(**dict(row)) for row in cx.execute(stmt).mappings()]


def run_once(engine: Engine, args: argparse.Namespace) -> Result:
    spans, skipped = read_spans(args.spans_file, args.trace_id)
    rows = read_rows(engine, args.trace_id)
    stored = {} if rows else {tid: read_rows(engine, tid) for tid in stored_trace_ids(spans)}
    return check(args.trace_id, rows, spans, backend_only=args.backend_only,
                 stored_rows=stored, skipped_lines=skipped)


def main(argv: list[str] | None = None, *, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic) -> int:
    args = parse_args(argv)
    url = os.environ.get("CHECK_DATABASE_URL", "").strip()
    if not url:
        print("error: CHECK_DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        engine = make_engine(url)
        deadline = clock() + args.wait
        while True:
            result = run_once(engine, args)
            if result.ok or clock() >= deadline:
                break
            sleep(POLL_SECONDS)
    except SetupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (SQLAlchemyError, ValueError) as exc:
        # never the message: it can contain the URL
        print(f"error: cannot read the database ({type(exc).__name__})", file=sys.stderr)
        return 2
    print(render(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
