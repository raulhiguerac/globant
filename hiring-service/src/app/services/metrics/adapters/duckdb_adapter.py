from app.integrations.duckdb.client import DuckDbClient
from app.services.metrics.ports.analytics_db import AnalyticsDb


class DuckDbAdapter(AnalyticsDb):
    def __init__(self, *, client: DuckDbClient) -> None:
        self._client = client

    def query(self, *, sql: str) -> list[dict]:
        return self._client.query(sql=sql)
