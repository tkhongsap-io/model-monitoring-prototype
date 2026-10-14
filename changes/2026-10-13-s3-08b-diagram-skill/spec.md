# Spec: diagram skill and one versioned architecture diagram (S3-08b)

Intent and decisions: `intent.md` in this folder.

## Files

| File | Change |
|---|---|
| `.agents/skills/diagram/**` | New. Copied from `project-template` (commit `9b1339d`): `SKILL.md`, `references/`, `scripts/`, `assets/examples/`, `evals/` |
| `.agents/rules/diagram.md` | New. The policy: types, subjects, statuses, format, icons |
| `docs/diagram/README.md`, `TEMPLATE.md`, `icons/README.md` | New. The index, the record template, the icon register (empty) |
| `docs/diagram/architecture/README.md`, `0001-gcp-test-host-and-aws-production.drawio.svg`, `.md` | New. The first version and its record |
| `.claude-plugin/plugin.json`, `marketplace.json` | New. Claude Code finds the skills in `.agents/skills` |
| `.github/workflows/check-diagrams.yml` | New. Runs `check_diagrams.py` |
| `docs/architecture/README.md`, `README.md`, `issues.md` (S3-08b), `CHANGELOG.md`, `DEVLOG.md` | Docs |

No pip or npm package. The five scripts use only the Python standard library.

## Adaptations of the copied skill

The template has files that this repository does not have. The text changes; the scripts do
not.

| The template names | This repository uses |
|---|---|
| `CONTEXT.md` (vocabulary) | The glossary in `changes/2026-10-02-batch-monitoring-mvp/plan.md` |
| The `verify` skill, the pre-commit gate, the six-document check | `TESTING.md`, `CHANGELOG.md`, `DEVLOG.md`, and the CI check |
| ADR-0008, ADR-0009, ADR-0010 | Removed. They are ADRs of the template. |
| All ten types in `docs/diagram/README.md` | The types for this repository, as Must or Nice to have |
| A Markdown image in `TEMPLATE.md` | An `<img>` tag. The existing link test in `backend/tests/test_docs.py` reads a Markdown image of a placeholder as a broken link, and the test must not change. |

The docstrings of the scripts still name the pre-commit gate of the template. They are not
changed, so that a later copy from the template is a clean copy.

`references/drawio.md` gets the icon styles that the drafts use and that render: the GCP
`hexIcon` stencils, and the AWS icons and shapes of the production detail.

## Claude Code discovery

`.claude-plugin/plugin.json` names `./.agents/skills` as the skills folder, and
`marketplace.json` makes the repository its own marketplace (`model-monitoring-prototype`,
plugin `model-monitoring-tools`). `.claude/` is in `.gitignore`, so the setting that turns
the plugin on is not in git. Each person adds it one time to `.claude/settings.json`:

```json
{
  "enabledPlugins": { "model-monitoring-tools@model-monitoring-prototype": true },
  "extraKnownMarketplaces": {
    "model-monitoring-prototype": { "source": { "source": "directory", "path": "./" } }
  }
}
```

Codex reads `.agents/skills` with no setting.

## CI check

`.github/workflows/check-diagrams.yml`: `ubuntu-latest`, timeout 5 minutes,
`permissions: contents: read`, no secrets. It runs on `pull_request` and on `push` to `dev`
for the paths `docs/diagram/**`, `.agents/skills/diagram/scripts/**` and the workflow file.
One step: `python .agents/skills/diagram/scripts/check_diagrams.py` with Python 3.12.

## Architecture 0001

One picture, about 3700 by 1400 units. Phase 1 is a panel on the left. Phase 2 is a panel on
the right. Each panel has its own actors, because the path of each actor is different in
each phase. The key, the data scope, the fixed versions and the change from phase 1 to
phase 2 are boxes below phase 1.

The model is built from the two drafts (`render.py extract`). The phase 2 cells keep their
positions from the AWS production detail draft.

**Phase 1 corrections** (sources: `issues.md` S1-04, Sprint 2 prerequisites, S2-03, S3-07;
`deploy/compose`, `deploy/nginx`, `deploy/langfuse`): plain HTTP on port 80; dashboard on
8080 and Langfuse on 3000; Langfuse only through the IAP tunnel; no OAuth2 Proxy, no
dashboard SSO, no Cloud DNS; VM `n4-highmem-4`, Debian 12, 100 GB; Cloud SQL holds only
`monitor`, and Langfuse has its own PostgreSQL 17.11 container.

**Phase 1 additions:** the Compose projects `model-monitor` and `langfuse`, the `edge`
network, the trace check tool, the two outputs of the Collector, the firewall rules.

**Phase 2 additions** (sources: `issues.md` S3-06, S3-07, S4-01, S4-02): the ingress routes,
the flow from the backend to Langfuse, the path through Cloud NAT, plan B, the fallback
without a DNS name. One RDS instance for both databases stays as drawn and is item 9 of
"Assumptions and items to verify" (plan A has one instance for each).

