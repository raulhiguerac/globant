import uuid
from datetime import datetime, timezone
from functools import partial

from fastapi.concurrency import run_in_threadpool

from app.core.config.settings import settings
from app.core.exceptions.ingestion import BatchNotFoundError
from app.models.models import IngestionBatchStatus
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.ingestion_response import BatchStatusResponse


class GetBatchStatusUseCase:
    def __init__(self, *, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def _is_stale(*, created_at: datetime) -> bool:
        age = datetime.now(timezone.utc) - created_at
        return age.total_seconds() > settings.BATCH_TIMEOUT_SECONDS
    
    async def execute(self, *, batch_id: uuid.UUID) -> BatchStatusResponse:
        batch = await run_in_threadpool(partial(self.uow.batch.get, batch_id=batch_id))
        if batch is None:
            raise BatchNotFoundError(batch_id=batch_id)

        status = batch.status
        if status == IngestionBatchStatus.pending and self._is_stale(created_at=batch.created_at):
            status = IngestionBatchStatus.failed
            await run_in_threadpool(
                partial(self.uow.batch.update_status, batch_id=batch_id, status=status)
            )
            await self.uow.commit()

        return BatchStatusResponse(batch_id=batch.id, status=status, errors=batch.errors or [])
