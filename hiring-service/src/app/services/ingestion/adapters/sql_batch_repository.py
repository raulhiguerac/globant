import uuid

from sqlalchemy import update
from sqlmodel import Session

from app.models.models import IngestionBatch, IngestionBatchStatus
from app.services.ingestion.ports.batch_repository import BatchRepository


class SqlBatchRepository(BatchRepository):

    def __init__(self, *, session: Session) -> None:
        self.session = session

    def add(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus) -> None:
        self.session.add(IngestionBatch(id=batch_id, status=status))
        self.session.flush()

    def update_status(self, *, batch_id: uuid.UUID, status: IngestionBatchStatus, errors: list[str] | None = None) -> None:
        stmt = update(IngestionBatch).where(IngestionBatch.id == batch_id).values(status=status, errors=errors or [])
        self.session.exec(stmt)
        self.session.flush()

    def get(self, *, batch_id: uuid.UUID) -> IngestionBatch | None:
        return self.session.get(IngestionBatch, batch_id)
