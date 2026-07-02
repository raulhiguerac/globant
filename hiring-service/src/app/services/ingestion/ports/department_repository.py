import uuid
from typing import Protocol

from app.services.ingestion.schemas.department import DepartmentRecord


class DepartmentRepository(Protocol):

    def bulk_insert(self, *, records: list[DepartmentRecord], batch_id: uuid.UUID) -> None: ...

    def add(self, *, record: DepartmentRecord, batch_id: uuid.UUID) -> None: ...
