import json
import os

from redis import asyncio as aioredis

from app.core.exceptions.cache import CacheMisconfiguredError
from app.core.logging.logger import get_logger
from app.integrations.cache.redis.mappers.error_mapper import log_cache_error

logger = get_logger(__name__)


class CacheClient:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        if not self.redis_url:
            raise CacheMisconfiguredError(context={"missing": "REDIS_URL"})

        self.client = aioredis.from_url(
            url=self.redis_url,
            decode_responses=True,
        )

    async def get_json(self, key: str) -> dict | list | None:
        try:
            payload = await self.client.get(key)
            return json.loads(payload) if payload is not None else None
        except Exception as exc:
            log_cache_error(exc=exc, operation="get_json", key=key)
            return None

    async def set_json(self, key: str, value: dict | list, ttl: int | None = None) -> None:
        try:
            payload = json.dumps(value)
            if ttl is not None:
                await self.client.setex(key, ttl, payload)
            else:
                await self.client.set(key, payload)
        except Exception as exc:
            log_cache_error(exc=exc, operation="set_json", key=key, payload_type=type(value).__name__)

    async def delete(self, key: str | list[str]) -> None:
        try:
            keys = key if isinstance(key, list) else [key]
            await self.client.delete(*keys)
        except Exception as exc:
            log_cache_error(exc=exc, operation="delete", key=key)
