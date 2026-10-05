# Intent: Receive GCP batch run summaries (S1-02)

- **Status:** Accepted
- **Originator:** project owner, GitHub issue [#4](https://github.com/tkhongsap-io/model-monitoring-prototype/issues/4)
- **Date:** 2026-10-05
- **Risk tier:** R1 — assisted internal workflow. The endpoint stores evidence for humans.
  It never acts on a model and never moves a v1.1 telemetry cursor.
- **Plan of record:** [S1-02 in issues.md](../2026-10-02-batch-monitoring-mvp/issues.md#s1-02--receiving-api-post-apibatchruns-with-api-key)

## Problem

The October batch MVP grades GCP batch jobs. The jobs push one run summary after they
publish their results (S1-03). The monitor has no endpoint that can receive this summary.
Without it, no later issue (evaluator, dashboard, trace check) has data.

## Proposed outcome

A GCP job sends `POST /api/batch/runs` with its API key. The monitor examines the key and
the body, and stores the run one time in `batch_runs`. A retry of the same run is safe. A
changed run with the same ID is refused and the first row stays unchanged.

## Users and systems affected

- GCP job developers (S1-03): the sender.
- The monitor backend: one new route, one new table (migration 8), two new settings.
- The v1.1 pull path for `AICT-L01..L03`: unchanged.

## Constraints

- The body follows the S1-01 **draft** schema `batch-run/1`. The schema is not approved
  yet, so all of its rules are in one Pydantic model (`backend/app/batch_schema.py`).
- No new pip or npm packages. No OpenTelemetry packages (S1-05 part B adds them).
- The key and the body are never written to a log. Only the SHA-256 hash of a key is
  configured.
- Stored rows never change. The migration is additive.

## Open items (not in this slice)

- The plan (DEVLOG 2026-10-02) asks for an ADR on push ingestion, because the contract
  is pull-only. This slice adds the endpoint as the issue specifies; the ADR is still open.
- The registry (S2-01) replaces the `BATCH_API_KEY_SHA256` setting and adds the
  per-use-case sample-size range (8 to 200).

## Decision

Accepted 2026-10-05: build against the draft schema, as the issue allows.
