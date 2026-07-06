import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.core.exceptions.ingestion import BatchNotFoundError
from app.models.models import IngestionBatchStatus
from app.services.ingestion.use_cases.get_batch_status import GetBatchStatusUseCase

MODULE = "app.services.ingestion.use_cases.get_batch_status.run_in_threadpool"


async def _passthrough(fn):
    return fn()


@pytest.mark.asyncio
async def test_happy_path_returns_status():
    batch_id = uuid.uuid4()
    batch = MagicMock()
    batch.id = batch_id
    batch.status = IngestionBatchStatus.completed
    batch.errors = ["row 2: invalid"]

    uow = MagicMock()
    uow.batch.get = MagicMock(return_value=batch)
    uc = GetBatchStatusUseCase(uow=uow)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(batch_id=batch_id)

    assert result.batch_id == batch_id
    assert result.status == IngestionBatchStatus.completed
    assert result.errors == ["row 2: invalid"]


@pytest.mark.asyncio
async def test_batch_not_found_raises():
    batch_id = uuid.uuid4()
    uow = MagicMock()
    uow.batch.get = MagicMock(return_value=None)
    uc = GetBatchStatusUseCase(uow=uow)

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(BatchNotFoundError):
            await uc.execute(batch_id=batch_id)


@pytest.mark.asyncio
async def test_operational_error_propagates():
    batch_id = uuid.uuid4()
    uow = MagicMock()
    uow.batch.get = MagicMock(side_effect=OperationalError("db down", {}, Exception()))
    uc = GetBatchStatusUseCase(uow=uow)

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(OperationalError):
            await uc.execute(batch_id=batch_id)


@pytest.mark.asyncio
async def test_pending_within_timeout_stays_pending():
    batch_id = uuid.uuid4()
    batch = MagicMock()
    batch.id = batch_id
    batch.status = IngestionBatchStatus.pending
    batch.errors = None
    batch.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    uow = MagicMock()
    uow.batch.get = MagicMock(return_value=batch)
    uow.commit = AsyncMock()
    uc = GetBatchStatusUseCase(uow=uow)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(batch_id=batch_id)

    assert result.status == IngestionBatchStatus.pending
    uow.batch.update_status.assert_not_called()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_past_timeout_is_reported_and_marked_failed():
    batch_id = uuid.uuid4()
    batch = MagicMock()
    batch.id = batch_id
    batch.status = IngestionBatchStatus.pending
    batch.errors = None
    batch.created_at = datetime.now(timezone.utc) - timedelta(seconds=601)

    uow = MagicMock()
    uow.batch.get = MagicMock(return_value=batch)
    uow.commit = AsyncMock()
    uc = GetBatchStatusUseCase(uow=uow)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(batch_id=batch_id)

    assert result.status == IngestionBatchStatus.failed
    uow.batch.update_status.assert_called_once_with(batch_id=batch_id, status=IngestionBatchStatus.failed)
    uow.commit.assert_awaited_once()
