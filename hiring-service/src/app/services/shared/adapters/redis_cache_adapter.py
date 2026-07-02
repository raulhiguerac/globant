from app.integrations.cache.redis.cache import CacheClient
from app.services.shared.ports.cache import CachePort


class RedisCacheAdapter(CachePort):
    def __init__(self, *, client: CacheClient) -> None:
        self._client = client

    async def get_json(self, *, key: str) -> dict | list | None:
        return await self._client.get_json(key)

    async def set_json(self, *, key: str, value: dict | list, ttl: int | None = None) -> None:
        await self._client.set_json(key, value, ttl)

    async def delete(self, *, key: str | list[str]) -> None:
        await self._client.delete(key)
