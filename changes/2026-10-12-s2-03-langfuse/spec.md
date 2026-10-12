# Spec: self-hosted Langfuse and the Collector export (S2-03)

Intent and decisions: `intent.md` in this folder.

## Files

| File | Change |
|---|---|
| `deploy/langfuse/compose.yaml` | New. Compose project `langfuse`: six services |
| `deploy/langfuse/compose.local.yaml`, `deploy/langfuse/local.env` | New. Local and CI: env file with test values |
| `deploy/langfuse/compose.testhost.yaml` | New. Test host: env file `/opt/langfuse/langfuse.env` |
| `deploy/langfuse/langfuse.env.example`, `deploy/langfuse/google-oauth.env.example` | New. Names only |
| `deploy/langfuse/make-langfuse-env.sh` | New. Test host only: makes the secrets |
| `deploy/langfuse/README.md` | New |
| `deploy/nginx/conf.d/langfuse.conf`, `deploy/nginx/compose.local.yaml`, `deploy/nginx/compose.testhost.yaml` | Port 3000 to `langfuse-web` |
| `deploy/compose/otel-collector.yaml` | Exporter `otlphttp/langfuse`; file rotation |
| `deploy/compose/compose.yaml`, `compose.local.yaml`, `compose.testhost.yaml` | Collector env; `trace-check` joins `edge` and gets the Langfuse check settings |
| `backend/app/trace_check.py`, `backend/scripts/check_trace.py` | 5th item "langfuse trace"; rotated span files |
| `scripts/langfuse-smoke.sh`, `.github/workflows/langfuse-smoke.yml` | New CI test |
| `backend/tests/test_langfuse_files.py` (new), `test_compose_files.py`, `test_nginx_files.py`, `test_trace_check.py`, `test_check_trace_script.py` | Tests |
| `deploy/compose/TESTHOST.md`, `issues.md` (S2-02, S2-03, S3-07), `CHANGELOG.md`, `DEVLOG.md` | Docs |

No new pip or npm package (the trace check reads Langfuse with `urllib` from the standard
library).

## Fixed versions (from the plan's fixed-versions table)

| Service | Image |
|---|---|
| `langfuse-web` | `langfuse/langfuse:4.50.0` |
| `langfuse-worker` | `langfuse/langfuse-worker:4.50.0` |
| `postgres` | `postgres:17.11-bookworm` |
| `clickhouse` | `clickhouse/clickhouse-server:25.12.11.4` |
| `redis` | `redis:7.4.11` |
| `minio` | `cgr.dev/chainguard/minio@sha256:dc455cdd4db6e390b1b26514f15ff37681a777bf8dab41aac445a0259f751e56` (the multi-arch index of `latest`, read from the registry on 2026-10-12; the free image has only the `latest` tag) |

## Compose project `langfuse`

