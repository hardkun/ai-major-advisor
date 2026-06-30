import json

from fastapi import APIRouter, HTTPException

from crud.reports import get_report_by_id, mark_report_paid
from schemas.reports import ReportResponse


router = APIRouter(prefix="/reports", tags=["reports"])


def build_report_response(report: dict) -> ReportResponse:
    """将数据库中的 JSON 字符串转换为接口响应。"""
    is_paid = bool(report["is_paid"])
    return ReportResponse(
        id=report["id"],
        log_id=report["log_id"],
        free_result=json.loads(report["free_result_json"]),
        paid_result=(
            json.loads(report["paid_result_json"])
            if is_paid
            else None
        ),
        is_paid=is_paid,
        created_at=report["created_at"],
        updated_at=report["updated_at"],
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int) -> ReportResponse:
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return build_report_response(report)


@router.post("/{report_id}/mock-pay", response_model=ReportResponse)
def mock_pay_report(report_id: int) -> ReportResponse:
    if not mark_report_paid(report_id):
        raise HTTPException(status_code=404, detail="报告不存在")

    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return build_report_response(report)
