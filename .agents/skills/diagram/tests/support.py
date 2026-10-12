"""Shared fixtures for the diagram script tests: a small docs/diagram tree in a temp dir.

Every file is written with explicit ``\\n`` line ends, so a test reads the same bytes on
Windows, macOS and Linux. Nothing here writes inside the repository.
"""

import html
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
sys.path.insert(0, str(SKILL / "scripts"))

MODEL = (
    '<mxfile host="drawio"><diagram id="d" name="Page-1"><mxGraphModel><root>'
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    '<mxCell id="2" value="Backend&lt;br&gt;API" style="rounded=1;" vertex="1" parent="1"/>'
    '<mxCell id="3" value="Übersicht" style="{style}" vertex="1" parent="1"/>'
    "</root></mxGraphModel></diagram></mxfile>"
)


def write(path: Path, text: str, newline: str = "\n") -> Path:
    """Write text to path with the given line end, creating the parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline=newline)
    return path


def svg(model: str) -> str:
    """Return a .drawio.svg whose content attribute embeds model, as draw.io writes it."""
    content = html.escape(model, quote=True)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="10px" content="{content}"></svg>\n'


def model(style: str = "rounded=0;") -> str:
    """Return a small uncompressed draw.io model; style is the second cell's style."""
    return MODEL.format(style=style)


def record(status: str = "current", extra: str = "", body: str = "") -> str:
    """Return a version record: frontmatter with status and extra lines, then body."""
    return (
        "---\n"
        f"status: {status}\n"
        "date: 2026-10-13\n"
        "author: Test Person <test@example.com>\n"
        "related: []\n"
        f"{extra}"
        "---\n\n"
        "# Title\n\n"
        f"{body}"
    )


def mermaid_record(block: str, status: str = "current") -> str:
    """Return a Mermaid version record whose single fence holds block."""
    return record(status, "format: mermaid\n", f"```mermaid\n{block}\n```\n")


def index(*stems: str) -> str:
    """Return a README.md index that links each stem's record."""
    rows = "".join(f"| [{stem}]({stem}.md) | current |\n" for stem in stems)
    return f"# Index\n\n| Version | Status |\n|---|---|\n{rows}"


def drawio_version(directory: Path, stem: str = "0001-first", status: str = "current") -> None:
    """Write one draw.io version (both files) into directory."""
    write(directory / f"{stem}.drawio.svg", svg(model()))
    write(directory / f"{stem}.md", record(status))
