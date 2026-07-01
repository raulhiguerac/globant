from typing import Protocol

from app.services.ingestion.ports.batch_repository import BatchRepository
from app.services.ingestion.ports.department_repository import DepartmentRepository
from app.services.ingestion.ports.employee_repository import EmployeeRepository
from app.services.ingestion.ports.job_repository import JobRepository


class UnitOfWork(Protocol):
    batch: BatchRepository
    departments: DepartmentRepository
    jobs: JobRepository
    employees: EmployeeRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def refresh(self, instance: object) -> None: ...
    async def begin_nested(self) -> None: ...
    async def rollback_to_savepoint(self) -> None: ...
