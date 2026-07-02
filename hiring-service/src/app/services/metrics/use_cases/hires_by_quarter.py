from pathlib import Path

from fastapi.concurrency import run_in_threadpool
from jinja2 import Template

from app.core.config.settings import settings
from app.core.exceptions.metrics import AnalyticsUnavailableError
from app.core.logging.logger import get_logger
from app.services.metrics.ports.analytics_db import AnalyticsDb
from app.services.shared.ports.cache import CachePort

logger = get_logger(__name__)

_TEMPLATE = Template(
    (Path(__file__).parent.parent / "helpers" / "hires_by_quarter.sql.jinja").read_text()
)

_QUARTERS = [
    {"name": "Q1", "month_start": 1, "month_end": 3},
    {"name": "Q2", "month_start": 4, "month_end": 6},
    {"name": "Q3", "month_start": 7, "month_end": 9},
    {"name": "Q4", "month_start": 10, "month_end": 12},
]


class HiresByQuarterUseCase:
    def __init__(self, *, db: AnalyticsDb, cache_client: CachePort):
        self.db = db
        self.cache_client = cache_client

    async def execute(self) -> list[dict]:
        cache_key = settings.CACHE_KEY_HIRES_BY_QUARTER
        result = await self.cache_client.get_json(key=cache_key)
        if result is not None:
            return result

        sql = _TEMPLATE.render(quarters=_QUARTERS)

        try:
            result = await run_in_threadpool(self.db.query, sql=sql)
        except Exception as exc:
            logger.error("analytics query failed", exc_info=exc)
            raise AnalyticsUnavailableError(cause=exc) from exc

        await self.cache_client.set_json(key=cache_key, value=result, ttl=settings.METRICS_CACHE_TTL)
        return result
