# Test host: HTTPS with an openssl private CA

| Item | Value |
|---|---|
| Date | 2026-10-15 |
| Issues | S1-04 (certificate), S1-06 (front door) in [issues.md](../2026-10-02-batch-monitoring-mvp/issues.md) |
| Risk | R1. Configuration files and a runbook only. No application code changes. |

## Intent

Prakasit wants to test an HTTPS connection to the GCP test host now. The VM has no public
IP, and it must stay private. A public CA cannot sign a private name or an internal IP.
S1-04 asks for a private CA and forbids paid Google Certificate Authority Service.

## Decision

Make a private CA with `openssl`. The nginx that already runs on the VM serves HTTPS.

- Caddy was considered and dropped on 2026-10-15. nginx already runs on the VM, and two
  servers cannot both use port 443. Caddy only as a certificate issuer is also dropped: its
  certificates last about 12 hours, so nginx would need a reload job.
- `openssl` and nginx are already on the VM. Nothing new is installed.
- The root CA lives 730 days. The server certificate lives 90 days and is renewed by
  running the script again. The root is kept, so clients change nothing.
- The client trusts `root.crt`. Verification stays on (S1-03).
- No public DNS, no port 80 server, no new firewall rule. The laptop test uses an IAP SSH
  tunnel on the existing port 22 rule.

## Scope

In: `deploy/test-host/` (CA script, nginx site, runbook). Port 443 sends only
`/api/health` and `/api/batch/runs` to the backend. All other paths return `404` (S1-06).

Out: `/otlp/*` to the Collector (comes with the Collector in S1-06), ports 8443 and 3443
for the staff (Sprint 2), SSO (S3-07), automatic renewal.

## Done when

1. `sudo nginx -t` passes on the VM.
2. On the VM: `curl --cacert root.crt https://<internal-ip>/api/health` returns the backend
   health body, without `-k`.
3. Through an IAP SSH tunnel from a laptop: `curl --cacert root.crt https://localhost:8443/api/health` works.
4. `https://<internal-ip>/api/live/portfolio` returns `404`.
5. From the job VPC: the S1-04 test steps 1 and 2 pass.
