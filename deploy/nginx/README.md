# nginx front door (S1-06)

One nginx for all apps on a host. Each app has one file in `conf.d/`. The apps join the
external Docker network `edge` with their own aliases (for example `model-monitor-backend`),
so two apps with a service named `backend` cannot collide. nginx finds the apps at request
time: if an app is down, nginx still starts, and only that app gives `502`.

There is no DNS name on the test host, so each app has its own port (one `server` block for
each port): 80 = model-monitor job paths (`conf.d/model-monitor.conf`). Sprint 2 adds the
dashboard and Langfuse.

## Start

Make the network once:

```bash
docker network create edge
```

From this folder (on the test host, `/opt/nginx`, with `sudo`):

```bash
docker compose -f compose.yaml -f compose.local.yaml up -d --wait
```

Use `compose.testhost.yaml` instead of `compose.local.yaml` on the test host.

## Add an app

1. Add `conf.d/<app>.conf` with a `server` block on a new port, and publish the port in the host file.
2. Check the configuration:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec nginx nginx -t
```

3. Reload without a restart of the other apps:

```bash
docker compose -f compose.yaml -f compose.local.yaml exec nginx nginx -s reload
```

A new published port needs `up -d` instead of a reload.
