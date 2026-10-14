# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check the structure of the recorded diagram versions in docs/diagram/.

The gate runs this (the ``check-diagrams`` hook in .pre-commit-config.yaml), so it needs
nothing but the standard library: no draw.io, no network. It checks what the rule in
.agents/rules/diagram.md makes checkable:

- a type directory holds either versions or subject directories, never both: beside its
  subjects it holds only its ``README.md``; a subject directory is named like a slug and
  holds versions
- every ``NNNN-slug.drawio.svg`` has its ``NNNN-slug.md`` beside it and the other way
  round, and no number is used twice in one directory
- a record with ``format: mermaid`` (a version recorded without draw.io) has no
  ``.drawio.svg``; it holds one ``mermaid`` block that ``mermaid_block.py`` accepts for
  the type
- each record's frontmatter has ``status`` (``current``, ``proposed``, ``withdrawn``, or
  ``superseded by NNNN`` naming a later version in the same directory), an ISO ``date``,
  ``author`` as ``Name <email>``, and, when present, an ISO ``confirmed``
- a directory of versions has at most one ``current`` and at most one ``proposed``, and
  at least one of the two unless every version is ``withdrawn``
- the ``README.md`` beside the versions links every one of them, and a type's
  ``README.md`` links every subject's index
- each ``.drawio.svg`` is at most ``MAX_KB`` (1024 KB) and embeds an uncompressed draw.io
  model whose images are all data URIs or draw.io's own ``img/lib/...``
- every file in ``icons/`` passes the icon check: it is an ``.svg`` or a ``.png`` that
  ``icon_safety.py`` accepts, and its table row in ``icons/README.md`` carries its SHA-256,
  so a file changed after review fails

    uv run .agents/skills/diagram/scripts/check_diagrams.py [--root docs/diagram]

An empty or missing root passes: a project records its first version when it has a
component to draw. Exits 1 and prints one line per problem otherwise.
"""

import argparse
import datetime
import hashlib
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from icon_safety import icon_problems  # beside this script, as in fetch_icon.py
from mermaid_block import record_problems as mermaid_problems

MAX_KB = 1024  # the largest .drawio.svg the gate accepts; render.py refuses to write more
SUBJECT =re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION = re.compile(r"^(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.(drawio\.svg|md)$")
SUPERSEDED = re.compile(r"^superseded by (\d{4})$")
AUTHOR = re.compile(r"^[^<>]+ <[^<>@\s]+@[^<>\s]+>$")
CONTENT = re.compile(r'<svg\b[^>]*?\scontent="([^"]*)"', re.DOTALL)
IMAGE = re.compile(r"(?:^|;)image=([^;]*)")
ALLOWED_IMAGE = ("data:", "img/lib/")  # an embedded icon, or draw.io's own image libraries
SHA256 = re.compile(r"\b[0-9a-f]{64}\b")
NOT_TYPES = {"icons"}
LIVE = ("current", "proposed")


def frontmatter(path: Path) -> dict:
    """Return the ``key: value`` pairs between the leading ``---`` lines of path.

    A value in matching quotes (``"current"``, ``'2026-10-13'``) is returned without them,
    as YAML reads it.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(":")
        if sep:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key.strip()] = value
    return {}


def outside_images(model: str) -> list:
    """Return the images in the cell styles of a draw.io model that are not allowed.

    Allowed: a data URI and ``img/lib/...``. ``render.py export`` runs this on its source
    and the gate on every recorded version, so the two agree. Raises ET.ParseError when
    model is not well-formed XML.
    """
    root = ET.fromstring(model)
    return sorted(
        {
            image
            for cell in root.iter()
            for image in IMAGE.findall(cell.get("style", ""))
            if not image.startswith(ALLOWED_IMAGE)
        }
    )


def model_problems(svg: Path) -> list:
    """Return what is wrong with svg: its size, and the draw.io model embedded in it."""
    size = svg.stat().st_size
    if size > MAX_KB * 1024:
        return [f"{size // 1024} KB; a version may be at most {MAX_KB} KB"]
    match = CONTENT.search(svg.read_text(encoding="utf-8"))
    if not match:
        return ["no embedded draw.io model (export with render.py)"]
    model = html.unescape(match.group(1))
    if "<mxGraphModel" not in model:
        return ["the embedded model is compressed (export with render.py, which passes -u)"]
    try:
        linked = outside_images(model)
    except ET.ParseError as error:
        return [f"the embedded model is not well-formed XML: {error}"]
    return [f"image linked by URL or path, not embedded: {image}" for image in linked]


def record_problems(md: Path, number: str, numbers: set) -> list:
    """Return what is wrong with the frontmatter of one version's .md."""
    fields = frontmatter(md)
    if not fields:
        return ["no frontmatter (copy docs/diagram/TEMPLATE.md)"]
    problems = []
    status = fields.get("status", "")
    superseded = SUPERSEDED.match(status)
    if superseded:
        later = superseded.group(1)
        if later not in numbers:
            problems.append(f"status names {later}, which does not exist in this directory")
        elif later <= number:
            problems.append(f"status names {later}, which is not a later version")
    elif status not in LIVE and status != "withdrawn":
        problems.append(
            f"status is {status!r}; expected 'current', 'proposed', 'withdrawn', "
            "or 'superseded by NNNN'"
        )
    try:
        datetime.date.fromisoformat(fields.get("date", ""))
    except ValueError:
        problems.append(f"date is {fields.get('date', '')!r}; expected YYYY-MM-DD")
    if not AUTHOR.match(fields.get("author", "")):
        problems.append("author is not 'Name <email>' (git config user.name / user.email)")
    if fields.get("format", "mermaid") != "mermaid":
        problems.append(f"format is {fields['format']!r}; omit it for draw.io, or 'mermaid'")
    if "confirmed" in fields:
        try:
            datetime.date.fromisoformat(fields["confirmed"])
        except ValueError:
            problems.append(f"confirmed is {fields['confirmed']!r}; expected YYYY-MM-DD")
        if status == "proposed":
            problems.append("confirmed is set on a proposed version; it marks the flip to current")
    return problems


