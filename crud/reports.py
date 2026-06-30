from db import create_connection


def create_report(
    log_id: int,
    free_result_json: str,
    paid_result_json: str,
) -> int:
    """保存免费版和付费版报告，并返回报告 ID。"""
    db = create_connection()
    try:
        cursor = db.execute(
            """
            INSERT INTO reports
                (log_id, free_result_json, paid_result_json)
            VALUES (?, ?, ?)
            """,
            (log_id, free_result_json, paid_result_json),
        )
        db.commit()
        return int(cursor.lastrowid)
    finally:
        db.close()


def get_report_by_id(report_id: int) -> dict | None:
    """按 ID 查询报告原始记录。"""
    db = create_connection()
    try:
        row = db.execute(
            "SELECT * FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def mark_report_paid(report_id: int) -> bool:
    """将报告标记为已支付；报告不存在时返回 False。"""
    db = create_connection()
    try:
        report = db.execute(
            "SELECT id FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if report is None:
            return False

        db.execute(
            """
            UPDATE reports
            SET is_paid = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (report_id,),
        )
        db.commit()
        return True
    finally:
        db.close()
