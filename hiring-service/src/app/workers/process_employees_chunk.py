import uuid

from app.core.config.settings import settings
from app.core.logging.logger import get_logger
from app.services.ingestion.helpers.csv_parser import parse_employees
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort
from app.workers.helpers.batch_status import finalize_batch, mark_batch_failed
from app.workers.helpers.chunking import iter_chunks
from app.workers.helpers.employee_writer import write_employees
from app.workers.helpers.storage_reader import download_file

logger = get_logger(__name__)


class ProcessEmployeesChunkWorker:
    def __init__(self, *, uow: UnitOfWork, cache_client: CachePort, storage: StoragePort):
        self.uow = uow
        self.cache_client = cache_client
        self.storage = storage

    async def stream_and_process(self, *, batch_id: uuid.UUID) -> None:
        try:
            await self._process(batch_id=batch_id)
        except Exception as exc:
            logger.error("stream_and_process failed", extra={"batch_id": str(batch_id)}, exc_info=exc)
            await mark_batch_failed(uow=self.uow, batch_id=batch_id)
            raise

    async def _process(self, *, batch_id: uuid.UUID) -> None:
        key = f"employees/{batch_id}.csv"
        logger.info("stream_and_process start", extra={"batch_id": str(batch_id), "key": key})

        raw = await download_file(storage=self.storage, bucket=settings.STORAGE_BUCKET, key=key)
        logger.info("stream_and_process downloaded", extra={"batch_id": str(batch_id), "bytes": len(raw)})

        records, parse_errors = parse_employees(raw)
        logger.info(
            "stream_and_process parsed",
            extra={"batch_id": str(batch_id), "records": len(records), "parse_errors": len(parse_errors)},
        )

        all_errors: list[str] = list(parse_errors)
        for chunk_count, chunk in enumerate(iter_chunks(records, settings.EMPLOYEE_CHUNK_SIZE)):
            logger.info(
                "stream_and_process running chunk",
                extra={"batch_id": str(batch_id), "chunk": chunk_count, "size": len(chunk)},
            )
            chunk_errors = await write_employees(uow=self.uow, batch_id=batch_id, records=chunk)
            logger.info(
                "stream_and_process chunk done",
                extra={"batch_id": str(batch_id), "chunk": chunk_count, "errors": len(chunk_errors)},
            )
            all_errors.extend(chunk_errors)

        logger.info(
            "stream_and_process finalizing",
            extra={"batch_id": str(batch_id), "total_errors": len(all_errors)},
        )
        await finalize_batch(uow=self.uow, cache_client=self.cache_client, batch_id=batch_id, errors=all_errors)
        logger.info("stream_and_process complete", extra={"batch_id": str(batch_id)})
