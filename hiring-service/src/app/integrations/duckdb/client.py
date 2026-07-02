import duckdb

from app.core.config.settings import settings
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class DuckDbClient:
    def __init__(self) -> None:
        logger.info("initializing DuckDB client")
        self._conn = duckdb.connect()

        try:
            self._conn.execute("INSTALL postgres;")
            logger.info("postgres extension installed")
            self._conn.execute("LOAD postgres;")
            logger.info("postgres extension loaded")
        except Exception as exc:
            logger.error("failed to load postgres extension", exc_info=exc)
            raise

        try:
            self._conn.execute(
                f"ATTACH '{settings.DATABASE_URL}' AS pg (TYPE postgres, READ_ONLY);"
            )
            logger.info("postgres attached as pg", extra={"url": settings.DATABASE_URL})
        except Exception as exc:
            logger.error("failed to attach postgres", exc_info=exc)
            raise

    def query(self, *, sql: str) -> list[dict]:
        logger.debug("executing analytics query", extra={"sql": sql[:120]})
        result = self._conn.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        logger.info("analytics query returned rows", extra={"count": len(rows)})
        return rows
