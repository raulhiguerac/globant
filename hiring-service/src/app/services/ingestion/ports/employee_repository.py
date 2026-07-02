import uuid
from typing import Protocol

from app.services.ingestion.schemas.employee import EmployeeRecord


class EmployeeRepository(Protocol):

    def bulk_insert(self, *, records: list[EmployeeRecord], batch_id: uuid.UUID) -> None: ...

    def add(self, *, record: EmployeeRecord, batch_id: uuid.UUID) -> None: ...
