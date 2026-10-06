# Plan: `POST /api/batch/runs` (S1-02)

One pull request, branch `feat/s1-02-batch-runs-api`. Write each test before its code.

| Step | Work | Done when |
|---|---|---|
| 1 | `backend/tests/test_batch_schema.py`: the five valid S1-01 examples pass, the three invalid examples fail, plus one test per backend rule | Tests fail (no module) |
| 2 | `backend/app/batch_schema.py`: Pydantic model `BatchRunV1` and `validate_run(raw)` | Step 1 tests pass |
| 3 | `backend/tests/test_batch_runs_api.py`: each acceptance criterion of #4 through the strict-live middleware; traceparent parse; logs contain no key or body | Tests fail |
| 4 | `db.py`: table `batch_runs`, migration 8, `put_batch_run`, `get_batch_run`, `list_batch_runs` | Persistence tests pass |
| 5 | `config.py`: `BATCH_API_KEY_SHA256`, `BATCH_MAX_BODY_BYTES`, malformed-entry check | Config tests pass |
| 6 | `backend/app/api/batch_routes.py`; mount in `main.py`; allow the POST in `strict_live_route_isolation` | Step 3 tests pass |
| 7 | Docs: `README.md`, `docs/STRICT-LIVE.md`, `CHANGELOG.md`, `DEVLOG.md` | `tests/test_docs.py` passes |
| 8 | Fast suite, `scripts/migrate.py` twice, diff review, commit, push, PR that references #4 | Evidence in DEVLOG and PR |

Rollback: revert the PR. Migration 8 only adds a table; an unused table is harmless.
