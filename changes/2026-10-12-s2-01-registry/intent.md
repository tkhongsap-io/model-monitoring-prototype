# Intent: source registry of the batch use cases (S2-01)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-12)
- **Issue:** S2-01 (#15)
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09)
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S2-01

## Problem

The monitor knows a use case only from an API key entry `USE_CASE_ID:<sha256>` in
`BATCH_API_KEY_SHA256`. There is no list of use cases with their settings, so a key for any
use case ID is accepted, and S2-05 (the `turnaround_s` limit, band overrides), S3-02 (the
expected schedule) and S2-06 (onboarding) have no place to read their settings from.

## Outcome

A reviewed YAML registry in the backend image lists each batch use case with its October
settings. The backend does not start with a bad registry. A key for a use case that is not
registered gives `403`, and readiness reports a key entry for an unregistered use case.
`scripts/batch_keys.py` makes, adds, lists and removes key entries without showing a key
or a full hash.

## Decisions (project owner, 2026-10-12)

| Decision | Reason |
|---|---|
| The key hashes stay in the backend env file (`BATCH_API_KEY_SHA256`), not in a database table (option B; the plan had a table) | Rotation already works with two entries for one use case; removing a key needs only a restart (seconds), which a daily batch job does not mind. No migration and no script with the database write user. On AWS the env file becomes a Kubernetes Secret. |
| The registry is `backend/registry/batch-use-cases.yaml`, inside the image | Each image carries its own reviewed registry; a change is a pull request and a new image |
| October fields only: ID, name, owner, developer, mode, schedule, `turnaround_limit_s`, data classification, band overrides | Identity-only MVP. The task description, the profile and the sample size come back with `SEND_RECORDS`; the loader rejects them until then. |
| `scripts/batch_keys.py` uses only the standard library, writes the key and the hash line to mode-600 files, and prints only file names and 8-character hash prefixes | It runs on the laptop and on the VM host with no install. The project owner runs it; Claude never sees a key or a hash. |
| The local stack and the CI smoke test use the real use case `rtr-fraud-validation` with the local test key (changed from `GCP-UC-03`) | The production registry gets no test entry. The unit tests use their own registry file under `backend/tests/`. |

## Success criteria

- The registry, API and script tests pass; the CI smoke test passes.
- On the test host after the next image: readiness `ready`, and a request with the existing
  `rtr-fraud-validation` key still gives `201`.
