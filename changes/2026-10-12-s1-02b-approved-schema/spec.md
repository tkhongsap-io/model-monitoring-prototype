# S1-02b — The receiver agrees with the approved S1-01 schema

| | |
|---|---|
| **Issue** | [#44](https://github.com/tkhongsap-io/model-monitoring-prototype/issues/44) (S1-02b) |
| **Depends on** | S1-01 (#3), closed 2026-10-09; S1-02 (#41), merged |
| **Risk tier** | R1, the same as S1-02. One validation module, its tests and docs. |
| **Scope** | Option B, chosen by the owner on 2026-10-12: descriptions, file move, and the two record rules. Rule 1 is a note only (owner, 2026-10-12). |

## Outcome

`backend/app/batch_schema.py` and the schema file agree, with no DRAFT note. The schema and
its examples are in the backend (`backend/schemas/batch-run/1/`). The two decided record
rules that break no stored row are enforced.

## Compare: approved schema and `BatchRunV1`

Each field, type, length, required list and `allOf` rule was compared on 2026-10-12.

| Area | Result |
|---|---|
| Top-level fields, types, lengths, required list | Same. `Identifier`, the UTC pattern, `model` 1–128, counts ≥ 0. |
| `sample`, `records[]`, `retrieval_context[]`, `tool_calls[]` | Same, with `additionalProperties: false` at every level. |
| `latency_s` | Same: required, number above 0 or `null`. |
| `allOf` (request_count 0, empty records, records present, failed run) | Same. The code puts each error on the field. |
| `submitted_at` | Same (added with #57). |
| Timestamps | The code also rejects a date that is not on the calendar (`2026-13-40`). This is stricter than the schema pattern, not a difference in meaning. |
| Backend-only rules (README) | Same, except the change below. |

Differences found against the decisions of 2026-10-08 (issue #3), and what this change does:

| # | Decided rule | Before | Now |
|---|---|---|---|
| 1 | `completed` means `failed_count` 0; `partial` means `failed_count` above 0 | Not enforced | **Note only** (owner, 2026-10-12). Applies to every run; example `04-identity-only.json` breaks it, and stored rows can have that shape, so a check would need `batch-run/2`. Metrics read `failed_count`, not `status`. |
| 2 | Records only from answered or refused requests | Records ≤ `request_count` | Records ≤ `request_count` − `failed_count` (backend rule; error on `records`) |
| 3 | `refused: true` means `answer: ""` | Not enforced | Enforced in the schema (`if`/`else` on the record) and the code (error on `records[i].answer`) |
| — | Descriptions | DRAFT, `job_failed` "PROPOSED", "to fill in" notes, 4 `finishReason` values | Approved text; the 2026-10-08 answers for `question`, `answer`, `retrieval_context`, `refused` (7 `finishReason` values) |

## Schema version

It stays `batch-run/1`. Rules 2 and 3 apply only to records. Every run in Sprint 1 is
identity-only (`records: []`), so no stored row can break them.

## Files

- Moved: `changes/2026-10-02-batch-monitoring-mvp/schema/{batch-run-1.schema.json,examples/}`
  to `backend/schemas/batch-run/1/`. The schema README stays in the change folder as the
  S1-01 review record.
- New invalid examples: `records-from-failed-requests.json`, `refused-with-answer.json`.
- Code: `backend/app/batch_schema.py`. Tests: `test_batch_schema.py`,
  `test_batch_runs_api.py`, `test_batch_runs_tracing.py` (new path).
- Paths: `scripts/compose-smoke.sh`, `deploy/compose/README.md`. Older plans in `changes/`
  keep the old path as history.
- Docs: `docs/STRICT-LIVE.md`, `CHANGELOG.md`, `DEVLOG.md`.

## Done when

- The fast backend suite passes. Each valid example passes; each invalid example fails with
  its expected field.
- The schema file has no DRAFT or PROPOSED text and its `schema_version` const is
  `SCHEMA_VERSION`.
- A JSON Schema 2020-12 validator agrees with the backend on all examples, except the
  backend-only rule 2.
