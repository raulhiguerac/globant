import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.models import IngestionBatchStatus
from app.services.ingestion.use_cases.ingest_employees import IngestEmployeesUseCase

MODULE = "app.services.ingestion.use_cases.ingest_employees.run_in_threadpool"


def _make_deps():
    uow = MagicMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    storage = MagicMock()
    storage.upload_file = AsyncMock()

    cache_client = MagicMock()

    return uow, storage, cache_client


async def _passthrough(fn):
    fn()


@pytest.mark.asyncio
async def test_happy_path_returns_batch_id():
    uow, storage, cache_client = _make_deps()
    uc = IngestEmployeesUseCase(uow=uow, storage=storage, cache_client=cache_client)
    stream = BytesIO(b"1,Harold,2021-11-07T02:48:42Z,2,96")

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(stream=stream)

    assert isinstance(result, uuid.UUID)
    storage.upload_file.assert_awaited_once()
    _, call_kwargs = storage.upload_file.call_args
    assert call_kwargs["key"] == f"employees/{result}.csv"
    uow.batch.add.assert_called_once_with(batch_id=result, status=IngestionBatchStatus.pending)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_storage_failure_propagates():
    uow, storage, cache_client = _make_deps()
    storage.upload_file = AsyncMock(side_effect=RuntimeError("storage down"))
    uc = IngestEmployeesUseCase(uow=uow, storage=storage, cache_client=cache_client)
    stream = BytesIO(b"data")

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(RuntimeError, match="storage down"):
            await uc.execute(stream=stream)

    uow.commit.assert_not_awaited()
