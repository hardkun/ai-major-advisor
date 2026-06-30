from fastapi import HTTPException

from db import create_connection
from utils.subject_type import normalize_subject_type


def _get_or_create_school(db, record) -> int:
    row = db.execute(
        "SELECT id FROM schools WHERE name = ? ORDER BY id DESC LIMIT 1",
        (record["school_name"],),
    ).fetchone()
    if row:
        return row["id"]

    cursor = db.execute(
        """
        INSERT INTO schools (name, province, city, level, tags)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            record["school_name"],
            record["school_province"],
            record["city"],
            record["school_level"],
            record["school_tags"],
        ),
    )
    return cursor.lastrowid


def _get_or_create_major(db, record) -> int:
    row = db.execute(
        "SELECT id FROM majors WHERE name = ? ORDER BY id DESC LIMIT 1",
        (record["major_name"],),
    ).fetchone()
    if row:
        return row["id"]

    cursor = db.execute(
        """
        INSERT INTO majors
            (name, category, direction_tags, description, career_paths)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            record["major_name"],
            record["major_category"],
            record["direction_tags"],
            record["major_description"],
            record["career_paths"],
        ),
    )
    return cursor.lastrowid


def _get_raw_source_info(db, raw_source_id: int | None) -> dict | None:
    if raw_source_id is None:
        return None
    row = db.execute(
        "SELECT * FROM raw_data_sources WHERE id = ?",
        (raw_source_id,),
    ).fetchone()
    return dict(row) if row else None


def _get_or_create_data_source(db, record, raw_source: dict | None) -> int:
    source_name = record["source_name"] or (
        raw_source["name"] if raw_source else "原始采集数据"
    )
    source_url = record["source_url"] or (raw_source["url"] if raw_source else None)
    source_type = raw_source["source_type"] if raw_source else "raw_verified"
    description = "由原始采集记录核验生成的数据来源"

    row = db.execute(
        """
        SELECT id FROM data_sources
        WHERE name = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (source_name,),
    ).fetchone()
    if row:
        return row["id"]

    cursor = db.execute(
        """
        INSERT INTO data_sources (name, source_type, url, description)
        VALUES (?, ?, ?, ?)
        """,
        (source_name, source_type, source_url, description),
    )
    return cursor.lastrowid


def _validate_record_for_verification(record) -> None:
    required_fields = [
        "school_name",
        "major_name",
        "admission_year",
        "admission_province",
        "subject_type",
    ]
    missing_fields = [field for field in required_fields if not record[field]]
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"原始记录缺少正式录取数据必需字段：{', '.join(missing_fields)}",
        )


def verify_raw_record_to_admission(record_id: int) -> dict:
    """将一条人工核验通过的原始记录写入正式 admissions 表。"""
    db = create_connection()
    try:
        record = db.execute(
            "SELECT * FROM raw_admission_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if not record:
            raise HTTPException(status_code=404, detail="原始招生记录不存在")

        if record["status"] == "verified":
            return {
                "admission_id": None,
                "record_id": record_id,
                "message": "该原始记录已经核验通过，无需重复写入。",
            }

        _validate_record_for_verification(record)

        raw_source = _get_raw_source_info(db, record["raw_source_id"])
        school_id = _get_or_create_school(db, record)
        major_id = _get_or_create_major(db, record)
        source_id = _get_or_create_data_source(db, record, raw_source)
        normalized_subject_type = normalize_subject_type(record["subject_type"])

        cursor = db.execute(
            """
            INSERT INTO admissions
                (school_id, major_id, year, province, subject_type, batch,
                 min_score, min_rank, plan_count, tuition, source,
                 school_code, major_group_code, major_code,
                 elective_requirement, campus, source_id,
                 is_verified, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                school_id,
                major_id,
                record["admission_year"],
                record["admission_province"],
                normalized_subject_type,
                record["batch"],
                record["min_score"],
                record["min_rank"],
                record["plan_count"],
                record["tuition"],
                record["source_name"],
                record["school_code"],
                record["major_group_code"],
                record["major_code"],
                record["elective_requirement"],
                record["campus"],
                source_id,
                1,
                "由原始采集记录核验生成",
            ),
        )

        db.execute(
            """
            UPDATE raw_admission_records
            SET status = 'verified',
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (record_id,),
        )
        db.commit()

        return {
            "admission_id": cursor.lastrowid,
            "record_id": record_id,
            "message": "原始记录已核验通过，并写入正式 admissions 表。",
        }
    finally:
        db.close()
