---
title: Hiring Service — Design Decisions
captured-from: conversation
captured-on: 2026-06-30
participants: [raul, claude]
---

## Context
Globant Data Engineering challenge: REST API for CSV ingestion into departments, jobs, and employees tables. The user is implementing everything; Claude advises on design decisions only.

## Key conclusions

### Naming
- Service folder: `hiring-service` (intentional domain name, not `ingestion-service` which is generic)
- Domain inside the service: `ingestion`

### Models (`src/app/models/models.py`)
- Three tables: `Departments`, `Jobs`, `Employees` — all NOT NULL, IDs come from CSV (not autoincrement)
- `AuditMixin`: `created_at` (server_default=func.now()) + `batch_id` FK → `ingestion_batches`
- `IngestionBatch`: UUID PK + `created_at` server_default — tracks each CSV ingestion request
- Column comments via `sa_column=Column(..., comment="...")`, table comments via `__table_args__` dict
- `Departments` and `Jobs` defined before `Employees` — FK dependency order for Alembic
- `DateTime(timezone=True)` on all datetime columns
- `server_default=func.now()` preferred over `lambda: datetime.now()` — DB-side, not app-side

### Use Case pattern (`IngestDepartmentsUseCase`, `IngestJobsUseCase`)
- Single commit covers batch creation + records — no orphan `ingestion_batch` rows on failure
- Happy path: `batch.add` + `bulk_insert` → single `commit()`
- Fallback: row-by-row with savepoints, commit only if `ok_count > 0`
- `batch_ingestion_id = uuid.uuid4()` generated in UC — passed to both `batch.add` and `bulk_insert`
- Error log on batch creation failure is `logger.error` + `raise` (critical, cannot continue)
- Error translator (translate_db_error pattern) lives in the adapter, not the UC

### IngestEmployeesUseCase
- Has `stream` in `__init__` — receives the file stream to upload to MinIO/GCS
- Flow: upload stream to storage → create batch with file key → delegate to worker
- Bulk insert + fallback lives in the worker, not the UC (file can be large, can't block request)

### System design rationale
- No front-end: multipart upload directly to API (`POST /v1/ingest`)
- Optimal production architecture (defensible in interview): presigned URL → client PUTs directly to storage → API never pays bandwidth
- Worker (Celery/ARQ) processes file in chunks (100-200 MB) → bulk insert
- `batch_id` is the correlation ID for tracing chunks

### Validation
- Max 1000 rows per request per endpoint — parser validates `len(records) <= 1000`, returns 400 if exceeded

### Schemas
- `DepartmentRecord`, `JobRecord` — Pydantic models matching CSV columns
- `IngestionResponse(created_count, errors: list[str])` — shared across all 3 endpoints
- Errors list format: `"id:name"` for failed rows

### Infrastructure
- `pyrightconfig.json` with `extraPaths: ["src"]` — required for Pylance to resolve `app.*` imports from `src/app/`

## Open questions
- `IngestEmployeesUseCase` full implementation pending (stream upload + worker delegation)
- Worker implementation not started

## Next steps
- Implement adapters + UoW
- Implement CSV parser dep
- Wire routes
- Alembic migration
