from fastapi import APIRouter, Depends

from app.api.deps.metrics import get_departments_above_mean_uc, get_hires_by_quarter_uc
from app.services.metrics.use_cases.departments_above_mean import DepartmentsAboveMeanUseCase
from app.services.metrics.use_cases.hires_by_quarter import HiresByQuarterUseCase

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/hires-by-quarter", response_model=list[dict])
async def hires_by_quarter(
    uc: HiresByQuarterUseCase = Depends(get_hires_by_quarter_uc),
) -> list[dict]:
    return await uc.execute()


@router.get("/departments-above-mean", response_model=list[dict])
async def departments_above_mean(
    uc: DepartmentsAboveMeanUseCase = Depends(get_departments_above_mean_uc),
) -> list[dict]:
    return await uc.execute()
