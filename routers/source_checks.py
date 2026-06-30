from fastapi import APIRouter

from services.source_check_service import (
    check_enabled_raw_data_sources,
    check_raw_data_source,
)


router = APIRouter(tags=["source-checks"])


@router.post("/raw-data-sources/{source_id}/check")
def check_source(source_id: int) -> dict:
    return check_raw_data_source(source_id)


@router.post("/raw-data-sources/check-enabled")
def check_enabled_sources() -> list[dict]:
    return check_enabled_raw_data_sources()
