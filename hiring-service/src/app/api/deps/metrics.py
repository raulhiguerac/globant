from functools import lru_cache

from fastapi import Depends

from app.api.deps.shared import get_cache_client
from app.integrations.duckdb.client import DuckDbClient
from app.services.metrics.adapters.duckdb_adapter import DuckDbAdapter
from app.services.metrics.ports.analytics_db import AnalyticsDb
from app.services.metrics.use_cases.departments_above_mean import DepartmentsAboveMeanUseCase
from app.services.metrics.use_cases.hires_by_quarter import HiresByQuarterUseCase
from app.services.shared.ports.cache import CachePort


@lru_cache
def _analytics_db() -> DuckDbAdapter:
    return DuckDbAdapter(client=DuckDbClient())


def get_analytics_db() -> AnalyticsDb:
    return _analytics_db()


def get_hires_by_quarter_uc(
    db: AnalyticsDb = Depends(get_analytics_db),
    cache_client: CachePort = Depends(get_cache_client),
) -> HiresByQuarterUseCase:
    return HiresByQuarterUseCase(db=db, cache_client=cache_client)


def get_departments_above_mean_uc(
    db: AnalyticsDb = Depends(get_analytics_db),
    cache_client: CachePort = Depends(get_cache_client),
) -> DepartmentsAboveMeanUseCase:
    return DepartmentsAboveMeanUseCase(db=db, cache_client=cache_client)
