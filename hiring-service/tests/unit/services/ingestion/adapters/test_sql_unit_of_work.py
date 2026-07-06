from unittest.mock import MagicMock

import pytest

from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork


@pytest.mark.asyncio
async def test_rollback_to_savepoint_without_begin_nested_is_a_safe_noop():
    uow = SqlUnitOfWork(session=MagicMock())

    await uow.rollback_to_savepoint()


@pytest.mark.asyncio
async def test_rollback_to_savepoint_rolls_back_and_clears_after_begin_nested():
    session = MagicMock()
    savepoint = MagicMock()
    session.begin_nested = MagicMock(return_value=savepoint)
    uow = SqlUnitOfWork(session=session)

    await uow.begin_nested()
    await uow.rollback_to_savepoint()

    savepoint.rollback.assert_called_once()
    assert uow._savepoint is None
