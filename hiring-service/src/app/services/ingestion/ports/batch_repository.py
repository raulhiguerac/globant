import uuid
from typing import Protocol

from app.models.models import IngestionBatchStatus


class BatchRepository(Protocol):

    def add(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus) -> None: ...

    def update_status(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus) -> None: ...