**Not in the drawing:** the words "planned" or "proposed". The record has the table "Built
and not built", so the drawing does not change when a part is built.

## Added 2026-10-13: record without draw.io, and `.claude` in git

This section replaces three statements above: "The text changes; the scripts do not",
"The five scripts", and the section "Claude Code discovery". The CI check becomes a
matrix. No pip or npm package is added.

### Mermaid version

- One file, `NNNN-slug.md`. Its frontmatter has `format: mermaid`. A record with no
  `format` is a draw.io version, so the 10 recorded versions do not change.
- The record has exactly one `mermaid` code block, where a draw.io record has the image.
  There is no `NNNN-slug.drawio.svg`.
- The first line of the block is the keyword of the type:

| Type | Keyword |
|---|---|
| `sequence` | `sequenceDiagram` |
| `state` | `stateDiagram-v2` |
| `er` | `erDiagram` |
| `class` | `classDiagram` |
| every other type | `flowchart` and a direction |

- The check refuses: an `%%{` directive, a `---` configuration block, `click`, `href`, a
  URL, and the tags `img`, `a`, `script`, `iframe`, `object`, `embed`, `style`.
- A Mermaid version has no product icons and no image file.
- `erDiagram` needs a type for each column, and the rule shows no data types. Every
  column has the constant type `col`.

### Scripts

| Script | Change |
|---|---|
| `render.py` | Searches the install places of each operating system. A new `doctor` command reports draw.io: exit 0 found, 1 not installed, 2 `DRAWIO_BIN` is wrong. `extract` reads the embedded model with no draw.io. `labels` prints the block of a Mermaid version. The output of draw.io is read as UTF-8. |
| `mermaid_block.py` | New. Finds the block in a record and lists what is wrong with it. |
| `check_diagrams.py` | Accepts a `format: mermaid` version: the `.md` only, with the block checks. Prints UTF-8. |
| `fetch_icon.py`, `icon_safety.py`, `icon_style.py` | No change. |

`.agents/skills/diagram/tests/` is new: `unittest` tests of the three scripts above, with
files in a temporary directory.

### Skill and rule

`SKILL.md` runs `render.py doctor` at the end of step 1. Exit 1 selects Mermaid; exit 2
stops. Step 5 (icons) is for draw.io only. Step 6 has a Mermaid branch. The report says
why Mermaid was used and that no rendered picture was inspected. `references/mermaid.md`
is new: the keyword of each type, one example for each keyword, what the check refuses,
and what to read in the text. The ten type references do not change.

`.agents/rules/diagram.md` and `docs/diagram/README.md` describe the two formats.

### Claude Code discovery

| File | Change |
|---|---|
| `.gitignore` | `.claude/*` is ignored, except `.claude/rules/` and `.claude/skills/`. `settings.json` and `settings.local.json` stay personal. |
| `.claude/rules/diagram.md` | In git. It imports `.agents/rules/diagram.md` for files under `docs/diagram/`. |
| `.claude/skills/diagram/SKILL.md` | New. The same `name` and `description` as the skill, and one instruction: read and follow `.agents/skills/diagram/SKILL.md`. A test compares the two descriptions. |
| `.claude-plugin/` | Removed. A person with the plugin on would see the skill two times. |

Codex reads `.agents/skills` with no setting, as before.

### CI check

`check-diagrams.yml` runs on `ubuntu-latest`, `macos-latest` and `windows-latest`
(`fail-fast: false`, Python 3.12): first
`python -m unittest discover -s .agents/skills/diagram/tests`, then `check_diagrams.py`.
The paths are `docs/diagram/**`, `.agents/skills/diagram/**`,
`.agents/rules/diagram.md`, `.claude/**` and the workflow file, because a test compares
the pointers in `.claude/` with the skill and the rule.

### Verification of this addition

1. The script tests pass.
2. `check_diagrams.py` exits with 0 on the 10 recorded versions.
3. `render.py doctor` exits with 0 with draw.io installed and with 2 when `DRAWIO_BIN`
   names no file. A test covers exit 1.
4. `render.py extract` on a recorded version gives a model that draw.io exports again.
5. A new Claude Code session lists `diagram`.
6. macOS and Linux have no local evidence: only the CI matrix shows them, after a push.
   That GitHub draws each example in `references/mermaid.md` is also seen after a push.

## Verification

1. `uv run .agents/skills/diagram/scripts/check_diagrams.py` exits with 0.
2. `render.py labels` on `0001`: none of `8443`, `3443`, `e2-standard-8`, `Ubuntu`,
   `200 GiB`, `private CA`, `Cloud DNS`, `18 for the monitor`, `Token Factory`; no IP
   address; no URL. "judge" is only in the sentence "There is no judge".
3. The PNG preview is read as an image: no overlapping labels, no edge through a box, no
   empty icon.
4. The fast backend suite, with `test_docs.py` unchanged.
5. `git diff --stat dev` shows only new files and the docs in the table.
