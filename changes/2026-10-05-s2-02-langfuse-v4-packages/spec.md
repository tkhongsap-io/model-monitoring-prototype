# Spec — S2-02 slice 1

## Packages (approved 2026-10-05)

| Package | Range | Added in | Reason |
|---|---|---|---|
| `langfuse` | `>=4.16,<5` | This slice (replaces `>=2.53,<3`) | SDK v4 for the `monitor.evaluate` span and `create_score` |
| `opentelemetry-api` | `>=1.45,<2` | This slice | `langfuse` 4.x needs it. S1-05 part B uses the same range. |
| `opentelemetry-sdk` | `>=1.45,<2` | This slice | The same |
| `opentelemetry-exporter-otlp-proto-http` | `>=1.45,<2` | This slice | The same |
| `opentelemetry-instrumentation-fastapi` | `>=0.66b0,<0.67` | S1-05 part B | The FastAPI spans. 0.66b0 is the release for OTel 1.45. |

Checked on PyPI on 2026-10-05: `langfuse` 4.17.0 needs OTel `>=1.45.0,<2`. The newest OTel
release is 1.45.0. The fixed-versions table in
[`issues.md`](../2026-10-02-batch-monitoring-mvp/issues.md#fixed-versions-checked-2026-10-03)
has the same rows.

## Behavior

1. `app.adapters.llm_eval.stores` has no `LangfuseCloudStore`.
2. `SeededJudgeAdapter` uses `SqliteTraceStore` for both names, `langfuse_stub` and
   `langfuse_cloud`, also when the Langfuse keys are set.
3. `LiveHttpLLMAdapter` uses `SqliteTraceStore`, also when the Langfuse keys are set.
4. No module in `app/adapters/llm_eval/` imports `langfuse`.
5. These stay the same: the score write-back through the producer (`push_scores`), the
   Langfuse settings in `config.py`, and the strict-live check for the Langfuse keys. The
   SDK v4 work in S2-02 uses these keys.

## Tests

`backend/tests/test_llm_eval_local_store.py` covers items 1 to 4. The full backend suite
proves that the grades and the golden bake do not change.