def check_type(directory: Path) -> list:
    """Return the problems in one type directory: its versions, or its subjects' versions."""
    subjects = sorted(p for p in directory.iterdir() if p.is_dir())
    if not subjects:
        return check_versions(directory, directory.name)
    problems = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.name != "README.md"):
        problems.append(
            f"{path}: this type has subject directories, so its versions live in them;"
            " beside them it holds only README.md"
        )
    index_path = directory / "README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    if index is None:
        problems.append(f"{index_path}: missing; it indexes this type's subjects")
    for subject in subjects:
        if not SUBJECT.match(subject.name):
            problems.append(f"{subject}: not a subject name (lowercase words joined by dashes)")
        if index is not None and f"({subject.name}/README.md)" not in index:
            problems.append(f"{index_path}: no row linking {subject.name}/README.md")
        problems += check_versions(subject, directory.name)
    return problems


def check_versions(directory: Path, diagram_type: str) -> list:
    """Return the problems in one directory of versions, each prefixed with its path."""
    problems = []
    stems = {}
    for path in sorted(directory.iterdir()):
        if path.name == "README.md":
            continue
        match = VERSION.match(path.name)
        if not match or not path.is_file():
            problems.append(f"{path}: not a version file (NNNN-slug.drawio.svg or NNNN-slug.md)")
            continue
        number, slug, kind = match.groups()
        stems.setdefault((number, slug), set()).add(kind)

    numbers = {}
    for number, slug in stems:
        numbers.setdefault(number, []).append(slug)
    for number, slugs in sorted(numbers.items()):
        if len(slugs) > 1:
            problems.append(f"{directory}: number {number} is used by {', '.join(sorted(slugs))}")

    index_path = directory / "README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    if index is None and stems:
        problems.append(f"{index_path}: missing; it indexes these versions")

    statuses = {}
    for (number, slug), kinds in sorted(stems.items()):
        stem = directory / f"{number}-{slug}"
        md = Path(f"{stem}.md")
        svg = Path(f"{stem}.drawio.svg")
        fields = frontmatter(md) if "md" in kinds else {}
        mermaid = fields.get("format") == "mermaid"
        if "md" not in kinds:
            problems.append(f"{md}: missing; every version has its record")
        elif mermaid and "drawio.svg" in kinds:
            problems.append(f"{svg}: a format: mermaid version has no .drawio.svg")
        elif not mermaid and "drawio.svg" not in kinds:
            problems.append(
                f"{svg}: missing; a version has both files, or 'format: mermaid' in its record"
            )
        if "md" in kinds:
            problems += [f"{md}: {p}" for p in record_problems(md, number, set(numbers))]
            statuses.setdefault(fields.get("status", ""), []).append(number)
        if mermaid:
            problems += [f"{md}: {p}" for p in mermaid_problems(md, diagram_type)]
        if "drawio.svg" in kinds:
            problems += [f"{svg}: {p}" for p in model_problems(svg)]
        if index is not None and f"({number}-{slug}.md)" not in index:
            problems.append(f"{index_path}: no row linking {number}-{slug}.md")

    for status in LIVE:
        if len(statuses.get(status, [])) > 1:
            found = ", ".join(statuses[status])
            problems.append(f"{directory}: expected at most one {status} version, found {found}")
    if stems and not any(statuses.get(s) for s in LIVE) and set(statuses) != {"withdrawn"}:
        problems.append(f"{directory}: no current or proposed version, and not all are withdrawn")
    return problems


def check_icons(directory: Path) -> list:
    """Return the icons that fail the icon check: unsafe content, or no row with their hash."""
    icons = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "README.md")
    if not icons:
        return []
    readme = directory / "README.md"
    lines = readme.read_text(encoding="utf-8").splitlines() if readme.is_file() else []
    problems = []
    for icon in icons:
        problems += [f"{icon}: {problem}" for problem in icon_problems(icon)]
        # Only a table row counts: a note that names the icon, or quotes an old hash, does not.
        row = re.compile(rf"^\|\s*`{re.escape(icon.name)}`\s*\|")
        rows = [line for line in lines if row.match(line)]
        if not rows:
            problems.append(
                f"{icon}: no row in {readme} (source URL, license, date retrieved, SHA-256)"
            )
            continue
        digest = hashlib.sha256(icon.read_bytes()).hexdigest()
        recorded = SHA256.findall(rows[0])
        if not recorded:
            problems.append(f"{icon}: its row in {readme} has no SHA-256")
        elif digest not in recorded:
            problems.append(f"{icon}: its SHA-256 is {digest}, not the one in {readme}")
    return problems


def main() -> None:
    """Check every type directory under the root and the icons; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path("docs/diagram"))
    args = parser.parse_args()

    if not args.root.is_dir():
        return
    sys.stdout.reconfigure(encoding="utf-8")  # paths and labels carry non-ASCII; Windows defaults to cp1252
    problems = []
    for directory in sorted(p for p in args.root.iterdir() if p.is_dir()):
        if directory.name in NOT_TYPES:
            problems += check_icons(directory)
        else:
            problems += check_type(directory)
    for problem in problems:
        print(problem.replace("\\", "/"))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
