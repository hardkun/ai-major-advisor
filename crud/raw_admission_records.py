import sqlite3

from db import create_connection
from schemas.raw_admission_records import (
    RawAdmissionRecordCreate,
    RawAdmissionRecordResponse,
    RawAdmissionRecordUpdateStatus,
)


RAW_ADMISSION_COLUMNS = [
    "raw_source_id",
    "school_name",
    "school_code",
    "school_province",
    "city",
    "school_level",
    "school_tags",
    "major_name",
    "major_code",
    "major_category",
    "direction_tags",
    "major_description",
    "career_paths",
    "admission_year",
    "admission_province",
    "subject_type",
    "batch",
    "major_group_code",
    "elective_requirement",
    "min_score",
    "min_rank",
    "plan_count",
    "tuition",
    "campus",
    "source_name",
    "source_url",
    "raw_text",
    "status",
    "error_message",
]


def _row_to_response(row: sqlite3.Row) -> RawAdmissionRecordResponse:
    data = dict(row)
    data["is_duplicate"] = bool(data["is_duplicate"])
    return RawAdmissionRecordResponse(**data)


def create_raw_admission_record(
    data: RawAdmissionRecordCreate,
) -> RawAdmissionRecordResponse:
    """新增一条未核验原始招生记录。"""
    db = create_connection()
    try:
        placeholders = ", ".join(["?"] * len(RAW_ADMISSION_COLUMNS))
        column_names = ", ".join(RAW_ADMISSION_COLUMNS)
        values = [getattr(data, column) for column in RAW_ADMISSION_COLUMNS]

        cursor = db.execute(
            f"""
            INSERT INTO raw_admission_records ({column_names})
            VALUES ({placeholders})
            """,
            values,
        )
        db.commit()

        mark_duplicate_records(db)

        row = db.execute(
            "SELECT * FROM raw_admission_records WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_response(row)
    finally:
        db.close()


def list_raw_admission_records(
    status: str | None = None,
) -> list[RawAdmissionRecordResponse]:
    """查询原始招生记录列表，可按状态过滤。"""
    db = create_connection()
    try:
        if status:
            rows = db.execute(
                """
                SELECT * FROM raw_admission_records
                WHERE status = ?
                ORDER BY id DESC
                """,
                (status,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM raw_admission_records ORDER BY id DESC"
            ).fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        db.close()


def get_raw_admission_record_by_id(
    record_id: int,
) -> RawAdmissionRecordResponse | None:
    db = create_connection()
    try:
        row = db.execute(
            "SELECT * FROM raw_admission_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        return _row_to_response(row) if row else None
    finally:
        db.close()


def update_raw_admission_record_status(
    record_id: int,
    data: RawAdmissionRecordUpdateStatus,
) -> RawAdmissionRecordResponse | None:
    """更新原始招生记录状态。"""
    db = create_connection()
    try:
        row = db.execute(
            "SELECT id FROM raw_admission_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not row:
            return None

        db.execute(
            """
            UPDATE raw_admission_records
            SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (data.status, data.error_message, record_id),
        )
        db.commit()

        updated = db.execute(
            "SELECT * FROM raw_admission_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        return _row_to_response(updated)
    finally:
        db.close()


def mark_duplicate_records(db: sqlite3.Connection | None = None) -> None:
    """标记重复原始记录。

    重复规则：
    school_name、major_name、admission_year、admission_province、
    subject_type、major_group_code、major_code 全部相同。
    """
    owns_connection = db is None
    connection = db or create_connection()
    try:
        connection.execute("UPDATE raw_admission_records SET is_duplicate = 0")
        connection.execute(
            """
            UPDATE raw_admission_records
            SET is_duplicate = 1
            WHERE EXISTS (
                SELECT 1
                FROM raw_admission_records AS other
                WHERE other.id != raw_admission_records.id
                  AND COALESCE(other.school_name, '') =
                      COALESCE(raw_admission_records.school_name, '')
                  AND COALESCE(other.major_name, '') =
                      COALESCE(raw_admission_records.major_name, '')
                  AND COALESCE(other.admission_year, -1) =
                      COALESCE(raw_admission_records.admission_year, -1)
                  AND COALESCE(other.admission_province, '') =
                      COALESCE(raw_admission_records.admission_province, '')
                  AND COALESCE(other.subject_type, '') =
                      COALESCE(raw_admission_records.subject_type, '')
                  AND COALESCE(other.major_group_code, '') =
                      COALESCE(raw_admission_records.major_group_code, '')
                  AND COALESCE(other.major_code, '') =
                      COALESCE(raw_admission_records.major_code, '')
            )
            """
        )
        connection.commit()
    finally:
        if owns_connection:
            connection.close()
