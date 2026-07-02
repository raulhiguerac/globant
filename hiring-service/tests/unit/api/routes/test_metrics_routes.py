from unittest.mock import AsyncMock, MagicMock

from app.api.deps.metrics import get_departments_above_mean_uc, get_hires_by_quarter_uc

_QUARTERS_ROWS = [{"department": "Engineering", "job": "Quality Engineer", "Q1": 0, "Q2": 1, "Q3": 5, "Q4": 0}]
_MEAN_ROWS = [{"id": 7, "department": "Staff", "hired": 45}]


def test_hires_by_quarter_200(app, client):
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=_QUARTERS_ROWS)
    app.dependency_overrides[get_hires_by_quarter_uc] = lambda: mock_uc

    resp = client.get("/v1/metrics/hires-by-quarter")

    assert resp.status_code == 200
    assert resp.json() == _QUARTERS_ROWS

    app.dependency_overrides.clear()


def test_departments_above_mean_200(app, client):
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock(return_value=_MEAN_ROWS)
    app.dependency_overrides[get_departments_above_mean_uc] = lambda: mock_uc

    resp = client.get("/v1/metrics/departments-above-mean")

    assert resp.status_code == 200
    assert resp.json() == _MEAN_ROWS

    app.dependency_overrides.clear()
