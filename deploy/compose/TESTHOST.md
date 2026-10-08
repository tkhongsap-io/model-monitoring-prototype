# Deploy the backend to the GCP test host

The test host for Sprints 1 to 3 (S1-04): the VM `ai-ml-monitoring-dev-env`
(`asia-southeast3-c`, no public IP) with Docker Compose, and the Cloud SQL instance
`sandbox-pg17-db` (PostgreSQL 17, private IP only, TLS only). Project
`gcp-noexp-wl-nprd-automationsb`.

The VM uses the base file and `compose.testhost.yaml`. The backend image comes from
Artifact Registry (`asia-southeast3-docker.pkg.dev/gcp-noexp-wl-nprd-automationsb/model-monitoring/dev/backend:<tag>`).
Until the front door exists (S1-06 test-host part), the backend listens only on
`127.0.0.1:8000` inside the VM.

## Files on the VM

| Path | Content | Mode |
|---|---|---|
| `/opt/model-monitor/compose/` | `compose.yaml`, `compose.testhost.yaml`, `otel-collector.yaml` from this folder | 644 |
| `/opt/model-monitor/compose/.env` | `BACKEND_IMAGE=<image>:<tag>` (not a secret) | 644 |
| `/opt/model-monitor/backend.env` | `DATABASE_URL` (user `monitor_backend`) and `BATCH_API_KEY_SHA256` (see `backend.env.example`) | **600** |
| `/opt/model-monitor/cloudsql-server-ca.pem` | The server CA of `sandbox-pg17-db` (public certificate) | 644 |

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

## Roll back

Set `BACKEND_IMAGE` to the previous tag, then `pull` and `up -d --wait`. The migrations are
additive, so an older image works with a newer database.
