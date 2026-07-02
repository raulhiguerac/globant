import uuid
from unittest.mock import MagicMock, patch

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
