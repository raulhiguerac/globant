from app.core.exceptions.base import BaseError


class AnalyticsUnavailableError(BaseError):
    def __init__(self, *, cause: Exception):
        super().__init__(
            message="Analytics engine unavailable, please retry later",
            code="ANALYTICS_UNAVAILABLE",
            cause=cause,
            http_status=503,
        )
