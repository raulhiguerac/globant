from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workers.helpers.storage_reader import download_file


async def _agen(chunks):
    for chunk in chunks:
        yield chunk


@pytest.mark.asyncio
async def test_joins_streamed_chunks():
    storage = MagicMock()
    storage.stream_file = AsyncMock(return_value=_agen([b"id,name\n", b"1,Ana\n"]))

    raw = await download_file(storage=storage, bucket="bucket", key="employees/x.csv")

    assert raw == b"id,name\n1,Ana\n"
    storage.stream_file.assert_awaited_once_with(bucket="bucket", key="employees/x.csv")


@pytest.mark.asyncio
async def test_storage_error_propagates():
    storage = MagicMock()
    storage.stream_file = AsyncMock(side_effect=ConnectionError("storage down"))

    with pytest.raises(ConnectionError):
        await download_file(storage=storage, bucket="bucket", key="employees/x.csv")
