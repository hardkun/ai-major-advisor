"""批量导入包含真实招生字段的 CSV 数据。"""

import csv
from datetime import datetime
from pathlib import Path

from db import create_connection, init_db
from utils.subject_type import normalize_subject_type


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "real_admissions_template.csv"


def empty_to_none(value: str | None) -> str | None:
    """清理字符串；CSV 空字段保存为数据库 NULL。"""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_optional_int(
    value: str | None,
    field_name: str,
    row_number: int,
) -> int | None:
    """安全转换可为空的整数字段。"""
    cleaned = empty_to_none(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ValueError(
            f"第 {row_number} 行的 {field_name} 不是有效整数：{cleaned}"
        ) from exc


def parse_verified(value: str | None, row_number: int) -> int:
    """将常见布尔写法转换为 SQLite 使用的 0 或 1。"""
    cleaned = (value or "").strip().lower()
    true_values = {"1", "true", "是"}
    false_values = {"", "0", "false", "否"}

    if cleaned in true_values:
        return 1
    if cleaned in false_values:
        return 0
    raise ValueError(
        f"第 {row_number} 行的 is_verified 仅支持 0/1/true/false/是/否"
    )


def read_csv_rows() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"找不到真实数据 CSV：{CSV_PATH}")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_fields = {
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
            "source_type",
            "source_url",
            "source_description",
            "is_verified",
            "remark",
        }
        missing_fields = required_fields - set(reader.fieldnames or [])
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"CSV 缺少字段：{missing}")
        return list(reader)


