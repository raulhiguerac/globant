from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from app.core.config.settings import settings
from app.core.exceptions.metrics import AnalyticsUnavailableError
from app.core.logging.logger import get_logger
from app.services.metrics.ports.analytics_db import AnalyticsDb
from app.services.shared.ports.cache import CachePort

logger = get_logger(__name__)

_SQL = (Path(__file__).parent.parent / "helpers" / "departments_above_mean.sql").read_text()


class DepartmentsAboveMeanUseCase:
    def __init__(self, *, db: AnalyticsDb, cache_client: CachePort):
        self.db = db
        self.cache_client = cache_client

    async def execute(self) -> list[dict]:
        cache_key = settings.CACHE_KEY_DEPARTMENTS_ABOVE_MEAN
        result = await self.cache_client.get_json(key=cache_key)
        if result is not None:
            return result

        try:
            result = await run_in_threadpool(self.db.query, sql=_SQL)
        except Exception as exc:
            logger.error("analytics query failed", exc_info=exc)
            raise AnalyticsUnavailableError(cause=exc) from exc

        await self.cache_client.set_json(key=cache_key, value=result, ttl=settings.METRICS_CACHE_TTL)
        return result
