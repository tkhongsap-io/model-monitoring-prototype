# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""The content half of the icon check: is one file in docs/diagram/icons/ safe to keep?

An icon may come from any website that licenses it (.agents/rules/diagram.md), so its
bytes are untrusted. An SVG can carry script, event handlers, HTML, links that fetch
other files, and XMP metadata; a PNG can carry location data, free text, or bytes hidden
after the image. A file that fails is refused, never repaired: the agent picks another
source. The comments on SVG_ELEMENTS, PNG_CHUNKS and PNG_REFUSED say what is refused and
why; tests/test_icon_safety.py gives one hostile file for each reason.

    uv run .agents/skills/diagram/scripts/icon_safety.py FILE [FILE ...]

Prints one line per problem and exits 1 if any file fails. ``fetch_icon.py`` runs it on
every download and ``check_diagrams.py`` on every file in icons/, so the gate refuses a
file that was copied in by hand. Standard library only, Python 3.9 or later: the gate runs
it with plain ``python``.
"""

import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

MAX_BYTES = 100 * 1024
MAX_PNG_SIDE = 1024

SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
# Static vector shapes, a subset of DOMPurify's SVG profile. Absent on purpose: script,
# foreignObject, a, image, feImage and the filters, animate, set, and anything that loads
# or runs something.
# fmt: off
SVG_ELEMENTS = {
    "svg", "g", "defs", "title", "desc", "metadata", "path", "rect", "circle", "ellipse",
    "line", "polyline", "polygon", "linearGradient", "radialGradient", "stop", "clipPath",
    "mask", "pattern", "symbol", "marker", "use", "text", "tspan", "style",
}
# fmt: on

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# The critical chunks and the colour and transparency information (W3C PNG 3). Absent on
# purpose: eXIf and the text chunks (below), the animation chunks, and any chunk type the
# specification does not define.
# fmt: off
PNG_CHUNKS = {
    b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"cHRM", b"gAMA", b"iCCP", b"sBIT",
    b"sRGB", b"cICP", b"mDCV", b"cLLI", b"bKGD", b"hIST", b"pHYs", b"sPLT", b"tIME",
}
# fmt: on
# Chunks refused with their reason: eXIf holds Exif, which can hold a GPS location; the
# text chunks hold free text, and iTXt with keyword XML:com.adobe.xmp holds XMP, which can
# hold one too (exif:GPSLatitude). An icon needs none of them.
PNG_REFUSED = {
    b"eXIf": "it can hold a location",
    b"tEXt": "it holds free text, which can hold a location",
    b"zTXt": "it holds free text, which can hold a location",
    b"iTXt": "it holds free text or XMP, which can hold a location",
}

DTD = re.compile(rb"<!(DOCTYPE|ENTITY)", re.IGNORECASE)
PROCESSING_INSTRUCTION = re.compile(r"<\?(?!xml\s)", re.IGNORECASE)
CSS_URL = re.compile(r"""url\(\s*['"]?\s*([^'")\s]*)""", re.IGNORECASE)
CSS_FORBIDDEN = re.compile(r"@import|expression\s*\(|javascript\s*:", re.IGNORECASE)
SCRIPT_URL = re.compile(r"javascript\s*:", re.IGNORECASE)


def split_name(name: str) -> tuple:
    """Return (namespace, local name) from ElementTree's ``{namespace}local`` form."""
    if name.startswith("{"):
        namespace, _, local = name[1:].partition("}")
        return namespace, local
    return "", name


def css_problems(css: str, where: str) -> list:
    """Return what is unsafe in a CSS text or attribute value: imports, script, outside URLs."""
    problems = []
    forbidden = CSS_FORBIDDEN.search(css)
    if forbidden:
        problems.append(f"{where}: '{forbidden.group(0)}' is not allowed")
    for target in CSS_URL.findall(css):
        if not target.startswith("#"):
            problems.append(f"{where}: url({target}) points outside the file")
    return problems


def attribute_problems(element: ET.Element, where: str) -> list:
    """Return the event handlers, outside links, and unsafe values among element's attributes."""
    problems = []
    for name, value in element.attrib.items():
        _, local = split_name(name)
        if local.lower().startswith("on"):
            problems.append(f"{where}: event attribute '{local}' is not allowed")
        elif local == "href" and not value.startswith("#"):
            problems.append(f"{where}: href '{value}' points outside the file")
        elif SCRIPT_URL.search(value):
            problems.append(f"{where}: attribute '{local}' holds a javascript: URL")
        else:
            problems += css_problems(value, f"{where} attribute '{local}'")
    return problems


def svg_problems(data: bytes) -> list:
    """Return why the SVG in data is unsafe, or an empty list."""
    # A DTD is how XML declares entities: refusing it before parsing stops entity expansion
    # and external entities whatever the Expat version (OWASP: disable DTDs).
    if DTD.search(data):
        return ["a DOCTYPE or ENTITY declaration is not allowed"]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["not UTF-8 text"]
    if PROCESSING_INSTRUCTION.search(text):
        return ["a processing instruction (such as xml-stylesheet) is not allowed"]
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        return [f"not well-formed XML: {error}"]
    if root.tag != f"{{{SVG_NS}}}svg":
        return [f"the root element is {root.tag}, not an SVG <svg>"]

    problems = []

    def walk(element: ET.Element) -> None:
        namespace, local = split_name(element.tag)
        where = f"<{local}>"
        if namespace == SVG_NS and local not in SVG_ELEMENTS:
            problems.append(f"{where}: element is not allowed")
        elif namespace == XHTML_NS:
            problems.append(f"{where}: HTML element is not allowed")
        elif namespace != SVG_NS:
            # Inside <metadata> too: XMP and RDF (as editors write them) can hold a location.
            source = namespace or "no namespace"
            problems.append(f"{where}: element from {source} is not allowed")
        problems.extend(attribute_problems(element, where))
        if namespace == SVG_NS and local == "style":
            problems.extend(css_problems(element.text or "", where))
        for child in element:
            walk(child)

    walk(root)
    return problems


def png_problems(data: bytes) -> list:
    """Return why the PNG in data is unsafe or malformed, or an empty list."""
    if not data.startswith(PNG_SIGNATURE):
        return ["not a PNG: the signature is missing"]
    position = len(PNG_SIGNATURE)
    first = True
    while True:
        if position + 8 > len(data):
            return ["truncated: no IEND chunk"]
        length, kind = struct.unpack(">I4s", data[position : position + 8])
        end = position + 12 + length
        if length > 2**31 - 1 or end > len(data):
            return [f"truncated or malformed chunk {kind!r}"]
        body = data[position + 8 : end - 4]
        (crc,) = struct.unpack(">I", data[end - 4 : end])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            return [f"chunk {kind.decode('latin-1')} has a bad CRC"]
        name = kind.decode("latin-1")
        if first:
            if kind != b"IHDR" or length != 13:
                return ["the first chunk is not IHDR"]
            width, height = struct.unpack(">II", body[:8])
            if not (1 <= width <= MAX_PNG_SIDE and 1 <= height <= MAX_PNG_SIDE):
                return [f"{width}x{height} px: each side must be 1 to {MAX_PNG_SIDE} px"]
            first = False
        elif kind in PNG_REFUSED:
            return [f"chunk {name} is not allowed: {PNG_REFUSED[kind]}"]
        elif kind not in PNG_CHUNKS:
            return [f"chunk {name} is not allowed"]
        position = end
        if kind == b"IEND":
            break
    if position != len(data):
        return [f"{len(data) - position} bytes after IEND"]
    return []


def icon_problems(path: Path) -> list:
    """Return every reason the icon at path is refused; an empty list means it passes."""
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        return [f"{len(data) // 1024} KB: an icon may be at most {MAX_BYTES // 1024} KB"]
    suffix = path.suffix.lower()
    if suffix == ".svg":
        if data.startswith(PNG_SIGNATURE):
            return ["named .svg but it is a PNG"]
        return svg_problems(data)
    if suffix == ".png":
        return png_problems(data)
    return [f"'{suffix or path.name}' files are not allowed: an icon is an .svg or a .png"]


def main() -> None:
    """Check each file named on the command line; exit 1 if any is refused."""
    failed = False
    for name in sys.argv[1:]:
        for problem in icon_problems(Path(name)):
            print(f"{name}: {problem}")
            failed = True
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
