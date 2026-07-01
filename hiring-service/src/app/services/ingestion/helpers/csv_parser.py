import csv
import io
from datetime import datetime

from app.services.ingestion.schemas.department import DepartmentRecord
from app.services.ingestion.schemas.employee import EmployeeRecord
from app.services.ingestion.schemas.job import JobRecord


def parse_departments(raw: bytes) -> tuple[list[DepartmentRecord], list[str]]:
    records, errors = [], []
    for i, row in enumerate(csv.reader(io.StringIO(raw.decode())), start=1):
        try:
            records.append(DepartmentRecord(id=int(row[0]), department=row[1]))
        except Exception:
            errors.append(f"row {i}: invalid")
    return records, errors


def parse_jobs(raw: bytes) -> tuple[list[JobRecord], list[str]]:
    records, errors = [], []
    for i, row in enumerate(csv.reader(io.StringIO(raw.decode())), start=1):
        try:
            records.append(JobRecord(id=int(row[0]), job=row[1]))
        except Exception:
            errors.append(f"row {i}: invalid")
    return records, errors


def parse_employees(raw: bytes) -> tuple[list[EmployeeRecord], list[str]]:
    records, errors = [], []
    for i, row in enumerate(csv.reader(io.StringIO(raw.decode())), start=1):
        try:
            records.append(
                EmployeeRecord(
                    id=int(row[0]),
                    name=row[1],
                    hiring_datetime=datetime.fromisoformat(row[2]),
                    department_id=int(row[3]),
                    job_id=int(row[4]),
                )
            )
        except Exception:
            errors.append(f"row {i}: invalid")
    return records, errors
