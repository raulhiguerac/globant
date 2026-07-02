---
title: README, Architecture Diagram, and Project Finalization
captured-from: conversation
captured-on: 2026-07-01
participants: [raul, claude]
---

## Context
Final cleanup pass on the hiring-service challenge: README, draw.io architecture diagram, .dockerignore, .env.example, and a cache invalidation scope decision.

## Key conclusions

### README
- Repo root `README.md` (not inside `hiring-service/`) starts with `![Architecture](assets/architecture.jpg)`.
- Dev Playground uses devcontainer — no `docker compose up` needed. Steps: open in container → `cd hiring-service` → `uv run alembic upgrade head` → `uv run fastapi dev src/app/main.py --host 0.0.0.0`.
- Design decisions documented: presigned URLs rejected (no front-end client to orchestrate 2-step flow), BackgroundTask over Celery (no broker needed for bounded concurrency), DuckDB via `pg` extension (no ETL, 8h Redis TTL mitigates OLTP load), bulk insert + savepoint fallback (orphan-safe batches).
- Terraform section notes: kept manual intentionally to retain full `destroy` and lifecycle control — not wired to CD pipeline.
- Database migrations: manual via Cloud SQL Auth Proxy using `{project}:{region}:{instance}` placeholder (no real credentials in README).
- No real GCP project IDs anywhere — all `{placeholders}`.

### Architecture diagram (draw.io)
- File: `docs/architecture.drawio` (XML format).
- Color-coded edges: green=REST API calls, red=Redis cache, orange=GCS file flow, blue=DB operations, yellow dashed=worker trigger, purple dashed=secrets config.
- No nested groups — caused page-fit whitespace issues; all nodes parented to a single outer container with adjusted coordinates.
- White background (`background="#ffffff"`), black labels, legend block with color key.

### Cache invalidation scope
- `departments` and `jobs` ingest endpoints do **not** invalidate metrics cache.
- Rationale: both metrics queries (`hires-by-quarter`, `departments-above-mean`) read `hired_employees` via JOIN — department and job data is reference-only. The employee ingest worker already invalidates on finalize; no second invalidation path needed.

### Other file changes
- `.dockerignore`: added `tests/` and `*.md` (exclude test suite and docs from image).
- `.gitignore`: added `terraform/terraform.tfstate.*.backup` pattern (timestamped backups like `terraform.tfstate.1782950581.backup` were not covered).
- `.env.example`: created at repo root with dummy values for `DATABASE_URL`, `REDIS_URL`, `STORAGE_BUCKET`, `GCS_PROJECT`, optional `GOOGLE_APPLICATION_CREDENTIALS` and MinIO vars commented out.

## Open questions
- None — project is finalized pending Cloud Run deploy validation.

## Next steps
- Commit all changes.
- Uncomment Cloud Run module and validate full end-to-end deploy when ready.
