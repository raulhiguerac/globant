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

    class Config:
        env_file = ".env"


settings = Settings()
