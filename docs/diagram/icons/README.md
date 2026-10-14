# Icons

These are provider icons downloaded for the diagrams, because draw.io's built-in
libraries do not have them. Each one is embedded in a diagram as a data URI, so no diagram
depends on this directory to render. The files are kept so the next version can embed
them again, and so their origin and license are on record.

Each file is an SVG or a PNG that `fetch_icon.py` downloaded and the icon check accepted.
It is kept byte for byte as downloaded, with two exceptions: an SVG ends in exactly one
newline, and a Simple Icons SVG may get its brand colour from `data/simple-icons.json` as
`fill`. A file that fails the icon check is refused, never repaired. Rule and source
order: [`.agents/rules/diagram.md`](../../../.agents/rules/diagram.md#icons).

Each row records:

- **License / terms:** the license name, linked to the page that grants it.
- **Credit:** the attribution the license asks for, or `—`.
- **SHA-256:** the hash of the committed file. The check fails when the file changes
  without its row.

A brand's mark stays its owner's trademark even when the file is CC0 (Simple Icons). Note
any brand guidelines in the License / terms cell.

| File | For | Source | License / terms | Credit | Retrieved | SHA-256 |
|---|---|---|---|---|---|---|
| `clickhouse.svg` | ClickHouse | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/clickhouse.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/clickhouse.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); trademark of ClickHouse, Inc. | — | 2026-10-13 | `fc2d64706cede1c6a3e6bb28f683ed0553b20ddf36be582b83a61e0e8e4784fa` |
| `docker.svg` | Docker | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/docker.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/docker.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); trademark of Docker, Inc. | — | 2026-10-13 | `142d54231e11f6bbec26731a55388fdec65452928b2b2ea5e7916a5c16a0841f` |
| `kubernetes.svg` | Kubernetes | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/kubernetes.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/kubernetes.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); trademark of The Linux Foundation | — | 2026-10-13 | `947241dc140f355d2dcae54d356704baedf67096bb7016e3685a553e762002cb` |
| `minio.svg` | MinIO | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/minio.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/minio.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); [brand guidelines](https://min.io/logo) | — | 2026-10-13 | `3d7c85e6232949185118d76d6412cc7f6de6dd87303643478376e91d63084dcb` |
| `nginx.svg` | nginx | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/nginx.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/nginx.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); [brand guidelines](https://www.nginx.com/press/) | — | 2026-10-13 | `27aa195f5b58c1e82e32e826665c72c6a0b005335e9d589cfd3d85e0793279c2` |
| `opentelemetry.svg` | OpenTelemetry Collector | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/opentelemetry.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/opentelemetry.svg) | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) (Simple Icons 16.35.0 data); [brand guidelines](https://cncf-branding.netlify.app/projects/opentelemetry/) | The OpenTelemetry Authors, CC BY 4.0 | 2026-10-13 | `a0660a9102a9df3124092453ba0243e966c0db9d820403c486dbe70846dee82d` |
| `postgresql.svg` | PostgreSQL | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/postgresql.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/postgresql.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); [trademark policy](https://www.postgresql.org/about/policies/trademarks/) | — | 2026-10-13 | `381038f4454c5e33d47687e0f693da5f0276b1efdf2a77f17b73fafa37e86727` |
| `redis.svg` | Redis | [https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/redis.svg](https://cdn.jsdelivr.net/npm/simple-icons@16.35.0/icons/redis.svg) | [CC0-1.0](https://github.com/simple-icons/simple-icons/blob/16.35.0/LICENSE.md) (Simple Icons 16.35.0); [brand guidelines](https://redis.io/brand-guidelines) | — | 2026-10-13 | `fa656f58d508f7d303c97dbcc107b95b9ec60450535d4c722d388e8ac1f9ffd9` |

Each Simple Icons file has the brand colour from `data/simple-icons.json` as `fill`. A brand's
mark is used only to name the product in a diagram. Not used, because no licence or no icon
was found: Langfuse (its brand page grants no licence), OAuth2 Proxy, Google Workspace.
