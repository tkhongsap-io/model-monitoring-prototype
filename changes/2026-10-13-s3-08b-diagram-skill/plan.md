# Plan: diagram skill and one versioned architecture diagram (S3-08b)

Intent: `intent.md`. Spec: `spec.md`. One pull request to `dev`, one commit for each slice.

| Slice | Work | Done when |
|---|---|---|
| 1 | Intent, spec and plan; S3-08b in `issues.md` | `test_docs.py` passes |
| 2 | Copy and adapt the skill, the rule and `docs/diagram/`; `.claude-plugin/`; the CI workflow | `check_diagrams.py` exits with 0 on the empty records |
| 3 | Architecture `0001`: build the model from the two drafts, export, read the preview, write the record and the index | The check and the label scan pass; the preview reads cleanly |
| 4 | `docs/architecture/README.md`, `README.md`, `CHANGELOG.md`, `DEVLOG.md` | The fast suite passes |

## Rollback

Revert the pull request. Nothing reads the new files at run time.

## Follow-up (not in this pull request)

- `data-flow` / `batch-run` and `sequence` / `batch-run-ingest` (Must, #85).
- A new architecture version when a part of the picture is built in a different way, or a
  change of status to `current` when the build agrees with the picture.
- A maintainer sets the labels, the assignee and the parent link of #85. The account that
  opened it has no permission for them.
