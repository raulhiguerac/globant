import os
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlmodel import Session
from testcontainers.postgres import PostgresContainer
from app.core.config.settings import settings

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
_ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "..", "src", "app", "alembic.ini")


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17") as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(postgres_container):
    url = postgres_container.get_connection_url(driver=None)
    os.environ["DATABASE_URL"] = url
    settings.DATABASE_URL = url

    cfg = Config(os.path.abspath(_ALEMBIC_INI))
    command.upgrade(cfg, "head")

    return url


@pytest.fixture(scope="session")
def engine(database_url):
    return create_engine(database_url)


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def real_session(engine):
    # Commits for real, so a second physical connection (DuckDB's ATTACH) can see it.
    session = Session(engine)

    yield session

    session.close()
    with engine.connect() as conn:
        for table in ("employees", "departments", "jobs", "ingestion_batches"):
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        conn.commit()
