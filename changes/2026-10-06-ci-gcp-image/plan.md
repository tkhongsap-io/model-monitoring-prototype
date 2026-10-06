# CI: build the backend image and store it in GCP Artifact Registry

## Outcome

Each merge to `dev` that changes `backend/` builds one backend image and pushes it to
Artifact Registry. The GCP test host VM (S1-04 in
[issues.md](../2026-10-02-batch-monitoring-mvp/issues.md)) pulls that image with Docker
Compose.

## Done when

- A merge to `dev` starts `.github/workflows/build-image.yml`, and the run is green.
- The image is at
  `asia-southeast3-docker.pkg.dev/gcp-noexp-wl-nprd-automationsb/model-monitoring/dev/backend:<run_number>`.
- The image label `org.opencontainers.image.revision` and the `GIT_SHA` environment
  variable hold the commit SHA.
- No service-account key exists. GitHub signs in with Workload Identity Federation.

## Decisions

| Decision | Reason |
|---|---|
| Artifact Registry, Docker format, Standard mode, region `asia-southeast3` | Same project and region as the test host. The VM pulls without cross-project permissions. |
| Workload Identity Federation, provider limited to `tkhongsap-io/model-monitoring-prototype` | No long-lived key to store or rotate |
| One package per environment: `dev/backend`, later `uat/backend` and `main/backend` | Each environment has its own keep count. Many dev builds cannot remove the image that uat or main runs. |
| Tag is the GitHub run number, for example `57` | Easy to read. The commit SHA stays in the image label. Immutable tags are on. |
| Cleanup: keep the 5 newest `dev` versions, and delete versions older than 30 days | Limits storage cost. The keep policy wins over the delete policy. |
| Backend only. The dashboard SPA is not in the image. | The batch MVP needs `/api/batch/runs` and `/api/health` first. A later slice can add a frontend stage. |
| Migrations run at startup through `db.engine()` | Same as the existing rule: the Python backend migrates at startup |

## Cost and dependencies

- Artifact Registry storage is a paid GCP service. The cleanup policy keeps it small.
  Vulnerability scanning stays off, because it is a separate paid service.
- New GitHub Actions: `google-github-actions/auth@v2`, `google-github-actions/setup-gcloud@v2`.
- No new pip or npm packages. The base image is `python:3.12-slim` with `libgomp1`.

## GCP and GitHub setup (done by hand, not in the repository)

1. The Artifact Registry repository `model-monitoring`, with immutable tags and the two
   cleanup policies (dry run first).
2. The service account `gh-ci-pusher` with `roles/artifactregistry.writer` on that
   repository only.
3. The Workload Identity pool `github` and the provider `github-oidc`, with the condition
   `assertion.repository=='tkhongsap-io/model-monitoring-prototype'`.
4. The GitHub repository variables `GCP_PROJECT_ID`, `GCP_REGION`, `GAR_REPO`,
   `WIF_PROVIDER` and `WIF_SERVICE_ACCOUNT`.

## Slices

1. This PR: `backend/Dockerfile`, `backend/.dockerignore`, `.github/workflows/build-image.yml`.
2. Later: the VM pulls the image (VM service account gets `roles/artifactregistry.reader`,
   Private Google Access on the subnet).
3. Later: `uat` and `main` builds, maybe by promoting the same image instead of a rebuild.

## Rollback

Revert the PR. Images already in the registry stay until the cleanup policy removes them.
