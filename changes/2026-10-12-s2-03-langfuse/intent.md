# Intent: self-hosted Langfuse and the Collector export (S2-03)

- **Status:** Accepted (design approved in chat by the project owner on 2026-10-12)
- **Issue:** S2-03 (#17). S2-02 (#16) stays approved (packages approved 2026-10-05); its
  SDK use (scores) comes with S2-05.
- **Risk tier:** R1 (identity-only MVP, decided 2026-10-09)
- **Plan of record:** `changes/2026-10-02-batch-monitoring-mvp/issues.md`, section S2-03

## Problem

Engineers can see a run's trace only with the trace check tool on the VM. The spans sit in
a file that grows without a limit. S2-03 brings the planned Langfuse UI: each GCP run as one
trace, for engineers only.

## Outcome

Langfuse 4.50.0 runs on the test host as its own Compose project. The Collector sends every
span to it. Engineers open it through an IAP tunnel at `http://localhost:3000` and sign in
with their company Google account. Its databases are reachable by nobody but Langfuse. A
CI test proves that a run's spans appear in Langfuse and stay after a restart.

## Decisions (project owner, 2026-10-12)

| Decision | Reason |
|---|---|
| Langfuse is its own Compose project `langfuse` (`deploy/langfuse/`, `/opt/langfuse/` on the VM) | Restarts and upgrades do not touch the monitor; the same pattern as nginx |
| PostgreSQL, ClickHouse, Redis and MinIO publish no port and are only on the project's private network; only `langfuse-web` joins `edge` (alias `langfuse-web`) | They are Langfuse's own stores; no developer or user connects to them |
| Langfuse's Redis is not shared. Another app that needs Redis gets its own. | Langfuse uses Redis as a job queue with `noeviction`; sharing would couple failures and settings |
| Google sign-in (company domain only), password login off, public sign-up off, on the test host now | Safer than passwords; Google accepts `http://localhost` redirects, so it works through the tunnel without DNS. Moves the Langfuse part of S3-07 forward. |
| Engineers reach the UI through an IAP tunnel to port 3000; the firewall allows port 3000 only from the IAP range `35.235.240.0/20` | No staff IP ranges and no network team needed; engineers already use IAP for SSH |
| Secrets are made on the VM by `make-langfuse-env.sh`; the Google client ID and secret come from a file the project owner copies to the VM | They are used only on the VM; the coding tool never handles secret values |
| The span file stays, with rotation; the trace check tool also reads the rotated files and gets a 5th item, "langfuse trace" | The tool reads its span items from the file; deleting it would break the tool (change to S2-03's cleanup rule) |
| A separate CI workflow `langfuse-smoke` | The normal smoke test stays fast; Langfuse is tested only when its files change |

Licenses for internal use: Langfuse core MIT, ClickHouse Apache 2.0, PostgreSQL License,
Redis 7.4 RSALv2/SSPL (no fee for internal use), MinIO AGPLv3 (run unmodified). No cost and
no license key.

## Success criteria

- Static tests and the `langfuse-smoke` CI test pass: the trace of a fake-job run is read
  back from Langfuse, also after a Langfuse restart, and the trace check tool shows 5 of 5.
- On the test host: the project owner signs in with Google through the tunnel and sees the
  RTR trace; the dependency ports are not reachable.
