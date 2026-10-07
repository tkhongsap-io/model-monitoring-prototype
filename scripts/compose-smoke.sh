#!/usr/bin/env bash
# Smoke test of the local Compose stack (S1-06). macOS and Linux.
# Starts backend + PostgreSQL + OTel Collector, stores one batch run with a known
# traceparent, and checks the row and the monitor.ingest span in the Collector file.
# KEEP=1 keeps the stack running afterwards. Needs: docker (Compose v2), curl, python3.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/deploy/compose"
COMPOSE=(docker compose -f compose.yaml -f compose.local.yaml)
BASE_URL="http://127.0.0.1:8000"
KEY="local-dev-batch-key-not-a-secret"            # local test value, not a secret
EXAMPLE="$ROOT/changes/2026-10-02-batch-monitoring-mvp/schema/examples/valid/04-identity-only.json"
WORK="$(mktemp -d)"
STEP="start"

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "SMOKE FAIL: $STEP"
    "${COMPOSE[@]}" logs --no-color --tail 200 backend collector || true
  fi
  if [ "${KEEP:-0}" != "1" ]; then
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

STEP="compose up"
"${COMPOSE[@]}" up --build --wait --wait-timeout 300

STEP="readiness"
curl -fsS "$BASE_URL/api/readiness" >/dev/null

STEP="prepare request"
TRACE_ID="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
PARENT_ID="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"
RUN_ID="smoke-$(date -u +%Y%m%dT%H%M%SZ)-$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
python3 - "$EXAMPLE" "$RUN_ID" > "$WORK/body.json" <<'PY'
import json, sys
body = json.load(open(sys.argv[1], encoding="utf-8"))
body["run_id"] = sys.argv[2]
print(json.dumps(body))
PY

STEP="POST /api/batch/runs"
STATUS="$(curl -sS -o "$WORK/response.json" -w '%{http_code}' -X POST "$BASE_URL/api/batch/runs" \
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

STEP="monitor.ingest span in the Collector file"
for _ in $(seq 1 15); do
  if "${COMPOSE[@]}" cp collector:/data/spans.jsonl "$WORK/spans.jsonl" >/dev/null 2>&1 &&
     python3 - "$WORK/spans.jsonl" "$TRACE_ID" <<'PY'
import json, sys
found = False
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    for resource in json.loads(line).get("resourceSpans", []):
        for scope in resource.get("scopeSpans", []):
            for span in scope.get("spans", []):
                if span.get("name") == "monitor.ingest" and \
                        span.get("traceId", "").lower() == sys.argv[2]:
                    found = True
sys.exit(0 if found else 1)
PY
  then
    echo "SMOKE PASS: run $RUN_ID, trace $TRACE_ID"
    exit 0
  fi
  sleep 2
done
exit 1
