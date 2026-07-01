from pydantic import BaseModel


class DepartmentRecord(BaseModel):
    id: int
    department: str
