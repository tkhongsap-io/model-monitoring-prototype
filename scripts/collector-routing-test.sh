#!/usr/bin/env bash
# S2-03b: proves the Collector routing with the real Collector image, without Langfuse.
# The project tool renders the routes file with file exporters; spans with each label case
# are sent; each must land in the file of the right project. Linux CI; needs docker, python3.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="otel/opentelemetry-collector-contrib:0.161.0"
WORK="$(mktemp -d)"
NAME="routing-test-$$"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$WORK"; }
trap cleanup EXIT
# The Collector runs as uid 10001 and must be able to read the config files.
chmod 755 "$WORK"
mkdir -p "$WORK/out"; chmod 777 "$WORK/out"

python3 "$ROOT/backend/scripts/langfuse_projects.py" routes --use-cases unrouted,rtr-fraud-validation --exporter file --file-dir /out --output "$WORK/routes.yaml"
cat > "$WORK/base.yaml" <<'YAML'
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [routing/langfuse]
YAML
docker run -d --name "$NAME" -p 127.0.0.1:14318:4318 -v "$WORK:/cfg:ro" -v "$WORK/out:/out" \
  "$IMAGE" --config=/cfg/base.yaml --config=/cfg/routes.yaml >/dev/null
for i in $(seq 1 30); do
  curl -s -o /dev/null -X POST http://127.0.0.1:14318/v1/traces -H 'Content-Type: application/json' --data '{"resourceSpans":[]}' && break
  [ "$i" = "30" ] && { docker logs "$NAME"; echo "Collector did not start"; exit 1; }
  sleep 1
done

send() {  # send <span name> <resource attrs json> <span attrs json>
  python3 - "$1" "$2" "$3" > "$WORK/body.json" <<'PY'
import json, secrets, sys, time
name, res, attrs = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
kv = lambda d: [{"key": k, "value": {"stringValue": v}} for k, v in d.items()]
now = time.time_ns()
print(json.dumps({"resourceSpans": [{"resource": {"attributes": kv(res)}, "scopeSpans": [{
    "scope": {"name": "routing-test"}, "spans": [{"traceId": secrets.token_hex(16),
    "spanId": secrets.token_hex(8), "name": name, "kind": 1,
    "startTimeUnixNano": str(now), "endTimeUnixNano": str(now + 1000),
    "attributes": kv(attrs)}]}]}]}))
PY
  curl -fsS -o /dev/null -X POST http://127.0.0.1:14318/v1/traces -H 'Content-Type: application/json' --data-binary "@$WORK/body.json"
}
send resource-label '{"service.name":"x","use.case.id":"rtr-fraud-validation"}' '{}'
send span-label '{"service.name":"model-monitor"}' '{"use_case_id":"rtr-fraud-validation"}'
send service-name '{"service.name":"rtr-fraud-validation"}' '{}'
send no-label '{"service.name":"model-monitor"}' '{}'
send resource-wins '{"service.name":"x","use.case.id":"other-use-case"}' '{"use_case_id":"rtr-fraud-validation"}'
sleep 3
docker stop "$NAME" >/dev/null   # flush the file exporters
expect() {  # expect <span name> <project>
  grep -q "\"$1\"" "$WORK/out/$2.jsonl" || { echo "FAIL: $1 is not in $2"; cat "$WORK/out/"*.jsonl || true; exit 1; }
}
expect resource-label rtr-fraud-validation
expect span-label rtr-fraud-validation
expect service-name rtr-fraud-validation
expect no-label unrouted
expect resource-wins unrouted
if grep -q '"no-label"\|"resource-wins"' "$WORK/out/rtr-fraud-validation.jsonl"; then echo "FAIL: unrouted spans in rtr-fraud-validation"; exit 1; fi
echo "ROUTING PASS"
