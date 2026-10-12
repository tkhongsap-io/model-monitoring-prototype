# Self-hosted Langfuse (S2-03)

This Compose project runs web, worker, PostgreSQL, ClickHouse, Redis and MinIO.
No service publishes a port; only `langfuse-web` joins `edge`. Its Redis is not
shared: another app that needs Redis deploys its own.

Licenses for internal use: Langfuse core MIT, ClickHouse Apache 2.0, PostgreSQL License,
Redis 7.4 RSALv2/SSPL (no fee for internal use), MinIO AGPLv3 (run unmodified).
No cost and no license key.

Create the shared network once:

```sh
docker network create edge
```

From this folder, start the local project:

```sh
docker compose -f compose.yaml -f compose.local.yaml up -d --wait
```

Start nginx with its local overlay, then open http://127.0.0.1:3000.
Sign in as `local@example.com` with the local password value in `local.env`.
These are local test values only.

Test-host steps are in [TESTHOST.md](../compose/TESTHOST.md), ?Langfuse (S2-03)?.
