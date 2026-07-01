import uuid

from sqlmodel import Session

from sqlalchemy.dialects.postgresql import insert

from app.models.models import Jobs
from app.services.ingestion.ports.job_repository import JobRepository
from app.services.ingestion.schemas.job import JobRecord


class SqlJobRepository(JobRepository):

    def __init__(self, *, session: Session) -> None:
        self.session = session

    def bulk_insert(self, *, records: list[JobRecord], batch_id: uuid.UUID) -> None:
        stmt = insert(Jobs).values([
            {**n.model_dump(), "batch_id": batch_id} for n in records
        ])
        self.session.exec(stmt)
        self.session.flush()

    def add(self, *, record: JobRecord, batch_id: uuid.UUID) -> None:
        self.session.add(
            Jobs(
                id=record.id,
                job=record.job,
                batch_id=batch_id
            )
        )
        self.session.flush()
