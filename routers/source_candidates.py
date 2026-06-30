"""候选数据源管理接口。

仅用于本地 admin 演示；正式上线前需要增加权限保护。
"""

from fastapi import APIRouter, Body, Query

from services.deep_missing_source_service import deep_search_missing_school_sources
from services.official_source_service import (
    apply_official_filter_to_candidates,
    keep_top_official_candidates_per_school,
)
from services.source_candidate_service import (
    approve_source_candidate,
    list_source_candidates,
    reject_source_candidate,
)


router = APIRouter(prefix="/source-candidates", tags=["source-candidates"])


@router.post("/deep-search-missing")
def deep_search_missing(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return deep_search_missing_school_sources(limit=limit)


@router.get("")
def get_source_candidates(
    limit: int = Query(default=100, ge=1, le=300),
    include_all: bool = Query(default=False),
) -> list[dict]:
    return list_source_candidates(limit=limit, include_all=include_all)


@router.post("/filter-official")
def filter_official_candidates(
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict:
    return apply_official_filter_to_candidates(limit=limit)


@router.post("/keep-top-official")
def keep_top_official_candidates(
    top: int = Query(default=3, ge=1, le=20),
) -> dict:
    return keep_top_official_candidates_per_school(max_per_school=top)


@router.post("/{source_id}/approve")
def approve_candidate(source_id: int) -> dict:
    return approve_source_candidate(source_id)


@router.post("/{source_id}/reject")
def reject_candidate(
    source_id: int,
    reason: str | None = Body(default=None, embed=True),
) -> dict:
    return reject_source_candidate(source_id, reason=reason)
