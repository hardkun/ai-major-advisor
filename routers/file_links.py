"""附件链接提取接口。"""

from fastapi import APIRouter

from services.file_link_service import extract_file_links_from_source


router = APIRouter(prefix="/raw-data-sources", tags=["file-links"])


@router.post("/{source_id}/extract-file-links")
def extract_file_links(source_id: int) -> dict:
    return extract_file_links_from_source(source_id)
