import uuid

from sqlmodel import Session

from app.models.models import Departments
from sqlalchemy.dialects.postgresql import insert

from app.services.ingestion.ports.department_repository import DepartmentRepository
from app.services.ingestion.schemas.department import DepartmentRecord


class SqlDepartmentRepository(DepartmentRepository):

    def __init__(self, *, session: Session) -> None:
        self.session = session

    def bulk_insert(self, *, records: list[DepartmentRecord], batch_id: uuid.UUID) -> None:
        stmt = insert(Departments).values([
            {**n.model_dump(), "batch_id": batch_id} for n in records
        ])
        self.session.exec(stmt)
        self.session.flush()
    
    def add(self, *, record: DepartmentRecord, batch_id: uuid.UUID) -> None:
        self.session.add(
            Departments(
                id=record.id,
                department=record.department,
                batch_id=batch_id
            )
        )
        self.session.flush()
