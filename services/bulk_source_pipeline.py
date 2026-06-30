"""四川 2025 AI 相关专业数据源批量工程流水线。"""

import json
from urllib.parse import urlparse

from collectors.collector_preview import preview_single_collector
from collectors.collector_runner import run_single_collector
from db import create_connection, init_db
from services.school_seed_service import import_school_seed_csv
from services.file_link_service import extract_file_links_from_source
from services.source_check_service import check_raw_data_source
from services.source_discovery_service import discover_sources_for_school


def _load_ai_keywords() -> list[str]:
    from pathlib import Path

    from db import BASE_DIR

    path = BASE_DIR / "data_sources" / "ai_major_keywords.txt"
    if not path.exists():
        return ["人工智能", "计算机", "软件工程", "数据科学", "电子信息", "自动化"]
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _default_parser_config() -> str:
    config = {
        "table_index": 0,
        "header_row_index": 0,
        "auto_detect_header": True,
        "header_keywords": ["科类", "专业名称", "录取专业", "最低分", "最低位次", "位次"],
        "header_min_match_count": 3,
        "skip_rows": 0,
        "fill_down_fields": ["subject_type", "major_group_code", "elective_requirement"],
        "auto_direction_tags": True,
        "major_filter_keywords": _load_ai_keywords(),
        "default_values": {
            "admission_province": "四川",
            "admission_year": 2025,
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


def _is_disallowed_source_url(url: str) -> bool:
    lower_url = (url or "").lower()
    bad_keywords = [
        "baidu",
        "zhihu",
        "sohu",
        "sina",
        "163.com",
        "toutiao",
        "bilibili",
        "youzy",
        "gaokao.cn",
        "eol.cn",
        "eol",
        "掌上高考",
    ]
    return any(keyword in lower_url for keyword in bad_keywords)


def _upsert_raw_data_source(
    school_name: str,
    url: str,
    detected_type: str | None = None,
    enabled: bool = True,
    description: str | None = None,
    discovery_mode: str | None = None,
    score: int | None = None,
) -> int:
    conn = create_connection()
    try:
        name = f"{school_name} 2025四川专业录取分数"
        parser_type = _guess_parser_type(url)
        if _is_disallowed_source_url(url):
            enabled = False
            description = description or "搜索候选，需人工确认"
            description = f"{description}；命中第三方/内容平台关键词，禁止自动启用"
        final_description = description or "自动发现的高校招生数据源，需检测和预览确认"
        if score is not None:
            final_description = f"{final_description}；score={score}"
        if discovery_mode:
            final_description = f"{final_description}；discovery_mode={discovery_mode}"
        row = conn.execute(
            """
            SELECT id FROM raw_data_sources
            WHERE url = ?
            LIMIT 1
            """,
            (url,),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE raw_data_sources
                SET url = ?,
                    parser_type = ?,
                    enabled = ?,
                    description = ?,
                    school_name = COALESCE(school_name, ?),
                    discovery_score = ?,
                    discovery_mode = ?,
                    is_candidate = ?,
                    last_detected_type = COALESCE(?, last_detected_type),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    url,
                    parser_type,
                    1 if enabled else 0,
                    final_description,
                    school_name,
                    int(score or 0),
                    discovery_mode,
                    0 if enabled else 1,
                    detected_type,
                    row["id"],
                ),
            )
            conn.commit()
            return row["id"]

        cursor = conn.execute(
            """
            INSERT INTO raw_data_sources
                (name, source_type, url, parser_type, enabled, description,
                 school_name, discovery_score, discovery_mode, is_candidate,
                 field_mapping_json, parser_config_json, last_detected_type)
            VALUES (?, 'school', ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                name,
                url,
                parser_type,
                1 if enabled else 0,
                final_description,
                school_name,
                int(score or 0),
                discovery_mode,
                0 if enabled else 1,
                _default_parser_config(),
                detected_type,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def run_import_school_seed() -> dict:
    return import_school_seed_csv()


def _fetch_discovery_tasks(limit: int, retry_skipped: bool = False) -> list[dict]:
    conn = create_connection()
    try:
        if retry_skipped:
            rows = conn.execute(
                """
                SELECT * FROM source_discovery_tasks
                WHERE status IN ('pending', 'skipped')
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

        rows = conn.execute(
            """
            SELECT * FROM source_discovery_tasks
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def reset_missing_site_skipped_tasks() -> int:
    """把“缺少招生官网入口”的 skipped 任务重置为 pending，便于补配置后重跑。"""
    init_db()
    conn = create_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE source_discovery_tasks
            SET status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'skipped'
              AND (
                    message LIKE '%缺少招生官网入口%'
                    OR message LIKE '%admission_site%'
                  )
            """
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def _update_task(task_id: int, data: dict) -> None:
    allowed = {
        "status",
        "discovered_url",
        "discovered_score_url",
        "detected_type",
        "score",
        "message",
        "discovered_admission_site",
        "search_candidates_json",
        "discovery_mode",
    }
    update_data = {key: value for key, value in data.items() if key in allowed}
    if not update_data:
        return

    set_parts = [f"{key} = ?" for key in update_data]
    set_parts.append("updated_at = CURRENT_TIMESTAMP")
    values = list(update_data.values())
    values.append(task_id)

    conn = create_connection()
    try:
        conn.execute(
            f"""
            UPDATE source_discovery_tasks
            SET {", ".join(set_parts)}
            WHERE id = ?
            """,
            values,
        )
        conn.commit()
    finally:
        conn.close()


def run_discovery_tasks(
    limit: int = 20,
    use_search: bool = False,
    retry_skipped: bool = False,
    allow_search: bool | None = None,
) -> list[dict]:
    """运行数据源发现任务。

    use_search=True 时，admission_site 为空的任务允许调用搜索 API。
    retry_skipped=True 时，查询范围包含 pending 和 skipped，但不会重跑 success。
    allow_search 是旧参数名，保留兼容。
    """
    if allow_search is not None:
        use_search = allow_search

    init_db()
    results = []
    for task in _fetch_discovery_tasks(limit, retry_skipped=retry_skipped):
        if not task.get("admission_site"):
            if not use_search:
                result = {
                    "task_id": task["id"],
                    "school_name": task.get("school_name"),
                    "status": "skipped",
                    "best_url": None,
                    "score": 0,
                    "message": "缺少招生官网入口，需要人工补充 admission_site；如需自动搜索请使用 --use-search",
                }
                _update_task(
                    task["id"],
                    {
                        "status": "skipped",
                        "score": 0,
                        "message": result["message"],
                    },
                )
                results.append(result)
                continue

        discovery = discover_sources_for_school(
            school_name=task.get("school_name") or "",
            admission_site=task.get("admission_site"),
            allow_search=use_search,
        )
        best_url = discovery.get("best_url")
        score = int(discovery.get("score") or 0)
        discovery_mode = discovery.get("discovery_mode") or "none"
        if best_url:
            enabled = score >= 60 or discovery_mode in {"admission_site", "mixed"}
            if discovery_mode == "direct_score_page" and score < 60:
                description = "搜索候选，需人工确认"
            elif discovery_mode == "direct_score_page":
                description = "搜索 API 直接发现分数页面"
            elif discovery_mode == "admission_site":
                description = "招生官网站内发现"
            elif discovery_mode == "mixed":
                description = "搜索发现招生官网后，站内发现分数页面"
            else:
                description = "自动发现的高校招生数据源，需检测和预览确认"
            source_id = _upsert_raw_data_source(
                school_name=task.get("school_name") or "",
                url=best_url,
                enabled=enabled,
                description=description,
                discovery_mode=discovery_mode,
                score=score,
            )
            status = "success" if enabled else "skipped"
            message = (
                f"{discovery.get('message')}，已写入 raw_data_sources #{source_id}"
                if enabled
                else f"{discovery.get('message')}，已写入 disabled 搜索候选 raw_data_sources #{source_id}"
            )
        else:
            source_id = None
            status = "skipped" if discovery.get("discovered_admission_site") is None else "failed"
            message = discovery.get("message") or "未发现候选页面"

        _update_task(
            task["id"],
            {
                "status": status,
                "discovered_url": best_url,
                "discovered_score_url": discovery.get("discovered_score_url") or best_url,
                "discovered_admission_site": discovery.get("discovered_admission_site"),
                "search_candidates_json": discovery.get("search_candidates_json"),
                "discovery_mode": discovery_mode,
                "score": score,
                "message": message,
            },
        )
        results.append(
            {
                "task_id": task["id"],
                "school_name": task.get("school_name"),
                "status": status,
                "best_url": best_url,
                "discovered_score_url": discovery.get("discovered_score_url") or best_url,
                "discovered_admission_site": discovery.get("discovered_admission_site"),
                "discovery_mode": discovery_mode,
                "source_id": source_id,
                "score": score,
                "best_score": score,
                "candidate_count": len(discovery.get("search_candidates", []))
                + len(discovery.get("candidate_urls", [])),
                "message": message,
                "search_candidates": discovery.get("search_candidates", []),
                "candidate_urls": discovery.get("candidate_urls", []),
            }
        )
    return results


def _enabled_sources(limit: int, detected_type: str | None = None) -> list[dict]:
    sql = """
        SELECT * FROM raw_data_sources
        WHERE enabled = 1
    """
    params: list = []
    if detected_type:
        sql += " AND last_detected_type = ?"
        params.append(detected_type)
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)

    conn = create_connection()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def run_check_all_sources(limit: int = 50) -> list[dict]:
    init_db()
    results = []
    for source in _enabled_sources(limit):
        try:
            results.append(check_raw_data_source(source["id"]))
        except Exception as exc:
            results.append(
                {
                    "source_id": source["id"],
                    "source_name": source.get("name"),
                    "last_check_status": "failed",
                    "last_check_message": str(exc),
                }
            )
    return results


def run_extract_file_links_for_html_with_files(limit: int = 20) -> list[dict]:
    init_db()
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, name
            FROM raw_data_sources
            WHERE enabled = 1
              AND last_detected_type = 'html_with_files'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        sources = [dict(row) for row in rows]
    finally:
        conn.close()

    results = []
    for source in sources:
        try:
            result = extract_file_links_from_source(source["id"])
            result["source_name"] = source.get("name")
            results.append(result)
        except Exception as exc:
            results.append(
                {
                    "parent_source_id": source["id"],
                    "source_name": source.get("name"),
                    "discovered_count": 0,
                    "created_count": 0,
                    "skipped_count": 0,
                    "error": str(exc),
                }
            )
    return results


def run_preview_collectable_sources(limit: int = 50) -> list[dict]:
    init_db()
    results = []
    for source in _enabled_sources(limit, detected_type="html_table"):
        try:
            preview = preview_single_collector(source["id"])
            results.append(preview)
        except Exception as exc:
            results.append(
                {
                    "source_id": source["id"],
                    "source_name": source.get("name"),
                    "error_count": 1,
                    "message": str(exc),
                }
            )
    return results


def run_collect_successful_sources(limit: int = 20) -> list[dict]:
    init_db()
    results = []
    for source in _enabled_sources(limit, detected_type="html_table"):
        try:
            results.append(run_single_collector(source["id"]))
        except Exception as exc:
            results.append(
                {
                    "source_id": source["id"],
                    "source_name": source.get("name"),
                    "status": "failed",
                    "inserted_count": 0,
                    "skipped_count": 0,
                    "error_count": 1,
                    "message": str(exc),
                }
            )
    return results
