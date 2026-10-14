# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Render a draw.io diagram into the repository's recorded format, and back.

A recorded diagram version is one ``NNNN-slug.drawio.svg``: an SVG image with the
draw.io model embedded, so it renders in Markdown and still opens in draw.io. This
script wraps the draw.io desktop CLI, which does the rendering.

    uv run render.py doctor
    uv run render.py export SRC.drawio OUT.drawio.svg [--preview OUT.png]
    uv run render.py extract IN.drawio.svg OUT.drawio
    uv run render.py labels IN.drawio.svg | IN.md

(render.py is .agents/skills/diagram/scripts/render.py.)

``export`` refuses a model whose icons link to a URL or a file, then renders SRC with
the model and images embedded but not the fonts (they are most of the file's size;
viewers fall back to their own sans-serif). The model is embedded uncompressed, so a
version diffs as text and its labels can be searched without draw.io. It is drawn in the
light theme on a white background: draw.io otherwise exports adaptive light-dark colours
on a transparent background, which a dark page can turn unreadable. It ends the file
with a newline (so an editor that adds one does not change the file), refuses a result
over the gate's 1024 KB limit (``check_diagrams.MAX_KB``), and optionally writes a PNG
preview.
``extract`` recovers the uncompressed model from a recorded version, which is where the
next version starts; it only reads the recorded file, and needs draw.io only for a
compressed model. ``labels`` prints every cell's label as plain text, one per line,
straight from the embedded model and without draw.io: the quick way to compare a version
with the repository or search the other type.

``doctor`` says whether ``export`` can run here. It exits 0 when draw.io was found, 1
when it is not installed, and 2 when ``DRAWIO_BIN`` is set but names no file. The skill
records a version in Mermaid on 1 and stops on 2: a typing mistake must not change the
format of a version.

The draw.io binary is taken from ``DRAWIO_BIN``, then the install places of the platform
(Windows, macOS, Linux), then ``PATH``. An AppImage has no fixed place: name it in
``DRAWIO_BIN``. On a Linux machine with no display, run under ``xvfb-run``.

