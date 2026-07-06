import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status

from app.api.deps.ingestion import (
    get_batch_status_uc,
    get_department_records,
    get_ingest_departments_uc,
    get_ingest_employees_uc,
    get_ingest_jobs_uc,
    get_job_records,
    get_process_employees_runner,
)
from app.services.ingestion.schemas.ingestion_response import AcceptedResponse, BatchStatusResponse, IngestionResponse
from app.services.ingestion.use_cases.get_batch_status import GetBatchStatusUseCase
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase
from app.services.ingestion.use_cases.ingest_employees import IngestEmployeesUseCase
from app.services.ingestion.use_cases.ingest_jobs import IngestJobsUseCase
from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.schemas.job import JobRecord

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/departments", response_model=IngestionResponse)
async def ingest_departments(
    parsed: tuple[list[DepartmentRecord], list[str]] = Depends(get_department_records),
    uc: IngestDepartmentsUseCase = Depends(get_ingest_departments_uc),
) -> IngestionResponse:
    records, parse_errors = parsed
    response = await uc.execute(records=records)
    response.errors.extend(parse_errors)
    return response


@router.post("/jobs", response_model=IngestionResponse)
async def ingest_jobs(
    parsed: tuple[list[JobRecord], list[str]] = Depends(get_job_records),
    uc: IngestJobsUseCase = Depends(get_ingest_jobs_uc),
) -> IngestionResponse:
    records, parse_errors = parsed
    response = await uc.execute(records=records)
    response.errors.extend(parse_errors)
    return response


@router.get("/employees/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: uuid.UUID,
    uc: GetBatchStatusUseCase = Depends(get_batch_status_uc),
) -> BatchStatusResponse:
    return await uc.execute(batch_id=batch_id)


@router.post("/employees", status_code=status.HTTP_202_ACCEPTED, response_model=AcceptedResponse)
async def ingest_employees(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uc: IngestEmployeesUseCase = Depends(get_ingest_employees_uc),
    runner: Callable[..., Awaitable[None]] = Depends(get_process_employees_runner),
) -> AcceptedResponse:
    batch_id = await uc.execute(stream=file.file)
    background_tasks.add_task(runner, batch_id=batch_id)
    return AcceptedResponse(batch_id=batch_id)
