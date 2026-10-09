# Deploy the backend to the GCP test host

The test host for Sprints 1 to 3 (S1-04): the VM `ai-ml-monitoring-dev-env`
(`asia-southeast3-c`, no public IP) with Docker Compose, and the Cloud SQL instance
`sandbox-pg17-db` (PostgreSQL 17, private IP only, TLS only). Project
`gcp-noexp-wl-nprd-automationsb`.

The VM uses the base file and `compose.testhost.yaml`. The backend image comes from
Artifact Registry (`asia-southeast3-docker.pkg.dev/gcp-noexp-wl-nprd-automationsb/model-monitoring/dev/backend:<tag>`).
The GCP jobs reach the monitor through nginx on port 80 (`deploy/nginx`, on the VM
`/opt/nginx`). The backend also listens on `127.0.0.1:8000` for operators inside the VM.

## Files on the VM

| Path | Content | Mode |
|---|---|---|
| `/opt/model-monitor/compose/` | `compose.yaml`, `compose.testhost.yaml`, `otel-collector.yaml` from this folder | 644 |
| `/opt/model-monitor/compose/.env` | `BACKEND_IMAGE=<image>:<tag>` (not a secret) | 644 |
| `/opt/model-monitor/backend.env` | `DATABASE_URL` (user `monitor_backend`) and `BATCH_API_KEY_SHA256` (see `backend.env.example`) | **600** |
| `/opt/model-monitor/cloudsql-server-ca.pem` | The server CA of `sandbox-pg17-db` (public certificate) | 644 |
| `/opt/model-monitor/compose/check-trace.sh`, `make-check-env.sh` | The trace check tool (S1-07) from this folder | 755 |
| `/opt/model-monitor/check.env` | `CHECK_DATABASE_URL` with `monitor_readonly` (made by `make-check-env.sh`) | **600** |
| `/opt/nginx/` | `compose.yaml`, `compose.testhost.yaml`, `conf.d/` from `deploy/nginx` | 644 |
| `/opt/model-monitor/compose/make-collector-env.sh` | Token setup script from this folder | 755 |
| `/opt/model-monitor/collector.env` | `OTLP_TOKEN`, made by `make-collector-env.sh` | **600** |

Never put a password or an API key in git, in chat, or in a command that prints it.

## One-time setup

1. Database and user (from a computer with `gcloud`):
   - `gcloud sql databases create monitor --instance sandbox-pg17-db`
   - Accounts: follow `deploy/sql/s1-11/README.md`. The backend user `monitor_backend` is made
     with SQL, not with `gcloud sql users create`, because a `gcloud` user is a member of
     `cloudsqlsuperuser` (S1-11).
2. Server CA: `gcloud sql instances describe sandbox-pg17-db --format="value(serverCaCert.cert)" > cloudsql-server-ca.pem`
3. Start the VM: `gcloud compute instances start ai-ml-monitoring-dev-env --zone asia-southeast3-c`
4. Install Docker Engine and the Compose plugin on the VM (Debian 12), from Docker's apt
   repository, through `gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap`.
5. Let Docker pull with the VM's service account:
   `sudo gcloud auth configure-docker asia-southeast3-docker.pkg.dev --quiet`

## Deploy or update

1. Copy the files of the table above to the VM (`gcloud compute scp --tunnel-through-iap`).
2. On the VM, in `/opt/model-monitor/compose`:

```bash
sudo docker compose -f compose.yaml -f compose.testhost.yaml pull
```

```bash
sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
```

3. Check on the VM:

```bash
curl -s http://127.0.0.1:8000/api/health
```

```bash
curl -s http://127.0.0.1:8000/api/readiness
```

