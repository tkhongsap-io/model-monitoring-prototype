---
status: current
date: 2026-10-14
author: eatrabyo <itthisak.prk@gmail.com>
related: [ADR-0002]
format: mermaid
---

# Architecture, gcp-test-host 0004: the GCP test host with the dashboard and the evaluator

```mermaid
flowchart LR
  rai["RAI team<br/>health grid, through IAP"]
  eng["Engineers, platform team<br/>dashboard, Langfuse and SSH, through IAP"]
  gws["Google Workspace<br/>Langfuse sign-in, company domain only"]
  gha["GitHub Actions<br/>build-image.yml"]
  subgraph gcp["GCP: one VPC, private IPs only"]
    jobs["GCP batch jobs<br/>Cloud Run jobs in the same VPC<br/>registered: rtr-fraud-validation"]
    iap["IAP<br/>SSH and the tunnels to 3000 and 8082"]
    registry["Artifact Registry<br/>backend and dashboard images"]
    subgraph vm["Compute Engine VM, Docker Compose, no external IP"]
      frontdoor["Front door, nginx<br/>80: job API and OTLP<br/>3000: Langfuse UI<br/>8082: dashboard, GET only<br/>other paths: 404"]
      subgraph mm["Compose project model-monitor"]
        backend["Monitor backend<br/>job API, dashboard API, health<br/>registry file in the image"]
        evaluator["Batch evaluator<br/>worker in the backend process<br/>lease batch-evaluator, core metrics"]
        dashboard["Dashboard<br/>control-tower UI, health grid<br/>dashboard file server"]
        collector["OTel Collector<br/>4319 token, 4318 inside"]
        spanfile[("Span file<br/>volume collector-data")]
        tracecheck["Trace check tool<br/>run by hand"]
      end
      subgraph lf["Compose project langfuse"]
        lfweb["Langfuse web<br/>Google sign-in, no sign-up"]
        lfworker["Langfuse worker"]
        lfstores[("PostgreSQL, ClickHouse,<br/>Redis, MinIO")]
      end
    end
    sql[("Cloud SQL, PostgreSQL 17<br/>database monitor<br/>batch_runs, batch_evaluations")]
  end
  jobs -->|"run summary, HTTP 80"| frontdoor
  jobs -->|"OTLP spans, token, no text"| frontdoor
  rai -.->|"IAP tunnel 8082"| iap
  eng -.->|"IAP tunnel 3000, 8082, SSH 22"| iap
  iap -.-> frontdoor
  eng -.->|"Google sign-in"| gws
  frontdoor -->|"/api/batch/runs, /api/health"| backend
  frontdoor -->|"/api/live/*, /api/version"| backend
  frontdoor -->|"/ static files"| dashboard
  frontdoor -->|"/otlp/*"| collector
  frontdoor -->|"3000"| lfweb
  backend -->|"run rows, TLS 5432"| sql
  evaluator -->|"reads runs, writes evaluations, TLS 5432"| sql
  evaluator -->|"scores, 3000"| lfweb
  backend -->|"OTLP 4318"| collector
  collector -->|"OTLP"| lfweb
  collector --> spanfile
  tracecheck -->|"TLS 5432, monitor_readonly"| sql
  tracecheck --> spanfile
  tracecheck -->|"3000"| lfweb
  lfweb --> lfstores
  lfworker --> lfstores
  gha -.->|"push (WIF)"| registry
  registry -.->|"pull"| vm
```

## What it shows

The batch monitoring MVP on the GCP test host as it runs on 2026-10-14: one Compute Engine
VM with three Docker Compose projects (`nginx`, `model-monitor`, `langfuse`), Cloud SQL,
and the GCP batch jobs in the same VPC. It shows who connects, the front door and its
ports, the components, the stores, and the flows between them.

The picture leaves out AWS production ([`aws-production`](../aws-production/README.md)),
the content of a run summary, the grading rules (the decision `run-grade`), the prototype
code that is not mounted, the local stack, the volumes and the account names. It contains
no IP address, token or internal URL.

## What changed since the previous version

Version 0003 listed the dashboard and the evaluator as "not on the test host yet". Both
are now deployed (`backend:16`, `dashboard:16`, 2026-10-14).

| Version 0003 | This version | Source |
|---|---|---|
| — | **RAI team**: opens the health grid through an IAP tunnel to 8082 | S2-07; `TESTHOST.md` "Dashboard (S2-07)" |
| Front door: 80 and 3000 | Also **8082**: the dashboard (GET only); `/` to the dashboard, `/api/live/*` and `/api/version` to the backend | `deploy/nginx/conf.d/dashboard.conf` |
| — | **Dashboard**: the unchanged control-tower UI (tab "Health grid"), served by the dashboard file server | `deploy/dashboard/`, `artifacts/control-tower` |
| Monitor backend: batch API and health | Also the **dashboard API** (read-only) | `backend/app/api/dashboard_routes.py` |
| — | **Batch evaluator**: grades each stored run, writes `batch_evaluations`, sends the scores to Langfuse | `backend/app/batch_evaluator.py` (S2-05) |
| Cloud SQL: database monitor | Names the two batch tables, `batch_runs` and `batch_evaluations` | `backend/app/db.py` |
| Artifact Registry: backend image | Backend and dashboard images | `.github/workflows/build-image.yml` |
| Firewall: 3000 and 22 from IAP | 3000, 8082 and 22 from the IAP range only (in the IAP node's label) | firewall `langfuse-testhost-allow-iap` |

Notes of 0003 that are not in the block (a Mermaid version has no free notes) stay true:
the identity-only data scope (records: []), no DNS name and no HTTPS on the test host, the
fixed versions, and that the stores publish no port.

Recorded as a Mermaid version: draw.io desktop is not installed on the machine that
recorded it. It has no product icons and no image file.

## Key

| Mark | Means |
|---|---|
| Solid arrow | Data flow |
| Dotted arrow | Control or deployment: access, sign-in, images |
| Cylinder | A store |
| Group | A boundary: the VPC, the VM, a Compose project |

## Sources

- `deploy/compose/`, `deploy/nginx/` (with `conf.d/dashboard.conf`), `deploy/dashboard/`,
  `deploy/langfuse/compose.yaml`
- `backend/app/main.py`, `api/dashboard_routes.py`, `batch_evaluator.py`,
  `adapters/langfuse_scores.py`, `db.py`
- `artifacts/control-tower/src/components/ChromeLive.tsx` (tab "Health grid")
- `.github/workflows/build-image.yml`
- `changes/2026-10-14-s2-05-batch-evaluator/`, `changes/2026-10-14-s2-07-dashboard/`
- `deploy/compose/TESTHOST.md`; `DEVLOG.md`, 2026-10-14
- `docs/adr/0002-batch-push-ingest.md`
- Version 0003
