from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.cache.redis.cache import CacheClient

MODULE = "app.integrations.cache.redis.cache"


def _make_client():
    with patch(f"{MODULE}.aioredis.from_url", MagicMock(return_value=MagicMock())):
        return CacheClient()


@pytest.mark.asyncio
async def test_delete_succeeds_on_first_try_without_sleeping():
    client = _make_client()
    client.client.delete = AsyncMock()

    with patch(f"{MODULE}.asyncio.sleep", AsyncMock()) as sleep:
        await client.delete("key")

    client.client.delete.assert_awaited_once_with("key")
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_retries_with_backoff_then_succeeds():
    client = _make_client()
    client.client.delete = AsyncMock(side_effect=[ConnectionError("down"), ConnectionError("down"), None])

    with patch(f"{MODULE}.asyncio.sleep", AsyncMock()) as sleep:
        await client.delete("key")

    assert client.client.delete.await_count == 3
    sleep.assert_any_call(15)
    sleep.assert_any_call(30)


@pytest.mark.asyncio
async def test_delete_gives_up_and_logs_after_exhausting_retries():
    client = _make_client()
    client.client.delete = AsyncMock(side_effect=ConnectionError("down"))

    with (
        patch(f"{MODULE}.asyncio.sleep", AsyncMock()),
        patch(f"{MODULE}.log_cache_error") as log_cache_error,
    ):
        await client.delete("key")

    assert client.client.delete.await_count == 3
    log_cache_error.assert_called_once()
