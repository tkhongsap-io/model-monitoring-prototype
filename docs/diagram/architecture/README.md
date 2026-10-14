# Architecture

Components and the boundaries between them. One picture per subject: the GCP test host and
AWS production run side by side during the cut-over week (S4-02), so each has its own line
of versions. Policy: [`.agents/rules/diagram.md`](../../../.agents/rules/diagram.md).

| Subject | About |
|---|---|
| [`gcp-test-host`](gcp-test-host/README.md) | Phase 1: the GCP test host (Sprints 1 to 3), as it runs. Versions 0001 and 0002 show both phases in one picture. |
| [`aws-production`](aws-production/README.md) | Phase 2: AWS production (Sprint 4). |

Until 2026-10-14 this type held one picture of the whole project. The review of #89 split
it into the two subjects above, as in `deployment/`: with one line of versions, AWS
becoming `current` would supersede the test host while it still runs as the fallback. The
versions moved into `gcp-test-host/` with their numbers; the AWS picture became
`aws-production` 0001.
