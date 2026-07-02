from pydantic import BaseModel


class JobRecord(BaseModel):
    id: int
    job: str
