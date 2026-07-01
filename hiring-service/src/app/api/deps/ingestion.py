from fastapi import Depends
from sqlmodel import Session

from app.api.deps.shared import get_cache_client, get_storage
from app.db import get_session
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase
from app.services.ingestion.use_cases.ingest_employees import IngestEmployeesUseCase
from app.services.ingestion.use_cases.ingest_jobs import IngestJobsUseCase
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort
from app.workers.process_employees_chunk import ProcessEmployeesChunkWorker


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


def get_process_employees_worker(
    uow: UnitOfWork = Depends(get_uow),
    cache_client: CachePort = Depends(get_cache_client),
    storage: StoragePort = Depends(get_storage),
) -> ProcessEmployeesChunkWorker:
    return ProcessEmployeesChunkWorker(uow=uow, cache_client=cache_client, storage=storage)
