import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.workers.helpers.employee_writer import write_employees

MODULE = "app.workers.helpers.employee_writer.run_in_threadpool"


async def _passthrough(fn):
    return fn()


def _make_uow():
    uow = MagicMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.begin_nested = AsyncMock()
    uow.rollback_to_savepoint = AsyncMock()
    return uow


def _record(id_=1, name="Ana"):
    record = MagicMock()
    record.id = id_
    record.name = name
    return record


@pytest.mark.asyncio
async def test_bulk_insert_happy_path_returns_no_errors():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    records = [_record(1), _record(2)]

    with patch(MODULE, side_effect=_passthrough):
        errors = await write_employees(uow=uow, batch_id=batch_id, records=records)

    assert errors == []
    uow.employees.bulk_insert.assert_called_once_with(records=records, batch_id=batch_id)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_insert_operational_error_raises_translated():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    uow.employees.bulk_insert = MagicMock(side_effect=OperationalError("db down", {}, Exception()))

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(Exception):
            await write_employees(uow=uow, batch_id=batch_id, records=[_record()])

    uow.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_bulk_insert_generic_error_falls_back_to_row_by_row():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    uow.employees.bulk_insert = MagicMock(side_effect=ValueError("bad row"))
    records = [_record(1), _record(2)]

    with patch(MODULE, side_effect=_passthrough):
        errors = await write_employees(uow=uow, batch_id=batch_id, records=records)

    assert errors == []
    assert uow.employees.add.call_count == 2


@pytest.mark.asyncio
async def test_row_by_row_collects_errors_for_failing_records():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    uow.employees.bulk_insert = MagicMock(side_effect=ValueError("bad batch"))
    uow.employees.add = MagicMock(side_effect=[None, ValueError("bad row")])
    records = [_record(1, "Ana"), _record(2, "Beto")]

    with patch(MODULE, side_effect=_passthrough):
        errors = await write_employees(uow=uow, batch_id=batch_id, records=records)

    assert errors == ["2:Beto"]
    uow.rollback_to_savepoint.assert_awaited_once()


@pytest.mark.asyncio
async def test_row_by_row_operational_error_raises_translated():
    batch_id = uuid.uuid4()
    uow = _make_uow()
    uow.employees.bulk_insert = MagicMock(side_effect=ValueError("bad batch"))
    uow.employees.add = MagicMock(side_effect=OperationalError("db down", {}, Exception()))

    with patch(MODULE, side_effect=_passthrough):
        with pytest.raises(Exception):
            await write_employees(uow=uow, batch_id=batch_id, records=[_record()])
