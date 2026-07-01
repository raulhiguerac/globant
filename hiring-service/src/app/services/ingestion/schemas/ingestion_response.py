import uuid

from pydantic import BaseModel


class IngestionResponse(BaseModel):
    created_count: int
    errors: list[str]


class AcceptedResponse(BaseModel):
    batch_id: uuid.UUID
