"""Remove the free text from a `batch-run/1` body before anyone (or Claude) reads it.

A body from a GCP job can contain customer data in its free-text fields. This script
writes a copy in which every free-text value is replaced by a short marker, and every
other value is unchanged. Thus the copy is safe to share and to use for development.

Replaced, wherever they occur in the file:
    question, answer                      -> "[REMOVED <n> chars <placeholders>]"
    retrieval_context[].title / .text     -> the same marker
    tool_calls[].output                   -> the same marker (from its JSON text)

The marker keeps the length and the counts of the placeholders [PHONE], [EMAIL],
[NATIONAL_ID] and [IMAGE], because the length limits and the PII metric need them. An
empty string stays empty (an empty answer with refused=true stays valid).

The script never prints a value from the file: only counts and file names.

Usage, from the repository root:
    python scripts/strip_record_text.py data/run.json            # writes data/run.stripped.json
    python scripts/strip_record_text.py data/run.json -o out.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEXT_KEYS = ("question", "answer")
CONTEXT_KEYS = ("title", "text")
PLACEHOLDER = re.compile(r"\[(PHONE|EMAIL|NATIONAL_ID|IMAGE)\]")


class Stats:
    def __init__(self) -> None:
        self.fields = 0
        self.chars = 0


def marker(value, stats: Stats):
    """The replacement for one free-text value. Never contains the value itself."""
    if value is None or value == "":
        return value
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    stats.fields += 1
    stats.chars += len(text)
    counts: dict[str, int] = {}
    for name in PLACEHOLDER.findall(text):
        counts[name] = counts.get(name, 0) + 1
    found = "".join(f" [{name}]x{n}" for name, n in sorted(counts.items()))
    return f"[REMOVED {len(text)} chars{found}]"


def strip(node, stats: Stats):
    """Walk the whole document, so the text is removed in any shape of body."""
    if isinstance(node, list):
        return [strip(item, stats) for item in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key in TEXT_KEYS:
            out[key] = marker(value, stats)
        elif key == "retrieval_context" and isinstance(value, list):
            out[key] = [
                {k: (marker(v, stats) if k in CONTEXT_KEYS else strip(v, stats)) for k, v in doc.items()}
                if isinstance(doc, dict) else marker(doc, stats)
                for doc in value
            ]
        elif key == "tool_calls" and isinstance(value, list):
            out[key] = [
                {k: (marker(v, stats) if k == "output" else strip(v, stats)) for k, v in call.items()}
                if isinstance(call, dict) else marker(call, stats)
                for call in value
            ]
        else:
            out[key] = strip(value, stats)
    return out


def count_records(doc) -> int:
    if isinstance(doc, dict) and isinstance(doc.get("records"), list):
        return len(doc["records"])
    if isinstance(doc, list):
        return sum(count_records(item) for item in doc)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove free text from a batch-run/1 JSON body.")
    parser.add_argument("input", type=Path, help="the JSON file from the GCP job")
    parser.add_argument("-o", "--output", type=Path,
                        help="output file (default: <input>.stripped.json next to the input)")
    args = parser.parse_args(argv)

    src: Path = args.input
    dst: Path = args.output or src.with_name(f"{src.stem}.stripped.json")
    if dst.resolve() == src.resolve():
        print("error: the output must be a different file from the input", file=sys.stderr)
        return 2
    try:
        doc = json.loads(src.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"error: file not found: {src}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:  # position only, never the content
        print(f"error: not valid JSON at line {exc.lineno}, column {exc.colno}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print("error: the file is not UTF-8 text", file=sys.stderr)
        return 2

    stats = Stats()
    clean = strip(doc, stats)
    dst.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dst}: {count_records(doc)} records, "
          f"{stats.fields} text values removed ({stats.chars} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
