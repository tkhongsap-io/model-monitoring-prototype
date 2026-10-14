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

## Add or rotate an API key (S2-01)

1. On the laptop (PowerShell, repository root), write the key and hash line to files:

   ```powershell
   backend\.venv\Scripts\python.exe backend\scripts\batch_keys.py make --use-case <use_case_id> --key-out key.tmp --hash-out hash.tmp
   ```

2. For a new use case, put the key in GCP Secret Manager:

   ```powershell
   gcloud secrets create batch-api-key-<use_case_id> --data-file key.tmp
   ```

   For rotation, add a version instead:

   ```powershell
   gcloud secrets versions add batch-api-key-<use_case_id> --data-file key.tmp
   ```

3. Copy only the hash line and script to the VM, then delete the local key file:

   ```powershell
   gcloud compute scp hash.tmp backend/scripts/batch_keys.py ai-ml-monitoring-dev-env:/tmp/ --zone asia-southeast3-c --tunnel-through-iap
   ```

   ```powershell
   Remove-Item key.tmp
   ```

4. On the VM, add the hash entry to the backend env file:

   ```bash
   sudo python3 /tmp/batch_keys.py add --env-file /opt/model-monitor/backend.env --hash-file /tmp/hash.tmp
   ```

5. On the VM, in `/opt/model-monitor/compose`, recreate the backend to load the setting:

   ```bash
   sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --force-recreate --wait backend
   ```

6. For rotation only, after one successful run with the new key, list the prefixes:

   ```bash
   sudo python3 /tmp/batch_keys.py list --env-file /opt/model-monitor/backend.env
   ```

   Remove the old entry, then repeat step 5:

   ```bash
   sudo python3 /tmp/batch_keys.py remove --env-file /opt/model-monitor/backend.env --use-case <use_case_id> --hash-prefix <old prefix>
   ```

A new use case also needs its entry in `backend/registry/batch-use-cases.yaml` (pull
request and a new image) before its key works. The tool never prints a key or a full hash.

## Langfuse (S2-03)

1. On the VM, check capacity: expect 4 CPUs and 32 GB RAM. If `/` has less than
   50 GB free, grow the disk first.

   ```sh
   nproc
   ```

   ```sh
   free -g
   ```

   ```sh
   df -h /
   ```

   From the laptop:

   ```sh
   gcloud compute disks resize ai-ml-monitoring-dev-env --size 200 --zone asia-southeast3-c
   ```

   On the VM, check the device name before growing its partition and filesystem:

   ```sh
   lsblk
   ```

   ```sh
   sudo growpart /dev/nvme0n1 1 && sudo resize2fs /dev/nvme0n1p1
   ```

2. In Google Cloud Console, APIs & Services → Credentials → OAuth client ID,
   create a Web application client with an Internal consent screen. Set the redirect
   URI to `http://localhost:3000/api/auth/callback/google`. On the laptop, copy the
   template, then fill in its two values in an editor; never put them in chat.

   ```powershell
   Copy-Item deploy/langfuse/google-oauth.env.example google-oauth.tmp
   ```

3. From the laptop, allow port 3000 only from IAP:

   ```sh
   gcloud compute firewall-rules create langfuse-testhost-allow-iap --network test-true-corp-ai --direction INGRESS --action ALLOW --rules tcp:3000 --source-ranges 35.235.240.0/20 --target-tags monitor-frontdoor
   ```

4. Copy the files from the laptop, then delete the laptop's OAuth file:

   ```sh
   gcloud compute ssh ai-ml-monitoring-dev-env --zone asia-southeast3-c --tunnel-through-iap --command "mkdir -m 700 /tmp/s2-03"
   ```

   ```sh
   gcloud compute scp --recurse google-oauth.tmp deploy/langfuse deploy/nginx/conf.d/langfuse.conf deploy/nginx/compose.testhost.yaml deploy/compose/otel-collector.yaml deploy/compose/compose.yaml ai-ml-monitoring-dev-env:/tmp/s2-03/ --zone asia-southeast3-c --tunnel-through-iap
   ```

   ```powershell
   Remove-Item google-oauth.tmp
   ```

5. On the VM, install the copied files:

   ```sh
   sudo mv /tmp/s2-03/langfuse /opt/langfuse
   ```

   ```sh
   sudo mv /tmp/s2-03/langfuse.conf /opt/nginx/conf.d/
   ```

   ```sh
   sudo mv /tmp/s2-03/compose.testhost.yaml /opt/nginx/
   ```

   ```sh
   sudo mv /tmp/s2-03/otel-collector.yaml /tmp/s2-03/compose.yaml /opt/model-monitor/compose/
   ```

6. On the VM, generate secrets once. Replace the email placeholder with your company
   email. Expect three `600 root` lines and `LANGFUSE ENV DONE`. The script deletes
   the copied Google file and refuses a second run.

   ```sh
   sudo bash /opt/langfuse/make-langfuse-env.sh --admin-email <your-company-email> --google-file /tmp/s2-03/google-oauth.tmp
   ```

7. On the VM, from `/opt/langfuse`, start Langfuse:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

8. On the VM, set `BACKEND_IMAGE` in `/opt/model-monitor/compose/.env` to the build that
   contains S2-03 (`backend:14` or later), then run
   `sudo docker compose -f compose.yaml -f compose.testhost.yaml pull`.

9. On the VM, from `/opt/model-monitor/compose`, reload the Collector exporter:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

10. On the VM, from `/opt/nginx`, publish the UI through nginx:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

11. On the laptop, open the IAP tunnel:

    ```sh
    gcloud compute start-iap-tunnel ai-ml-monitoring-dev-env 3000 --local-host-port=localhost:3000 --zone asia-southeast3-c
    ```

    Or, when you connect to the VM with VS Code Remote-SSH, forward port 3000 in the
    **Ports** panel. The local port must be 3000.

    Open `http://localhost:3000`, sign in with Google, and open project `model-monitor`.

12. Add engineers in Settings → Members using their company email. They sign in with Google.

13. On the VM, verify that Langfuse publishes no port, then check a trace:

    ```sh
    sudo docker ps --format '{{.Names}} {{.Ports}}' | grep langfuse
    ```

    ```sh
    sudo bash /opt/model-monitor/compose/check-trace.sh <trace_id>
    ```

    The output includes the fifth item, `langfuse trace`.

## Batch evaluator (S2-05)

1. Copy `deploy/compose/add-langfuse-backend-env.sh` to `/opt/model-monitor/compose/`.
2. On the VM, give the backend the Langfuse keys. Expect `600 root` and `BACKEND LANGFUSE ENV DONE`.

   ```sh
   sudo bash /opt/model-monitor/compose/add-langfuse-backend-env.sh
   ```

3. Set `BACKEND_IMAGE` in `/opt/model-monitor/compose/.env` to the build that contains
   S2-05, then from `/opt/model-monitor/compose`:

   ```sh
   sudo docker compose -f compose.yaml -f compose.testhost.yaml pull && sudo docker compose -f compose.yaml -f compose.testhost.yaml up -d --wait
   ```

4. Check readiness. `batch_evaluator.unevaluated` and `langfuse_pending` must be `0`
   after one or two minutes.

   ```sh
   curl -s http://127.0.0.1:8000/api/readiness
   ```

5. In Langfuse, open the trace of the latest RTR run. It must show the `grade` and
   `delivery_grade` scores.

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
