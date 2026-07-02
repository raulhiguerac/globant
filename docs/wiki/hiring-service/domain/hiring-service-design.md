---
title: Hiring Service — Design Overview
status: stable
last-verified: 2026-07-01
sources:
  - sources/hiring-service/2026-06-30-hiring-service-design.md
  - sources/hiring-service/2026-06-30-ingestion-wiring-completion.md
  - sources/hiring-service/2026-07-01-gcp-infra-and-cicd.md
related:
  - adr-0001-single-commit-batch-records
  - adr-0002-multipart-vs-presigned-url
  - metrics
  - gcp-infra
---

## Overview

REST API for CSV ingestion of historical hiring data into three tables: `departments`, `jobs`, `employees`. Domain inside the service: `ingestion`.

## Models (`src/app/models/models.py`)

- `IngestionBatch` — UUID PK + `created_at` (server_default). Tracks each ingestion request for audit and traceability.
- `AuditMixin` — `created_at` (server_default=func.now()) + `batch_id` FK → `ingestion_batches`. Applied to all three tables.
- `Departments`, `Jobs`, `Employees` — all columns NOT NULL. IDs come from CSV, not autoincrement.
- `Departments` and `Jobs` defined before `Employees` in the file — Alembic FK dependency order.
- `DateTime(timezone=True)` on all datetime columns.
- Column comments via `sa_column=Column(..., comment="...")`, table comments via `__table_args__` dict.

## Use Case Pattern

Applies to `IngestDepartmentsUseCase` and `IngestJobsUseCase` (employees has different flow — see below):

- `batch_ingestion_id = uuid.uuid4()` generated in UC, passed to both `batch.add` and `bulk_insert`.
- Happy path: `batch.add` + `bulk_insert` → single `commit()` — no orphan batch rows on failure.
- Fallback: row-by-row with savepoints. Commit only if `ok_count > 0`.
- Batch creation failure → `logger.error` + `raise` (critical, cannot continue without batch_id).
- Error translator (`translate_db_error` pattern) lives in the adapter, not the UC.

## IngestEmployeesUseCase

- `stream: BinaryIO` received in `execute()`, not `__init__` — it is operation input, not a dependency.
- Flow: upload stream to storage → `batch.add(pending)` → commit → return `batch_id`.
- Bulk insert + fallback row-by-row lives in the **worker**, not the UC (file can be large, cannot block request).
- Returns `batch_id` immediately; router enqueues `worker.stream_and_process` as `BackgroundTask`.

## Worker — `ProcessEmployeesChunkWorker`

- `run(batch_id, records)` — bulk insert one chunk + savepoint row-by-row fallback. Returns `list[str]` of failed rows.
- `finalize(batch_id)` — `update_status(completed)` + commit + `cache_client.delete(METRICS_CACHE_KEYS)`. Called once after all chunks.
- `stream_and_process(batch_id)` — full background orchestration: re-streams file from storage (key `employees/{batch_id}.csv`), parses, chunks by `EMPLOYEE_CHUNK_SIZE`, loop `run()`, then `finalize()`.
- Must read from storage, not from the request file — the upload in the UC already consumed the stream.
- Cache keys invalidated: `hiring:metrics:hires_by_quarter`, `hiring:metrics:departments_above_mean`.

## Router (`api/routes/ingestion.py`)

- `POST /ingest/departments` + `POST /ingest/jobs` — sync, `200 IngestionResponse`.
- `POST /ingest/employees` — async, `202 AcceptedResponse(batch_id)` + `BackgroundTask`.
- Parsers live in `helpers/csv_parser.py`, not in the router.
- `_MAX_ROWS = 1000` constant in router (API contract, not runtime config).

## DI Wiring (`api/deps/`)

- `deps/shared.py` — `@lru_cache` singletons for cache and storage. Public getters have no `Depends` params to avoid the lru_cache + Depends incompatibility.
- `deps/ingestion.py` — per-request: `get_uow(session=Depends(get_session))` + UC/worker providers.

## DB Error Translation (`helpers/db_error_translator.py`)

- `OperationalError` → `IngestionDbUnavailableError` (503).
- `IntegrityError` + PK (`departments_pkey`, `jobs_pkey`, `employees_pkey`) → `RecordConflictError` (409).
- `IntegrityError` + FK (`employees_department_id_fkey`, `employees_job_id_fkey`) → `RecordForeignKeyError` (422).
- In bulk except: `except OperationalError` → translate + raise; `except Exception` → rollback + fall to row-by-row.
- In row-by-row except: `except OperationalError` → translate + raise; `except Exception` → rollback_to_savepoint + append to errors list.
- `IntegrityError` in bulk falls to row-by-row — allows rescuing valid rows from the same batch.

## Schemas

- `DepartmentRecord`, `JobRecord` — Pydantic models matching CSV columns exactly.
- `IngestionResponse(created_count: int, errors: list[str])` — shared across all 3 endpoints.
- Failed row format in errors list: `"id:name"`.

## Validation

- Max 1000 rows per request per endpoint.
- Parser dep validates `len(records) <= 1000` and returns 400 if exceeded.

## Infrastructure

- `pyrightconfig.json` at service root with `extraPaths: ["src"]` — required for Pylance to resolve `app.*` imports from `src/app/`.

## Pending

- [x] `GET /ingest/employees/{batch_id}/status` — polling endpoint to check `IngestionBatch.status`
- [x] Alembic migration
- [x] Section 2 OLAP endpoints (DuckDB + Redis cache) — see [[metrics]]
- [x] docker-compose, Dockerfile (Python 3.11-slim)
- [x] Unit tests — 49 passing (UCs, endpoints, helpers)
- [x] Terraform + GH Actions — see [[gcp-infra]]
- [ ] README (explicitly required by challenge)
- [ ] Cloud Run deploy validated end-to-end

## Claims

- `IngestionBatch` must be persisted in the same transaction as the records — FK constraint enforces this.
- `server_default=func.now()` is used (not Python-side `default_factory`) for all `created_at` columns.
- IDs on all three tables are provided by CSV — no autoincrement.
- Error translator lives in `services/ingestion/helpers/`, not in the UC or adapter.
- Max batch size is 1000 rows per request.
- `stream_and_process` reads the file from storage, not from the original request object.
- `@lru_cache` singletons must not receive `Depends()` params — call the cached function directly inside the getter.
