---
title: Hiring Service — Ingestion Wiring Completion
captured-from: conversation
captured-on: 2026-06-30
participants: [raul, claude]
---

## Context
Second session completing the hiring-service ingestion domain: worker finalize pattern, DI wiring, router, CSV parsers, and db error translation.

## Key conclusions

### Worker — `ProcessEmployeesChunkWorker`
- `run(batch_id, records)` processes one chunk — bulk insert + savepoint row-by-row fallback
- `finalize(batch_id)` is a separate method: `update_status(completed)` + commit + cache invalidation
- `stream_and_process(batch_id)` orchestrates the full background flow: stream from storage → parse → chunk loop → finalize
- `finalize` is intentionally separate from `run` — `completed` and cache invalidation happen once after ALL chunks, not per chunk
- Cache keys to invalidate: `hiring:metrics:hires_by_quarter`, `hiring:metrics:departments_above_mean` (Section 2 endpoints)

### `stream_and_process` reads from storage, not from the request file
- `IngestEmployeesUseCase.execute()` uploads `file.file` stream to storage — stream is consumed after upload
- Background task must re-stream from storage via `worker.storage.stream_file()` using `employees/{batch_id}.csv` key

### DI wiring split (`api/deps/`)
- `deps/shared.py` — `@lru_cache` singletons: `_cache_client()` and `_storage()`; public `get_cache_client()` / `get_storage()` without Depends params (lru_cache + Depends don't mix)
- `deps/ingestion.py` — per-request: `get_uow(session=Depends(get_session))` + UC/worker providers that compose both

### Router slim pattern
- Parsers extracted to `services/ingestion/helpers/csv_parser.py` — `parse_departments`, `parse_jobs`, `parse_employees`
- `stream_and_process` encapsulated in worker — router just calls `background_tasks.add_task(worker.stream_and_process, batch_id=batch_id)`
- `AcceptedResponse(batch_id: uuid.UUID)` lives in `ingestion_response.py`
- `_MAX_ROWS = 1000` constant in router (API concern, not runtime config)

### db_error_translator (`services/ingestion/helpers/db_error_translator.py`)
- `OperationalError` → `IngestionDbUnavailableError` (503)
- `IntegrityError` + PK constraint (`departments_pkey`, `jobs_pkey`, `employees_pkey`) → `RecordConflictError` (409)
- `IntegrityError` + FK constraint (`employees_department_id_fkey`, `employees_job_id_fkey`) → `RecordForeignKeyError` (422)
- Constraint names parsed from Postgres error string via regex

### Error handling strategy in UCs and worker
- **Bulk except**: `except OperationalError` → translate + raise immediately (DB down = no point falling to row-by-row); `except Exception` → rollback + fall to row-by-row
- **Row-by-row except**: `except OperationalError` → translate + raise; `except Exception` → rollback_to_savepoint + append to errors list
- `IntegrityError` (duplicate PK, FK violation) in bulk → falls to row-by-row to rescue valid rows

## Open questions
- None for Section 1 architecture

## Next steps
- `GET /ingest/employees/{batch_id}/status` — polling endpoint (pending → completed)
- Alembic migration
- Section 2 OLAP endpoints (DuckDB + Redis cache-aside)
- docker-compose + Dockerfile
- Tests
- Terraform + GH Actions
