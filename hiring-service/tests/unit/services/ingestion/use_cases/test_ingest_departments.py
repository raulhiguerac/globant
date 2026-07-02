from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.exceptions.ingestion import IngestionDbUnavailableError
from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.use_cases.ingest_departments import IngestDepartmentsUseCase

MODULE = "app.services.ingestion.use_cases.ingest_departments.run_in_threadpool"


def _make_uow():
    uow = MagicMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.begin_nested = AsyncMock()
    uow.rollback_to_savepoint = AsyncMock()
    return uow


def _records(n: int = 2) -> list[DepartmentRecord]:
    return [DepartmentRecord(id=i, department=f"Dept {i}") for i in range(1, n + 1)]


async def _passthrough(fn):
    fn()


@pytest.mark.asyncio
async def test_happy_path_bulk_insert():
    uow = _make_uow()
    uc = IngestDepartmentsUseCase(uow=uow)
    records = _records(3)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(records=records)

    assert result.created_count == 3
    assert result.errors == []
    uow.commit.assert_awaited_once()
    uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_fallback_row_by_row_all_ok():
    uow = _make_uow()
    uow.departments.bulk_insert = MagicMock(side_effect=IntegrityError("bulk", {}, Exception()))
    uc = IngestDepartmentsUseCase(uow=uow)
    records = _records(2)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(records=records)

    assert result.created_count == 2
    assert result.errors == []
    uow.rollback.assert_awaited_once()
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_row_by_row_partial_failures():
    uow = _make_uow()
    uow.departments.bulk_insert = MagicMock(side_effect=IntegrityError("bulk", {}, Exception()))

    row_call = 0

    def failing_add(**kwargs):
        nonlocal row_call
        row_call += 1
        if row_call == 2:
            raise IntegrityError("row", {}, Exception())

    uow.departments.add = failing_add
    uc = IngestDepartmentsUseCase(uow=uow)
    records = _records(3)

    with patch(MODULE, side_effect=_passthrough):
        result = await uc.execute(records=records)

    assert result.created_count == 2
    assert len(result.errors) == 1
    assert "2:Dept 2" in result.errors[0]
    uow.rollback_to_savepoint.assert_awaited_once()


@pytest.mark.asyncio
async def test_operational_error_raises():
    uow = _make_uow()
    uow.batch.add = MagicMock(side_effect=OperationalError("db down", {}, Exception()))
    uc = IngestDepartmentsUseCase(uow=uow)
    records = _records(2)

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(IngestionDbUnavailableError):
            await uc.execute(records=records)

    uow.rollback.assert_awaited_once()
