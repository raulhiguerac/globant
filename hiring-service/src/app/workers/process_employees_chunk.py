import uuid
from functools import partial

from fastapi.concurrency import run_in_threadpool

from sqlalchemy.exc import OperationalError

from app.core.config.settings import settings
from app.core.logging.logger import get_logger
from app.models.models import IngestionBatchStatus
from app.services.ingestion.helpers.csv_parser import parse_employees
from app.services.ingestion.helpers.db_error_translator import translate_db_error
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.employee import EmployeeRecord
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort

logger = get_logger(__name__)

METRICS_CACHE_KEYS = [
    "hiring:metrics:hires_by_quarter",
    "hiring:metrics:departments_above_mean",
]


class ProcessEmployeesChunkWorker:
    def __init__(self, *, uow: UnitOfWork, cache_client: CachePort, storage: StoragePort):
        self.uow = uow
        self.cache_client = cache_client
        self.storage = storage

    async def run(self, *, batch_id: uuid.UUID, records: list[EmployeeRecord]) -> list[str]:
        try:
            await run_in_threadpool(
                partial(self.uow.employees.bulk_insert, records=records, batch_id=batch_id)
            )
            await self.uow.commit()
            return []
        except OperationalError as exc:
            await self.uow.rollback()
            raise translate_db_error(exc) from exc
        except Exception as exc:
            await self.uow.rollback()
            logger.warning(
                "bulk_insert failed, falling back to row-by-row",
                extra={"batch_id": str(batch_id), "total": len(records)},
                exc_info=exc,
            )

        errors: list[str] = []

        for record in records:
            try:
                await self.uow.begin_nested()
                await run_in_threadpool(
                    partial(self.uow.employees.add, record=record, batch_id=batch_id)
                )
                await self.uow.commit()
            except OperationalError as exc:
                raise translate_db_error(exc) from exc
            except Exception as exc:
                await self.uow.rollback_to_savepoint()
                logger.warning(
                    "failed to insert employee",
                    extra={"employee_id": record.id, "name": record.name},
                    exc_info=exc,
                )
                errors.append(f"{record.id}:{record.name}")

        return errors

    async def finalize(self, *, batch_id: uuid.UUID) -> None:
        await run_in_threadpool(
            partial(self.uow.batch.update_status, batch_id=batch_id, status=IngestionBatchStatus.completed)
        )
        await self.uow.commit()
        await self.cache_client.delete(key=METRICS_CACHE_KEYS)

    async def stream_and_process(self, *, batch_id: uuid.UUID) -> None:
        key = f"employees/{batch_id}.csv"
        raw_chunks: list[bytes] = []
        async for chunk in await self.storage.stream_file(bucket=settings.STORAGE_BUCKET, key=key):
            raw_chunks.append(chunk)

        records, _ = parse_employees(b"".join(raw_chunks))
        for i in range(0, len(records), settings.EMPLOYEE_CHUNK_SIZE):
            await self.run(batch_id=batch_id, records=records[i : i + settings.EMPLOYEE_CHUNK_SIZE])

        await self.finalize(batch_id=batch_id)
