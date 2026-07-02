from typing import Protocol


class AnalyticsDb(Protocol):
    def query(self, *, sql: str) -> list[dict]: ...
