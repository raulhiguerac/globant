from datetime import datetime

from pydantic import BaseModel


class EmployeeRecord(BaseModel):
    id: int
    name: str
    hiring_datetime: datetime
    department_id: int
    job_id: int
