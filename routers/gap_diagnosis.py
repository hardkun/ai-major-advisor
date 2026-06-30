"""缺口诊断本地管理接口。"""

from fastapi import APIRouter, HTTPException, Query

from services.gap_diagnosis_service import (
    generate_gap_diagnosis_report,
    get_latest_gap_diagnosis_report,
)


router = APIRouter(prefix="/gap-diagnosis", tags=["gap-diagnosis"])


@router.post("/generate")
def generate_gap_diagnosis(
    province: str = Query(default="四川"),
    year: int = Query(default=2025),
) -> dict:
    return generate_gap_diagnosis_report(province=province, year=year)


@router.get("/latest")
def latest_gap_diagnosis() -> dict:
    report = get_latest_gap_diagnosis_report()
    if not report:
        raise HTTPException(status_code=404, detail="暂无缺口诊断报告")
    return report
