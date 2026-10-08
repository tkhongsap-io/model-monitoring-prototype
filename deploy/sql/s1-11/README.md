# S1-11: database accounts on the test host

Cloud SQL `sandbox-pg17-db`, database `monitor`. The goal (S1-11, R2 least privilege):

| Account | Rights | Used by |
|---|---|---|
| `monitor_backend` | Owns the database and the tables; reads and writes; runs the migrations. Not in `cloudsqlsuperuser`, no `CREATEROLE`, no `CREATEDB`. | The backend (`DATABASE_URL`) |
| `monitor_read` (group, no login) | `SELECT` on all tables, also future tables | — |
| `monitor_readonly` | Member of `monitor_read` | The S1-07 trace check tool and other checks |
| `dev_itthisak`, `dev_prakasit` | Members of `monitor_read` | Developers, with `psql` on the VM |
| `postgres` | Cloud SQL admin | Platform only |

Why a new backend user: `monitor_app` was made with `gcloud sql users create`, so Cloud SQL
put it in `cloudsqlsuperuser`, and `postgres` cannot take it out (no ADMIN OPTION on that
group). A role made with SQL is not in that group. The database belonged to
`cloudsqlsuperuser`, so the backend could create tables only through that group; phase 1
makes `monitor_backend` the owner first.

All passwords stay in `/opt/model-monitor/secrets` on the VM (folder 700, files 600, root).
No script prints a password.

## Run the phases

Run each command from the repository root in PowerShell, one at a time. Send the output
to the reviewer before the next phase. Stop at the first unexpected result.

Shortcut used below (paste it first):

```powershell
$vm = @("ai-ml-monitoring-dev-env", "--zone", "asia-southeast3-c", "--tunnel-through-iap")
```

**Copy the scripts and the admin password.** The admin password goes to a local file,
then into a folder that only you can read on the VM, and phase 0 deletes the copy.

```powershell
gcloud compute ssh @vm --command "mkdir -m 700 /tmp/s1-11"
```

```powershell
gcloud secrets versions access latest --secret sandbox-pg17-db --out-file admin-password.tmp
```

```powershell
$files = @((Get-ChildItem deploy\sql\s1-11 -File).FullName) + "admin-password.tmp"; gcloud compute scp @files ai-ml-monitoring-dev-env:/tmp/s1-11/ --zone asia-southeast3-c --tunnel-through-iap
```

```powershell
Remove-Item admin-password.tmp
```

**Phase 0: passwords** (expected: `600 root` for each file, then `PHASE 0 DONE`)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/phase0-passwords.sh"
```

**Phase 1: `monitor_backend` owns the database** (expected: owner `monitor_backend`; `f | f`)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/run-sql.sh postgres phase1.sql"
```

**Phase 2: move the tables** (expected: only `monitor_backend`; `0` objects left)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/run-sql.sh monitor_app phase2.sql"
```

**Phase 3: read users** (expected: five roles, all `f | f`; only `monitor_read` cannot log in)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/run-sql.sh postgres phase3.sql"
```

**Phase 4: switch the backend** (expected: user `monitor_backend`, readiness `ready`,
`database user: monitor_backend`, `PHASE 4 DONE`)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/phase4-switch.sh"
```

If phase 4 fails, undo it (only before phase 6):

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/phase4-rollback.sh"
```

**Phase 5: checks** (expected: `f | f | f` and `monitor_backend: OK`; for each read user a
count, `insert refused: OK` and `create refused: OK`)

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/run-sql.sh monitor_backend phase5-backend.sql"
```

```powershell
foreach ($u in "monitor_readonly", "dev_itthisak", "dev_prakasit") { gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/run-sql.sh $u phase5-read.sql" }
```

**Phase 6: delete `monitor_app` and clean up** (only after phase 5 passed; the delete
cannot be undone, but `monitor_app` then owns nothing)

```powershell
gcloud sql users delete monitor_app --instance sandbox-pg17-db
```

```powershell
gcloud compute ssh @vm --command "sudo bash /tmp/s1-11/phase6-cleanup.sh"
```

## How a developer connects (read-only)

On the VM, through IAP SSH, as yourself:

```powershell
gcloud compute ssh @vm
```

Then on the VM (your password is in the file of your account; `sudo` reads it):

```bash
sudo docker run --rm -it --network host -e PGPASSWORD="$(sudo cat /opt/model-monitor/secrets/dev-itthisak.password)" -v /opt/model-monitor/cloudsql-server-ca.pem:/ca.pem:ro postgres:17.11-bookworm psql "host=10.188.112.8 dbname=monitor user=dev_itthisak sslmode=verify-ca sslrootcert=/ca.pem"
```
