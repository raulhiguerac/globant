import uuid
from typing import Protocol

from app.services.ingestion.schemas.job import JobRecord


class JobRepository(Protocol):

    def bulk_insert(self, *, records: list[JobRecord], batch_id: uuid.UUID) -> None: ...

    def add(self, *, record: JobRecord, batch_id: uuid.UUID) -> None: ...
