from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.deps.ingestion import (
    get_ingest_departments_uc,
    get_ingest_employees_uc,
    get_ingest_jobs_uc,
    get_process_employees_worker,
)
from app.services.ingestion.helpers.csv_parser import parse_departments, parse_jobs
from app.services.ingestion.schemas.ingestion_response import AcceptedResponse, IngestionResponse
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase
from app.services.ingestion.use_cases.ingest_employees import IngestEmployeesUseCase
from app.services.ingestion.use_cases.ingest_jobs import IngestJobsUseCase
from app.workers.process_employees_chunk import ProcessEmployeesChunkWorker

router = APIRouter(prefix="/ingest", tags=["ingestion"])

_MAX_ROWS = 1000


@router.post("/departments", response_model=IngestionResponse)
async def ingest_departments(
    file: UploadFile = File(...),
    uc: IngestDepartmentsUseCase = Depends(get_ingest_departments_uc),
) -> IngestionResponse:
    records, parse_errors = parse_departments(await file.read())
    if not records:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid rows found")
    if len(records) > _MAX_ROWS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Max {_MAX_ROWS} rows per request")
    response = await uc.execute(records=records)
    response.errors.extend(parse_errors)
    return response


@router.post("/jobs", response_model=IngestionResponse)
async def ingest_jobs(
    file: UploadFile = File(...),
    uc: IngestJobsUseCase = Depends(get_ingest_jobs_uc),
) -> IngestionResponse:
    records, parse_errors = parse_jobs(await file.read())
    if not records:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid rows found")
    if len(records) > _MAX_ROWS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Max {_MAX_ROWS} rows per request")
    response = await uc.execute(records=records)
    response.errors.extend(parse_errors)
    return response


@router.post("/employees", status_code=status.HTTP_202_ACCEPTED, response_model=AcceptedResponse)
async def ingest_employees(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uc: IngestEmployeesUseCase = Depends(get_ingest_employees_uc),
    worker: ProcessEmployeesChunkWorker = Depends(get_process_employees_worker),
) -> AcceptedResponse:
    batch_id = await uc.execute(stream=file.file)
    background_tasks.add_task(worker.stream_and_process, batch_id=batch_id)
    return AcceptedResponse(batch_id=batch_id)
