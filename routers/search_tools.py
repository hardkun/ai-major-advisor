"""本地管理用搜索调试接口。

正式上线前需要增加管理员权限保护。
"""

from fastapi import APIRouter, Query

from services.school_site_discovery_service import (
    discover_school_admission_site_by_search,
)


router = APIRouter(prefix="/search-tools", tags=["search-tools"])


@router.get("/school-site")
def search_school_site(school_name: str = Query(..., min_length=1)) -> dict:
    return discover_school_admission_site_by_search(school_name)
