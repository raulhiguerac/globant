import pytest
from sqlmodel import select

from app.models.models import IngestionBatch, IngestionBatchStatus, Jobs
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.schemas.job import JobRecord
from app.services.ingestion.use_cases.ingest_jobs import IngestJobsUseCase


@pytest.mark.asyncio
async def test_ingest_jobs_happy_path(session):
    uc = IngestJobsUseCase(uow=SqlUnitOfWork(session=session))
    records = [
        JobRecord(id=1, job="Recruiter"),
        JobRecord(id=2, job="Manager"),
    ]

    response = await uc.execute(records=records)

    assert response.created_count == 2
    assert response.errors == []

    jobs = session.exec(select(Jobs).order_by(Jobs.id)).all()
    assert [j.job for j in jobs] == ["Recruiter", "Manager"]

    batch = session.exec(select(IngestionBatch)).one()
    assert batch.status == IngestionBatchStatus.completed
