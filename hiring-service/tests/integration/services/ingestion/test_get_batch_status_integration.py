import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions.ingestion import BatchNotFoundError
from app.models.models import IngestionBatch, IngestionBatchStatus
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.services.ingestion.use_cases.get_batch_status import GetBatchStatusUseCase


@pytest.mark.asyncio
async def test_get_batch_status_completed_returns_as_is(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.completed, errors=["1:Ana"]))
    session.commit()

    uc = GetBatchStatusUseCase(uow=SqlUnitOfWork(session=session))
    result = await uc.execute(batch_id=batch_id)

    assert result.status == IngestionBatchStatus.completed
    assert result.errors == ["1:Ana"]


@pytest.mark.asyncio
async def test_get_batch_status_pending_within_timeout_stays_pending(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.commit()

    uc = GetBatchStatusUseCase(uow=SqlUnitOfWork(session=session))
    result = await uc.execute(batch_id=batch_id)

    assert result.status == IngestionBatchStatus.pending
    assert session.get(IngestionBatch, batch_id).status == IngestionBatchStatus.pending


@pytest.mark.asyncio
async def test_get_batch_status_pending_past_timeout_marked_failed_and_persisted(session):
    batch_id = uuid.uuid4()
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=10, seconds=1)
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.commit()
    session.execute(
        IngestionBatch.__table__.update()
        .where(IngestionBatch.id == batch_id)
        .values(created_at=stale_created_at)
    )
    session.commit()

    uc = GetBatchStatusUseCase(uow=SqlUnitOfWork(session=session))
    result = await uc.execute(batch_id=batch_id)

    assert result.status == IngestionBatchStatus.failed

    session.expire_all()
    assert session.get(IngestionBatch, batch_id).status == IngestionBatchStatus.failed


@pytest.mark.asyncio
async def test_get_batch_status_not_found_raises(session):
    uc = GetBatchStatusUseCase(uow=SqlUnitOfWork(session=session))

    with pytest.raises(BatchNotFoundError):
        await uc.execute(batch_id=uuid.uuid4())
