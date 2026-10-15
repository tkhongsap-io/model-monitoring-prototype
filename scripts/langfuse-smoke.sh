#!/usr/bin/env bash
# Langfuse smoke test (S2-03). Linux CI and macOS.
# Starts edge, Langfuse, the monitor stack and nginx with local test values; sends one batch
# run and fake GCP job spans through nginx; the trace check must find 5 of 5 (also the
# Langfuse trace), also after a Langfuse restart. KEEP=1 keeps the stacks running.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/deploy/compose/compose.yaml" -f "$ROOT/deploy/compose/compose.local.yaml")
NGINX=(docker compose -f "$ROOT/deploy/nginx/compose.yaml" -f "$ROOT/deploy/nginx/compose.local.yaml")
LANGFUSE=(docker compose -f "$ROOT/deploy/langfuse/compose.yaml" -f "$ROOT/deploy/langfuse/compose.local.yaml")
FRONT="http://127.0.0.1:8080"
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
OTLP_TOKEN="local-dev-otlp-token-not-a-secret"    # local test value, not a secret
EXAMPLE="$ROOT/backend/schemas/batch-run/1/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"
MADE_EDGE=0

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "LANGFUSE SMOKE FAIL: $STEP"
    for c in $("${LANGFUSE[@]}" ps -aq); do
      docker inspect --format '{{.Name}} {{if .State.Health}}{{.State.Health.Status}} {{range .State.Health.Log}}{{.Output}}{{end}}{{end}}' "$c" || true
    done
    "${LANGFUSE[@]}" logs --no-color --tail 100 langfuse-web langfuse-worker || true
    "${COMPOSE[@]}" logs --no-color --tail 100 collector || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${NGINX[@]}" down --remove-orphans >/dev/null 2>&1 || true
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    "${LANGFUSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    if [ "$MADE_EDGE" = "1" ]; then
      docker network rm edge >/dev/null 2>&1 || true
    fi
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

# The trace check reads Langfuse only when this is set (compose.local.yaml).
export CHECK_LANGFUSE_URL="http://langfuse-web:3000"
# The backend sends its scores to Langfuse only when this is set (compose.local.yaml, S2-05).
export BACKEND_LANGFUSE_HOST="http://langfuse-web:3000"

STEP="edge network"
if ! docker network inspect edge >/dev/null 2>&1; then
  docker network create edge >/dev/null
  MADE_EDGE=1
fi

STEP="langfuse up"
"${LANGFUSE[@]}" up -d --wait --wait-timeout 600
STEP="monitor up"
"${COMPOSE[@]}" up --build -d --wait --wait-timeout 300
STEP="nginx up"
"${NGINX[@]}" up -d --wait --wait-timeout 120

STEP="langfuse health through nginx"
[ "$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/public/health)" = "200" ]

STEP="batch run and fake job spans"
TRACE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PARENT_ID="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
RUN_ID="lf-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
python3 - "$EXAMPLE" "$RUN_ID" > "$WORK/body.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1], encoding="utf-8"))
body["run_id"] = sys.argv[2]
body["use_case_id"] = "rtr-fraud-validation"
print(json.dumps(body))
PY
[ "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$FRONT/api/batch/runs" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -H "traceparent: 00-$TRACE_ID-$PARENT_ID-01" --data-binary "@$WORK/body.json")" = "201" ]
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
    "scopeSpans": [{"scope": {"name": "langfuse-smoke"}, "spans": [
        span("batch.run", run_id, "", 1),
        span("batch.send", send_id, run_id, 1),
        span("POST", client_id, send_id, 3),
    ]}]}]}))
PY
[ "$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$FRONT/otlp/v1/traces" \
  -H "Content-Type: application/json" -H "Authorization: Bearer $OTLP_TOKEN" \
  --data-binary "@$WORK/spans.json")" = "200" ]

STEP="trace check with Langfuse"
OUT="$(bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 90 || true)"
echo "$OUT"
grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"
grep -q "observations in Langfuse project rtr-fraud-validation" <<<"$OUT"

STEP="grade score in Langfuse"
AUTH="$(python3 -c 'import base64; print(base64.b64encode(b"pk-lf-local-00000000-0000-0000-0000-000000000000:sk-lf-local-00000000-0000-0000-0000-000000000000").decode())')"
for i in $(seq 1 45); do
  FOUND="$(curl -sS -H "Authorization: Basic $AUTH" \
    "http://127.0.0.1:3000/api/public/v3/scores?traceId=$TRACE_ID&name=grade" \
    | python3 -c 'import json, sys
try:
    print(len(json.load(sys.stdin).get("data", [])))
except Exception:
    print(0)')"
  [ "$FOUND" = "1" ] && break
  [ "$i" = "45" ] && { echo "no grade score on the trace after 90 s"; exit 1; }
  sleep 2
done
PENDING="$(curl -fsS http://127.0.0.1:8000/api/readiness | python3 -c 'import json, sys; print(json.load(sys.stdin)["batch_evaluator"]["langfuse_pending"])')"
[ "$PENDING" = "0" ] || { echo "langfuse_pending is $PENDING"; exit 1; }

STEP="langfuse restart"
"${LANGFUSE[@]}" restart
"${LANGFUSE[@]}" up -d --wait --wait-timeout 300
OUT="$(bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 60 || true)"
echo "$OUT"
grep -q "RESULT: OK (5 of 5 found)" <<<"$OUT"
echo "LANGFUSE SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