Raises SystemExit with a message when draw.io is missing or an export fails.
"""

import argparse
import html
import logging
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from check_diagrams import CONTENT, MAX_KB, outside_images  # beside this script

log = logging.getLogger("render")

PATH_NAMES = ("drawio", "draw.io", "com.jgraph.drawio.desktop")  # the last is the Flatpak
INSTALL_URL = "https://github.com/jgraph/drawio-desktop/releases"
TIMEOUT_SECONDS = 180
SVG_START = re.compile(r"<svg\b[^>]*>")
STYLE = re.compile(r'\sstyle="([^"]*)"')
WHITE = "background-color: #ffffff"


class DrawioBinError(Exception):
    """``DRAWIO_BIN`` is set but does not name a file."""


def install_places() -> list[Path]:
    """Return where draw.io desktop installs itself on this platform."""
    if sys.platform == "win32":
        roots = [os.environ.get(name) for name in ("ProgramFiles", "ProgramFiles(x86)")]
        places = [Path(root) / "draw.io" / "draw.io.exe" for root in roots if root]
        local = os.environ.get("LOCALAPPDATA")  # the per-user installer
        if local:
            places.append(Path(local) / "Programs" / "draw.io" / "draw.io.exe")
        return places
    if sys.platform == "darwin":
        binary = Path("draw.io.app") / "Contents" / "MacOS" / "draw.io"
        return [Path("/Applications") / binary, Path.home() / "Applications" / binary]
    return [Path("/opt/drawio/drawio"), Path("/usr/bin/drawio"), Path("/snap/bin/drawio")]


def locate_drawio() -> Path | None:
    """Return the draw.io desktop binary, or None when it is not installed.

    Raises DrawioBinError when ``DRAWIO_BIN`` is set and names no file: the caller asked
    for one binary, so another one, or none, is not what they meant.
    """
    configured = os.environ.get("DRAWIO_BIN")
    if configured:
        if not Path(configured).is_file():
            raise DrawioBinError(f"DRAWIO_BIN is {configured!r}, which is not a file")
        return Path(configured)
    for place in install_places():
        if place.is_file():
            return place
    for name in PATH_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def find_drawio() -> Path:
    """Return the draw.io desktop binary, or exit with how to install it."""
    try:
        found = locate_drawio()
    except DrawioBinError as error:
        raise SystemExit(f"{error}. Correct it or unset it.") from error
    if found is None:
        raise SystemExit(
            f"draw.io desktop not found. Install it from {INSTALL_URL} "
            "or set DRAWIO_BIN to its executable."
        )
    return found


def doctor() -> int:
    """Print whether draw.io was found; return 0 found, 1 not installed, 2 misconfigured."""
    try:
        found = locate_drawio()
    except DrawioBinError as error:
        print(f"drawio: misconfigured\n{error}. Correct it or unset it.")
        return 2
    if found is None:
        print("drawio: missing")
        print("searched: DRAWIO_BIN (not set)")
        for place in install_places():
            print(f"searched: {place}")
        print(f"searched: PATH for {', '.join(PATH_NAMES)}")
        print(f"install: {INSTALL_URL}")
        return 1
    print(f"drawio: {found}")
    displays = ("DISPLAY", "WAYLAND_DISPLAY")
    if sys.platform.startswith("linux") and not any(os.environ.get(d) for d in displays):
        print("no display: put xvfb-run in front of the export command")
    return 0


def run_drawio(args: list[str]) -> None:
    """Run the draw.io CLI with args; exit with its output if it fails."""
    command = [str(find_drawio()), *args]
    log.info("running %s", " ".join(command))
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",  # not the locale codec: it fails on output it cannot decode
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(f"draw.io did not finish in {TIMEOUT_SECONDS} seconds") from error
    if result.returncode != 0:
        raise SystemExit(f"draw.io failed ({result.returncode}):\n{result.stdout}{result.stderr}")


def end_with_newline(path: Path) -> None:
    """Append a newline to path unless it already ends with one."""
    data = path.read_bytes()
    if not data.endswith(b"\n"):
        path.write_bytes(data + b"\n")


def linked_images(source: Path) -> list[str]:
    """Return the image references in source that point outside the file and draw.io.

    The same rule as the gate (``check_diagrams.outside_images``): a data URI (an icon
    from docs/diagram/icons/) and ``img/lib/...`` (draw.io's own image libraries) are
    allowed. A URL or a file path makes the next edit depend on the network or on one
    machine's disk.
    """
    try:
        return outside_images(source.read_text(encoding="utf-8"))
    except ET.ParseError as error:
        raise SystemExit(f"{source} is not a draw.io model: {error}") from error


def white_background(rendered: str) -> str:
    """Return the exported SVG with a white background on its root ``<svg>``.

    draw.io exports a transparent background, which a dark page turns unreadable. Every
    ``background`` declaration in the root's style is replaced by one white background,
    so the result does not depend on how a draw.io version orders or spaces the style.
    Only the root's ``style`` attribute changes; the embedded model is left alone.
    """
    start = SVG_START.search(rendered)
    if start is None:
        raise SystemExit("the export holds no <svg> element")
    tag = start.group(0)
    style = STYLE.search(tag)
    declarations = (style.group(1) if style else "").split(";")
    kept = [d.strip() for d in declarations if d.strip() and not d.strip().startswith("background")]
    value = "; ".join([WHITE, *kept]) + ";"
    if style:
        tag = tag[: style.start(1)] + value + tag[style.end(1) :]
    else:
        tag = f'<svg style="{value}"' + tag[4:]
    return rendered[: start.start()] + tag + rendered[start.end() :]


def export(source: Path, output: Path, preview: Path | None) -> None:
    """Render source into output as an SVG with the model embedded; optionally a PNG preview."""
    if not output.name.endswith(".drawio.svg"):
        raise SystemExit(f"{output} must end in .drawio.svg")
    linked = linked_images(source)
    if linked:
        raise SystemExit(
            "images linked by URL or path; use img/lib/... or embed from docs/diagram/icons/: "
            + ", ".join(sorted(set(linked)))
        )
    output.unlink(missing_ok=True)  # so a stale file cannot pass for a fresh export
    run_drawio(
        ["-x", "-f", "svg", "-e", "-u", "--svg-theme", "light"]
        + ["--embed-svg-images", "--embed-svg-fonts", "false"]
        + ["-o", str(output), str(source)]
    )
    if not output.is_file():
        raise SystemExit(f"draw.io wrote no {output}; an option this version does not know?")
    rendered = output.read_text(encoding="utf-8")
    if 'content="' not in rendered:
        raise SystemExit(f"{output} has no embedded diagram; draw.io did not embed the model")
    if "&lt;mxGraphModel" not in rendered:
        raise SystemExit(f"{output} embeds a compressed model; draw.io ignored -u")
    output.write_text(white_background(rendered), encoding="utf-8", newline="")
    end_with_newline(output)
    size = output.stat().st_size
    if size > MAX_KB * 1024:
        raise SystemExit(f"{output} is {size // 1024} KB; the gate refuses files over {MAX_KB} KB")
    if preview is not None:
        run_drawio(["-x", "-f", "png", "-b", "20", "-s", "1.5", "-o", str(preview), str(source)])
    log.info("wrote %s", output)


def embedded_model(source: Path) -> str:
    """Return the text of the model embedded in a .drawio.svg, or "" when there is none."""
    match = CONTENT.search(source.read_text(encoding="utf-8"))
    return html.unescape(match.group(1)) if match else ""


def extract(source: Path, output: Path) -> None:
    """Recover the uncompressed draw.io model embedded in a recorded .drawio.svg.

    A recorded version holds the model as text, so this needs no draw.io. Only a
    compressed model (a file that ``export`` did not write) is handed to draw.io.
    """
    model = embedded_model(source)
    if not model:
        raise SystemExit(f"{source} embeds no model; is it a draw.io export?")
    if "<mxGraphModel" in model:
        output.write_text(model.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    else:
        run_drawio(["-x", "-f", "xml", "-u", "-o", str(output), str(source)])
        if "<mxGraphModel" not in output.read_text(encoding="utf-8"):
            raise SystemExit(f"{output} holds no mxGraphModel; is {source} a draw.io export?")
    log.info("wrote %s", output)


def labels(source: Path) -> None:
    """Print the plain-text label of every cell in the model embedded in source.

    For the record of a Mermaid version (a ``.md``), print its block: the labels are in
    the text already.
    """
    sys.stdout.reconfigure(encoding="utf-8")  # labels carry non-ASCII; Windows defaults to cp1252
    if source.suffix == ".md":
        from mermaid_block import block  # beside this script

        try:
            print(block(source))
        except ValueError as error:
            raise SystemExit(str(error)) from error
        return
    model = embedded_model(source)
    if "<mxGraphModel" not in model:
        raise SystemExit(f"{source} embeds no uncompressed model; use extract")
    for value in re.findall(r'\svalue="([^"]*)"', model):
        text = re.sub(r"<br\s*/?>", " / ", html.unescape(value))
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
        if text:
            print(text)


def main() -> None:
    """Parse the command line and run the command it names."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="say whether draw.io is installed here")
    export_cmd = commands.add_parser("export", help="render .drawio into .drawio.svg")
    export_cmd.add_argument("source", type=Path)
    export_cmd.add_argument("output", type=Path)
    export_cmd.add_argument("--preview", type=Path, help="also write a PNG to look at")
    extract_cmd = commands.add_parser("extract", help="recover the model from .drawio.svg")
    extract_cmd.add_argument("source", type=Path)
    extract_cmd.add_argument("output", type=Path)
    labels_cmd = commands.add_parser("labels", help="print the labels of a version")
    labels_cmd.add_argument("source", type=Path)
    args = parser.parse_args()

    if args.command == "doctor":
        sys.exit(doctor())
    if not args.source.is_file():
        sys.exit(f"{args.source} does not exist")
    if args.command == "export":
        export(args.source, args.output, args.preview)
    elif args.command == "extract":
        extract(args.source, args.output)
    else:
        labels(args.source)


if __name__ == "__main__":
    main()
