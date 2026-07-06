import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.models import IngestionBatchStatus
from app.workers.helpers.batch_status import finalize_batch, mark_batch_failed

MODULE = "app.workers.helpers.batch_status.run_in_threadpool"


async def _passthrough(fn):
    return fn()


def _make_uow():
    uow = MagicMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.mark.asyncio
async def test_marks_batch_failed_and_commits():
    batch_id = uuid.uuid4()
    uow = _make_uow()

    with patch(MODULE, side_effect=_passthrough):
        await mark_batch_failed(uow=uow, batch_id=batch_id)

    uow.batch.update_status.assert_called_once_with(batch_id=batch_id, status=IngestionBatchStatus.failed)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_failure_is_swallowed_and_rolled_back():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    uow.batch.update_status = MagicMock(side_effect=RuntimeError("db down"))

    with patch(MODULE, side_effect=_passthrough):
        await mark_batch_failed(uow=uow, batch_id=batch_id)

    uow.commit.assert_not_awaited()
    assert uow.rollback.await_count == 2


@pytest.mark.asyncio
async def test_finalize_batch_marks_completed_commits_and_invalidates_cache():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    cache_client = MagicMock()
    cache_client.delete = AsyncMock()

    with patch(MODULE, side_effect=_passthrough):
        await finalize_batch(uow=uow, cache_client=cache_client, batch_id=batch_id, errors=["1:Ana"])

    uow.batch.update_status.assert_called_once_with(
        batch_id=batch_id, status=IngestionBatchStatus.completed, errors=["1:Ana"]
    )
    uow.commit.assert_awaited_once()
    cache_client.delete.assert_awaited_once()
