# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Find and check the Mermaid block of a diagram version recorded without draw.io.

A version whose record has ``format: mermaid`` in its frontmatter is one file,
``NNNN-slug.md``, with exactly one ``mermaid`` code block where a draw.io record has its
image. GitHub draws the block, so recording needs no tool on any platform. This module is
used by check_diagrams.py and render.py, and needs nothing but the standard library.

    uv run .agents/skills/diagram/scripts/mermaid_block.py TYPE RECORD.md [RECORD.md ...]

It checks what can be checked without a Mermaid parser:

- the record has exactly one closed ``mermaid`` block, and the block is not empty
- the block opens with the keyword of the type (KEYWORDS; ``flowchart`` and a direction
  for every other type), so GitHub knows the syntax and the type keeps its notation
- the block has no directive (``%%{``), no ``---`` configuration block, no ``click`` or
  ``href``, no URL, and none of the tags in TAGS: a diagram depends on nothing outside
  its file, the same rule as an embedded image in a draw.io version

It does not prove that the block renders: the first rendered view is GitHub's.
references/mermaid.md has one example for each type to start from. Exits 1 and prints
one line per problem.
"""

import re
import sys
from pathlib import Path

OPEN = "```mermaid"
CLOSE = "```"
KEYWORDS = {
    "sequence": "sequenceDiagram",
    "state": "stateDiagram-v2",
    "er": "erDiagram",
    "class": "classDiagram",
}
FLOWCHART_TYPES = {"architecture", "workflow", "deployment", "use-case", "data-flow", "decision"}
FLOWCHART = re.compile(r"^flowchart (TB|TD|BT|LR|RL)$")
URL = re.compile(r"https?://|\bwww\.", re.IGNORECASE)
TAGS = re.compile(r"<\s*(img|a|script|iframe|object|embed|style)\b", re.IGNORECASE)
LINK = re.compile(r"^click\s|\bhref\b")


def blocks(text: str) -> list:
    """Return the body of every ``mermaid`` block in text; None for one that never closes."""
    found = []
    body = None
    for line in text.splitlines():
        if body is None:
            if line.rstrip() == OPEN:
                body = []
        elif line.rstrip() == CLOSE:
            found.append("\n".join(body))
            body = None
        else:
            body.append(line)
    if body is not None:
        found.append(None)
    return found


def block(md: Path) -> str:
    """Return the body of the single Mermaid block in md; raise ValueError when it has none."""
    found = blocks(md.read_text(encoding="utf-8"))
    if len(found) != 1 or found[0] is None:
        raise ValueError(f"{md} does not hold exactly one closed mermaid block")
    return found[0]


def keyword_problem(first: str, diagram_type: str) -> list:
    """Return the problem with the block's first line for this type, if any."""
    allowed = set(KEYWORDS.values())
    if diagram_type in KEYWORDS:
        expected = KEYWORDS[diagram_type]
        if first != expected:
            return [f"a {diagram_type} block starts with '{expected}', not {first!r}"]
    elif diagram_type in FLOWCHART_TYPES:
        if not FLOWCHART.match(first):
            return [f"a {diagram_type} block starts with 'flowchart' and a direction, not {first!r}"]
    elif first not in allowed and not FLOWCHART.match(first):  # a type the project added
        return [f"the block starts with {first!r}; expected flowchart or {sorted(allowed)}"]
    return []


def body_problems(body: str, diagram_type: str) -> list:
    """Return what is wrong with the body of a Mermaid block for this type."""
    lines = [line.strip() for line in body.splitlines()]
    problems = []
    if any(line.startswith("%%{") for line in lines):
        problems.append("a %%{ directive; the block keeps GitHub's default look")
    statements = [line for line in lines if line and not line.startswith("%%")]
    if not statements:
        return problems + ["the mermaid block is empty"]
    if statements[0] == "---":
        return problems + ["a --- configuration block; the block starts with its keyword"]
    problems += keyword_problem(statements[0], diagram_type)
    if len(statements) == 1:
        problems.append("the mermaid block has a keyword and nothing drawn")
    for line in statements[1:]:
        if LINK.search(line):
            problems.append(f"a link (click or href): {line}")
        if URL.search(line):
            problems.append(f"a URL: {line}")
        tag = TAGS.search(line)
        if tag:
            problems.append(f"the tag <{tag.group(1).lower()}>: {line}")
    return problems


def record_problems(md: Path, diagram_type: str) -> list:
    """Return what is wrong with the Mermaid block of one version's record."""
    found = blocks(md.read_text(encoding="utf-8"))
    if not found:
        return ["format is mermaid, but the record has no ```mermaid block"]
    if None in found:
        return ["a ```mermaid block is not closed"]
    if len(found) > 1:
        return [f"{len(found)} mermaid blocks; a version is one picture"]
    return body_problems(found[0], diagram_type)


def main() -> None:
    """Check the records named on the command line as versions of the given type."""
    if len(sys.argv) < 3:
        sys.exit(__doc__.split("\n\n")[1].strip())
    diagram_type = sys.argv[1]
    problems = []
    for name in sys.argv[2:]:
        problems += [f"{name}: {problem}" for problem in record_problems(Path(name), diagram_type)]
    for problem in problems:
        print(problem.replace("\\", "/"))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
