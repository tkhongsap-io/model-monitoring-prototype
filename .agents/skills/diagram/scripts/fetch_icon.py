# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Download one icon into docs/diagram/icons/, and keep it only if it passes the icon check.

The only way an icon from the internet enters the repository (.agents/rules/diagram.md).
The file is fetched over HTTPS, written beside its final name, and checked with
``icon_safety.py``; a refused file is deleted and the reasons are printed, so the next
source can be tried. A file that passes is kept as downloaded, with two exceptions: an
SVG's end is set to exactly one newline (so an editor that adds one does not change the
file and its SHA-256), and ``--fill`` adds the brand colour to the root ``<svg>`` of a
Simple Icons file at a pinned version, which ships without one.

    uv run .agents/skills/diagram/scripts/fetch_icon.py URL NAME [--fill '#RRGGBB']

NAME is a lowercase slug (``renovate``); the extension comes from the content. An icon
that already exists is replaced in place. Prints the SHA-256 and the start of the row to
add to docs/diagram/icons/README.md. The file is never opened, rendered, or executed.

Raises SystemExit with a message on a refused URL, a failed download, or a refused file.
"""

import argparse
import datetime
import hashlib
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from icon_safety import MAX_BYTES, PNG_SIGNATURE, icon_problems

ICONS = Path("docs/diagram/icons")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FILL = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Simple Icons at a pinned version, from the npm CDN or the repository's release tag.
SIMPLE_ICONS = re.compile(
    r"^https://(cdn\.jsdelivr\.net/npm/simple-icons@"
    r"|raw\.githubusercontent\.com/simple-icons/simple-icons/)"
    r"\d+\.\d+\.\d+/icons/[a-z0-9]+\.svg$"
)
SVG_START = re.compile(rb"<svg\b[^>]*>")


class HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only when it stays on HTTPS."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://"):
            raise SystemExit(f"refused: the server redirected to a non-HTTPS URL: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str) -> bytes:
    """Return the body at url, refusing anything over the icon size limit."""
    opener = urllib.request.build_opener(HttpsOnlyRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "fetch_icon.py"})
    try:
        with opener.open(request, timeout=30) as response:
            data = response.read(MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(f"download failed: {error}") from error
    if len(data) > MAX_BYTES:
        raise SystemExit(f"refused: larger than {MAX_BYTES // 1024} KB")
    return data


def add_fill(data: bytes, fill: str) -> bytes:
    """Return the SVG with fill set on its root element, which must not already have one."""
    start = SVG_START.search(data)
    if not start or b" fill=" in start.group(0):
        raise SystemExit("refused: --fill needs a root <svg> without a fill attribute")
    return data[: start.start() + 4] + f' fill="{fill}"'.encode() + data[start.start() + 4 :]


def problems_of(data: bytes, suffix: str) -> list:
    """Return icon_problems for data, checked as a temporary file with this suffix."""
    handle, name = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(handle, "wb") as file:
            file.write(data)
        return icon_problems(Path(name))
    finally:
        os.unlink(name)


def main() -> None:
    """Fetch, check, and store one icon; print its SHA-256 and README row."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="an https:// URL of an .svg or .png")
    parser.add_argument("name", help="lowercase slug for the file name, e.g. renovate")
    parser.add_argument("--fill", help="brand colour for a pinned Simple Icons SVG")
    parser.add_argument("--icons", type=Path, default=ICONS, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not args.url.startswith("https://"):
        raise SystemExit("refused: only https:// URLs")
    if not NAME.match(args.name):
        raise SystemExit("refused: NAME must be a lowercase slug with dashes")
    if args.fill and not (FILL.match(args.fill) and SIMPLE_ICONS.match(args.url)):
        raise SystemExit("refused: --fill takes #RRGGBB, for a pinned Simple Icons URL only")
    args.icons.mkdir(parents=True, exist_ok=True)

    data = download(args.url)
    suffix = ".png" if data.startswith(PNG_SIGNATURE) else ".svg"
    problems = problems_of(data, suffix)
    if not problems and suffix == ".svg":
        data = data.rstrip(b"\r\n") + b"\n"
        if args.fill:
            data = add_fill(data, args.fill)
        problems = problems_of(data, suffix)
    if problems:
        reasons = "\n".join(f"  - {problem}" for problem in problems)
        raise SystemExit(f"refused {args.url}; try another source:\n{reasons}")

    target = args.icons / f"{args.name}{suffix}"
    replaced = target.exists()
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    today = datetime.date.today().isoformat()
    print(f"{'replaced' if replaced else 'wrote'} {target.as_posix()}")
    print(f"sha256 {digest}")
    print("row for docs/diagram/icons/README.md (fill in For, License / terms, Credit):")
    print(
        f"| `{target.name}` | <For> | [{args.url}]({args.url}) | <License / terms> "
        f"| <Credit or —> | {today} | `{digest}` |"
    )
    if replaced:
        print("the file existed: update its row instead of adding one")


if __name__ == "__main__":
    main()
