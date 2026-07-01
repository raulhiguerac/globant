from app.core.exceptions.base import BaseError


class RecordConflictError(BaseError):
    def __init__(self, *, table: str, record_id: int):
        super().__init__(
            message=f"Record {record_id} already exists in {table}",
            code="RECORD_CONFLICT",
            context={"table": table, "id": record_id},
            http_status=409,
        )


class RecordForeignKeyError(BaseError):
    def __init__(self, *, field: str, value: str):
        super().__init__(
            message=f"Foreign key violation: {field}={value} does not exist",
            code="RECORD_FK_VIOLATION",
            context={"field": field, "value": value},
            http_status=422,
        )


class IngestionDbUnavailableError(BaseError):
    def __init__(self, *, cause: Exception):
        super().__init__(
            message="Database unavailable",
            code="DB_UNAVAILABLE",
            cause=cause,
            http_status=503,
        )
