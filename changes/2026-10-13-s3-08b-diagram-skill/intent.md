# Intent: diagram skill and one versioned architecture diagram (S3-08b)

- **Status:** Accepted (plan approved in chat by @Prakasit-Iss on 2026-10-13)
- **Issue:** S3-08b (#85), sub-issue of S3-08a (#81)
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09). This change is documentation
  and agent tooling. It does not change the backend, the frontend or the deploy files.
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S3-08b

## Problem

The recheck of the S3-08a architecture draft (#81) found 7 differences between the GCP test
host diagram and the plan and deploy files. The drafts in `docs/architecture/` were drawn by
hand, so nothing keeps them in step with the repository. The drafts also do not show the
data scope (identity-only) or the fixed versions, which #81 asks for.

## Outcome

The `diagram` skill from `project-template` is in this repository. It records each diagram
as a numbered draw.io version in `docs/diagram/`, and a check examines the records without
draw.io. One architecture diagram, version `0001`, holds both phases of the MVP in one
picture: phase 1 (the GCP test host) and phase 2 (AWS production). It starts from the two
drafts, corrects them and adds the missing detail.

## Decisions (@Prakasit-Iss, 2026-10-13)

| Decision | Reason |
|---|---|
| Phase 1 and phase 2 are in one picture and one file, side by side | One architecture for the consultation and the AF Slide |
| The work is the skill and the documentation only. No existing test, workflow or application file changes. | No change to the behavior of this repository |
| Wiring: the skill files, Claude Code discovery, and a CI check | The check keeps the records correct without a person |
| `docs/diagram/README.md` lists the diagram types that relate to this repository, as Must or Nice to have | The other Must types are the next work |
| Type `architecture`, single. Version `0001`, status `proposed`. | The picture shows an end state that is partly not built. The record lists what is built. |
| The three drafts stay in `docs/architecture/`, unchanged | The links in #81 keep working |
| No IP address, token or internal URL in a diagram | The same rule as the scan of the first drafts |

## Success criteria

- `check_diagrams.py` exits with 0, locally and in CI.
- The labels of version `0001` contain none of the 7 old values.
- The fast backend suite passes with no change to an existing test.
- `git diff --stat dev` shows no file under `backend/app`, `artifacts/`, `deploy/` or the
  existing workflows.

## Not in scope

The `data-flow` and `sequence` diagrams (Must, follow-up in #85). The Nice-to-have types.
The consultation with K. Wirat (S3-08a). The AF Slide (S3-08).
