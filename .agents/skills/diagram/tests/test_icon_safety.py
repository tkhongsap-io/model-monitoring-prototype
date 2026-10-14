"""icon_safety.py: one hostile file for each reason the icon check refuses a file."""

import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import support

import icon_safety

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{}</svg>\n'
PATH = '<path d="M0 0h24v24H0z"/>'


def svg(body: str = PATH) -> bytes:
    """Return a small SVG icon whose root holds body."""
    return SVG.format(body).encode("utf-8")


def chunk(kind: bytes, body: bytes) -> bytes:
    """Return one PNG chunk: length, type, body and the CRC of type and body."""
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def png(*extra: bytes, width: int = 1, height: int = 1) -> bytes:
    """Return a valid RGBA PNG of width x height with extra chunks before IDAT."""
    header = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    pixels = chunk(b"IDAT", zlib.compress(b"\x00" + b"\x00" * 4 * width))
    return icon_safety.PNG_SIGNATURE + header + b"".join(extra) + pixels + chunk(b"IEND", b"")


class Svg(unittest.TestCase):
    def problems(self, data: bytes) -> str:
        return "\n".join(icon_safety.svg_problems(data))

    def test_a_plain_icon_with_a_title_passes(self) -> None:
        self.assertEqual(self.problems(svg(f"<title>Docker</title>{PATH}")), "")

    def test_a_local_reference_and_a_gradient_pass(self) -> None:
        body = (
            '<defs><linearGradient id="g"><stop offset="0"/></linearGradient></defs>'
            '<path id="p" d="M0 0h1" fill="url(#g)"/><use href="#p"/>'
        )
        self.assertEqual(self.problems(svg(body)), "")

    def test_a_script_element_is_refused(self) -> None:
        self.assertIn("<script>: element is not allowed", self.problems(svg("<script>x()</script>")))

    def test_a_foreign_object_is_refused(self) -> None:
        self.assertIn("<foreignObject>: element is not allowed", self.problems(svg("<foreignObject/>")))

    def test_an_html_element_is_refused(self) -> None:
        body = '<h:div xmlns:h="http://www.w3.org/1999/xhtml"/>'
        self.assertIn("<div>: HTML element is not allowed", self.problems(svg(body)))

    def test_an_element_from_another_namespace_is_refused(self) -> None:
        body = '<x:thing xmlns:x="https://example.com/ns"/>'
        self.assertIn("element from https://example.com/ns is not allowed", self.problems(svg(body)))

    def test_xmp_inside_metadata_is_refused(self) -> None:
        body = (
            '<metadata><x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF'
            ' xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/></x:xmpmeta></metadata>'
        )
        problems = self.problems(svg(body))
        self.assertIn("<xmpmeta>: element from adobe:ns:meta/ is not allowed", problems)
        self.assertIn("<RDF>: element from", problems)

    def test_an_empty_metadata_element_passes(self) -> None:
        self.assertEqual(self.problems(svg(f"<metadata/>{PATH}")), "")

    def test_an_event_attribute_is_refused(self) -> None:
        body = '<path d="M0" onload="x()"/>'
        self.assertIn("event attribute 'onload' is not allowed", self.problems(svg(body)))

    def test_a_link_to_another_file_is_refused(self) -> None:
        problems = self.problems(svg('<a href="https://example.com/">' + PATH + "</a>"))
        self.assertIn("<a>: element is not allowed", problems)
        self.assertIn("href 'https://example.com/' points outside the file", problems)

    def test_a_use_of_another_file_is_refused(self) -> None:
        body = '<use href="https://example.com/a.svg#i"/>'
        self.assertIn("points outside the file", self.problems(svg(body)))

    def test_a_css_url_to_another_file_is_refused(self) -> None:
        body = '<path d="M0" style="fill: url(https://example.com/a.svg#g)"/>'
        self.assertIn("url(https://example.com/a.svg#g) points outside the file", self.problems(svg(body)))

    def test_a_css_import_is_refused(self) -> None:
        body = "<style>@import 'https://example.com/a.css';</style>"
        self.assertIn("'@import' is not allowed", self.problems(svg(body)))

    def test_a_javascript_url_is_refused(self) -> None:
        body = '<path d="M0" fill="javascript:x()"/>'
        self.assertIn("attribute 'fill' holds a javascript: URL", self.problems(svg(body)))

    def test_a_doctype_is_refused(self) -> None:
        data = b'<!DOCTYPE svg [<!ENTITY a "b">]>' + svg()
        self.assertIn("DOCTYPE or ENTITY", self.problems(data))

    def test_a_stylesheet_instruction_is_refused(self) -> None:
        data = b'<?xml-stylesheet href="https://example.com/a.css"?>' + svg()
        self.assertIn("processing instruction", self.problems(data))

    def test_the_xml_declaration_passes(self) -> None:
        data = b'<?xml version="1.0" encoding="UTF-8"?>' + svg()
        self.assertEqual(self.problems(data), "")

    def test_text_that_is_not_utf8_is_refused(self) -> None:
        self.assertIn("not UTF-8", self.problems(b"\xff\xfe<svg/>"))

    def test_xml_that_is_not_well_formed_is_refused(self) -> None:
        self.assertIn("not well-formed", self.problems(b'<svg xmlns="http://www.w3.org/2000/svg">'))

    def test_a_root_that_is_not_svg_is_refused(self) -> None:
        self.assertIn("not an SVG <svg>", self.problems(b"<svg/>"))


