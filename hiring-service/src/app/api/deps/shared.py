from functools import lru_cache

from app.integrations.cache.redis.cache import CacheClient
# For local development with MinIO, swap this import:
# from app.integrations.storage.minio.storage import StorageClient
from app.integrations.storage.gcs.storage import StorageClient
from app.services.shared.adapters.redis_cache_adapter import RedisCacheAdapter
from app.services.shared.adapters.storage_adapter import StorageAdapter
from app.services.shared.ports.cache import CachePort
from app.services.shared.ports.storage import StoragePort


@lru_cache
def _cache_client() -> RedisCacheAdapter:
    return RedisCacheAdapter(client=CacheClient())


@lru_cache
def _storage() -> StorageAdapter:
    return StorageAdapter(client=StorageClient())


def get_cache_client() -> CachePort:
    return _cache_client()


def get_storage() -> StoragePort:
    return _storage()
