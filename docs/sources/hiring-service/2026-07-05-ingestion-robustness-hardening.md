---
title: Ingestion pipeline robustness hardening (post-review fixes)
captured-from: conversation
captured-on: 2026-07-05
participants: [raul, claude]
---

## Context

A self-review of the ingestion domain (branch `feat/section-1-ingestion`) flagged five operational-robustness gaps and a handful of minor issues. This session closed the highest-impact ones for a take-home assessment scope, explicitly rejecting a real task queue as overkill.

## Key conclusions

- Added `IngestionBatchStatus.failed` to the enum (`models.py`) plus an Alembic migration (`1099b8b292cc`) running `ALTER TYPE ingestion_batch_status ADD VALUE IF NOT EXISTS 'failed'` — validated end-to-end against a local Postgres 17 container.
- `ProcessEmployeesChunkWorker.stream_and_process` now wraps its whole body in a catch-all that marks the batch `failed` and re-raises on any exception (storage, DB, parse, or finalize failures) — closes the "batch stuck in `pending` forever" gap for in-process crashes.
- `GetBatchStatusUseCase` adds a `BATCH_TIMEOUT_SECONDS` (default 600) heuristic: a `pending` batch older than the threshold is reported (and persisted) as `failed` on the next poll — covers the case where the worker process is killed outright and never runs its own except block. 600s is deliberately generous since batches are capped at 1000 rows (`batch_guard._MAX_ROWS`).
- Root cause of the "worker reuses request-scoped DB session" fragility: FastAPI 0.106+ closes `yield`-dependencies before running `BackgroundTasks`. Fix wasn't "give the worker its own `Depends`" (same problem, wrong layer) — it's that the background task must open its own `Session(engine)` inside its own execution window. Implemented as `run_process_employees_chunk` in `app/api/deps/ingestion.py`; the route's `Depends` now returns that function reference, not a pre-built worker, so `dependency_overrides` still works in tests.
- Worker was refactored to be pure orchestration: business logic extracted into `app/workers/helpers/` (`batch_status.py`, `employee_writer.py`, `storage_reader.py`, `chunking.py`), each independently unit-tested.
- `DuckDbClient.query()` now catches failures and does one reconnect+retry (re-running `INSTALL`/`LOAD`/`ATTACH`) before propagating — fixes the permanent-503-until-restart gap when Postgres restarts after the `@lru_cache`'d DuckDB connection was established.
- `CacheClient.delete()` now retries with a 15s/30s backoff before giving up and logging — narrows (doesn't eliminate) the stale-metrics-cache gap. Clarified during review: a fully-down Redis doesn't cause staleness (reads degrade to cache-miss → live DuckDB query), only an isolated transient failure of the `delete` call while reads still succeed does. The 8h TTL remains the hard ceiling on staleness if retries exhaust.
- Fixed a real (not just robustness) bug: `SqlUnitOfWork.__init__` didn't initialize `self._savepoint`, so calling `rollback_to_savepoint()` before any `begin_nested()` raised `AttributeError`. Now initialized to `None` — safe no-op.
- `stream_and_process` still buffers the whole CSV in memory before parsing (`download_file` in `storage_reader.py` does `chunks.append` + `b"".join`) despite the name — deliberately not fixed, to avoid handling records split across chunk boundaries. The GCS-level `stream_file` read (8KB reads via `blob.open("rb")`) is genuinely lazy; the buffering happens one layer up, in the worker's own consumption of that stream. Acceptable for the ~2MB challenge CSV.

## Open questions

- Whether to document the streaming/staleness/queue trade-offs explicitly in the README (agreed conceptually, not yet written).

## Next steps

- Write the README section documenting known limitations: fake full-parse "streaming", cache-invalidation retry ceiling (8h TTL), and why no real job queue was introduced.
- Still open, not addressed this session: `validate_batch` counts only valid rows (a 1500-row CSV with 600 invalid rows bypasses the 1000-row cap), department/job parse errors aren't persisted to `batch.errors` (asymmetric with employees), GCS sync generator blocks the event loop per 8KB read, `tests/integration/` is empty, no auth on endpoints, GCS/MinIO swap is done via commented-out import instead of an env var.
