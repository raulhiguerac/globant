import os
import time

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from app.core.config.settings import settings
from app.integrations.duckdb.client import DuckDbClient

_ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "app", "alembic.ini")


def _wait_until_postgres_is_up(database_url: str, timeout_seconds: float = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_exc = None
    while time.monotonic() < deadline:
        try:
            psycopg2.connect(database_url).close()
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(0.5)
    pytest.fail(f"postgres did not come back up after restart: {last_exc}")


def test_duckdb_client_reconnects_after_postgres_restart(database_url):
    # Dedicated container (restarting it must not affect other tests) with a pinned
    # host port (Docker reassigns a random one on restart otherwise, unlike prod).
    with PostgresContainer("postgres:17").with_bind_ports(5432, 55432) as pg:
        isolated_url = pg.get_connection_url(driver=None)
        os.environ["DATABASE_URL"] = isolated_url
        settings.DATABASE_URL = isolated_url
        try:
            cfg = Config(os.path.abspath(_ALEMBIC_INI))
            command.upgrade(cfg, "head")

            client = DuckDbClient()
            assert client.query(sql="SELECT 1 AS one") == [{"one": 1}]

            pg.get_wrapped_container().restart()
            _wait_until_postgres_is_up(isolated_url)

            assert client.query(sql="SELECT 1 AS one") == [{"one": 1}]
        finally:
            os.environ["DATABASE_URL"] = database_url
            settings.DATABASE_URL = database_url
