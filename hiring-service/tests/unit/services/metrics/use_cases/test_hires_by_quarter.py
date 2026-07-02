from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions.metrics import AnalyticsUnavailableError
from app.services.metrics.use_cases.hires_by_quarter import HiresByQuarterUseCase

MODULE = "app.services.metrics.use_cases.hires_by_quarter.run_in_threadpool"

_ROWS = [{"department": "Engineering", "job": "Quality Engineer", "Q1": 0, "Q2": 1, "Q3": 5, "Q4": 0}]


def _make_deps():
    db = MagicMock()
    db.query = MagicMock(return_value=_ROWS)
    cache_client = MagicMock()
    cache_client.get_json = AsyncMock(return_value=None)
    cache_client.set_json = AsyncMock()
    return db, cache_client


async def _passthrough(fn, **kwargs):
    return fn(**kwargs)


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_result():
    db, cache_client = _make_deps()
    cache_client.get_json = AsyncMock(return_value=_ROWS)
    uc = HiresByQuarterUseCase(db=db, cache_client=cache_client)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute()

    assert result == _ROWS
    db.query.assert_not_called()
    cache_client.set_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_miss_queries_db_and_caches():
    db, cache_client = _make_deps()
    uc = HiresByQuarterUseCase(db=db, cache_client=cache_client)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute()

    assert result == _ROWS
    db.query.assert_called_once()
    cache_client.set_json.assert_awaited_once()
    _, kwargs = cache_client.set_json.call_args
    assert kwargs["value"] == _ROWS


@pytest.mark.asyncio
async def test_db_error_raises_analytics_unavailable():
    db, cache_client = _make_deps()
    db.query = MagicMock(side_effect=RuntimeError("duckdb down"))
    uc = HiresByQuarterUseCase(db=db, cache_client=cache_client)

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(AnalyticsUnavailableError):
            await uc.execute()

    cache_client.set_json.assert_not_awaited()
