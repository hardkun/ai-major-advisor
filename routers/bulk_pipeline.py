"""全量数据工程本地管理接口。

这些接口用于本地管理后台演示。正式上线前需要增加管理员权限保护。
"""

from fastapi import APIRouter, Query

from services.bulk_source_pipeline import (
    reset_missing_site_skipped_tasks,
    run_check_all_sources,
    run_collect_successful_sources,
    run_discovery_tasks,
    run_extract_file_links_for_html_with_files,
    run_import_school_seed,
    run_preview_collectable_sources,
)
from services.coverage_report_service import (
    generate_coverage_report,
    list_coverage_reports,
)
from services.data_quality_service import check_ai_major_data_quality
from services.school_seed_service import list_school_seed_status


router = APIRouter(prefix="/bulk", tags=["bulk-pipeline"])


@router.post("/import-school-seed")
def import_school_seed() -> dict:
    return run_import_school_seed()


@router.post("/discover-sources")
def discover_sources(
    limit: int = Query(default=20, ge=1, le=100),
    use_search: bool = Query(default=False),
    retry_skipped: bool = Query(default=False),
) -> list[dict]:
    return run_discovery_tasks(
        limit=limit,
        use_search=use_search,
        retry_skipped=retry_skipped,
    )


@router.post("/reset-missing-site-skipped")
def reset_missing_site_skipped() -> dict:
    return {"reset_count": reset_missing_site_skipped_tasks()}


@router.post("/check-sources")
def check_sources(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return run_check_all_sources(limit=limit)


@router.post("/extract-file-links")
def extract_file_links(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return run_extract_file_links_for_html_with_files(limit=limit)


@router.post("/preview-sources")
def preview_sources(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return run_preview_collectable_sources(limit=limit)


@router.post("/collect-sources")
def collect_sources(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return run_collect_successful_sources(limit=limit)


@router.post("/generate-coverage-report")
def create_coverage_report(
    province: str = Query(default="四川"),
    year: int = Query(default=2025),
) -> dict:
    return generate_coverage_report(province=province, year=year)


@router.get("/coverage-reports")
def coverage_reports(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return list_coverage_reports(limit=limit)


@router.get("/school-seed-status")
def school_seed_status() -> list[dict]:
    return list_school_seed_status()


@router.get("/data-quality")
def data_quality() -> dict:
    return check_ai_major_data_quality()
