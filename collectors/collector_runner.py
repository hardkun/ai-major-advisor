"""自动采集器运行入口。"""

from datetime import datetime

from fastapi import HTTPException

from collectors.csv_url_collector import collect_csv_url_source
from collectors.excel_url_collector import collect_excel_url_source
from collectors.html_table_collector import collect_html_table_source
from collectors.pdf_collector import collect_pdf_source
from crud.collector_runs import create_collector_run
from db import create_connection, init_db


def _now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _list_enabled_sources() -> list[dict]:
    conn = create_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM raw_data_sources
            WHERE enabled = 1
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


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


def _unsupported_source_result(source: dict) -> dict:
    return {
        "source_id": source["id"],
        "source_name": source.get("name"),
        "parser_type": source.get("parser_type"),
        "inserted_count": 0,
        "skipped_count": 0,
        "error_count": 1,
        "message": f"不支持的 parser_type：{source.get('parser_type')}",
    }


def _judge_status(result: dict) -> str:
    inserted_count = int(result.get("inserted_count") or 0)
    skipped_count = int(result.get("skipped_count") or 0)
    error_count = int(result.get("error_count") or 0)

    if error_count > 0 and inserted_count > 0:
        return "partial"
    if error_count > 0 and inserted_count == 0:
        return "failed"
    if inserted_count == 0 and skipped_count > 0:
        return "skipped"
    return "success"


def _save_collector_run(
    source: dict,
    result: dict,
    started_at: str,
    finished_at: str,
) -> int:
    status = _judge_status(result)
    message = result.get("message") or result.get("error")
    collector_run_id = create_collector_run(
        raw_source_id=source.get("id"),
        source_name=source.get("name"),
        parser_type=source.get("parser_type"),
        status=status,
        inserted_count=int(result.get("inserted_count") or 0),
        skipped_count=int(result.get("skipped_count") or 0),
        error_count=int(result.get("error_count") or 0),
        message=message,
        started_at=started_at,
        finished_at=finished_at,
    )
    result["status"] = status
    result["collector_run_id"] = collector_run_id
    return collector_run_id


def _run_source(source: dict) -> dict:
    started_at = _now_text()
    try:
        parser_type = source.get("parser_type")
        if parser_type == "csv_url":
            result = collect_csv_url_source(source)
        elif parser_type == "excel_url":
            result = collect_excel_url_source(source, preview=False)
        elif parser_type == "html_table":
            result = collect_html_table_source(source)
        elif parser_type == "pdf":
            result = collect_pdf_source(source, preview=False)
        else:
            result = _unsupported_source_result(source)
    except Exception as exc:
        result = {
            "source_id": source["id"],
            "source_name": source.get("name"),
            "parser_type": source.get("parser_type"),
            "inserted_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "message": str(exc),
        }

    result["source_id"] = result.get("source_id") or source.get("id")
    result["source_name"] = result.get("source_name") or source.get("name")
    result["parser_type"] = result.get("parser_type") or source.get("parser_type")

    finished_at = _now_text()
    try:
        _save_collector_run(
            source=source,
            result=result,
            started_at=started_at,
            finished_at=finished_at,
        )
    except Exception as exc:
        # 采集日志保存失败不能影响接口返回，但要把错误带回调用方。
        result["collector_run_id"] = None
        result["collector_run_save_error"] = str(exc)
        result["status"] = _judge_status(result)

    return result


def run_enabled_collectors() -> list[dict]:
    """运行所有启用的数据源采集器，并保存每个来源的运行记录。"""
    init_db()
    sources = _list_enabled_sources()
    return [_run_source(source) for source in sources]


def run_single_collector(source_id: int) -> dict:
    """只运行一个指定数据源的采集器，并保存 collector_runs 记录。"""
    init_db()
    source = _get_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="原始数据源不存在")

    return _run_source(source)
