import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.deps.ingestion import get_process_employees_runner, run_process_employees_chunk

MODULE = "app.api.deps.ingestion"


@pytest.mark.asyncio
async def test_run_process_employees_chunk_opens_and_closes_its_own_session():
    batch_id = uuid.uuid4()
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    mock_worker = MagicMock()
    mock_worker.stream_and_process = AsyncMock()

    with (
        patch(f"{MODULE}.Session", MagicMock(return_value=session)) as session_cls,
        patch(f"{MODULE}.SqlUnitOfWork") as uow_cls,
        patch(f"{MODULE}.ProcessEmployeesChunkWorker", MagicMock(return_value=mock_worker)) as worker_cls,
        patch(f"{MODULE}.get_cache_client", MagicMock(return_value="cache")),
        patch(f"{MODULE}.get_storage", MagicMock(return_value="storage")),
    ):
        await run_process_employees_chunk(batch_id=batch_id)

    session_cls.assert_called_once()
    uow_cls.assert_called_once_with(session=session)
    worker_cls.assert_called_once_with(uow=uow_cls.return_value, cache_client="cache", storage="storage")
    mock_worker.stream_and_process.assert_awaited_once_with(batch_id=batch_id)
    session.__exit__.assert_called_once()


def test_get_process_employees_runner_returns_the_function():
    assert get_process_employees_runner() is run_process_employees_chunk
