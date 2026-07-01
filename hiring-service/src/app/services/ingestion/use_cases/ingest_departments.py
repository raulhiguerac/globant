import uuid
from functools import partial
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import OperationalError

from app.core.logging.logger import get_logger
from app.models.models import IngestionBatchStatus
from app.services.ingestion.helpers.db_error_translator import translate_db_error
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.schemas.ingestion_response import IngestionResponse

logger = get_logger(__name__)


class IngestDepartmentsUseCase:
    def __init__(self, *, uow: UnitOfWork):
        self.uow = uow

    async def execute(self, *, records: list[DepartmentRecord]) -> IngestionResponse:
        batch_ingestion_id = uuid.uuid4()
        try:
            await run_in_threadpool(
                partial(self.uow.batch.add, batch_id=batch_ingestion_id, status=IngestionBatchStatus.pending)
            )
            await run_in_threadpool(
                partial(
                    self.uow.departments.bulk_insert,
                    records=records,
                    batch_id=batch_ingestion_id,
                )
            )
            await run_in_threadpool(
                partial(self.uow.batch.update_status, batch_id=batch_ingestion_id, status=IngestionBatchStatus.completed)
            )
            await self.uow.commit()
            return IngestionResponse(created_count=len(records), errors=[])
        except OperationalError as exc:
            await self.uow.rollback()
            raise translate_db_error(exc) from exc
        except Exception as exc:
            await self.uow.rollback()
            logger.warning(
                "bulk_insert failed, falling back to row-by-row",
                extra={"total": len(records)},
                exc_info=exc,
            )

        errors: list[str] = []
        ok_count = 0

        await run_in_threadpool(
            partial(self.uow.batch.add, batch_id=batch_ingestion_id, status=IngestionBatchStatus.pending)
        )

        for record in records:
            try:
                await self.uow.begin_nested()
                await run_in_threadpool(
                    partial(self.uow.departments.add, record=record, batch_id=batch_ingestion_id)
                )
                ok_count += 1
            except OperationalError as exc:
                raise translate_db_error(exc) from exc
            except Exception as exc:
                await self.uow.rollback_to_savepoint()
                logger.warning(
                    "failed to insert department",
                    extra={"department_id": record.id, "department": record.department},
                    exc_info=exc,
                )
                errors.append(f"{record.id}:{record.department}")

        if ok_count:
            await run_in_threadpool(
                partial(self.uow.batch.update_status, batch_id=batch_ingestion_id, status=IngestionBatchStatus.completed)
            )
            await self.uow.commit()

        return IngestionResponse(created_count=ok_count, errors=errors)
