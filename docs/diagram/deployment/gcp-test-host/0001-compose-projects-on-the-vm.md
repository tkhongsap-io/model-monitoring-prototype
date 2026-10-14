---
status: current
date: 2026-10-13
author: Prakasit Issanapong <prakasit.tar@outlook.com>
related: []
---

# Deployment, gcp-test-host 0001: the Compose projects on the VM

![Deployment, gcp-test-host 0001](0001-compose-projects-on-the-vm.drawio.svg)

## What it shows

Where each part runs on the GCP test host, and the protocol and port between the places:
the Compute Engine VM with the Compose projects `nginx`, `model-monitor` and `langfuse`,
the Cloud SQL instance, Artifact Registry, and the nodes outside (the Cloud Run job, GitHub
Actions, an engineer's laptop). Each artifact names its image and its ports and volumes.

The picture leaves out what the components do (the architecture) and the machine size. It
is drawn from the deploy files.

## What changed since the previous version

First recorded version.

Corrected in place on 2026-10-14 (drawing mistakes; the deploy files did not change):

- The Cloud Run job is inside the VPC: the jobs run in the same VPC as the VM (S1-04).
- `trace-check` has its paths: TLS 5432 to Cloud SQL and HTTP 3000 to `langfuse-web`, and
  its read-only mount of `collector-data`.
- `collector-init` (`busybox` 1.37.0), which sets the owner of `collector-data`, is drawn.
- `clickhouse` lists both of its volumes, `clickhouse-data` and `clickhouse-logs`.
- The secrets note names the S1-11 password files.

## Key

| Mark | Means |
|---|---|
| Box with a folded edge | A node: a place where software runs |
| Grey box in a node | An artifact: one service, with its image |
| Rounded grey box | A network or a Compose project |
| Small logo | The product of a node or an artifact; the sources are in `docs/diagram/icons/README.md` |
| Arrow | A communication path, with protocol and port |

## Sources

- `deploy/compose/compose.yaml`, `compose.testhost.yaml`, `otel-collector.yaml`
- `deploy/nginx/compose.yaml`, `compose.testhost.yaml`, `conf.d/`
- `deploy/langfuse/compose.yaml`, `compose.testhost.yaml`
- `deploy/sql/s1-11/`; `DEVLOG.md` (S1-04: the jobs in the same VPC)
- `.github/workflows/build-image.yml`
- `changes/2026-10-02-batch-monitoring-mvp/issues.md`, S1-04 (Cloud SQL, IAP)
