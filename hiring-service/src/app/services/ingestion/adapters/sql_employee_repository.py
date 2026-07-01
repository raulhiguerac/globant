import uuid

from sqlmodel import Session

from sqlalchemy.dialects.postgresql import insert

from app.models.models import Employees
from app.services.ingestion.ports.employee_repository import EmployeeRepository
from app.services.ingestion.schemas.employee import EmployeeRecord


class SqlEmployeeRepository(EmployeeRepository):

    def __init__(self, *, session: Session) -> None:
        self.session = session

    def bulk_insert(self, *, records: list[EmployeeRecord], batch_id: uuid.UUID) -> None:
        stmt = insert(Employees).values([
            {**n.model_dump(), "batch_id": batch_id} for n in records
        ])
        self.session.exec(stmt)
        self.session.flush()

    def add(self, *, record: EmployeeRecord, batch_id: uuid.UUID) -> None:
        self.session.add(
            Employees(
                id=record.id,
                name=record.name,
                hiring_datetime=record.hiring_datetime,
                department_id=record.department_id,
                job_id=record.job_id,
                batch_id=batch_id
            )
        )
        self.session.flush()
