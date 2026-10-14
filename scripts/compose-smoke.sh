#!/usr/bin/env bash
# Smoke test of the local Compose stack (S1-06, S1-07). macOS and Linux.
# Starts the edge network, the monitor stack (backend + PostgreSQL + OTel Collector) and the
# nginx front door. Through nginx it checks the routes, the OTLP token, one batch run with a
# known traceparent, and fake GCP job spans; then the trace check tool finds all the items, and the worker grades the run (S2-05).
# KEEP=1 keeps the stacks running afterwards. Needs: docker (Compose v2), curl, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/deploy/compose"
COMPOSE=(docker compose -f compose.yaml -f compose.local.yaml)
NGINX=(docker compose -f "$ROOT/deploy/nginx/compose.yaml" -f "$ROOT/deploy/nginx/compose.local.yaml")
BASE_URL="http://127.0.0.1:8000"
FRONT="http://127.0.0.1:8080"
DASH="http://127.0.0.1:8082"   # front-door port of the dashboard (S2-07)
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
OTLP_TOKEN="local-dev-otlp-token-not-a-secret"    # local test value, not a secret
EXAMPLE="$ROOT/backend/schemas/batch-run/1/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"
MADE_EDGE=0

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "SMOKE FAIL: $STEP"
    "${COMPOSE[@]}" logs --no-color --tail 200 backend collector || true
    "${COMPOSE[@]}" logs --no-color --tail 50 dashboard || true
    "${NGINX[@]}" logs --no-color --tail 100 nginx || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${NGINX[@]}" down --remove-orphans >/dev/null 2>&1 || true
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    if [ "$MADE_EDGE" = "1" ]; then
      docker network rm edge >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

# code <expected> <curl arguments...>: fails the step when the HTTP status differs
code() {
  local expected="$1"
  shift
  local got
  got="$(curl -sS -o /dev/null -w '%{http_code}' "$@")"
  [ "$got" = "$expected" ] || { echo "expected $expected, got $got"; return 1; }
}

STEP="edge network"
if ! docker network inspect edge >/dev/null 2>&1; then
  docker network create edge >/dev/null
  MADE_EDGE=1
fi

STEP="compose up"
"${COMPOSE[@]}" up --build --wait --wait-timeout 300

STEP="nginx up"
"${NGINX[@]}" up -d --wait --wait-timeout 120

STEP="readiness"
curl -fsS "$BASE_URL/api/readiness" >/dev/null

STEP="nginx routes"
code "200" "$FRONT/api/health"
code "404" "$FRONT/api/live/portfolio"
code "404" "$FRONT/api/readiness"
code "404" "$FRONT/api/healthx"

STEP="OTLP token required"
code "401" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" --data '{}'
code "401" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" \
  -H "Authorization: Bearer wrong-token" --data '{}'

STEP="prepare request"
TRACE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PARENT_ID="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
RUN_ID="smoke-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
python3 - "$EXAMPLE" "$RUN_ID" > "$WORK/body.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1], encoding="utf-8"))
body["run_id"] = sys.argv[2]
body["use_case_id"] = "rtr-fraud-validation"   # a registered use case (S2-01)
print(json.dumps(body))
PY

STEP="POST /api/batch/runs through nginx"
STATUS="$(curl -sS -o "$WORK/response.json" -w '%{http_code}' -X POST "$FRONT/api/batch/runs" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-$TRACE_ID-$PARENT_ID-01" \
  --data-binary "@$WORK/body.json")"
[ "$STATUS" = "201" ]
python3 - "$WORK/response.json" "$TRACE_ID" <<'PY'
import json, sys
answer = json.load(open(sys.argv[1], encoding="utf-8"))
assert answer["trace_id"] == sys.argv[2], "trace_id in the answer is not the sent trace ID"
PY

STEP="batch_runs row"
ROW="$("${COMPOSE[@]}" exec -T postgres psql -U monitor -d monitor -tAc \
  "select trace_id, trace_id_source from batch_runs where run_id = '$RUN_ID'")"
[ "$ROW" = "$TRACE_ID|traceparent" ]

STEP="fake job spans through nginx"
# What a GCP job sends (S1-05 part A): batch.run -> batch.send -> HTTP client span. The client
# span ID is the parent ID of the traceparent above, so the chain reaches monitor.ingest.
python3 - "$TRACE_ID" "$PARENT_ID" > "$WORK/spans.json" <<'PY'
import json, secrets, sys, time
trace_id, client_id = sys.argv[1], sys.argv[2]
run_id, send_id = secrets.token_hex(8), secrets.token_hex(8)
now = time.time_ns()

def span(name, span_id, parent, kind):
    return {"traceId": trace_id, "spanId": span_id, "parentSpanId": parent, "name": name,
            "kind": kind, "startTimeUnixNano": str(now), "endTimeUnixNano": str(now + 1000000)}

print(json.dumps({"resourceSpans": [{
    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "smoke-fake-job"}}]},
    "scopeSpans": [{"scope": {"name": "compose-smoke"}, "spans": [
        span("batch.run", run_id, "", 1),
        span("batch.send", send_id, run_id, 1),
        span("POST", client_id, send_id, 3),
    ]}]}]}))
PY
code "200" -X POST "$FRONT/otlp/v1/traces" -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OTLP_TOKEN" --data-binary "@$WORK/spans.json"

STEP="check-trace"
bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 30
STEP="batch evaluation"
# S2-05: the worker grades the run within a few cycles (interval 5 s locally). No Langfuse
# here, so the score status is "skipped". The example body has no baseline and no
# submitted_at, so both grades are Unknown.
for i in $(seq 1 30); do
  if curl -fsS "$BASE_URL/api/readiness" | python3 -c '
import json, sys
e = json.load(sys.stdin)["batch_evaluator"]
sys.exit(0 if e["unevaluated"] == 0 and e["last_cycle_at"] else 1)'; then
    break
  fi
  [ "$i" = "30" ] && { echo "the run was not graded in 60 s"; exit 1; }
  sleep 2
done
GRADE="$("${COMPOSE[@]}" exec -T postgres psql -U monitor -d monitor -tAc \
  "select grade, delivery_grade, langfuse_status from batch_evaluations where run_id = '$RUN_ID'")"
[ "$GRADE" = "Unknown|Unknown|skipped" ] || { echo "unexpected evaluation: $GRADE"; exit 1; }

STEP="dashboard through the front door (S2-07)"
code "200" "$DASH/"
curl -fsS "$DASH/" | grep -q '<div id="root">'
code "200" "$DASH/heatmap"
curl -fsS "$DASH/api/live/portfolio" | python3 -c '
import json, sys
rows = {r["registry_id"]: r for r in json.load(sys.stdin)["rows"]}
row = rows["rtr-fraud-validation"]
assert row["grade"] is not None, "the run is not graded on the dashboard"'
curl -fsS "$DASH/api/live/use-case/rtr-fraud-validation" | python3 -c '
import json, sys
body = json.load(sys.stdin)
assert body["trace_id"] == sys.argv[1], "trace_id differs"
assert "payload" not in body' "$TRACE_ID"
# The job API is not on 8082: every unlisted /api/ path is 404 (Task 4), any method.
code "404" -X POST "$DASH/api/batch/runs" -H "Content-Type: application/json" --data '{}'
code "404" "$DASH/api/readiness"
code "403" -X POST "$DASH/api/live/portfolio"
# The dashboard API is not on the job port.
code "404" "$FRONT/api/live/portfolio"

echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
