# S2-02 slice 1 — Langfuse SDK v4 packages and removal of the v2 store

## Outcome

The backend can install the Langfuse SDK v4 and the OTel packages that the batch MVP needs.
No code calls the deprecated Langfuse SDK v2 functions `trace()` and `score()`.

## Why now

S2-02 (#16) depends on S1-05 for its trace check. S1-05 part B waits for S1-02, and S1-02
waits for the S1-01 schema confirmation. The package approval and the removal of the
prototype-only store do not wait for these issues, so this slice does them first.

## Scope

- In: the approved package list with version ranges, `backend/requirements.txt`, the
  removal of `LangfuseCloudStore`, tests, `CHANGELOG.md`, `DEVLOG.md`.
- Out: the `monitor.ingest` and `monitor.evaluate` spans, `create_score`, and the
  FastAPI instrumentation. These need S1-05 part B and S2-03.

## Risk tier

R1, the same as the project. The change removes a best-effort push to Langfuse Cloud from
the prototype chatbot judge. The grades do not change, because the local store and the
producer score write-back stay the same.

## Approval

The project owner approved the packages in chat on 2026-10-05.
