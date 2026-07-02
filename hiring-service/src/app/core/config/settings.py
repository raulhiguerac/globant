import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # Storage
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "hiring")

    # Workers
    EMPLOYEE_CHUNK_SIZE: int = int(os.getenv("EMPLOYEE_CHUNK_SIZE", "10000"))

    # Cache keys invalidated on employee ingestion (Section 2 OLAP endpoints)
    METRICS_CACHE_KEYS: list[str] = [
        "hiring:metrics:hires_by_quarter",
        "hiring:metrics:departments_above_mean",
    ]
    CACHE_KEY_HIRES_BY_QUARTER: str = "hiring:metrics:hires_by_quarter"
    CACHE_KEY_DEPARTMENTS_ABOVE_MEAN: str = "hiring:metrics:departments_above_mean"

    # Metrics TTL — 8h, invalidación proactiva en cada ingesta de employees
    METRICS_CACHE_TTL: int = 3600 * 8

    class Config:
        env_file = ".env"


settings = Settings()
