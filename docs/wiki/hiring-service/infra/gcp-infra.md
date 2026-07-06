---
title: Hiring Service — GCP Infrastructure & CI/CD
status: draft
last-verified: 2026-07-05
sources:
  - sources/hiring-service/2026-07-01-gcp-infra-and-cicd.md
  - sources/hiring-service/2026-07-01-readme-diagram-finalization.md
  - sources/hiring-service/2026-07-05-integration-tests-and-terraform-hardening.md
related:
  - hiring-service-design
  - testing
---

## Overview

Terraform-based GCP infrastructure for hiring-service. Modules are applied sequentially to avoid dependency errors. The Cloud Run module is enabled (`terraform validate` passes); the deploy itself has not yet been validated end-to-end against GCP.

## Terraform Modules (`terraform/`)

Sequential dependency chain:

```
APIs → time_sleep (30s) → IAM + secret_manager → gcs + cloud_sql → cloud_run
```

| Module | Resource |
|---|---|
| `google_project_service` | API enablement (split — see below) |
| `secret_manager` | `DATABASE_URL` + `REDIS_URL` secrets + SA accessor IAM |
| `gcs` | GCS bucket + SA `objectAdmin` IAM |
| `cloud_sql` | Postgres 15, `db-f1-micro`, public IP, instance name `hiring-db` |
| `cloud_run` | Cloud Run v2 + Cloud SQL volume + secrets as env vars + invoker IAM from `var.invoker_members` |

## Cloud Run image & invokers

- `var.image` must be passed on every apply as `raulhiguera/globant:<git-sha>` (Docker Hub, public repo). CD never publishes `:latest` nor pushes to GCR — a stale `gcr.io/...:latest` value fails to pull.
- Invoker access is `for_each` over `var.invoker_members` (required, no default) — exposing the service (`["allUsers"]`) is an explicit tfvars decision, not a hidden module default.
- For zero internet exposure (discussed, not implemented — assessment scope): `ingress = INGRESS_TRAFFIC_INTERNAL_ONLY` (IAM alone still leaves the URL reachable), Serverless VPC Access connector, Cloud SQL `ipv4_enabled = false`, Memorystore instead of external Redis Cloud.

## API Enablement

Two separate `google_project_service` resources due to `storage.googleapis.com` depending on `cloudapis.googleapis.com`:

```hcl
# disable_on_destroy = true
apis: secretmanager.googleapis.com, sqladmin.googleapis.com, run.googleapis.com

# disable_on_destroy = false (has core GCP dependency, cannot be disabled)
apis_no_disable: storage.googleapis.com
```

A `time_sleep` resource (30s) sits between API activation and resource creation to avoid race-condition 403s.

## Storage — GCS

- `StorageClient` injected in `deps/shared.py` (GCS by default)
- For local dev with MinIO: swap import in `deps/shared.py` (comment in file)
- Auth: ADC — automatic in Cloud Run; `gcloud auth application-default login` locally
- Env vars: `GCS_PROJECT` (required by client), `STORAGE_BUCKET` (passed per call)

## DATABASE_URL format (Cloud SQL via proxy)

```
postgresql://admin:{password}@/app_db?host=/cloudsql/{project}:{region}:hiring-db
```

## .gitignore entries

```
terraform/terraform.tfvars
terraform/.terraform/
terraform/.terraform.lock.hcl
terraform/terraform.tfstate
terraform/terraform.tfstate.backup
terraform/terraform.tfstate.*.backup   # timestamped backups (e.g. *.1782950581.backup)
**/*.csv
```

## .dockerignore entries

`tests/` and `*.md` are excluded from the Docker image (no test suite or docs in prod).

## .env.example

File at repo root. Dummy values only — never commit real credentials. Variables documented:

```
DATABASE_URL=postgresql://admin:password@db:5432/app_db
REDIS_URL=redis://redis:6379/0
STORAGE_BUCKET=hiring
GCS_PROJECT={your-gcp-project-id}
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
# MINIO_URL=http://minio-hiring:9000
# ACCESS_KEY=minioadmin
# SECRET_KEY=minioadmin
```

## Architecture diagram

`docs/architecture.drawio` — color-coded edges (green=REST, red=Redis, orange=GCS, blue=DB, yellow dashed=worker trigger, purple dashed=secrets). White background, black labels, legend block. No nested groups.

## GitHub Actions

### CI (`.github/workflows/ci.yml`)
- Trigger: `pull_request` types `[opened, synchronize]` → `main`
- `working-directory: hiring-service`, `PYTHONPATH: hiring-service/src`
- Steps: checkout → `uv sync --extra dev` → `uv run pytest tests/unit` → `uv run pytest tests/integration` (`timeout-minutes: 10` so a hung testcontainers/Ryuk fails fast instead of eating the 6h default)
- Integration tests use testcontainers against the runner's Docker daemon — no `services:` block needed. See [[testing]].

### CD (`.github/workflows/cd.yml`)
- Trigger: `push` → `main`
- Steps: checkout → Docker Hub login → QEMU → Buildx → build+push
- Image: `raulhiguera/globant:{github.sha}` with registry cache tag `raulhiguera/globant:cache`
- `context: hiring-service` (Dockerfile lives there, not at repo root)
- Deliberately does **not** re-run tests: branch protection + CI on PR already gate `main`; duplicating them here only adds deploy latency.

## Claims

- `time_sleep` `create_duration = "30s"` is required — GCP API propagation is async and causes 403 without it.
- `storage.googleapis.com` cannot use `disable_on_destroy = true` — it has a dependency on `cloudapis.googleapis.com`.
- `working-directory` in GitHub Actions only applies to `run` steps, not `uses` steps — `context:` must be explicit in `build-push-action`.
- `PYTHONPATH: hiring-service/src` is set at job level so pytest can resolve `app.*` imports.
- `var.invoker_members` has no default — `terraform plan` fails until the tfvars decides who can invoke.
- CD publishes only SHA-tagged images to Docker Hub; there is no `:latest` tag anywhere.
