"""采集器预览入口。

预览只解析数据源并返回映射结果，不写入 raw_admission_records，
也不生成 collector_runs。
"""

from fastapi import HTTPException

from collectors.excel_url_collector import collect_excel_url_source
from collectors.html_table_collector import parse_html_table_source
from collectors.pdf_collector import collect_pdf_source
from db import create_connection, init_db


def _get_source_by_id(source_id: int) -> dict | None:
    conn = create_connection()
    try:
        row = conn.execute(
            "SELECT * FROM raw_data_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def preview_single_collector(source_id: int) -> dict:
    """预览指定数据源的采集解析结果。"""
    init_db()
    source = _get_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")

    parser_type = source.get("parser_type")
    if parser_type == "html_table":
        return parse_html_table_source(source, preview=True)

    if parser_type == "excel_url":
        return collect_excel_url_source(source, preview=True)

    if parser_type == "pdf":
        return collect_pdf_source(source, preview=True)

    if parser_type == "csv_url":
        return {
            "source_id": source_id,
            "source_name": source.get("name"),
            "parser_type": parser_type,
            "preview": True,
            "inserted_count": 0,
            "would_insert_count": 0,
            "skipped_count": 0,
            "error_count": 0,
            "message": "CSV URL 暂不支持预览，请使用正式采集或后续扩展 CSV 预览。",
        }

    return {
        "source_id": source_id,
        "source_name": source.get("name"),
        "parser_type": parser_type,
        "preview": True,
        "inserted_count": 0,
        "would_insert_count": 0,
        "skipped_count": 0,
        "error_count": 1,
        "message": f"暂不支持该 parser_type 的预览：{parser_type}",
    }
