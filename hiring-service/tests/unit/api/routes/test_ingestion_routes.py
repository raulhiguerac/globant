import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.deps.ingestion import (
    get_batch_status_uc,
    get_ingest_departments_uc,
    get_ingest_employees_uc,
    get_process_employees_worker,
    get_ingest_jobs_uc,
)
from app.models.models import IngestionBatchStatus
from app.services.ingestion.schemas.ingestion_response import (
    AcceptedResponse,
    BatchStatusResponse,
    IngestionResponse,
)

_DEPT_CSV = b"1,Engineering\n2,HR"
_JOB_CSV = b"1,Recruiter\n2,Manager"
_EMP_CSV = b"1,Harold,2021-11-07T02:48:42Z,2,96\n2,Lidia,2021-07-27T19:04:09Z,1,2"


# ---------------------------------------------------------------------------
# POST /ingest/departments
# ---------------------------------------------------------------------------

def test_ingest_departments_200(app, client):
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=IngestionResponse(created_count=2, errors=[]))
    app.dependency_overrides[get_ingest_departments_uc] = lambda: mock_uc

    resp = client.post("/v1/ingest/departments", files={"file": ("d.csv", BytesIO(_DEPT_CSV), "text/csv")})

    assert resp.status_code == 200
    assert resp.json()["created_count"] == 2
    assert resp.json()["errors"] == []

    app.dependency_overrides.clear()


def test_ingest_departments_422_empty_file(client):
    resp = client.post("/v1/ingest/departments", files={"file": ("d.csv", BytesIO(b""), "text/csv")})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /ingest/jobs
# ---------------------------------------------------------------------------

def test_ingest_jobs_200(app, client):
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=IngestionResponse(created_count=2, errors=[]))
    app.dependency_overrides[get_ingest_jobs_uc] = lambda: mock_uc

    resp = client.post("/v1/ingest/jobs", files={"file": ("j.csv", BytesIO(_JOB_CSV), "text/csv")})

    assert resp.status_code == 200
    assert resp.json()["created_count"] == 2

    app.dependency_overrides.clear()


def test_ingest_jobs_422_empty_file(client):
    resp = client.post("/v1/ingest/jobs", files={"file": ("j.csv", BytesIO(b""), "text/csv")})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /ingest/employees
# ---------------------------------------------------------------------------

def test_ingest_employees_202(app, client):
    batch_id = uuid.uuid4()

    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=batch_id)

    mock_worker = MagicMock()
    mock_worker.stream_and_process = AsyncMock()

    app.dependency_overrides[get_ingest_employees_uc] = lambda: mock_uc
    app.dependency_overrides[get_process_employees_worker] = lambda: mock_worker

    resp = client.post("/v1/ingest/employees", files={"file": ("e.csv", BytesIO(_EMP_CSV), "text/csv")})

    assert resp.status_code == 202
    assert resp.json()["batch_id"] == str(batch_id)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /ingest/employees/{batch_id}/status
# ---------------------------------------------------------------------------

def test_get_batch_status_200(app, client):
    batch_id = uuid.uuid4()
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(
        return_value=BatchStatusResponse(
            batch_id=batch_id,
            status=IngestionBatchStatus.completed,
            errors=[],
        )
    )
    app.dependency_overrides[get_batch_status_uc] = lambda: mock_uc

    resp = client.get(f"/v1/ingest/employees/{batch_id}/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["batch_id"] == str(batch_id)
    assert body["status"] == "completed"

    app.dependency_overrides.clear()


def test_get_batch_status_404(app, client):
    from app.core.exceptions.ingestion import BatchNotFoundError

    batch_id = uuid.uuid4()
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(side_effect=BatchNotFoundError(batch_id=batch_id))
    app.dependency_overrides[get_batch_status_uc] = lambda: mock_uc

    resp = client.get(f"/v1/ingest/employees/{batch_id}/status")

    assert resp.status_code == 404

    app.dependency_overrides.clear()
