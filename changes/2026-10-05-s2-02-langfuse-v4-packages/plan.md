# Plan — S2-02 slice 1

1. Write `tests/test_llm_eval_local_store.py`. Make sure that it fails.
2. Remove `LangfuseCloudStore` from `stores.py`.
3. Make `judge.py` and `live_http.py` use only `SqliteTraceStore`.
4. Change `backend/requirements.txt` to the approved ranges. Install them in a new venv.
5. Run the fast suite and the full suite.
6. Add the package rows to the fixed-versions table in `issues.md`.
7. Update `CHANGELOG.md` and `DEVLOG.md`. Open one pull request for #16.

## Remaining S2-02 work (after this slice)

- Add the `monitor.evaluate` span and `create_score` with SDK v4 (needs S1-05 part B).
- Make sure that one trace holds the GCP spans and the monitor spans (needs S2-03).
