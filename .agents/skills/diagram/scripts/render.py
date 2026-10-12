# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Render a draw.io diagram into the repository's recorded format, and back.

A recorded diagram version is one ``NNNN-slug.drawio.svg``: an SVG image with the
draw.io model embedded, so it renders in Markdown and still opens in draw.io. This
script wraps the draw.io desktop CLI, which does the rendering.

    uv run render.py export SRC.drawio OUT.drawio.svg [--preview OUT.png]
    uv run render.py extract IN.drawio.svg OUT.drawio
    uv run render.py labels IN.drawio.svg

(render.py is .agents/skills/diagram/scripts/render.py.)

``export`` refuses a model whose icons link to a URL or a file, then renders SRC with
the model and images embedded but not the fonts (they are most of the file's size;
viewers fall back to their own sans-serif). The model is embedded uncompressed, so a
version diffs as text and its labels can be searched without draw.io. It is drawn in the
light theme on a white background: draw.io otherwise exports adaptive light-dark colours
on a transparent background, which a dark page can turn unreadable. It ends the file
with a newline (the gate's end-of-file-fixer would otherwise rewrite it), refuses a
result the gate's 500 KB limit would reject, and optionally writes a PNG preview.
``extract`` recovers the uncompressed model from a recorded version, which is where the
next version starts; it only reads the recorded file. ``labels`` prints every cell's label
as plain text, one per line, straight from the embedded model and without draw.io: the
quick way to compare a version with the repository or search the other type.

The draw.io binary is taken from ``DRAWIO_BIN``, then the default install path for the
platform, then ``PATH``. On a Linux machine with no display, run under ``xvfb-run``.

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
from pathlib import Path

log = logging.getLogger("render")

DEFAULT_PATHS = [
    Path(r"C:\Program Files\draw.io\draw.io.exe"),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "draw.io" / "draw.io.exe",
    Path("/Applications/draw.io.app/Contents/MacOS/draw.io"),
    Path("/opt/drawio/drawio"),
    Path("/usr/bin/drawio"),
]
TIMEOUT_SECONDS = 180
MAX_KB = 500  # check-added-large-files in .pre-commit-config.yaml
TRANSPARENT = "background: transparent; background-color: transparent;"
WHITE = "background-color: #ffffff;"


def find_drawio() -> Path:
    """Return the draw.io desktop binary, or exit with how to install it."""
    configured = os.environ.get("DRAWIO_BIN")
    if configured and Path(configured).is_file():
        return Path(configured)
    for candidate in DEFAULT_PATHS:
        if candidate.is_file():
            return candidate
    for name in ("drawio", "draw.io"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise SystemExit(
        "draw.io desktop not found. Install it from "
        "https://github.com/jgraph/drawio-desktop/releases or set DRAWIO_BIN to its executable."
    )


def run_drawio(args: list[str]) -> None:
    """Run the draw.io CLI with args; exit with its output if it fails."""
    command = [str(find_drawio()), *args]
    log.info("running %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise SystemExit(f"draw.io failed ({result.returncode}):\n{result.stdout}{result.stderr}")


def end_with_newline(path: Path) -> None:
    """Append a newline to path unless it already ends with one."""
    data = path.read_bytes()
    if not data.endswith(b"\n"):
        path.write_bytes(data + b"\n")


def linked_images(source: Path) -> list[str]:
    """Return the image references in source that point outside the file and draw.io.

    Allowed: a data URI (an icon from docs/diagram/icons/) and ``img/lib/...`` (draw.io's
    own image libraries, which ship with every copy of draw.io). A URL or a file path
    makes the next edit depend on the network or on one machine's disk.
    """
    styles = re.findall(r'style="([^"]*)"', source.read_text(encoding="utf-8"))
    images = [m for style in styles for m in re.findall(r"(?:^|;)image=([^;]*)", style)]
    return [i for i in images if not i.startswith(("data:", "img/lib/"))]


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
    output.write_text(rendered.replace(TRANSPARENT, WHITE, 1), encoding="utf-8", newline="")
    end_with_newline(output)
    size_kb = output.stat().st_size // 1024
    if size_kb > MAX_KB:
        raise SystemExit(f"{output} is {size_kb} KB; the gate refuses files over {MAX_KB} KB")
    if preview is not None:
        run_drawio(["-x", "-f", "png", "-b", "20", "-s", "1.5", "-o", str(preview), str(source)])
    log.info("wrote %s", output)


def extract(source: Path, output: Path) -> None:
    """Recover the uncompressed draw.io model embedded in a recorded .drawio.svg."""
    run_drawio(["-x", "-f", "xml", "-u", "-o", str(output), str(source)])
    if "<mxGraphModel" not in output.read_text(encoding="utf-8"):
        raise SystemExit(f"{output} holds no mxGraphModel; is {source} a draw.io export?")
    log.info("wrote %s", output)


def labels(source: Path) -> None:
    """Print the plain-text label of every cell in the model embedded in source."""
    match = re.search(r'<svg\b[^>]*?\scontent="([^"]*)"', source.read_text(encoding="utf-8"))
    model = html.unescape(match.group(1)) if match else ""
    if "<mxGraphModel" not in model:
        raise SystemExit(f"{source} embeds no uncompressed model; use extract")
    sys.stdout.reconfigure(encoding="utf-8")  # labels carry non-ASCII; Windows defaults to cp1252
    for value in re.findall(r'\svalue="([^"]*)"', model):
        text = re.sub(r"<br\s*/?>", " / ", html.unescape(value))
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
        if text:
            print(text)


def main() -> None:
    """Parse the command line and run export or extract."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    export_cmd = commands.add_parser("export", help="render .drawio into .drawio.svg")
    export_cmd.add_argument("source", type=Path)
    export_cmd.add_argument("output", type=Path)
    export_cmd.add_argument("--preview", type=Path, help="also write a PNG to look at")
    extract_cmd = commands.add_parser("extract", help="recover the model from .drawio.svg")
    extract_cmd.add_argument("source", type=Path)
    extract_cmd.add_argument("output", type=Path)
    labels_cmd = commands.add_parser("labels", help="print the labels of a .drawio.svg")
    labels_cmd.add_argument("source", type=Path)
    args = parser.parse_args()

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
