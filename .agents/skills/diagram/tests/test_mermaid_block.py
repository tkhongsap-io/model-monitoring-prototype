"""mermaid_block.py and the Mermaid path of check_diagrams.py and render.py."""

import contextlib
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support

import check_diagrams
import mermaid_block
import render

FLOW = "flowchart LR\n  api[Backend API] --> db[(monitor)]"
SEQUENCE = "sequenceDiagram\n  autonumber\n  Job->>API: POST /api/batch/runs"


class Body(unittest.TestCase):
    def problems(self, body: str, diagram_type: str = "architecture") -> str:
        return "\n".join(mermaid_block.body_problems(body, diagram_type))

    def test_the_keyword_of_each_type_passes(self) -> None:
        bodies = {
            "architecture": FLOW,
            "decision": "flowchart TD\n  q{Count is 0?} -->|yes| green[Green]",
            "sequence": SEQUENCE,
            "state": "stateDiagram-v2\n  [*] --> Draft",
            "er": "erDiagram\n  BATCH_RUNS {\n    col run_id PK\n  }",
            "class": "classDiagram\n  class Run\n  Run <|-- BatchRun",
        }
        for diagram_type, body in bodies.items():
            with self.subTest(diagram_type=diagram_type):
                self.assertEqual(self.problems(body, diagram_type), "")

    def test_a_comment_before_the_keyword_passes(self) -> None:
        self.assertEqual(self.problems("%% phase 1\n" + FLOW), "")

    def test_the_wrong_keyword_for_the_type_is_refused(self) -> None:
        self.assertIn("starts with 'sequenceDiagram'", self.problems(FLOW, "sequence"))
        self.assertIn("starts with 'flowchart'", self.problems(SEQUENCE, "architecture"))
        self.assertIn("a direction", self.problems("flowchart\n  a --> b"))
        self.assertIn("a direction", self.problems("graph LR\n  a --> b"))

    def test_a_type_the_project_added_takes_any_keyword(self) -> None:
        self.assertEqual(self.problems(FLOW, "network"), "")
        self.assertEqual(self.problems(SEQUENCE, "network"), "")
        self.assertIn("expected flowchart", self.problems("architecture-beta\n  x", "network"))

    def test_an_empty_block_and_a_bare_keyword_are_refused(self) -> None:
        self.assertIn("empty", self.problems("\n%% only a comment\n"))
        self.assertIn("nothing drawn", self.problems("flowchart LR"))

    def test_each_construct_that_leaves_the_file_is_refused(self) -> None:
        refused = {
            "%%{": '%%{init: {"theme": "dark"}}%%\n' + FLOW,
            "configuration block": "---\nconfig:\n  theme: dark\n---\n" + FLOW,
            "click or href": FLOW + "\n  click api callback",
            "a link (click or href)": FLOW + '\n  api["<b>API</b> href"]',
            "a URL": FLOW + "\n  api --> ext[https://example.com]",
            "a URL: ": FLOW + "\n  api --> ext[www.example.com]",
            "<img>": FLOW + '\n  api["<img src=x>"]',
            "<a>": FLOW + '\n  api["<A onclick=x>t</a>"]',
            "<script>": FLOW + '\n  api["< script>x"]',
        }
        for expected, body in refused.items():
            with self.subTest(expected=expected):
                self.assertIn(expected, self.problems(body))

    def test_mermaid_arrows_and_stereotypes_are_not_tags(self) -> None:
        body = "classDiagram\n  class Shape\n  <<interface>> Shape\n  Shape <|-- Box\n  A <--> B"
        self.assertEqual(self.problems(body, "class"), "")

    def test_a_label_that_only_contains_the_word_clicks_passes(self) -> None:
        self.assertEqual(self.problems(FLOW + "\n  u[User clicks Save] --> api"), "")


class Record(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name) / "sequence" / "batch-run-ingest"
        support.write(self.directory.parent / "README.md", "# S\n\n[s](batch-run-ingest/README.md)\n")
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.md = self.directory / "0001-first.md"

    def problems(self) -> str:
        return "\n".join(check_diagrams.check_type(self.directory.parent))

    def test_a_mermaid_version_is_one_file_and_passes(self) -> None:
        support.write(self.md, support.mermaid_record(SEQUENCE))
        self.assertEqual(self.problems(), "")

    def test_crlf_line_ends_pass(self) -> None:
        support.write(self.md, support.mermaid_record(SEQUENCE), newline="\r\n")
        self.assertEqual(self.problems(), "")

    def test_the_type_comes_from_the_type_directory_not_the_subject(self) -> None:
        support.write(self.md, support.mermaid_record(FLOW))
        self.assertIn("a sequence block starts with 'sequenceDiagram'", self.problems())

    def test_a_mermaid_version_with_an_svg_is_refused(self) -> None:
        support.write(self.md, support.mermaid_record(SEQUENCE))
        support.write(self.directory / "0001-first.drawio.svg", support.svg(support.model()))
        self.assertIn("a format: mermaid version has no .drawio.svg", self.problems())

    def test_format_mermaid_with_no_block_is_refused(self) -> None:
        support.write(self.md, support.record(extra="format: mermaid\n"))
        self.assertIn("no ```mermaid block", self.problems())

    def test_two_blocks_and_an_open_block_are_refused(self) -> None:
        two = support.mermaid_record(SEQUENCE) + f"\n```mermaid\n{SEQUENCE}\n```\n"
        support.write(self.md, two)
        self.assertIn("2 mermaid blocks", self.problems())
        support.write(self.md, support.record(extra="format: mermaid\n", body="```mermaid\nx\n"))
        self.assertIn("not closed", self.problems())

    def test_an_unknown_format_is_refused(self) -> None:
        support.write(self.md, support.record(extra="format: plantuml\n"))
        self.assertIn("format is 'plantuml'", self.problems())

    def test_a_mermaid_block_without_the_format_field_still_needs_the_svg(self) -> None:
        support.write(self.md, support.record(body=f"```mermaid\n{SEQUENCE}\n```\n"))
        self.assertIn("0001-first.drawio.svg: missing", self.problems())

    def test_labels_prints_the_block_of_a_mermaid_version(self) -> None:
        support.write(self.md, support.mermaid_record(SEQUENCE))
        buffer = io.StringIO()
        buffer.reconfigure = lambda **_: None
        with mock.patch("sys.stdout", buffer), contextlib.redirect_stdout(buffer):
            render.labels(self.md)
        self.assertEqual(buffer.getvalue(), SEQUENCE + "\n")


class Reference(unittest.TestCase):
    """Every example in references/mermaid.md passes the check for the type it names."""

    def test_each_example_passes_for_its_type(self) -> None:
        text = (support.SKILL / "references" / "mermaid.md").read_text(encoding="utf-8")
        examples = re.findall(r"^### `([a-z-]+)`.*?^```mermaid\n(.*?)^```$", text, re.M | re.S)
        self.assertEqual({name for name, _ in examples}, mermaid_block.FLOWCHART_TYPES | set(mermaid_block.KEYWORDS))
        for diagram_type, body in examples:
            with self.subTest(diagram_type=diagram_type):
                self.assertEqual(mermaid_block.body_problems(body, diagram_type), [])


if __name__ == "__main__":
    unittest.main()
