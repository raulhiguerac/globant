import uuid
from functools import partial
from typing import BinaryIO

from fastapi.concurrency import run_in_threadpool

from app.core.config.settings import settings
from app.core.logging.logger import get_logger
from app.models.models import IngestionBatchStatus
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort

logger = get_logger(__name__)


class IngestEmployeesUseCase:
    def __init__(self, *, uow: UnitOfWork, cache_client: CachePort, storage: StoragePort):
        self.uow = uow
        self.cache_client = cache_client
        self.storage = storage

    async def execute(self, *, stream: BinaryIO) -> uuid.UUID:
        batch_id = uuid.uuid4()
        key = f"employees/{batch_id}.csv"

        await self.storage.upload_file(fileobj=stream, bucket=settings.STORAGE_BUCKET, key=key)

        await run_in_threadpool(
            partial(self.uow.batch.add, batch_id=batch_id, status=IngestionBatchStatus.pending)
        )
        await self.uow.commit()

        return batch_id
