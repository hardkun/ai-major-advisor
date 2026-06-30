"""AI 相关专业数据质量检查服务。"""

from db import create_connection, init_db


def _append_issue(items: list[dict], table_name: str, row_id: int, field: str, message: str):
    items.append(
        {
            "table": table_name,
            "id": row_id,
            "field": field,
            "message": message,
        }
    )


def _check_row(
    table_name: str,
    row: dict,
    errors: list[dict],
    warnings: list[dict],
) -> None:
    row_id = row.get("id")

    required_errors = [
        ("school_name", "school_name 不能为空"),
        ("major_name", "major_name 不能为空"),
        ("admission_year", "admission_year 不能为空"),
        ("admission_province", "admission_province 不能为空"),
        ("min_score", "min_score 不能为空"),
        ("source_url", "source_url 不能为空"),
        ("source_name", "source_name 不能为空"),
    ]
    for field, message in required_errors:
        if row.get(field) is None or str(row.get(field)).strip() == "":
            _append_issue(errors, table_name, row_id, field, message)

    if row.get("admission_province") and row.get("admission_province") != "四川":
        _append_issue(errors, table_name, row_id, "admission_province", "admission_province 必须是四川")

    subject_type = row.get("subject_type")
    if subject_type not in {"物理类", "历史类"}:
        _append_issue(warnings, table_name, row_id, "subject_type", "subject_type 建议为物理类或历史类")

    if row.get("min_rank") is None or str(row.get("min_rank")).strip() == "":
        _append_issue(warnings, table_name, row_id, "min_rank", "min_rank 建议补充")

    if row.get("direction_tags") is None or str(row.get("direction_tags")).strip() == "":
        _append_issue(warnings, table_name, row_id, "direction_tags", "direction_tags 不能为空，建议补充方向标签")


def check_ai_major_data_quality() -> dict:
    """检查 raw_admission_records 和 admissions 的核心数据质量。"""
    init_db()
    errors: list[dict] = []
    warnings: list[dict] = []

    conn = create_connection()
    try:
        raw_rows = conn.execute(
            """
            SELECT
                id,
                school_name,
                major_name,
                admission_year,
                admission_province,
                subject_type,
                min_score,
                min_rank,
                source_url,
                source_name,
                direction_tags
            FROM raw_admission_records
            """
        ).fetchall()
        for row in raw_rows:
            _check_row("raw_admission_records", dict(row), errors, warnings)

        admission_rows = conn.execute(
            """
            SELECT
                admissions.id AS id,
                schools.name AS school_name,
                majors.name AS major_name,
                admissions.year AS admission_year,
                admissions.province AS admission_province,
                admissions.subject_type AS subject_type,
                admissions.min_score AS min_score,
                admissions.min_rank AS min_rank,
                COALESCE(data_sources.url, admissions.source) AS source_url,
                COALESCE(data_sources.name, admissions.source) AS source_name,
                majors.direction_tags AS direction_tags
            FROM admissions
            JOIN schools ON schools.id = admissions.school_id
            JOIN majors ON majors.id = admissions.major_id
            LEFT JOIN data_sources ON data_sources.id = admissions.source_id
            """
        ).fetchall()
        for row in admission_rows:
            _check_row("admissions", dict(row), errors, warnings)

        return {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:500],
            "warnings": warnings[:500],
        }
    finally:
        conn.close()
