"""render.py: what it does without draw.io (labels, the image check)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import support

import check_diagrams
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


class Locate(Fixture):
    """The search for draw.io, with the environment, the platform and PATH replaced."""

    def locate(self, platform: str, env: dict, which: str | None = None):
        with (
            mock.patch.object(render.sys, "platform", platform),
            mock.patch.dict(render.os.environ, env, clear=True),
            mock.patch.object(render.shutil, "which", return_value=which),
            mock.patch.object(render.Path, "home", return_value=self.temp / "home"),
        ):
            return render.locate_drawio(), render.install_places()

    def test_nothing_installed_is_none_on_each_platform(self) -> None:
        for platform in ("win32", "darwin", "linux"):
            with self.subTest(platform=platform):
                found, _ = self.locate(platform, {})
                self.assertIsNone(found)

    def test_windows_places_come_only_from_variables_that_are_set(self) -> None:
        _, places = self.locate("win32", {})
        self.assertEqual(places, [])
        local = self.temp / "local"
        binary = support.write(local / "Programs" / "draw.io" / "draw.io.exe", "")
        found, places = self.locate("win32", {"LOCALAPPDATA": str(local)})
        self.assertEqual(found, binary)
        self.assertTrue(all(place.is_absolute() for place in places))

    def test_macos_searches_the_user_applications_folder(self) -> None:
        app = self.temp / "home" / "Applications" / "draw.io.app" / "Contents" / "MacOS"
        binary = support.write(app / "draw.io", "")
        found, _ = self.locate("darwin", {})
        self.assertEqual(found, binary)

    def test_linux_falls_back_to_path(self) -> None:
        found, places = self.locate("linux", {}, which="/home/me/bin/drawio")
        self.assertEqual(found, Path("/home/me/bin/drawio"))
        self.assertIn(Path("/snap/bin/drawio"), places)

    def test_drawio_bin_wins_when_it_is_a_file(self) -> None:
        binary = support.write(self.temp / "drawio-x86_64.AppImage", "")
        found, _ = self.locate("linux", {"DRAWIO_BIN": str(binary)}, which="/usr/bin/drawio")
        self.assertEqual(found, binary)

    def test_a_wrong_drawio_bin_is_an_error_not_a_fallback(self) -> None:
        with self.assertRaises(render.DrawioBinError):
            self.locate("linux", {"DRAWIO_BIN": str(self.temp / "nope")}, which="/usr/bin/drawio")


class Doctor(Fixture):
    def doctor(self, located) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch.object(render, "locate_drawio", side_effect=located):
            with contextlib.redirect_stdout(buffer):
                code = render.doctor()
        return code, buffer.getvalue()

    def test_found_is_0(self) -> None:
        code, text = self.doctor([Path("/usr/bin/drawio")])
        self.assertEqual(code, 0)
        self.assertIn("drawio: ", text)

    def test_not_installed_is_1_and_lists_the_places(self) -> None:
        code, text = self.doctor([None])
        self.assertEqual(code, 1)
        self.assertIn("drawio: missing", text)
        self.assertIn("searched: PATH", text)

    def test_a_wrong_drawio_bin_is_2(self) -> None:
        code, text = self.doctor(render.DrawioBinError("DRAWIO_BIN is 'x', which is not a file"))
        self.assertEqual(code, 2)
        self.assertIn("misconfigured", text)

    def test_the_command_line_runs_doctor_with_no_source(self) -> None:
        with (
            mock.patch.object(render.sys, "argv", ["render.py", "doctor"]),
            mock.patch.object(render, "doctor", return_value=1),
            self.assertRaises(SystemExit) as exit_,
        ):
            render.main()
        self.assertEqual(exit_.exception.code, 1)


class Extract(Fixture):
    def test_an_uncompressed_model_is_recovered_without_drawio(self) -> None:
        source = support.write(self.temp / "0001-a.drawio.svg", support.svg(support.model()))
        output = self.temp / "out.drawio"
        with mock.patch.object(render, "run_drawio") as run:
            render.extract(source, output)
        run.assert_not_called()
        self.assertEqual(output.read_bytes().decode("utf-8"), support.model() + "\n")

    def test_a_compressed_model_goes_to_drawio(self) -> None:
        source = support.write(self.temp / "0001-a.drawio.svg", support.svg("<mxfile>7V1b</mxfile>"))
        output = self.temp / "out.drawio"

        def fake(args: list) -> None:
            support.write(output, support.model())

        with mock.patch.object(render, "run_drawio", side_effect=fake) as run:
            render.extract(source, output)
        run.assert_called_once()

    def test_a_file_with_no_model_is_refused(self) -> None:
        source = support.write(self.temp / "plain.svg", "<svg></svg>\n")
        with self.assertRaises(SystemExit):
            render.extract(source, self.temp / "out.drawio")


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

    def test_export_and_the_gate_use_one_allowlist(self) -> None:
        self.assertIs(render.outside_images, check_diagrams.outside_images)
        for style in ("image=data:image/png,AAAA;", "image=img/lib/a.svg;", "image=../a.svg;"):
            with self.subTest(style=style):
                source = support.write(self.temp / "a.drawio", support.model(style))
                svg = support.write(self.temp / "0001-a.drawio.svg", support.svg(support.model(style)))
                self.assertEqual(bool(render.linked_images(source)), bool(check_diagrams.model_problems(svg)))

    def test_a_source_that_is_not_xml_is_refused(self) -> None:
        source = support.write(self.temp / "a.drawio", "<mxfile>")
        with self.assertRaises(SystemExit):
            render.linked_images(source)


class WhiteBackground(unittest.TestCase):
    """The background of the root <svg>, whatever style text draw.io writes."""

    CONTENT = ' content="&lt;mxCell style=&quot;fillColor=transparent;&quot;/&gt;"'

    def root_style(self, rendered: str) -> str:
        return render.STYLE.search(render.SVG_START.search(rendered).group(0)).group(1)

    def test_the_style_of_drawio_29_becomes_white(self) -> None:
        rendered = (
            '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" style="background:'
            ' transparent; background-color: transparent; color-scheme: light;" width="10px">'
        )
        self.assertEqual(
            self.root_style(render.white_background(rendered)),
            "background-color: #ffffff; color-scheme: light;",
        )

    def test_another_order_and_spacing_become_white(self) -> None:
        rendered = '<svg style="color-scheme:light;background-color:transparent;background:none">'
        self.assertEqual(
            self.root_style(render.white_background(rendered)),
            "background-color: #ffffff; color-scheme:light;",
        )

    def test_a_root_without_a_style_gets_one(self) -> None:
        rendered = '<svg xmlns="http://www.w3.org/2000/svg" width="10px"></svg>'
        self.assertEqual(self.root_style(render.white_background(rendered)), "background-color: #ffffff;")

    def test_the_embedded_model_and_inner_elements_are_left_alone(self) -> None:
        rendered = f'<svg style="background: transparent;"{self.CONTENT}><svg style="background: red"/></svg>'
        result = render.white_background(rendered)
        self.assertIn(self.CONTENT, result)
        self.assertIn('<svg style="background: red"/>', result)
        self.assertEqual(self.root_style(result), "background-color: #ffffff;")

    def test_an_export_without_an_svg_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            render.white_background("<html></html>")


if __name__ == "__main__":
    unittest.main()
