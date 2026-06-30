"""从 html_with_files 数据源中提取附件链接并创建子数据源。"""

from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from fastapi import HTTPException

from db import create_connection, init_db


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

ALLOWED_SUFFIXES = {".xlsx": "xlsx", ".xls": "xls", ".csv": "csv", ".pdf": "pdf"}
SCORE_KEYWORDS = ["四川", "2025", "专业录取", "分专业", "录取分数", "录取情况", "最低分", "位次"]


def _get_source(source_id: int) -> dict | None:
    conn = create_connection()
    try:
        row = conn.execute("SELECT * FROM raw_data_sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _download_html(url: str) -> str:
    request = Request(url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=30) as response:
        content = response.read()
        charset = response.headers.get_content_charset()
    for encoding in [charset, "utf-8", "utf-8-sig", "gb18030", "gbk"]:
        if not encoding:
            continue
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _file_type_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for suffix, file_type in ALLOWED_SUFFIXES.items():
        if path.endswith(suffix):
            return file_type
    return "unknown"


def _parser_type_for_file(file_type: str) -> str:
    if file_type in {"xlsx", "xls"}:
        return "excel_url"
    if file_type == "csv":
        return "csv_url"
    if file_type == "pdf":
        return "pdf"
    return "unknown"


def _score_link(text: str, url: str) -> int:
    haystack = f"{text} {url}".lower()
    score = 0
    for keyword in SCORE_KEYWORDS:
        if keyword.lower() in haystack:
            score += 10
    if "2025" in haystack:
        score += 8
    if "四川" in haystack:
        score += 8
    return score


def _source_exists_by_url(url: str) -> bool:
    conn = create_connection()
    try:
        row = conn.execute(
            "SELECT id FROM raw_data_sources WHERE url = ? LIMIT 1",
            (url,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _create_child_source(parent: dict, link: dict) -> int:
    conn = create_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO raw_data_sources
                (name, source_type, url, parser_type, enabled, description,
                 school_name, discovery_mode, field_mapping_json, parser_config_json,
                 parent_source_id, file_type)
            VALUES (?, 'school_file', ?, ?, 1, ?, ?, 'file_link', ?, ?, ?, ?)
            """,
            (
                f"{parent.get('name')} - {link.get('text') or link.get('file_type')}",
                link["url"],
                _parser_type_for_file(link["file_type"]),
                "从父数据源附件链接自动发现",
                parent.get("school_name"),
                parent.get("field_mapping_json"),
                parent.get("parser_config_json"),
                parent["id"],
                link["file_type"],
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def extract_file_links_from_source(source_id: int) -> dict:
    """从父数据源页面中提取 Excel/CSV/PDF 附件链接，并创建子数据源。"""
    init_db()
    source = _get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")
    if not source.get("url"):
        raise HTTPException(status_code=400, detail="数据源 URL 为空")

    html = _download_html(source["url"])
    soup = BeautifulSoup(html, "html.parser")
    file_links = []

    for link in soup.find_all("a"):
        href = link.get("href")
        if not href:
            continue
        absolute_url = urljoin(source["url"], href)
        file_type = _file_type_from_url(absolute_url)
        if file_type not in {"xlsx", "xls", "csv", "pdf"}:
            continue
        text = link.get_text(" ", strip=True)
        file_links.append(
            {
                "text": text,
                "url": absolute_url,
                "file_type": file_type,
                "score": _score_link(text, absolute_url),
            }
        )

    file_links.sort(key=lambda item: item["score"], reverse=True)

    created_count = 0
    skipped_count = 0
    for link in file_links:
        if _source_exists_by_url(link["url"]):
            skipped_count += 1
            link["created"] = False
            continue
        link["source_id"] = _create_child_source(source, link)
        link["created"] = True
        created_count += 1

    return {
        "parent_source_id": source_id,
        "discovered_count": len(file_links),
        "created_count": created_count,
        "skipped_count": skipped_count,
        "file_links": file_links,
    }
