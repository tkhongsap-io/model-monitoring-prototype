# Intent: local Docker Compose stack with the OTel Collector (S1-06, local part)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-07)
- **Issue:** S1-06 (#8), local part only. The test-host part (front door on port 443,
  `/otlp/*` with the OTLP token, `compose.testhost.yaml` with Cloud SQL and the Artifact
  Registry image) comes with S1-04.
- **Risk tier:** R2, the batch MVP tier (`changes/2026-10-02-batch-monitoring-mvp/intent.md`).
  Local and CI only; no real data.
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S1-06

## Problem

The repository has no Compose file and no Collector configuration. Nobody can see the
spans of #48 end to end, S1-07 (trace check tool) has no stack to read, and the S1-10
fallback ("replay a saved real body into the local stack") has no local stack.

## Outcome

One command starts the backend (the S1-13 app), PostgreSQL 18.6 and the OTel Collector
0.161.0 on a laptop or a CI runner. A `POST /api/batch/runs` with a `traceparent` stores
one row, and the `monitor.ingest` span appears in the Collector file with the same trace
ID. A smoke test proves this in CI on each change and on the project owner's Mac.

## Decisions (project owner, 2026-10-07)

| Decision | Reason |
|---|---|
| Proof: a CI smoke test, plus a hand test on the project owner's Mac | Docker does not run on the Windows development computer |
| Files: a base `compose.yaml` and one file for each environment (`compose.local.yaml` now, `compose.testhost.yaml` with S1-04) | The test host reuses the backend and Collector definition that CI tested |
| ~~The Collector writes its file to `/tmp`~~ **Changed 2026-10-07:** the Collector writes `/data/spans.jsonl` in the named volume `collector-data`; a one-time `collector-init` service (`busybox:1.37.0`) gives the volume to uid 10001 first. The smoke test reads the file with `docker compose cp`. | The first CI run of #54 failed: the distroless Collector image has **no `/tmp`**. The Collector runs as uid 10001, a new volume belongs to root, and the image has no shell. The Collector stays non-root. The file output is temporary until S2-03. |
| Local ports are published on `127.0.0.1` only; PostgreSQL is not published | A laptop stack must not be reachable from the network |
| A fixed, documented local test key (`local-dev-batch-key-not-a-secret`) | The smoke test needs a key; only its hash is in the file, and it is not a secret |

## Success criteria

The CI smoke test passes on the pull request, and the smoke test passes on the Mac.