Expected: health `200`. Readiness `200`, or `503` with the reason (for example "no valid
entry" until the first API key hash is in `backend.env`).

To deploy a new backend image, change `BACKEND_IMAGE` in `.env`, then `pull` and `up -d --wait`.

## Front door and OTLP token (S1-06)

The project owner runs these steps; never print the token or paste it into chat.
Laptop commands use PowerShell from the repository root. VM commands use bash.

1. Log in if the login expired:

```powershell
gcloud auth login
```

2. Make the token file on the laptop without displaying its value:

```powershell
backend\.venv\Scripts\python.exe -c "import secrets,pathlib; pathlib.Path('otlp-token.tmp').write_text(secrets.token_urlsafe(32), encoding='ascii')"
```

3. Check the existing secret's replication:

```powershell
gcloud secrets describe batch-api-key-rtr-fraud-validation --format="yaml(replication)"
```

Create the new secret with the same replication. If the existing secret is user-managed,
add `--replication-policy user-managed --locations <region>` to this command:

```powershell
gcloud secrets create otlp-token --data-file otlp-token.tmp
```

4. Make a private staging folder on the VM:

```powershell
gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "mkdir -m 700 /tmp/s1-06"
```

5. Copy the token file, then delete the laptop copy after the copy succeeds:

```powershell
gcloud compute scp otlp-token.tmp ai-ml-monitoring-dev-env:/tmp/s1-06/ --zone asia-southeast3-c --tunnel-through-iap
```

```powershell
Remove-Item otlp-token.tmp
```

6. Copy `deploy/nginx` to `/opt/nginx` and the changed `deploy/compose` files to
`/opt/model-monitor/compose`, through `/tmp` with `gcloud compute scp`, then `sudo mv`.
For the first nginx installation:

```powershell
gcloud compute scp --recurse deploy/nginx ai-ml-monitoring-dev-env:/tmp/s1-06/ --zone asia-southeast3-c --tunnel-through-iap
```

```powershell
gcloud compute scp deploy/compose/compose.yaml deploy/compose/compose.testhost.yaml deploy/compose/otel-collector.yaml deploy/compose/make-collector-env.sh ai-ml-monitoring-dev-env:/tmp/s1-06/ --zone asia-southeast3-c --tunnel-through-iap
```

On the VM:

```bash
sudo mv /tmp/s1-06/nginx /opt/nginx
```

```bash
sudo mv /tmp/s1-06/compose.yaml /tmp/s1-06/compose.testhost.yaml /tmp/s1-06/otel-collector.yaml /tmp/s1-06/make-collector-env.sh /opt/model-monitor/compose/
```

```bash
sudo chmod 755 /opt/model-monitor/compose/make-collector-env.sh
```

7. On the VM, make the external network once:

```bash
sudo docker network create edge
```

8. On the VM, install the token file:

```bash
sudo bash /opt/model-monitor/compose/make-collector-env.sh /tmp/s1-06/otlp-token.tmp
```

Expected: `600 root /opt/model-monitor/collector.env`, then `COLLECTOR ENV DONE`.
The script deletes the copied token file and its folder if empty.

9. On the VM, in `/opt/model-monitor/compose`:

```bash
sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
```

10. On the VM, in `/opt/nginx`:

```bash
sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
```

11. Check on the VM:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.10.0.4/api/health
```

Expected: `200`.

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.10.0.4/api/live/portfolio
```

Expected: `404`.

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://10.10.0.4/otlp/v1/traces -H 'Content-Type: application/json' --data '{}'
```

Expected: `401`.

12. The job (Prakasit): grant `secretAccessor` on `otlp-token` to the job service account;
set `OTEL_EXPORTER_OTLP_ENDPOINT=http://10.10.0.4/otlp` and
`OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <token>` from the secret at runtime.
From the job runtime, this must return `200` (closes the S1-04 test):

```bash
curl http://10.10.0.4/api/health
```

Rollback: in `/opt/nginx`, close port 80; the monitor keeps working inside the VM:

```bash
sudo docker compose -f compose.yaml -f compose.testhost.yaml down
```

Token change: add a secret version, repeat steps 4, 5, 8 and 9, then restart the jobs.

## Check a trace (S1-07)

One time, after the files are copied (the image must contain `scripts/check_trace.py`):

```bash
sudo bash /opt/model-monitor/compose/make-check-env.sh
```

Expected: `600 root /opt/model-monitor/check.env`, then `CHECK ENV DONE`.

From a laptop, in one line (use `--backend-only` until a GCP job sends spans):

```bash
gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "sudo bash /opt/model-monitor/compose/check-trace.sh <trace_id> --backend-only"
```

Exit 0: all checked items found; 1: an item is missing; 2: usage or setup error.

## Roll back

Set `BACKEND_IMAGE` to the previous tag, then `pull` and `up -d --wait`. The migrations are
additive, so an older image works with a newer database.
