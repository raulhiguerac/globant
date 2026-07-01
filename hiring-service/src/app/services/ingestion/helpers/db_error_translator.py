import re

from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.exceptions.ingestion import (
    IngestionDbUnavailableError,
    RecordConflictError,
    RecordForeignKeyError,
)

# PK constraint name → table name
_PK_MAP = {
    "departments_pkey": "departments",
    "jobs_pkey": "jobs",
    "employees_pkey": "employees",
}

# FK constraint name → field name
_FK_MAP = {
    "employees_department_id_fkey": "department_id",
    "employees_job_id_fkey": "job_id",
}


def _parse_constraint(exc: IntegrityError) -> str:
    match = re.search(r'constraint "(.+?)"', str(exc))
    return match.group(1) if match else ""


def _parse_fk_value(exc: IntegrityError) -> str:
    match = re.search(r"Key \(.+?\)=\((.+?)\)", str(exc))
    return match.group(1) if match else "unknown"


def _parse_pk_id(exc: IntegrityError) -> int:
    match = re.search(r"Key \(id\)=\((\d+)\)", str(exc))
    return int(match.group(1)) if match else -1


def translate_db_error(exc: Exception) -> Exception:
    if isinstance(exc, IntegrityError):
        constraint = _parse_constraint(exc)
        if constraint in _PK_MAP:
            return RecordConflictError(table=_PK_MAP[constraint], record_id=_parse_pk_id(exc))
        if constraint in _FK_MAP:
            field = _FK_MAP[constraint]
            return RecordForeignKeyError(field=field, value=_parse_fk_value(exc))
        return exc

    if isinstance(exc, OperationalError):
        return IngestionDbUnavailableError(cause=exc)

    return exc
