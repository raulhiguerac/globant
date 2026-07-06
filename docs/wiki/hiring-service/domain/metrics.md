---
title: Hiring Service — Metrics Domain (Section 2)
status: stable
last-verified: 2026-07-05
sources:
  - sources/hiring-service/2026-07-01-gcp-infra-and-cicd.md
  - sources/hiring-service/2026-07-01-readme-diagram-finalization.md
  - sources/hiring-service/2026-07-05-ingestion-robustness-hardening.md
related:
  - hiring-service-design
  - adr-0003-background-worker-session-and-failure-detection
---

## Overview

Two OLAP endpoints backed by DuckDB querying Postgres via the `pg` extension. Both use Redis cache-aside with an 8-hour TTL. Cache is invalidated by `ProcessEmployeesChunkWorker.finalize()` after each successful ingestion.

## Endpoints (`api/routes/metrics.py`)

| Method | Path | UC |
|---|---|---|
| `GET` | `/v1/metrics/hires-by-quarter` | `HiresByQuarterUseCase` |
| `GET` | `/v1/metrics/departments-above-mean` | `DepartmentsAboveMeanUseCase` |

## Use Case Pattern

Both UCs follow the same cache-aside pattern:

```python
result = await cache_client.get_json(key=cache_key)
if result is not None:
    return result

result = await run_in_threadpool(self.db.query, sql=sql)  # DuckDB is sync

await cache_client.set_json(key=cache_key, value=result, ttl=settings.METRICS_CACHE_TTL)
return result
```

- `run_in_threadpool` wraps the sync DuckDB call — never block the async event loop.
- On exception: `logger.error` + raise `AnalyticsUnavailableError` (503).

## Cache Keys & TTL (`core/config/settings.py`)

```python
CACHE_KEY_HIRES_BY_QUARTER       = "hiring:metrics:hires_by_quarter"
CACHE_KEY_DEPARTMENTS_ABOVE_MEAN = "hiring:metrics:departments_above_mean"
METRICS_CACHE_TTL                = 3600 * 8   # 8 hours
```

## SQL — Hires by Quarter

Template: `services/metrics/helpers/hires_by_quarter.sql.jinja`

Renders four `SUM(CASE WHEN EXTRACT(MONTH ...) BETWEEN x AND y THEN 1 ELSE 0 END)` columns (Q1–Q4) for 2021. Groups by `department` + `job`, ordered alphabetically.

DuckDB syntax: tables referenced as `pg.public.employees`, `pg.public.departments`, `pg.public.jobs`.

## SQL — Departments Above Mean

File: `services/metrics/helpers/departments_above_mean.sql`

CTE pattern: `dept_hires` (count per department for 2021) → `mean_hires` (AVG) → filter `hired > mean`. Returns `id`, `department`, `hired`, ordered by `hired DESC`.

## Adapters

- **Port**: `AnalyticsDb` (Protocol) with `query(sql: str) -> list[dict]`
- **Adapter**: `DuckDbAdapter` wraps `DuckDbClient` from `integrations/duckdb/client.py`
- `DuckDbClient` is a `@lru_cache` singleton (see `deps/metrics.py::_analytics_db`) — the `ATTACH` to Postgres happens once, on first use, for the lifetime of the process.
- `DuckDbClient.query()` self-heals from a broken `ATTACH` (e.g. Postgres restarted after the connection was established): on any exception it reconnects (re-runs `INSTALL`/`LOAD`/`ATTACH` via `_connect()`) and retries the query once before propagating. Without this, a Postgres restart would permanently 503 all metrics endpoints until the whole service restarted.

## Cache Invalidation

`ProcessEmployeesChunkWorker` calls `finalize_batch` (in `workers/helpers/batch_status.py`) after every successful employee ingestion, which deletes both cache keys to keep metrics fresh.

- `CacheClient.delete()` retries with a 15s/30s backoff before giving up — covers isolated/transient failures of the delete call itself.
- This does **not** help if Redis is fully down: reads (`get_json`) already degrade gracefully to a cache miss (falls through to a live DuckDB query), so a full Redis outage never serves stale data, just slower (uncached) responses.
- What the retry *does* cover: Redis is reachable for reads but the specific `delete` call fails transiently. Without the retry, the stale pre-ingestion value would keep being served by `get_json` until the 8h TTL naturally expires.
- The 8h `METRICS_CACHE_TTL` remains the hard ceiling on staleness even if all delete retries are exhausted.

## Claims

- DuckDB queries Postgres via the `pg` extension — tables prefixed `pg.public.*`.
- Both metrics UCs are stateless — no UC-level state, all data from DuckDB + cache.
- `METRICS_CACHE_TTL = 28800` seconds (8 hours).
- Cache invalidation happens in `finalize()`, not in `run()` — only after all chunks complete.
- `departments` and `jobs` ingest endpoints do **not** invalidate the metrics cache. Both metrics queries read `hired_employees` (with JOINs to departments/jobs as reference data) — only employee data changes affect query results, so only the employee worker needs to invalidate.
- `DuckDbClient.query()` reconnects and retries exactly once on failure — a second consecutive failure propagates as `AnalyticsUnavailableError` (503).
- `CacheClient.delete()` retries at 15s then 30s (two retries, three total attempts) before logging and giving up.
