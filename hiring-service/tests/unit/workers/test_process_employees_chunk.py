import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.process_employees_chunk import ProcessEmployeesChunkWorker

MODULE = "app.workers.process_employees_chunk"


def _make_worker():
    uow = MagicMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    cache_client = MagicMock()
    cache_client.delete = AsyncMock()
    storage = MagicMock()
    return ProcessEmployeesChunkWorker(uow=uow, cache_client=cache_client, storage=storage)


@pytest.mark.asyncio
async def test_crash_marks_batch_failed_and_reraises():
    batch_id = uuid.uuid4()
    worker = _make_worker()

    with (
        patch(f"{MODULE}.download_file", AsyncMock(side_effect=ConnectionError("storage down"))),
        patch(f"{MODULE}.mark_batch_failed", AsyncMock()) as mark_failed,
    ):
        with pytest.raises(ConnectionError):
            await worker.stream_and_process(batch_id=batch_id)

    mark_failed.assert_awaited_once_with(uow=worker.uow, batch_id=batch_id)


@pytest.mark.asyncio
async def test_happy_path_finalizes_without_marking_failed():
    batch_id = uuid.uuid4()
    worker = _make_worker()

    with (
        patch(f"{MODULE}.download_file", AsyncMock(return_value=b"csv")),
        patch(f"{MODULE}.parse_employees", MagicMock(return_value=([MagicMock()], []))),
        patch(f"{MODULE}.write_employees", AsyncMock(return_value=[])),
        patch(f"{MODULE}.finalize_batch", AsyncMock()) as finalize_batch,
        patch(f"{MODULE}.mark_batch_failed", AsyncMock()) as mark_failed,
    ):
        await worker.stream_and_process(batch_id=batch_id)

    finalize_batch.assert_awaited_once_with(
        uow=worker.uow, cache_client=worker.cache_client, batch_id=batch_id, errors=[]
    )
    mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_finalize_failure_marks_batch_failed():
    batch_id = uuid.uuid4()
    worker = _make_worker()

    with (
        patch(f"{MODULE}.download_file", AsyncMock(return_value=b"csv")),
        patch(f"{MODULE}.parse_employees", MagicMock(return_value=([MagicMock()], []))),
        patch(f"{MODULE}.write_employees", AsyncMock(return_value=[])),
        patch(f"{MODULE}.finalize_batch", AsyncMock(side_effect=RuntimeError("db down"))),
        patch(f"{MODULE}.mark_batch_failed", AsyncMock()) as mark_failed,
    ):
        with pytest.raises(RuntimeError):
            await worker.stream_and_process(batch_id=batch_id)

    mark_failed.assert_awaited_once_with(uow=worker.uow, batch_id=batch_id)
