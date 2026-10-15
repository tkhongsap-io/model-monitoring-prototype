# Test host HTTPS with a private CA

This folder sets up HTTPS on the GCP test host (S1-04, S1-06 in
[issues.md](../../changes/2026-10-02-batch-monitoring-mvp/issues.md)). The VM has no public
IP. A public CA cannot sign a private name or an internal IP, so we make a private CA with
`openssl`. The nginx that already runs on the VM serves HTTPS on port 443.

| File | What it does |
|---|---|
| `make-private-ca.sh` | Makes the root CA once. Issues the nginx server certificate. Run it again to renew. |
| `nginx-test-host.conf` | The nginx site on port 443. Sends `/api/health` and `/api/batch/runs` to the backend. All other paths return `404`. |

Clients trust `root.crt` and keep certificate verification on (S1-03). Never use `curl -k`
or `verify=False`.

## Values

| Value | Default | Where |
|---|---|---|
| Root CA folder | `/etc/monitor-test-ca` | `root.key` (secret, mode 600) and `root.crt` (public) |
| Server certificate | `/etc/nginx/tls/test-host` | `server.crt`, `server.key` |
| Root CA life | 730 days | `ROOT_DAYS` |
| Server certificate life | 90 days | `SERVER_DAYS` |
| Backend | `127.0.0.1:8000` | `proxy_pass` in `nginx-test-host.conf` |

## Set up on the VM

1. Connect to the VM: `gcloud compute ssh <vm> --tunnel-through-iap`.
2. Copy this folder to the VM, for example with `gcloud compute scp --tunnel-through-iap`.
3. Find the internal IP: `hostname -I`.
4. Make sure that no other nginx site uses port 443: `sudo grep -rn "listen.*443" /etc/nginx/`.
5. If another site uses port 443, merge the `location` blocks into that site instead of step 8.
6. Make the CA and the server certificate: `sudo bash make-private-ca.sh <internal-ip>`.
7. If the network team gave a private DNS name, add it: `sudo bash make-private-ca.sh <internal-ip> <dns-name>`.
8. Install the site: `sudo cp nginx-test-host.conf /etc/nginx/sites-available/monitor-test-host`.
9. Enable the site: `sudo ln -s /etc/nginx/sites-available/monitor-test-host /etc/nginx/sites-enabled/`.
10. Test the configuration: `sudo nginx -t`.
11. If the test passes, reload nginx: `sudo systemctl reload nginx`.

CAUTION: Do not copy `root.key` off the VM. Anybody with this key can make certificates
that the clients trust. If you lose it, make a new root and give the new `root.crt` to every
client.

## Test the connection

Run these tests on the VM first:

1. `curl --cacert /etc/monitor-test-ca/root.crt https://<internal-ip>/api/health` returns the backend health body.
2. `curl --cacert /etc/monitor-test-ca/root.crt -o /dev/null -w "%{http_code}\n" https://<internal-ip>/api/live/portfolio` returns `404`.
3. `curl https://<internal-ip>/api/health` without `--cacert` fails with a certificate error. This is correct.
4. `openssl s_client -connect <internal-ip>:443 -CAfile /etc/monitor-test-ca/root.crt </dev/null` shows `Verify return code: 0 (ok)`.

Then test from a laptop through an IAP SSH tunnel. No new firewall rule is necessary:

1. Get the root certificate: `gcloud compute scp --tunnel-through-iap <vm>:/etc/monitor-test-ca/root.crt .`
2. Open the tunnel and keep it open: `gcloud compute ssh <vm> --tunnel-through-iap -- -N -L 8443:127.0.0.1:443`
3. In a second terminal: `curl --cacert root.crt https://localhost:8443/api/health`.
4. In Python: `requests.get("https://localhost:8443/api/health", verify="root.crt")`.

The certificate contains `localhost` and `127.0.0.1` for this tunnel test. On Windows, the
built-in `curl.exe` uses Schannel, which can ignore `--cacert`. If step 3 fails on Windows,
use the `curl` of Git Bash or WSL.

From the job VPC (S1-03, S1-04), use `https://<internal-ip>/...` or the private DNS name.
The job trusts `root.crt`.

## Renew the server certificate

The server certificate expires after 90 days. The root CA is kept, so clients change
nothing.

1. Show the end date: `sudo openssl x509 -in /etc/nginx/tls/test-host/server.crt -noout -enddate`.
2. If fewer than 14 days remain, run `make-private-ca.sh` again with the same arguments.
3. Reload nginx: `sudo nginx -t && sudo systemctl reload nginx`.
