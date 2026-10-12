"""render.py: what it does without draw.io (labels, the image check)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support

import render


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)

    def output(self, function, *args) -> str:
        """Return what function prints; stdout.reconfigure is a no-op on the buffer."""
        buffer = io.StringIO()
        buffer.reconfigure = lambda **_: None
        with mock.patch("sys.stdout", buffer), contextlib.redirect_stdout(buffer):
            function(*args)
        return buffer.getvalue()


class Labels(Fixture):
    def test_labels_are_plain_text_one_per_line(self) -> None:
        source = support.write(self.temp / "0001-a.drawio.svg", support.svg(support.model()))
        self.assertEqual(self.output(render.labels, source), "Backend / API\nÜbersicht\n")

    def test_a_file_with_no_model_is_refused(self) -> None:
        source = support.write(self.temp / "0001-a.drawio.svg", "<svg></svg>\n")
        with self.assertRaises(SystemExit):
            render.labels(source)


class LinkedImages(Fixture):
    def test_data_uris_and_built_in_libraries_are_allowed(self) -> None:
        style = "image=data:image/svg+xml,AAAA;"
        source = support.write(self.temp / "a.drawio", support.model(style))
        self.assertEqual(render.linked_images(source), [])
        source = support.write(self.temp / "b.drawio", support.model("image=img/lib/azure2/a.svg;"))
        self.assertEqual(render.linked_images(source), [])

    def test_a_url_and_a_path_are_returned(self) -> None:
        source = support.write(self.temp / "a.drawio", support.model("image=https://x.test/a.svg;"))
        self.assertEqual(render.linked_images(source), ["https://x.test/a.svg"])
        source = support.write(self.temp / "b.drawio", support.model("image=C:/icons/a.svg;"))
        self.assertEqual(render.linked_images(source), ["C:/icons/a.svg"])

    def test_export_refuses_a_linked_image_before_calling_drawio(self) -> None:
        source = support.write(self.temp / "a.drawio", support.model("image=https://x.test/a.svg;"))
        with mock.patch.object(render, "run_drawio") as run, self.assertRaises(SystemExit):
            render.export(source, self.temp / "0001-a.drawio.svg", None)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
