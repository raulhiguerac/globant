# Hiring Service

![Architecture](assets/architecture.jpg)

REST API for historical hiring data ingestion and analytics. Built for the Globant Data Engineering Challenge.

## Overview

The service exposes two groups of endpoints:

- **Section 1 — Ingestion**: Upload CSV files for `departments`, `jobs`, and `employees` into a Postgres database.
- **Section 2 — Metrics**: OLAP queries over the ingested data, backed by DuckDB and Redis cache.

---

## Architecture

Hexagonal architecture — ports (Protocol interfaces) → adapters (implementations) → use cases → API layer.

```
api/routes/       ← thin HTTP layer, no business logic
api/deps/         ← dependency injection (FastAPI Depends)
services/
  ingestion/
    use_cases/    ← IngestDepartmentsUC, IngestJobsUC, IngestEmployeesUC, GetBatchStatusUC
    adapters/     ← SQLAlchemy repositories + UoW
    ports/        ← Protocol interfaces
    helpers/      ← CSV parser, DB error translator, batch guard
  metrics/
    use_cases/    ← HiresByQuarterUC, DepartmentsAboveMeanUC
    adapters/     ← DuckDbAdapter
  shared/
    adapters/     ← RedisCacheAdapter, StorageAdapter
    ports/        ← CachePort, StoragePort
integrations/
  storage/gcs/   ← GCS client (swap to minio/ for local dev)
  cache/redis/   ← Redis client
  duckdb/        ← DuckDB client with pg extension
workers/
  process_employees_chunk.py  ← BackgroundTask worker
```

### Ingestion flow — Employees

```
POST /v1/ingest/employees
  → upload CSV to GCS (employees/{batch_id}.csv)
  → create IngestionBatch (status: pending)
  → return 202 AcceptedResponse(batch_id)
  → [BackgroundTask] ProcessEmployeesChunkWorker.stream_and_process()
      re-stream from GCS → parse → chunk (10k rows) → bulk INSERT + savepoint fallback
      → finalize: mark batch completed + invalidate metrics cache
```

Departments and jobs are **synchronous** (smaller datasets, bounded by 1000 rows per request).

### Metrics flow

```
GET /v1/metrics/hires-by-quarter
GET /v1/metrics/departments-above-mean

  → Redis cache hit → return immediately
  → cache miss → DuckDB queries Postgres via pg extension → cache result (TTL 8h)
```

Cache is proactively invalidated after every successful employee ingestion.

---

## Design Decisions

### Why not presigned URLs for CSV upload?

The optimal production pattern is: presigned URL → client PUTs directly to GCS → worker processes. This removes the API from the data path entirely.

**I chose direct multipart upload because there is no front-end client.** The consumers of this API are data engineers running scripts or tools like Postman. A presigned URL workflow requires a two-step client flow (get URL → upload), which adds complexity without a front-end to orchestrate it. The API handling the stream is acceptable given the target file sizes.

If a front-end were added, switching to presigned URLs would be the right call.

### Why BackgroundTask instead of Celery/ARQ?

FastAPI `BackgroundTasks` runs in the same process, guaranteed to complete before the server tears down the request lifecycle. No broker infrastructure required. For a challenge with bounded concurrency, this is the right tradeoff. Production at scale would use a proper task queue.

### Why DuckDB for metrics?

DuckDB's `pg` extension allows running analytical SQL directly on the Postgres tables without ETL. No separate data warehouse, no sync jobs. The tradeoff: queries hit the OLTP database, so heavy analytics load would compete with writes. The 8-hour Redis TTL mitigates this — queries are cached after the first hit.

### Bulk insert + savepoint fallback

Happy path: single `commit()` covers the batch row + all records — no orphan `ingestion_batch` rows on failure. On `IntegrityError` (duplicate PK, FK violation), falls to row-by-row with savepoints to rescue valid rows from the same batch.

---

## Endpoints

