import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, File, UploadFile
from sqlmodel import Session

from app.api.deps.shared import get_cache_client, get_storage
from app.db import engine, get_session
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.helpers.batch_guard import validate_batch
from app.services.ingestion.helpers.csv_parser import parse_departments, parse_jobs
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.schemas.job import JobRecord
from app.services.ingestion.use_cases.get_batch_status import GetBatchStatusUseCase
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase
from app.services.ingestion.use_cases.ingest_employees import IngestEmployeesUseCase
from app.services.ingestion.use_cases.ingest_jobs import IngestJobsUseCase
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort
from app.workers.process_employees_chunk import ProcessEmployeesChunkWorker


async def get_department_records(file: UploadFile = File(...)) -> tuple[list[DepartmentRecord], list[str]]:
    records, parse_errors = parse_departments(await file.read())
    validate_batch(records)
    return records, parse_errors


async def get_job_records(file: UploadFile = File(...)) -> tuple[list[JobRecord], list[str]]:
    records, parse_errors = parse_jobs(await file.read())
    validate_batch(records)
    return records, parse_errors


def get_uow(session: Session = Depends(get_session)) -> UnitOfWork:
    return SqlUnitOfWork(session=session)


def get_ingest_departments_uc(
    uow: UnitOfWork = Depends(get_uow),
) -> IngestDepartmentsUseCase:
    return IngestDepartmentsUseCase(uow=uow)


def get_ingest_jobs_uc(
    uow: UnitOfWork = Depends(get_uow),
) -> IngestJobsUseCase:
    return IngestJobsUseCase(uow=uow)


def get_ingest_employees_uc(
    uow: UnitOfWork = Depends(get_uow),
    cache_client: CachePort = Depends(get_cache_client),
    storage: StoragePort = Depends(get_storage),
) -> IngestEmployeesUseCase:
    return IngestEmployeesUseCase(uow=uow, cache_client=cache_client, storage=storage)


def get_batch_status_uc(
    uow: UnitOfWork = Depends(get_uow),
) -> GetBatchStatusUseCase:
    return GetBatchStatusUseCase(uow=uow)


async def run_process_employees_chunk(*, batch_id: uuid.UUID) -> None:
    # Own session scoped to the background task, not to the request that scheduled it.
    with Session(engine) as session:
        worker = ProcessEmployeesChunkWorker(
            uow=SqlUnitOfWork(session=session),
            cache_client=get_cache_client(),
            storage=get_storage(),
        )
        await worker.stream_and_process(batch_id=batch_id)


def get_process_employees_runner() -> Callable[..., Awaitable[None]]:
    return run_process_employees_chunk