`deploy/langfuse/compose.yaml` (`name: langfuse`). Every service: `restart: unless-stopped`,
no `ports`. Networks: `default` (the project's private network) for all; `langfuse-web`
also `edge` with `aliases: [langfuse-web]`. `networks.edge.external: true`.

Settings that are the same on every host go in `environment` of the base file:

| Service | `environment` (base) |
|---|---|
| `langfuse-web`, `langfuse-worker` | `TELEMETRY_ENABLED: "false"`, `LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES: "false"`, `AUTH_DISABLE_SIGNUP: "true"`, `CLICKHOUSE_MIGRATION_URL: clickhouse://clickhouse:9000`, `CLICKHOUSE_URL: http://clickhouse:8123`, `CLICKHOUSE_CLUSTER_ENABLED: "false"`, `REDIS_HOST: redis`, `REDIS_PORT: "6379"`, `LANGFUSE_S3_EVENT_UPLOAD_BUCKET: langfuse`, `LANGFUSE_S3_EVENT_UPLOAD_REGION: auto`, `LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: http://minio:9000`, `LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE: "true"`, `LANGFUSE_S3_EVENT_UPLOAD_PREFIX: events/` |
| `langfuse-web` only | `LANGFUSE_INIT_ORG_ID: model-monitor`, `LANGFUSE_INIT_ORG_NAME: Model monitor`, `LANGFUSE_INIT_PROJECT_ID: model-monitor`, `LANGFUSE_INIT_PROJECT_NAME: model-monitor` |
| `postgres` | `POSTGRES_USER: langfuse`, `POSTGRES_DB: langfuse` |
| `clickhouse` | `CLICKHOUSE_DB: default`, `CLICKHOUSE_USER: clickhouse` |
| `minio` | `MINIO_ROOT_USER: langfuse` |

Secret and host-specific settings come from the host env file (same names on every host),
given to **every** service with `env_file`. (One file for the six containers of one app on
one host; each container sees the passwords of its neighbours. Accepted for the test host.)

| Name | Used by |
|---|---|
| `DATABASE_URL` (`postgresql://langfuse:<pw>@postgres:5432/langfuse`), `POSTGRES_PASSWORD` | web, worker; postgres |
| `CLICKHOUSE_PASSWORD` | web, worker, clickhouse (and `CLICKHOUSE_USER` from the base) |
| `REDIS_AUTH` | web, worker, redis |
| `MINIO_ROOT_PASSWORD`, `LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID` (= `langfuse`), `LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY` (= the MinIO password) | minio; web, worker |
| `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` (64 hex) | web, worker |
| `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` (`pk-lf-<uuid4>`), `LANGFUSE_INIT_PROJECT_SECRET_KEY` (`sk-lf-<uuid4>`), `LANGFUSE_INIT_USER_EMAIL`, `LANGFUSE_INIT_USER_NAME`, `LANGFUSE_INIT_USER_PASSWORD` | web |
| `AUTH_DISABLE_USERNAME_PASSWORD`, `AUTH_GOOGLE_CLIENT_ID`, `AUTH_GOOGLE_CLIENT_SECRET`, `AUTH_GOOGLE_ALLOWED_DOMAINS`, `AUTH_GOOGLE_ALLOW_ACCOUNT_LINKING` | web (test host only) |

Commands and checks:
- `redis`: `command: ["sh", "-c", "exec redis-server --requirepass \"$$REDIS_AUTH\" --maxmemory-policy noeviction --save \"\" --appendonly no"]`; health `redis-cli -a "$$REDIS_AUTH" ping` (via `sh -c`).
- `minio`: `entrypoint: ["sh", "-c"]`, `command: ["mkdir -p /data/langfuse && minio server --address :9000 --console-address :9001 /data"]`; volume `minio-data:/data`; health `curl -f http://localhost:9000/minio/health/live` if the image has `curl`, else `mc ready local` (the implementer uses what the Langfuse Compose file of 4.50 uses).
- `postgres`: volume `postgres-data:/var/lib/postgresql/data`; health `pg_isready -U langfuse -d langfuse`.
- `clickhouse`: `user: "101:101"`; volumes `clickhouse-data:/var/lib/clickhouse`, `clickhouse-logs:/var/log/clickhouse-server`; health `wget --no-verbose --tries=1 --spider http://localhost:8123/ping`.
- `langfuse-worker`: `depends_on` postgres, clickhouse, redis, minio `condition: service_healthy`.
- `langfuse-web`: same `depends_on`; health `wget -q -O /dev/null http://localhost:3000/api/public/health` (interval 10 s, retries 30, start period 60 s).

`compose.local.yaml`: every service `env_file: [./local.env]`.
`compose.testhost.yaml`: every service `env_file: [{path: /opt/langfuse/langfuse.env, required: true}]`.

`local.env` (committed; local test values, not secrets; first line says so):
`NEXTAUTH_URL=http://localhost:3000`, fixed local passwords and keys
(`pk-lf-local-0000…`, `sk-lf-local-0000…`), `LANGFUSE_INIT_USER_EMAIL=local@example.com`,
`LANGFUSE_INIT_USER_PASSWORD=local-dev-password-not-a-secret`, `AUTH_DISABLE_USERNAME_PASSWORD=false`,
no Google settings.

`langfuse.env.example` and `google-oauth.env.example`: names only, no values.

## Secrets on the test host: `make-langfuse-env.sh`

`sudo bash make-langfuse-env.sh --admin-email <email> --google-file <path>`
- bash header, `set -euo pipefail`, root only, `umask 077`. Uses `python3 -c` (`secrets`,
  `uuid`) for random values; values are never echoed.
- Refuses if `/opt/langfuse/langfuse.env` exists (exit 1): a second run would change the
  database passwords and the project keys.
- `--google-file`: lines `AUTH_GOOGLE_CLIENT_ID=…` and `AUTH_GOOGLE_CLIENT_SECRET=…`; both
  must be present and not empty, else exit 1. The file is deleted after use.
- Writes `/opt/langfuse/langfuse.env` (600, root) with every name in the table above, and
  `NEXTAUTH_URL=http://localhost:3000`, `AUTH_DISABLE_USERNAME_PASSWORD=true`,
  `AUTH_GOOGLE_ALLOWED_DOMAINS=<domain of --admin-email>`, `AUTH_GOOGLE_ALLOW_ACCOUNT_LINKING=true`,
  `LANGFUSE_INIT_USER_NAME=<part of the email before @>`.
- Sets (adds or replaces) in `/opt/model-monitor/collector.env`:
  `LANGFUSE_OTLP_AUTH=<base64 of pk:sk>`; and in `/opt/model-monitor/check.env`:
  `CHECK_LANGFUSE_URL=http://langfuse-web:3000`, `CHECK_LANGFUSE_PUBLIC_KEY=<pk>`,
  `CHECK_LANGFUSE_SECRET_KEY=<sk>`. Both files keep mode 600.
- Prints only `stat -c '%a %U %n'` of the three files and `LANGFUSE ENV DONE`.

## nginx

`conf.d/langfuse.conf`:

```nginx
# Langfuse UI (S2-03). Engineers only, through the IAP tunnel to host port 3000.
server {
    listen 3000;
    client_max_body_size 10m;
    proxy_http_version 1.1;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    set $langfuse http://langfuse-web:3000;
    location / {
        proxy_pass $langfuse;
    }
}
```

`compose.local.yaml` ports add `127.0.0.1:3000:3000`; `compose.testhost.yaml` ports add
`3000:3000`. Firewall (project owner, once):
`gcloud compute firewall-rules create langfuse-testhost-allow-iap --network test-true-corp-ai --direction INGRESS --action ALLOW --rules tcp:3000 --source-ranges 35.235.240.0/20 --target-tags monitor-frontdoor`.

## Collector

`otel-collector.yaml`:

```yaml
exporters:
  debug: {verbosity: basic}
  file:
    path: /data/spans.jsonl
    rotation:
      max_megabytes: 100
      max_days: 14
      max_backups: 5
  # Langfuse OTLP endpoint (S2-03); project keys from the environment.
  otlphttp/langfuse:
    endpoint: http://langfuse-web:3000/api/public/otel
    headers:
      Authorization: "Basic ${env:LANGFUSE_OTLP_AUTH}"
      x-langfuse-ingestion-version: "4"
```

Pipeline exporters: `[debug, file, otlphttp/langfuse]`. If Langfuse is down, the exporter
retries and then drops; the file and the backend are not affected (S1-05 rule).

`compose.local.yaml` Collector env adds `LANGFUSE_OTLP_AUTH: <base64 of the local pk:sk>`.
The test-host Collector already reads `collector.env`.

## Trace check: 5th item and rotated files

`check_trace.py`:
- Spans: read `--spans-file` and the rotated files next to it whose name starts with the
  same stem (`spans*.jsonl`), oldest first.
- Langfuse: if `CHECK_LANGFUSE_URL`, `CHECK_LANGFUSE_PUBLIC_KEY` and `CHECK_LANGFUSE_SECRET_KEY`
  are all set, `GET <url>/api/public/v2/observations?traceId=<trace_id>&limit=100` with
  Basic auth (pk:sk), timeout 10 s, through `urllib.request`. The observation names go to
  the check logic. If any is missing, the item is `skipped`.
- An HTTP error, a timeout or a bad JSON answer: the item is `missing` with
  `Langfuse answered <status>` or `Langfuse is not reachable (<ExceptionClassName>)`. Never
  the URL with keys, never a key.
- `--backend-only` does not skip it (Langfuse holds the backend span too).

`trace_check.py`: `check(..., langfuse_names: list[str] | None = None, langfuse_error: str | None = None)`.
`None` and no error → `skipped`. Found when the names contain `monitor.ingest` (with
`--backend-only`) or `monitor.ingest` and `batch.run` (without); detail
`<n> observations in Langfuse`. Otherwise `missing` with the missing names. The item is
the 5th in the output, named `langfuse trace`.

Compose: `trace-check` (base) joins `default` and `edge` (it must reach `langfuse-web`);
local env adds `CHECK_LANGFUSE_URL=http://langfuse-web:3000` and the local keys; the test
host gets them from `check.env`.

## CI: `langfuse-smoke`

`scripts/langfuse-smoke.sh` (bash, `set -euo pipefail`, cleanup trap, `KEEP=1`):
1. `edge` network (made if absent, removed at the end if made), Langfuse local
   (`up -d --wait --wait-timeout 600`), the monitor stack, nginx.
2. The same batch POST and fake job spans as `compose-smoke.sh` (through nginx).
3. `check-trace.sh "$TRACE_ID" --wait 90`: expect `RESULT: OK (5 of 5 found)`.
4. `docker compose ... restart` of the Langfuse project, wait healthy, then
   `check-trace.sh "$TRACE_ID" --wait 60` again: still 5 of 5.
5. Through nginx `http://127.0.0.1:3000/api/public/health` gives `200`.

`.github/workflows/langfuse-smoke.yml`: `ubuntu-latest`, timeout 30 min, `permissions:
contents: read`, no secrets; on `pull_request` and `push` to `dev` with paths
`deploy/langfuse/**`, `deploy/nginx/**`, `deploy/compose/otel-collector.yaml`,
`scripts/langfuse-smoke.sh`, `.github/workflows/langfuse-smoke.yml`,
`backend/app/trace_check.py`, `backend/scripts/check_trace.py`.

## Tests

`test_langfuse_files.py`:
- images exactly as the table, MinIO by the exact digest;
- no service has `ports`; only `langfuse-web` is on `edge`, with the alias; `edge` external;
- base env: telemetry off, sign-up off, experimental off; no value that looks like a
  password, key or secret in `compose*.yaml`;
- host files: every service has the env file (local `./local.env`; test host the required
  `/opt/langfuse/langfuse.env`);
- `local.env` starts with the "local test values" comment and has
  `AUTH_DISABLE_USERNAME_PASSWORD=false`; the examples have no values;
- `make-langfuse-env.sh`: bash header, `set -euo pipefail`, `umask 077`, `chmod 600`, the
  refusal when `langfuse.env` exists, `AUTH_DISABLE_USERNAME_PASSWORD=true`, no `echo` of a
  value variable, LF endings;
- the workflow paths and `permissions`.

`test_nginx_files.py`: `langfuse.conf` listens on 3000 and proxies to the variable
`http://langfuse-web:3000`; ports local `127.0.0.1:3000:3000`, test host `3000:3000`.

`test_compose_files.py`: the Collector exporter (endpoint, both headers, the auth from
`${env:LANGFUSE_OTLP_AUTH}`), the pipeline, the rotation; `trace-check` joins `edge`
(the old "not on edge" check changes); local Collector and `trace-check` Langfuse settings.

`test_trace_check.py` / `test_check_trace_script.py`: langfuse item skipped, found (both
modes), missing with names, error text; rotated files are read; a fake Langfuse server
(`http.server` on `127.0.0.1`, random port) for found / 401 / bad JSON / not reachable;
no key in any output.

## Docs

- `TESTHOST.md`: section "Langfuse (S2-03)": VM check (`nproc`, `free -g`, `df -h /`; grow
  the disk if less than 50 GB free), the Google OAuth client (type
  Internal, redirect `http://localhost:3000/api/auth/callback/google`), the
  `google-oauth.tmp` file and its copy, the firewall rule, `make-langfuse-env.sh`, start
  Langfuse, reload nginx, restart the Collector, the tunnel command
  `gcloud compute start-iap-tunnel ai-ml-monitoring-dev-env 3000 --local-host-port=localhost:3000 --zone asia-southeast3-c`,
  sign in, add members.
- `issues.md`: S2-03 dated note (own project, Google sign-in, IAP tunnel, span file kept
  with rotation); S2-02 note (approved; SDK use with S2-05); S3-07 note (the Langfuse part is
  done in S2-03).
- `CHANGELOG.md`, `DEVLOG.md`.

## Not in scope

The backend Langfuse SDK and the scores (S2-02 / S2-05), the dashboard SSO (S3-07), staff
IP ranges, Langfuse retention settings (S1-08 decides the period), and deleting the span file.
