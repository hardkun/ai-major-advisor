"""缺口分型与采集器补全优先队列服务。"""

import json
from collections import Counter

from db import create_connection, init_db
from services.school_seed_service import list_school_seed_status


def _safe_load_json(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _source_belongs_to_school(source: dict, school_name: str) -> bool:
    haystack = " ".join(
        str(source.get(field) or "")
        for field in ["name", "description", "url", "source_type"]
    )
    return school_name in haystack


def _classify_collect_failure(row: dict) -> str:
    status = row.get("status")
    inserted_count = int(row.get("inserted_count") or 0)
    skipped_count = int(row.get("skipped_count") or 0)
    error_count = int(row.get("error_count") or 0)
    message = str(row.get("message") or "").lower()

    if "不支持" in message or "unsupported" in message or "manual_upload" in message:
        return "unsupported_parser_type"
    if "http error" in message or "http" in message or "403" in message or "412" in message:
        return "http_error"
    if "parse" in message or "解析" in message or "header" in message or "table" in message:
        return "parse_error"
    if status == "skipped" and inserted_count == 0 and skipped_count > 0 and error_count == 0:
        if "duplicate" in message or "重复" in message:
            return "duplicate_only"
        return "no_ai_major_matched"
    return "unknown"


def _is_demo_or_manual_source(source: dict) -> bool:
    text = " ".join(
        str(source.get(field) or "")
        for field in ["name", "description", "url", "parser_type", "source_type"]
    ).lower()
    return (
        "示例" in text
        or "demo" in text
        or "example" in text
        or source.get("parser_type") == "manual_upload"
    )


def _priority_action(
    *,
    school_name: str | None,
    source: dict | None,
    action: str,
    priority: int,
    reason: str,
) -> dict:
    return {
        "school_name": school_name,
        "source_id": source.get("id") if source else None,
        "source_name": source.get("name") if source else None,
        "url": source.get("url") if source else None,
        "detected_type": source.get("last_detected_type") if source else None,
        "parser_type": source.get("parser_type") if source else None,
        "action": action,
        "priority": priority,
        "reason": reason,
    }


def _load_sources(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM raw_data_sources
        ORDER BY id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _raw_count_for_school(conn, school_name: str, province: str, year: int) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM raw_admission_records
        WHERE school_name = ?
          AND admission_province = ?
          AND admission_year = ?
        """,
        (school_name, province, year),
    ).fetchone()["count"]


def _verified_count_for_school(conn, school_name: str, province: str, year: int) -> int:
    return conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM admissions
        JOIN schools ON schools.id = admissions.school_id
        WHERE schools.name = ?
          AND admissions.province = ?
          AND admissions.year = ?
        """,
        (school_name, province, year),
    ).fetchone()["count"]


def _latest_collector_run_by_source(conn) -> dict[int, dict]:
    rows = conn.execute(
        """
        SELECT *
        FROM collector_runs
        ORDER BY id DESC
        """
    ).fetchall()
    latest = {}
    for row in rows:
        data = dict(row)
        source_id = data.get("raw_source_id")
        if source_id is not None and source_id not in latest:
            latest[source_id] = data
    return latest


def generate_gap_diagnosis_report(province: str = "四川", year: int = 2025) -> dict:
    """生成缺口分型与下一步优先处理清单。"""
    init_db()
    seed_status = list_school_seed_status()
    total_schools = len(seed_status)

    conn = create_connection()
    try:
        sources = _load_sources(conn)
        latest_runs = _latest_collector_run_by_source(conn)

        detected_type_distribution = Counter()
        for source in sources:
            if _is_demo_or_manual_source(source):
                continue
            detected_type = source.get("last_detected_type")
            if source.get("last_check_status") == "failed":
                detected_type_distribution["failed"] += 1
            elif detected_type:
                detected_type_distribution[detected_type] += 1
            else:
                detected_type_distribution["unknown"] += 1

        collect_failure_distribution = Counter()
        for run in latest_runs.values():
            source = next((item for item in sources if item.get("id") == run.get("raw_source_id")), None)
            if source and _is_demo_or_manual_source(source):
                continue
            if run.get("status") in {"failed", "partial", "skipped"}:
                collect_failure_distribution[_classify_collect_failure(run)] += 1

        schools_with_sources = 0
        schools_with_raw = 0
        schools_with_verified = 0
        missing_source_schools = []
        source_but_no_raw_schools = []
        priority_actions = []

        for school in seed_status:
            school_name = school["school_name"]
            school_sources = [
                source for source in sources if _source_belongs_to_school(source, school_name)
            ]
            raw_count = _raw_count_for_school(conn, school_name, province, year)
            verified_count = _verified_count_for_school(conn, school_name, province, year)

            if school_sources:
                schools_with_sources += 1
            if raw_count > 0:
                schools_with_raw += 1
            if verified_count > 0:
                schools_with_verified += 1

            if not school_sources:
                missing_source_schools.append(
                    {
                        "school_name": school_name,
                        "reason": "未发现数据源",
                    }
                )
                priority_actions.append(
                    _priority_action(
                        school_name=school_name,
                        source=None,
                        action="improve_search_or_fill_admission_site",
                        priority=4,
                        reason="需要继续自动搜索或补充招生官网入口",
                    )
                )
                continue

            if raw_count == 0:
                source_but_no_raw_schools.append(
                    {
                        "school_name": school_name,
                        "source_count": len(school_sources),
                        "reason": "有数据源但 raw_records_count = 0",
                    }
                )

            for source in school_sources:
                detected_type = source.get("last_detected_type")
                check_message = str(source.get("last_check_message") or "")
                parser_type = source.get("parser_type")

                if parser_type == "manual_upload" or _is_demo_or_manual_source(source):
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="exclude_demo_source",
                            priority=5,
                            reason="示例数据源不应计入失败统计",
                        )
                    )
                    continue

                if raw_count == 0 and detected_type == "html_table":
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="review_html_preview",
                            priority=1,
                            reason="已有 HTML 表格源，但未采集到记录，优先检查表头、字段映射、关键词过滤",
                        )
                    )

                if detected_type == "html_with_files":
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="implement_file_link_collector",
                            priority=2,
                            reason="页面含 Excel/PDF 附件，需要附件采集器",
                        )
                    )
                elif detected_type == "excel_url":
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="implement_excel_url_collector",
                            priority=2,
                            reason="Excel 文件可直接下载解析",
                        )
                    )
                elif detected_type == "pdf":
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="implement_pdf_table_collector",
                            priority=3,
                            reason="PDF 需要表格解析",
                        )
                    )

                if "412" in check_message or "403" in check_message:
                    priority_actions.append(
                        _priority_action(
                            school_name=school_name,
                            source=source,
                            action="retry_with_headers_or_manual_review",
                            priority=3,
                            reason="网站拒绝默认请求，需要增加 User-Agent/Referer 或人工确认",
                        )
                    )

        failed_sources = [
            {
                "source_id": source.get("id"),
                "source_name": source.get("name"),
                "url": source.get("url"),
                "last_check_status": source.get("last_check_status"),
                "last_check_message": source.get("last_check_message"),
                "last_detected_type": source.get("last_detected_type"),
                "parser_type": source.get("parser_type"),
            }
            for source in sources
            if source.get("last_check_status") == "failed" and not _is_demo_or_manual_source(source)
        ]

        priority_actions.sort(key=lambda item: (item["priority"], item.get("school_name") or ""))

        report = {
            "province": province,
            "year": year,
            "total_schools": total_schools,
            "schools_with_sources": schools_with_sources,
            "schools_with_raw": schools_with_raw,
            "schools_with_verified": schools_with_verified,
            "missing_source_schools": missing_source_schools,
            "source_but_no_raw_schools": source_but_no_raw_schools,
            "failed_sources": failed_sources,
            "detected_type_distribution": dict(detected_type_distribution),
            "collect_failure_distribution": dict(collect_failure_distribution),
            "priority_actions": priority_actions,
        }

        cursor = conn.execute(
            """
            INSERT INTO gap_diagnosis_reports
                (province, year, report_json)
            VALUES (?, ?, ?)
            """,
            (province, year, json.dumps(report, ensure_ascii=False)),
        )
        conn.commit()
        report["id"] = cursor.lastrowid
        return report
    finally:
        conn.close()


def get_latest_gap_diagnosis_report() -> dict | None:
    init_db()
    conn = create_connection()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM gap_diagnosis_reports
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        report = _safe_load_json(row["report_json"], {})
        report["id"] = row["id"]
        report["created_at"] = row["created_at"]
        return report
    finally:
        conn.close()
