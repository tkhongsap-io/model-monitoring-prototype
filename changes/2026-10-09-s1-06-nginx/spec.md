# Spec: nginx front door and the OTLP token (S1-06, test-host part)

Intent and decisions: `intent.md` in this folder.

## Files

| File | Change |
|---|---|
| `deploy/nginx/compose.yaml` | New. Compose project `nginx`: one service `nginx` |
| `deploy/nginx/compose.local.yaml` | New. Local and CI port |
| `deploy/nginx/compose.testhost.yaml` | New. Test-host port |
| `deploy/nginx/conf.d/00-common.conf` | New. http-level settings and the nginx health server |
| `deploy/nginx/conf.d/model-monitor.conf` | New. The model-monitor job paths |
| `deploy/nginx/README.md` | New. How to add an app; how to reload |
| `deploy/compose/compose.yaml` | The backend and the Collector join the external network `edge` with aliases |
| `deploy/compose/compose.local.yaml` | The Collector gets the local test token |
| `deploy/compose/compose.testhost.yaml` | The Collector reads `/opt/model-monitor/collector.env` |
| `deploy/compose/otel-collector.yaml` | The second receiver `otlp/external` with `bearertokenauth` |
| `deploy/compose/collector.env.example` | New. Names only |
| `deploy/compose/make-collector-env.sh` | New. Test host only: writes `collector.env` from a copied token file |
| `scripts/compose-smoke.sh` | Starts `edge` and nginx; tests routes, token and a full fake-job trace |
| `backend/tests/test_compose_files.py`, new `backend/tests/test_nginx_files.py` | Static tests |
| `deploy/compose/TESTHOST.md`, `deploy/compose/README.md`, `issues.md` (S1-06), `CHANGELOG.md`, `DEVLOG.md` | Docs |

No backend code change. No new package.

## Fixed values

| Item | Value |
|---|---|
| nginx image | `nginxinc/nginx-unprivileged:1.28.0-alpine` (non-root, uid 101) |
| Docker network | `edge`, external, made once with `docker network create edge` |
| Aliases on `edge` | `model-monitor-backend` (backend), `model-monitor-collector` (Collector) |
| model-monitor server port in the nginx container | `8080` |
| Published port | Local and CI: `127.0.0.1:8080:8080`. Test host: `80:8080` (all interfaces; the VPC rule `monitor-testhost-allow-http-jobs` allows only `10.10.0.0/24`) |
| nginx health server | `127.0.0.1:8081`, path `/healthz`, inside the container only |
| Collector receivers | `otlp` on `0.0.0.0:4318` (internal, no token, unchanged); `otlp/external` on `0.0.0.0:4319` (token). Port 4319 is never published. |
| Body limit | `client_max_body_size 10m` = backend `BATCH_MAX_BODY_BYTES` default (10 MiB) |
| Local test token | `local-dev-otlp-token-not-a-secret` (not a secret, like the local API key) |
| Test-host token | Secret Manager secret `otlp-token`; on the VM `/opt/model-monitor/collector.env` (mode 600, root): `OTLP_TOKEN=<token>` |

## nginx project

`deploy/nginx/compose.yaml`:

```yaml
# Standalone front door (S1-06). One nginx for all apps on this host. Each app has its own
# file in conf.d/. The apps join the external network `edge` with their own aliases.
# Make the network once: docker network create edge
name: nginx

services:
  nginx:
    image: nginxinc/nginx-unprivileged:1.28.0-alpine
    volumes:
      - ./conf.d:/etc/nginx/conf.d:ro
    networks:
      - edge
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8081/healthz"]
      interval: 5s
      timeout: 3s
      retries: 12
    restart: unless-stopped

networks:
  edge:
    external: true
```

Mounting `conf.d` hides the image's `default.conf`, so only our server blocks exist.

`compose.local.yaml`: `services.nginx.ports: ["127.0.0.1:8080:8080"]`.
`compose.testhost.yaml`: `services.nginx.ports: ["80:8080"]`.

