---
title: GCP Infrastructure, Terraform, and GitHub Actions CI/CD
captured-from: conversation
captured-on: 2026-07-01
participants: [raul, claude]
---

## Context
Completed the GCP infrastructure setup for hiring-service using Terraform and wired GitHub Actions for CI/CD. GCS replaced MinIO as the cloud storage integration.

## Key conclusions
- **Storage**: GCS `StorageClient` injected in `deps/shared.py`; swap import to MinIO for local dev. Only env vars needed: `GCS_PROJECT` + `STORAGE_BUCKET`. Auth via ADC (automatic in Cloud Run, `gcloud auth application-default login` locally).
- **Terraform modules**: `secret_manager` → `gcs` + `cloud_sql` → `cloud_run` (sequential `depends_on`). `cloud_run` currently commented out pending deploy validation.
- **API enablement**: Split into two `google_project_service` resources — `secretmanager`, `sqladmin`, `run` with `disable_on_destroy = true`; `storage` with `disable_on_destroy = false` (has core dependency, cannot be disabled).
- **API propagation**: `time_sleep` resource (30s) between API enablement and resource creation to avoid race condition 403s.
- **Terraform state**: `.gitignore` covers `terraform.tfvars`, `.terraform/`, `.terraform.lock.hcl`, `terraform.tfstate`, `terraform.tfstate.backup`, `**/*.csv`.
- **CI** (`.github/workflows/ci.yml`): triggers on `pull_request` types `[opened, synchronize]` to `main`; runs `uv sync` + `uv run pytest` with `working-directory: hiring-service` and `PYTHONPATH: hiring-service/src`.
- **CD** (`.github/workflows/cd.yml`): triggers on `push` to `main`; Docker login → QEMU → Buildx → build+push to `raulhiguera/globant:{github.sha}` with registry cache (`raulhiguera/globant:cache`).
- **Tag strategy**: `github.sha` for traceability; branch protection rules enforce CI passes before merge.

## Open questions
- Cloud Run deploy not yet validated end-to-end (module commented out).
- `redis_url` in tfvars had redis-cli format — confirm it's a proper connection URL before applying.

## Next steps
- Write README (explicitly required by the Globant challenge).
- Uncomment Cloud Run module and validate full deploy.
