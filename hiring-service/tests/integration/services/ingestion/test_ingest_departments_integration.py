import uuid

import pytest
from sqlmodel import select

from app.models.models import Departments, IngestionBatch, IngestionBatchStatus
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase


@pytest.mark.asyncio
async def test_ingest_departments_happy_path(session):
    uc = IngestDepartmentsUseCase(uow=SqlUnitOfWork(session=session))
    records = [
        DepartmentRecord(id=1, department="Engineering"),
        DepartmentRecord(id=2, department="HR"),
    ]

    response = await uc.execute(records=records)

    assert response.created_count == 2
    assert response.errors == []

    departments = session.exec(select(Departments).order_by(Departments.id)).all()
    assert [d.department for d in departments] == ["Engineering", "HR"]

    batch = session.exec(select(IngestionBatch)).one()
    assert batch.status == IngestionBatchStatus.completed


@pytest.mark.asyncio
async def test_ingest_departments_duplicate_pk_falls_back_and_rescues_valid_row(session):
    existing_batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=existing_batch_id, status=IngestionBatchStatus.completed))
    session.flush()
    session.add(Departments(id=1, department="Engineering", batch_id=existing_batch_id))
    session.commit()

    uc = IngestDepartmentsUseCase(uow=SqlUnitOfWork(session=session))
    records = [
        DepartmentRecord(id=1, department="Duplicated"),
        DepartmentRecord(id=2, department="HR"),
    ]

    response = await uc.execute(records=records)

    assert response.created_count == 1
    assert response.errors == ["1:Duplicated"]

    assert session.get(Departments, 1).department == "Engineering"
    assert session.get(Departments, 2).department == "HR"
