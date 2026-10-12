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

## Verification

1. `uv run .agents/skills/diagram/scripts/check_diagrams.py` exits with 0.
2. `render.py labels` on `0001`: none of `8443`, `3443`, `e2-standard-8`, `Ubuntu`,
   `200 GiB`, `private CA`, `Cloud DNS`, `18 for the monitor`, `Token Factory`; no IP
   address; no URL. "judge" is only in the sentence "There is no judge".
3. The PNG preview is read as an image: no overlapping labels, no edge through a box, no
   empty icon.
4. The fast backend suite, with `test_docs.py` unchanged.
5. `git diff --stat dev` shows only new files and the docs in the table.
