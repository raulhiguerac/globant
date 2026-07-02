import uuid
from functools import partial

from fastapi.concurrency import run_in_threadpool

from app.core.exceptions.ingestion import BatchNotFoundError
from app.models.models import IngestionBatchStatus
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.ingestion_response import BatchStatusResponse


class GetBatchStatusUseCase:
    def __init__(self, *, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, *, batch_id: uuid.UUID) -> BatchStatusResponse:
        batch = await run_in_threadpool(partial(self.uow.batch.get, batch_id=batch_id))
        if batch is None:
            raise BatchNotFoundError(batch_id=batch_id)
        return BatchStatusResponse(batch_id=batch.id, status=batch.status, errors=batch.errors or [])
