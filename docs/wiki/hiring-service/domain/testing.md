---
title: Hiring Service — Testing Strategy
status: stable
last-verified: 2026-07-05
sources:
  - sources/hiring-service/2026-07-05-integration-tests-and-terraform-hardening.md
related:
  - hiring-service-design
  - metrics
  - gcp-infra
---

## Overview

Two suites, run as separate pytest processes:

- **Unit** (`tests/unit`, 79 tests) — mocks everywhere, no external services. This is what bare `pytest` runs (`testpaths = ["tests/unit"]` in pyproject).
- **Integration** (`tests/integration`, 15 tests) — real Postgres 17 via [testcontainers](https://testcontainers-python.readthedocs.io/), run explicitly with `pytest tests/integration`.

testcontainers over GH Actions `services:` because the same code runs locally and in CI, and because tests can manipulate containers at runtime (the DuckDB reconnect test restarts Postgres mid-test — impossible with a static `services:` block).

## Why the split into separate processes

`Settings` is a module-level singleton created at import time. Collecting both suites in one pytest process left it cached with `DATABASE_URL=""` (integration's conftest imports it before unit's env-var conftest runs), breaking collection. `testpaths = ["tests/unit"]` makes bare `pytest` unit-only; CI runs each suite as its own step.

## Integration fixtures (`tests/integration/conftest.py`)

- `postgres_container` / `database_url` (session-scoped): one `PostgresContainer("postgres:17")` for the whole run, Alembic `upgrade head` applied once. URL taken with `get_connection_url(driver=None)` — the default URL includes `+psycopg2`, which DuckDB's `ATTACH` rejects.
- `session` — savepoint-isolated (`join_transaction_mode="create_savepoint"`), auto-rolls back after each test. Default choice.
- `real_session` — commits for real, cleans up with `TRUNCATE ... CASCADE`. Needed only when a **second physical connection** must see the data: DuckDB's `ATTACH` opens its own connection to Postgres and can never see another transaction's uncommitted state.

## What integration covers that mocks can't

- `db_error_translator` regex-parses the **literal** Postgres error text (`constraint "departments_pkey"`, `Key (id)=(5)`); unit tests fabricate those strings, so only integration proves the regexes match real output.
- Real savepoint behavior in the bulk-insert → row-by-row fallback.
- Stale-`pending` batch (>`BATCH_TIMEOUT_SECONDS`) reported **and persisted** as `failed`.
- Worker end-to-end (fake storage/cache + real DB), including storage failure → batch `failed` in DB.
- Both DuckDB metrics queries against seeded rows.
- `DuckDbClient` reconnect across an actual Postgres container restart.

## Pitfalls found (and their fixes)

- SQLAlchemy does **not** reorder INSERTs across tables within one flush — seed data needs an explicit `flush()` after the batch row, before FK-dependent rows (the app code already does this).
- Docker reassigns a random host port on container restart. The restart test pins it (`.with_bind_ports(5432, 55432)`) — a real prod restart never changes address, so the random port would test the wrong thing.
- The restart test uses its **own dedicated container**: restarting the shared session-scoped one broke every test that ran after it.

## Claims

- Bare `pytest` runs only `tests/unit`; integration is opt-in via `pytest tests/integration`.
- `real_session` exists solely because DuckDB's `ATTACH` is a second physical connection — savepoint-isolated fixtures are invisible to it.
- `testcontainers[postgres]` lives in the `dev` extra of `hiring-service/pyproject.toml`.
- CI's integration step has `timeout-minutes: 10`.
