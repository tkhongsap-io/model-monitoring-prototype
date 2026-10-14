---
status: current
date: 2026-10-14
author: eatrabyo <itthisak.prk@gmail.com>
related: []
format: mermaid
---

# Data flow, batch-run 0002: the data of one run, with its grade and the dashboard

```mermaid
flowchart LR
  job["GCP batch job<br/>Cloud Run job"]
  eng["Engineers"]
  rai["RAI team, engineers<br/>dashboard"]
  subgraph vmtb["Trust boundary: test host VM, Docker networks, no published store port"]
    p1(("1.0 Route request"))
    p2(("2.0 Ingest run summary"))
    p3(("3.0 Collect spans"))
    p4(("4.0 Store and show traces"))
    p5(("5.0 Check a trace"))
    p6(("6.0 Grade run"))
    p7(("7.0 Show dashboard"))
    d2[("D2 span file")]
    d3[("D3 Langfuse stores")]
    d4[("D4 registry, key hashes")]
  end
  subgraph sqltb["Trust boundary: Cloud SQL, private IP, TLS only"]
    d1[("D1 batch_runs")]
    d5[("D5 batch_evaluations")]
  end
  job -->|"run summary, API key, traceparent"| p1
  job -->|"spans without text, OTLP token"| p1
  p1 -->|"result: status, IDs, trace ID"| job
  p1 -->|"run summary, API key, traceparent"| p2
  p2 -->|"result"| p1
  p1 -->|"spans, OTLP token"| p3
  d4 -->|"use cases, key hashes"| p2
  p2 -->|"backend spans"| p3
  p2 -->|"run row"| d1
  p3 -->|"spans"| d2
  p3 -->|"spans, project keys"| p4
  p4 -->|"traces"| d3
  d3 -->|"observations"| p4
  p4 -->|"traces, Langfuse UI"| eng
  d1 -->|"stored run"| p5
  d2 -->|"spans"| p5
  p4 -->|"observations"| p5
  eng -->|"trace ID"| p5
  p5 -->|"check result"| eng
  d1 -->|"stored run, earlier request counts"| p6
  d4 -->|"turnaround limit"| p6
  p6 -->|"evaluation: metrics, grades"| d5
  p6 -->|"scores, project keys"| p4
  d4 -->|"use cases"| p7
  d1 -->|"latest run, no payload"| p7
  d5 -->|"grades, history"| p7
  rai -->|"dashboard request"| p1
  p1 -->|"dashboard request"| p7
  p7 -->|"portfolio and detail data"| p1
  p1 -->|"dashboard page and data"| rai
```

## What it shows

The data of one batch run on the GCP test host: what leaves the GCP job, which processes
handle it, where it is stored, how it is graded, and what the dashboard reads. It marks
the two trust boundaries: the test host VM and Cloud SQL.

The picture leaves out control (what starts the worker), the order in time, and the
grading rules (the decision `run-grade`). No record text crosses a boundary in October
(`records: []`), and process 7.0 never reads `payload`.

## What changed since the previous version

| Version 0001 | This version | Source |
|---|---|---|
| — | **6.0 Grade run** (S2-05): reads the stored run and the earlier request counts from D1 and the turnaround limit from D4; writes D5; sends the scores to 4.0 | `backend/app/batch_evaluator.py` |
| — | **D5 batch_evaluations** in the Cloud SQL boundary | `backend/app/db.py` (migration 9) |
| — | **7.0 Show dashboard** (S2-07): reads the use cases (D4), the latest run (D1, no `payload`) and the grades and history (D5) | `backend/app/dashboard_view.py`, `api/dashboard_routes.py` |
| — | External entity **RAI team, engineers**: the dashboard, through 1.0 (front-door port 8082) | `deploy/nginx/conf.d/dashboard.conf` |

Recorded as a Mermaid version: draw.io desktop is not installed on the machine that
recorded it.

## Key

| Mark | Means |
|---|---|
| Circle | A process, numbered |
| Cylinder | A data store, numbered D1 to D5 |
| Box | An external entity |
| Group | A trust boundary |
| Arrow | A data flow, labelled with the data |

## Sources

- `backend/app/api/batch_routes.py`, `dashboard_routes.py`; `backend/app/batch_evaluator.py`,
  `dashboard_view.py`, `db.py`, `registry.py`
- `deploy/compose/otel-collector.yaml`, `deploy/nginx/conf.d/`
- `changes/2026-10-14-s2-05-batch-evaluator/spec.md`, `changes/2026-10-14-s2-07-dashboard/spec.md`
- Version 0001