`conf.d/00-common.conf` (included in the `http` block of the image's `nginx.conf`):

```nginx
# Shared settings for all apps (S1-06).
server_tokens off;
# Docker DNS at request time: nginx starts even when an app is down; that app gives 502.
resolver 127.0.0.11 valid=10s ipv6=off;

# Health of nginx itself, for the Compose health check. Inside the container only.
server {
    listen 127.0.0.1:8081;
    location = /healthz {
        access_log off;
        return 200 "ok\n";
    }
}
```

`conf.d/model-monitor.conf`:

```nginx
# model-monitor (S1-06): the GCP job paths only. Host port 80 on the test host.
# Every other path gives 404, so nobody reaches the dashboard API here (S3-07).
server {
    listen 8080;
    client_max_body_size 10m;          # = BATCH_MAX_BODY_BYTES of the backend
    proxy_http_version 1.1;
    proxy_set_header Host $host;

    set $mm_backend http://model-monitor-backend:8000;
    set $mm_collector http://model-monitor-collector:4319;

    location = /api/batch/runs {
        proxy_pass $mm_backend;
    }
    location = /api/health {
        proxy_pass $mm_backend;
    }
    # OTLP/HTTP: /otlp/v1/traces -> Collector /v1/traces. The Collector checks the token.
    location /otlp/ {
        rewrite ^/otlp/(.*)$ /$1 break;
        proxy_pass $mm_collector;
    }
    location / {
        return 404;
    }
}
```

With a variable in `proxy_pass` and no URI part, nginx sends the original request URI
(after the `rewrite`). All request headers, also `Authorization` and `traceparent`, pass
through. The default access log format has no request headers, so the token and the key
are never logged.

`deploy/nginx/README.md`: what the project is; make the network; start it
(`docker compose -f compose.yaml -f compose.<host>.yaml up -d --wait`); add an app (new file
in `conf.d/`, `docker compose exec nginx nginx -t`, then `docker compose exec nginx nginx -s reload`);
the port rule (one server block for each app port, because there is no DNS name).

## model-monitor project

`deploy/compose/compose.yaml`: add to `backend` and to `collector`:

```yaml
    networks:
      default: {}
      edge:
        aliases: [model-monitor-backend]      # collector: [model-monitor-collector]
```

and at the end:

```yaml
networks:
  edge:
    external: true          # made once: docker network create edge (see deploy/nginx)
```

`collector-init` and `trace-check` stay on the default network only. The backend export
stays `http://collector:4318` (the internal receiver).

`compose.local.yaml`: `services.collector.environment.OTLP_TOKEN: local-dev-otlp-token-not-a-secret`.

`compose.testhost.yaml`:

```yaml
  collector:
    env_file:
      - path: /opt/model-monitor/collector.env      # OTLP_TOKEN, mode 600 (make-collector-env.sh)
        required: true
```

`otel-collector.yaml`:

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  # The OTLP token of the GCP jobs (S1-06). Only the external receiver uses it.
  bearertokenauth:
    scheme: Bearer
    token: ${env:OTLP_TOKEN}

receivers:
  otlp:                        # internal: the backend, inside the Docker network
    protocols:
      http:
        endpoint: 0.0.0.0:4318
  otlp/external:               # GCP jobs, only through nginx (/otlp/*)
    protocols:
      http:
        endpoint: 0.0.0.0:4319
        auth:
          authenticator: bearertokenauth
```

`service.extensions: [health_check, bearertokenauth]`;
`service.pipelines.traces.receivers: [otlp, otlp/external]`. The rest does not change.

`collector.env.example`: a comment and `OTLP_TOKEN=` with no value.

## Test-host token steps

The project owner runs these (the safety check blocks Claude from handling the value).
`TESTHOST.md` lists them as commands:

1. Laptop, repository root (PowerShell): make the token in a file, never on the screen:
   `backend\.venv\Scripts\python.exe -c "import secrets,pathlib; pathlib.Path('otlp-token.tmp').write_text(secrets.token_urlsafe(32), encoding='ascii')"`
2. `gcloud secrets create otlp-token --data-file otlp-token.tmp` with the same replication
   as `batch-api-key-rtr-fraud-validation` (`gcloud secrets describe` shows it).
3. `gcloud compute ssh <vm> --command "mkdir -m 700 /tmp/s1-06"`, then
   `gcloud compute scp otlp-token.tmp <vm>:/tmp/s1-06/ ...`, then `Remove-Item otlp-token.tmp`.
4. VM: `sudo bash /opt/model-monitor/compose/make-collector-env.sh /tmp/s1-06/otlp-token.tmp`.

`deploy/compose/make-collector-env.sh <token-file>`:
- `#!/usr/bin/env bash`, `set -euo pipefail`; must run as root.
- The argument file must exist and not be empty, else exit `1`.
- `umask 077`; reads the token without `\r` and `\n`; refuses a token shorter than 32
  characters (exit `1`, the message has no value).
- Writes `/opt/model-monitor/collector.env.tmp` with `printf 'OTLP_TOKEN=%s\n'`, `chown root:root`,
  `chmod 600`, `mv` to `/opt/model-monitor/collector.env`.
- Deletes the argument file and, if empty, its folder.
- Prints only `stat -c '%a %U %n'` of the file and `COLLECTOR ENV DONE`. Never echoes the token.

## Test-host deploy order (TESTHOST.md)

1. Once: `sudo docker network create edge`.
2. Copy `deploy/nginx/` to `/opt/nginx/` and the changed `deploy/compose/` files to
   `/opt/model-monitor/compose/`.
3. Token steps above.
4. Model-monitor: `up -d --wait` (the Collector restarts with the token and both receivers;
   the backend joins `edge`).
5. nginx: in `/opt/nginx`, `sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait`.
6. Checks (next section).

Rollback: `docker compose down` in `/opt/nginx` closes port 80 again; the monitor keeps
working inside the VM.

## CI smoke test (`scripts/compose-smoke.sh`)

Additions (the existing steps stay unless named):

- Variables: `FRONT="http://127.0.0.1:8080"`, `OTLP_TOKEN="local-dev-otlp-token-not-a-secret"`
  (local test value), `NGINX=(docker compose -f "$ROOT/deploy/nginx/compose.yaml" -f "$ROOT/deploy/nginx/compose.local.yaml")`.
- Before `compose up`: `docker network create edge >/dev/null 2>&1 || true`. Remember if this
  run made it (`MADE_EDGE=1`).
- After the monitor stack is up: `STEP="nginx up"`, `"${NGINX[@]}" up -d --wait --wait-timeout 120`.
- Cleanup (when `KEEP` is not `1`): `"${NGINX[@]}" down` before the monitor `down -v`; then
  `docker network rm edge` if `MADE_EDGE=1`. On failure, also print `"${NGINX[@]}" logs --tail 100`.
- Route checks through `$FRONT` (each a separate `STEP`):
  - `GET /api/health` → `200`
  - `GET /api/live/portfolio` → `404`; `GET /api/readiness` → `404`
  - `POST /otlp/v1/traces` with no `Authorization` → `401`; with `Bearer wrong-token` → `401`
- The batch POST goes through `$FRONT/api/batch/runs` (not port 8000). The rest of that step
  does not change.
- `STEP="fake job spans"`: a Python block writes an OTLP JSON body with `TRACE_ID` and three
  spans: `batch.run` (new span ID, no parent), `batch.send` (new span ID, parent `batch.run`),
  `POST` (span ID = `PARENT_ID` of the `traceparent`, parent `batch.send`, `kind` 3), times
  = now in nanoseconds as strings. `POST $FRONT/otlp/v1/traces` with
  `Authorization: Bearer $OTLP_TOKEN` and `Content-Type: application/json` → `200`.
- `STEP="check-trace"`: `bash "$ROOT/deploy/compose/check-trace.sh" "$TRACE_ID" --wait 30`
  (**without** `--backend-only`): all four items found.
- No line echoes the API key or the OTLP token.

## Static tests

`backend/tests/test_nginx_files.py` (new):
- The image is `nginxinc/nginx-unprivileged:1.28.0-alpine`; `conf.d` is mounted read-only at
  `/etc/nginx/conf.d`; the network `edge` is external; the health check uses `/healthz`.
- Ports: local exactly `["127.0.0.1:8080:8080"]`; test host exactly `["80:8080"]`; the base file has no `ports`.
- `model-monitor.conf`: exactly the locations `= /api/batch/runs`, `= /api/health`,
  `/otlp/`, `/`; the `/` location returns `404`; the upstreams use the aliases and ports
  8000 and 4319; `client_max_body_size 10m`.
- `00-common.conf`: `server_tokens off`, `resolver 127.0.0.11`, the health server listens on `127.0.0.1:8081`.
- No file under `deploy/nginx/` contains `Authorization`, `log_format` or a token value.

`backend/tests/test_compose_files.py` (changes):
- `backend` and `collector` join `default` and `edge` with the aliases; `edge` is external;
  `collector-init` and `trace-check` are not on `edge`.
- No published port is `4319` in any file.
- The Collector config: both receivers, `auth.authenticator: bearertokenauth` only on
  `otlp/external`, `token` is exactly `${env:OTLP_TOKEN}`, pipeline receivers `[otlp, otlp/external]`.
  (The old check "the word `token` is not in the file" changes to this exact check.)
- Local Collector `OTLP_TOKEN` is the local test value; the test-host Collector uses the
  required `env_file` `/opt/model-monitor/collector.env`; `collector.env.example` has no value.
- `make-collector-env.sh`: bash header, `set -euo pipefail`, `umask 077`, `chmod 600`,
  the length check, LF endings, and no `echo` line with the token variable.
- The smoke script: the route checks, the `401` checks, the fake spans, `check-trace.sh`
  without `--backend-only`, the nginx cleanup, no echo of the key or the token.
- `test_published_ports_are_loopback_only` does not change (the nginx port is in
  `deploy/nginx/compose.local.yaml`, checked by `test_nginx_files.py`).

## Not in scope

The Sprint 2 server blocks (dashboard 8080, Langfuse 3000), TLS (production, S4-01), the
job-side code and its Secret Manager access (Prakasit, S1-05 part A and S1-03), and
rate limits (S3-03).
