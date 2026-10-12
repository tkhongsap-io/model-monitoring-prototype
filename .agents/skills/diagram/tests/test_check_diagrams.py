"""check_diagrams.py: the structure of recorded versions, on fixtures and on the repository."""

import tempfile
import unittest
from pathlib import Path

import support

import check_diagrams


class DrawioVersions(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name) / "architecture"

    def problems(self) -> str:
        return "\n".join(check_diagrams.check_type(self.directory))

    def test_a_paired_version_with_an_index_row_passes(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertEqual(self.problems(), "")

    def test_crlf_line_ends_pass(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "0001-first.md", support.record(), newline="\r\n")
        support.write(self.directory / "README.md", support.index("0001-first"), newline="\r\n")
        self.assertEqual(self.problems(), "")

    def test_a_version_without_its_svg_is_reported(self) -> None:
        support.write(self.directory / "0001-first.md", support.record())
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertIn("0001-first.drawio.svg: missing", self.problems())

    def test_a_version_without_its_record_is_reported(self) -> None:
        support.write(self.directory / "0001-first.drawio.svg", support.svg(support.model()))
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertIn("0001-first.md: missing", self.problems())

    def test_a_missing_index_row_is_reported(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "README.md", support.index())
        self.assertIn("no row linking 0001-first.md", self.problems())

    def test_a_compressed_model_is_reported(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "0001-first.drawio.svg", support.svg("<mxfile>7V1bc</mxfile>"))
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertIn("compressed", self.problems())

    def test_an_image_linked_by_url_is_reported(self) -> None:
        support.drawio_version(self.directory)
        linked = support.model("shape=image;image=https://example.com/a.svg;")
        support.write(self.directory / "0001-first.drawio.svg", support.svg(linked))
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertIn("image linked by URL or path", self.problems())

    def test_two_current_versions_are_reported(self) -> None:
        support.drawio_version(self.directory, "0001-first")
        support.drawio_version(self.directory, "0002-second")
        support.write(self.directory / "README.md", support.index("0001-first", "0002-second"))
        self.assertIn("at most one current version", self.problems())

    def test_a_number_used_twice_is_reported(self) -> None:
        support.drawio_version(self.directory, "0001-first")
        support.drawio_version(self.directory, "0001-other", status="proposed")
        support.write(self.directory / "README.md", support.index("0001-first", "0001-other"))
        self.assertIn("number 0001 is used by", self.problems())


class Repository(unittest.TestCase):
    def test_the_recorded_versions_and_icons_pass(self) -> None:
        root = support.REPO / "docs" / "diagram"
        problems = []
        for directory in sorted(p for p in root.iterdir() if p.is_dir()):
            if directory.name in check_diagrams.NOT_TYPES:
                problems += check_diagrams.check_icons(directory)
            else:
                problems += check_diagrams.check_type(directory)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
