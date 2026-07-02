import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.exceptions.ingestion import IngestionDbUnavailableError, RecordConflictError, RecordForeignKeyError
from app.services.ingestion.helpers.db_error_translator import translate_db_error


def _integrity(msg: str) -> IntegrityError:
    return IntegrityError(msg, {}, Exception())


def _operational() -> OperationalError:
    return OperationalError("connection refused", {}, Exception())


def test_pk_violation_departments():
    exc = _integrity('duplicate key value violates unique constraint "departments_pkey"\nDETAIL: Key (id)=(5) already exists.')
    result = translate_db_error(exc)
    assert isinstance(result, RecordConflictError)
    assert result.context["table"] == "departments"
    assert result.context["id"] == 5


def test_pk_violation_jobs():
    exc = _integrity('duplicate key value violates unique constraint "jobs_pkey"\nDETAIL: Key (id)=(10) already exists.')
    result = translate_db_error(exc)
    assert isinstance(result, RecordConflictError)
    assert result.context["table"] == "jobs"


def test_pk_violation_employees():
    exc = _integrity('duplicate key value violates unique constraint "employees_pkey"\nDETAIL: Key (id)=(99) already exists.')
    result = translate_db_error(exc)
    assert isinstance(result, RecordConflictError)
    assert result.context["table"] == "employees"


def test_fk_violation_department_id():
    exc = _integrity('insert or update on table "employees" violates foreign key constraint "employees_department_id_fkey"\nDETAIL: Key (department_id)=(999) is not present in table "departments".')
    result = translate_db_error(exc)
    assert isinstance(result, RecordForeignKeyError)
    assert result.context["field"] == "department_id"


def test_fk_violation_job_id():
    exc = _integrity('insert or update on table "employees" violates foreign key constraint "employees_job_id_fkey"\nDETAIL: Key (job_id)=(42) is not present in table "jobs".')
    result = translate_db_error(exc)
    assert isinstance(result, RecordForeignKeyError)
    assert result.context["field"] == "job_id"


def test_operational_error_returns_unavailable():
    result = translate_db_error(_operational())
    assert isinstance(result, IngestionDbUnavailableError)


def test_unknown_integrity_error_returned_as_is():
    exc = _integrity('some unknown constraint "unknown_constraint"')
    result = translate_db_error(exc)
    assert isinstance(result, IntegrityError)
