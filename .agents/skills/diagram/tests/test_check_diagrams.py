"""check_diagrams.py: the structure of recorded versions, on fixtures and on the repository."""

import hashlib
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

    def test_quoted_frontmatter_values_pass(self) -> None:
        support.drawio_version(self.directory)
        quoted = support.record('"current"').replace("date: 2026-10-13", "date: '2026-10-13'")
        support.write(self.directory / "0001-first.md", quoted)
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.assertEqual(self.problems(), "")
        fields = check_diagrams.frontmatter(self.directory / "0001-first.md")
        self.assertEqual((fields["status"], fields["date"]), ("current", "2026-10-13"))

    def sized_svg(self, size: int) -> None:
        """Write the version's .drawio.svg padded with a comment to exactly size bytes."""
        data = support.svg(support.model()).encode("utf-8")
        filler = b"x" * (size - len(data) - len(b"<!---->"))
        path = self.directory / "0001-first.drawio.svg"
        path.write_bytes(data.replace(b"</svg>", b"<!--" + filler + b"--></svg>"))
        self.assertEqual(path.stat().st_size, size)

    def test_a_version_at_the_size_limit_passes(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.sized_svg(check_diagrams.MAX_KB * 1024)
        self.assertEqual(self.problems(), "")

    def test_a_version_over_the_size_limit_is_reported(self) -> None:
        support.drawio_version(self.directory)
        support.write(self.directory / "README.md", support.index("0001-first"))
        self.sized_svg(check_diagrams.MAX_KB * 1024 + 1)
        self.assertIn("a version may be at most 1024 KB", self.problems())


class Subjects(unittest.TestCase):
    """A type whose versions live in subject directories."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name) / "sequence"
        subject = self.directory / "batch-run-ingest"
        support.drawio_version(subject)
        support.write(subject / "README.md", support.index("0001-first"))
        support.write(self.directory / "README.md", "| [x](batch-run-ingest/README.md) |\n")

    def problems(self) -> str:
        return "\n".join(check_diagrams.check_type(self.directory))

    def test_subjects_with_only_the_type_index_beside_them_pass(self) -> None:
        self.assertEqual(self.problems(), "")

    def test_every_other_file_beside_the_subjects_is_reported(self) -> None:
        for name in ("0002-Batch-Run.drawio.svg", "notes.md", "0002-second.md"):
            with self.subTest(name=name):
                path = support.write(self.directory / name, "x\n")
                self.assertIn(f"{name}: this type has subject directories", self.problems())
                path.unlink()


class Icons(unittest.TestCase):
    """The hash of an icon is read from its table row in icons/README.md only."""

    ICON = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0"/></svg>\n'

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name) / "icons"
        self.directory.mkdir()
        (self.directory / "docker.svg").write_bytes(self.ICON)
        self.digest = hashlib.sha256(self.ICON).hexdigest()

    def problems(self, readme: str) -> str:
        support.write(self.directory / "README.md", readme)
        return "\n".join(check_diagrams.check_icons(self.directory))

    def row(self, digest: str) -> str:
        return f"| File | SHA-256 |\n|---|---|\n| `docker.svg` | `{digest}` |\n"

    def test_a_row_with_the_hash_passes(self) -> None:
        self.assertEqual(self.problems(self.row(self.digest)), "")

    def test_a_note_above_the_table_does_not_hide_the_row(self) -> None:
        note = "`docker.svg` was fetched again on 2026-10-14.\n\n"
        self.assertEqual(self.problems(note + self.row(self.digest)), "")

    def test_a_note_with_the_hash_does_not_pass_a_wrong_row(self) -> None:
        note = f"`docker.svg` had the hash `{self.digest}` before.\n\n"
        problems = self.problems(note + self.row("0" * 64))
        self.assertIn("its SHA-256 is", problems)

    def test_a_note_alone_is_not_a_row(self) -> None:
        problems = self.problems(f"`docker.svg`: `{self.digest}`\n")
        self.assertIn("no row in", problems)


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
