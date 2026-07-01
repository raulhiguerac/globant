from sqlmodel import Session

from app.services.ingestion.adapters.sql_batch_repository import SqlBatchRepository
from app.services.ingestion.adapters.sql_department_repository import SqlDepartmentRepository
from app.services.ingestion.adapters.sql_employee_repository import SqlEmployeeRepository
from app.services.ingestion.adapters.sql_job_repository import SqlJobRepository
from app.services.ingestion.ports.unit_of_work import UnitOfWork


class SqlUnitOfWork(UnitOfWork):

    def __init__(self, *, session: Session) -> None:
        self.session = session
        self.batch = SqlBatchRepository(session=session)
        self.departments = SqlDepartmentRepository(session=session)
        self.jobs = SqlJobRepository(session=session)
        self.employees = SqlEmployeeRepository(session=session)

    async def commit(self) -> None:
        self.session.commit()

    async def rollback(self) -> None:
        self.session.rollback()

    async def refresh(self, instance: object) -> None:
        self.session.refresh(instance)

    async def begin_nested(self) -> None:
        self._savepoint = self.session.begin_nested()

    async def rollback_to_savepoint(self) -> None:
        if self._savepoint:
            self._savepoint.rollback()
            self._savepoint = None
