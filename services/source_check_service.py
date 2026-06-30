"""原始数据源可采性检测服务。"""

import json
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from fastapi import HTTPException

from crud.raw_data_sources import (
    get_raw_data_source_by_id,
    list_raw_data_sources,
    update_source_check_result,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
)

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _detect_type(url: str, content_type: str | None) -> str:
    lower_url = url.lower()
    lower_content_type = (content_type or "").lower()

    if lower_url.endswith(".csv") or "csv" in lower_content_type:
        return "csv_url"
    if lower_url.endswith((".xls", ".xlsx")) or any(
        keyword in lower_content_type
        for keyword in ["excel", "spreadsheet", "officedocument.spreadsheet"]
    ):
        return "excel_url"
    if lower_url.endswith(".pdf") or "pdf" in lower_content_type:
        return "pdf"
    if "text/html" in lower_content_type or lower_url.endswith((".html", ".htm")):
        return "html"
    return "unknown"


def _file_type_from_url(url: str) -> str | None:
    lower_path = urlparse(url).path.lower()
    for suffix in [".csv", ".xlsx", ".xls", ".pdf"]:
        if lower_path.endswith(suffix):
            return suffix.replace(".", "")
    return None


def _extract_file_links(html: str, base_url: str) -> tuple[int, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    table_count = len(soup.find_all("table"))
    file_links: list[dict] = []

    for link in soup.find_all("a"):
        href = link.get("href")
        if not href:
            continue
        absolute_url = urljoin(base_url, href)
        file_type = _file_type_from_url(absolute_url)
        if not file_type:
            continue
        file_links.append(
            {
                "text": link.get_text(" ", strip=True),
                "url": absolute_url,
                "file_type": file_type,
            }
        )

    return table_count, file_links


def _save_result(
    source_id: int,
    status: str,
    message: str | None,
    content_type: str | None,
    detected_type: str | None,
    table_count: int = 0,
    file_links: list[dict] | None = None,
) -> dict:
    file_links_json = json.dumps(file_links or [], ensure_ascii=False)
    update_source_check_result(
        source_id=source_id,
        last_check_status=status,
        last_check_message=message,
        last_content_type=content_type,
        last_detected_type=detected_type,
        last_table_count=table_count,
        last_file_links_json=file_links_json,
    )
    return {
        "source_id": source_id,
        "last_check_status": status,
        "last_check_message": message,
        "last_content_type": content_type,
        "last_detected_type": detected_type,
        "last_table_count": table_count,
        "last_file_links": file_links or [],
    }


def check_raw_data_source(source_id: int) -> dict:
    """检测一个 raw_data_sources URL 的可采性，并写回检测结果。"""
    source = get_raw_data_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")

    source_data = source.model_dump()
    url = source_data.get("url")
    if not url:
        return _save_result(
            source_id=source_id,
            status="failed",
            message="数据源 URL 为空",
            content_type=None,
            detected_type=None,
        )

    try:
        url_file_type = _file_type_from_url(url)
        if url_file_type == "csv":
            return _save_result(source_id, "success", "检测完成", None, "csv_url")
        if url_file_type in {"xlsx", "xls"}:
            return _save_result(source_id, "success", "检测完成", None, "excel_url")
        if url_file_type == "pdf":
            return _save_result(source_id, "success", "检测完成", None, "pdf")

        request = Request(url, headers=REQUEST_HEADERS)
        with urlopen(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type")
            raw_content = response.read()

        detected_type = _detect_type(url, content_type)
        table_count = 0
        file_links: list[dict] = []

        if detected_type == "html":
            html = raw_content.decode("utf-8", errors="ignore")
            table_count, file_links = _extract_file_links(html, url)
            if table_count > 0:
                detected_type = "html_table"
            elif file_links:
                detected_type = "html_with_files"

        return _save_result(
            source_id=source_id,
            status="success",
            message="检测完成",
            content_type=content_type,
            detected_type=detected_type,
            table_count=table_count,
            file_links=file_links,
        )
    except Exception as exc:
        return _save_result(
            source_id=source_id,
            status="failed",
            message=str(exc),
            content_type=None,
            detected_type=None,
        )


def check_enabled_raw_data_sources() -> list[dict]:
    """批量检测所有 enabled=True 的原始数据源。"""
    results: list[dict] = []
    for source in list_raw_data_sources():
        if not source.enabled:
            continue
        try:
            results.append(check_raw_data_source(source.id))
        except Exception as exc:
            results.append(
                {
                    "source_id": source.id,
                    "last_check_status": "failed",
                    "last_check_message": str(exc),
                }
            )
    return results
