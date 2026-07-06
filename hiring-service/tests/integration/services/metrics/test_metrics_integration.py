import uuid
from datetime import datetime, timezone

import pytest

from app.integrations.duckdb.client import DuckDbClient
from app.models.models import Departments, Employees, IngestionBatch, IngestionBatchStatus, Jobs
from app.services.metrics.adapters.duckdb_adapter import DuckDbAdapter
from app.services.metrics.use_cases.departments_above_mean import DepartmentsAboveMeanUseCase
from app.services.metrics.use_cases.hires_by_quarter import HiresByQuarterUseCase


class NoOpCache:
    async def get_json(self, *, key):
        return None

    async def set_json(self, *, key, value, ttl=None):
        return None

    async def delete(self, *, key):
        return None


def _seed(real_session):
    batch_id = uuid.uuid4()
    real_session.add(IngestionBatch(id=batch_id, status=IngestionBatchStatus.completed))
    real_session.flush()
    real_session.add(Departments(id=1, department="Engineering", batch_id=batch_id))
    real_session.add(Departments(id=2, department="HR", batch_id=batch_id))
    real_session.add(Jobs(id=1, job="Recruiter", batch_id=batch_id))
    real_session.flush()
    real_session.add_all(
        [
            Employees(
                id=1, name="Ana", hiring_datetime=datetime(2021, 1, 15, tzinfo=timezone.utc),
                department_id=1, job_id=1, batch_id=batch_id,
            ),
            Employees(
                id=2, name="Beto", hiring_datetime=datetime(2021, 4, 10, tzinfo=timezone.utc),
                department_id=1, job_id=1, batch_id=batch_id,
            ),
            Employees(
                id=3, name="Caro", hiring_datetime=datetime(2021, 4, 20, tzinfo=timezone.utc),
                department_id=1, job_id=1, batch_id=batch_id,
            ),
            Employees(
                id=4, name="Dani", hiring_datetime=datetime(2021, 6, 1, tzinfo=timezone.utc),
                department_id=2, job_id=1, batch_id=batch_id,
            ),
        ]
    )
    real_session.commit()


@pytest.mark.asyncio
async def test_hires_by_quarter_real_data(real_session):
    _seed(real_session)
    db = DuckDbAdapter(client=DuckDbClient())
    uc = HiresByQuarterUseCase(db=db, cache_client=NoOpCache())

    result = await uc.execute()

    engineering = next(r for r in result if r["department"] == "Engineering")
    assert engineering["Q1"] == 1
    assert engineering["Q2"] == 2
    assert engineering["Q3"] == 0
    assert engineering["Q4"] == 0


@pytest.mark.asyncio
async def test_departments_above_mean_real_data(real_session):
    _seed(real_session)
    db = DuckDbAdapter(client=DuckDbClient())
    uc = DepartmentsAboveMeanUseCase(db=db, cache_client=NoOpCache())

    result = await uc.execute()

    # mean = (3 + 1) / 2 = 2 -> only Engineering (3 hires) is above the mean
    assert [r["department"] for r in result] == ["Engineering"]
    assert result[0]["hired"] == 3
