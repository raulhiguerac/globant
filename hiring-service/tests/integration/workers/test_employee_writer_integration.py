import uuid
from datetime import datetime, timezone

import pytest

from app.models.models import Departments, Employees, IngestionBatch, IngestionBatchStatus, Jobs
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.schemas.employee import EmployeeRecord
from app.workers.helpers.employee_writer import write_employees


@pytest.mark.asyncio
async def test_write_employees_fk_violation_falls_back_and_rescues_valid_row(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.flush()
    session.add(Departments(id=1, department="Engineering", batch_id=batch_id))
    session.add(Jobs(id=1, job="Recruiter", batch_id=batch_id))
    session.commit()

    records = [
        EmployeeRecord(
            id=1,
            name="Bad FK",
            hiring_datetime=datetime(2021, 3, 3, tzinfo=timezone.utc),
            department_id=1,
            job_id=999,
        ),
        EmployeeRecord(
            id=2,
            name="Ana",
            hiring_datetime=datetime(2021, 3, 3, tzinfo=timezone.utc),
            department_id=1,
            job_id=1,
        ),
    ]

    uow = SqlUnitOfWork(session=session)
    errors = await write_employees(uow=uow, batch_id=batch_id, records=records)

    assert errors == ["1:Bad FK"]
    assert session.get(Employees, 2) is not None
    assert session.get(Employees, 1) is None
