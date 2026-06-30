from fastapi import APIRouter

from collectors.collector_preview import preview_single_collector
from collectors.collector_runner import run_enabled_collectors, run_single_collector


router = APIRouter(prefix="/collectors", tags=["collectors"])


@router.post("/run")
def run_collectors() -> list[dict]:
    """运行所有启用的数据源采集器。"""
    return run_enabled_collectors()


@router.post("/run-source/{source_id}")
def run_collector_source(source_id: int) -> dict:
    """只运行指定数据源的采集器，用于真实数据源专项调试。"""
    return run_single_collector(source_id)


@router.post("/preview-source/{source_id}")
def preview_collector_source(source_id: int) -> dict:
    """预览指定数据源的解析结果，不写入 raw 数据，也不生成采集日志。"""
    return preview_single_collector(source_id)
