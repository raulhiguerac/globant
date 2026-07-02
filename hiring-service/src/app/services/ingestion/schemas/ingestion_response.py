import uuid

from pydantic import BaseModel

from app.models.models import IngestionBatchStatus


class IngestionResponse(BaseModel):
    created_count: int
    errors: list[str]


class AcceptedResponse(BaseModel):
    batch_id: uuid.UUID


class BatchStatusResponse(BaseModel):
    batch_id: uuid.UUID
    status: IngestionBatchStatus
    errors: list[str]