class Png(unittest.TestCase):
    def problems(self, data: bytes) -> str:
        return "\n".join(icon_safety.png_problems(data))

    def test_a_plain_image_passes(self) -> None:
        self.assertEqual(self.problems(png()), "")

    def test_colour_information_passes(self) -> None:
        self.assertEqual(self.problems(png(chunk(b"sRGB", b"\x00"), chunk(b"pHYs", b"\x00" * 9))), "")

    def test_location_and_text_chunks_are_refused(self) -> None:
        for kind, body in (
            (b"eXIf", b"MM\x00*"),
            (b"tEXt", b"Comment\x00somewhere"),
            (b"zTXt", b"Comment\x00\x00" + zlib.compress(b"somewhere")),
            (b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00<x:xmpmeta/>"),
        ):
            with self.subTest(chunk=kind):
                problems = self.problems(png(chunk(kind, body)))
                self.assertIn(f"chunk {kind.decode()} is not allowed", problems)
                self.assertIn("location", problems)

    def test_an_animation_chunk_is_refused(self) -> None:
        self.assertIn("chunk acTL is not allowed", self.problems(png(chunk(b"acTL", b"\x00" * 8))))

    def test_bytes_after_iend_are_refused(self) -> None:
        self.assertIn("5 bytes after IEND", self.problems(png() + b"extra"))

    def test_a_side_over_the_limit_is_refused(self) -> None:
        self.assertIn("each side must be 1 to 1024 px", self.problems(png(width=1025)))

    def test_a_truncated_file_is_refused(self) -> None:
        self.assertIn("truncated", self.problems(png()[:-12]))

    def test_a_bad_crc_is_refused(self) -> None:
        data = bytearray(png())
        data[-1] ^= 0xFF
        self.assertIn("bad CRC", self.problems(bytes(data)))

    def test_a_missing_signature_is_refused(self) -> None:
        self.assertIn("signature is missing", self.problems(png()[8:]))

    def test_a_first_chunk_that_is_not_ihdr_is_refused(self) -> None:
        data = icon_safety.PNG_SIGNATURE + chunk(b"IEND", b"")
        self.assertIn("first chunk is not IHDR", self.problems(data))


class IconFile(unittest.TestCase):
    """icon_problems: the size limit and the file name, before the content check."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)

    def problems(self, name: str, data: bytes) -> str:
        path = self.temp / name
        path.write_bytes(data)
        return "\n".join(icon_safety.icon_problems(path))

    def test_a_valid_svg_and_png_pass(self) -> None:
        self.assertEqual(self.problems("a.svg", svg()), "")
        self.assertEqual(self.problems("a.png", png()), "")

    def test_a_file_over_the_size_limit_is_refused(self) -> None:
        padding = "<!--" + "x" * icon_safety.MAX_BYTES + "-->"
        self.assertIn("an icon may be at most 100 KB", self.problems("a.svg", svg(padding)))

    def test_a_png_named_svg_is_refused(self) -> None:
        self.assertIn("named .svg but it is a PNG", self.problems("a.svg", png()))

    def test_another_file_type_is_refused(self) -> None:
        self.assertIn("'.gif' files are not allowed", self.problems("a.gif", b"GIF89a"))

    def test_the_committed_icons_pass(self) -> None:
        icons = sorted((support.REPO / "docs" / "diagram" / "icons").glob("*.svg"))
        self.assertTrue(icons)
        for icon in icons:
            with self.subTest(icon=icon.name):
                self.assertEqual(icon_safety.icon_problems(icon), [])


if __name__ == "__main__":
    unittest.main()
