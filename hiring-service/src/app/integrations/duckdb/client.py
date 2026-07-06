import duckdb

from app.core.config.settings import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class DuckDbClient:
    def __init__(self) -> None:
        self._conn = self._connect()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        logger.info("initializing DuckDB client")
        conn = duckdb.connect()

        try:
            conn.execute("INSTALL postgres;")
            conn.execute("LOAD postgres;")
            conn.execute(f"ATTACH '{settings.DATABASE_URL}' AS pg (TYPE postgres, READ_ONLY);")
            logger.info("postgres attached as pg")
        except Exception as exc:
            logger.error("failed to attach postgres", exc_info=exc)
            raise

        return conn

    def query(self, *, sql: str) -> list[dict]:
        try:
            return self._execute(sql=sql)
        except Exception as exc:
            logger.warning("analytics query failed, reconnecting to postgres", exc_info=exc)
            self._conn = self._connect()
            return self._execute(sql=sql)

    def _execute(self, *, sql: str) -> list[dict]:
        logger.debug("executing analytics query", extra={"sql": sql[:120]})
        result = self._conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        logger.info("analytics query returned rows", extra={"count": len(rows)})
        return rows
