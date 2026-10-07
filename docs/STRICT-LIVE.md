# Strict live control tower

> **Prototype only, except "Batch run receiver".** This page describes the Replit
> prototype for the three `ai-use-cases` models. The "Batch run receiver" section is
> for the batch MVP (S1-02). Replit is not a release target. CI does not deploy to Replit
> and does not wake it (the `autoscale-poll.yml` schedule was removed on 2026-10-05).
> The batch MVP releases to the GCP test host (S1-04) and then to production AWS (S4-01);
> see [the batch MVP plan](../changes/2026-10-02-batch-monitoring-mvp/plan.md).

Set `CONTROL_TOWER_MODE=live` for the deployed monitor. In this mode the backend does
not bake or reset `DEMO-FULL`, does not seed the simulated registry, and returns 404 for
scenario, simulation, export, baked artifact, and browser-driven tick routes.

## Required deployment configuration

- `DATABASE_URL`: managed PostgreSQL; SQLite is rejected by readiness.
- `LIVE_CHURN_URL`, `LIVE_CHATBOT_URL`, `LIVE_NBA_URL`: external telemetry service URLs.
- `LIVE_PRODUCER_URL`: portfolio gateway used for observation acknowledgements.
  All four must be `https://` (the bearer token travels with every call); `http://` or a
  localhost address is a configuration error.
- `LIVE_TELEMETRY_TOKEN`: shared bearer token used for pulls, score write-back, and ack.
- `LIVE_WORKER_TOKEN`: dedicated bearer token for `POST /api/live/poll`. The manual
  GitHub Actions workflow uses the same value as secret `MONITOR_WORKER_TOKEN` (never
  expose it to the SPA).
