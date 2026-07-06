---
title: Integration tests (testcontainers) + Terraform Cloud Run hardening
captured-from: conversation
captured-on: 2026-07-05
participants: [raul, claude]
---

## Context

Continuation of the robustness-hardening session: the last open gap was the empty `tests/integration/` folder. Decided to build the suite with testcontainers (portable local/CI, runtime container control) instead of GH Actions `services:`. Also enabled the Cloud Run Terraform module and reviewed its security posture.

## Key conclusions

- **15 integration tests added, all passing** (plus the 79 unit tests): ingestion happy paths, real PK-duplicate fallback, `db_error_translator` against genuine Postgres `IntegrityError` text (regex parsing that mocks can't validate), `GetBatchStatusUseCase` stale-pending→failed edge case persisted in DB, `employee_writer` FK-violation rescue, worker end-to-end (fake storage/cache + real DB) including storage-failure→`failed`, both DuckDB metrics queries against seeded data, and `DuckDbClient` reconnect through a **real Postgres container restart**.
- **Fixtures** (`tests/integration/conftest.py`): session-scoped `PostgresContainer("postgres:17")` + Alembic `upgrade head`; `session` (savepoint-isolated via `join_transaction_mode="create_savepoint"`, auto-rollback) and `real_session` (real commits + TRUNCATE cleanup — required because DuckDB's `ATTACH` is a second physical connection that can't see uncommitted data).
- Pitfalls hit and solved: SQLAlchemy does **not** reorder INSERTs across tables within one flush (explicit `flush()` after creating the batch row, matching app code); Docker reassigns a random host port on container restart, so the restart test pins the port with `.with_bind_ports(5432, 55432)` and uses a **dedicated** container (restarting the shared one broke every subsequent test); testcontainers URL needs `get_connection_url(driver=None)` — the default includes `+psycopg2`, which DuckDB's `ATTACH` rejects.
- **`Settings` singleton collection bug**: running unit+integration in one pytest process left `DATABASE_URL=""` cached at import time and broke collection. Fix: `testpaths = ["tests/unit"]` in pyproject (bare `pytest` = unit only); integration runs explicitly via `pytest tests/integration`.
- **CI** (`ci.yml`): separate steps `pytest tests/unit` and `pytest tests/integration` (separate processes, so the singleton bug doesn't apply), integration step has `timeout-minutes: 10` to fail fast if testcontainers/Ryuk hangs. `testcontainers[postgres]` added to dev extras.
- **CD does not re-run tests** — deliberate: branch protection + CI on PR already gate `main`; duplicating in CD only adds latency, and the bypass-push scenario is better solved by stricter branch protection.
- **Terraform Cloud Run module uncommented** and `terraform validate` passes. `image` must be passed per apply as `raulhiguera/globant:<git-sha>` (Docker Hub, public repo) — CD never publishes `:latest` nor to GCR, so the stale `gcr.io/...:latest` value in local tfvars would fail to pull.
- **`allUsers` invoker removed**: `google_cloud_run_v2_service_iam_member` now iterates `var.invoker_members` (required, no default) — exposure is an explicit tfvars decision, not a hidden module default.
- Full no-internet exposure would additionally need: `ingress = INGRESS_TRAFFIC_INTERNAL_ONLY` (the actual change — IAM alone still leaves the URL reachable), Serverless VPC Access connector, Cloud SQL with `ipv4_enabled = false`, and Memorystore instead of external Redis Cloud. Discussed, not implemented (assessment scope).
- Repo verdict: solid to defend. README gained Known Limitations + test-running docs; wiki/ADR coverage current.

## Open questions

- Cloud Run deploy still not validated end-to-end against GCP.

## Next steps

- **Commit and push everything** — all of today's work is uncommitted in the working tree.
- Before a live Terraform demo: fix local tfvars `image` (Docker Hub + real SHA) and add `invoker_members` (now mandatory).
- Cosmetic: `ci.yml` workflow is still named "Run unit test" but also runs integration.
