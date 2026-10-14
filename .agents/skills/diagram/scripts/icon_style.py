# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Print the draw.io style that embeds an icon from docs/diagram/icons/.

The icon is embedded in the diagram as a data URI rather than linked by path, so a
recorded .drawio.svg renders the same on GitHub, in VS Code, and in draw.io, with no
file beside it. draw.io's own convention is ``image=data:image/svg+xml,<base64>`` with
no ``;base64`` marker, because a semicolon would end the style entry; a PNG is
``image=data:image/png,<base64>`` the same way, and draw.io adds the marker itself when it
loads the cell.

    uv run .agents/skills/diagram/scripts/icon_style.py docs/diagram/icons/<name>.svg [--width 48]

Prints two lines: the style string, and the width and height that keep the icon's
aspect ratio at the requested width (from the SVG's viewBox, or the PNG's IHDR).

Raises SystemExit when the file fails the icon check (``icon_safety.py``) or has no
usable size.
"""

import argparse
import base64
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from icon_safety import icon_problems

STYLE = (
    "shape=image;html=1;verticalLabelPosition=bottom;verticalAlign=top;"
    "labelBackgroundColor=default;aspect=fixed;imageAspect=0;image=data:{media},{data};"
)
MEDIA = {".svg": "image/svg+xml", ".png": "image/png"}


def svg_size(root: ET.Element) -> tuple[float, float]:
    """Return the SVG's width and height from its viewBox, else its width/height attributes."""
    view_box = root.get("viewBox")
    if view_box:
        _, _, width, height = (float(part) for part in re.split(r"[\s,]+", view_box.strip()))
        return width, height
    try:
        return float(root.get("width", "").rstrip("px")), float(root.get("height", "").rstrip("px"))
    except ValueError as error:
        raise SystemExit("the SVG has neither a viewBox nor a numeric width and height") from error


def main() -> None:
    """Print the embedding style and the scaled size for the given icon."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("icon", type=Path, help="an .svg or .png under docs/diagram/icons/")
    parser.add_argument("--width", type=float, default=48, help="rendered width (default 48)")
    args = parser.parse_args()

    suffix = args.icon.suffix.lower()
    if suffix not in MEDIA or not args.icon.is_file():
        sys.exit(f"{args.icon} is not an SVG or PNG file")
    problems = icon_problems(args.icon)
    if problems:
        sys.exit("\n".join(f"{args.icon}: {problem}" for problem in problems))
    raw = args.icon.read_bytes()
    if suffix == ".png":
        width, height = struct.unpack(">II", raw[16:24])
    else:
        width, height = svg_size(ET.fromstring(raw))
        raw = raw.strip()
    data = base64.b64encode(raw).decode("ascii")
    print(STYLE.format(media=MEDIA[suffix], data=data))
    print(f"width={args.width:g} height={round(args.width * height / width)}")


if __name__ == "__main__":
    main()
