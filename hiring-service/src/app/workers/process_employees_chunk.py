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


class ProcessEmployeesChunkWorker:
    def __init__(self, *, uow: UnitOfWork, cache_client: CachePort, storage: StoragePort):
        self.uow = uow
        self.cache_client = cache_client
        self.storage = storage

    async def run(self, *, batch_id: uuid.UUID, records: list[EmployeeRecord]) -> list[str]:
        logger.debug("run bulk_insert", extra={"batch_id": str(batch_id), "count": len(records)})
        try:
            await run_in_threadpool(
                partial(self.uow.employees.bulk_insert, records=records, batch_id=batch_id)
            )
            await self.uow.commit()
            logger.debug("run bulk_insert committed", extra={"batch_id": str(batch_id), "count": len(records)})
            return []
        except OperationalError as exc:
            await self.uow.rollback()
            logger.error("run bulk_insert operational error", extra={"batch_id": str(batch_id)}, exc_info=exc)
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
                    extra={"employee_id": record.id, "employee_name": record.name},
                    exc_info=exc,
                )
                errors.append(f"{record.id}:{record.name}")

        return errors

    async def finalize(self, *, batch_id: uuid.UUID, errors: list[str]) -> None:
        logger.info("finalize start", extra={"batch_id": str(batch_id), "errors": len(errors)})
        await run_in_threadpool(
            partial(
                self.uow.batch.update_status,
                batch_id=batch_id,
                status=IngestionBatchStatus.completed,
                errors=errors,
            )
        )
        await self.uow.commit()
        await self.cache_client.delete(key=settings.METRICS_CACHE_KEYS)
        logger.info("finalize done", extra={"batch_id": str(batch_id)})

    async def stream_and_process(self, *, batch_id: uuid.UUID) -> None:
        key = f"employees/{batch_id}.csv"
        logger.info("stream_and_process start", extra={"batch_id": str(batch_id), "key": key})

        raw_chunks: list[bytes] = []
        try:
            async for chunk in await self.storage.stream_file(bucket=settings.STORAGE_BUCKET, key=key):
                raw_chunks.append(chunk)
        except Exception as exc:
            logger.error("stream_and_process storage error", extra={"batch_id": str(batch_id)}, exc_info=exc)
            raise

        total_bytes = sum(len(c) for c in raw_chunks)
        logger.info("stream_and_process downloaded", extra={"batch_id": str(batch_id), "bytes": total_bytes})

        records, parse_errors = parse_employees(b"".join(raw_chunks))
        logger.info(
            "stream_and_process parsed",
            extra={"batch_id": str(batch_id), "records": len(records), "parse_errors": len(parse_errors)},
        )

        all_errors: list[str] = list(parse_errors)
        chunk_count = 0
        for i in range(0, len(records), settings.EMPLOYEE_CHUNK_SIZE):
            chunk = records[i : i + settings.EMPLOYEE_CHUNK_SIZE]
            logger.info(
                "stream_and_process running chunk",
                extra={"batch_id": str(batch_id), "chunk": chunk_count, "size": len(chunk)},
            )
            chunk_errors = await self.run(batch_id=batch_id, records=chunk)
            logger.info(
                "stream_and_process chunk done",
                extra={"batch_id": str(batch_id), "chunk": chunk_count, "errors": len(chunk_errors)},
            )
            all_errors.extend(chunk_errors)
            chunk_count += 1

        logger.info(
            "stream_and_process finalizing",
            extra={"batch_id": str(batch_id), "total_errors": len(all_errors)},
        )
        await self.finalize(batch_id=batch_id, errors=all_errors)
        logger.info("stream_and_process complete", extra={"batch_id": str(batch_id)})
