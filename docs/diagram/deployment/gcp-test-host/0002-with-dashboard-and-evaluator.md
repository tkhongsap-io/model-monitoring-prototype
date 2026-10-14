---
status: current
date: 2026-10-14
author: eatrabyo <itthisak.prk@gmail.com>
related: []
format: mermaid
---

# Deployment, gcp-test-host 0002: the Compose projects on the VM, with the dashboard

```mermaid
flowchart TB
  laptop["«device» Engineer's or RAI laptop<br/>browser, gcloud IAP tunnel or VS Code port forward"]
  gha["«node» GitHub Actions<br/>build-image.yml: backend and dashboard images, one run number"]
  subgraph gcp["GCP: one VPC, private IPs only"]
    registry["«node» Artifact Registry<br/>dev/backend and dev/dashboard, immutable tags"]
    job["«node» Cloud Run job<br/>job code: OTel SDK, send step"]
    subgraph vm["«node» Compute Engine VM, Docker Engine and Compose"]
      subgraph pnginx["Compose project nginx"]
        frontdoor["«artifact» front door<br/>nginx-unprivileged 1.28.0<br/>host 80 to 8080, host 3000, host 8082"]
      end
      subgraph pmm["Compose project model-monitor"]
        backend["«artifact» backend<br/>backend image, 8000 host loopback only<br/>batch API, dashboard API, evaluator worker"]
        dashboard["«artifact» dashboard<br/>dashboard image: dashboard file server<br/>nginx-unprivileged 1.28.0, 8090, no published port"]
        collector["«artifact» collector<br/>collector-contrib 0.161.0, 4318 and 4319<br/>volume collector-data"]
        tracecheck["«artifact» trace-check<br/>backend image, run on demand<br/>collector-data read-only"]
        collinit["«artifact» collector-init<br/>busybox 1.37.0, runs once"]
      end
      subgraph plf["Compose project langfuse (no published port)"]
        lfweb["«artifact» langfuse-web<br/>langfuse 4.50.0, 3000"]
        lfworker["«artifact» langfuse-worker<br/>langfuse-worker 4.50.0"]
        lfstores[("«artifact» postgres 17.11, clickhouse 25.12.11.4<br/>redis 7.4.11, minio by digest")]
      end
    end
    sql[("«node» Cloud SQL for PostgreSQL 17<br/>database monitor, private IP, TLS only")]
  end
  job -->|"HTTP 80"| frontdoor
  laptop -->|"IAP tunnel, HTTP 3000 and 8082"| frontdoor
  gha -->|"push, 443"| registry
  registry -->|"pull"| backend
  registry -->|"pull"| dashboard
  frontdoor -->|"HTTP 8000"| backend
  frontdoor -->|"HTTP 8090"| dashboard
  frontdoor -->|"HTTP 4319"| collector
  frontdoor -->|"HTTP 3000"| lfweb
  backend -->|"HTTP 4318"| collector
  backend -->|"TLS 5432"| sql
  backend -->|"HTTP 3000, scores"| lfweb
  collector -->|"HTTP 3000"| lfweb
  tracecheck -->|"TLS 5432"| sql
  tracecheck -->|"HTTP 3000"| lfweb
  collinit -->|"sets the owner of collector-data"| collector
  lfweb -->|"TCP 5432, 6379, 8123, 9000"| lfstores
  lfworker -->|"TCP 5432, 6379, 8123, 9000"| lfstores
```

## What it shows

Where each part runs on the GCP test host, and the protocol and port between the places:
the Compute Engine VM with the Compose projects `nginx`, `model-monitor` and `langfuse`,
Cloud SQL, Artifact Registry, and the nodes outside (the Cloud Run job, GitHub Actions, a
laptop). Each artifact names its image and its ports.

The picture leaves out what the components do (the architecture), the machine size and
the volumes of Langfuse. It is drawn from the deploy files.

## What changed since the previous version

| Version 0001 | This version | Source |
|---|---|---|
| — | The `dashboard` artifact (S2-07): the dashboard image with the dashboard file server on 8090, no published port | `deploy/compose/compose.yaml`, `deploy/dashboard/` |
| Front door: host 80 and 3000 | Also host **8082** (dashboard); the front door sends `/` to the dashboard and the dashboard API to the backend | `deploy/nginx/compose.testhost.yaml`, `conf.d/dashboard.conf` |
| Artifact Registry: the backend image | The backend and dashboard images, one run number for both | `.github/workflows/build-image.yml` |
| Backend: batch API | Also the dashboard API and the evaluator worker (S2-05) | `backend/app/main.py`, `backend/app/batch_evaluator.py` |
| — | Backend to `langfuse-web` on HTTP 3000: the scores of each graded run (S2-05) | `deploy/compose/add-langfuse-backend-env.sh`, `backend/app/adapters/langfuse_scores.py` |
| Laptop: HTTP 3000 through IAP | HTTP 3000 and 8082 through IAP; also used by the RAI team | `TESTHOST.md`; firewall `langfuse-testhost-allow-iap` (tcp:3000, tcp:8082) |

Recorded as a Mermaid version: draw.io desktop is not installed on the machine that
recorded it. It has no product icons and no image file.

## Key

| Mark | Means |
|---|---|
| Box with `«node»` or `«device»` | A node: a place where software runs |
| Box with `«artifact»` | One service, with its image |
| Rounded group | A network or a Compose project |
| Arrow | A communication path, with protocol and port |

## Sources

- `deploy/compose/compose.yaml`, `compose.testhost.yaml`, `add-langfuse-backend-env.sh`
- `deploy/nginx/compose.yaml`, `compose.testhost.yaml`, `conf.d/` (with `dashboard.conf`)
- `deploy/dashboard/Dockerfile`, `file-server.conf`
- `deploy/langfuse/compose.yaml`
- `.github/workflows/build-image.yml`
- `deploy/compose/TESTHOST.md`, sections "Batch evaluator (S2-05)" and "Dashboard (S2-07)"
- `DEVLOG.md`, 2026-10-14 (S2-05 and S2-07 deployed: `backend:16`, `dashboard:16`)
- Version 0001