def import_real_admissions() -> None:
    rows = read_csv_rows()
    if not rows:
        print("CSV 中没有可导入的数据")
        return

    init_db()
    db = create_connection()

    new_sources = 0
    new_schools = 0
    new_majors = 0
    new_admissions = 0
    skipped_admissions = 0

    try:
        source_ids: dict[str, int] = {}

        # 先准备数据来源，以便导入批次和录取记录关联 source_id。
        for row in rows:
            source_name = empty_to_none(row.get("source_name"))
            if source_name is None or source_name in source_ids:
                continue

            source = db.execute(
                "SELECT id FROM data_sources WHERE name = ? ORDER BY id LIMIT 1",
                (source_name,),
            ).fetchone()
            if source is None:
                cursor = db.execute(
                    """
                    INSERT INTO data_sources
                        (name, source_type, url, description)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        source_name,
                        empty_to_none(row.get("source_type")),
                        empty_to_none(row.get("source_url")),
                        empty_to_none(row.get("source_description")),
                    ),
                )
                source_ids[source_name] = int(cursor.lastrowid)
                new_sources += 1
            else:
                source_ids[source_name] = int(source["id"])

        years = {
            int(row["admission_year"].strip())
            for row in rows
            if empty_to_none(row.get("admission_year")) is not None
        }
        provinces = {
            row["admission_province"].strip()
            for row in rows
            if empty_to_none(row.get("admission_province")) is not None
        }
        unique_source_ids = set(source_ids.values())

        batch_name = "真实招生数据导入 - " + datetime.now().strftime("%Y%m%d%H%M%S")
        batch_cursor = db.execute(
            """
            INSERT INTO import_batches
                (batch_name, data_year, province, source_id, row_count, remark)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                batch_name,
                next(iter(years)) if len(years) == 1 else None,
                next(iter(provinces)) if len(provinces) == 1 else None,
                next(iter(unique_source_ids)) if len(unique_source_ids) == 1 else None,
                f"从 {CSV_PATH.name} 导入",
            ),
        )
        import_batch_id = int(batch_cursor.lastrowid)

        for row_number, row in enumerate(rows, start=2):
            school_name = empty_to_none(row.get("school_name"))
            major_name = empty_to_none(row.get("major_name"))
            year = parse_optional_int(
                row.get("admission_year"), "admission_year", row_number
            )
            province = empty_to_none(row.get("admission_province"))
            subject_type = normalize_subject_type(empty_to_none(row.get("subject_type")))

            if not school_name or not major_name or year is None:
                raise ValueError(
                    f"第 {row_number} 行缺少 school_name、major_name 或 admission_year"
                )
            if not province or not subject_type:
                raise ValueError(
                    f"第 {row_number} 行缺少 admission_province 或 subject_type"
                )

            school = db.execute(
                "SELECT id FROM schools WHERE name = ? ORDER BY id LIMIT 1",
                (school_name,),
            ).fetchone()
            if school is None:
                cursor = db.execute(
                    """
                    INSERT INTO schools (name, province, city, level, tags)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        school_name,
                        empty_to_none(row.get("school_province")),
                        empty_to_none(row.get("city")),
                        empty_to_none(row.get("school_level")),
                        empty_to_none(row.get("school_tags")),
                    ),
                )
                school_id = int(cursor.lastrowid)
                new_schools += 1
            else:
                school_id = int(school["id"])

            major = db.execute(
                "SELECT id FROM majors WHERE name = ? ORDER BY id LIMIT 1",
                (major_name,),
            ).fetchone()
            if major is None:
                cursor = db.execute(
                    """
                    INSERT INTO majors
                        (name, category, direction_tags, description, career_paths)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        major_name,
                        empty_to_none(row.get("major_category")),
                        empty_to_none(row.get("direction_tags")),
                        empty_to_none(row.get("major_description")),
                        empty_to_none(row.get("career_paths")),
                    ),
                )
                major_id = int(cursor.lastrowid)
                new_majors += 1
            else:
                major_id = int(major["id"])

            major_group_code = empty_to_none(row.get("major_group_code"))
            major_code = empty_to_none(row.get("major_code"))
            duplicate = db.execute(
                """
                SELECT id FROM admissions
                WHERE school_id = ?
                  AND major_id = ?
                  AND year = ?
                  AND province = ?
                  AND subject_type = ?
                  AND major_group_code IS ?
                  AND major_code IS ?
                LIMIT 1
                """,
                (
                    school_id,
                    major_id,
                    year,
                    province,
                    subject_type,
                    major_group_code,
                    major_code,
                ),
            ).fetchone()
            if duplicate is not None:
                skipped_admissions += 1
                continue

            source_name = empty_to_none(row.get("source_name"))
            source_id = source_ids.get(source_name) if source_name else None
            db.execute(
                """
                INSERT INTO admissions
                    (school_id, major_id, year, province, subject_type, batch,
                     min_score, min_rank, plan_count, tuition, source,
                     school_code, major_group_code, major_code,
                     elective_requirement, campus, source_id, import_batch_id,
                     is_verified, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    school_id,
                    major_id,
                    year,
                    province,
                    subject_type,
                    empty_to_none(row.get("batch")),
                    parse_optional_int(row.get("min_score"), "min_score", row_number),
                    parse_optional_int(row.get("min_rank"), "min_rank", row_number),
                    parse_optional_int(row.get("plan_count"), "plan_count", row_number),
                    empty_to_none(row.get("tuition")),
                    source_name,
                    empty_to_none(row.get("school_code")),
                    major_group_code,
                    major_code,
                    empty_to_none(row.get("elective_requirement")),
                    empty_to_none(row.get("campus")),
                    source_id,
                    import_batch_id,
                    parse_verified(row.get("is_verified"), row_number),
                    empty_to_none(row.get("remark")),
                ),
            )
            new_admissions += 1

        db.execute(
            "UPDATE import_batches SET row_count = ? WHERE id = ?",
            (new_admissions, import_batch_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"新增数据来源数量：{new_sources}")
    print(f"新增学校数量：{new_schools}")
    print(f"新增专业数量：{new_majors}")
    print(f"新增录取数据数量：{new_admissions}")
    print(f"跳过重复数据数量：{skipped_admissions}")
    print(f"import_batch_id：{import_batch_id}")


if __name__ == "__main__":
    import_real_admissions()
