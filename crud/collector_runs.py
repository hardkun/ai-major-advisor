from db import create_connection
from schemas.collector_runs import CollectorRunResponse


def create_collector_run(
    raw_source_id: int | None,
    source_name: str | None,
    parser_type: str | None,
    status: str,
    inserted_count: int = 0,
    skipped_count: int = 0,
    error_count: int = 0,
    message: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> int:
    """保存一次单数据源采集运行结果，返回 collector_run_id。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO collector_runs
                (raw_source_id, source_name, parser_type, status,
                 inserted_count, skipped_count, error_count, message,
                 started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_source_id,
                source_name,
                parser_type,
                status,
                inserted_count,
                skipped_count,
                error_count,
                message,
                started_at,
                finished_at,
            ),
        )
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()


def list_collector_runs(limit: int = 50) -> list[CollectorRunResponse]:
    """查询最近的采集运行记录。"""
    safe_limit = min(max(limit, 1), 200)
    db = create_connection()
    try:
        rows = db.execute(
            """
            SELECT * FROM collector_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
        return [CollectorRunResponse(**dict(row)) for row in rows]
    finally:
        db.close()
