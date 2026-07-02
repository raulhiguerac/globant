import uuid
from typing import Protocol

from app.models.models import IngestionBatch, IngestionBatchStatus


class BatchRepository(Protocol):

    def add(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus) -> None: ...

    def update_status(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus, errors: list[str] | None = None) -> None: ...

    def get(self, *, batch_id: uuid.UUID) -> IngestionBatch | None: ...
