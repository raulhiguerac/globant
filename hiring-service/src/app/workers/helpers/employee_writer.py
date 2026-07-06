import uuid
from functools import partial

from fastapi.concurrency import run_in_threadpool

from sqlalchemy.exc import OperationalError

from app.core.logging.logger import get_logger
from app.services.ingestion.helpers.db_error_translator import translate_db_error
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.employee import EmployeeRecord

logger = get_logger(__name__)


async def write_employees(*, uow: UnitOfWork, batch_id: uuid.UUID, records: list[EmployeeRecord]) -> list[str]:
    try:
        await run_in_threadpool(partial(uow.employees.bulk_insert, records=records, batch_id=batch_id))
        await uow.commit()
        return []
    except OperationalError as exc:
        await uow.rollback()
        logger.error("bulk_insert operational error", extra={"batch_id": str(batch_id)}, exc_info=exc)
        raise translate_db_error(exc) from exc
    except Exception as exc:
        await uow.rollback()
        logger.warning(
            "bulk_insert failed, falling back to row-by-row",
            extra={"batch_id": str(batch_id), "total": len(records)},
            exc_info=exc,
        )

    return await _write_row_by_row(uow=uow, batch_id=batch_id, records=records)


async def _write_row_by_row(*, uow: UnitOfWork, batch_id: uuid.UUID, records: list[EmployeeRecord]) -> list[str]:
    errors: list[str] = []

    for record in records:
        try:
            await uow.begin_nested()
            await run_in_threadpool(partial(uow.employees.add, record=record, batch_id=batch_id))
            await uow.commit()
        except OperationalError as exc:
            await uow.rollback()
            raise translate_db_error(exc) from exc
        except Exception as exc:
            await uow.rollback_to_savepoint()
            logger.warning(
                "failed to insert employee",
                extra={"employee_id": record.id, "employee_name": record.name},
                exc_info=exc,
            )
            errors.append(f"{record.id}:{record.name}")

    return errors