- `ANTHROPIC_API_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
- `LIVE_POLL_SECONDS` greater than zero; `LIVE_POLL_LEASE_SECONDS` defaults to 30.
- Optional: `LOG_FORMAT=json` for one JSON object per log line (default plain text);
  `LIVE_ALERT_WEBHOOK_URL` and `LIVE_DASHBOARD_URL` (see Alerting);
  `BATCH_API_KEY_SHA256` and `BATCH_MAX_BODY_BYTES` (see Batch run receiver).

`GET /api/readiness` returns HTTP 503 and `not_ready` until the durable database,
external URLs, tokens, poller, and judge configuration are present. Health endpoints
also return 503 for an invalid strict-live configuration. `ALLOW_INSECURE_LIVE_TESTING=1` is the only
bypass and is intended solely for isolated automated tests.

## Runtime behavior

The producer remains a Reserved VM. The monitor is Autoscale, with cursors,
observations, history, leases, and live artifact bytes in a separate monitor-owned
PostgreSQL database. Autoscale may scale to zero, and nothing wakes it on a schedule:
`.github/workflows/autoscale-poll.yml` runs only by hand and then waits for one
authenticated, lease-protected `POST /api/live/poll` cycle. A process-local poller improves latency while an instance is
warm; neither browsers nor GET health checks advance monitoring state. A heartbeat
renews lease ownership while Evidently, SHAP, or Claude work is in flight.
Each observation and its signal history are committed before the source cursor advances.
Every window envelope must carry `contract_version` `1.0` or `1.1`; any other value, or
a missing field, is a telemetry error that holds the cursor until the producer is fixed.
Duplicate `window_id` values are idempotent; the same id with a different
`content_sha256` is an integrity error and holds the cursor. The monitor independently
recomputes that digest from the exact public primary-record JSON before grading. Failed
producer acknowledgements remain durable and are retried on later lease cycles.

Every outbound telemetry or webhook call — telemetry pulls, the model artifact,
acknowledgements, score write-back and the alert webhook — uses one retry policy (contract §12,
`backend/app/http_retry.py`): three attempts on 429/502/503/504 and connection errors,
exponential backoff 0.5 s → 4 s with ±25 % jitter, `Retry-After` honoured and capped at
4 s. A 404 or any other 4xx is never retried. When the retries are exhausted the last
response is handled as before (a window 404 is `WindowEvicted`; a webhook failure is
recorded on the alert and retried next cycle).

Each poll cycle logs one line per source with `cycle_id`, `source_id`, `tick`,
`duration_ms`, `outcome` (`ok`, `waiting`, `held`, `error`), `backlog` and `error`, and
one `cycle complete` line. `GET /api/readiness` returns the same for the most recent
cycle under `poller.last_cycle` (per-source `outcome`, `duration_ms` and the last
`error`), so an operator can see which source is held without reading logs.

Closed churn/NBA windows below 500 records and chatbot windows below 8 traces are
persisted as real observations, but statistical health stays `Unknown` with an explicit
insufficient-sample reason. A closed window with `count=0` is likewise a real observation
(every signal `Unknown`, reason "empty window") and advances the cursor; only a missing
window (HTTP 404) or an integrity error holds it. Public observations omit raw chat
input/output and per-instance LIME values. Live artifact bytes are served from PostgreSQL,
not an Autoscale filesystem; per-instance LIME HTML is not public.

## Label-lag backfill

Labels (churn) and rewards (NBA) arrive `label_lag_ticks` / `reward_lag_ticks` after a
window closes (contract §7; the monitor reads the lag from `/telemetry/meta`, default 3).
The observation for tick *t* therefore records realized metrics as `pending`. Inside the
same lease-held cycle, after observing *t* and while waiting at the tail, each runner
revisits the ticks in `[t - L - 1, t)`, re-pulls their inferences, verifies the digest
against the stored observation, joins the labels and writes one row per
`(source_id, tick, metric_key)` to `live_realized_metrics` with status `realized`,
`pending`, `insufficient_coverage` (below 50 %), `single_class`, `no_labels`, `evicted`
(the inference window answered 404; final) or `error` (digest changed; retried). A tick
is done (`final`) once it is `realized` or `evicted`, or once the labels window's
`available_at_tick` is at or before the producer's source tick — its latest closed tick,
`latest_tick - 1`, never the open window it is still writing — and still carries no
labels: then it is final `no_labels` and never pulled again, even if labels appear
later. While the monitor waits at the tail its own tick equals the open window, so
nothing due in that window is finalized until it closes. A 404 on the labels window,
or an empty one without `available_at_tick`, is `pending` until the tick's own due tick
(`t + L`) is at or before the source tick. A `count=0` or undersized inference window
is final `no_labels` at once (no label can realize it). `pending` rows that slipped
below the window during a producer outage are swept once more. Final rows are never overwritten, and the backfill never
rewrites an observation or touches the cursor. `GET /api/live/use-case/{uc}` and the
portfolio grade `realized_roc_auc` and `acceptance_rate` on the most recent `realized`
tick, reported as `as_of_tick`; with no realized row the lane stays reasoned-Unknown with
its pending reason.

## Baselines across restarts

The NBA `recommendation_drift` baseline (the offer mix of the first window served by
the current model version) is persisted in `live_baselines` per
`(source_id, kind, model_version)` (migration 7) and read on cold start and on
rebaseline, so an Autoscale restart does not return the signal to pending. The CBPE
baseline is not persisted: it is refit from the model artifact, which is acceptable to
recompute.

## Alerting

After each runner tick in the lease-held cycle, the poller grades the use case the way
the dashboard does (latest observation plus the newest realized metric) and diffs the
per-lane and overall health against the previous snapshot in `live_health_snapshots`.
`* → Red` and `Green → Amber` open a row in `live_alerts`; a lane that returns to Green
resolves every open alert on it; a current Unknown (stale source, pending labels,
uninstrumented lane) never opens or resolves anything, a previous Unknown followed by
Red opens (`* → Red`), and an open `(lane, health)` is never duplicated,
so Red → Unknown → Red is one alert. Both tables are migration 6 and hold derived
metadata only.

`GET /api/live/alerts?uc=&open=true&limit=` lists alerts newest first with their
delivery status; the use-case detail carries its open alerts as `alerts` and the
portfolio summary counts `open_alerts` by severity. The SPA shows an alerts strip on the
home page and a panel on each use-case page; both are read-only.

Set `LIVE_ALERT_WEBHOOK_URL` (a secret: it is the credential) to deliver each opened and
resolved alert as one POST with a Slack-incoming-webhook-compatible body
`{"text", "blocks", "alert"}` carrying use case id, lane, from/to health, tick and, when
`LIVE_DASHBOARD_URL` is set, a link to the use-case page. No features and no trace text
are sent. Delivery is at-least-once: a non-2xx or connection error is recorded on the
alert (`open_delivery_error` / `resolve_delivery_error`) and retried on the next cycle
(each delivery itself retries with backoff, see above); it never
blocks grading or holds a cursor. Logs name the webhook host only. Without a webhook the
phase is marked `skipped` and the alert remains visible in the API and UI. Triage
ownership is recorded in [adr/0001-alert-ownership.md](adr/0001-alert-ownership.md).

## Batch run receiver

`POST /api/batch/runs` receives one run summary from a GCP batch job (October batch MVP,
issue S1-02; spec in
[changes/2026-10-05-s1-02-batch-runs-api/spec.md](../changes/2026-10-05-s1-02-batch-runs-api/spec.md)).
It is available in demo and strict live mode. It stores the run in `batch_runs`
(migration 8) and never touches a telemetry cursor.

- Body: the S1-01 **draft** schema `batch-run/1`
  ([schema](../changes/2026-10-02-batch-monitoring-mvp/schema/README.md)). The backend
  enforces it in `backend/app/batch_schema.py`.
- Key: `Authorization: Bearer <key>`. Configure only the SHA-256 of each key in
  `BATCH_API_KEY_SHA256` as comma-separated `USE_CASE_ID:<64 hex>` entries. Two entries for
  one use case are allowed during a key rotation. If the setting is empty, every request
  is `401`. A malformed entry is listed by position in `GET /api/readiness`. The source
  registry (S2-01) replaces this setting.
- `BATCH_MAX_BODY_BYTES`: the body limit, default 10 MB (`413` above it).
- Responses: `201` stored, `200` the same body again (no change), `409` the same
  `(use_case_id, run_id)` with other content (the stored run does not change), `400` with
  `errors` (`loc`, `msg`, `type`; never the input value), `401` no or wrong key, `403` the
  key is for another use case. Nothing is stored unless the answer is `201`.
- Trace ID: the OTel FastAPI instrumentation reads the W3C `traceparent` header and the
  handler runs in the span `monitor.ingest`; the row stores that span's trace ID with
  `trace_id_source = traceparent`. Without a valid header, or with tracing off, a new ID
  is stored with `trace_id_source = generated`. Only `POST /api/batch/runs` makes spans.
- Tracing settings (all optional): `OTEL_EXPORTER_OTLP_ENDPOINT` sends the spans to the
  Collector over OTLP/HTTP (unset: no export); `OTEL_SERVICE_NAME` (default
  `model-monitor`); `OTEL_SDK_DISABLED=true` turns tracing off;
  `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS` replaces the exclude pattern. A failed export never
  stops a run.
- Logs carry the outcome, `use_case_id`, `run_id`, the record count and the trace ID.
  They never carry the key, the `Authorization` header or the body.

To make a key and its hash for one use case (the key goes to GCP Secret Manager, the hash
to `BATCH_API_KEY_SHA256`; never put either in git, chat or email):

```bash
python -c "import hashlib,secrets; k=secrets.token_urlsafe(32); print(k); print(hashlib.sha256(k.encode()).hexdigest())"
```

## Unsticking a source

A source whose cursor is held shows `state: "error"` in `GET /api/live/sync` and a
`held` outcome with its error in `GET /api/readiness` (`poller.last_cycle.sources`).
Transient producer errors clear themselves (the retry policy above, then the next
cycle). Two conditions do not: an integrity error (the producer rewrote a window it had
already served — the stored digest differs from the one on the wire) and a window the
monitor cannot grade at all. For those the operator skips the held tick. Both commands
need the worker token (`LIVE_WORKER_TOKEN`, the same secret the Autoscale wake uses);
nothing else can move a cursor, and a browser cannot reach these routes.

1. Confirm the hold and read the error:

   ```bash
   curl -s "$MONITOR_URL/api/live/sync/AICT-L01" | jq '{sync_state, last_error}'
   curl -s "$MONITOR_URL/api/readiness" | jq '.poller.last_cycle.sources["AICT-L01"]'
   ```

2. Skip the held tick with a reason (the reason is stored on the stub observation and
   is visible in the API and the dashboard; keep it factual):

   ```bash
   curl -s -X POST "$MONITOR_URL/api/live/sources/AICT-L01/skip" \
     -H "Authorization: Bearer $LIVE_WORKER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"reason": "producer rewrote window w5 after a redeploy; digest mismatch"}'
   ```

   The response carries `skipped_tick`, `next_tick`, `observation_id` and the previous
   error. In one transaction the monitor writes a stub observation for the tick
   (`record_count: 0`, `skipped: true`, every lane Unknown, the reason under
   `errors.skipped`), marks its realized rows final so the backfill never pulls the
   window again and advances the cursor; then it reloads the runner. The stub was never
   served by the producer, so it is stored with `ack_status: "skipped"` and is never
   acknowledged to the producer (the acknowledgement retry loop ignores it). `409`
   means the cursor is not held on an error
   (`state` is `at_tail`, `catching_up`, `idle`, `stale` or `connecting`): a healthy or
   merely waiting source is never skipped. `401` is a wrong or missing token; `404` an
   unknown use case id.

3. If the error was an acknowledgement that the producer keeps rejecting (visible as
   `ack_status: "error"` on the observation and a failing acknowledgement retry every
   cycle), abandon it; observations and cursors are untouched:

   ```bash
   curl -s -X POST "$MONITOR_URL/api/live/sources/AICT-L01/reset-ack" \
     -H "Authorization: Bearer $LIVE_WORKER_TOKEN"
   ```

   The response is `{"use_case_id": "AICT-L01", "abandoned": <n>}`.

4. Trigger a cycle (or wait for the next wake) and confirm the source is moving:

   ```bash
   curl -s -X POST "$MONITOR_URL/api/live/poll" \
     -H "Authorization: Bearer $LIVE_WORKER_TOKEN" | jq '.sync'
   ```

Use case ids are `AICT-L01` (churn), `AICT-L02` (chatbot) and `AICT-L03` (NBA). The
skipped window stays auditable: `GET /api/live/observations?uc=AICT-L01` lists the stub
with `skipped: true` and `skip_reason`, and the use-case detail shows the same fields
while it is the newest observation. Every other `POST` under `/api/live/` returns 404
in strict live mode; outside `/api/live/`, only `POST /api/batch/runs` is accepted.

Sync states are `connecting`, `catching_up`, `at_tail`, `idle`, `stale`, and `error`.
Inspect them through `GET /api/live/sync`, the live portfolio response, or a use-case
detail response. Live observation evidence is under `/api/live/observations` and live
artifacts are served only from `/api/live/artifacts/{artifact_id}`.

Run `python backend/scripts/migrate.py` (or start the service) to apply ordered schema
migrations. PostgreSQL runs them under an advisory transaction lock, so concurrent
Autoscale starts are safe. `GET /api/version` reports both the baked monitor Git SHA and
the producer gateway Git SHA for direct comparison with their respective GitHub repos.