### Section 1 — Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/ingest/departments` | Upload departments CSV (sync, max 1000 rows) |
| `POST` | `/v1/ingest/jobs` | Upload jobs CSV (sync, max 1000 rows) |
| `POST` | `/v1/ingest/employees` | Upload employees CSV (async, returns `batch_id`) |
| `GET`  | `/v1/ingest/employees/{batch_id}/status` | Poll batch status (`pending` → `completed`) |

CSV format — departments: `id,department` · jobs: `id,job` · employees: `id,name,hiring_datetime,department_id,job_id`

### Section 2 — Metrics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/metrics/hires-by-quarter` | Hires per department/job broken down by Q1–Q4 (2021) |
| `GET` | `/v1/metrics/departments-above-mean` | Departments that hired above the 2021 mean |

---

## Dev Playground

Open the repo in VS Code and **Reopen in Container** — the devcontainer starts Postgres, Redis, and MinIO automatically via Docker Compose.

Once inside the container:

```bash
# 1. Run migrations
cd hiring-service
uv run alembic upgrade head

# 2. Start the API
uv run fastapi dev src/app/main.py --host 0.0.0.0
```

API available at `http://localhost:8000` — docs at `http://localhost:8000/docs`.

### Ingest sample data

```bash
# Departments
curl -X POST http://localhost:8000/v1/ingest/departments \
  -F "file=@data/departments.csv"

# Jobs
curl -X POST http://localhost:8000/v1/ingest/jobs \
  -F "file=@data/jobs.csv"

# Employees (async — returns batch_id)
curl -X POST http://localhost:8000/v1/ingest/employees \
  -F "file=@data/hired_employees.csv"

# Poll status
curl http://localhost:8000/v1/ingest/employees/{batch_id}/status
```

### Storage backend

By default the service uses **GCS**. For local development, swap the import in `src/app/api/deps/shared.py`:

```python
# Local (MinIO)
from app.integrations.storage.minio.storage import StorageClient

# Cloud (GCS) — default
from app.integrations.storage.gcs.storage import StorageClient
```

MinIO console: `http://localhost:9001` (user: `minioadmin` / pass: `minioadmin`)

### Run tests

```bash
docker compose exec develop uv run pytest
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Postgres connection string | — |
| `REDIS_URL` | Redis connection string | — |
| `STORAGE_BUCKET` | GCS or MinIO bucket name | `hiring` |
| `GCS_PROJECT` | GCP project ID (GCS only) | — |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (local GCS auth) | — |
| `EMPLOYEE_CHUNK_SIZE` | Rows per bulk insert chunk | `10000` |

---

## GCP Infrastructure (Terraform)

Resources defined in `terraform/`:

```
APIs (Secret Manager, Cloud SQL, GCS, Cloud Run)
  → time_sleep (30s propagation)
  → IAM service account
  → Secret Manager (DATABASE_URL, REDIS_URL)
  → GCS bucket + Cloud SQL (Postgres 15)
  → Cloud Run (FastAPI container)
```

### Deploy

```bash
cd terraform

# 1. Authenticate
gcloud auth application-default login

# 2. Copy and fill variables
cp terraform.tfvars.example terraform.tfvars

# 3. Init and apply
terraform init
terraform apply
```

`terraform.tfvars` is gitignored. Never commit credentials.

> Terraform could be managed from the existing CI/CD pipeline, but I intentionally keep it manual — this preserves full control over `destroy` and the infrastructure lifecycle without tying it to the deployment flow.

### CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| `ci.yml` | PR to `main` | `uv run pytest` |
| `cd.yml` | Push to `main` | Build + push Docker image to Docker Hub (`{dockerhub-user}/{image}:{git-sha}`) |

Branch protection on `main` enforces CI passing before merge.

### Database migrations

Migrations are run manually via Cloud SQL Auth Proxy:

```bash
# Start proxy
./cloud-sql-proxy {project}:{region}:{instance} --port 5432 &

# Run migrations
DATABASE_URL="postgresql://{user}:{password}@127.0.0.1:5432/{db}" \
  uv run alembic upgrade head
```

Automating this via a Cloud Run Job in the CD pipeline is possible but kept manual to retain control over schema changes.
