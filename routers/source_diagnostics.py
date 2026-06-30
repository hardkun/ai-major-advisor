"""数据源归属、诊断和处理队列接口。"""

from fastapi import APIRouter, Query

from services.action_queue_service import generate_source_action_queue
from services.collect_diagnosis_service import diagnose_sources_without_records
from services.source_backfill_service import backfill_raw_data_source_school_names


router = APIRouter(prefix="/source-diagnostics", tags=["source-diagnostics"])


@router.post("/backfill-school-names")
def backfill_school_names() -> dict:
    return backfill_raw_data_source_school_names()


@router.post("/diagnose-without-records")
def diagnose_without_records(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return diagnose_sources_without_records(limit=limit)


@router.post("/action-queue")
def create_action_queue() -> dict:
    return generate_source_action_queue()


@router.get("/action-queue")
def get_action_queue() -> dict:
    return generate_source_action_queue()
