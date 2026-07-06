import uuid
from functools import partial

from fastapi.concurrency import run_in_threadpool

from app.core.config.settings import settings
from app.core.logging.logger import get_logger
from app.models.models import IngestionBatchStatus
from app.services.ingestion.ports.unit_of_work import UnitOfWork
from app.services.shared.ports.cache import CachePort

logger = get_logger(__name__)


async def mark_batch_failed(*, uow: UnitOfWork, batch_id: uuid.UUID) -> None:
    try:
        await uow.rollback()
        await run_in_threadpool(
            partial(uow.batch.update_status, batch_id=batch_id, status=IngestionBatchStatus.failed)
        )
        await uow.commit()
    except Exception as exc:
        await uow.rollback()
        logger.error("failed to mark batch as failed", extra={"batch_id": str(batch_id)}, exc_info=exc)


async def finalize_batch(
    *, uow: UnitOfWork, cache_client: CachePort, batch_id: uuid.UUID, errors: list[str]
) -> None:
    await run_in_threadpool(
        partial(
            uow.batch.update_status,
            batch_id=batch_id,
            status=IngestionBatchStatus.completed,
            errors=errors,
        )
    )
    await uow.commit()
    await cache_client.delete(key=settings.METRICS_CACHE_KEYS)
