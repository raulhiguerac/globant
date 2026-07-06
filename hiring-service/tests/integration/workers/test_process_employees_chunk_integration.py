import uuid
from typing import AsyncIterator

import pytest

from app.models.models import Departments, Employees, IngestionBatch, IngestionBatchStatus, Jobs
from app.services.ingestion.adapters.sql_unit_of_work import SqlUnitOfWork
from app.workers.process_employees_chunk import ProcessEmployeesChunkWorker


class InMemoryStorage:
    def __init__(self, files: dict[str, bytes]):
        self._files = files

    async def upload_file(self, *, fileobj, bucket, key, extra_args=None):
        raise NotImplementedError

    async def stream_file(self, *, bucket: str, key: str) -> AsyncIterator[bytes]:
        data = self._files[key]

        async def _gen() -> AsyncIterator[bytes]:
            yield data

        return _gen()


class FailingStorage:
    async def upload_file(self, *, fileobj, bucket, key, extra_args=None):
        raise NotImplementedError

    async def stream_file(self, *, bucket: str, key: str) -> AsyncIterator[bytes]:
        raise ConnectionError("storage down")


class NoOpCache:
    async def get_json(self, *, key):
        return None

    async def set_json(self, *, key, value, ttl=None):
        return None

    async def delete(self, *, key):
        return None


@pytest.mark.asyncio
async def test_worker_happy_path_completes_and_persists_employees(session):
    seed_batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=seed_batch_id, status=IngestionBatchStatus.completed))
    session.flush()
    session.add(Departments(id=1, department="Engineering", batch_id=seed_batch_id))
    session.add(Jobs(id=1, job="Recruiter", batch_id=seed_batch_id))
    session.commit()

    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.commit()

    csv_bytes = b"1,Ana,2021-03-03T10:00:00Z,1,1\n"
    storage = InMemoryStorage({f"employees/{batch_id}.csv": csv_bytes})
    worker = ProcessEmployeesChunkWorker(
        uow=SqlUnitOfWork(session=session), cache_client=NoOpCache(), storage=storage
    )

    await worker.stream_and_process(batch_id=batch_id)

    session.expire_all()
    batch = session.get(IngestionBatch, batch_id)
    assert batch.status == IngestionBatchStatus.completed
    assert batch.errors == []
    assert session.get(Employees, 1).name == "Ana"


@pytest.mark.asyncio
async def test_worker_storage_error_marks_batch_failed_in_db(session):
    batch_id = uuid.uuid4()
    session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.pending))
    session.commit()

    worker = ProcessEmployeesChunkWorker(
        uow=SqlUnitOfWork(session=session), cache_client=NoOpCache(), storage=FailingStorage()
    )

    with pytest.raises(ConnectionError):
        await worker.stream_and_process(batch_id=batch_id)

    session.expire_all()
    assert session.get(IngestionBatch, batch_id).status == IngestionBatchStatus.failed
