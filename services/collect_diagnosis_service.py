"""数据源采集可行性预览诊断。"""

import json

from collectors.collector_preview import preview_single_collector
from db import create_connection, init_db


SUPPORTED_PREVIEW_TYPES = {"html_table", "excel_url", "pdf"}


def _row_to_dict(row) -> dict | None:
    return dict(row) if row else None


def _get_source(source_id: int) -> dict | None:
    conn = create_connection()
    try:
        return _row_to_dict(
            conn.execute(
                "SELECT * FROM raw_data_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        )
    finally:
        conn.close()


def _update_diagnosis(source_id: int, status: str, message: str, preview: dict | None) -> None:
    conn = create_connection()
    try:
        conn.execute(
            """
            UPDATE raw_data_sources
            SET collect_diagnosis_status = ?,
                collect_diagnosis_message = ?,
                last_preview_json = ?,
                last_preview_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                message,
                json.dumps(preview or {}, ensure_ascii=False),
                source_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _classify_preview(preview: dict) -> tuple[str, str]:
    if int(preview.get("error_count") or 0) > 0:
        return "preview_failed", preview.get("message") or "预览报错"

    total_data_rows = int(preview.get("total_data_rows") or 0)
    would_insert_count = int(preview.get("would_insert_count") or 0)
    empty_major = int(preview.get("empty_major_skipped_count") or 0)
    filter_skipped = int(preview.get("filter_skipped_count") or 0)
    duplicate_skipped = int(preview.get("duplicate_skipped_count") or 0)

    if total_data_rows == 0:
        return "no_rows", "预览未解析到数据行"
    if empty_major > 0 and would_insert_count == 0 and empty_major >= max(1, total_data_rows // 2):
        return "field_mapping_or_header_error", "大量行 major_name 为空，可能是表头识别或字段映射错误"
    if filter_skipped > 0 and would_insert_count == 0:
        return "no_ai_match_or_filter_too_strict", "有数据行但未命中 AI 相关专业关键词，可能关键词过严或该校无相关专业"
    if duplicate_skipped > 0 and would_insert_count == 0:
        return "duplicate_only", "预览结果均为重复数据"
    if would_insert_count > 0:
        return "preview_success", "预览成功，可以正式采集"
    return "unknown", preview.get("message") or "无法判断采集可行性"


def diagnose_source_collectability(source_id: int) -> dict:
    """诊断单个数据源为什么没有 raw 数据。"""
    init_db()
    source = _get_source(source_id)
    if not source:
        return {"source_id": source_id, "status": "not_found", "message": "数据源不存在"}

    if int(source.get("is_demo") or 0) == 1:
        status, message, preview = "demo_skipped", "演示/测试源不参与正式诊断", {}
    elif source.get("parser_type") not in SUPPORTED_PREVIEW_TYPES:
        status, message, preview = "unsupported", f"不支持的 parser_type：{source.get('parser_type')}", {}
    else:
        try:
            preview = preview_single_collector(source_id)
            status, message = _classify_preview(preview)
        except Exception as exc:
            status, message, preview = "preview_failed", str(exc), {}

    _update_diagnosis(source_id, status, message, preview)
    return {
        "source_id": source_id,
        "school_name": source.get("school_name"),
        "source_name": source.get("name"),
        "parser_type": source.get("parser_type"),
        "status": status,
        "message": message,
        "preview": preview,
    }


def diagnose_sources_without_records(limit: int = 50) -> list[dict]:
    """批量诊断：正式数据源中 school_name 有值但该校 raw 数为 0 的源。"""
    init_db()
    limit = min(max(int(limit), 1), 200)
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT raw_data_sources.*
            FROM raw_data_sources
            WHERE enabled = 1
              AND COALESCE(is_demo, 0) != 1
              AND COALESCE(is_candidate, 0) != 1
              AND COALESCE(school_name, '') != ''
              AND NOT EXISTS (
                    SELECT 1
                    FROM raw_admission_records
                    WHERE raw_admission_records.school_name = raw_data_sources.school_name
              )
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
            results.append(diagnose_source_collectability(source["id"]))
        except Exception as exc:
            results.append(
                {
                    "source_id": source["id"],
                    "school_name": source.get("school_name"),
                    "source_name": source.get("name"),
                    "parser_type": source.get("parser_type"),
                    "status": "preview_failed",
                    "message": str(exc),
                }
            )
    return results
