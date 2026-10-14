# Dashboard image (S2-07): the unchanged control-tower UI, built once, served as files.
# Build from the repository root:  docker build -f deploy/dashboard/Dockerfile .
# Stage "build" is Debian (glibc), not Alpine: the workspace keeps only the glibc Linux
# binaries of rollup, lightningcss and tailwind oxide (pnpm-workspace.yaml overrides).
FROM node:24.21.0-bookworm-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.15.1 --activate
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml tsconfig.base.json tsconfig.json ./
COPY artifacts/control-tower/package.json artifacts/control-tower/
COPY artifacts/api-server/package.json artifacts/api-server/
COPY scripts/package.json scripts/
RUN pnpm install --frozen-lockfile --filter @workspace/control-tower...
COPY artifacts/control-tower artifacts/control-tower
COPY scripts/check-strict-live-bundle.mjs scripts/
ENV PORT=8090 BASE_PATH=/ CONTROL_TOWER_MODE=live NODE_ENV=production
RUN pnpm run build:live && pnpm run check:strict-live

# Dashboard file server: hands out dist/ only. Non-root, port 8090, inside Docker only;
# the front door (deploy/nginx/conf.d/dashboard.conf) sends "/" here.
FROM nginxinc/nginx-unprivileged:1.28.0-alpine
COPY deploy/dashboard/file-server.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/artifacts/control-tower/dist/public /usr/share/nginx/html
EXPOSE 8090
