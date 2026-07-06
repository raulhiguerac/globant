import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions.ingestion import RecordConflictError, RecordForeignKeyError
from app.models.models import Departments, Employees, IngestionBatch, IngestionBatchStatus
from app.services.ingestion.helpers.db_error_translator import translate_db_error


def test_translate_db_error_real_pk_violation_returns_record_conflict_error(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.flush()
    session.add(Departments(id=1, department="Engineering", batch_id=batch_id))
    session.commit()

    session.add(Departments(id=1, department="Duplicated", batch_id=batch_id))
    with pytest.raises(IntegrityError) as exc_info:
        session.commit()
    session.rollback()

    translated = translate_db_error(exc_info.value)

    assert isinstance(translated, RecordConflictError)
    assert translated.context == {"table": "departments", "id": 1}


def test_translate_db_error_real_fk_violation_returns_record_foreign_key_error(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.flush()
    session.add(Departments(id=1, department="Engineering", batch_id=batch_id))
    session.commit()

    session.add(
        Employees(
            id=1,
            name="Ana",
            hiring_datetime=datetime(2021, 3, 3, tzinfo=timezone.utc),
            department_id=1,
            job_id=999,
            batch_id=batch_id,
        )
    )
    with pytest.raises(IntegrityError) as exc_info:
        session.commit()
    session.rollback()

    translated = translate_db_error(exc_info.value)

    assert isinstance(translated, RecordForeignKeyError)
    assert translated.context == {"field": "job_id", "value": "999"}
