"""缺失学校深度搜索候选数据源服务。"""

import json
from urllib.parse import urlparse

from config import SEARCH_RESULT_LIMIT
from db import create_connection, init_db
from services.school_site_discovery_service import (
    build_deep_score_source_queries,
    score_deep_source_candidate,
)
from services.official_source_service import score_official_source
from services.search_provider_service import search_web
from services.source_backfill_service import load_seed_school_names


def _load_ai_keywords() -> list[str]:
    from db import BASE_DIR

    path = BASE_DIR / "data_sources" / "ai_major_keywords.txt"
    if not path.exists():
        return ["人工智能", "计算机", "软件工程", "数据科学", "电子信息", "自动化"]
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _default_parser_config(province: str = "四川", year: int = 2025) -> str:
    config = {
        "table_index": 0,
        "header_row_index": 0,
        "auto_detect_header": True,
        "header_keywords": ["科类", "专业名称", "录取专业", "最低分", "最低位次", "位次", "分数"],
        "header_min_match_count": 3,
        "skip_rows": 0,
        "fill_down_fields": ["subject_type", "major_group_code", "elective_requirement"],
        "auto_direction_tags": True,
        "major_filter_keywords": _load_ai_keywords(),
        "default_values": {
            "admission_province": province,
            "admission_year": year,
        },
    }
    return json.dumps(config, ensure_ascii=False)


def _guess_parser_type(url: str) -> str:
    path = urlparse(url or "").path.lower()
    if path.endswith((".xlsx", ".xls")):
        return "excel_url"
    if path.endswith(".csv"):
        return "csv_url"
    if path.endswith(".pdf"):
        return "pdf"
    return "html_table"


def _formal_source_exists(conn, school_name: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM raw_data_sources
        WHERE school_name = ?
          AND enabled = 1
          AND COALESCE(is_demo, 0) != 1
          AND COALESCE(is_candidate, 0) != 1
        LIMIT 1
        """,
        (school_name,),
    ).fetchone()
    return row is not None


def _candidate_exists(conn, school_name: str, url: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM raw_data_sources
        WHERE school_name = ?
          AND url = ?
        LIMIT 1
        """,
        (school_name, url),
    ).fetchone()
    return row is not None


def _create_candidate_source(
    conn,
    school_name: str,
    candidate: dict,
    province: str,
    year: int,
) -> int | None:
    url = candidate.get("url")
    if not url or _candidate_exists(conn, school_name, url):
        return None

    official_result = score_official_source(
        school_name=school_name,
        url=url,
        title=candidate.get("title") or "",
        snippet=candidate.get("snippet") or "",
    )
    official_status = official_result["official_check_status"]
    candidate_status = "pending"
    reject_reason = None
    if official_status == "rejected":
        candidate_status = "rejected"
        reject_reason = official_result["message"]
    elif official_status in {"reference_only", "unknown"}:
        candidate_status = "reference_only"

    cursor = conn.execute(
        """
        INSERT INTO raw_data_sources
            (school_name, name, source_type, url, parser_type, enabled,
             is_candidate, is_demo, candidate_status, discovery_score,
             discovery_mode, description, parser_config_json,
             official_check_status, official_check_message, official_score,
             candidate_reject_reason, reference_only)
        VALUES (?, ?, 'school_candidate', ?, ?, 0,
                1, 0, ?, ?, 'deep_search_candidate', ?, ?,
                ?, ?, ?, ?, ?)
        """,
        (
            school_name,
            f"{school_name} 搜索候选数据源",
            url,
            _guess_parser_type(url),
            candidate_status,
            int(candidate.get("score") or 0),
            "深度搜索发现的候选数据源，需人工确认",
            _default_parser_config(province=province, year=year),
            official_status,
            official_result["message"],
            int(official_result["official_score"]),
            reject_reason,
            int(official_result["reference_only"]),
        ),
    )
    return cursor.lastrowid


def _missing_source_schools(limit: int) -> list[str]:
    school_names = load_seed_school_names()
    conn = create_connection()
    try:
        missing = []
        for school_name in school_names:
            if not _formal_source_exists(conn, school_name):
                missing.append(school_name)
            if len(missing) >= limit:
                break
        return missing
    finally:
        conn.close()


def _search_candidates_for_school(
    school_name: str,
    province: str,
    year: int,
    min_candidate_score: int,
) -> list[dict]:
    seen_urls = set()
    candidates = []
    for query in build_deep_score_source_queries(school_name, province=province, year=year):
        results = search_web(query, limit=SEARCH_RESULT_LIMIT)
        for result in results:
            url = result.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            scored = dict(result)
            scored["query"] = query
            scored["score"] = score_deep_source_candidate(
                school_name=school_name,
                result=result,
                province=province,
                year=year,
            )
            if int(scored["score"]) >= min_candidate_score:
                candidates.append(scored)
    candidates.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return candidates


def deep_search_missing_school_sources(
    limit: int = 20,
    min_candidate_score: int = 35,
    province: str = "四川",
    year: int = 2025,
) -> list[dict]:
    """深度搜索缺失学校，保存为候选源，不自动启用。"""
    init_db()
    schools = _missing_source_schools(limit=limit)
    results = []

    conn = create_connection()
    try:
        for school_name in schools:
            candidates = _search_candidates_for_school(
                school_name=school_name,
                province=province,
                year=year,
                min_candidate_score=min_candidate_score,
            )
            created_count = 0
            for candidate in candidates:
                source_id = _create_candidate_source(
                    conn=conn,
                    school_name=school_name,
                    candidate=candidate,
                    province=province,
                    year=year,
                )
                if source_id:
                    candidate["source_id"] = source_id
                    created_count += 1

            conn.commit()
            results.append(
                {
                    "school_name": school_name,
                    "candidates_found": len(candidates),
                    "candidates_created": created_count,
                    "top_candidates": candidates[:3],
                }
            )
    finally:
        conn.close()

    return results
