import sqlite3

from schemas.admission import AdmissionCreate
from utils.subject_type import normalize_subject_type


def create_admission(db: sqlite3.Connection, admission: AdmissionCreate) -> dict:
    cursor = db.execute(
        """
        INSERT INTO admissions
            (school_id, major_id, year, province, subject_type, batch,
             min_score, min_rank, plan_count, tuition, source, school_code,
             major_group_code, major_code, elective_requirement, campus,
             source_id, import_batch_id, is_verified, remark)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            admission.school_id,
            admission.major_id,
            admission.year,
            admission.province,
            normalize_subject_type(admission.subject_type),
            admission.batch,
            admission.min_score,
            admission.min_rank,
            admission.plan_count,
            admission.tuition,
            admission.source,
            admission.school_code,
            admission.major_group_code,
            admission.major_code,
            admission.elective_requirement,
            admission.campus,
            admission.source_id,
            admission.import_batch_id,
            int(admission.is_verified),
            admission.remark,
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM admissions WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    result = dict(row)
    result["is_verified"] = bool(result["is_verified"])
    return result


def list_admissions(
    db: sqlite3.Connection,
    school_id: int | None = None,
    major_id: int | None = None,
    year: int | None = None,
    province: str | None = None,
) -> list[dict]:
    sql = """
        SELECT * FROM admissions WHERE 1 = 1
    """
    params: list[object] = []

    if school_id is not None:
        sql += " AND school_id = ?"
        params.append(school_id)
    if major_id is not None:
        sql += " AND major_id = ?"
        params.append(major_id)
    if year is not None:
        sql += " AND year = ?"
        params.append(year)
    if province is not None:
        sql += " AND province = ?"
        params.append(province)

    sql += " ORDER BY year DESC, id DESC"
    rows = db.execute(sql, params).fetchall()
    results = []
    for row in rows:
        result = dict(row)
        result["is_verified"] = bool(result["is_verified"])
        results.append(result)
    return results
